"""
Perplexity AI Wrapper - Updated Data Models and Enums
Updated based on UI screenshots (2025-11-13)

File: src/core/models_updated.py
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


class SearchMode(Enum):
    """Available search modes in Perplexity"""
    AUTO = "auto"
    PRO = "pro"
    REASONING = "reasoning"
    DEEP_RESEARCH = "deep_research"


class AIModel(Enum):
    """
    Available AI models - UPDATED 2025-11-13
    Based on actual Perplexity UI
    """
    # Standard models
    BEST = "best"                          # Auto-select best model
    SONAR = "sonar"                        # Perplexity's model
    GPT_5 = "gpt-5"                        # OpenAI GPT-5
    CLAUDE_SONNET_4_5 = "claude-sonnet-4.5"  # Anthropic Claude Sonnet 4.5
    GEMINI_2_5_PRO = "gemini-2.5-pro"      # Google Gemini 2.5 Pro
    GROK_4 = "grok-4"                      # xAI Grok 4
    
    # Max-tier models (premium)
    CLAUDE_OPUS_4_1 = "claude-opus-4.1"    # Anthropic Claude Opus 4.1 (max)
    O3_PRO = "o3-pro"                      # OpenAI o3-pro (max)
    
    # Legacy/backward compatibility
    GPT_4O = "gpt-4o"                      # Old: GPT-4o
    GPT_4_5 = "gpt-4.5"                    # Old: GPT-4.5
    CLAUDE_3_7_SONNET = "claude-3.7-sonnet"  # Old: Claude 3.7


class SourceType(Enum):
    """
    Available source types - UPDATED 2025-11-13
    Based on actual Perplexity UI
    """
    WEB = "web"                            # Search across entire Internet
    ACADEMIC = "academic"                  # Search academic papers (was "scholar")
    SOCIAL = "social"                      # Discussions and opinions
    FINANCE = "finance"                    # Search SEC filings
    
    # Additional connectors (premium integrations)
    GMAIL_CALENDAR = "gmail-calendar"      # Gmail with Calendar integration
    WILEY = "wiley"                        # Wiley publications
    CB_INSIGHTS = "cb-insights"            # CB Insights data
    
    # Legacy/backward compatibility
    SCHOLAR = "academic"                   # Alias for ACADEMIC
    REDDIT = "social"                      # Included in SOCIAL
    YOUTUBE = "web"                        # Included in WEB


class ResponseFormat(Enum):
    """Response format types"""
    JSON = "json"
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"


@dataclass
class SearchConfig:
    """Configuration for a search request"""
    query: str
    mode: SearchMode = SearchMode.AUTO
    model: Optional[AIModel] = None
    sources: List[SourceType] = field(default_factory=lambda: [SourceType.WEB])
    language: str = "en-US"
    stream: bool = False
    incognito: bool = False
    follow_up_context: Optional[Dict[str, Any]] = None
    files: Optional[Dict[str, str]] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    with_reasoning: bool = False  # NEW: Enable reasoning mode toggle
    
    def to_payload(self) -> Dict[str, Any]:
        """Convert to API payload"""
        payload = {
            "query": self.query,
            "mode": self.mode.value,
            "language": self.language,
            "incognito": self.incognito,
            "sources": [s.value for s in self.sources]
        }
        
        if self.model:
            payload["model"] = self.model.value
        
        if self.with_reasoning:
            payload["reasoning"] = True
        
        if self.files:
            payload["files"] = self.files
        
        if self.follow_up_context:
            payload["follow_up"] = self.follow_up_context
        
        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens
        
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        
        return payload


@dataclass
class SearchResponse:
    """Structured search response"""
    query: str
    answer: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    related_questions: List[str] = field(default_factory=list)
    mode: str = "auto"
    model: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    conversation_id: Optional[str] = None
    tokens_used: Optional[int] = None
    raw_response: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "query": self.query,
            "answer": self.answer,
            "sources": self.sources,
            "related_questions": self.related_questions,
            "mode": self.mode,
            "model": self.model,
            "timestamp": self.timestamp.isoformat(),
            "conversation_id": self.conversation_id,
            "tokens_used": self.tokens_used
        }
    
    def to_markdown(self) -> str:
        """Convert to markdown format"""
        md = f"# Query: {self.query}\n\n"
        md += f"## Answer\n{self.answer}\n\n"
        
        if self.sources:
            md += "## Sources\n"
            for idx, source in enumerate(self.sources, 1):
                md += f"{idx}. [{source.get('title', 'Source')}]({source.get('url', '#')})\n"
            md += "\n"
        
        if self.related_questions:
            md += "## Related Questions\n"
            for q in self.related_questions:
                md += f"- {q}\n"
        
        return md


@dataclass
class AccountCredentials:
    """Account credentials"""
    email: str
    cookies: Dict[str, str]
    session_token: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "email": self.email,
            "cookies": self.cookies,
            "session_token": self.session_token,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "metadata": self.metadata
        }


@dataclass
class ConversationMessage:
    """Single conversation message"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """Conversation thread"""
    conversation_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, sources: List[Dict] = None):
        """Add message to conversation"""
        message = ConversationMessage(
            role=role,
            content=content,
            sources=sources or []
        )
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_context(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation context"""
        recent = self.messages[-max_messages:]
        return [
            {"role": msg.role, "content": msg.content}
            for msg in recent
        ]


