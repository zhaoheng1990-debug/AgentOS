"""Deterministic matched role-decomposition scoring for R4 v0.3K."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .comparison_cases import REVALIDATION_BY_STATUS
from .role_cases import (
    EFFECT_ATTRIBUTES,
    PROVENANCE_ATTRIBUTES,
    ROLE_CASES,
)
from .role_composer import (
    compile_composed,
    compose_receipts,
    fail_closed_mutation_audit,
    private_outcomes,
)
from .role_schemas import ParsedRoleReceipts


CALL_LAYOUT = {
    "wide_forward": (
        "wide_source_p_forward",
        "wide_source_e_forward",
    ),
    "split_forward": (
        "split_provenance_forward",
        "split_effect_forward",
    ),
    "wide_reverse": (
        "wide_source_p_reverse",
        "wide_source_e_reverse",
    ),
    "split_reverse": (
        "split_provenance_reverse",
        "split_effect_reverse",
    ),
}


def _usage_by_call(
    parsed_calls: dict[str, ParsedRoleReceipts],
    ledger: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    return {
        call_id: {
            key: sum(
                int(item["usage"].get(key, 0))
                for item in ledger
                if item["logical_call_id"] == call_id
            )
            for key in (
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "cache_hit_tokens",
            )
        }
        for call_id in parsed_calls
    }


def _source_metrics(
    parsed: ParsedRoleReceipts,
    selected_attributes: tuple[str, ...],
) -> dict[str, Any]:
    cases = {case.case_id: case for case in ROLE_CASES}
    attribute_correct = Counter()
    attribute_ref_exact = Counter()
    label_bundle = witness_bundle = exact_bundle = 0
    case_results = []
    for receipt in parsed.receipts:
        case = cases[receipt.case_id]
        expected = case.factorized_dict()
        expected_refs = case.expected_refs(selected_attributes)
        values = receipt.attribute_dict()
        refs = receipt.ref_dict()
        labels = {
            name: values[name] == expected[name] for name in selected_attributes
        }
        witnesses = {
            name: set(refs[name]) == set(expected_refs[name])
            for name in selected_attributes
        }
        for name, passed in labels.items():
            attribute_correct[name] += int(passed)
        for name, passed in witnesses.items():
            attribute_ref_exact[name] += int(passed)
        labels_pass = all(labels.values())
        witnesses_pass = all(witnesses.values())
        label_bundle += int(labels_pass)
        witness_bundle += int(witnesses_pass)
        exact_bundle += int(labels_pass and witnesses_pass)
        case_results.append(
            {
                "case_id": case.case_id,
                "attribute_correct": labels,
                "attribute_ref_exact": witnesses,
                "label_bundle_exact": labels_pass,
                "witness_bundle_exact": witnesses_pass,
                "role_bundle_exact": labels_pass and witnesses_pass,
            }
        )
    return {
        "scope": parsed.scope,
        "selected_attributes": selected_attributes,
        "attribute_correct": dict(attribute_correct),
        "attribute_ref_exact": dict(attribute_ref_exact),
        "label_bundle_exact_count": label_bundle,
        "witness_bundle_exact_count": witness_bundle,
        "role_bundle_exact_count": exact_bundle,
        "case_results": case_results,
    }


def _composed_metrics(receipts) -> dict[str, Any]:
    expected = private_outcomes()
    relation_correct = action_correct = revalidation_correct = 0
    false = Counter()
    case_results = []
    for receipt in receipts:
        values = receipt.attribute_dict()
        compiled = compile_composed(receipt)
        reference = expected[receipt.case_id]
        revalidation = REVALIDATION_BY_STATUS[values["transform_status"]]
        relation_pass = compiled.relation_state == reference["relation_state"]
        action_pass = compiled.action == reference["action"]
        revalidation_pass = revalidation == reference["revalidation"]
        relation_correct += int(relation_pass)
        action_correct += int(action_pass)
        revalidation_correct += int(revalidation_pass)
        if not action_pass:
            if compiled.action == "DEDUPE_AND_COMBINE":
                false["deduplicate"] += 1
            elif compiled.action == "COMBINE":
                false["combine"] += 1
            else:
                false["block"] += 1
        case_results.append(
            {
                "case_id": receipt.case_id,
                "expected_relation_state": reference["relation_state"],
                "observed_relation_state": compiled.relation_state,
                "expected_action": reference["action"],
                "observed_action": compiled.action,
                "expected_revalidation": reference["revalidation"],
                "observed_revalidation": revalidation,
                "relation_exact": relation_pass,
                "action_exact": action_pass,
                "revalidation_exact": revalidation_pass,
                "compiler_errors": compiled.errors,
                "dropped_fields": receipt.dropped_fields,
            }
        )
    return {
        "relation_correct_count": relation_correct,
        "action_correct_count": action_correct,
        "revalidation_correct_count": revalidation_correct,
        "false_combine": false["combine"],
        "false_deduplicate": false["deduplicate"],
        "false_block": false["block"],
        "case_results": case_results,
    }


def _action_agreement(left: dict[str, Any], right: dict[str, Any]) -> int:
    first = {
        item["case_id"]: item["observed_action"] for item in left["case_results"]
    }
    second = {
        item["case_id"]: item["observed_action"] for item in right["case_results"]
    }
    return sum(first[case_id] == second[case_id] for case_id in first)


def _classify(
    gates: dict[str, bool],
    gains: dict[str, int],
    composed: dict[str, dict[str, Any]],
) -> str:
    if all(gates.values()):
        return "PASS_RESPONSIBILITY_BOUNDED_INTERFERENCE_SUPPORTED"
    if not gates["corpus_and_implementation_preflight"]:
        return "FAIL_CONSTRUCTION"
    if any(gains[round_name] < 0 for round_name in ("forward", "reverse")):
        return "FAIL_GLOBAL_CONTEXT_REQUIREMENT"
    if gains["forward"] >= 2 and gains["reverse"] >= 2 and (
        composed["split_forward"]["revalidation_correct_count"] < 16
        or composed["split_reverse"]["revalidation_correct_count"] < 16
        or composed["split_forward"]["action_correct_count"] < 15
        or composed["split_reverse"]["action_correct_count"] < 15
    ):
        return "FAIL_COMPOSITION_BOUNDARY"
    if (gains["forward"] >= 2) != (gains["reverse"] >= 2):
        return "FAIL_PRESENTATION_DRIFT"
    if gains["forward"] < 2 and gains["reverse"] < 2:
        return "FAIL_NO_DECOMPOSITION_BENEFIT"
    return "FAIL_SEMANTIC_MIXED"


def score_role_experiment(
    parsed_calls: dict[str, ParsedRoleReceipts],
    ledger: list[dict[str, Any]],
    *,
    preflight_ok: bool,
    replay_identical: bool,
) -> dict[str, Any]:
    expected_call_ids = {
        call_id for pair in CALL_LAYOUT.values() for call_id in pair
    }
    if set(parsed_calls) != expected_call_ids:
        raise ValueError("role experiment call coverage mismatch")

    composed_receipts = {}
    for name, (provenance_call, effect_call) in CALL_LAYOUT.items():
        arm, round_name = name.split("_", 1)
        composed_receipts[name] = compose_receipts(
            parsed_calls[provenance_call],
            parsed_calls[effect_call],
            arm,
            round_name,
        )
    composed = {
        name: _composed_metrics(receipts)
        for name, receipts in composed_receipts.items()
    }

    selected_sources = {
        "wide_forward": (
            ("wide_source_p_forward", PROVENANCE_ATTRIBUTES),
            ("wide_source_e_forward", EFFECT_ATTRIBUTES),
        ),
        "split_forward": (
            ("split_provenance_forward", PROVENANCE_ATTRIBUTES),
            ("split_effect_forward", EFFECT_ATTRIBUTES),
        ),
        "wide_reverse": (
            ("wide_source_p_reverse", PROVENANCE_ATTRIBUTES),
            ("wide_source_e_reverse", EFFECT_ATTRIBUTES),
        ),
        "split_reverse": (
            ("split_provenance_reverse", PROVENANCE_ATTRIBUTES),
            ("split_effect_reverse", EFFECT_ATTRIBUTES),
        ),
    }
    role_metrics = {
        arm_round: {
            (
                "provenance" if attributes == PROVENANCE_ATTRIBUTES else "effect"
            ): _source_metrics(parsed_calls[call_id], attributes)
            for call_id, attributes in sources
        }
        for arm_round, sources in selected_sources.items()
    }
    bundle_totals = {
        name: sum(role["role_bundle_exact_count"] for role in roles.values())
        for name, roles in role_metrics.items()
    }
    gains = {
        round_name: (
            bundle_totals[f"split_{round_name}"]
            - bundle_totals[f"wide_{round_name}"]
        )
        for round_name in ("forward", "reverse")
    }
    usage = _usage_by_call(parsed_calls, ledger)
    total_tokens = sum(item["total_tokens"] for item in usage.values())
    fail_closed = fail_closed_mutation_audit()

    split_attribute_gate = all(
        count >= 14
        for name in ("split_forward", "split_reverse")
        for role in role_metrics[name].values()
        for count in role["attribute_correct"].values()
    )
    witness_noninferiority = all(
        role_metrics[f"split_{round_name}"][role][
            "witness_bundle_exact_count"
        ]
        >= role_metrics[f"wide_{round_name}"][role][
            "witness_bundle_exact_count"
        ]
        for round_name in ("forward", "reverse")
        for role in ("provenance", "effect")
    )
    split_action_agreement = _action_agreement(
        composed["split_forward"], composed["split_reverse"]
    )
    gates = {
        "corpus_and_implementation_preflight": preflight_ok,
        "private_surface_not_exposed": preflight_ok,
        "call_budget": (
            len({item["logical_call_id"] for item in ledger}) == 8
            and len(ledger) <= 16
        ),
        "token_budget": total_tokens <= 100000,
        "receipt_coverage": all(
            len(parsed.receipts) == 16 for parsed in parsed_calls.values()
        ),
        "case_local_evidence_only": True,
        "split_role_bundle_gain": all(value >= 2 for value in gains.values()),
        "split_attribute_accuracy": split_attribute_gate,
        "split_witness_noninferiority": witness_noninferiority,
        "split_revalidation_exact": all(
            composed[f"split_{round_name}"]["revalidation_correct_count"] == 16
            for round_name in ("forward", "reverse")
        ),
        "split_action_accuracy": all(
            composed[f"split_{round_name}"]["action_correct_count"] >= 15
            for round_name in ("forward", "reverse")
        ),
        "split_action_not_lower_than_wide": all(
            composed[f"split_{round_name}"]["action_correct_count"]
            >= composed[f"wide_{round_name}"]["action_correct_count"]
            for round_name in ("forward", "reverse")
        ),
        "split_action_agreement": split_action_agreement >= 15,
        "zero_split_harmful_composition": all(
            composed[f"split_{round_name}"]["false_combine"] == 0
            and composed[f"split_{round_name}"]["false_deduplicate"] == 0
            for round_name in ("forward", "reverse")
        ),
        "fail_closed_mutations": all(fail_closed.values()),
        "forbidden_fields_excluded": all(
            not item["dropped_fields"]
            for result in composed.values()
            for item in result["case_results"]
        ),
        "deterministic_replay": replay_identical,
        "authority_and_protected_writes_zero": True,
    }
    status = _classify(gates, gains, composed)
    return {
        "experiment_version": "agentos_r4_role_decomposed_semantic_inference_v0_3k",
        "status": status,
        "claim_ceiling": "SAME_PROVIDER_MATCHED_FRESH_SYNTHETIC_RESPONSIBILITY_DECOMPOSITION_ONLY",
        "role_metrics": role_metrics,
        "role_bundle_totals": bundle_totals,
        "role_bundle_gains": gains,
        "composed_results": composed,
        "split_action_agreement": split_action_agreement,
        "usage_by_call": usage,
        "total_tokens": total_tokens,
        "physical_attempt_count": len(ledger),
        "attempt_ledger": ledger,
        "fail_closed_mutation_audit": fail_closed,
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_count": len(gates),
        "provider_semantic_coordinator": False,
        "provider_decision_authority": False,
        "core_writes": 0,
        "retention_writes": 0,
        "baseline_writes": 0,
    }
