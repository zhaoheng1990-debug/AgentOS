"""DeepSeek transport for paired direct and evidence-scope v0.88 arms."""

from __future__ import annotations

import os

from ..bounded_retry_provider import BoundedRetryProviderAdapter
from ..openai_compatible_provider import (
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from .claim_scope_receipt import TASK_KIND as SCOPE_TASK_KIND
from .evidence_set_receipt import TASK_KIND as EVIDENCE_TASK_KIND
from .semantic_warrant import TASK_KIND as DIRECT_TASK_KIND


def build_deepseek_v0_88_adapter() -> BoundedRetryProviderAdapter:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    adapter = OpenAICompatibleJsonAdapter(
        OpenAICompatibleProviderSpec(
            provider_id="deepseek-scifact-evidence-scope-v0-88",
            model_id="deepseek-v4-flash",
            endpoint="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            task_kinds=(
                DIRECT_TASK_KIND,
                EVIDENCE_TASK_KIND,
                SCOPE_TASK_KIND,
            ),
            max_tokens=2200,
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
