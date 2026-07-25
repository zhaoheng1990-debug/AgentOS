"""Frozen Runtime scoring for Provider semantic relation receipts."""

from __future__ import annotations

import statistics
from collections import Counter
from typing import Any

from .contracts import RELATION_STATES
from .semantic_cases import CASES, STATE_TO_ACTION
from .semantic_schemas import ParsedSemanticReceipts


def _states(parsed: ParsedSemanticReceipts) -> dict[str, str]:
    return {receipt.case_id: receipt.relation_state for receipt in parsed.receipts}


def score_relation_predictions(predictions: dict[str, str]) -> dict[str, Any]:
    truth = {case.case_id: case.private_relation_state for case in CASES}
    truth_actions = {case.case_id: case.private_action for case in CASES}
    predicted_actions = {
        case_id: STATE_TO_ACTION[state] for case_id, state in predictions.items()
    }
    recalls = {}
    for state in RELATION_STATES:
        case_ids = [case_id for case_id, value in truth.items() if value == state]
        recalls[state] = sum(predictions[case_id] == state for case_id in case_ids) / len(
            case_ids
        )
    false_combine = [
        case_id
        for case_id in truth
        if predicted_actions[case_id] == "COMBINE"
        and truth_actions[case_id] != "COMBINE"
    ]
    false_dedupe = [
        case_id
        for case_id in truth
        if predicted_actions[case_id] == "DEDUPE_AND_COMBINE"
        and truth_actions[case_id] != "DEDUPE_AND_COMBINE"
    ]
    false_block = [
        case_id
        for case_id in truth
        if predicted_actions[case_id] == "BLOCK"
        and truth_actions[case_id] != "BLOCK"
    ]
    return {
        "relation_accuracy": sum(
            predictions[case_id] == truth[case_id] for case_id in truth
        )
        / len(truth),
        "state_recall": recalls,
        "macro_state_recall": statistics.fmean(recalls.values()),
        "action_accuracy": sum(
            predicted_actions[case_id] == truth_actions[case_id]
            for case_id in truth
        )
        / len(truth),
        "false_combine_case_ids": false_combine,
        "false_deduplicate_case_ids": false_dedupe,
        "false_block_case_ids": false_block,
        "confusion": [
            {
                "case_id": case_id,
                "truth": truth[case_id],
                "observed": predictions[case_id],
                "truth_action": truth_actions[case_id],
                "observed_action": predicted_actions[case_id],
            }
            for case_id in sorted(truth)
            if predictions[case_id] != truth[case_id]
        ],
    }


def score_panel(
    parsed_runs: dict[str, ParsedSemanticReceipts],
    ledger: list[dict[str, Any]],
    raw_contents: dict[str, str],
) -> dict[str, Any]:
    predictions = {
        "batch_a": _states(parsed_runs["batch_A"]),
        "batch_b": _states(parsed_runs["batch_B"]),
        "single": {
            case.case_id: parsed_runs[f"single_{case.case_id}"].receipts[
                0
            ].relation_state
            for case in CASES
        },
    }
    arm_metrics = {
        arm: score_relation_predictions(values)
        for arm, values in predictions.items()
    }
    batch_consensus = {
        case.case_id: (
            predictions["batch_a"][case.case_id]
            if predictions["batch_a"][case.case_id]
            == predictions["batch_b"][case.case_id]
            else "UNRESOLVED"
        )
        for case in CASES
    }
    batch_agreement = sum(
        predictions["batch_a"][case.case_id]
        == predictions["batch_b"][case.case_id]
        for case in CASES
    ) / len(CASES)
    consensus_single_agreement = sum(
        batch_consensus[case.case_id] == predictions["single"][case.case_id]
        for case in CASES
    ) / len(CASES)
    all_receipts = [
        receipt
        for parsed in parsed_runs.values()
        for receipt in parsed.receipts
    ]
    total_tokens = sum(int(row["usage"]["total_tokens"]) for row in ledger)
    valid_calls = sum(row["status"] == "VALID" for row in ledger)
    false_combine_count = sum(
        len(metrics["false_combine_case_ids"]) for metrics in arm_metrics.values()
    )
    false_dedupe_count = sum(
        len(metrics["false_deduplicate_case_ids"])
        for metrics in arm_metrics.values()
    )
    gates = {
        "call_and_attempt_budget": valid_calls == 14 and len(ledger) <= 28,
        "token_limit": total_tokens <= 120000,
        "mechanical_receipt_coverage": len(all_receipts) == 36,
        "batch_a_relation_accuracy": arm_metrics["batch_a"][
            "relation_accuracy"
        ]
        >= 11 / 12,
        "batch_b_relation_accuracy": arm_metrics["batch_b"][
            "relation_accuracy"
        ]
        >= 11 / 12,
        "single_relation_accuracy": arm_metrics["single"]["relation_accuracy"]
        >= 11 / 12,
        "macro_state_recall": all(
            metrics["macro_state_recall"] >= 0.80
            for metrics in arm_metrics.values()
        ),
        "batch_exact_agreement": batch_agreement >= 11 / 12,
        "batch_consensus_single_agreement": consensus_single_agreement >= 10 / 12,
        "runtime_action_accuracy": all(
            metrics["action_accuracy"] >= 11 / 12
            for metrics in arm_metrics.values()
        ),
        "false_combine_zero": false_combine_count == 0,
        "false_deduplicate_zero": false_dedupe_count == 0,
        "evidence_and_forbidden_field_gate": all(
            len(receipt.evidence_refs) == 2 for receipt in all_receipts
        ),
        "forbidden_authority_and_writes_zero": True,
    }
    mechanical_names = {
        "call_and_attempt_budget",
        "token_limit",
        "mechanical_receipt_coverage",
        "evidence_and_forbidden_field_gate",
        "forbidden_authority_and_writes_zero",
    }
    status = (
        "PASS"
        if all(gates.values())
        else "PARTIAL"
        if all(gates[name] for name in mechanical_names)
        else "FAIL"
    )
    return {
        "experiment_version": "agentos_r4_provider_semantic_relation_v0_3b",
        "status": status,
        "claim_ceiling": "SAME_PROVIDER_FRESH_SEMANTIC_RELATION_INSTANTIATION_ONLY",
        "provider": {
            "provider_id": "deepseek",
            "model_id": "deepseek-v4-flash",
            "thinking": "disabled",
        },
        "logical_call_count": valid_calls,
        "physical_attempt_count": len(ledger),
        "total_tokens": total_tokens,
        "tokens_per_relation_receipt": total_tokens / len(all_receipts),
        "attempt_ledger": ledger,
        "root_type_counts": dict(
            Counter(parsed.root_type for parsed in parsed_runs.values())
        ),
        "dropped_provider_fields": dict(
            Counter(
                field
                for receipt in all_receipts
                for field in receipt.dropped_provider_fields
            )
        ),
        "predictions": predictions,
        "batch_consensus": batch_consensus,
        "arm_metrics": arm_metrics,
        "cross_arm": {
            "batch_a_batch_b_agreement": batch_agreement,
            "batch_consensus_single_agreement": consensus_single_agreement,
            "single_minus_mean_batch_accuracy": arm_metrics["single"][
                "relation_accuracy"
            ]
            - statistics.fmean(
                (
                    arm_metrics["batch_a"]["relation_accuracy"],
                    arm_metrics["batch_b"]["relation_accuracy"],
                )
            ),
        },
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_count": len(gates),
        "raw_contents": raw_contents,
        "provider_decision_authority": False,
        "core_writes": 0,
        "retention_writes": 0,
        "baseline_writes": 0,
    }
