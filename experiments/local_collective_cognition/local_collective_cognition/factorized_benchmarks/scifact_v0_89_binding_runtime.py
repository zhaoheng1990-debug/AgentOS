"""Claim-atom binding, isolated challenge, and veto compilation runtimes."""

from __future__ import annotations

from typing import Any, Callable

from agentos_kernel import ProviderTaskRouter

from ..selection_retention_fresh_provider_helpers import call_record, failed_call
from .claim_atom_binding import (
    build_claim_atom_binding_task,
    validate_claim_atom_binding,
)
from .evidence_binding_challenge import (
    build_binding_challenge_task,
    validate_binding_challenge,
)
from .kernel_binding_veto import compile_binding_veto_candidate
from .scifact_v0_89_runtime_common import (
    finalize_run,
    validate_source_run,
    validated_public_panel,
)


def run_claim_atom_binding_panel(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    evidence_run: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    return _run_evidence_group_role(
        panel=panel,
        preregistration=preregistration,
        evidence_run=evidence_run,
        adapter=adapter,
        runtime_version="scifact_claim_atom_binding_runtime_v0_89",
        arm_id="A1_CLAIM_ATOM_BINDING",
        task_builder=build_claim_atom_binding_task,
        receipt_validator=validate_claim_atom_binding,
    )


def run_binding_challenge_panel(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    evidence_run: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    return _run_evidence_group_role(
        panel=panel,
        preregistration=preregistration,
        evidence_run=evidence_run,
        adapter=adapter,
        runtime_version="scifact_binding_challenge_runtime_v0_89",
        arm_id="A1_BINDING_CHALLENGER",
        task_builder=build_binding_challenge_task,
        receipt_validator=validate_binding_challenge,
    )


def compile_binding_veto_panel(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    evidence_run: dict[str, Any],
    scope_run: dict[str, Any],
    binding_run: dict[str, Any],
    challenge_run: dict[str, Any],
) -> dict[str, Any]:
    public_panel = validated_public_panel(panel, preregistration)
    expected = (
        (evidence_run, "SHARED_EVIDENCE_SET"),
        (scope_run, "A0_FROZEN_V0_88"),
        (binding_run, "A1_CLAIM_ATOM_BINDING"),
        (challenge_run, "A1_BINDING_CHALLENGER"),
    )
    for run, arm in expected:
        validate_source_run(run, panel=panel, expected_arm=arm)
    candidates, failures = {}, []
    for public_case in public_panel["cases"]:
        case_id = public_case["case_id"]
        values = {
            "evidence": evidence_run["receipts"].get(case_id),
            "scope": scope_run["receipts"].get(case_id),
            "binding": binding_run["receipts"].get(case_id),
            "challenge": challenge_run["receipts"].get(case_id),
        }
        missing = sorted(key for key, value in values.items() if value is None)
        if missing:
            failures.append({
                "role": "A1_BINDING_VETO_COMPILER",
                "case_id": case_id,
                "status": "UPSTREAM_RECEIPT_UNAVAILABLE",
                "missing_sources": missing,
                "token_usage": {},
                "task_id": "",
            })
            continue
        candidates[case_id] = compile_binding_veto_candidate(
            public_case=public_case,
            evidence_receipt=values["evidence"],
            scope_receipt=values["scope"],
            binding_receipt=values["binding"],
            challenge_receipt=values["challenge"],
        )
    return finalize_run(
        runtime_version="scifact_binding_veto_compilation_runtime_v0_89",
        arm_id="A1_BINDING_VETO",
        panel=panel,
        public_panel=public_panel,
        preregistration=preregistration,
        provider_id="NO_PROVIDER_MECHANICAL_COMPILATION",
        model_id="NONE",
        calls=[],
        receipts={},
        candidates=candidates,
        failures=failures,
        sources={
            "binding": binding_run["run_hash"],
            "challenge": challenge_run["run_hash"],
            "evidence": evidence_run["run_hash"],
            "scope": scope_run["run_hash"],
        },
    )


def _run_evidence_group_role(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    evidence_run: dict[str, Any],
    adapter: Any,
    runtime_version: str,
    arm_id: str,
    task_builder: Callable[..., Any],
    receipt_validator: Callable[..., list[str]],
) -> dict[str, Any]:
    public_panel = validated_public_panel(panel, preregistration)
    validate_source_run(
        evidence_run,
        panel=panel,
        expected_arm="SHARED_EVIDENCE_SET",
    )
    calls, receipts, failures = [], {}, []
    for public_case in public_panel["cases"]:
        case_id = public_case["case_id"]
        evidence_receipt = evidence_run["receipts"].get(case_id)
        if evidence_receipt is None:
            failures.append({
                "role": arm_id,
                "case_id": case_id,
                "status": "UPSTREAM_EVIDENCE_SET_UNAVAILABLE",
                "token_usage": {},
                "task_id": "",
            })
            continue
        task = task_builder(
            public_case=public_case,
            evidence_receipt=evidence_receipt,
            adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = call_record(arm_id, case_id, task, envelope)
        calls.append(call)
        if envelope.status != "COMPLETED":
            failures.append(failed_call(call, envelope))
            continue
        receipt = envelope.normalized_result
        contract_failures = receipt_validator(
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
    return finalize_run(
        runtime_version=runtime_version,
        arm_id=arm_id,
        panel=panel,
        public_panel=public_panel,
        preregistration=preregistration,
        provider_id=adapter.profile.provider_id,
        model_id=adapter.profile.model_id,
        calls=calls,
        receipts=receipts,
        candidates={},
        failures=failures,
        sources={"evidence": evidence_run["run_hash"]},
    )
