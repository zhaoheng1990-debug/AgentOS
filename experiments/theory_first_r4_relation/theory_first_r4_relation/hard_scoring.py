"""Frozen fresh hard-corpus scoring for R4 v0.3E."""

from __future__ import annotations

import statistics
from collections import Counter
from typing import Any

from .contracts import RELATION_STATES
from .hard_cases import HARD_CASES
from .hard_corpus_audit import audit_hard_corpus
from .semantic_cases import STATE_TO_ACTION
from .semantic_schemas import ParsedSemanticReceipts


def score_hard_batch(
    parsed: ParsedSemanticReceipts, ledger: list[dict[str, Any]]
) -> dict[str, Any]:
    truth = {case.case_id: case.private_relation_state for case in HARD_CASES}
    truth_actions = {case.case_id: case.private_action for case in HARD_CASES}
    receipts = {receipt.case_id: receipt for receipt in parsed.receipts}
    predictions = {
        case_id: receipts[case_id].relation_state for case_id in truth
    }
    predicted_actions = {
        case_id: STATE_TO_ACTION[state] for case_id, state in predictions.items()
    }
    state_recall = {}
    for state in RELATION_STATES:
        case_ids = [case_id for case_id, value in truth.items() if value == state]
        state_recall[state] = sum(
            predictions[case_id] == state for case_id in case_ids
        ) / len(case_ids)
    relation_accuracy = sum(
        predictions[case_id] == truth[case_id] for case_id in truth
    ) / len(truth)
    action_accuracy = sum(
        predicted_actions[case_id] == truth_actions[case_id]
        for case_id in truth
    ) / len(truth)
    false_combine = [
        case_id
        for case_id in truth
        if predicted_actions[case_id] == "COMBINE"
        and truth_actions[case_id] != "COMBINE"
    ]
    false_deduplicate = [
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
    unresolved_case_ids = [
        case.case_id
        for case in HARD_CASES
        if case.private_relation_state == "UNRESOLVED"
    ]
    unresolved_assumption_coverage = sum(
        bool(receipts[case_id].unresolved_assumptions)
        for case_id in unresolved_case_ids
    ) / len(unresolved_case_ids)
    total_tokens = sum(int(row["usage"]["total_tokens"]) for row in ledger)
    valid_calls = sum(row["status"] == "VALID" for row in ledger)
    audit = audit_hard_corpus()
    gates = {
        "corpus_fixture_validity": audit["status"] == "PASS",
        "lexical_and_private_leakage": audit["gates"]["lexical_decueing"]
        and audit["gates"]["private_surface_absent"],
        "call_and_attempt_budget": valid_calls == 1 and len(ledger) <= 2,
        "token_limit": total_tokens <= 20000,
        "mechanical_receipt_coverage": len(receipts) == 18,
        "relation_accuracy": relation_accuracy >= 15 / 18,
        "per_state_recall": all(value >= 2 / 3 for value in state_recall.values()),
        "macro_state_recall": statistics.fmean(state_recall.values()) >= 0.80,
        "runtime_action_accuracy": action_accuracy >= 17 / 18,
        "false_combine_zero": not false_combine,
        "false_deduplicate_zero": not false_deduplicate,
        "false_block_and_unresolved_assumptions": len(false_block) <= 1
        and unresolved_assumption_coverage == 1.0,
        "evidence_authority_and_writes": all(
            len(receipt.evidence_refs) == 2 for receipt in parsed.receipts
        ),
    }
    if false_combine or false_deduplicate:
        status = "FAIL_HARMFUL_GENERALIZATION"
    elif all(gates.values()):
        status = "PASS_FRESH_HARD_RELATION_GENERALIZATION"
    else:
        status = "FAIL_SEMANTIC_TRANSFER"
    return {
        "experiment_version": "agentos_r4_fresh_hard_relation_v0_3e",
        "status": status,
        "claim_ceiling": (
            "SAME_PROVIDER_FRESH_HARD_SYNTHETIC_RELATION_GENERALIZATION_ONLY"
        ),
        "provider": {
            "provider_id": "deepseek",
            "model_request": "deepseek-v4-flash",
            "thinking": "disabled",
        },
        "case_count": len(HARD_CASES),
        "corpus_audit": audit,
        "logical_call_count": valid_calls,
        "physical_attempt_count": len(ledger),
        "total_tokens": total_tokens,
        "tokens_per_receipt": total_tokens / len(receipts),
        "root_type": parsed.root_type,
        "source_key": parsed.source_key,
        "dropped_provider_fields": dict(
            Counter(
                field
                for receipt in parsed.receipts
                for field in receipt.dropped_provider_fields
            )
        ),
        "relation_accuracy": relation_accuracy,
        "state_recall": state_recall,
        "macro_state_recall": statistics.fmean(state_recall.values()),
        "runtime_action_accuracy": action_accuracy,
        "false_combine_case_ids": false_combine,
        "false_deduplicate_case_ids": false_deduplicate,
        "false_block_case_ids": false_block,
        "unresolved_assumption_coverage": unresolved_assumption_coverage,
        "predictions": predictions,
        "confusion": [
            {
                "case_id": case_id,
                "truth": truth[case_id],
                "observed": predictions[case_id],
                "truth_action": truth_actions[case_id],
                "observed_action": predicted_actions[case_id],
                "unresolved_assumptions": list(
                    receipts[case_id].unresolved_assumptions
                ),
            }
            for case_id in sorted(truth)
            if predictions[case_id] != truth[case_id]
        ],
        "attempt_ledger": ledger,
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_count": len(gates),
        "provider_decision_authority": False,
        "core_writes": 0,
        "retention_writes": 0,
        "baseline_writes": 0,
    }

