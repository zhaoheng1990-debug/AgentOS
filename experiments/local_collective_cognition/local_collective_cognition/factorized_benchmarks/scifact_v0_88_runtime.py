"""Paired direct and evidence-scope runtimes for v0.88."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderTaskRouter

from ..provider_telemetry import hash_payload
from ..selection_retention_fresh_provider_helpers import call_record, failed_call
from .claim_scope_receipt import (
    build_claim_scope_task,
    validate_claim_scope,
)
from .evidence_set_receipt import (
    build_evidence_set_task,
    validate_evidence_set,
)
from .kernel_scope_utility import compile_evidence_scope_candidate
from .kernel_utility import compile_warrant_candidate
from .scifact_v0_88_holdout import (
    public_holdout,
    validate_holdout,
    validate_preregistration,
)
from .semantic_warrant import build_warrant_task, validate_warrant


def run_direct_baseline(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    public_panel = _validated_public_panel(panel, preregistration)
    calls, receipts, candidates, failures = [], {}, {}, []
    for public_case in public_panel["cases"]:
        case_id = public_case["case_id"]
        task = build_warrant_task(public_case=public_case, adapter=adapter)
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = call_record("A0_DIRECT_WARRANT", case_id, task, envelope)
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
    return _finalize_run(
        runtime_version="scifact_direct_baseline_runtime_v0_88",
        arm_id="A0_DIRECT_WARRANT",
        panel=panel,
        public_panel=public_panel,
        preregistration=preregistration,
        adapter=adapter,
        calls=calls,
        receipts=receipts,
        candidates=candidates,
        failures=failures,
    )


def run_evidence_set_panel(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    public_panel = _validated_public_panel(panel, preregistration)
    calls, receipts, failures = [], {}, []
    for public_case in public_panel["cases"]:
        case_id = public_case["case_id"]
        task = build_evidence_set_task(
            public_case=public_case,
            adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = call_record("A1_EVIDENCE_SET", case_id, task, envelope)
        calls.append(call)
        if envelope.status != "COMPLETED":
            failures.append(failed_call(call, envelope))
            continue
        receipt = envelope.normalized_result
        contract_failures = validate_evidence_set(
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
    return _finalize_run(
        runtime_version="scifact_evidence_set_runtime_v0_88",
        arm_id="A1_EVIDENCE_SET",
        panel=panel,
        public_panel=public_panel,
        preregistration=preregistration,
        adapter=adapter,
        calls=calls,
        receipts=receipts,
        candidates={},
        failures=failures,
    )


def run_claim_scope_panel(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    evidence_run: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    public_panel = _validated_public_panel(panel, preregistration)
    if evidence_run.get("source_holdout_hash") != panel["artifact_hash"]:
        raise ValueError("scifact_v0_88_evidence_run_panel_mismatch")
    calls, receipts, candidates, failures = [], {}, {}, []
    for public_case in public_panel["cases"]:
        case_id = public_case["case_id"]
        evidence_receipt = evidence_run["receipts"].get(case_id)
        if evidence_receipt is None:
            failures.append({
                "role": "A1_CLAIM_SCOPE",
                "case_id": case_id,
                "status": "UPSTREAM_EVIDENCE_SET_UNAVAILABLE",
                "token_usage": {},
                "task_id": "",
            })
            continue
        task = build_claim_scope_task(
            public_case=public_case,
            evidence_receipt=evidence_receipt,
            adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = call_record("A1_CLAIM_SCOPE", case_id, task, envelope)
        calls.append(call)
        if envelope.status != "COMPLETED":
            failures.append(failed_call(call, envelope))
            continue
        receipt = envelope.normalized_result
        contract_failures = validate_claim_scope(
            receipt,
            public_case=public_case,
            evidence_receipt=evidence_receipt,
        )
        if contract_failures:
            failures.append({
                **call,
                "contract_failures": contract_failures,
                "invalid_receipt": receipt,
            })
            continue
        receipts[case_id] = receipt
        candidates[case_id] = compile_evidence_scope_candidate(
            public_case=public_case,
            evidence_receipt=evidence_receipt,
            scope_receipt=receipt,
        )
    value = _finalize_run(
        runtime_version="scifact_claim_scope_runtime_v0_88",
        arm_id="A1_CLAIM_SCOPE",
        panel=panel,
        public_panel=public_panel,
        preregistration=preregistration,
        adapter=adapter,
        calls=calls,
        receipts=receipts,
        candidates=candidates,
        failures=failures,
    )
    value_without_hash = {
        key: item for key, item in value.items() if key != "run_hash"
    }
    value_without_hash["source_evidence_run_hash"] = evidence_run["run_hash"]
    return {
        **value_without_hash,
        "run_hash": hash_payload(value_without_hash),
    }


def _validated_public_panel(
    panel: dict[str, Any],
    preregistration: dict[str, Any],
) -> dict[str, Any]:
    validate_holdout(panel)
    validate_preregistration(preregistration, panel=panel)
    return public_holdout(panel)


def _finalize_run(
    *,
    runtime_version: str,
    arm_id: str,
    panel: dict[str, Any],
    public_panel: dict[str, Any],
    preregistration: dict[str, Any],
    adapter: Any,
    calls: list[dict[str, Any]],
    receipts: dict[str, Any],
    candidates: dict[str, Any],
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    value = {
        "runtime_version": runtime_version,
        "arm_id": arm_id,
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
