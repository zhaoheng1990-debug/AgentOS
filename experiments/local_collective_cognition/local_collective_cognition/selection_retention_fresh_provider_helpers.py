"""Shared Provider-call receipts for the v0.64 experiment."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderCognitiveTask


def call_record(
    role: str,
    case_id: str,
    task: ProviderCognitiveTask,
    envelope: Any,
) -> dict[str, Any]:
    return {
        "role": role,
        "case_id": case_id,
        "status": envelope.status,
        "token_usage": dict(envelope.invocation_receipt.token_usage),
        "task_id": task.task_id,
    }


def failed_call(
    call: dict[str, Any],
    envelope: Any,
) -> dict[str, Any]:
    return {
        **call,
        "validation_errors": list(envelope.validation_errors),
        "redacted_error_state": envelope.invocation_receipt.redacted_error_state,
    }


def token_count(calls: list[dict[str, Any]]) -> int:
    return sum(call["token_usage"]["total_tokens"] for call in calls)


def physical_attempts(calls: list[dict[str, Any]]) -> int:
    return sum(
        int(call["token_usage"].get("provider_calls", 1)) for call in calls
    )
