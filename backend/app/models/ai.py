from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from app.database import Base

class AIProvider(Base):
    __tablename__ = "ai_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # OpenAI, Azure, Ollama, etc.
    provider_type = Column(String(50), nullable=False)  # openai, azure, ollama, lmstudio, anthropic, openrouter
    api_key = Column(String(500), nullable=True)  # Encrypted in real app
    base_url = Column(String(500), nullable=True)
    model = Column(String(100), nullable=True)
    is_default = Column(Boolean, default=False)
    is_enabled = Column(Boolean, default=True)
    config = Column(JSON, default=dict)  # Extra params like temperature, max_tokens
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
