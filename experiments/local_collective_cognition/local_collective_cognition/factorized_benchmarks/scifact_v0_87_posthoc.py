"""Descriptive SciFact-official sentence metric audit for frozen v0.87."""

from __future__ import annotations

from typing import Any

from ..provider_telemetry import hash_payload

OFFICIAL_EVALUATION_URL = (
    "https://github.com/allenai/scifact/blob/master/doc/evaluation.md"
)


def build_official_sentence_audit(
    *,
    panel: dict[str, Any],
    run: dict[str, Any],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    if evaluation.get("source_run_hash") != run.get("run_hash"):
        raise ValueError("scifact_v0_87_posthoc_run_mismatch")
    if evaluation.get("source_holdout_hash") != panel.get("artifact_hash"):
        raise ValueError("scifact_v0_87_posthoc_panel_mismatch")
    rows = []
    for item in panel["cases"]:
        case_id = item["public_case"]["case_id"]
        private = item["private_reference"]
        receipt = run["receipts"].get(case_id)
        rows.append(_score_official_sentences(
            case_id=case_id,
            gold_state=private["expected_state"],
            gold_sets=private["metadata"].get("gold_rationale_sets", []),
            receipt=receipt,
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
    value = {
        "audit_version": "scifact_official_sentence_posthoc_v0_87",
        "source_holdout_hash": panel["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_evaluation_hash": evaluation["artifact_hash"],
        "official_evaluation_url": OFFICIAL_EVALUATION_URL,
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
        "case_scores": rows,
        "descriptive_posthoc_only": True,
        "preregistered_gate_changed": False,
        "gate_authority": False,
        "same_version_retuning_allowed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def _score_official_sentences(
    *,
    case_id: str,
    gold_state: str,
    gold_sets: list[list[str]],
    receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    predicted_ordered = (
        list(receipt["selected_unit_ids"]) if receipt is not None else []
    )
    predicted = set(predicted_ordered)
    normalized_sets = [set(values) for values in gold_sets]
    gold_union = set().union(*normalized_sets) if normalized_sets else set()
    correct = set()
    label_correct = (
        receipt is not None and receipt["claim_state"] == gold_state
    )
    if label_correct:
        for gold_set in normalized_sets:
            if gold_set.issubset(predicted):
                correct.update(gold_set)
        correct.intersection_update(predicted)
    return {
        "case_id": case_id,
        "label_correct": label_correct,
        "predicted_sentence_count": len(predicted),
        "gold_sentence_count": len(gold_union),
        "correct_sentence_count": len(correct),
        "overselected_sentence_count": len(predicted - correct),
        "unrecovered_gold_sentence_count": len(gold_union - correct),
        "incomplete_gold_set_count": sum(
            bool(predicted.intersection(gold_set))
            and not gold_set.issubset(predicted)
            for gold_set in normalized_sets
        ),
    }
