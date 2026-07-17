"""Provider-backed cognitive task execution plane.

Core owns the task contract, validation, receipts, fallback semantics, and
final candidate state. Provider adapters only translate provider-specific
formats into bounded runtime envelopes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Protocol


PROVIDER_EXECUTION_PLANE_VERSION = "provider_cognitive_execution_plane_v0_1"

STATUS_COMPLETED = "COMPLETED"
STATUS_PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
STATUS_VALIDATION_FAILED = "VALIDATION_FAILED"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(data).hexdigest()


def _redact_error(error: Exception | str) -> str:
    text = str(error)
    for marker in ("sk-", "ghp_", "gho_", "Bearer "):
        if marker in text:
            return "redacted_provider_error"
    return text[:240]


@dataclass(frozen=True)
class ProviderCognitiveTask:
    task_id: str
    task_kind: str
    objective: str
    inputs: dict[str, Any]
    allowed_evidence: list[str]
    expected_schema: dict[str, Any]
    budget: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 60
    freshness_requirement: str = "unknown"
    failure_semantics: str = "recoverable_no_semantic_result"
    idempotency_key: str = ""

    def __post_init__(self) -> None:
        if not self.idempotency_key:
            object.__setattr__(
                self,
                "idempotency_key",
                f"pct-{_hash_payload([self.task_id, self.task_kind, self.objective, self.inputs])[:16]}",
            )

    def contract_hash(self) -> str:
        return _hash_payload(
            {
                "task_id": self.task_id,
                "task_kind": self.task_kind,
                "objective": self.objective,
                "inputs": self.inputs,
                "allowed_evidence": self.allowed_evidence,
                "expected_schema": self.expected_schema,
                "budget": self.budget,
                "timeout_seconds": self.timeout_seconds,
                "freshness_requirement": self.freshness_requirement,
                "failure_semantics": self.failure_semantics,
                "idempotency_key": self.idempotency_key,
            }
        )


@dataclass(frozen=True)
class ProviderCapabilityProfile:
    provider_id: str
    model_id: str
    task_kinds: tuple[str, ...]
    supports_thinking_mode: bool = False
    supports_web_search: bool = False
    local_model: bool = False
    custom_endpoint: str = ""
    max_timeout_seconds: int = 60

    def supports(self, task: ProviderCognitiveTask) -> bool:
        return task.task_kind in self.task_kinds and task.timeout_seconds <= self.max_timeout_seconds


@dataclass(frozen=True)
class ProviderFallbackDecision:
    decision: str
    reason: str
    attempted_providers: tuple[str, ...]
    selected_provider: str = ""


@dataclass(frozen=True)
class ProviderInvocationReceipt:
    task_id: str
    idempotency_key: str
    provider_id: str
    model_id: str
    input_hash: str
    output_hash: str
    token_usage: dict[str, Any]
    timeout_seconds: int
    retry_count: int
    fallback_decision: ProviderFallbackDecision
    redacted_error_state: str = ""
    created_at: str = field(default_factory=_utc_now)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "task_id": self.task_id,
            "idempotency_key": self.idempotency_key,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "token_usage": self.token_usage,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "fallback_decision": {
                "decision": self.fallback_decision.decision,
                "reason": self.fallback_decision.reason,
                "attempted_providers": list(self.fallback_decision.attempted_providers),
                "selected_provider": self.fallback_decision.selected_provider,
            },
            "redacted_error_state": self.redacted_error_state,
            "created_at": self.created_at,
        }
        payload["receipt_hash"] = _hash_payload(payload)
        return payload


@dataclass(frozen=True)
class ProviderResultEnvelope:
    status: str
    task_id: str
    task_kind: str
    normalized_result: dict[str, Any] | None
    semantic_result_present: bool
    validation_errors: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    invocation_receipt: ProviderInvocationReceipt

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "task_id": self.task_id,
            "task_kind": self.task_kind,
            "normalized_result": self.normalized_result,
            "semantic_result_present": self.semantic_result_present,
            "validation_errors": list(self.validation_errors),
            "provenance_refs": list(self.provenance_refs),
            "invocation_receipt": self.invocation_receipt.as_dict(),
        }


class ProviderAdapter(Protocol):
    profile: ProviderCapabilityProfile

    def invoke(self, task: ProviderCognitiveTask) -> dict[str, Any]:
        """Return provider-specific raw output.

        Expected raw shape is deliberately small and adapter-normalized:
        {"result": dict, "usage": dict, "provenance_refs": list[str]}.
        """


class ProviderTaskRouter:
    """Routes provider cognitive tasks through bounded adapters."""

    def __init__(self, adapters: list[ProviderAdapter]):
        self.adapters = list(adapters)

    def route(self, task: ProviderCognitiveTask) -> ProviderResultEnvelope:
        attempted: list[str] = []
        last_error = ""
        for adapter in self.adapters:
            profile = adapter.profile
            if not profile.supports(task):
                continue
            attempted.append(profile.provider_id)
            try:
                raw = adapter.invoke(task)
            except Exception as exc:  # provider boundary: preserve typed failure, do not fabricate result
                last_error = _redact_error(exc)
                continue
            result = raw.get("result")
            usage = raw.get("usage") or {}
            provenance = tuple(raw.get("provenance_refs") or [])
            errors = tuple(self._validate_result(task.expected_schema, result))
            status = STATUS_COMPLETED if not errors else STATUS_VALIDATION_FAILED
            fallback = ProviderFallbackDecision(
                "selected_provider",
                "provider_result_normalized" if not errors else "provider_result_failed_runtime_validation",
                tuple(attempted),
                profile.provider_id,
            )
            receipt = ProviderInvocationReceipt(
                task_id=task.task_id,
                idempotency_key=task.idempotency_key,
                provider_id=profile.provider_id,
                model_id=profile.model_id,
                input_hash=task.contract_hash(),
                output_hash=_hash_payload(result),
                token_usage=usage,
                timeout_seconds=task.timeout_seconds,
                retry_count=max(0, len(attempted) - 1),
                fallback_decision=fallback,
            )
            return ProviderResultEnvelope(
                status=status,
                task_id=task.task_id,
                task_kind=task.task_kind,
                normalized_result=result if isinstance(result, dict) else None,
                semantic_result_present=status == STATUS_COMPLETED,
                validation_errors=errors,
                provenance_refs=provenance,
                invocation_receipt=receipt,
            )
        fallback = ProviderFallbackDecision(
            "provider_unavailable",
            "no_adapter_returned_valid_provider_output",
            tuple(attempted),
        )
        receipt = ProviderInvocationReceipt(
            task_id=task.task_id,
            idempotency_key=task.idempotency_key,
            provider_id="none",
            model_id="none",
            input_hash=task.contract_hash(),
            output_hash="",
            token_usage={},
            timeout_seconds=task.timeout_seconds,
            retry_count=len(attempted),
            fallback_decision=fallback,
            redacted_error_state=last_error,
        )
        return ProviderResultEnvelope(
            status=STATUS_PROVIDER_UNAVAILABLE,
            task_id=task.task_id,
            task_kind=task.task_kind,
            normalized_result=None,
            semantic_result_present=False,
            validation_errors=("provider_unavailable",),
            provenance_refs=(),
            invocation_receipt=receipt,
        )

    @staticmethod
    def _validate_result(expected_schema: dict[str, Any], result: Any) -> list[str]:
        if not isinstance(result, dict):
            return ["provider_result_not_object"]
        errors = []
        for field_name in expected_schema.get("required", []):
            if field_name not in result:
                errors.append(f"missing_required_field:{field_name}")
        properties = expected_schema.get("properties") or {}
        for field_name, spec in properties.items():
            if field_name not in result:
                continue
            expected_type = spec.get("type")
            if expected_type == "array" and not isinstance(result[field_name], list):
                errors.append(f"field_type_mismatch:{field_name}:array")
            if expected_type == "object" and not isinstance(result[field_name], dict):
                errors.append(f"field_type_mismatch:{field_name}:object")
            if expected_type == "string" and not isinstance(result[field_name], str):
                errors.append(f"field_type_mismatch:{field_name}:string")
            if expected_type == "number" and not isinstance(result[field_name], (int, float)):
                errors.append(f"field_type_mismatch:{field_name}:number")
        return errors
