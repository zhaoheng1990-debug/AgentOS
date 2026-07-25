"""DeepSeek transport dedicated to the frozen v0.87 SciFact contract."""

from __future__ import annotations

import os

from ..bounded_retry_provider import BoundedRetryProviderAdapter
from ..openai_compatible_provider import (
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from .semantic_warrant import TASK_KIND


def build_deepseek_warrant_adapter() -> BoundedRetryProviderAdapter:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    adapter = OpenAICompatibleJsonAdapter(
        OpenAICompatibleProviderSpec(
            provider_id="deepseek-scifact-warrant-v0-87",
            model_id="deepseek-v4-flash",
            endpoint="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            task_kinds=(TASK_KIND,),
            max_tokens=1800,
            timeout_seconds=300,
            extra_body={
                "thinking": {"type": "disabled"},
                "temperature": 0,
            },
        )
    )
    return BoundedRetryProviderAdapter(
        adapter,
        max_attempts=2,
        delay_seconds=1.0,
    )
