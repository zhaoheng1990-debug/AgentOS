"""Deterministic veto-only compiler for claim-atom binding evidence."""

from __future__ import annotations

from typing import Any

from ..provider_telemetry import hash_payload
from .kernel_scope_utility import compile_evidence_scope_candidate

COMPILER_VERSION = "kernel_claim_atom_binding_veto_compiler_v0_89"
STRONG_ACTIONS = {
    "OPEN_SUPPORTED_CANDIDATE",
    "OPEN_REFUTATION_CANDIDATE",
}
DIRECT_STATES = {"DIRECT_EXPLICIT", "DIRECT_COMPOSITIONAL"}
BOUND_STATES = {"BOUND_EXPLICIT", "BOUND_COMPOSITIONAL"}


def compile_binding_veto_candidate(
    *,
    public_case: dict[str, Any],
    evidence_receipt: dict[str, Any],
    scope_receipt: dict[str, Any],
    binding_receipt: dict[str, Any],
    challenge_receipt: dict[str, Any],
) -> dict[str, Any]:
    baseline = compile_evidence_scope_candidate(
        public_case=public_case,
        evidence_receipt=evidence_receipt,
        scope_receipt=scope_receipt,
    )
    binding_map = {
        item["group_id"]: item
        for item in binding_receipt["group_bindings"]
    }
    challenge_map = {
        item["group_id"]: item
        for item in challenge_receipt["group_challenges"]
    }
    group_map = {
        item["group_id"]: item
        for item in evidence_receipt["evidence_groups"]
    }
    group_decisions = []
    retained_groups = []
    expected_relation = {
        "SUPPORTED": "SUPPORTS",
        "REFUTED": "REFUTES",
    }.get(baseline["semantic_state"])
    for group_id in baseline["selected_group_ids"]:
        binding = binding_map[group_id]
        challenge = challenge_map[group_id]
        reasons = _veto_reasons(
            binding,
            challenge,
            expected_relation=expected_relation,
        )
        retained = not reasons
        if retained:
            retained_groups.append(group_id)
        group_decisions.append({
            "group_id": group_id,
            "retained": retained,
            "veto_reasons": reasons,
        })

    baseline_strong = baseline["runtime_action"] in STRONG_ACTIONS
    if baseline_strong and retained_groups:
        semantic_state = baseline["semantic_state"]
        action = baseline["runtime_action"]
        selected_units = [
            unit_id
            for group_id in retained_groups
            for unit_id in group_map[group_id]["unit_ids"]
        ]
    elif baseline_strong:
        semantic_state = "UNCERTAIN"
        action = "ABSTAIN"
        selected_units = []
    else:
        semantic_state = baseline["semantic_state"]
        action = baseline["runtime_action"]
        selected_units = baseline["selected_unit_ids"]

    value = {
        "compiler_version": COMPILER_VERSION,
        "case_id": public_case["case_id"],
        "source_public_case_hash": hash_payload(public_case),
        "source_evidence_set_hash": hash_payload(evidence_receipt),
        "source_scope_receipt_hash": hash_payload(scope_receipt),
        "source_binding_receipt_hash": hash_payload(binding_receipt),
        "source_challenge_receipt_hash": hash_payload(challenge_receipt),
        "source_baseline_candidate_hash": baseline["candidate_hash"],
        "baseline_semantic_state": baseline["semantic_state"],
        "baseline_runtime_action": baseline["runtime_action"],
        "semantic_state": semantic_state,
        "runtime_action": action,
        "selected_group_ids": retained_groups,
        "selected_unit_ids": list(dict.fromkeys(selected_units)),
        "group_decisions": group_decisions,
        "veto_applied": baseline_strong and not retained_groups,
        "veto_only": True,
        "provider_action_authority": False,
        "candidate_only": True,
        "promotion_authorized": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "rollback_required_before_any_future_write": True,
    }
    return {**value, "candidate_hash": hash_payload(value)}


def _veto_reasons(
    binding: dict[str, Any],
    challenge: dict[str, Any],
    *,
    expected_relation: str | None,
) -> list[str]:
    reasons = []
    if binding["relation_to_claim"] != expected_relation:
        reasons.append(
            f"PRIMARY_RELATION:{binding['relation_to_claim']}"
        )
    if binding["directness"] not in DIRECT_STATES:
        reasons.append(f"PRIMARY_DIRECTNESS:{binding['directness']}")
    if binding["unstated_bridge_required"]:
        reasons.append("PRIMARY_UNSTATED_BRIDGE")
    for atom in binding["atom_bindings"]:
        if atom["binding_state"] not in BOUND_STATES:
            reasons.append(
                f"PRIMARY_ATOM:{atom['atom_id']}:{atom['binding_state']}"
            )
    if challenge["verdict"] != "PASS_DIRECT":
        reasons.append(f"CHALLENGER:{challenge['verdict']}")
    if challenge["issue_codes"] != ["NONE"]:
        reasons.extend(
            f"CHALLENGER_ISSUE:{code}"
            for code in challenge["issue_codes"]
        )
    return sorted(set(reasons))
