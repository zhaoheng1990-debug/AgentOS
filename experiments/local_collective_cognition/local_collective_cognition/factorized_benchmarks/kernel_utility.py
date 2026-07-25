"""Deterministic no-write compilation of semantic warrants into candidate states."""

from __future__ import annotations

from typing import Any

from ..provider_telemetry import hash_payload

COMPILER_VERSION = "kernel_warrant_utility_compiler_v0_87"


def compile_warrant_candidate(
    *,
    public_case: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    state = receipt["claim_state"]
    if (
        state == "UNCERTAIN"
        or receipt["uncertainty_state"] == "MATERIAL_UNCERTAINTY"
    ):
        action = "ABSTAIN"
    elif state == "SUPPORTED":
        action = "OPEN_SUPPORTED_CANDIDATE"
    elif state == "REFUTED":
        action = "OPEN_REFUTATION_CANDIDATE"
    else:
        action = "RETAIN_UNRESOLVED"
    value = {
        "compiler_version": COMPILER_VERSION,
        "case_id": public_case["case_id"],
        "source_public_case_hash": hash_payload(public_case),
        "source_receipt_hash": hash_payload(receipt),
        "semantic_state": state,
        "runtime_action": action,
        "selected_unit_ids": list(receipt["selected_unit_ids"]),
        "provider_action_authority": False,
        "candidate_only": True,
        "promotion_authorized": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "rollback_required_before_any_future_write": True,
    }
    return {**value, "candidate_hash": hash_payload(value)}
