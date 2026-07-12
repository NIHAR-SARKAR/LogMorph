import time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.ai import AIProvider
from app.schemas.ai import AIRequest, AIResponse, AIChatRequest, AIChatMessage
from app.core.logging import logger
from app.config import get_settings
from app.providers import registry, ResolvedLLMConfig

_settings = get_settings()


class AIService:
    """Unified AI service supporting multiple providers via adapter registry."""

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

    def _build_messages(self, request: AIRequest) -> List[Dict[str, str]]:
        """Build standard message list from AIRequest."""
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        if request.context:
            messages.append({
                "role": "user",
                "content": f"Context:\n{request.context}\n\nQuestion: {request.prompt}",
            })
        else:
            messages.append({"role": "user", "content": request.prompt})
        return messages

    async def generate(self, db: Session, request: AIRequest) -> AIResponse:
        """Generate AI response using the configured provider adapter."""
        provider = self.get_provider(db, request.provider_id)
        if not provider:
            return AIResponse(
                content="No AI provider configured. Please configure an AI provider in settings.",
                provider="none",
                error="No provider available",
            )

        start_time = time.time()
        adapter = registry.get(provider.provider_type)
        if not adapter:
            return AIResponse(
                content="",
                provider=provider.provider_type,
                error=f"Unsupported provider type: {provider.provider_type}",
            )

        try:
            messages = self._build_messages(request)
            config = ResolvedLLMConfig.from_ai_provider(provider)
            chunks = []
            async for chunk in adapter.generate(
                messages=messages,
                config=config,
                max_tokens=request.max_tokens or 500,
            ):
                chunks.append(chunk)

            return AIResponse(
                content="".join(chunks),
                provider=provider.provider_type,
                model=provider.model,
                processing_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"AI generation error: {e}")
            return AIResponse(
                content="",
                provider=provider.provider_type,
                error=str(e),
            )

    async def chat(self, db: Session, request: AIChatRequest) -> AIResponse:
        """Chat with AI using structured messages. Optionally scoped to a project."""
        provider = self.get_provider(db, request.provider_id)
        if not provider:
            return AIResponse(content="No AI provider configured.", provider="none")

        start_time = time.time()
        adapter = registry.get(provider.provider_type)
        if not adapter:
            return AIResponse(
                content="",
                provider=provider.provider_type,
                error=f"Unsupported provider type: {provider.provider_type}",
            )

        try:
            messages = [{"role": m.role, "content": m.content} for m in request.messages]

            # If project_id is provided, inject project-specific log context as system prompt
            if request.project_id is not None:
                from app.models.project import Project
                from app.models.log import LogEntry, LogFile
                from app.models.project import LogSource
                from sqlalchemy import desc

                project = db.query(Project).filter(Project.id == request.project_id).first()
                if project:
                    recent_errors = (
                        db.query(LogEntry)
                        .join(LogFile, LogEntry.log_file_id == LogFile.id)
                        .join(LogSource, LogFile.log_source_id == LogSource.id)
                        .filter(
                            LogSource.project_id == request.project_id,
                            LogEntry.severity.in_(["error", "critical", "fatal"])
                        )
                        .order_by(desc(LogEntry.timestamp))
                        .limit(20)
                        .all()
                    )

                    error_summary = ""
                    if recent_errors:
                        error_lines = []
                        for e in recent_errors[:10]:
                            msg = e.message[:200] if e.message else ""
                            error_lines.append(f"- [{e.severity.value}] {e.logger or 'unknown'}: {msg}")
                        error_summary = "\n".join(error_lines)
                    else:
                        error_summary = "No recent errors found."

                    context_msg = {
                        "role": "system",
                        "content": (
                            f"You are analyzing logs for project: {project.name}.\n\n"
                            f"Recent errors from this project:\n{error_summary}\n\n"
                            "Answer the user's questions based only on this project's logs."
                        ),
                    }
                    messages.insert(0, context_msg)

            config = ResolvedLLMConfig.from_ai_provider(provider)
            chunks = []
            async for chunk in adapter.generate(
                messages=messages,
                config=config,
                max_tokens=request.max_tokens or 500,
            ):
                chunks.append(chunk)

            return AIResponse(
                content="".join(chunks),
                provider=provider.provider_type,
                model=provider.model,
                processing_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            return AIResponse(
                content="",
                provider=provider.provider_type,
                error=str(e),
            )

    async def summarize_logs(self, db: Session, log_entries: List[str], provider_id: Optional[int] = None) -> AIResponse:
        """Generate summary of log entries."""
        context = "\n".join(log_entries[:50])
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
            max_tokens=500,
            temperature=0.2,
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
            max_tokens=500,
            temperature=0.2,
        )
        return await self.generate(db, request)


ai_service = AIService()
