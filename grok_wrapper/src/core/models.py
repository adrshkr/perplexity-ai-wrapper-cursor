"""
Grok Chat API Wrapper - Data Models
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


class GrokModel(Enum):
    """Available Grok models"""
    GROK_4 = "grok-4"
    GROK_2 = "grok-2"
    GROK_BETA = "grok-beta"


class ModelMode(Enum):
    """Model mode options"""
    EXPERT = "MODEL_MODE_EXPERT"
    BALANCED = "MODEL_MODE_BALANCED"
    FUN = "MODEL_MODE_FUN"


@dataclass
class ChatRequest:
    """Request model for Grok chat"""
    message: str
    model_name: str = "grok-4"
    temporary: bool = False
    file_attachments: List[Dict[str, Any]] = field(default_factory=list)
    image_attachments: List[Dict[str, Any]] = field(default_factory=list)
    disable_search: bool = False
    enable_image_generation: bool = True
    return_image_bytes: bool = False
    return_raw_grok_in_xai_request: bool = False
    enable_image_streaming: bool = True
    image_generation_count: int = 2
    force_concise: bool = False
    tool_overrides: Dict[str, Any] = field(default_factory=dict)
    enable_side_by_side: bool = True
    send_final_metadata: bool = True
    is_reasoning: bool = False
    disable_text_follow_ups: bool = False
    disable_memory: bool = False
    force_side_by_side: bool = False
    model_mode: str = "MODEL_MODE_EXPERT"
    is_async_chat: bool = False
    disable_self_harm_short_circuit: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API request payload"""
        return {
            "temporary": self.temporary,
            "modelName": self.model_name,
            "message": self.message,
            "fileAttachments": self.file_attachments,
            "imageAttachments": self.image_attachments,
            "disableSearch": self.disable_search,
            "enableImageGeneration": self.enable_image_generation,
            "returnImageBytes": self.return_image_bytes,
            "returnRawGrokInXaiRequest": self.return_raw_grok_in_xai_request,
            "enableImageStreaming": self.enable_image_streaming,
            "imageGenerationCount": self.image_generation_count,
            "forceConcise": self.force_concise,
            "toolOverrides": self.tool_overrides,
            "enableSideBySide": self.enable_side_by_side,
            "sendFinalMetadata": self.send_final_metadata,
            "isReasoning": self.is_reasoning,
            "disableTextFollowUps": self.disable_text_follow_ups,
            "responseMetadata": {
                "modelConfigOverride": {
                    "modelMap": {}
                },
                "requestModelDetails": {
                    "modelId": self.model_name
                }
            },
            "disableMemory": self.disable_memory,
            "forceSideBySide": self.force_side_by_side,
            "modelMode": self.model_mode,
            "isAsyncChat": self.is_async_chat,
            "disableSelfHarmShortCircuit": self.disable_self_harm_short_circuit
        }


@dataclass
class StreamingToken:
    """Single streaming token from Grok API"""
    token: Optional[str] = None
    is_thinking: bool = False
    is_soft_stop: bool = False
    response_id: Optional[str] = None
    message_tag: Optional[str] = None
    message_step_id: Optional[int] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> Optional['StreamingToken']:
        """Parse streaming token from JSON response"""
        if "result" not in data or "response" not in data["result"]:
            return None
        
        response = data["result"]["response"]
        token = cls(
            token=response.get("token"),
            is_thinking=response.get("isThinking", False),
            is_soft_stop=response.get("isSoftStop", False),
            response_id=response.get("responseId"),
            message_tag=response.get("messageTag"),
            message_step_id=response.get("messageStepId"),
            raw_data=response
        )
        return token


@dataclass
class ChatResponse:
    """Complete chat response from Grok"""
    message: str
    conversation_id: Optional[str] = None
    response_id: Optional[str] = None
    model: Optional[str] = None
    thinking_trace: Optional[str] = None
    sources: List[Dict[str, Any]] = field(default_factory=list)
    follow_up_suggestions: List[Dict[str, Any]] = field(default_factory=list)
    raw_response: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_final_metadata(cls, metadata: Dict[str, Any], message: str, 
                          conversation_id: Optional[str] = None,
                          response_id: Optional[str] = None,
                          model: Optional[str] = None) -> 'ChatResponse':
        """Create response from final metadata"""
        return cls(
            message=message,
            conversation_id=conversation_id,
            response_id=response_id,
            model=model,
            follow_up_suggestions=metadata.get("followUpSuggestions", []),
            raw_response=metadata
        )
    
    @classmethod
    def from_model_response(cls, model_response: Dict[str, Any], 
                          conversation_id: Optional[str] = None) -> 'ChatResponse':
        """Create response from model response object"""
        return cls(
            message=model_response.get("message", ""),
            conversation_id=conversation_id,
            response_id=model_response.get("responseId"),
            model=model_response.get("model"),
            thinking_trace=model_response.get("thinkingTrace"),
            sources=model_response.get("citedWebSearchResults", []),
            raw_response=model_response
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "message": self.message,
            "conversation_id": self.conversation_id,
            "response_id": self.response_id,
            "model": self.model,
            "thinking_trace": self.thinking_trace,
            "sources": self.sources,
            "follow_up_suggestions": self.follow_up_suggestions
        }
    
    def to_markdown(self) -> str:
        """Convert to markdown format"""
        md = f"# Grok Response\n\n{self.message}\n\n"
        
        if self.sources:
            md += "## Sources\n\n"
            for idx, source in enumerate(self.sources, 1):
                title = source.get("title", "N/A")
                url = source.get("url", "")
                md += f"{idx}. [{title}]({url})\n"
            md += "\n"
        
        if self.follow_up_suggestions:
            md += "## Follow-up Suggestions\n\n"
            for idx, suggestion in enumerate(self.follow_up_suggestions, 1):
                label = suggestion.get("label", "N/A")
                md += f"{idx}. {label}\n"
            md += "\n"
        
        return md


class GrokException(Exception):
    """Base exception for Grok API errors"""
    pass


class AuthenticationError(GrokException):
    """Authentication failed"""
    pass


class NetworkError(GrokException):
    """Network or connection error"""
    pass


class APIError(GrokException):
    """API returned an error"""
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

