"""
Grok Chat API Wrapper - Synchronous Client
"""
import json
import time
from typing import Any, Dict, List, Optional, Generator, Union
import requests
from .models import (
    ChatRequest, ChatResponse, StreamingToken,
    GrokException, AuthenticationError, NetworkError, APIError
)


class GrokClient:
    """
    Main synchronous client for Grok chat
    
    Usage:
        client = GrokClient(cookies={'session': 'your_token'})
        response = client.chat("Hello!")
        print(response.message)
    """
    
    def __init__(
        self,
        cookies: Optional[Dict[str, str]] = None,
        base_url: str = "https://grok.com",
        timeout: int = 120,
        max_retries: int = 3,
        user_agent: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize Grok client
        
        Args:
            cookies: Authentication cookies (dict of cookie name -> value)
            base_url: Base URL for Grok API
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            user_agent: Custom user agent string
            headers: Custom headers dictionary (will be merged with defaults)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        
        # Set default headers
        default_user_agent = (
            user_agent or 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        )
        
        default_headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "User-Agent": default_user_agent,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-full-version": '"140.0.7339.186"',
            "sec-ch-ua-full-version-list": '"Chromium";v="140.0.7339.186", "Not=A?Brand";v="24.0.0.0", "Google Chrome";v="140.0.7339.186"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-platform-version": '"19.0.0"',
        }
        
        # Merge custom headers if provided
        if headers:
            default_headers.update(headers)
        
        self.session.headers.update(default_headers)
        
        # Set cookies if provided
        if cookies:
            for name, value in cookies.items():
                self.session.cookies.set(name, value, domain='.grok.com')
    
    def get_cookies(self) -> Dict[str, str]:
        """Get current cookies as dictionary"""
        return dict(self.session.cookies)
    
    def set_cookies(self, cookies: Dict[str, str]):
        """Set cookies"""
        for name, value in cookies.items():
            self.session.cookies.set(name, value, domain='.grok.com')
    
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any
    ) -> requests.Response:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method,
                    url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # Handle authentication errors
                if response.status_code == 401:
                    raise AuthenticationError(
                        "Authentication failed. Please check your cookies."
                    )
                
                # Handle other errors
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                    except (ValueError, json.JSONDecodeError):
                        error_data = {"error": response.text}
                    
                    raise APIError(
                        f"API error: {response.status_code}",
                        status_code=response.status_code,
                        response=error_data
                    )
                
                return response
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise NetworkError(f"Network error after {self.max_retries} attempts: {str(e)}")
            except (AuthenticationError, APIError):
                # Don't retry authentication or API errors
                raise
        
        # This should never be reached, but included for type safety
        if last_exception:
            raise NetworkError(f"Max retries exceeded: {str(last_exception)}")
        raise NetworkError("Max retries exceeded")
    
    def chat(
        self,
        message: str,
        model_name: str = "grok-4",
        model_mode: Optional[str] = None,
        stream: bool = False,
        **kwargs: Any
    ) -> Union[ChatResponse, Generator[StreamingToken, None, None]]:
        """
        Send a chat message to Grok
        
        Args:
            message: The message to send
            model_name: Model to use (default: grok-4)
            model_mode: Model mode (MODEL_MODE_EXPERT, MODEL_MODE_BALANCED, MODEL_MODE_FUN)
            stream: Whether to stream the response
            **kwargs: Additional parameters for ChatRequest (e.g., temporary, disable_search, 
                     enable_image_generation, etc.)
        
        Returns:
            ChatResponse if stream=False, Generator[StreamingToken] if stream=True
        """
        # Set model_mode if provided
        if model_mode:
            kwargs['model_mode'] = model_mode
        
        request = ChatRequest(
            message=message,
            model_name=model_name,
            **kwargs
        )
        
        payload = request.to_dict()
        
        if stream:
            return self._chat_stream(payload)
        else:
            return self._chat_complete(payload)
    
    def _chat_stream(self, payload: Dict[str, Any]) -> Generator[StreamingToken, None, None]:
        """Stream chat response"""
        response = self._request("POST", "/rest/app-chat/conversations/new", json=payload, stream=True)
        
        # Parse streaming newline-delimited JSON
        for line in response.iter_lines():
            if not line:
                continue
            
            # Handle bytes
            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='ignore')
            
            try:
                data = json.loads(line)
                
                # Yield streaming token
                token = StreamingToken.from_json(data)
                if token:
                    yield token
                    
            except json.JSONDecodeError:
                continue
    
    def _chat_complete(self, payload: Dict[str, Any]) -> ChatResponse:
        """Get complete chat response (non-streaming)"""
        response = self._request("POST", "/rest/app-chat/conversations/new", json=payload, stream=True)
        
        conversation_id = None
        final_message = ""
        final_metadata = None
        model_response = None
        
        # Collect all streaming data
        for line in response.iter_lines():
            if not line:
                continue
            
            # Handle bytes
            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='ignore')
            
            try:
                data = json.loads(line)
                
                if "result" in data:
                    if "conversation" in data["result"]:
                        conversation_id = data["result"]["conversation"].get("conversationId")
                    
                    if "response" in data["result"]:
                        response_data = data["result"]["response"]
                        
                        # Collect tokens
                        token = response_data.get("token")
                        if token:
                            final_message += token
                        
                        # Check for final metadata
                        if "finalMetadata" in response_data:
                            final_metadata = response_data["finalMetadata"]
                        
                        # Check for model response
                        if "modelResponse" in response_data:
                            model_response = response_data["modelResponse"]
                    
            except json.JSONDecodeError:
                continue
        
        # Prefer model response if available
        if model_response:
            return ChatResponse.from_model_response(
                model_response,
                conversation_id=conversation_id
            )
        
        # Fallback to collected message
        return ChatResponse(
            message=final_message.strip(),
            conversation_id=conversation_id
        )

