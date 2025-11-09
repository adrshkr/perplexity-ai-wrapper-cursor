"""
Perplexity AI Wrapper - Asynchronous Client
File: src/core/async_client.py
"""
import aiohttp
import asyncio
import json
import uuid
from typing import Dict, List, Optional, AsyncGenerator, Union
from .models import (
    SearchMode, AIModel, SourceType, SearchConfig, SearchResponse,
    Conversation, validate_model_compatibility,
    PerplexityException, AuthenticationError, RateLimitError,
    InvalidParameterError, NetworkError
)

# Note: cloudscraper is synchronous, so for async client we extract cookies
# with cloudscraper and use them with aiohttp
try:
    from ..utils.cloudflare_bypass import CloudflareBypass
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False
    CloudflareBypass = None


class AsyncPerplexityClient:
    """
    Asynchronous client for Perplexity.ai
    
    Usage:
        async with AsyncPerplexityClient(cookies={'session': 'token'}) as client:
            response = await client.search("What is AI?")
            print(response.answer)
    """
    
    def __init__(
        self,
        cookies: Optional[Dict[str, str]] = None,
        base_url: str = "https://www.perplexity.ai",
        timeout: int = 30,
        max_retries: int = 3,
        user_agent: Optional[str] = None,
        connector: Optional[aiohttp.BaseConnector] = None,
        use_cloudflare_bypass: bool = True
    ):
        """
        Initialize async Perplexity client
        
        Args:
            cookies: Authentication cookies
            base_url: Base URL for Perplexity API
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            user_agent: Custom user agent string
            connector: Custom aiohttp connector
            use_cloudflare_bypass: Extract cookies with cloudscraper if not provided
        """
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.use_cloudflare_bypass = use_cloudflare_bypass and CLOUDSCRAPER_AVAILABLE
        
        # If no cookies provided and cloudscraper available, try to extract them
        if not cookies and self.use_cloudflare_bypass:
            try:
                bypass = CloudflareBypass(use_stealth=True, interpreter='js2py')
                if bypass.solve_challenge(base_url):
                    cookies = bypass.get_cookies_dict()
            except Exception:
                pass  # Fallback to no cookies
        self.cookies = cookies or {}
        self.connector = connector
        self.session: Optional[aiohttp.ClientSession] = None
        self.conversations: Dict[str, Conversation] = {}
        self.current_conversation: Optional[Conversation] = None
        
        # Headers
        self.headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/json',
            'Origin': 'https://www.perplexity.ai',
            'Referer': 'https://www.perplexity.ai/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure session is initialized"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                cookies=self.cookies,
                headers=self.headers,
                connector=self.connector,
                timeout=self.timeout
            )
    
    async def search(
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
    ) -> Union[SearchResponse, AsyncGenerator[Dict, None]]:
        """
        Execute search query asynchronously
        
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
            SearchResponse object or AsyncGenerator for streaming
        """
        await self._ensure_session()
        
        # Convert string enums
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
        
        # Add conversation context
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
                return await self._direct_search(config)
        except asyncio.TimeoutError:
            raise NetworkError("Request timed out")
        except aiohttp.ClientError as e:
            raise NetworkError(f"Connection error: {str(e)}")
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
    
    async def _direct_search(self, config: SearchConfig) -> SearchResponse:
        """Execute direct (non-streaming) search using SSE endpoint"""
        import uuid as uuid_module
        
        # Build payload according to discovered API format
        frontend_uuid = str(uuid_module.uuid4())
        frontend_context_uuid = str(uuid_module.uuid4())
        
        # Map mode to API format
        mode_map = {
            SearchMode.AUTO: "concise",
            SearchMode.PRO: "copilot",
            SearchMode.REASONING: "reasoning",
            SearchMode.DEEP_RESEARCH: "research"
        }
        api_mode = mode_map.get(config.mode, "concise")
        
        payload = {
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
                "query_source": "home"
            },
            "query": config.query,
            "user_identity": {
                "lang": config.language,
                "country": "US",
                "ab_active_tests": []
            }
        }
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.post(
                    f"{self.base_url}/rest/sse/perplexity_ask",
                    json=payload
                ) as response:
                    if response.status != 200:
                        await self._handle_error_response(response)
                    
                    # Read SSE stream and accumulate complete response
                    accumulated_data = {}
                    async for line in response.content:
                        if line:
                            line_str = line.decode('utf-8', errors='ignore')
                            if line_str.startswith('data: '):
                                try:
                                    chunk = json.loads(line_str[6:])  # Remove 'data: ' prefix
                                    accumulated_data.update(chunk)
                                except json.JSONDecodeError:
                                    continue
                    
                    return self._parse_response(accumulated_data, config.query)
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == self.max_retries - 1:
                    raise NetworkError(f"Max retries exceeded: {str(e)}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _stream_search(self, config: SearchConfig) -> AsyncGenerator[Dict, None]:
        """Execute streaming search using SSE endpoint"""
        import uuid as uuid_module
        
        # Build payload according to discovered API format
        frontend_uuid = str(uuid_module.uuid4())
        frontend_context_uuid = str(uuid_module.uuid4())
        
        # Map mode to API format
        mode_map = {
            SearchMode.AUTO: "concise",
            SearchMode.PRO: "copilot",
            SearchMode.REASONING: "reasoning",
            SearchMode.DEEP_RESEARCH: "research"
        }
        api_mode = mode_map.get(config.mode, "concise")
        
        payload = {
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
                "query_source": "home"
            },
            "query": config.query,
            "user_identity": {
                "lang": config.language,
                "country": "US",
                "ab_active_tests": []
            }
        }
        
        async with self.session.post(
            f"{self.base_url}/rest/sse/perplexity_ask",
            json=payload
        ) as response:
            
            if response.status != 200:
                await self._handle_error_response(response)
            
            # Stream SSE chunks
            async for line in response.content:
                if line:
                    line_str = line.decode('utf-8', errors='ignore')
                    if line_str.startswith('data: '):
                        try:
                            chunk = json.loads(line_str[6:])  # Remove 'data: ' prefix
                            yield chunk
                        except json.JSONDecodeError:
                            continue
    
    async def _handle_response(
        self,
        response: aiohttp.ClientResponse,
        query: str
    ) -> SearchResponse:
        """Handle API response"""
        if response.status == 200:
            data = await response.json()
            return self._parse_response(data, query)
        else:
            await self._handle_error_response(response)
    
    async def _handle_error_response(self, response: aiohttp.ClientResponse) -> None:
        """Handle error responses"""
        text = await response.text()
        
        if response.status == 401:
            raise AuthenticationError("Authentication failed - invalid cookies")
        elif response.status == 429:
            raise RateLimitError("Rate limit exceeded - too many requests")
        elif response.status == 400:
            raise InvalidParameterError(f"Invalid request: {text}")
        else:
            raise PerplexityException(f"Request failed: {response.status} - {text}")
    
    def _parse_response(self, data: Dict, query: str) -> SearchResponse:
        """Parse API response into SearchResponse object"""
        response = SearchResponse(
            query=query,
            answer=data.get('answer', ''),
            sources=data.get('sources', []),
            related_questions=data.get('related_questions', []),
            mode=data.get('mode', 'auto'),
            model=data.get('model'),
            conversation_id=data.get('conversation_id'),
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
    
    async def batch_search(
        self,
        queries: List[str],
        **search_kwargs
    ) -> List[SearchResponse]:
        """
        Execute multiple searches concurrently
        
        Args:
            queries: List of search queries
            **search_kwargs: Common search parameters
        
        Returns:
            List of SearchResponse objects
        """
        tasks = [self.search(query, **search_kwargs) for query in queries]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def close(self) -> None:
        """Close session and cleanup"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def get_cookies(self) -> Dict[str, str]:
        """Get current session cookies"""
        return self.cookies.copy()
    
    def set_cookies(self, cookies: Dict[str, str]) -> None:
        """Update session cookies"""
        self.cookies.update(cookies)