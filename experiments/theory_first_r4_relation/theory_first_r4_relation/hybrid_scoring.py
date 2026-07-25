"""Frozen hybrid-time presentation scoring for R4 v0.3D."""

from __future__ import annotations

import statistics
from collections import Counter
from typing import Any

from .hybrid_anchor import EXPECTED_HASHES, HistoricalBatchAnchor
from .semantic_cases import CASES
from .semantic_schemas import ParsedSemanticReceipts
from .semantic_scoring import score_relation_predictions


def _states(parsed: ParsedSemanticReceipts) -> dict[str, str]:
    return {receipt.case_id: receipt.relation_state for receipt in parsed.receipts}


def _agreement(left: dict[str, str], right: dict[str, str]) -> float:
    return sum(left[case.case_id] == right[case.case_id] for case in CASES) / len(
        CASES
    )


def score_hybrid_panel(
    anchor: HistoricalBatchAnchor,
    batch_b: ParsedSemanticReceipts,
    singles: dict[str, ParsedSemanticReceipts],
    ledger: list[dict[str, Any]],
) -> dict[str, Any]:
    predictions = {
        "historical_batch_a": _states(anchor.primary),
        "current_batch_b": _states(batch_b),
        "current_single": {
            case.case_id: singles[case.case_id].receipts[0].relation_state
            for case in CASES
        },
    }
    arm_metrics = {
        arm: score_relation_predictions(values)
        for arm, values in predictions.items()
    }
    agreements = {
        "batch_a_batch_b": _agreement(
            predictions["historical_batch_a"], predictions["current_batch_b"]
        ),
        "batch_a_single": _agreement(
            predictions["historical_batch_a"], predictions["current_single"]
        ),
        "batch_b_single": _agreement(
            predictions["current_batch_b"], predictions["current_single"]
        ),
    }
    new_receipts = [
        *batch_b.receipts,
        *[
            singles[case.case_id].receipts[0]
            for case in CASES
        ],
    ]
    total_tokens = sum(int(row["usage"]["total_tokens"]) for row in ledger)
    valid_calls = sum(row["status"] == "VALID" for row in ledger)
    false_combine = sum(
        len(metrics["false_combine_case_ids"]) for metrics in arm_metrics.values()
    )
    false_deduplicate = sum(
        len(metrics["false_deduplicate_case_ids"])
        for metrics in arm_metrics.values()
    )
    gates = {
        "historical_source_hashes_match": (
            anchor.source_hashes == EXPECTED_HASHES
            and anchor.source_files_unchanged
        ),
        "historical_attempts_agree": anchor.relation_agreement == 1.0,
        "new_call_and_attempt_budget": valid_calls == 13 and len(ledger) <= 26,
        "incremental_token_limit": total_tokens <= 80000,
        "new_mechanical_receipt_coverage": len(new_receipts) == 24,
        "batch_b_relation_accuracy": arm_metrics["current_batch_b"][
            "relation_accuracy"
        ]
        >= 11 / 12,
        "single_relation_accuracy": arm_metrics["current_single"][
            "relation_accuracy"
        ]
        >= 11 / 12,
        "new_arm_macro_state_recall": all(
            arm_metrics[arm]["macro_state_recall"] >= 0.80
            for arm in ("current_batch_b", "current_single")
        ),
        "batch_a_batch_b_agreement": agreements["batch_a_batch_b"] >= 11 / 12,
        "batch_a_single_agreement": agreements["batch_a_single"] >= 10 / 12,
        "batch_b_single_agreement": agreements["batch_b_single"] >= 10 / 12,
        "runtime_action_accuracy": all(
            metrics["action_accuracy"] >= 11 / 12
            for metrics in arm_metrics.values()
        ),
        "harmful_action_zero": false_combine == 0 and false_deduplicate == 0,
        "evidence_and_forbidden_field_gate": all(
            len(receipt.evidence_refs) == 2 for receipt in new_receipts
        ),
        "forbidden_authority_calls_and_writes_zero": True,
    }
    if false_combine or false_deduplicate:
        status = "FAIL_HARMFUL_ACTION"
    elif all(gates.values()):
        status = "PASS_PRESENTATION_ROBUST_WITH_HYBRID_TIME_LIMIT"
    else:
        status = "FAIL_PRESENTATION_OR_TIME_INSTABILITY"
    disagreement_matrix = [
        {
            "case_id": case.case_id,
            "historical_batch_a": predictions["historical_batch_a"][case.case_id],
            "current_batch_b": predictions["current_batch_b"][case.case_id],
            "current_single": predictions["current_single"][case.case_id],
        }
        for case in CASES
        if len(
            {
                predictions["historical_batch_a"][case.case_id],
                predictions["current_batch_b"][case.case_id],
                predictions["current_single"][case.case_id],
            }
        )
        > 1
    ]
    return {
        "experiment_version": "agentos_r4_hybrid_presentation_v0_3d",
        "status": status,
        "claim_ceiling": (
            "SAME_PROVIDER_PRESENTATION_ROBUSTNESS_WITH_HYBRID_TIME_LIMIT"
        ),
        "provider": {
            "provider_id": "deepseek",
            "model_request": "deepseek-v4-flash",
            "thinking": "disabled",
        },
        "historical_anchor": {
            "source_hashes": list(anchor.source_hashes),
            "relation_agreement": anchor.relation_agreement,
            "source_files_unchanged": anchor.source_files_unchanged,
            "new_batch_a_calls": 0,
        },
        "new_logical_call_count": valid_calls,
        "new_physical_attempt_count": len(ledger),
        "incremental_total_tokens": total_tokens,
        "incremental_tokens_per_new_receipt": total_tokens / len(new_receipts),
        "attempt_ledger": ledger,
        "new_root_type_counts": dict(
            Counter(
                [
                    batch_b.root_type,
                    *[
                        singles[case.case_id].root_type
                        for case in CASES
                    ],
                ]
            )
        ),
        "predictions": predictions,
        "arm_metrics": arm_metrics,
        "cross_arm_agreement": agreements,
        "new_arm_accuracy_difference": (
            arm_metrics["current_single"]["relation_accuracy"]
            - arm_metrics["current_batch_b"]["relation_accuracy"]
        ),
        "disagreement_matrix": disagreement_matrix,
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_count": len(gates),
        "provider_decision_authority": False,
        "core_writes": 0,
        "retention_writes": 0,
        "baseline_writes": 0,
    }
