"""Ollama provider adapter using raw httpx."""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.providers.base import BaseLLMClient, ResolvedLLMConfig

logger = logging.getLogger(__name__)


class OllamaAdapter(BaseLLMClient):
    name = "ollama"

    def __init__(self) -> None:
        self._clients: Dict[str, httpx.AsyncClient] = {}

    def _get_client(self, config: ResolvedLLMConfig) -> httpx.AsyncClient:
        base = (config.base_url or "http://localhost:11434").rstrip("/")
        cache_key = f"ollama:{base}"
        if cache_key not in self._clients:
            self._clients[cache_key] = httpx.AsyncClient(
                base_url=base,
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._clients[cache_key]

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
            "model": config.model_id or "llama3",
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with client.stream("POST", "/api/chat", json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = chunk.get("message", {})
                content = msg.get("content", "")
                if content:
                    yield content

    async def test_connection(self, config: ResolvedLLMConfig) -> Dict[str, Any]:
        try:
            client = self._get_client(config)
            body = {
                "model": config.model_id or "llama3",
                "messages": [{"role": "user", "content": "Say hello"}],
                "stream": False,
                "options": {"num_predict": 10},
            }
            resp = await client.post("/api/chat", json=body)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            return {"success": True, "response": content}
        except Exception as e:
            logger.error("Ollama test connection error: %s", e)
            return {"success": False, "error": str(e)}
