"""Provider-backed semantic warrant runtime for the frozen v0.87 panel."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderTaskRouter

from ..provider_telemetry import hash_payload
from ..selection_retention_fresh_provider_helpers import call_record, failed_call
from .kernel_utility import compile_warrant_candidate
from .scifact_v0_87_holdout import (
    public_holdout,
    validate_holdout,
    validate_preregistration,
)
from .semantic_warrant import build_warrant_task, validate_warrant


def run_warrant_panel(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    validate_holdout(panel)
    validate_preregistration(preregistration, panel=panel)
    public_panel = public_holdout(panel)
    calls = []
    receipts = {}
    candidates = {}
    failures = []
    for public_case in public_panel["cases"]:
        case_id = public_case["case_id"]
        task = build_warrant_task(public_case=public_case, adapter=adapter)
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = call_record("SEMANTIC_WARRANT", case_id, task, envelope)
        calls.append(call)
        if envelope.status != "COMPLETED":
            failures.append(failed_call(call, envelope))
            continue
        receipt = envelope.normalized_result
        contract_failures = validate_warrant(
            receipt,
            public_case=public_case,
        )
        if contract_failures:
            failures.append({
                **call,
                "contract_failures": contract_failures,
                "invalid_receipt": receipt,
            })
            continue
        receipts[case_id] = receipt
        candidates[case_id] = compile_warrant_candidate(
            public_case=public_case,
            receipt=receipt,
        )
    value = {
        "runtime_version": "scifact_semantic_warrant_runtime_v0_87",
        "source_holdout_hash": panel["artifact_hash"],
        "source_public_holdout_hash": public_panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "receipts": receipts,
        "compiled_candidates": candidates,
        "failures": failures,
        "private_reference_exposed_to_provider": False,
        "provider_action_authority": False,
        "candidate_only": True,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**value, "run_hash": hash_payload(value)}
