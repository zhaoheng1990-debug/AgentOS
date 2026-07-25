"""Descriptive audit separating semantic vetoes from fail-closed cases."""

from __future__ import annotations

from typing import Any

from ..provider_telemetry import hash_payload


def build_binding_veto_posthoc(
    *,
    panel: dict[str, Any],
    scope_run: dict[str, Any],
    binding_run: dict[str, Any],
    challenge_run: dict[str, Any],
    candidate_run: dict[str, Any],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    if evaluation.get("source_holdout_hash") != panel.get("artifact_hash"):
        raise ValueError("scifact_v0_89_posthoc_panel_mismatch")
    expected_hashes = {
        "A0_FROZEN_V0_88": scope_run["run_hash"],
        "A1_CLAIM_ATOM_BINDING": binding_run["run_hash"],
        "A1_BINDING_CHALLENGER": challenge_run["run_hash"],
        "A1_BINDING_VETO": candidate_run["run_hash"],
    }
    for arm, run_hash in expected_hashes.items():
        if evaluation["source_run_hashes"].get(arm) != run_hash:
            raise ValueError(f"scifact_v0_89_posthoc_run_mismatch:{arm}")
    baseline_scores = {
        row["case_id"]: row for row in evaluation["baseline"]["case_scores"]
    }
    binding_failure_ids = {
        failure["case_id"] for failure in binding_run["failures"]
    }
    rows = []
    for item in panel["cases"]:
        case_id = item["public_case"]["case_id"]
        baseline = baseline_scores[case_id]
        candidate = candidate_run["compiled_candidates"].get(case_id)
        if candidate is None:
            closure = "UPSTREAM_BINDING_FAILURE_FAIL_CLOSED"
            reasons = []
            valid_semantic_veto = False
        elif candidate["veto_applied"]:
            closure = "VALID_RECEIPT_VETO"
            reasons = [
                reason
                for decision in candidate["group_decisions"]
                for reason in decision["veto_reasons"]
            ]
            valid_semantic_veto = True
        elif baseline["strong_candidate"]:
            closure = "STRONG_CANDIDATE_RETAINED"
            reasons = []
            valid_semantic_veto = False
        else:
            closure = "NON_STRONG_BASELINE_PRESERVED"
            reasons = []
            valid_semantic_veto = False
        contradiction_reason = any(
            reason.startswith("PRIMARY_ATOM:")
            and reason.endswith(":CONTRADICTED")
            for reason in reasons
        )
        rows.append({
            "case_id": case_id,
            "gold_state": baseline["gold_state"],
            "baseline_action": baseline["runtime_action"],
            "baseline_correct": baseline["label_correct"],
            "baseline_harmful_strong": baseline[
                "harmful_strong_candidate"
            ],
            "binding_receipt_valid": case_id not in binding_failure_ids,
            "closure_class": closure,
            "valid_semantic_veto": valid_semantic_veto,
            "veto_reasons": sorted(set(reasons)),
            "contradicted_atom_veto": contradiction_reason,
            "refutation_polarity_asymmetry": (
                baseline["runtime_action"]
                == "OPEN_REFUTATION_CANDIDATE"
                and contradiction_reason
            ),
        })
    valid_vetoes = [row for row in rows if row["valid_semantic_veto"]]
    failure_rows = [
        row
        for row in rows
        if row["closure_class"]
        == "UPSTREAM_BINDING_FAILURE_FAIL_CLOSED"
    ]
    value = {
        "audit_version": "scifact_binding_veto_posthoc_v0_89",
        "source_holdout_hash": panel["artifact_hash"],
        "source_scope_run_hash": scope_run["run_hash"],
        "source_binding_run_hash": binding_run["run_hash"],
        "source_challenge_run_hash": challenge_run["run_hash"],
        "source_candidate_run_hash": candidate_run["run_hash"],
        "source_evaluation_hash": evaluation["artifact_hash"],
        "provider_binding_failure_count": len(binding_run["failures"]),
        "downstream_propagated_failure_count": len(
            candidate_run["failures"]
        ),
        "unique_failed_case_count": len(binding_failure_ids),
        "valid_semantic_veto_count": len(valid_vetoes),
        "valid_semantic_correct_harm_veto_count": sum(
            row["baseline_harmful_strong"] for row in valid_vetoes
        ),
        "valid_semantic_false_veto_count": sum(
            row["baseline_correct"] for row in valid_vetoes
        ),
        "fail_closed_harmful_baseline_count": sum(
            row["baseline_harmful_strong"] for row in failure_rows
        ),
        "refutation_polarity_asymmetry_count": sum(
            row["refutation_polarity_asymmetry"] for row in rows
        ),
        "descriptive_rows": rows,
        "descriptive_posthoc_only": True,
        "preregistered_gate_changed": False,
        "gate_authority": False,
        "same_version_retuning_allowed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}
