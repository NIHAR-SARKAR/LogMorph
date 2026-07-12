"""Azure OpenAI provider implementation with comprehensive multi-model support.

Uses raw httpx instead of the openai SDK to support ALL Azure-hosted model families
including legacy, v1, Responses API, and Azure AI Foundry endpoints.

Supported families:
- OpenAI GPT-5.x series (5.1, 5.2, 5.3, 5.4, 5.5, codex, chat, pro, mini, nano)
- OpenAI o-series reasoning (o1, o1-mini, o3, o3-mini, o3-pro, o4, o4-mini)
- OpenAI GPT-4.x series (4, 4o, 4o-mini, 4.1, 4.1-mini, 4.1-nano)
- Non-OpenAI via Azure AI Foundry: DeepSeek, Meta Llama, Mistral, Cohere, Phi,
  NVIDIA Nemotron, Grok, Kimi, Jamba, MiniMax, gpt-oss, and others.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.providers.base import BaseLLMClient, ResolvedLLMConfig, TokenUsage, UsageCallback
from app.core.encryption import decrypt_api_key

logger = logging.getLogger(__name__)


class AzureAPIPattern(Enum):
    """Azure API endpoint patterns."""
    AZURE_OPENAI_LEGACY = "azure_openai_legacy"
    AZURE_OPENAI_V1 = "azure_openai_v1"
    AZURE_RESPONSES = "azure_responses"
    AZURE_AI_FOUNDRY = "azure_ai_foundry"


@dataclass
class ModelFamilyConfig:
    """Configuration for a model family."""
    family: str
    supported_patterns: List[AzureAPIPattern]
    default_pattern: AzureAPIPattern
    prefers_developer_role: bool = False
    uses_max_completion_tokens: bool = False
    supports_reasoning_effort: bool = False
    supports_temperature: bool = True


class AzureAdapter(BaseLLMClient):
    """Azure provider with comprehensive model support and intelligent API routing."""

    name = "azure"

    _MODEL_REGISTRY: Dict[str, ModelFamilyConfig] = {
        # GPT-5.x series
        "gpt-5.5": ModelFamilyConfig("gpt-5.5", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.4": ModelFamilyConfig("gpt-5.4", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.3-codex": ModelFamilyConfig("gpt-5.3-codex", [AzureAPIPattern.AZURE_RESPONSES, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_RESPONSES, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.3-chat": ModelFamilyConfig("gpt-5.3-chat", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.2-codex": ModelFamilyConfig("gpt-5.2-codex", [AzureAPIPattern.AZURE_RESPONSES, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_RESPONSES, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.2-chat": ModelFamilyConfig("gpt-5.2-chat", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.2": ModelFamilyConfig("gpt-5.2", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.1-codex-max": ModelFamilyConfig("gpt-5.1-codex-max", [AzureAPIPattern.AZURE_RESPONSES, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_RESPONSES, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.1-codex": ModelFamilyConfig("gpt-5.1-codex", [AzureAPIPattern.AZURE_RESPONSES, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_RESPONSES, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.1-codex-mini": ModelFamilyConfig("gpt-5.1-codex-mini", [AzureAPIPattern.AZURE_RESPONSES, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_RESPONSES, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.1-chat": ModelFamilyConfig("gpt-5.1-chat", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.1": ModelFamilyConfig("gpt-5.1", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5-pro": ModelFamilyConfig("gpt-5-pro", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5-codex": ModelFamilyConfig("gpt-5-codex", [AzureAPIPattern.AZURE_RESPONSES, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_RESPONSES, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5": ModelFamilyConfig("gpt-5", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5-mini": ModelFamilyConfig("gpt-5-mini", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5-nano": ModelFamilyConfig("gpt-5-nano", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),

        # o-series
        "o4-mini": ModelFamilyConfig("o4-mini", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "o4": ModelFamilyConfig("o4", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "o3-pro": ModelFamilyConfig("o3-pro", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "o3-mini": ModelFamilyConfig("o3-mini", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "o3": ModelFamilyConfig("o3", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "o1-mini": ModelFamilyConfig("o1-mini", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=False, supports_temperature=False),
        "o1": ModelFamilyConfig("o1", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),

        # GPT-4.x
        "gpt-4.1-nano": ModelFamilyConfig("gpt-4.1-nano", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_OPENAI_LEGACY], AzureAPIPattern.AZURE_OPENAI_V1),
        "gpt-4.1-mini": ModelFamilyConfig("gpt-4.1-mini", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_OPENAI_LEGACY], AzureAPIPattern.AZURE_OPENAI_V1),
        "gpt-4.1": ModelFamilyConfig("gpt-4.1", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_OPENAI_LEGACY], AzureAPIPattern.AZURE_OPENAI_V1),
        "gpt-4o-mini": ModelFamilyConfig("gpt-4o-mini", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_OPENAI_LEGACY], AzureAPIPattern.AZURE_OPENAI_V1),
        "gpt-4o": ModelFamilyConfig("gpt-4o", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_OPENAI_LEGACY], AzureAPIPattern.AZURE_OPENAI_V1),
        "gpt-4-turbo": ModelFamilyConfig("gpt-4-turbo", [AzureAPIPattern.AZURE_OPENAI_LEGACY, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_OPENAI_LEGACY),
        "gpt-4": ModelFamilyConfig("gpt-4", [AzureAPIPattern.AZURE_OPENAI_LEGACY, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_OPENAI_LEGACY),

        # Azure AI Foundry / non-OpenAI
        "deepseek": ModelFamilyConfig("deepseek", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "llama": ModelFamilyConfig("llama", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "meta-llama": ModelFamilyConfig("meta-llama", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "mistral": ModelFamilyConfig("mistral", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "cohere": ModelFamilyConfig("cohere", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "phi": ModelFamilyConfig("phi", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "nemotron": ModelFamilyConfig("nemotron", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "grok": ModelFamilyConfig("grok", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "jamba": ModelFamilyConfig("jamba", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "minimax": ModelFamilyConfig("minimax", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "kimi": ModelFamilyConfig("kimi", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "claude": ModelFamilyConfig("claude", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "anthropic": ModelFamilyConfig("anthropic", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "gpt-oss": ModelFamilyConfig("gpt-oss", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "qwen": ModelFamilyConfig("qwen", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "granite": ModelFamilyConfig("granite", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "command": ModelFamilyConfig("command", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "wizard": ModelFamilyConfig("wizard", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "falcon": ModelFamilyConfig("falcon", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "mamba": ModelFamilyConfig("mamba", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "nous": ModelFamilyConfig("nous", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "yi": ModelFamilyConfig("yi", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "baichuan": ModelFamilyConfig("baichuan", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
    }

    def __init__(self) -> None:
        self._clients: Dict[str, httpx.AsyncClient] = {}

    def _get_client(self, config: ResolvedLLMConfig) -> httpx.AsyncClient:
        """Get or create cached httpx client for a config."""
        key_material = config.api_key_encrypted or ""
        cache_key = f"{config.base_url or ''}:{key_material[:16]}"
        if cache_key not in self._clients:
            api_key = decrypt_api_key(key_material)
            headers = {"api-key": api_key, "Content-Type": "application/json"}
            # Support bearer auth for some endpoints
            extra = config.extra_headers or {}
            if isinstance(extra, dict) and extra.get("use_bearer_auth"):
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            self._clients[cache_key] = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._clients[cache_key]

    def _detect_model_config(self, model_or_deployment: str) -> ModelFamilyConfig:
        model_lower = model_or_deployment.lower().replace("_", "-").replace(" ", "-")
        best_match: Optional[str] = None
        best_len = 0
        for prefix in self._MODEL_REGISTRY:
            prefix_lower = prefix.lower()
            if model_lower.startswith(prefix_lower) and len(prefix_lower) > best_len:
                best_match = prefix
                best_len = len(prefix_lower)
        if best_match:
            return self._MODEL_REGISTRY[best_match]
        for prefix, cfg in self._MODEL_REGISTRY.items():
            if prefix.lower() in model_lower:
                return cfg
        return ModelFamilyConfig(
            family="unknown",
            supported_patterns=[AzureAPIPattern.AZURE_OPENAI_LEGACY],
            default_pattern=AzureAPIPattern.AZURE_OPENAI_LEGACY,
        )

    def _resolve_pattern(self, config: ModelFamilyConfig, llm_config: ResolvedLLMConfig) -> AzureAPIPattern:
        """Resolve which API pattern to use based on endpoint URL and config."""
        base_url = (llm_config.base_url or "").lower().rstrip("/")

        # Auto-detect from URL
        if ".services.ai.azure.com" in base_url:
            return AzureAPIPattern.AZURE_AI_FOUNDRY
        if "/openai/v1" in base_url:
            # Check if responses API is requested
            extra = llm_config.extra_headers or {}
            if isinstance(extra, dict) and extra.get("use_responses_api"):
                return AzureAPIPattern.AZURE_RESPONSES
            return AzureAPIPattern.AZURE_OPENAI_V1
        if "/openai/deployments/" in base_url:
            return AzureAPIPattern.AZURE_OPENAI_LEGACY

        # Default to config's default pattern
        return config.default_pattern

    def _get_url(self, base_url: str, deployment: str, pattern: AzureAPIPattern, api_version: str = "2024-12-01-preview") -> str:
        """Build the full API URL."""
        base = base_url.rstrip("/")

        if pattern == AzureAPIPattern.AZURE_OPENAI_LEGACY:
            if "/openai/deployments/" not in base:
                base = f"{base}/openai/deployments/{deployment}"
            return f"{base}/chat/completions?api-version={api_version}"

        elif pattern == AzureAPIPattern.AZURE_OPENAI_V1:
            if "/openai/v1" not in base:
                base = f"{base}/openai/v1"
            return f"{base}/chat/completions"

        elif pattern == AzureAPIPattern.AZURE_RESPONSES:
            if "/openai/v1" not in base:
                base = f"{base}/openai/v1"
            return f"{base}/responses?api-version=2025-04-01-preview"

        elif pattern == AzureAPIPattern.AZURE_AI_FOUNDRY:
            # Foundry endpoints: https://{resource}.services.ai.azure.com/models/chat/completions
            if ".services.ai.azure.com" in base or (".azure.com" in base and ".openai.azure.com" not in base):
                return f"{base}/chat/completions"
            else:
                if "/openai/v1" not in base:
                    base = f"{base}/openai/v1"
                return f"{base}/chat/completions"
        raise RuntimeError(f"Unsupported API pattern: {pattern}")

    def _build_messages(self, config: ModelFamilyConfig, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Process messages - convert system to developer role if needed."""
        result = []
        for msg in messages:
            if msg.get("role") == "system" and config.prefers_developer_role:
                result.append({"role": "developer", "content": msg.get("content", "")})
            else:
                result.append(msg)
        return result

    def _build_request_body(
        self,
        pattern: AzureAPIPattern,
        model_config: ModelFamilyConfig,
        messages: List[Dict[str, str]],
        deployment: str,
        temperature: float,
        max_tokens: int,
        stream: bool = True,
    ) -> Dict[str, Any]:
        """Build the request body. NEVER includes null temperature."""
        body: Dict[str, Any]

        if pattern == AzureAPIPattern.AZURE_RESPONSES:
            # Responses API uses "input" instead of "messages"
            inputs = []
            for msg in messages:
                if msg.get("role") in ("system", "developer"):
                    inputs.append({"role": "developer", "content": msg.get("content", "")})
                else:
                    inputs.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

            body = {
                "model": deployment,
                "input": inputs,
                "stream": stream,
            }
            if max_tokens > 0:
                body["max_output_tokens"] = max_tokens
            # Responses API does NOT support temperature
            return body

        else:
            # Chat Completions API
            body = {
                "messages": messages,
                "stream": stream,
            }

            # Only include model for V1 and Foundry (not legacy)
            if pattern in (AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_AI_FOUNDRY):
                body["model"] = deployment

            # Temperature: ONLY include if model supports it AND it's a valid number
            if model_config.supports_temperature:
                body["temperature"] = temperature

            # Max tokens handling
            if max_tokens > 0:
                if model_config.uses_max_completion_tokens and pattern != AzureAPIPattern.AZURE_AI_FOUNDRY:
                    body["max_completion_tokens"] = max_tokens
                else:
                    body["max_tokens"] = max_tokens

            return body

    def _parse_stream_chunk(self, pattern: AzureAPIPattern, line: str) -> Optional[str]:
        """Parse a single SSE line and extract text content."""
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

        if pattern == AzureAPIPattern.AZURE_RESPONSES:
            # Responses API format
            for item in chunk.get("output", []):
                if item.get("type") == "message":
                    for content in item.get("content", []):
                        if content.get("type") == "output_text":
                            text = content.get("text", "")
                            if text:
                                return text
            return None

        # Chat Completions format
        choices = chunk.get("choices", [])
        if choices and len(choices) > 0:
            delta = choices[0].get("delta", {})
            content = delta.get("content")
            if content:
                return content
        return None

    def _parse_usage(self, pattern: AzureAPIPattern, chunk: dict) -> Optional[TokenUsage]:
        """Extract usage from a parsed SSE chunk, if present."""
        if pattern == AzureAPIPattern.AZURE_RESPONSES:
            usage = chunk.get("usage")
            if usage:
                return TokenUsage(
                    input_tokens=usage.get("input_tokens", 0) or 0,
                    output_tokens=usage.get("output_tokens", 0) or 0,
                )
            return None

        usage = chunk.get("usage")
        if usage:
            return TokenUsage(
                input_tokens=usage.get("prompt_tokens", 0) or 0,
                output_tokens=usage.get("completion_tokens", 0) or 0,
            )
        return None

    def _parse_response(self, pattern: AzureAPIPattern, response_json: dict) -> str:
        """Parse non-streaming response."""
        if pattern == AzureAPIPattern.AZURE_RESPONSES:
            text = response_json.get("output_text")
            if text:
                return text
            output = response_json.get("output", [])
            if output and isinstance(output, list):
                content = output[0].get("content", [])
                if content and isinstance(content, list):
                    return content[0].get("text", "")
            return json.dumps(response_json)

        choices = response_json.get("choices", [])
        if choices and isinstance(choices, list):
            message = choices[0].get("message", {})
            return message.get("content", "")
        return json.dumps(response_json)

    def _parse_raw_line(self, line: str) -> Optional[dict]:
        """Parse a raw SSE line into a dict if possible."""
        line = line.strip()
        if not line or line.startswith(":"):
            return None
        if line.startswith("data: "):
            line = line[6:]
        if line == "[DONE]":
            return None
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None

    def _validate_config(self, config: ResolvedLLMConfig) -> None:
        """Validate that required config fields are present and well-formed."""
        from app.providers.base import validate_provider_url
        validate_provider_url(
            config.base_url,
            "Azure",
            "https://my-resource.openai.azure.com"
        )
        api_key = (config.api_key_encrypted or "").strip()
        if not api_key:
            raise ValueError(
                "Azure provider requires an API key. "
                "Please configure the provider in Settings > AI Providers."
            )

    async def generate(
        self,
        messages: List[Dict[str, str]],
        config: ResolvedLLMConfig,
        max_tokens: int = 2000,
        usage_callback: UsageCallback = None,
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response from Azure."""
        self._validate_config(config)
        deployment = config.model_id or "gpt-4.1"
        model_config = self._detect_model_config(deployment)
        pattern = self._resolve_pattern(model_config, config)

        base_url = config.base_url or ""
        api_version = getattr(config, "api_version", None) or "2024-12-01-preview"
        url = self._get_url(base_url, deployment, pattern, api_version)

        client = self._get_client(config)
        processed_messages = self._build_messages(model_config, messages)

        # CRITICAL FIX: temperature must be a valid float, never None
        # Get from config extra params, default to 0.7
        extra = config.extra_headers or {}
        temperature = 0.7
        if isinstance(extra, dict) and "temperature" in extra:
            try:
                temp_val = extra["temperature"]
                if temp_val is not None:
                    temperature = float(temp_val)
            except (ValueError, TypeError):
                temperature = 0.7

        body = self._build_request_body(
            pattern=pattern,
            model_config=model_config,
            messages=processed_messages,
            deployment=deployment,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                usage: Optional[TokenUsage] = None
                async with client.stream("POST", url, json=body) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        content = self._parse_stream_chunk(pattern, line)
                        if content is not None:
                            yield content
                        parsed = self._parse_raw_line(line)
                        if parsed:
                            parsed_usage = self._parse_usage(pattern, parsed)
                            if parsed_usage:
                                usage = parsed_usage

                if usage_callback and usage:
                    await usage_callback(usage)
                break

            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 500, 502, 503) and attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error("Azure HTTP error: %s - %s", e.response.status_code, e.response.text)
                raise RuntimeError(f"Azure API error {e.response.status_code}: {e.response.text}") from e
            except Exception as e:
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error("Azure API error: %s", e)
                raise

    async def test_connection(self, config: ResolvedLLMConfig) -> Dict[str, Any]:
        """Test connection to Azure."""
        try:
            self._validate_config(config)
            deployment = config.model_id or "gpt-4.1"
            model_config = self._detect_model_config(deployment)
            pattern = self._resolve_pattern(model_config, config)

            base_url = config.base_url or ""
            api_version = getattr(config, "api_version", None) or "2024-12-01-preview"
            url = self._get_url(base_url, deployment, pattern, api_version)

            client = self._get_client(config)
            processed_messages = self._build_messages(model_config, [{"role": "user", "content": "Say hello"}])

            # CRITICAL FIX: temperature must be a valid float, never None
            extra = config.extra_headers or {}
            temperature = 0.7
            if isinstance(extra, dict) and "temperature" in extra:
                try:
                    temp_val = extra["temperature"]
                    if temp_val is not None:
                        temperature = float(temp_val)
                except (ValueError, TypeError):
                    temperature = 0.7

            body = self._build_request_body(
                pattern=pattern,
                model_config=model_config,
                messages=processed_messages,
                deployment=deployment,
                temperature=temperature,
                max_tokens=50,
                stream=False,
            )

            response = await client.post(url, json=body)
            response.raise_for_status()
            data = response.json()
            content = self._parse_response(pattern, data)
            return {"success": True, "response": content}

        except Exception as e:
            logger.error("Azure test connection error: %s", e)
            return {"success": False, "error": str(e)}
