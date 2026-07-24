"""Independent hard-null holdout for material ambiguity coordination."""

from __future__ import annotations

from dataclasses import dataclass

from .ambiguity_coordinator_holdout import CASES as COORDINATOR_V01_CASES
from .provider_telemetry import hash_payload
from .unstated_ambiguity_holdout import (
    CASES as DISCOVERY_V04_CASES,
    LEAKAGE_TERMS,
    NULL,
    POSITIVE,
)


BENCHMARK_VERSION = "ambiguity_hard_null_holdout_v0_1"
BENCHMARK_ID = "local-ambiguity-hard-null-holdout-v0-1"
EVIDENCE_REFS = (f"benchmark://{BENCHMARK_ID}",)

MATERIALITY_CONTROL = {
    "control_version": "material_ambiguity_control_v0_1",
    "positive_iff": [
        "at_least_two_interpretations_target_the_requested_output_object",
        "both_interpretations_satisfy_all_explicit_task_constraints",
        "the_interpretations_change_the_required_operation_boundary_unit_or_output",
        "the_prompt_contains_no_decisive_disambiguating_qualifier",
    ],
    "null_if_any": [
        "a_unit_boundary_direction_or_operation_selects_one_interpretation",
        "the_second_interpretation_requires_invented_context",
        "the_rivals_are_semantic_paraphrases_or_produce_the_same_output",
        "the_difference_is_merely_wording_without_decision_consequence",
    ],
}
MATERIALITY_CONTROL_HASH = hash_payload(MATERIALITY_CONTROL)

RECEIPT_QUALITY_CONTROL = {
    "control_version": "ambiguity_receipt_quality_control_v0_1",
    "usable_material_support_requires": [
        "receipt_is_complete_and_provider_completed",
        "both_rivals_are_grounded_in_the_public_task",
        "rivals_are_semantically_distinct_not_paraphrases",
        "decisive_contrast_changes_operation_boundary_unit_or_output",
        "discriminating_question_resolves_the_rivals_without_solving_the_task",
    ],
    "invalid_support_states": [
        "SEMANTICALLY_COLLAPSED",
        "UNGROUNDED_OR_INVENTED",
        "INCOMPLETE",
        "UNRESOLVED",
    ],
    "positive_decision_requires_usable_material_support": True,
    "confidence_verbosity_position_and_model_identity_are_not_quality_evidence": True,
}
RECEIPT_QUALITY_CONTROL_HASH = hash_payload(RECEIPT_QUALITY_CONTROL)


@dataclass(frozen=True)
class HardNullAmbiguityCase:
    item_id: str
    domain: str
    prompt: str
    expected_state: str
    case_class: str
    construction_basis: str

    def public_input(self):
        return {"item_id": self.item_id, "task": self.prompt}

    def truth_commitment(self):
        return hash_payload({
            "item_id": self.item_id,
            "domain": self.domain,
            "prompt": self.prompt,
            "expected_state": self.expected_state,
            "case_class": self.case_class,
            "construction_basis": self.construction_basis,
        })


