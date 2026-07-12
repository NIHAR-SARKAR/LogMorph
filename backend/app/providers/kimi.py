"""Kimi (Moonshot AI) provider adapter using raw httpx."""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.providers.base import BaseLLMClient, ResolvedLLMConfig
from app.core.encryption import decrypt_api_key

logger = logging.getLogger(__name__)


class KimiAdapter(BaseLLMClient):
    name = "kimi"

    def __init__(self) -> None:
        self._clients: Dict[str, httpx.AsyncClient] = {}

    def _validate_config(self, config: ResolvedLLMConfig) -> None:
        from app.providers.base import validate_provider_url
        if config.base_url:
            validate_provider_url(config.base_url, "Kimi", "https://api.moonshot.cn")

    def _get_client(self, config: ResolvedLLMConfig) -> httpx.AsyncClient:
        self._validate_config(config)
        key = decrypt_api_key(config.api_key_encrypted)
        base = (config.base_url or "https://api.moonshot.cn").rstrip("/")
        cache_key = f"kimi:{base}:{key[:8]}"
        if cache_key not in self._clients:
            self._clients[cache_key] = httpx.AsyncClient(
                base_url=base,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._clients[cache_key]

    def _parse_sse(self, line: str) -> Optional[str]:
        line = line.strip()
        if not line or line.startswith(":"):
            return None
        if line.startswith("data: "):
            line = line[6:]
        if line == "[DONE]":
            return None
        try:
            chunk = json.loads(line)
        except json.JSONDecodeError:
            return None
        choices = chunk.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            content = delta.get("content")
            if content:
                return content
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

        body = {
            "model": config.model_id or "moonshot-v1-8k",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with client.stream("POST", "/v1/chat/completions", json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                text = self._parse_sse(line)
                if text is not None:
                    yield text

    async def test_connection(self, config: ResolvedLLMConfig) -> Dict[str, Any]:
        try:
            client = self._get_client(config)
            body = {
                "model": config.model_id or "moonshot-v1-8k",
                "messages": [{"role": "user", "content": "Say hello"}],
                "max_tokens": 10,
            }
            resp = await client.post("/v1/chat/completions", json=body)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return {"success": True, "response": content}
        except Exception as e:
            logger.error("Kimi test connection error: %s", e)
            return {"success": False, "error": str(e)}
