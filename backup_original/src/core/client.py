"""
Perplexity AI Wrapper - Synchronous Client
File: src/core/client.py
"""
import requests
import json
import time
import uuid
from typing import Dict, List, Optional, Generator, Union
from .models import (
    SearchMode, AIModel, SourceType, SearchConfig, SearchResponse,
    Conversation, validate_model_compatibility,
    PerplexityException, AuthenticationError, RateLimitError,
    InvalidParameterError, NetworkError
)

# Try to import cloudscraper bypass utility
# Check both that CloudflareBypass can be imported AND that cloudscraper is actually available
CLOUDSCRAPER_AVAILABLE = False
CloudflareBypass = None

try:
    from ..utils.cloudflare_bypass import CloudflareBypass
    # Verify cloudscraper is actually available by checking if it can be imported
    # This matches the check in cloudflare_bypass.py
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    cloudscraper_path = project_root / 'cloudscraper'
    if cloudscraper_path.exists() and str(cloudscraper_path) not in sys.path:
        sys.path.insert(0, str(cloudscraper_path))
    try:
        import cloudscraper
        # If we can import it, it's available
        CLOUDSCRAPER_AVAILABLE = True
    except ImportError:
        # cloudscraper not available - disable bypass
        CLOUDSCRAPER_AVAILABLE = False
        CloudflareBypass = None
except ImportError:
    # CloudflareBypass class itself can't be imported
    CLOUDSCRAPER_AVAILABLE = False
    CloudflareBypass = None


