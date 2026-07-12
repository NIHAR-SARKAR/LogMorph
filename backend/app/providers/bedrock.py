"""Amazon Bedrock provider adapter using boto3 via asyncio executor."""

import asyncio
import json
import logging
from functools import partial
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.providers.base import BaseLLMClient, ResolvedLLMConfig
from app.core.encryption import decrypt_api_key

logger = logging.getLogger(__name__)


class BedrockAdapter(BaseLLMClient):
    name = "bedrock"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        config: ResolvedLLMConfig,
        max_tokens: int = 2000,
        usage_callback=None,
    ) -> AsyncGenerator[str, None]:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for Amazon Bedrock support. Install it with: pip install boto3") from exc

        extra = config.extra_headers or {}
        region = extra.get("region", "us-east-1") if isinstance(extra, dict) else "us-east-1"
        access_key = config.api_key_encrypted or ""
        secret_key = extra.get("secret_key", "") if isinstance(extra, dict) else ""

        if not access_key or not secret_key:
            raise RuntimeError("AWS Access Key ID and Secret Access Key are required for Bedrock")

        client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

        system_texts: List[Dict[str, str]] = []
        bedrock_messages: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_texts.append({"text": content})
            else:
                bedrock_messages.append({
                    "role": role,
                    "content": [{"text": content}],
                })

        inference_config = {"maxTokens": max_tokens}
        if isinstance(extra, dict) and "temperature" in extra:
            try:
                inference_config["temperature"] = float(extra["temperature"])
            except (ValueError, TypeError):
                pass

        kwargs: Dict[str, Any] = {
            "modelId": config.model_id or "anthropic.claude-3-sonnet-20240229-v1:0",
            "messages": bedrock_messages,
            "inferenceConfig": inference_config,
        }
        if system_texts:
            kwargs["system"] = system_texts

        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None, partial(client.converse_stream, **kwargs)
            )
            stream = response.get("stream", [])
            for event in stream:
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"].get("delta", {})
                    text = delta.get("text")
                    if text:
                        yield text
        except Exception as e:
            logger.error("Bedrock stream error: %s", e)
            raise

    async def test_connection(self, config: ResolvedLLMConfig) -> Dict[str, Any]:
        try:
            import boto3
        except ImportError:
            return {"success": False, "error": "boto3 is required for Amazon Bedrock support"}

        extra = config.extra_headers or {}
        region = extra.get("region", "us-east-1") if isinstance(extra, dict) else "us-east-1"
        access_key = config.api_key_encrypted or ""
        secret_key = extra.get("secret_key", "") if isinstance(extra, dict) else ""

        if not access_key or not secret_key:
            return {"success": False, "error": "AWS Access Key ID and Secret Access Key are required"}

        client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                partial(
                    client.converse,
                    modelId=config.model_id or "anthropic.claude-3-sonnet-20240229-v1:0",
                    messages=[{"role": "user", "content": [{"text": "Say hello"}]}],
                    inferenceConfig={"maxTokens": 10},
                ),
            )
            text = response["output"]["message"]["content"][0]["text"]
            return {"success": True, "response": text}
        except Exception as e:
            logger.error("Bedrock test connection error: %s", e)
            return {"success": False, "error": str(e)}
