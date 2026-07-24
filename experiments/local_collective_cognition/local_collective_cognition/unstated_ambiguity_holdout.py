"""Paired fresh holdout for endogenous discovery of underspecified task objects."""

from __future__ import annotations

from dataclasses import dataclass

from .provider_telemetry import hash_payload


BENCHMARK_VERSION = "unstated_ambiguity_holdout_v0_1"
BENCHMARK_ID = "local-unstated-ambiguity-holdout-v0-1"
EVIDENCE_REFS = (f"benchmark://{BENCHMARK_ID}",)
POSITIVE = "AMBIGUITY_PRESENT"
NULL = "NO_MATERIAL_AMBIGUITY"
LEAKAGE_TERMS = ("ambiguous", "ambiguity", "unclear", "unspecified", "does not say", "whether")


@dataclass(frozen=True)
class UnstatedAmbiguityCase:
    item_id: str
    pair_id: str
    domain: str
    prompt: str
    expected_state: str

    def public_input(self):
        return {"item_id": self.item_id, "task": self.prompt}

    def truth_commitment(self):
        return hash_payload({
            "item_id": self.item_id, "pair_id": self.pair_id, "domain": self.domain,
            "prompt": self.prompt, "expected_state": self.expected_state,
        })


CASES = (
    UnstatedAmbiguityCase("U01", "change", "inventory", "Inventory starts at 420 units and ends at 365 units. Report the change as one integer.", POSITIVE),
    UnstatedAmbiguityCase("U02", "change", "inventory", "Inventory starts at 420 units and ends at 365 units. Report signed ending-minus-starting change as one integer.", NULL),
    UnstatedAmbiguityCase("U03", "path", "graph", "A route is written as nodes A-B-C-D. Report its length as one integer.", POSITIVE),
    UnstatedAmbiguityCase("U04", "path", "graph", "A route is written as nodes A-B-C-D. Report the number of links between consecutive nodes.", NULL),
    UnstatedAmbiguityCase("U05", "interval", "sensor", "A sensor records one sample every minute from 09:10 through 09:55. Report the interval as one integer.", POSITIVE),
    UnstatedAmbiguityCase("U06", "interval", "sensor", "A sensor records one sample every minute from 09:10 through 09:55. Report elapsed minutes from start time to end time.", NULL),
    UnstatedAmbiguityCase("U07", "traffic", "service", "A service observes 360 requests during 90 seconds. Report traffic as one number.", POSITIVE),
    UnstatedAmbiguityCase("U08", "traffic", "service", "A service observes 360 requests during 90 seconds. Report the total observed request count.", NULL),
)


TRUTH_COMMITMENT = hash_payload([case.truth_commitment() for case in CASES])
SPEC_COMMITMENT = {
    "benchmark_version": BENCHMARK_VERSION,
    "theory_baseline": "Cognitive Research Architecture v3.7",
    "methodology_kernel": "v1.1",
    "object_before_proxy": {
        "upper_ontology_object": "endogenous cognitive object discovery under underspecification",
        "project_object": "material multi-interpretation task-framing state",
        "observable_proxy": "blind Provider discovery state plus optional rival packet",
        "metrics": ["balanced_accuracy", "positive_recall", "null_specificity", "null_false_positive_rate"],
    },
    "case_count": len(CASES), "positive_count": sum(case.expected_state == POSITIVE for case in CASES),
    "null_count": sum(case.expected_state == NULL for case in CASES),
    "truth_commitment": TRUTH_COMMITMENT,
    "frozen_gates": {
        "minimum_balanced_accuracy": 0.75, "minimum_positive_recall": 0.75,
        "minimum_null_specificity": 0.75, "maximum_null_false_positive_rate": 0.25,
    },
    "semantic_packet_quality_pending": True,
    "selection_authority": False, "retention_authority": False,
}
HOLDOUT_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def validate_holdout_spec(cases=CASES, spec=HOLDOUT_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    if spec.get("spec_hash") != hash_payload(commitment) or tuple(cases) != CASES:
        raise ValueError("unstated_ambiguity_holdout_spec_invalid")
    if (len(cases) != 8 or len({case.item_id for case in cases}) != len(cases)
            or {case.expected_state for case in cases} != {POSITIVE, NULL}
            or any(term in case.prompt.lower() for case in cases for term in LEAKAGE_TERMS)):
        raise ValueError("unstated_ambiguity_holdout_surface_invalid")
    pairs = {case.pair_id for case in cases}
    if any(sum(case.pair_id == pair and case.expected_state == state for case in cases) != 1
           for pair in pairs for state in (POSITIVE, NULL)):
        raise ValueError("unstated_ambiguity_holdout_pairing_invalid")
