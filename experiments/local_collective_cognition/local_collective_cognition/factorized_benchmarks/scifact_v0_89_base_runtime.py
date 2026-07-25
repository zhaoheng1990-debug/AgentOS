"""Shared v0.88 evidence and scope path on the fresh v0.89 holdout."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderTaskRouter

from ..selection_retention_fresh_provider_helpers import call_record, failed_call
from .claim_scope_receipt import build_claim_scope_task, validate_claim_scope
from .evidence_set_receipt import build_evidence_set_task, validate_evidence_set
from .kernel_scope_utility import compile_evidence_scope_candidate
from .scifact_v0_89_runtime_common import (
    finalize_run,
    validate_source_run,
    validated_public_panel,
)


def run_evidence_set_panel(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    public_panel = validated_public_panel(panel, preregistration)
    calls, receipts, failures = [], {}, []
    for public_case in public_panel["cases"]:
        case_id = public_case["case_id"]
        task = build_evidence_set_task(
            public_case=public_case,
            adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = call_record("SHARED_EVIDENCE_SET", case_id, task, envelope)
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
    return finalize_run(
        runtime_version="scifact_evidence_set_runtime_v0_89",
        arm_id="SHARED_EVIDENCE_SET",
        panel=panel,
        public_panel=public_panel,
        preregistration=preregistration,
        provider_id=adapter.profile.provider_id,
        model_id=adapter.profile.model_id,
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
    public_panel = validated_public_panel(panel, preregistration)
    validate_source_run(
        evidence_run,
        panel=panel,
        expected_arm="SHARED_EVIDENCE_SET",
    )
    calls, receipts, candidates, failures = [], {}, {}, []
    for public_case in public_panel["cases"]:
        case_id = public_case["case_id"]
        evidence_receipt = evidence_run["receipts"].get(case_id)
        if evidence_receipt is None:
            failures.append(_upstream_failure(case_id))
            continue
        task = build_claim_scope_task(
            public_case=public_case,
            evidence_receipt=evidence_receipt,
            adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = call_record("A0_SHARED_CLAIM_SCOPE", case_id, task, envelope)
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
    return finalize_run(
        runtime_version="scifact_claim_scope_baseline_runtime_v0_89",
        arm_id="A0_FROZEN_V0_88",
        panel=panel,
        public_panel=public_panel,
        preregistration=preregistration,
        provider_id=adapter.profile.provider_id,
        model_id=adapter.profile.model_id,
        calls=calls,
        receipts=receipts,
        candidates=candidates,
        failures=failures,
        sources={"evidence": evidence_run["run_hash"]},
    )


def _upstream_failure(case_id: str) -> dict[str, Any]:
    return {
        "role": "A0_SHARED_CLAIM_SCOPE",
        "case_id": case_id,
        "status": "UPSTREAM_EVIDENCE_SET_UNAVAILABLE",
        "token_usage": {},
        "task_id": "",
    }
