"""Anthropic Claude provider adapter using raw httpx."""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.providers.base import BaseLLMClient, ResolvedLLMConfig
from app.core.encryption import decrypt_api_key

logger = logging.getLogger(__name__)


class ClaudeAdapter(BaseLLMClient):
    name = "claude"

    def __init__(self) -> None:
        self._clients: Dict[str, httpx.AsyncClient] = {}

    def _validate_config(self, config: ResolvedLLMConfig) -> None:
        from app.providers.base import validate_provider_url
        if config.base_url:
            validate_provider_url(config.base_url, "Anthropic Claude", "https://api.anthropic.com")

    def _get_client(self, config: ResolvedLLMConfig) -> httpx.AsyncClient:
        self._validate_config(config)
        key = decrypt_api_key(config.api_key_encrypted)
        base = (config.base_url or "https://api.anthropic.com").rstrip("/")
        cache_key = f"claude:{base}:{key[:8]}"
        if cache_key not in self._clients:
            self._clients[cache_key] = httpx.AsyncClient(
                base_url=base,
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._clients[cache_key]

    def _parse_sse(self, line: str) -> Optional[str]:
        line = line.strip()
        if not line or line.startswith(":") or line.startswith("event:"):
            return None
        if line.startswith("data: "):
            line = line[6:]
        if line == "[DONE]":
            return None
        try:
            chunk = json.loads(line)
        except json.JSONDecodeError:
            return None
        if chunk.get("type") == "content_block_delta":
            delta = chunk.get("delta", {})
            if delta.get("type") == "text_delta":
                return delta.get("text")
        return None

    async def generate(
        self,
        messages: List[Dict[str, str]],
        config: ResolvedLLMConfig,
        max_tokens: int = 2000,
        usage_callback=None,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client(config)
        extra = config.extra_headers or {}
        temperature = 0.7
        if isinstance(extra, dict) and "temperature" in extra:
            try:
                temperature = float(extra["temperature"])
            except (ValueError, TypeError):
                temperature = 0.7

        system_texts: List[str] = []
        chat_messages: List[Dict[str, str]] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_texts.append(content)
            else:
                chat_messages.append({"role": role, "content": content})

        body: Dict[str, Any] = {
            "model": config.model_id or "claude-3-sonnet-20240229",
            "max_tokens": max_tokens,
            "messages": chat_messages,
            "stream": True,
        }
        if temperature is not None:
            body["temperature"] = temperature
        if system_texts:
            body["system"] = "\n".join(system_texts)

        async with client.stream("POST", "/v1/messages", json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                text = self._parse_sse(line)
                if text is not None:
                    yield text

    async def test_connection(self, config: ResolvedLLMConfig) -> Dict[str, Any]:
        try:
            client = self._get_client(config)
            body = {
                "model": config.model_id or "claude-3-sonnet-20240229",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Say hello"}],
            }
            resp = await client.post("/v1/messages", json=body)
            resp.raise_for_status()
            data = resp.json()
            content = data["content"][0]["text"]
            return {"success": True, "response": content}
        except Exception as e:
            logger.error("Claude test connection error: %s", e)
            return {"success": False, "error": str(e)}
