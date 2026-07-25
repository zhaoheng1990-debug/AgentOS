"""Paired safety and sentence evaluation for binding-veto v0.89."""

from __future__ import annotations

from typing import Any

from ..provider_telemetry import hash_payload
from .scifact_v0_89_holdout import (
    validate_holdout,
    validate_preregistration,
)

STRONG_ACTIONS = {
    "OPEN_SUPPORTED_CANDIDATE",
    "OPEN_REFUTATION_CANDIDATE",
}


def evaluate_binding_veto_run(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    evidence_run: dict[str, Any],
    scope_run: dict[str, Any],
    binding_run: dict[str, Any],
    challenge_run: dict[str, Any],
    candidate_run: dict[str, Any],
) -> dict[str, Any]:
    validate_holdout(panel)
    validate_preregistration(preregistration, panel=panel)
    runs = (
        evidence_run,
        scope_run,
        binding_run,
        challenge_run,
        candidate_run,
    )
    if any(
        run.get("source_holdout_hash") != panel["artifact_hash"]
        for run in runs
    ):
        raise ValueError("scifact_v0_89_run_panel_mismatch")
    baseline = _score_arm(panel, scope_run)
    candidate = _score_arm(panel, candidate_run)
    pair = _paired_diagnostics(
        baseline["case_scores"],
        candidate["case_scores"],
    )
    provider_runs = (
        evidence_run,
        scope_run,
        binding_run,
        challenge_run,
    )
    all_calls = [
        call for run in provider_runs for call in run["task_calls"]
    ]
    all_failures = [
        failure for run in runs for failure in run["failures"]
    ]
    operational = preregistration["operational_gate"]
    semantic = preregistration["semantic_gate"]
    harm_reduction_required = (
        baseline["harmful_strong_candidate_count"] > 0
    )
    harm_reduction = (
        baseline["harmful_strong_candidate_count"]
        - candidate["harmful_strong_candidate_count"]
    )
    conditions = {
        "valid_evidence_receipts": (
            len(evidence_run["receipts"])
            >= operational["valid_evidence_receipts_min"]
        ),
        "valid_scope_receipts": (
            len(scope_run["receipts"])
            >= operational["valid_scope_receipts_min"]
        ),
        "valid_binding_receipts": (
            len(binding_run["receipts"])
            >= operational["valid_binding_receipts_min"]
        ),
        "valid_challenge_receipts": (
            len(challenge_run["receipts"])
            >= operational["valid_challenge_receipts_min"]
        ),
        "contract_failures": (
            len(all_failures) <= operational["contract_failures_max"]
        ),
        "physical_attempts": (
            _physical_attempts(all_calls)
            <= operational["physical_attempts_max"]
        ),
        "token_ceiling": (
            _token_count(all_calls)
            <= operational["hard_total_token_ceiling"]
        ),
        "candidate_zero_harm": (
            candidate["harmful_strong_candidate_count"]
            <= semantic["candidate_harmful_strong_candidates_max"]
        ),
        "candidate_harm_not_above_baseline": (
            candidate["harmful_strong_candidate_count"]
            <= baseline["harmful_strong_candidate_count"]
        ),
        "conditional_harm_reduction": (
            not harm_reduction_required
            or harm_reduction
            >= semantic["conditional_harm_reduction_min"]
        ),
        "candidate_strong_precision": (
            candidate["strong_candidate_precision"]
            >= semantic["candidate_strong_precision_min"]
        ),
        "correct_strong_retention": (
            pair["correct_strong_retention"]
            >= semantic["correct_strong_retention_min"]
        ),
        "sentence_precision_not_below_baseline": (
            candidate["sentence_precision"]
            >= baseline["sentence_precision"]
        ),
        "sentence_f1_delta": (
            candidate["sentence_f1"] - baseline["sentence_f1"]
            >= semantic["sentence_f1_delta_min"]
        ),
        "label_accuracy_delta": (
            candidate["label_accuracy"] - baseline["label_accuracy"]
            >= semantic["label_accuracy_delta_min"]
        ),
        "candidate_abstention_rate": (
            candidate["abstention_rate"]
            <= semantic["candidate_abstention_rate_max"]
        ),
        "veto_only_no_promotion": pair["promotion_count"] == 0,
        "no_write_boundary": all(
            run.get("core_write_allowed") is False
            and run.get("retention_write_allowed") is False
            and run.get("candidate_only") is True
            for run in runs
        ),
    }
    value = {
        "evaluation_version": "scifact_binding_veto_evaluation_v0_89",
        "source_holdout_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_run_hashes": {
            run["arm_id"]: run["run_hash"] for run in runs
        },
        "baseline": baseline,
        "candidate": candidate,
        "paired": pair,
        "harm_reduction_required": harm_reduction_required,
        "harmful_strong_candidate_reduction": harm_reduction,
        "sentence_precision_delta": (
            candidate["sentence_precision"] - baseline["sentence_precision"]
        ),
        "sentence_f1_delta": (
            candidate["sentence_f1"] - baseline["sentence_f1"]
        ),
        "label_accuracy_delta": (
            candidate["label_accuracy"] - baseline["label_accuracy"]
        ),
        "failure_count": len(all_failures),
        "physical_attempt_count": _physical_attempts(all_calls),
        "physical_total_tokens": _token_count(all_calls),
        "gate_conditions": conditions,
        "development_decision": (
            "PASS_V0_89_BINDING_VETO_DEVELOPMENT_GATE"
            if all(conditions.values())
            else "REJECT_V0_89_BINDING_VETO_DEVELOPMENT_GATE"
        ),
        "external_acceptance_eligible": False,
        "same_version_retuning_allowed": False,
        "candidate_acceptance_authorized": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def _score_arm(
    panel: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    rows = []
    for item in panel["cases"]:
        case_id = item["public_case"]["case_id"]
        rows.append(_score_case(
            case_id=case_id,
            private=item["private_reference"],
            candidate=run["compiled_candidates"].get(case_id),
        ))
    correct = sum(row["correct_sentence_count"] for row in rows)
    predicted = sum(row["predicted_sentence_count"] for row in rows)
    gold = sum(row["gold_sentence_count"] for row in rows)
    precision = correct / predicted if predicted else 0.0
    recall = correct / gold if gold else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    strong = [row for row in rows if row["strong_candidate"]]
    count = len(rows)
    return {
        "case_count": count,
        "valid_candidate_count": sum(row["candidate_valid"] for row in rows),
        "label_accuracy": sum(row["label_correct"] for row in rows) / count,
        "strong_candidate_count": len(strong),
        "strong_candidate_precision": (
            sum(row["label_correct"] for row in strong) / len(strong)
            if strong else 1.0
        ),
        "correct_sentence_count": correct,
        "predicted_sentence_count": predicted,
        "gold_sentence_count": gold,
        "sentence_precision": precision,
        "sentence_recall": recall,
        "sentence_f1": f1,
        "overselected_sentence_count": sum(
            row["overselected_sentence_count"] for row in rows
        ),
        "unrecovered_gold_sentence_count": sum(
            row["unrecovered_gold_sentence_count"] for row in rows
        ),
        "harmful_strong_candidate_count": sum(
            row["harmful_strong_candidate"] for row in rows
        ),
        "abstention_rate": sum(
            row["runtime_action"] == "ABSTAIN" for row in rows
        ) / count,
        "case_scores": rows,
    }


def _score_case(
    *,
    case_id: str,
    private: dict[str, Any],
    candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    gold_state = private["expected_state"]
    gold_sets = [
        set(values)
        for values in private["metadata"].get("gold_rationale_sets", [])
    ]
    gold_union = set().union(*gold_sets) if gold_sets else set()
    if candidate is None:
        return _empty_case(case_id, gold_state, len(gold_union))
    predicted_state = candidate["semantic_state"]
    predicted_units = set(candidate["selected_unit_ids"])
    label_correct = predicted_state == gold_state
    correct = set()
    if label_correct:
        for gold_set in gold_sets:
            if gold_set.issubset(predicted_units):
                correct.update(gold_set)
        correct.intersection_update(predicted_units)
    action = candidate["runtime_action"]
    strong = action in STRONG_ACTIONS
    return {
        "case_id": case_id,
        "candidate_valid": True,
        "gold_state": gold_state,
        "predicted_state": predicted_state,
        "runtime_action": action,
        "label_correct": label_correct,
        "strong_candidate": strong,
        "predicted_sentence_count": len(predicted_units),
        "gold_sentence_count": len(gold_union),
        "correct_sentence_count": len(correct),
        "overselected_sentence_count": len(predicted_units - correct),
        "unrecovered_gold_sentence_count": len(gold_union - correct),
        "harmful_strong_candidate": strong and not label_correct,
    }


def _empty_case(
    case_id: str,
    gold_state: str,
    gold_sentence_count: int,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "candidate_valid": False,
        "gold_state": gold_state,
        "predicted_state": "NO_VALID_CANDIDATE",
        "runtime_action": "ABSTAIN",
        "label_correct": False,
        "strong_candidate": False,
        "predicted_sentence_count": 0,
        "gold_sentence_count": gold_sentence_count,
        "correct_sentence_count": 0,
        "overselected_sentence_count": 0,
        "unrecovered_gold_sentence_count": gold_sentence_count,
        "harmful_strong_candidate": False,
    }


def _paired_diagnostics(
    baseline: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_map = {row["case_id"]: row for row in candidate}
    rows = []
    for base in baseline:
        new = candidate_map[base["case_id"]]
        rows.append({
            "case_id": base["case_id"],
            "baseline_action": base["runtime_action"],
            "candidate_action": new["runtime_action"],
            "baseline_correct": base["label_correct"],
            "candidate_correct": new["label_correct"],
            "vetoed": (
                base["strong_candidate"] and not new["strong_candidate"]
            ),
            "promoted": (
                not base["strong_candidate"] and new["strong_candidate"]
            ),
        })
    baseline_correct_strong = sum(
        row["strong_candidate"] and row["label_correct"] for row in baseline
    )
    retained_correct_strong = sum(
        base["strong_candidate"]
        and base["label_correct"]
        and candidate_map[base["case_id"]]["strong_candidate"]
        for base in baseline
    )
    return {
        "veto_count": sum(row["vetoed"] for row in rows),
        "promotion_count": sum(row["promoted"] for row in rows),
        "correct_harm_veto_count": sum(
            row["vetoed"] and not row["baseline_correct"] for row in rows
        ),
        "false_veto_count": sum(
            row["vetoed"] and row["baseline_correct"] for row in rows
        ),
        "baseline_correct_strong_count": baseline_correct_strong,
        "retained_correct_strong_count": retained_correct_strong,
        "correct_strong_retention": (
            retained_correct_strong / baseline_correct_strong
            if baseline_correct_strong
            else 1.0
        ),
        "case_transitions": rows,
    }


def _token_count(calls: list[dict[str, Any]]) -> int:
    return sum(
        int(call.get("token_usage", {}).get("total_tokens", 0))
        for call in calls
    )


def _physical_attempts(calls: list[dict[str, Any]]) -> int:
    return sum(
        int(call.get("token_usage", {}).get("provider_calls", 1))
        for call in calls
    )
