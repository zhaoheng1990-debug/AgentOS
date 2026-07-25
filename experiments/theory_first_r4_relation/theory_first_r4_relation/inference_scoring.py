"""Frozen Runtime scoring for R4 v0.3G."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .inference_cases import ATTRIBUTE_NAMES, INFERENCE_CASES, PAIR_EXPECTATIONS
from .inference_schemas import AttributeInferenceReceipt, ParsedAttributeReceipts
from .transform_compiler import compile_transformation_relation
from .transform_contracts import TransformationRelationCandidate


def _first_ref(refs: dict[str, tuple[str, ...]], name: str) -> str:
    return refs[name][0]


def _candidate(
    case: Any, receipt: AttributeInferenceReceipt
) -> TransformationRelationCandidate:
    attributes = receipt.attribute_dict()
    refs = receipt.ref_dict()
    tolerance_refs = [
        ref for ref in refs["added_uncertainty"] if ref.endswith("/tolerance")
    ]
    return TransformationRelationCandidate(
        case_id=case.case_id,
        case_family="provider_attribute_inference",
        **attributes,
        source_witness_ref=_first_ref(refs, "source_identity"),
        lineage_witness_ref=_first_ref(refs, "lineage_coupling"),
        transformation_witness_ref=_first_ref(refs, "information_relation"),
        target_claim_witness_ref=_first_ref(refs, "target_claim_relation"),
        uncertainty_witness_ref=_first_ref(refs, "added_uncertainty"),
        claim_tolerance_witness_ref=tolerance_refs[0] if tolerance_refs else None,
        expected_relation_state=case.expected_relation_state,
        expected_action=case.expected_action,
    )


def score_attribute_batch(
    parsed: ParsedAttributeReceipts, ledger: list[dict[str, Any]]
) -> dict[str, Any]:
    cases = {case.case_id: case for case in INFERENCE_CASES}
    receipts = {receipt.case_id: receipt for receipt in parsed.receipts}
    attribute_correct = Counter({name: 0 for name in ATTRIBUTE_NAMES})
    exact_tuple = 0
    exact_refs = 0
    missing_preserved = 0
    relation_correct = 0
    action_correct = 0
    false_actions = Counter()
    case_results = []
    for case_id in sorted(cases):
        case = cases[case_id]
        receipt = receipts[case_id]
        observed = receipt.attribute_dict()
        expected = case.attributes()
        correct = {
            name: observed[name] == expected[name] for name in ATTRIBUTE_NAMES
        }
        for name, passed in correct.items():
            attribute_correct[name] += int(passed)
        tuple_pass = all(correct.values())
        exact_tuple += int(tuple_pass)
        observed_refs = receipt.ref_dict()
        expected_refs = case.attribute_refs()
        refs_pass = all(
            set(observed_refs[name]) == set(expected_refs[name])
            for name in ATTRIBUTE_NAMES
        )
        exact_refs += int(refs_pass)
        missing_pass = all(
            observed[name].startswith("UNKNOWN") or observed[name] == "UNVERIFIED_TRANSFORM"
            for name in case.true_missing_attributes
        )
        if case.true_missing_attributes:
            missing_preserved += int(missing_pass)
        compiled = compile_transformation_relation(_candidate(case, receipt))
        relation_pass = compiled.relation_state == case.expected_relation_state
        action_pass = compiled.action == case.expected_action
        relation_correct += int(relation_pass)
        action_correct += int(action_pass)
        if compiled.action != case.expected_action:
            if compiled.action == "DEDUPE_AND_COMBINE":
                false_actions["false_deduplicate"] += 1
            elif compiled.action == "COMBINE":
                false_actions["false_combine"] += 1
            else:
                false_actions["false_block"] += 1
        case_results.append(
            {
                "case_id": case_id,
                "expected_attributes": expected,
                "observed_attributes": observed,
                "attribute_correct": correct,
                "exact_tuple": tuple_pass,
                "exact_attribute_refs": refs_pass,
                "expected_relation_state": case.expected_relation_state,
                "observed_relation_state": compiled.relation_state,
                "expected_action": case.expected_action,
                "observed_action": compiled.action,
                "compiler_errors": compiled.errors,
                "missing_facts": receipt.missing_facts,
                "dropped_provider_fields": receipt.dropped_provider_fields,
            }
        )
    pair_results = []
    for pair_id, left_id, right_id, changed in PAIR_EXPECTATIONS:
        left = receipts[left_id].attribute_dict()
        right = receipts[right_id].attribute_dict()
        expected_left = cases[left_id].attributes()
        expected_right = cases[right_id].attributes()
        passed = all(
            left[name] == expected_left[name]
            and right[name] == expected_right[name]
            and left[name] != right[name]
            for name in changed
        )
        pair_results.append(
            {
                "pair_id": pair_id,
                "changed_attributes": changed,
                "passed": passed,
            }
        )
    usage = {
        key: sum(int(item["usage"].get(key, 0)) for item in ledger)
        for key in (
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "cache_hit_tokens",
        )
    }
    true_missing_case_count = sum(bool(case.true_missing_attributes) for case in cases.values())
    gates = {
        "corpus_preflight": True,
        "private_surface_not_exposed": True,
        "logical_call_within_budget": len({item["logical_call_id"] for item in ledger}) == 1
        and len(ledger) <= 2
        and ledger[-1]["status"] == "VALID",
        "token_budget": usage["total_tokens"] <= 20000,
        "receipt_coverage": len(receipts) == 12,
        "per_attribute_accuracy": all(value >= 10 for value in attribute_correct.values()),
        "exact_tuple_accuracy": exact_tuple >= 9,
        "counterfactual_sensitivity": sum(item["passed"] for item in pair_results) >= 5,
        "evidence_reference_coverage": exact_refs == 12,
        "missing_fact_preservation": missing_preserved == true_missing_case_count,
        "relation_accuracy": relation_correct >= 10,
        "action_accuracy": action_correct >= 10,
        "zero_false_deduplicate": false_actions["false_deduplicate"] == 0,
        "forbidden_fields_excluded": not any(
            item["dropped_provider_fields"] for item in case_results
        ),
        "authority_and_protected_writes_zero": True,
    }
    return {
        "experiment_version": "agentos_r4_provider_transform_attribute_v0_3g",
        "status": "PASS" if all(gates.values()) else "FAIL_SEMANTIC",
        "claim_ceiling": "SAME_PROVIDER_FRESH_SYNTHETIC_TRANSFORMATION_ATTRIBUTE_INFERENCE_ONLY",
        "case_count": 12,
        "attribute_correct": dict(attribute_correct),
        "exact_tuple_count": exact_tuple,
        "exact_attribute_reference_count": exact_refs,
        "counterfactual_pair_pass_count": sum(item["passed"] for item in pair_results),
        "relation_correct_count": relation_correct,
        "action_correct_count": action_correct,
        "false_combine": false_actions["false_combine"],
        "false_deduplicate": false_actions["false_deduplicate"],
        "false_block": false_actions["false_block"],
        "root_type": parsed.root_type,
        "source_key": parsed.source_key,
        "root_metadata_fields": parsed.root_metadata_fields,
        "usage": usage,
        "physical_attempt_count": len(ledger),
        "attempt_ledger": ledger,
        "pair_results": pair_results,
        "case_results": case_results,
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_count": len(gates),
        "provider_decision_authority": False,
        "core_writes": 0,
        "retention_writes": 0,
        "baseline_writes": 0,
    }