class PerplexityClient:
    """
    Main synchronous client for Perplexity.ai
    
    Usage:
        client = PerplexityClient(cookies={'session': 'your_token'})
        response = client.search("What is quantum computing?")
        print(response.answer)
    """
    
    def __init__(
        self,
        cookies: Optional[Dict[str, str]] = None,
        base_url: str = "https://www.perplexity.ai",
        timeout: int = 30,
        max_retries: int = 3,
        user_agent: Optional[str] = None,
        use_cloudflare_bypass: bool = True,
        cloudflare_stealth: bool = True,
        proxy_rotation: Optional[List[str]] = None
    ):
        """
        Initialize Perplexity client
        
        Args:
            cookies: Authentication cookies
            base_url: Base URL for Perplexity API
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            user_agent: Custom user agent string
            use_cloudflare_bypass: Use cloudscraper for Cloudflare bypass (default: True)
            cloudflare_stealth: Enable stealth mode for cloudscraper (default: True)
            proxy_rotation: Optional list of proxy URLs for rotation
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_cloudflare_bypass = use_cloudflare_bypass and CLOUDSCRAPER_AVAILABLE
        self.conversations: Dict[str, Conversation] = {}
        self.current_conversation: Optional[Conversation] = None
        
        # Initialize session with cloudscraper if available and enabled
        if self.use_cloudflare_bypass:
            try:
                # Use minimal parameters to avoid compatibility issues
                self.bypass = CloudflareBypass(
                    browser='chrome',
                    use_stealth=cloudflare_stealth,
                    proxy_rotation=proxy_rotation,
                    interpreter='js2py',
                    debug=False
                )
                self.session = self.bypass.scraper
                
                # Update cookies if provided
                if cookies:
                    self.bypass.update_cookies(cookies)
            except Exception as e:
                # Fallback to regular requests if cloudscraper fails
                import warnings
                warnings.warn(f"Cloudflare bypass initialization failed: {e}. Falling back to regular requests.", UserWarning)
                self.use_cloudflare_bypass = False
                self.bypass = None
                self.session = requests.Session()
                if cookies:
                    self.session.cookies.update(cookies)
        else:
            # Use regular requests session
            self.bypass = None
            self.session = requests.Session()
            if cookies:
                self.session.cookies.update(cookies)
        
        # Set realistic headers (updated for SSE endpoint)
        self.session.headers.update({
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/event-stream, application/json, text/plain, */*',  # SSE support
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/json',
            'Origin': 'https://www.perplexity.ai',
            'Referer': 'https://www.perplexity.ai/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'no-cache',  # Required for SSE
        })
    
    def search(
        self,
        query: str,
        mode: Union[SearchMode, str] = SearchMode.AUTO,
        model: Optional[Union[AIModel, str]] = None,
        sources: Optional[List[Union[SourceType, str]]] = None,
        stream: bool = False,
        language: str = 'en-US',
        incognito: bool = False,
        files: Optional[Dict[str, str]] = None,
        use_conversation: bool = False,
        **kwargs
    ) -> Union[SearchResponse, Generator[Dict, None, None]]:
        """
        Execute search query
        
        Args:
            query: Search query string
            mode: Search mode (auto, pro, reasoning, deep_research)
            model: Specific AI model to use
            sources: Source types (web, scholar, social)
            stream: Whether to stream response
            language: Response language code
            incognito: Use incognito mode
            files: Dictionary of files to upload
            use_conversation: Continue current conversation
            **kwargs: Additional parameters
        
        Returns:
            SearchResponse object or Generator for streaming
        
        Raises:
            InvalidParameterError: Invalid parameters
            AuthenticationError: Authentication failed
            RateLimitError: Rate limit exceeded
            NetworkError: Network/connection error
        """
        
        # Convert string enums to proper types
        if isinstance(mode, str):
            mode = SearchMode(mode)
        if isinstance(model, str):
            model = AIModel(model)
        if sources and isinstance(sources[0], str):
            sources = [SourceType(s) for s in sources]
        
        # Validate parameters
        self._validate_search_params(mode, model)
        
        # Build configuration
        config = SearchConfig(
            query=query,
            mode=mode,
            model=model,
            sources=sources or [SourceType.WEB],
            language=language,
            stream=stream,
            incognito=incognito,
            files=files,
            **kwargs
        )
        
        # Add conversation context if enabled
        if use_conversation and self.current_conversation:
            config.follow_up_context = {
                'conversation_id': self.current_conversation.conversation_id,
                'context': self.current_conversation.get_context()
            }
        
        # Execute search
        try:
            if stream:
                return self._stream_search(config)
            else:
                return self._direct_search(config)
        except requests.exceptions.Timeout:
            raise NetworkError("Request timed out")
        except requests.exceptions.ConnectionError:
            raise NetworkError("Connection failed")
        except Exception as e:
            raise PerplexityException(f"Search failed: {str(e)}")
    
    def _validate_search_params(
        self,
        mode: SearchMode,
        model: Optional[AIModel]
    ) -> None:
        """Validate search parameters"""
        if not validate_model_compatibility(mode, model):
            raise InvalidParameterError(
                f"Model {model.value if model else 'None'} not compatible with mode {mode.value}"
            )
    
    def _build_search_payload(self, config: SearchConfig) -> Dict:
        """Build search payload for API request"""
        frontend_uuid = str(uuid.uuid4())
        frontend_context_uuid = str(uuid.uuid4())
        
        # Map mode to API format
        mode_map = {
            SearchMode.AUTO: "concise",
            SearchMode.PRO: "copilot",
            SearchMode.REASONING: "reasoning",
            SearchMode.DEEP_RESEARCH: "research"
        }
        api_mode = mode_map.get(config.mode, "concise")
        
        return {
            "params": {
                "attachments": [],
                "language": config.language,
                "timezone": "UTC",
                "search_focus": "internet",
                "sources": [s.value for s in (config.sources or [SourceType.WEB])],
                "search_recency_filter": None,
                "frontend_uuid": frontend_uuid,
                "mode": api_mode,
                "model_preference": config.model.value if config.model else "turbo",
                "is_related_query": False,
                "is_sponsored": False,
                "frontend_context_uuid": frontend_context_uuid,
                "prompt_source": "user",
                "query_source": "home",
                "query_str": config.query
            },
            "query": config.query,
            "query_str": config.query,
            "user_identity": {
                "lang": config.language,
                "country": "US",
                "ab_active_tests": []
            }
        }
    
    def _direct_search(self, config: SearchConfig) -> SearchResponse:
        """Execute direct (non-streaming) search using SSE endpoint"""
        payload = self._build_search_payload(config)
        
        for attempt in range(self.max_retries):
            try:
                # SSE endpoint requires streaming even for non-streaming requests
                response = self.session.post(
                    f"{self.base_url}/rest/sse/perplexity_ask",
                    json=payload,
                    stream=True,  # SSE requires streaming
                    timeout=self.timeout * 2
                )
                
                if response.status_code != 200:
                    self._handle_error_response(response)
                
                # Read SSE stream and accumulate complete response
                accumulated_data = {}
                all_chunks = []
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8', errors='ignore')
                        if line_str.startswith('data: '):
                            try:
                                chunk = json.loads(line_str[6:])  # Remove 'data: ' prefix
                                
                                # Handle array format (new API format)
                                if isinstance(chunk, list):
                                    all_chunks.extend(chunk)
                                    # Extract answer from the last chunk that has answer content
                                    for item in chunk:
                                        if isinstance(item, dict):
                                            if 'content' in item:
                                                content = item['content']
                                                if isinstance(content, dict):
                                                    # Look for answer text in various fields
                                                    if 'text' in content:
                                                        accumulated_data['text'] = content['text']
                                                    elif 'answer' in content:
                                                        # Answer field might be a JSON string that needs parsing
                                                        answer_val = content['answer']
                                                        if isinstance(answer_val, str):
                                                            try:
                                                                # Try to parse as JSON
                                                                answer_obj = json.loads(answer_val)
                                                                if isinstance(answer_obj, dict) and 'answer' in answer_obj:
                                                                    accumulated_data['text'] = answer_obj['answer']
                                                                else:
                                                                    accumulated_data['text'] = answer_val
                                                            except json.JSONDecodeError:
                                                                # Not JSON, use as-is
                                                                accumulated_data['text'] = answer_val
                                                        else:
                                                            accumulated_data['text'] = str(answer_val)
                                                    elif 'chunks' in content and isinstance(content['chunks'], list):
                                                        # Extract from chunks array (new format)
                                                        answer_parts = []
                                                        for part in content['chunks']:
                                                            if isinstance(part, str):
                                                                answer_parts.append(part)
                                                        if answer_parts:
                                                            accumulated_data['text'] = ''.join(answer_parts)  # Join without spaces
                                                    elif 'structured_answer' in content and content['structured_answer']:
                                                        # Extract from structured_answer array
                                                        if isinstance(content['structured_answer'], list):
                                                            answer_parts = []
                                                            for part in content['structured_answer']:
                                                                if isinstance(part, str):
                                                                    answer_parts.append(part)
                                                                elif isinstance(part, dict) and 'text' in part:
                                                                    answer_parts.append(part['text'])
                                                            accumulated_data['text'] = ' '.join(answer_parts)
                                else:
                                    # Old format - single object
                                    # Check if it's a dict with step_type (might be a single chunk)
                                    if isinstance(chunk, dict):
                                        # If it has step_type, treat it as a chunk
                                        if 'step_type' in chunk:
                                            all_chunks.append(chunk)
                                        # Update accumulated data
                                        accumulated_data.update(chunk)
                                    else:
                                        accumulated_data.update(chunk)
                            except json.JSONDecodeError:
                                continue
                
                # If we collected chunks but no answer yet, try to extract from all chunks
                # Also check if we stored it in 'answer' instead of 'text'
                if accumulated_data.get('answer') and not accumulated_data.get('text'):
                    answer_val = accumulated_data['answer']
                    if isinstance(answer_val, str):
                        try:
                            answer_obj = json.loads(answer_val)
                            if isinstance(answer_obj, dict) and 'answer' in answer_obj:
                                accumulated_data['text'] = answer_obj['answer']
                            else:
                                accumulated_data['text'] = answer_val
                        except json.JSONDecodeError:
                            accumulated_data['text'] = answer_val
                    else:
                        accumulated_data['text'] = str(answer_val)
                
                if all_chunks and not accumulated_data.get('text'):
                    # Look through all chunks for answer content
                    for chunk in reversed(all_chunks):  # Start from end (most recent)
                        if isinstance(chunk, dict):
                            # Check for FINAL step_type first (most reliable)
                            if chunk.get('step_type') == 'FINAL' and 'content' in chunk:
                                content = chunk['content']
                                if isinstance(content, dict) and 'answer' in content:
                                    answer_str = content['answer']
                                    # Answer is a JSON string, parse it
                                    if isinstance(answer_str, str):
                                        try:
                                            answer_obj = json.loads(answer_str)
                                            if isinstance(answer_obj, dict) and 'answer' in answer_obj:
                                                accumulated_data['text'] = answer_obj['answer']
                                                break  # Found answer, stop looking
                                        except json.JSONDecodeError:
                                            accumulated_data['text'] = answer_str
                                            break
                            elif 'content' in chunk:
                                content = chunk['content']
                                if isinstance(content, dict):
                                    # Check for chunks array (new format)
                                    if 'chunks' in content and isinstance(content['chunks'], list):
                                        answer_parts = []
                                        for part in content['chunks']:
                                            if isinstance(part, str):
                                                answer_parts.append(part)
                                        if answer_parts:
                                            accumulated_data['text'] = ''.join(answer_parts)  # Join without spaces
                                            break
                                    # Check structured_answer
                                    elif 'structured_answer' in content and content['structured_answer']:
                                        if isinstance(content['structured_answer'], list) and len(content['structured_answer']) > 0:
                                            # Extract text from structured_answer
                                            answer_parts = []
                                            for part in content['structured_answer']:
                                                if isinstance(part, str):
                                                    answer_parts.append(part)
                                                elif isinstance(part, dict):
                                                    if 'text' in part:
                                                        answer_parts.append(part['text'])
                                                    elif isinstance(part.get('content'), str):
                                                        answer_parts.append(part['content'])
                                            if answer_parts:
                                                accumulated_data['text'] = ' '.join(answer_parts)
                                                break
                
                # Store all chunks for debugging
                accumulated_data['_all_chunks'] = all_chunks
                
                return self._parse_response(accumulated_data, config.query)
                
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise NetworkError(f"Max retries exceeded: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def _stream_search(self, config: SearchConfig) -> Generator[Dict, None, None]:
        """Execute streaming search using SSE endpoint"""
        payload = self._build_search_payload(config)
        
        response = self.session.post(
            f"{self.base_url}/rest/sse/perplexity_ask",
            json=payload,
            stream=True,
            timeout=self.timeout * 2  # Longer timeout for streaming
        )
        
        if response.status_code != 200:
            self._handle_error_response(response)
        
        # Stream SSE chunks
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8', errors='ignore')
                if line_str.startswith('data: '):
                    try:
                        chunk = json.loads(line_str[6:])  # Remove 'data: ' prefix
                        yield chunk
                    except json.JSONDecodeError:
                        continue
    
    def _handle_response(self, response: requests.Response, query: str, data: Optional[Dict] = None) -> SearchResponse:
        """Handle API response"""
        if data is not None:
            return self._parse_response(data, query)
        
        if response.status_code == 200:
            try:
                data = response.json()
                return self._parse_response(data, query)
            except json.JSONDecodeError:
                # If not JSON, might be SSE - this shouldn't happen here
                raise NetworkError("Unexpected response format")
        else:
            self._handle_error_response(response)
    
    def _handle_error_response(self, response: requests.Response) -> None:
        """Handle error responses"""
        # Check for Cloudflare challenge
        if response.status_code == 403:
            response_text_lower = response.text.lower()
            if ('cloudflare' in response_text_lower or 
                'just a moment' in response_text_lower or
                'challenge' in response_text_lower):
                # If cloudscraper is enabled, it should have handled this
                # If we still get here, cloudscraper may have failed
                if self.use_cloudflare_bypass:
                    raise NetworkError(
                        "Cloudflare protection detected despite cloudscraper bypass.\n\n"
                        "This may indicate:\n"
                        "  1. Cloudflare challenge is too complex\n"
                        "  2. IP address is blocked\n"
                        "  3. Cloudflare protection has been updated\n\n"
                        "RECOMMENDED SOLUTION:\n"
                        "  Use browser automation (works reliably):\n"
                        "    .\\perplexity.bat browser --persistent\n"
                        "    Or: .\\perplexity.bat browser --profile my_account\n\n"
                        "ALTERNATIVE:\n"
                        "  Try with proxy rotation or disable cloudflare bypass:\n"
                        "    perplexity search \"query\" --no-cloudflare-bypass\n\n"
                        "See API_STATUS.md for more details.\n"
                    )
                else:
                    raise NetworkError(
                        "Cloudflare protection detected - API endpoint blocked.\n\n"
                        "Direct API calls are unreliable due to Cloudflare's advanced bot detection.\n"
                        "Even with valid cookies, Cloudflare checks browser fingerprints and behavioral patterns.\n\n"
                        "RECOMMENDED SOLUTION:\n"
                        "  Enable cloudflare bypass (default):\n"
                        "    perplexity search \"query\"  # Uses cloudscraper automatically\n"
                        "  Or use browser automation:\n"
                        "    .\\perplexity.bat browser --persistent\n\n"
                        "See API_STATUS.md for more details on Cloudflare protection.\n"
                    )
        
        if response.status_code == 401:
            raise AuthenticationError("Authentication failed - invalid cookies")
        elif response.status_code == 429:
            raise RateLimitError("Rate limit exceeded - too many requests")
        elif response.status_code == 400:
            raise InvalidParameterError(f"Invalid request: {response.text}")
        else:
            raise PerplexityException(
                f"Request failed: {response.status_code} - {response.text[:500]}"
            )
    
    def _parse_response(self, data: Dict, query: str) -> SearchResponse:
        """Parse API response into SearchResponse object (SSE format)"""
        # SSE response structure from Perplexity:
        # - answer text might be in "text" or accumulated chunks
        # - citations in "citations" array or citation objects
        # - sources from citations
        
        # Extract answer text (could be in multiple fields)
        # IMPORTANT: Check _all_chunks FIRST (new format) before checking data fields
        # because data might have raw JSON strings that we don't want
        answer = ''
        
        # Check _all_chunks first (new format) - this is the most reliable
        if '_all_chunks' in data:
            all_chunks = data['_all_chunks']
            for chunk in reversed(all_chunks):  # Start from end (most recent)
                if isinstance(chunk, dict):
                    # Check for FINAL step_type with answer field (most reliable)
                    if chunk.get('step_type') == 'FINAL' and 'content' in chunk:
                        content = chunk['content']
                        if isinstance(content, dict) and 'answer' in content:
                            answer_str = content['answer']
                            # Answer might be a JSON string, try to parse it
                            if isinstance(answer_str, str):
                                try:
                                    answer_obj = json.loads(answer_str)
                                    if isinstance(answer_obj, dict):
                                        # Try 'answer' field first
                                        if 'answer' in answer_obj:
                                            answer = answer_obj['answer']
                                            break
                                        # Fall back to 'text' or other fields
                                        elif 'text' in answer_obj:
                                            answer = answer_obj['text']
                                            break
                                except json.JSONDecodeError:
                                    # Not JSON, use as-is
                                    answer = answer_str
                                    break
                            elif isinstance(answer_str, dict):
                                # Already a dict
                                if 'answer' in answer_str:
                                    answer = answer_str['answer']
                                    break
                                elif 'text' in answer_str:
                                    answer = answer_str['text']
                                    break
                    
                    # Check content for chunks array
                    if 'content' in chunk:
                        content = chunk['content']
                        if isinstance(content, dict):
                            # Check for chunks array
                            if 'chunks' in content and isinstance(content['chunks'], list):
                                answer_parts = []
                                for part in content['chunks']:
                                    if isinstance(part, str):
                                        answer_parts.append(part)
                                if answer_parts:
                                    answer = ''.join(answer_parts)
                                    break
                            # Check for answer field (direct)
                            if 'answer' in content:
                                answer_val = content['answer']
                                if isinstance(answer_val, str):
                                    try:
                                        answer_obj = json.loads(answer_val)
                                        if isinstance(answer_obj, dict) and 'answer' in answer_obj:
                                            answer = answer_obj['answer']
                                            break
                                    except:
                                        pass
                                elif isinstance(answer_val, dict) and 'answer' in answer_val:
                                    answer = answer_val['answer']
                                    break
        
        # Fallback to old format fields (only if not a JSON string)
        if not answer:
            # Check text field - might be a JSON array string that needs parsing
            if 'text' in data and isinstance(data['text'], str):
                text_val = data['text']
                # If it looks like a JSON array, try to parse it and extract chunks
                if text_val.strip().startswith('['):
                    try:
                        parsed_chunks = json.loads(text_val)
                        if isinstance(parsed_chunks, list):
                            # Add to all_chunks if not already there
                            if '_all_chunks' not in data or not data['_all_chunks']:
                                data['_all_chunks'] = parsed_chunks
                            # Try to extract answer from parsed chunks
                            for chunk in reversed(parsed_chunks):
                                if isinstance(chunk, dict) and chunk.get('step_type') == 'FINAL':
                                    content = chunk.get('content', {})
                                    if isinstance(content, dict) and 'answer' in content:
                                        answer_str = content['answer']
                                        if isinstance(answer_str, str):
                                            try:
                                                answer_obj = json.loads(answer_str)
                                                if isinstance(answer_obj, dict) and 'answer' in answer_obj:
                                                    answer = answer_obj['answer']
                                                    break
                                            except:
                                                pass
                    except json.JSONDecodeError:
                        pass
                # Don't use if it looks like JSON object (but not array)
                elif not text_val.strip().startswith('{'):
                    answer = text_val
            
            # Check answer field (but be careful - might be JSON string)
            if not answer and 'answer' in data:
                answer_val = data['answer']
                if isinstance(answer_val, str):
                    # Don't use if it looks like JSON array/object
                    if not (answer_val.strip().startswith('[') or answer_val.strip().startswith('{')):
                        answer = answer_val
                elif isinstance(answer_val, dict) and 'answer' in answer_val:
                    answer = answer_val['answer']
            
            # Check response field
            if not answer and 'response' in data:
                response_val = data['response']
                if isinstance(response_val, dict):
                    answer = response_val.get('text', '')
                else:
                    answer = str(response_val) if not (str(response_val).strip().startswith('[') or str(response_val).strip().startswith('{')) else ''
        
        # Extract sources/citations
        sources = []
        citations = data.get('citations', []) or data.get('citation', [])
        
        # Also extract from _all_chunks if available (new format)
        if '_all_chunks' in data:
            all_chunks = data['_all_chunks']
            for chunk in all_chunks:
                if isinstance(chunk, dict) and chunk.get('step_type') == 'SEARCH_RESULTS':
                    content = chunk.get('content', {})
                    if isinstance(content, dict):
                        # Extract web_results
                        web_results = content.get('web_results', [])
                        for result in web_results:
                            if isinstance(result, dict):
                                sources.append({
                                    'title': result.get('name', result.get('title', '')),
                                    'url': result.get('url', ''),
                                    'snippet': result.get('snippet', ''),
                                    'citation': result.get('name', '')
                                })
        
        # Handle different citation formats
        if citations:
            for citation in citations:
                if isinstance(citation, dict):
                    sources.append({
                        'title': citation.get('title', citation.get('name', '')),
                        'url': citation.get('url', citation.get('link', '')),
                        'citation': citation.get('citation', ''),
                        'citation_number': citation.get('number')
                    })
                elif isinstance(citation, str):
                    # Sometimes citations are just URLs
                    sources.append({
                        'url': citation,
                        'title': ''
                    })
        
        # Extract related questions if available
        related_questions = data.get('related_questions', []) or data.get('related', [])
        
        # Extract mode (map back from API format)
        api_mode = data.get('mode', 'COPILOT')
        mode_map = {
            'COPILOT': 'pro',
            'concise': 'auto',
            'reasoning': 'reasoning',
            'research': 'deep_research'
        }
        mode = mode_map.get(api_mode, 'auto')
        
        # Extract model
        model = data.get('display_model') or data.get('model_preference') or data.get('model')
        
        # Extract conversation IDs
        conversation_id = data.get('uuid') or data.get('context_uuid') or data.get('frontend_context_uuid')
        
        response = SearchResponse(
            query=query,
            answer=answer,
            sources=sources,
            related_questions=related_questions,
            mode=mode,
            model=model,
            conversation_id=conversation_id,
            tokens_used=data.get('tokens_used'),
            raw_response=data
        )
        
        # Update conversation if exists
        if self.current_conversation and response.conversation_id:
            self.current_conversation.add_message('user', query)
            self.current_conversation.add_message('assistant', response.answer, response.sources)
        
        return response
    
    def start_conversation(self) -> str:
        """Start a new conversation thread"""
        conversation_id = str(uuid.uuid4())
        self.current_conversation = Conversation(conversation_id=conversation_id)
        self.conversations[conversation_id] = self.current_conversation
        return conversation_id
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        return self.conversations.get(conversation_id)
    
    def set_conversation(self, conversation_id: str) -> bool:
        """Set active conversation"""
        if conversation_id in self.conversations:
            self.current_conversation = self.conversations[conversation_id]
            return True
        return False
    
    def clear_conversation(self) -> None:
        """Clear current conversation"""
        self.current_conversation = None
    
    def export_conversation(
        self,
        conversation_id: Optional[str] = None,
        format: str = 'json'
    ) -> str:
        """
        Export conversation in specified format
        
        Args:
            conversation_id: ID of conversation to export (current if None)
            format: Export format ('json', 'text', 'markdown')
        
        Returns:
            Formatted conversation string
        """
        conv = self.conversations.get(conversation_id) if conversation_id else self.current_conversation
        
        if not conv:
            return ""
        
        if format == 'json':
            return json.dumps({
                'conversation_id': conv.conversation_id,
                'created_at': conv.created_at.isoformat(),
                'messages': [
                    {
                        'role': msg.role,
                        'content': msg.content,
                        'timestamp': msg.timestamp.isoformat(),
                        'sources': msg.sources
                    }
                    for msg in conv.messages
                ]
            }, indent=2)
        
        elif format == 'text':
            lines = []
            for msg in conv.messages:
                prefix = "Q:" if msg.role == 'user' else "A:"
                lines.append(f"{prefix} {msg.content}\n")
            return '\n'.join(lines)
        
        elif format == 'markdown':
            lines = [f"# Conversation: {conv.conversation_id}\n"]
            for msg in conv.messages:
                if msg.role == 'user':
                    lines.append(f"## Question\n{msg.content}\n")
                else:
                    lines.append(f"## Answer\n{msg.content}\n")
                    if msg.sources:
                        lines.append("### Sources")
                        for idx, src in enumerate(msg.sources, 1):
                            lines.append(f"{idx}. [{src.get('title', 'Source')}]({src.get('url', '#')})")
                        lines.append("")
            return '\n'.join(lines)
        
        return ""
    
    def get_cookies(self) -> Dict[str, str]:
        """Get current session cookies"""
        return dict(self.session.cookies)
    
    def set_cookies(self, cookies: Dict[str, str]) -> None:
        """Update session cookies"""
        self.session.cookies.update(cookies)
    
    def close(self) -> None:
        """Close session and cleanup"""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def create_labs_project(
        self,
        query: str,
        project_type: str = "document",
        **kwargs
    ) -> SearchResponse:
        """
        Create a Labs project (document, slides, dashboard, etc.)
        
        Args:
            query: Project description/idea
            project_type: Type of project (document, slides, dashboard, etc.)
            **kwargs: Additional parameters
        
        Returns:
            SearchResponse with project content
        
        Note:
            Labs API endpoint needs to be discovered. Until then, use browser automation:
            from automation.web_driver import PerplexityWebDriver
            driver = PerplexityWebDriver()
            driver.start()
            driver.navigate_to_perplexity()
            # Use browser UI to create Labs project
        """
        # Check if response is Cloudflare challenge
        def is_cloudflare_challenge(response):
            return (
                response.status_code == 403 and 
                ('cloudflare' in response.text.lower() or 
                 'just a moment' in response.text.lower() or
                 'challenge' in response.text.lower())
            )
        
        payload = {
            "query": query,
            "type": project_type,
            "mode": "labs",
            **kwargs
        }
        
        # Note: This endpoint needs to be discovered and updated
        # Run: python discover_endpoints.py to find the actual Labs endpoint
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    f"{self.base_url}/api/labs/create",  # Placeholder - needs discovery
                    json=payload,
                    timeout=self.timeout
                )
                
                # Check for Cloudflare challenge
                if is_cloudflare_challenge(response):
                    raise NetworkError(
                        "Labs API endpoint blocked by Cloudflare or endpoint not found.\n"
                        "The Labs endpoint needs to be discovered via network inspection.\n"
                        "Run: python discover_endpoints.py\n\n"
                        "Alternatively, use browser automation for Labs:\n"
                        "  from automation.web_driver import PerplexityWebDriver\n"
                        "  driver = PerplexityWebDriver()\n"
                        "  driver.start()\n"
                        "  driver.navigate_to_perplexity()\n"
                        "  # Create Labs project via browser UI"
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_response(data, query)
                else:
                    self._handle_error_response(response)
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise NetworkError(f"Labs project creation failed: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff