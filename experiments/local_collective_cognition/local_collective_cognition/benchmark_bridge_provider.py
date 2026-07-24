"""Frozen Provider transport for the v0.65 benchmark bridge."""

from __future__ import annotations

import os

from .bounded_retry_provider import BoundedRetryProviderAdapter
from .frontier_experiment import TASK_KIND
from .openai_compatible_provider import (
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)


def build_deepseek_adapter() -> BoundedRetryProviderAdapter:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    return BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-benchmark-bridge-v0-65",
            model_id="deepseek-v4-flash",
            endpoint="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            task_kinds=(TASK_KIND,),
            max_tokens=2600,
            timeout_seconds=300,
            extra_body={
                "thinking": {"type": "disabled"},
                "temperature": 0,
            },
        )),
        max_attempts=2,
        delay_seconds=1.0,
    )
