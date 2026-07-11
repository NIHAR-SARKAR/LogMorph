import asyncio
import time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.ai import AIProvider
from app.schemas.ai import AIRequest, AIResponse, AIChatRequest, AIChatMessage
from app.core.logging import logger
from app.config import get_settings

_settings = get_settings()

class AIService:
    """Unified AI service supporting multiple providers."""

    def __init__(self):
        self.providers = {}

    def get_provider(self, db: Session, provider_id: Optional[int] = None) -> AIProvider:
        """Get AI provider from database."""
        if provider_id:
            provider = db.query(AIProvider).filter(AIProvider.id == provider_id).first()
            if provider and provider.is_enabled:
                return provider

        # Return default provider
        provider = db.query(AIProvider).filter(
            AIProvider.is_default == True,
            AIProvider.is_enabled == True
        ).first()

        if not provider:
            # Return first enabled provider
            provider = db.query(AIProvider).filter(AIProvider.is_enabled == True).first()

        return provider

    async def generate(self, db: Session, request: AIRequest) -> AIResponse:
        """Generate AI response based on provider type."""
        provider = self.get_provider(db, request.provider_id)
        if not provider:
            return AIResponse(
                content="No AI provider configured. Please configure an AI provider in settings.",
                provider="none",
                error="No provider available"
            )

        start_time = time.time()

        try:
            if provider.provider_type == "openai":
                return await self._openai_generate(provider, request)
            elif provider.provider_type == "azure":
                return await self._azure_generate(provider, request)
            elif provider.provider_type == "anthropic":
                return await self._anthropic_generate(provider, request)
            elif provider.provider_type == "ollama":
                return await self._ollama_generate(provider, request)
            elif provider.provider_type == "lmstudio":
                return await self._lmstudio_generate(provider, request)
            elif provider.provider_type == "openrouter":
                return await self._openrouter_generate(provider, request)
            else:
                return AIResponse(
                    content="",
                    provider=provider.provider_type,
                    error=f"Unknown provider type: {provider.provider_type}"
                )
        except Exception as e:
            logger.error(f"AI generation error: {e}")
            return AIResponse(
                content="",
                provider=provider.provider_type,
                error=str(e)
            )

    async def _openai_generate(self, provider: AIProvider, request: AIRequest) -> AIResponse:
        import openai
        client = openai.AsyncOpenAI(api_key=provider.api_key or "")

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        if request.context:
            messages.append({"role": "user", "content": f"Context:\n{request.context}\n\nQuestion: {request.prompt}"})
        else:
            messages.append({"role": "user", "content": request.prompt})

        response = await client.chat.completions.create(
            model=provider.model or "gpt-4o",
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        return AIResponse(
            content=response.choices[0].message.content,
            provider="openai",
            model=provider.model,
            tokens_used=response.usage.total_tokens if response.usage else None,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )

    async def _azure_generate(self, provider: AIProvider, request: AIRequest) -> AIResponse:
        import openai
        client = openai.AsyncAzureOpenAI(
            api_key=provider.api_key or "",
            azure_endpoint=provider.base_url or "",
            api_version=(provider.config.get("api_version") if provider.config else None) or "2024-02-15-preview"
        )

        messages = [{"role": "user", "content": request.prompt}]
        if request.context:
            messages[0]["content"] = f"Context:\n{request.context}\n\n{request.prompt}"

        response = await client.chat.completions.create(
            model=provider.model or "gpt-4",
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        return AIResponse(
            content=response.choices[0].message.content,
            provider="azure",
            model=provider.model,
            tokens_used=response.usage.total_tokens if response.usage else None
        )

    async def _anthropic_generate(self, provider: AIProvider, request: AIRequest) -> AIResponse:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=provider.api_key or "")

        content = request.prompt
        if request.context:
            content = f"Context:\n{request.context}\n\n{request.prompt}"

        response = await client.messages.create(
            model=provider.model or "claude-3-sonnet-20240229",
            max_tokens=request.max_tokens or 2000,
            temperature=request.temperature,
            messages=[{"role": "user", "content": content}]
        )

        return AIResponse(
            content=response.content[0].text,
            provider="anthropic",
            model=provider.model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens if response.usage else None
        )

    async def _ollama_generate(self, provider: AIProvider, request: AIRequest) -> AIResponse:
        import httpx
        base_url = provider.base_url or _settings.OLLAMA_HOST

        content = request.prompt
        if request.context:
            content = f"Context:\n{request.context}\n\n{request.prompt}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": provider.model or "llama3",
                    "prompt": content,
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens
                    }
                },
                timeout=120.0
            )
            data = response.json()
            return AIResponse(
                content=data.get("response", ""),
                provider="ollama",
                model=provider.model
            )

    async def _lmstudio_generate(self, provider: AIProvider, request: AIRequest) -> AIResponse:
        import httpx
        base_url = provider.base_url or _settings.LM_STUDIO_HOST

        content = request.prompt
        if request.context:
            content = f"Context:\n{request.context}\n\n{request.prompt}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "model": provider.model or "local-model",
                    "messages": [{"role": "user", "content": content}],
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens
                },
                timeout=120.0
            )
            data = response.json()
            return AIResponse(
                content=data["choices"][0]["message"]["content"],
                provider="lmstudio",
                model=provider.model
            )

    async def _openrouter_generate(self, provider: AIProvider, request: AIRequest) -> AIResponse:
        import httpx

        content = request.prompt
        if request.context:
            content = f"Context:\n{request.context}\n\n{request.prompt}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {provider.api_key}",
                    "HTTP-Referer": "https://logmorph.ai",
                    "X-Title": "LogMorph AI"
                },
                json={
                    "model": provider.model or "openai/gpt-4o",
                    "messages": [{"role": "user", "content": content}],
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens
                },
                timeout=120.0
            )
            data = response.json()
            return AIResponse(
                content=data["choices"][0]["message"]["content"],
                provider="openrouter",
                model=provider.model
            )

    async def summarize_logs(self, db: Session, log_entries: List[str], provider_id: Optional[int] = None) -> AIResponse:
        """Generate summary of log entries."""
        context = "\n".join(log_entries[:50])  # Limit context
        prompt = """Analyze these log entries and provide:
1. Executive summary (2-3 sentences)
2. Key issues found
3. Recommended actions

Log entries:
"""
        request = AIRequest(
            provider_id=provider_id,
            prompt=prompt + context,
            system_prompt="You are an expert log analysis assistant. Be concise and technical.",
            max_tokens=1500,
            temperature=0.2
        )
        return await self.generate(db, request)

    async def analyze_exception(self, db: Session, exception_type: str, stack_trace: str, provider_id: Optional[int] = None) -> AIResponse:
        """Analyze an exception with AI."""
        prompt = f"""Analyze this exception and provide:
1. Root cause explanation
2. Likely causes
3. Suggested fixes

Exception Type: {exception_type}
Stack Trace:
{stack_trace}"""

        request = AIRequest(
            provider_id=provider_id,
            prompt=prompt,
            system_prompt="You are an expert debugging assistant. Explain clearly and suggest concrete fixes.",
            max_tokens=2000,
            temperature=0.2
        )
        return await self.generate(db, request)

    async def chat(self, db: Session, request: AIChatRequest) -> AIResponse:
        """Chat with AI about logs."""
        provider = self.get_provider(db, request.provider_id)
        if not provider:
            return AIResponse(content="No AI provider configured.", provider="none")

        # Convert to single prompt for simplicity
        context = "\n".join([f"{m.role}: {m.content}" for m in request.messages[-5:]])

        ai_request = AIRequest(
            provider_id=request.provider_id,
            prompt=context,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        return await self.generate(db, ai_request)

ai_service = AIService()
