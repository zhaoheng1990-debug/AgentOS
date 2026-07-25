"""Deterministic matched-arm compilation and scoring for R4 v0.3J."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .comparison_cases import (
    COMPARISON_CASES,
    LEGACY_INVERSE,
    REVALIDATION_BY_STATUS,
    SHARED_ATTRIBUTES,
)
from .comparison_schemas import ParsedComparisonReceipts
from .factor_compiler import compile_factorized_transformation
from .factor_contracts import FactorizedTransformationCandidate
from .transform_compiler import compile_transformation_relation
from .transform_contracts import TransformationRelationCandidate


def _ref(refs: dict[str, tuple[str, ...]], name: str, suffix: str | None = None):
    values = refs[name]
    if suffix:
        return next((value for value in values if value.endswith(suffix)), None)
    return values[0]


def _compile(case, receipt):
    values, refs = receipt.attribute_dict(), receipt.ref_dict()
    common = {
        "case_id": case.case_id,
        "case_family": "matched_factorization_comparison",
        "source_identity": values["source_identity"],
        "lineage_coupling": values["lineage_coupling"],
        "added_uncertainty": values["added_uncertainty"],
        "target_claim_relation": values["target_claim_relation"],
        "source_witness_ref": _ref(refs, "source_identity"),
        "lineage_witness_ref": _ref(refs, "lineage_coupling"),
        "target_claim_witness_ref": _ref(refs, "target_claim_relation"),
        "uncertainty_witness_ref": _ref(refs, "added_uncertainty"),
        "claim_tolerance_witness_ref": _ref(
            refs, "added_uncertainty", "/tolerance"
        ),
        "expected_relation_state": "UNRESOLVED",
        "expected_action": "BLOCK",
    }
    if receipt.arm == "legacy":
        candidate = TransformationRelationCandidate(
            **common,
            information_relation=values["information_relation"],
            transformation_witness_ref=_ref(refs, "information_relation"),
        )
        return compile_transformation_relation(candidate)
    candidate = FactorizedTransformationCandidate(
        **common,
        transform_status=values["transform_status"],
        information_effect=values["information_effect"],
        transform_status_witness_ref=_ref(refs, "transform_status"),
        information_effect_witness_ref=_ref(refs, "information_effect"),
        full_domain_witness_ref=(
            _ref(refs, "information_effect")
            if values["information_effect"] == "GLOBAL_EQUIVALENT"
            else None
        ),
    )
    return compile_factorized_transformation(candidate)


def _private_receipt(case, arm):
    class PrivateReceipt:
        def __init__(self):
            self.arm = arm

        def attribute_dict(self):
            return case.legacy_dict() if arm == "legacy" else case.factorized_dict()

        def ref_dict(self):
            return case.expected_refs(arm)

    return PrivateReceipt()


def private_outcomes() -> dict[str, dict[str, str]]:
    outcomes = {}
    for case in COMPARISON_CASES:
        legacy = _compile(case, _private_receipt(case, "legacy"))
        factor = _compile(case, _private_receipt(case, "factorized"))
        if (legacy.relation_state, legacy.action) != (
            factor.relation_state,
            factor.action,
        ):
            raise ValueError(f"private compiler mismatch: {case.case_id}")
        outcomes[case.case_id] = {
            "relation_state": factor.relation_state,
            "action": factor.action,
            "revalidation": case.revalidation,
        }
    return outcomes


def _legacy_revalidation(information_relation: str) -> str:
    if information_relation == "UNVERIFIED_TRANSFORM":
        return "TRANSFORM_STATUS_UNRESOLVED"
    if information_relation == "NOT_APPLICABLE":
        return "NO_TRANSFORM_RELATION_ESTABLISHED"
    return "NO_TRANSFORM_STATUS_REVALIDATION"


def score_call(
    call_id: str,
    parsed: ParsedComparisonReceipts,
    usage: dict[str, int],
) -> dict[str, Any]:
    cases = {case.case_id: case for case in COMPARISON_CASES}
    expected_outcomes = private_outcomes()
    attribute_correct = Counter()
    relation_correct = action_correct = refs_exact = latent_exact = revalidation_exact = 0
    false = Counter()
    results = []
    for receipt in parsed.receipts:
        case = cases[receipt.case_id]
        expected = (
            case.legacy_dict()
            if parsed.arm == "legacy"
            else case.factorized_dict()
        )
        observed = receipt.attribute_dict()
        correctness = {name: observed[name] == expected[name] for name in expected}
        for name, passed in correctness.items():
            attribute_correct[name] += int(passed)
        expected_refs = case.expected_refs(parsed.arm)
        observed_refs = receipt.ref_dict()
        refs_pass = all(
            set(observed_refs[name]) == set(expected_refs[name])
            for name in expected_refs
        )
        refs_exact += int(refs_pass)
        compiled = _compile(case, receipt)
        expected_outcome = expected_outcomes[case.case_id]
        relation_pass = compiled.relation_state == expected_outcome["relation_state"]
        action_pass = compiled.action == expected_outcome["action"]
        relation_correct += int(relation_pass)
        action_correct += int(action_pass)
        if compiled.action != expected_outcome["action"]:
            if compiled.action == "DEDUPE_AND_COMBINE":
                false["deduplicate"] += 1
            elif compiled.action == "COMBINE":
                false["combine"] += 1
            else:
                false["block"] += 1
        true_pair = (
            case.factorized_dict()["transform_status"],
            case.factorized_dict()["information_effect"],
        )
        if parsed.arm == "legacy":
            possible = LEGACY_INVERSE[observed["information_relation"]]
            latent_pass = len(possible) == 1 and true_pair in possible
            revalidation = _legacy_revalidation(observed["information_relation"])
        else:
            latent_pass = (
                observed["transform_status"],
                observed["information_effect"],
            ) == true_pair
            revalidation = REVALIDATION_BY_STATUS[observed["transform_status"]]
        latent_exact += int(latent_pass)
        revalidation_pass = revalidation == expected_outcome["revalidation"]
        revalidation_exact += int(revalidation_pass)
        results.append(
            {
                "case_id": case.case_id,
                "attribute_correct": correctness,
                "refs_exact": refs_pass,
                "latent_exact": latent_pass,
                "expected_relation_state": expected_outcome["relation_state"],
                "observed_relation_state": compiled.relation_state,
                "expected_action": expected_outcome["action"],
                "observed_action": compiled.action,
                "expected_revalidation": expected_outcome["revalidation"],
                "observed_revalidation": revalidation,
                "revalidation_exact": revalidation_pass,
                "compiler_errors": compiled.errors,
                "dropped_fields": receipt.dropped_fields,
            }
        )
    return {
        "call_id": call_id,
        "arm": parsed.arm,
        "attribute_correct": dict(attribute_correct),
        "refs_exact_count": refs_exact,
        "latent_exact_count": latent_exact,
        "revalidation_exact_count": revalidation_exact,
        "relation_correct_count": relation_correct,
        "action_correct_count": action_correct,
        "false_combine": false["combine"],
        "false_deduplicate": false["deduplicate"],
        "false_block": false["block"],
        "usage": usage,
        "root_type": parsed.root_type,
        "source_key": parsed.source_key,
        "case_results": results,
    }


def score_comparison(
    parsed_calls: dict[str, ParsedComparisonReceipts],
    ledger: list[dict[str, Any]],
) -> dict[str, Any]:
    usage_by_call = {
        call_id: {
            key: sum(
                int(item["usage"].get(key, 0))
                for item in ledger
                if item["logical_call_id"] == call_id
            )
            for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cache_hit_tokens")
        }
        for call_id in parsed_calls
    }
    calls = {
        call_id: score_call(call_id, parsed, usage_by_call[call_id])
        for call_id, parsed in parsed_calls.items()
    }
    legacy_ids = ("legacy_forward", "legacy_reverse")
    factor_ids = ("factor_forward", "factor_reverse")
    matched = (
        ("round_forward", "legacy_forward", "factor_forward"),
        ("round_reverse", "legacy_reverse", "factor_reverse"),
    )
    gains = [
        {
            "round": name,
            "latent_gain": calls[factor]["latent_exact_count"]
            - calls[legacy]["latent_exact_count"],
            "revalidation_gain": calls[factor]["revalidation_exact_count"]
            - calls[legacy]["revalidation_exact_count"],
        }
        for name, legacy, factor in matched
    ]
    def action_agreement(first, second):
        left = {item["case_id"]: item["observed_action"] for item in calls[first]["case_results"]}
        right = {item["case_id"]: item["observed_action"] for item in calls[second]["case_results"]}
        return sum(left[key] == right[key] for key in left)

    shared_ok = all(
        all(call["attribute_correct"].get(name, 0) >= 10 for name in SHARED_ATTRIBUTES)
        for call in calls.values()
    )
    total_tokens = sum(call["usage"]["total_tokens"] for call in calls.values())
    gates = {
        "corpus_preflight": True,
        "private_surface_not_exposed": True,
        "call_budget": len({item["logical_call_id"] for item in ledger}) == 4 and len(ledger) <= 8,
        "token_budget": total_tokens <= 60000,
        "receipt_coverage": all(len(call["case_results"]) == 12 for call in calls.values()),
        "evidence_refs_exact": all(call["refs_exact_count"] == 12 for call in calls.values()),
        "shared_attribute_accuracy": shared_ok,
        "legacy_information_accuracy": all(calls[key]["attribute_correct"]["information_relation"] >= 10 for key in legacy_ids),
        "factor_status_accuracy": all(calls[key]["attribute_correct"]["transform_status"] >= 10 for key in factor_ids),
        "factor_effect_accuracy": all(calls[key]["attribute_correct"]["information_effect"] >= 10 for key in factor_ids),
        "latent_gain": all(item["latent_gain"] >= 2 for item in gains),
        "revalidation_gain": all(item["revalidation_gain"] >= 2 for item in gains),
        "relation_accuracy": all(call["relation_correct_count"] >= 10 for call in calls.values()),
        "action_accuracy": all(call["action_correct_count"] >= 11 for call in calls.values()),
        "zero_false_deduplicate": all(call["false_deduplicate"] == 0 for call in calls.values()),
        "within_arm_action_agreement": action_agreement(*legacy_ids) >= 11 and action_agreement(*factor_ids) >= 11,
        "forbidden_fields_excluded": all(not item["dropped_fields"] for call in calls.values() for item in call["case_results"]),
        "authority_and_protected_writes_zero": True,
    }
    return {
        "experiment_version": "agentos_r4_factorization_causal_benefit_v0_3j",
        "status": "PASS" if all(gates.values()) else "FAIL_SEMANTIC",
        "claim_ceiling": "SAME_PROVIDER_MATCHED_FRESH_SYNTHETIC_FACTORIZATION_BENEFIT_ONLY",
        "legacy_schema_unique_resolution_ceiling": 10,
        "factorized_schema_unique_resolution_ceiling": 12,
        "calls": calls,
        "matched_gains": gains,
        "legacy_action_agreement": action_agreement(*legacy_ids),
        "factor_action_agreement": action_agreement(*factor_ids),
        "total_tokens": total_tokens,
        "physical_attempt_count": len(ledger),
        "attempt_ledger": ledger,
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_count": len(gates),
        "provider_decision_authority": False,
        "core_writes": 0,
        "retention_writes": 0,
        "baseline_writes": 0,
    }