# Model validation mappings - UPDATED
MODEL_COMPATIBILITY = {
    SearchMode.AUTO: [
        None,
        AIModel.BEST,
        AIModel.SONAR,
        AIModel.GPT_5,
        AIModel.CLAUDE_SONNET_4_5,
        AIModel.GEMINI_2_5_PRO,
        AIModel.GROK_4,
        AIModel.CLAUDE_OPUS_4_1,
        AIModel.O3_PRO
    ],
    SearchMode.PRO: [
        None,
        AIModel.BEST,
        AIModel.SONAR,
        AIModel.GPT_5,
        AIModel.CLAUDE_SONNET_4_5,
        AIModel.GEMINI_2_5_PRO,
        AIModel.GROK_4,
        AIModel.CLAUDE_OPUS_4_1,
        AIModel.O3_PRO
    ],
    SearchMode.REASONING: [
        None,
        AIModel.CLAUDE_SONNET_4_5,  # With reasoning toggle
        AIModel.CLAUDE_OPUS_4_1,
        AIModel.O3_PRO
    ],
    SearchMode.DEEP_RESEARCH: [None]
}


def validate_model_compatibility(mode: SearchMode, model: Optional[AIModel]) -> bool:
    """Validate if model is compatible with search mode"""
    if model is None:
        return True
    return model in MODEL_COMPATIBILITY.get(mode, [])


class PerplexityException(Exception):
    """Base exception for Perplexity wrapper"""
    pass


class AuthenticationError(PerplexityException):
    """Authentication related errors"""
    pass


class RateLimitError(PerplexityException):
    """Rate limiting errors"""
    pass


class InvalidParameterError(PerplexityException):
    """Invalid parameter errors"""
    pass


class NetworkError(PerplexityException):
    """Network related errors"""
    pass


# Model tier information (for UI display)
MODEL_TIERS = {
    AIModel.BEST: "auto",
    AIModel.SONAR: "standard",
    AIModel.GPT_5: "standard",
    AIModel.CLAUDE_SONNET_4_5: "standard",
    AIModel.GEMINI_2_5_PRO: "standard",
    AIModel.GROK_4: "standard",
    AIModel.CLAUDE_OPUS_4_1: "max",     # Premium tier
    AIModel.O3_PRO: "max",              # Premium tier
}


# Source descriptions (for documentation)
SOURCE_DESCRIPTIONS = {
    SourceType.WEB: "Search across the entire Internet",
    SourceType.ACADEMIC: "Search academic papers and research",
    SourceType.SOCIAL: "Discussions and opinions from social platforms",
    SourceType.FINANCE: "Search SEC filings and financial documents",
    SourceType.GMAIL_CALENDAR: "Gmail with Calendar integration (requires connection)",
    SourceType.WILEY: "Wiley publications (requires connection)",
    SourceType.CB_INSIGHTS: "CB Insights data (requires connection)",
}
