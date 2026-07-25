"""Independent label, rationale, and candidate-state scoring for v0.87."""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any

from ..provider_telemetry import hash_payload
from ..selection_retention_fresh_provider_helpers import (
    physical_attempts,
)
from .scifact_v0_87_holdout import (
    validate_holdout,
    validate_preregistration,
)


def evaluate_warrant_run(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    validate_holdout(panel)
    validate_preregistration(preregistration, panel=panel)
    if run.get("source_holdout_hash") != panel["artifact_hash"]:
        raise ValueError("scifact_v0_87_run_panel_mismatch")
    rows = []
    for item in panel["cases"]:
        public = item["public_case"]
        private = item["private_reference"]
        case_id = public["case_id"]
        receipt = run["receipts"].get(case_id)
        candidate = run["compiled_candidates"].get(case_id)
        rows.append(_score_case(
            case_id=case_id,
            private=private,
            receipt=receipt,
            candidate=candidate,
        ))
    valid = [row for row in rows if row["receipt_valid"]]
    count = len(rows)
    label_accuracy = sum(row["label_correct"] for row in rows) / count
    macro_rationale_f1 = mean(row["rationale_f1"] for row in rows)
    joint_success_rate = sum(row["joint_success"] for row in rows) / count
    harmful_count = sum(row["harmful_compiled_candidate"] for row in rows)
    abstention_rate = sum(row["runtime_action"] == "ABSTAIN" for row in rows) / count
    calls = run["task_calls"]
    operational_gate = preregistration["operational_gate"]
    semantic_gate = preregistration["semantic_gate"]
    conditions = {
        "valid_receipts": (
            len(valid) >= operational_gate["valid_receipts_min"]
        ),
        "contract_failures": (
            len(run["failures"])
            <= operational_gate["contract_failures_max"]
        ),
        "physical_attempts": (
            physical_attempts(calls)
            <= operational_gate["physical_attempts_max"]
        ),
        "token_ceiling": (
            _token_count(calls)
            <= operational_gate["hard_total_token_ceiling"]
        ),
        "label_accuracy": (
            label_accuracy >= semantic_gate["label_accuracy_min"]
        ),
        "macro_rationale_f1": (
            macro_rationale_f1
            >= semantic_gate["macro_rationale_f1_min"]
        ),
        "joint_success_rate": (
            joint_success_rate
            >= semantic_gate["joint_success_rate_min"]
        ),
        "harmful_compiled_candidates": (
            harmful_count
            <= semantic_gate["harmful_compiled_candidates_max"]
        ),
        "abstention_rate": (
            abstention_rate <= semantic_gate["abstention_rate_max"]
        ),
        "no_write_boundary": (
            run.get("core_write_allowed") is False
            and run.get("retention_write_allowed") is False
            and run.get("candidate_only") is True
        ),
    }
    confusion = Counter(
        (row["gold_state"], row["predicted_state"]) for row in rows
    )
    value = {
        "evaluation_version": "scifact_semantic_warrant_evaluation_v0_87",
        "source_holdout_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "case_count": count,
        "valid_receipt_count": len(valid),
        "failure_count": len(run["failures"]),
        "label_accuracy": label_accuracy,
        "macro_rationale_f1": macro_rationale_f1,
        "joint_success_rate": joint_success_rate,
        "harmful_compiled_candidate_count": harmful_count,
        "abstention_rate": abstention_rate,
        "physical_attempt_count": physical_attempts(calls),
        "physical_total_tokens": _token_count(calls),
        "confusion": {
            f"{gold}->{predicted}": amount
            for (gold, predicted), amount in sorted(confusion.items())
        },
        "case_scores": rows,
        "gate_conditions": conditions,
        "development_decision": (
            "PASS_V0_87_DEVELOPMENT_GATE"
            if all(conditions.values())
            else "REJECT_V0_87_DEVELOPMENT_GATE"
        ),
        "external_acceptance_eligible": False,
        "same_version_retuning_allowed": False,
        "candidate_acceptance_authorized": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def _token_count(calls: list[dict[str, Any]]) -> int:
    return sum(
        int(call.get("token_usage", {}).get("total_tokens", 0))
        for call in calls
    )


def _score_case(
    *,
    case_id: str,
    private: dict[str, Any],
    receipt: dict[str, Any] | None,
    candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    gold_state = private["expected_state"]
    if receipt is None or candidate is None:
        return {
            "case_id": case_id,
            "receipt_valid": False,
            "gold_state": gold_state,
            "predicted_state": "NO_VALID_RECEIPT",
            "label_correct": False,
            "rationale_precision": 0.0,
            "rationale_recall": 0.0,
            "rationale_f1": 0.0,
            "joint_success": False,
            "runtime_action": "ABSTAIN",
            "harmful_compiled_candidate": False,
        }
    predicted = receipt["claim_state"]
    precision, recall, f1 = _best_rationale_score(
        set(receipt["selected_unit_ids"]),
        private["metadata"].get("gold_rationale_sets", []),
    )
    label_correct = predicted == gold_state
    joint = label_correct and f1 == 1.0
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
        "receipt_valid": True,
        "gold_state": gold_state,
        "predicted_state": predicted,
        "label_correct": label_correct,
        "rationale_precision": precision,
        "rationale_recall": recall,
        "rationale_f1": f1,
        "joint_success": joint,
        "runtime_action": action,
        "harmful_compiled_candidate": harmful,
    }


def _best_rationale_score(
    predicted: set[str],
    gold_sets: list[list[str]],
) -> tuple[float, float, float]:
    normalized = [set(value) for value in gold_sets] or [set()]
    scores = [_set_score(predicted, gold) for gold in normalized]
    return max(scores, key=lambda value: (value[2], value[1], value[0]))


def _set_score(
    predicted: set[str],
    gold: set[str],
) -> tuple[float, float, float]:
    if not predicted and not gold:
        return 1.0, 1.0, 1.0
    intersection = len(predicted.intersection(gold))
    precision = intersection / len(predicted) if predicted else 0.0
    recall = intersection / len(gold) if gold else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return precision, recall, f1
