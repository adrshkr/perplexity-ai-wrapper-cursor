"""
Perplexity AI Wrapper - Network Inspector
File: tools/network_inspector.py

This tool helps discover and document Perplexity's API endpoints
by monitoring network traffic during browser usage.
"""
import json
import asyncio
import sys
from datetime import datetime
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from pathlib import Path

# Force unbuffered output for real-time terminal updates
# NOTE: All print statements use flush=True for real-time output
# Run Python with -u flag for best results: python -u script.py


class NetworkInspector:
    """
    Monitor and capture network requests to discover API structure
    """
    
    def __init__(self, output_dir: str = "api_discovery"):
        """
        Initialize network inspector
        
        Args:
            output_dir: Directory to save captured data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.captured_requests: List[Dict] = []
        self.captured_responses: List[Dict] = []
        self.api_endpoints: Dict[str, List[Dict]] = {}
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    async def start(self, headless: bool = False):
        """Start browser with network monitoring"""
        print("Starting Network Inspector...", flush=True)
        print("="*70, flush=True)
        
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        self.page = await self.context.new_page()
        
        # CRITICAL: Enable request interception to see ALL requests
        # This bypasses any filtering and captures everything
        await self.page.route("**/*", self._route_handler)
        
        # Set up network monitoring - capture ALL requests
        self.page.on("request", self._on_request)
        self.page.on("response", self._on_response)
        
        # Monitor WebSocket connections
        self.page.on("websocket", self._on_websocket)
        
        # Monitor console for any API-related logs
        self.page.on("console", self._on_console)
        
        # Monitor page errors
        self.page.on("pageerror", self._on_page_error)
        
        print("[OK] Browser started with network monitoring", flush=True)
        print("[OK] Monitoring: HTTP requests, WebSockets, SSE, Console logs", flush=True)
        print("[OK] Navigating to Perplexity...", flush=True)
        
        await self.page.goto("https://www.perplexity.ai", wait_until="networkidle")
        await asyncio.sleep(3)
        
        print("[OK] Ready to capture traffic", flush=True)
        print("[!] IMPORTANT: Perform a search in the browser to capture search endpoints!", flush=True)
        print("[!] Watch for [TARGET] emoji - those are search-related endpoints\n", flush=True)
    
    async def _route_handler(self, route):
        """Intercept and log ALL network requests before they're processed"""
        try:
            request = route.request
            url = request.url
            
            # Log ALL requests to Perplexity domains (including subdomains)
            if 'perplexity' in url.lower():
                # Extract method and URL
                method = request.method
                endpoint = self._extract_endpoint(url)
                
                # Log immediately to ensure we see it
                print(f"[INTERCEPT] {method} {endpoint}", flush=True)
                
                # Check if it's a search-related request
                is_search = any(term in endpoint.lower() or term in url.lower() 
                              for term in ['search', 'chat', 'query', 'ask', 'stream', 'compose', 'message'])
                if is_search:
                    print(f"   [TARGET] SEARCH-RELATED REQUEST DETECTED!", flush=True)
                    if request.post_data:
                        print(f"   Post data: {request.post_data[:300]}...", flush=True)
            
            # Continue the request (don't block it)
            await route.continue_()
        except Exception as e:
            # Don't crash on route handler errors
            try:
                await route.continue_()
            except:
                pass
    
    def _on_page_error(self, error):
        """Capture page errors"""
        print(f"❌ PAGE ERROR: {error}", flush=True)
    
    def _on_request(self, request):
        """Capture outgoing requests - capture EVERYTHING related to Perplexity"""
        url = request.url
        
        # Capture ALL Perplexity-related requests (including subdomains, CDNs, etc.)
        if 'perplexity' in url.lower():
            # Skip only obvious static assets
            resource_type = request.resource_type
            if resource_type in ['stylesheet', 'image', 'font', 'media']:
                return
            
            # Log ALL non-GET requests (POST, PUT, PATCH, DELETE)
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                self._log_request(request, url)
            # Log all /api/ requests
            elif '/api/' in url:
                self._log_request(request, url)
            # Log WebSocket, SSE, stream endpoints
            elif any(term in url.lower() for term in ['/socket', '/sse', '/stream', '/ws', '/wss']):
                self._log_request(request, url)
            # Log anything with search/chat/query in URL
            elif any(term in url.lower() for term in ['/chat', '/search', '/query', '/ask', '/compose', '/message']):
                self._log_request(request, url)
            # Log any xhr/fetch requests (likely API calls)
            elif resource_type in ['xhr', 'fetch']:
                self._log_request(request, url)
    
    def _log_request(self, request, url):
        """Log a request with full details"""
        request_data = {
            'timestamp': datetime.now().isoformat(),
            'url': url,
            'method': request.method,
            'headers': dict(request.headers),
            'post_data': request.post_data if request.method in ['POST', 'PUT', 'PATCH'] else None,
            'resource_type': request.resource_type
        }
        
        self.captured_requests.append(request_data)
        
        # Organize by endpoint
        endpoint = self._extract_endpoint(url)
        if endpoint not in self.api_endpoints:
            self.api_endpoints[endpoint] = []
        self.api_endpoints[endpoint].append(request_data)
        
        # Highlight important endpoints
        is_search = any(term in endpoint.lower() for term in ['search', 'chat', 'query', 'ask', 'stream'])
        emoji = "🎯" if is_search else "📤"
        
        print(f"{emoji} REQUEST: {request.method} {endpoint}", flush=True)
        if request.post_data:
            try:
                payload = json.loads(request.post_data)
                print(f"   Payload: {json.dumps(payload, indent=2)[:500]}...", flush=True)
            except:
                print(f"   Payload: {request.post_data[:200]}...", flush=True)
        
        # Log headers for POST requests (might contain important info)
        if request.method == 'POST' and is_search:
            important_headers = {k: v for k, v in request.headers.items() 
                                if k.lower() in ['content-type', 'x-requested-with', 'referer', 'origin']}
            if important_headers:
                print(f"   Headers: {json.dumps(important_headers, indent=2)}", flush=True)
    
    def _on_websocket(self, ws):
        """Capture WebSocket connections"""
        url = ws.url
        if 'perplexity' in url.lower():
            print(f"🔌 WEBSOCKET: {url}", flush=True)
            # Store reference to avoid closure issues
            def on_received(data):
                try:
                    self._on_ws_frame(url, "received", data)
                except Exception as e:
                    print(f"   Error in WS frame received: {e}", flush=True)
            
            def on_sent(data):
                try:
                    self._on_ws_frame(url, "sent", data)
                except Exception as e:
                    print(f"   Error in WS frame sent: {e}", flush=True)
            
            ws.on("framereceived", on_received)
            ws.on("framesent", on_sent)
    
    def _on_ws_frame(self, url, direction, data):
        """Capture WebSocket frames"""
        try:
            endpoint = self._extract_endpoint(url)
            try:
                # Try to parse as JSON
                if isinstance(data, (str, bytes)):
                    data_str = data.decode('utf-8') if isinstance(data, bytes) else data
                    frame_data = json.loads(data_str)
                    print(f"🔌 WS {direction.upper()}: {endpoint}", flush=True)
                    print(f"   Data: {json.dumps(frame_data, indent=2)[:300]}...", flush=True)
                else:
                    print(f"🔌 WS {direction.upper()}: {endpoint}", flush=True)
                    print(f"   Data: {str(data)[:200]}...", flush=True)
            except (json.JSONDecodeError, UnicodeDecodeError):
                print(f"🔌 WS {direction.upper()}: {endpoint}", flush=True)
                data_str = str(data)[:200] if not isinstance(data, (str, bytes)) else (data.decode('utf-8', errors='ignore')[:200] if isinstance(data, bytes) else data[:200])
                print(f"   Data: {data_str}...", flush=True)
        except Exception as e:
            print(f"🔌 WS {direction.upper()}: Error processing frame: {e}", flush=True)
    
    def _on_console(self, msg):
        """Capture console messages (might contain API info)"""
        text = msg.text
        if any(term in text.lower() for term in ['api', 'endpoint', 'search', 'query', 'error']):
            print(f"💬 CONSOLE: {text[:200]}", flush=True)
    
    async def _on_response(self, response):
        """Capture incoming responses"""
        url = response.url
        
        # Capture ALL Perplexity API responses (not just /api/)
        if 'perplexity' in url.lower():
            # Skip static assets
            content_type = response.headers.get('content-type', '')
            if any(t in content_type for t in ['text/css', 'image/', 'font/', 'video/']):
                return
            
            # Get the request method from the request object
            request = response.request
            method = request.method if request else 'GET'
            
            # Log API responses, streams, SSE, etc.
            # Check URL patterns OR if it's a POST/PUT/PATCH response
            if ('/api/' in url or '/socket' in url or '/sse' in url or '/stream' in url or 
                '/chat' in url or '/search' in url or '/query' in url or 
                method in ['POST', 'PUT', 'PATCH']):
                await self._log_response(response, url)
    
    async def _log_response(self, response, url):
        """Log response with error handling"""
        try:
            body = await response.body()
            body_text = body.decode('utf-8', errors='ignore')
            
            # Try to parse as JSON
            try:
                body_json = json.loads(body_text)
            except (json.JSONDecodeError, ValueError):
                body_json = None
            
            response_data = {
                'timestamp': datetime.now().isoformat(),
                'url': url,
                'status': response.status,
                'headers': dict(response.headers),
                'body': body_json if body_json else body_text[:2000],  # Increased limit
                'content_type': response.headers.get('content-type', '')
            }
            
            self.captured_responses.append(response_data)
            
            endpoint = self._extract_endpoint(url)
            is_search = any(term in endpoint.lower() for term in ['search', 'chat', 'query', 'ask', 'stream', 'compose', 'message'])
            emoji = "🎯" if is_search else "📥"
            
            print(f"{emoji} RESPONSE: {response.status} {endpoint}", flush=True)
            if body_json:
                print(f"   Body: {json.dumps(body_json, indent=2)[:500]}...", flush=True)
            elif len(body_text) > 0:
                # Show first part of non-JSON response
                preview = body_text[:300].replace('\n', ' ')
                print(f"   Body (preview): {preview}...", flush=True)
            
        except Exception as e:
            # Don't crash on response errors, just log them
            print(f"   ⚠️ Error capturing response: {str(e)}", flush=True)
    
    def _extract_endpoint(self, url: str) -> str:
        """Extract endpoint from full URL"""
        # Remove base URL and query parameters
        if 'perplexity.ai' in url:
            parts = url.split('perplexity.ai')
            if len(parts) > 1:
                endpoint = parts[1].split('?')[0]
                return endpoint
        return url
    
    async def interactive_capture(self):
        """
        Interactive mode - user performs actions while we capture
        """
        print("\n" + "="*70)
        print("INTERACTIVE CAPTURE MODE")
        print("="*70)
        print("Instructions:")
        print("  1. Use the browser window to interact with Perplexity")
        print("  2. Perform searches, follow-ups, etc.")
        print("  3. All network traffic will be captured")
        print("  4. Press Ctrl+C in terminal when done")
        print("="*70 + "\n")
        
        try:
            # Keep running while user interacts
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n\nCapture stopped by user")
    
    async def automated_capture(self, queries: List[str]):
        """
        Automated capture - perform searches automatically
        
        Args:
            queries: List of search queries to test
        """
        print("\n" + "="*70)
        print("AUTOMATED CAPTURE MODE")
        print("="*70)
        print(f"Testing {len(queries)} queries...\n")
        
        for idx, query in enumerate(queries, 1):
            print(f"\n[{idx}/{len(queries)}] Testing query: {query}")
            print("-"*70)
            
            # Find search box
            search_box = await self.page.wait_for_selector(
                'textarea[placeholder*="Ask"]',
                timeout=10000
            )
            
            # Clear and type query
            await search_box.fill("")
            await search_box.type(query, delay=50)
            await search_box.press('Enter')
            
            # Wait for response
            print("Waiting for response...")
            await asyncio.sleep(5)  # Let response complete
            
            print(f"✓ Completed query {idx}")
            await asyncio.sleep(2)  # Delay between queries
    
    def analyze_endpoints(self) -> Dict[str, Any]:
        """
        Analyze captured traffic and generate endpoint documentation
        
        Returns:
            Analysis summary
        """
        print("\n" + "="*70)
        print("ENDPOINT ANALYSIS")
        print("="*70)
        
        analysis = {
            'total_requests': len(self.captured_requests),
            'total_responses': len(self.captured_responses),
            'unique_endpoints': len(self.api_endpoints),
            'endpoints': {}
        }
        
        # Analyze each endpoint
        for endpoint, requests in self.api_endpoints.items():
            methods = set(req['method'] for req in requests)
            
            # Sample payload
            sample_payload = None
            for req in requests:
                if req['post_data']:
                    try:
                        sample_payload = json.loads(req['post_data'])
                        break
                    except:
                        pass
            
            analysis['endpoints'][endpoint] = {
                'methods': list(methods),
                'call_count': len(requests),
                'sample_payload': sample_payload,
                'sample_request': requests[0] if requests else None
            }
            
            print(f"\nEndpoint: {endpoint}")
            print(f"  Methods: {', '.join(methods)}")
            print(f"  Calls: {len(requests)}")
            if sample_payload:
                print(f"  Sample Payload:")
                print(f"    {json.dumps(sample_payload, indent=4)[:300]}...")
        
        return analysis
    
    def save_results(self):
        """Save all captured data to files"""
        print("\n" + "="*70)
        print("SAVING RESULTS")
        print("="*70)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save requests
        requests_file = self.output_dir / f"requests_{timestamp}.json"
        with open(requests_file, 'w') as f:
            json.dump(self.captured_requests, f, indent=2)
        print(f"✓ Saved {len(self.captured_requests)} requests: {requests_file}")
        
        # Save responses
        responses_file = self.output_dir / f"responses_{timestamp}.json"
        with open(responses_file, 'w') as f:
            json.dump(self.captured_responses, f, indent=2)
        print(f"✓ Saved {len(self.captured_responses)} responses: {responses_file}")
        
        # Save endpoint analysis
        analysis = self.analyze_endpoints()
        analysis_file = self.output_dir / f"analysis_{timestamp}.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f"✓ Saved analysis: {analysis_file}")
        
        # Save endpoint documentation (Markdown)
        doc_file = self.output_dir / f"api_documentation_{timestamp}.md"
        self._generate_markdown_docs(doc_file, analysis)
        print(f"✓ Saved documentation: {doc_file}")
        
        print(f"\n✓ All results saved to: {self.output_dir}")
    
    def _generate_markdown_docs(self, filepath: Path, analysis: Dict):
        """Generate markdown documentation from analysis"""
        with open(filepath, 'w') as f:
            f.write("# Perplexity API Documentation\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- Total Requests: {analysis['total_requests']}\n")
            f.write(f"- Total Responses: {analysis['total_responses']}\n")
            f.write(f"- Unique Endpoints: {analysis['unique_endpoints']}\n\n")
            
            f.write("## Endpoints\n\n")
            
            for endpoint, data in analysis['endpoints'].items():
                f.write(f"### {endpoint}\n\n")
                f.write(f"**Methods:** {', '.join(data['methods'])}\n\n")
                f.write(f"**Call Count:** {data['call_count']}\n\n")
                
                if data['sample_payload']:
                    f.write("**Sample Payload:**\n\n")
                    f.write("```json\n")
                    f.write(json.dumps(data['sample_payload'], indent=2))
                    f.write("\n```\n\n")
                
                if data['sample_request']:
                    f.write("**Sample Request Headers:**\n\n")
                    f.write("```json\n")
                    headers = {k: v for k, v in data['sample_request']['headers'].items() 
                              if k.lower() not in ['cookie', 'authorization']}
                    f.write(json.dumps(headers, indent=2))
                    f.write("\n```\n\n")
                
                f.write("---\n\n")
    
    async def close(self):
        """Close browser and cleanup"""
        try:
            if self.browser:
                # Try graceful close first
                try:
                    await self.browser.close()
                except Exception as e:
                    # If graceful close fails, force close
                    print(f"   Warning: Browser close error (ignored): {e}", flush=True)
                    pass
            if self.playwright:
                await self.playwright.stop()
            print("\n✓ Browser closed", flush=True)
        except Exception as e:
            print(f"\n⚠ Browser cleanup warning: {e}", flush=True)
            # Continue anyway - data is already saved


# ============================================================================
# CLI Interface
# ============================================================================

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Perplexity API Network Inspector"
    )
    parser.add_argument(
        '--mode',
        choices=['interactive', 'automated'],
        default='interactive',
        help='Capture mode'
    )
    parser.add_argument(
        '--queries',
        nargs='+',
        help='Queries for automated mode'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode'
    )
    parser.add_argument(
        '--output',
        default='api_discovery',
        help='Output directory'
    )
    
    args = parser.parse_args()
    
    # Initialize inspector
    inspector = NetworkInspector(output_dir=args.output)
    
    try:
        # Start browser
        await inspector.start(headless=args.headless)
        
        # Run capture
        if args.mode == 'interactive':
            await inspector.interactive_capture()
        else:
            queries = args.queries or [
                "What is artificial intelligence?",
                "Explain quantum computing",
                "Latest AI developments"
            ]
            await inspector.automated_capture(queries)
        
        # Save results
        inspector.save_results()
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await inspector.close()


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║         Perplexity AI - Network Inspector Tool              ║
    ║                                                              ║
    ║  This tool captures API traffic to help understand the       ║
    ║  Perplexity.ai API structure and build accurate wrappers    ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())