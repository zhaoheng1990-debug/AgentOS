"""DeepSeek transport for the v0.89 binding-veto experiment."""

from __future__ import annotations

import os

from ..bounded_retry_provider import BoundedRetryProviderAdapter
from ..openai_compatible_provider import (
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from .claim_atom_binding import TASK_KIND as BINDING_TASK_KIND
from .claim_scope_receipt import TASK_KIND as SCOPE_TASK_KIND
from .evidence_binding_challenge import TASK_KIND as CHALLENGE_TASK_KIND
from .evidence_set_receipt import TASK_KIND as EVIDENCE_TASK_KIND


def build_deepseek_v0_89_adapter() -> BoundedRetryProviderAdapter:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    adapter = OpenAICompatibleJsonAdapter(
        OpenAICompatibleProviderSpec(
            provider_id="deepseek-scifact-claim-atom-binding-v0-89",
            model_id="deepseek-v4-flash",
            endpoint="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            task_kinds=(
                EVIDENCE_TASK_KIND,
                SCOPE_TASK_KIND,
                BINDING_TASK_KIND,
                CHALLENGE_TASK_KIND,
            ),
            max_tokens=2600,
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
