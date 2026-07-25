"""Paired official-metric evaluation for direct and evidence-scope arms."""

from __future__ import annotations

from typing import Any

from ..provider_telemetry import hash_payload
from .scifact_v0_88_holdout import (
    validate_holdout,
    validate_preregistration,
)


def evaluate_paired_run(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    baseline_run: dict[str, Any],
    evidence_run: dict[str, Any],
    scope_run: dict[str, Any],
) -> dict[str, Any]:
    validate_holdout(panel)
    validate_preregistration(preregistration, panel=panel)
    for run in (baseline_run, evidence_run, scope_run):
        if run.get("source_holdout_hash") != panel["artifact_hash"]:
            raise ValueError("scifact_v0_88_run_panel_mismatch")
    baseline = _score_arm(panel, baseline_run)
    candidate = _score_arm(panel, scope_run)
    sentence_f1_delta = (
        candidate["sentence_f1"] - baseline["sentence_f1"]
    )
    all_calls = (
        baseline_run["task_calls"]
        + evidence_run["task_calls"]
        + scope_run["task_calls"]
    )
    all_failures = (
        baseline_run["failures"]
        + evidence_run["failures"]
        + scope_run["failures"]
    )
    operational = preregistration["operational_gate"]
    semantic = preregistration["semantic_gate"]
    conflict_candidates = [
        candidate_value
        for candidate_value in scope_run["compiled_candidates"].values()
        if candidate_value["material_scope_conflict"]
    ]
    conflict_compliance = (
        sum(
            value["runtime_action"] == "ABSTAIN"
            for value in conflict_candidates
        ) / len(conflict_candidates)
        if conflict_candidates
        else 1.0
    )
    conditions = {
        "valid_baseline_receipts": (
            len(baseline_run["receipts"])
            >= operational["valid_baseline_receipts_min"]
        ),
        "valid_evidence_receipts": (
            len(evidence_run["receipts"])
            >= operational["valid_evidence_receipts_min"]
        ),
        "valid_scope_receipts": (
            len(scope_run["receipts"])
            >= operational["valid_scope_receipts_min"]
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
        "candidate_label_accuracy": (
            candidate["label_accuracy"]
            >= semantic["candidate_label_accuracy_min"]
        ),
        "candidate_sentence_f1": (
            candidate["sentence_f1"]
            >= semantic["candidate_sentence_f1_min"]
        ),
        "paired_sentence_f1_delta": (
            sentence_f1_delta
            >= semantic["paired_sentence_f1_delta_min"]
        ),
        "candidate_zero_harm": (
            candidate["harmful_strong_candidate_count"]
            <= semantic["candidate_harmful_strong_candidates_max"]
        ),
        "candidate_harm_not_above_baseline": (
            candidate["harmful_strong_candidate_count"]
            <= baseline["harmful_strong_candidate_count"]
        ),
        "candidate_abstention_rate": (
            candidate["abstention_rate"]
            <= semantic["candidate_abstention_rate_max"]
        ),
        "scope_conflict_abstention_compliance": (
            conflict_compliance
            >= semantic["scope_conflict_abstention_compliance_min"]
        ),
        "no_write_boundary": all(
            run.get("core_write_allowed") is False
            and run.get("retention_write_allowed") is False
            and run.get("candidate_only") is True
            for run in (baseline_run, evidence_run, scope_run)
        ),
    }
    value = {
        "evaluation_version": "scifact_evidence_scope_evaluation_v0_88",
        "source_holdout_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_run_hashes": {
            "baseline": baseline_run["run_hash"],
            "evidence": evidence_run["run_hash"],
            "scope": scope_run["run_hash"],
        },
        "authoritative_rationale_metric": (
            preregistration["authoritative_rationale_metric"]
        ),
        "baseline": baseline,
        "candidate": candidate,
        "paired_sentence_f1_delta": sentence_f1_delta,
        "scope_conflict_case_count": len(conflict_candidates),
        "scope_conflict_abstention_compliance": conflict_compliance,
        "failure_count": len(all_failures),
        "physical_attempt_count": _physical_attempts(all_calls),
        "physical_total_tokens": _token_count(all_calls),
        "gate_conditions": conditions,
        "development_decision": (
            "PASS_V0_88_PAIRED_DEVELOPMENT_GATE"
            if all(conditions.values())
            else "REJECT_V0_88_PAIRED_DEVELOPMENT_GATE"
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
    correct_sentence_count = 0
    predicted_sentence_count = 0
    gold_sentence_count = 0
    for item in panel["cases"]:
        case_id = item["public_case"]["case_id"]
        private = item["private_reference"]
        candidate = run["compiled_candidates"].get(case_id)
        row = _score_case(
            case_id=case_id,
            private=private,
            candidate=candidate,
        )
        rows.append(row)
        correct_sentence_count += row["correct_sentence_count"]
        predicted_sentence_count += row["predicted_sentence_count"]
        gold_sentence_count += row["gold_sentence_count"]
    precision = (
        correct_sentence_count / predicted_sentence_count
        if predicted_sentence_count
        else 0.0
    )
    recall = (
        correct_sentence_count / gold_sentence_count
        if gold_sentence_count
        else 0.0
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    count = len(rows)
    return {
        "case_count": count,
        "valid_candidate_count": sum(row["candidate_valid"] for row in rows),
        "label_accuracy": sum(row["label_correct"] for row in rows) / count,
        "correct_sentence_count": correct_sentence_count,
        "predicted_sentence_count": predicted_sentence_count,
        "gold_sentence_count": gold_sentence_count,
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
    harmful = (
        action in {
            "OPEN_SUPPORTED_CANDIDATE",
            "OPEN_REFUTATION_CANDIDATE",
        }
        and not label_correct
    )
    return {
        "case_id": case_id,
        "candidate_valid": True,
        "gold_state": gold_state,
        "predicted_state": predicted_state,
        "runtime_action": action,
        "label_correct": label_correct,
        "predicted_sentence_count": len(predicted_units),
        "gold_sentence_count": len(gold_union),
        "correct_sentence_count": len(correct),
        "overselected_sentence_count": len(predicted_units - correct),
        "unrecovered_gold_sentence_count": len(gold_union - correct),
        "harmful_strong_candidate": harmful,
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
        "predicted_sentence_count": 0,
        "gold_sentence_count": gold_sentence_count,
        "correct_sentence_count": 0,
        "overselected_sentence_count": 0,
        "unrecovered_gold_sentence_count": gold_sentence_count,
        "harmful_strong_candidate": False,
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