CASES = (
    HardNullAmbiguityCase(
        "HN01", "battery-test",
        "A rechargeable cell is rated at 72 ampere-hours and delivered 58 ampere-hours in a discharge test. Report its rated capacity in ampere-hours as one integer.",
        NULL, "HARD_NULL", "rated selects nominal rather than measured capacity",
    ),
    HardNullAmbiguityCase(
        "HN02", "digital-archive",
        "A digital archive contains 480 documents occupying 3.2 gigabytes. Report the archive size as one number.",
        POSITIVE, "MATERIAL_POSITIVE", "size may denote document count or storage footprint",
    ),
    HardNullAmbiguityCase(
        "HN03", "workshop-output",
        "A workshop completed 84 of 96 scheduled jobs. Report the completion percentage, rounded to the nearest integer.",
        NULL, "HARD_NULL", "percentage and rounding select one operation",
    ),
    HardNullAmbiguityCase(
        "HN04", "consumer-loan",
        "A loan has a principal of 10000 dollars and requires total repayments of 12400 dollars. Report the loan cost as one integer.",
        POSITIVE, "MATERIAL_POSITIVE", "cost may denote finance charge or total repayment",
    ),
    HardNullAmbiguityCase(
        "HN05", "class-attendance",
        "A class has 30 enrolled students and 24 students present. Report attendance as one integer.",
        POSITIVE, "MATERIAL_POSITIVE", "attendance may denote present count or attendance percentage",
    ),
    HardNullAmbiguityCase(
        "HN06", "delivery-route",
        "A delivery route visits six stops and covers 18 kilometres. Report the route length in kilometres as one integer.",
        NULL, "HARD_NULL", "kilometres select travelled distance rather than stop count",
    ),
    HardNullAmbiguityCase(
        "HN07", "software-package",
        "A software package includes 14 modules containing 260 functions in total. Report the number of modules as one integer.",
        NULL, "HARD_NULL", "the requested object and unit are explicit despite a competing count",
    ),
    HardNullAmbiguityCase(
        "HN08", "battery-test",
        "A battery is rated at 72 ampere-hours and delivered 58 ampere-hours in a discharge test. Report its capacity as one integer.",
        POSITIVE, "MATERIAL_POSITIVE", "capacity may denote rated or measured delivered capacity",
    ),
    HardNullAmbiguityCase(
        "HN09", "service-plan",
        "A service plan lists a base fee of 25 dollars and a total invoice of 65 dollars. Report its price as one integer.",
        POSITIVE, "MATERIAL_POSITIVE", "price may denote listed base fee or total charged amount",
    ),
    HardNullAmbiguityCase(
        "HN10", "storage-bin",
        "A storage bin measures 2 metres by 3 metres by 4 metres. Report its volume in cubic metres as one integer.",
        NULL, "HARD_NULL", "volume and cubic metres select one geometric operation",
    ),
    HardNullAmbiguityCase(
        "HN11", "classifier-evaluation",
        "A classifier evaluation contains 45 true positives, 5 false positives, 10 false negatives, and 40 true negatives. Report model performance as one percentage.",
        POSITIVE, "MATERIAL_POSITIVE", "performance may denote accuracy precision recall or another metric",
    ),
    HardNullAmbiguityCase(
        "HN12", "machine-uptime",
        "A machine ran for 54 minutes during a 60-minute observation. Report uptime percentage, rounded to the nearest integer.",
        NULL, "HARD_NULL", "percentage fixes normalization despite count and duration alternatives",
    ),
    HardNullAmbiguityCase(
        "HN13", "warehouse-stock",
        "A warehouse stores 18 cartons with 24 units in each carton. Report its stock as one integer.",
        POSITIVE, "MATERIAL_POSITIVE", "stock may denote cartons or individual units",
    ),
    HardNullAmbiguityCase(
        "HN14", "image-resolution",
        "An image is 1600 pixels wide and 900 pixels high. Report its vertical resolution in pixels as one integer.",
        NULL, "HARD_NULL", "vertical and pixels select the height dimension",
    ),
    HardNullAmbiguityCase(
        "HN15", "server-throughput",
        "A server completed 900 requests during 60 seconds. Report throughput as one integer.",
        POSITIVE, "MATERIAL_POSITIVE", "throughput may denote completed count or completion rate",
    ),
    HardNullAmbiguityCase(
        "HN16", "recipe-scaling",
        "A recipe uses 3 cups of flour to make 12 servings. Report the flour per serving as one decimal number.",
        NULL, "HARD_NULL", "per serving selects division rather than total flour",
    ),
)

