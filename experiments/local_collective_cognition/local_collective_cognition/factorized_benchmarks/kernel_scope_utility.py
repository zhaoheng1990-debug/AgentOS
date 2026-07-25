"""No-write Kernel compiler for evidence-set and claim-scope receipts."""

from __future__ import annotations

from typing import Any

from ..provider_telemetry import hash_payload

COMPILER_VERSION = "kernel_evidence_scope_utility_compiler_v0_88"
ACTIONABLE_RELATIONS = {"DIRECTLY_RESOLVES", "OVERTURNS"}


def compile_evidence_scope_candidate(
    *,
    public_case: dict[str, Any],
    evidence_receipt: dict[str, Any],
    scope_receipt: dict[str, Any],
) -> dict[str, Any]:
    state = scope_receipt["claim_state"]
    assessments = {
        value["group_id"]: value
        for value in scope_receipt["group_assessments"]
    }
    target_relation = {
        "SUPPORTED": "SUPPORTS",
        "REFUTED": "REFUTES",
    }.get(state)
    selected_group_ids = []
    selected_unit_ids = []
    if target_relation is not None:
        for group in evidence_receipt["evidence_groups"]:
            assessment = assessments[group["group_id"]]
            if (
                group["relation"] == target_relation
                and assessment["claim_relation"] in ACTIONABLE_RELATIONS
            ):
                selected_group_ids.append(group["group_id"])
                selected_unit_ids.extend(group["unit_ids"])
    material_conflict = (
        scope_receipt["exception_effect"] == "MATERIAL_SCOPE_CONFLICT"
        or state == "UNCERTAIN"
    )
    if material_conflict:
        action = "ABSTAIN"
    elif state == "NOT_ENOUGH_INFO":
        action = "RETAIN_UNRESOLVED"
    elif state == "SUPPORTED" and selected_group_ids:
        action = "OPEN_SUPPORTED_CANDIDATE"
    elif state == "REFUTED" and selected_group_ids:
        action = "OPEN_REFUTATION_CANDIDATE"
    else:
        action = "ABSTAIN"
    value = {
        "compiler_version": COMPILER_VERSION,
        "case_id": public_case["case_id"],
        "source_public_case_hash": hash_payload(public_case),
        "source_evidence_set_hash": hash_payload(evidence_receipt),
        "source_scope_receipt_hash": hash_payload(scope_receipt),
        "semantic_state": state,
        "runtime_action": action,
        "selected_group_ids": selected_group_ids,
        "selected_unit_ids": list(dict.fromkeys(selected_unit_ids)),
        "material_scope_conflict": material_conflict,
        "provider_action_authority": False,
        "candidate_only": True,
        "promotion_authorized": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "rollback_required_before_any_future_write": True,
    }
    return {**value, "candidate_hash": hash_payload(value)}
