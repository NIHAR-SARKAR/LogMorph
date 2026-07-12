"""Base abstractions for LLM providers."""

import re
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable, Awaitable, Dict, List, Optional

import httpx


def validate_provider_url(base_url: Optional[str], provider_name: str, example: str) -> None:
    """Validate that a provider base_url is a real, resolvable URL."""
    url = (base_url or "").strip()
    if not url:
        raise ValueError(
            f"{provider_name} provider requires a base URL (e.g., {example}). "
            "Please configure the provider in Settings > AI Providers."
        )
    if "<" in url or ">" in url:
        raise ValueError(
            f"{provider_name} base URL contains placeholder characters: {url}. "
            f"Replace placeholders with a real hostname (e.g., {example})."
        )
    parsed: Optional[httpx.URL] = None
    try:
        parsed = httpx.URL(url)
    except Exception:
        pass
    if not parsed or not parsed.host:
        raise ValueError(
            f"{provider_name} base URL is invalid: '{url}'. "
            f"It must be a valid URL like {example}"
        )
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}$", parsed.host):
        raise ValueError(
            f"{provider_name} base URL hostname looks invalid: '{parsed.host}'. "
            f"It should be something like {example}"
        )


@dataclass
class TokenUsage:
    """Token consumption for a request/response."""
    input_tokens: int = 0
    output_tokens: int = 0


# Optional async callback invoked when usage data is available.
UsageCallback = Optional[Callable[[TokenUsage], Awaitable[None]]]


@dataclass
class ResolvedLLMConfig:
    """Normalized configuration passed to a provider adapter."""
    base_url: Optional[str] = None
    api_key_encrypted: str = ""
    model_id: Optional[str] = None
    api_version: Optional[str] = None
    extra_headers: Optional[Dict[str, Any]] = None

    @classmethod
    def from_ai_provider(cls, provider) -> "ResolvedLLMConfig":
        """Build a ResolvedLLMConfig from an app.models.ai.AIProvider instance."""
        config_dict = getattr(provider, "config", None) or {}
        if not isinstance(config_dict, dict):
            config_dict = {}
        return cls(
            base_url=getattr(provider, "base_url", None),
            api_key_encrypted=getattr(provider, "api_key", "") or "",
            model_id=getattr(provider, "model", None),
            api_version=config_dict.get("api_version"),
            extra_headers=config_dict,
        )


class BaseLLMClient:
    """Abstract base for all LLM provider adapters."""

    name: str = "base"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        config: ResolvedLLMConfig,
        max_tokens: int = 2000,
        usage_callback: UsageCallback = None,
    ) -> AsyncGenerator[str, None]:
        """Stream text completions from the LLM."""
        raise NotImplementedError

    async def test_connection(self, config: ResolvedLLMConfig) -> Dict[str, Any]:
        """Test connectivity and credentials with the provider."""
        raise NotImplementedError
