from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class AIProviderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider_type: str = Field(..., pattern="^(openai|azure|ollama|lmstudio|anthropic|openrouter|bedrock|kimi|google|claude)$")
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    is_default: bool = False
    is_enabled: bool = True
    config: Dict[str, Any] = {}

class AIProviderCreate(AIProviderBase):
    pass

class AIProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    is_default: Optional[bool] = None
    is_enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None

class AIProvider(AIProviderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AIRequest(BaseModel):
    provider_id: Optional[int] = None
    prompt: str
    context: Optional[str] = None
    max_tokens: Optional[int] = 500
    temperature: float = 0.3
    system_prompt: Optional[str] = None
    stream: bool = False

class AIResponse(BaseModel):
    content: str
    provider: str
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None

class AIChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str

class AIChatRequest(BaseModel):
    provider_id: Optional[int] = None
    project_id: Optional[int] = None
    messages: List[AIChatMessage]
    max_tokens: Optional[int] = 500
    temperature: float = 0.3
    stream: bool = False