TRUTH_COMMITMENT = hash_payload([case.truth_commitment() for case in CASES])
PREDECESSOR_COMMITMENTS = {
    "unstated_ambiguity_holdout": hash_payload(
        [case.truth_commitment() for case in DISCOVERY_V04_CASES]
    ),
    "ambiguity_coordinator_holdout": hash_payload(
        [case.truth_commitment() for case in COORDINATOR_V01_CASES]
    ),
}
SPEC_COMMITMENT = {
    "benchmark_version": BENCHMARK_VERSION,
    "theory_baseline": "Cognitive Research Architecture v3.7",
    "methodology_kernel": "v1.1",
    "object_before_proxy": {
        "upper_ontology_object": "collective resolution of task-object uncertainty",
        "project_object": "material ambiguity discrimination under hard-null pressure",
        "observable_proxy": "identity-blind controlled coordination over anonymous discovery receipts",
        "metrics": [
            "balanced_accuracy",
            "positive_recall",
            "hard_null_specificity",
            "balanced_gain",
            "receipt_control_consistency",
            "cost_ratio",
        ],
    },
    "case_count": len(CASES),
    "positive_count": sum(case.expected_state == POSITIVE for case in CASES),
    "hard_null_count": sum(case.case_class == "HARD_NULL" for case in CASES),
    "truth_commitment": TRUTH_COMMITMENT,
    "predecessor_commitments": PREDECESSOR_COMMITMENTS,
    "materiality_control": MATERIALITY_CONTROL,
    "materiality_control_hash": MATERIALITY_CONTROL_HASH,
    "receipt_quality_control": RECEIPT_QUALITY_CONTROL,
    "receipt_quality_control_hash": RECEIPT_QUALITY_CONTROL_HASH,
    "frozen_comparator": "OR_POSITIVE",
    "frozen_gates": {
        "minimum_balanced_accuracy": 0.75,
        "minimum_positive_recall": 0.75,
        "minimum_hard_null_specificity": 0.80,
        "minimum_balanced_gain_vs_frozen_comparator": 0.08,
        "minimum_receipt_control_consistency": 1.0,
        "maximum_low_quality_positive_rate": 0.0,
        "maximum_uncertain_or_unavailable_rate": 0.25,
        "maximum_provider_call_ratio": 1.25,
        "maximum_token_ratio": 2.5,
    },
    "labels_available_to_providers": False,
    "predecessor_labels_available_for_tuning": False,
    "prompt_or_gate_adaptation_after_reveal_forbidden": True,
    "selection_authority": False,
    "retention_authority": False,
}
HOLDOUT_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def validate_hard_null_holdout_spec(*, cases=CASES, spec=HOLDOUT_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    if spec.get("spec_hash") != hash_payload(commitment) or tuple(cases) != CASES:
        raise ValueError("ambiguity_hard_null_holdout_spec_invalid")
    if (
        len(cases) != 16
        or len({case.item_id for case in cases}) != len(cases)
        or sum(case.expected_state == POSITIVE for case in cases) != 8
        or sum(case.case_class == "HARD_NULL" for case in cases) != 8
        or any(term in case.prompt.lower() for case in cases for term in LEAKAGE_TERMS)
    ):
        raise ValueError("ambiguity_hard_null_holdout_surface_invalid")
    predecessor_ids = {
        case.item_id for case in (*DISCOVERY_V04_CASES, *COORDINATOR_V01_CASES)
    }
    predecessor_prompts = {
        case.prompt for case in (*DISCOVERY_V04_CASES, *COORDINATOR_V01_CASES)
    }
    if ({case.item_id for case in cases} & predecessor_ids
            or {case.prompt for case in cases} & predecessor_prompts):
        raise ValueError("ambiguity_hard_null_predecessor_reuse_invalid")
    if (
        spec.get("materiality_control_hash") != hash_payload(spec["materiality_control"])
        or spec.get("receipt_quality_control_hash")
        != hash_payload(spec["receipt_quality_control"])
    ):
        raise ValueError("ambiguity_hard_null_control_commitment_invalid")
