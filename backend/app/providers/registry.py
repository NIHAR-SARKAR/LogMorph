"""Provider registry mapping provider_type names to adapter classes."""

from typing import Dict, List, Optional, Type

from app.providers.base import BaseLLMClient
from app.providers.azure import AzureAdapter
from app.providers.openai import OpenAIAdapter
from app.providers.claude import ClaudeAdapter
from app.providers.google import GoogleAdapter
from app.providers.openrouter import OpenRouterAdapter
from app.providers.bedrock import BedrockAdapter
from app.providers.kimi import KimiAdapter
from app.providers.ollama import OllamaAdapter
from app.providers.lmstudio import LMStudioAdapter


class ProviderRegistry:
    def __init__(self):
        self._map: Dict[str, Type[BaseLLMClient]] = {}

    def register(self, name: str, cls: Type[BaseLLMClient]) -> None:
        self._map[name] = cls

    def get(self, name: str) -> Optional[BaseLLMClient]:
        cls = self._map.get(name)
        if cls:
            return cls()
        return None

    def list_providers(self) -> List[str]:
        return list(self._map.keys())


registry = ProviderRegistry()
registry.register("azure", AzureAdapter)
registry.register("openai", OpenAIAdapter)
registry.register("anthropic", ClaudeAdapter)
registry.register("claude", ClaudeAdapter)
registry.register("google", GoogleAdapter)
registry.register("openrouter", OpenRouterAdapter)
registry.register("bedrock", BedrockAdapter)
registry.register("kimi", KimiAdapter)
registry.register("ollama", OllamaAdapter)
registry.register("lmstudio", LMStudioAdapter)
