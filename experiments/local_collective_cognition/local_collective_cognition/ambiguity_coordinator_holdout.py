"""Fresh paired holdout for identity-blind ambiguity coordination."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .unstated_ambiguity_holdout import (
    CASES as PREDECESSOR_CASES, LEAKAGE_TERMS, NULL, POSITIVE, UnstatedAmbiguityCase,
)


BENCHMARK_VERSION = "ambiguity_coordinator_holdout_v0_1"
BENCHMARK_ID = "local-ambiguity-coordinator-holdout-v0-1"
EVIDENCE_REFS = (f"benchmark://{BENCHMARK_ID}",)

CASES = (
    UnstatedAmbiguityCase("C01", "rectangle-size", "land-parcel", "A rectangular plot is 18 metres long and 7 metres wide. Report its size as one integer.", POSITIVE),
    UnstatedAmbiguityCase("C02", "rectangle-size", "land-parcel", "A rectangular plot is 18 metres long and 7 metres wide. Report its area in square metres as one integer.", NULL),
    UnstatedAmbiguityCase("C03", "hex-size", "data-encoding", "The hexadecimal string 2F is stored. Report its size as one integer.", POSITIVE),
    UnstatedAmbiguityCase("C04", "hex-size", "data-encoding", "The hexadecimal string 2F is stored. Report its number of hexadecimal characters as one integer.", NULL),
    UnstatedAmbiguityCase("C05", "table-dimension", "data-table", "A table has 24 rows and 6 columns. Report its dimension as one integer.", POSITIVE),
    UnstatedAmbiguityCase("C06", "table-dimension", "data-table", "A table has 24 rows and 6 columns. Report its total cell count as one integer.", NULL),
    UnstatedAmbiguityCase("C07", "vote-support", "ballot", "A ballot records 72 support votes out of 120 votes. Report support as one number.", POSITIVE),
    UnstatedAmbiguityCase("C08", "vote-support", "ballot", "A ballot records 72 support votes out of 120 votes. Report the support percentage as one integer.", NULL),
    UnstatedAmbiguityCase("C09", "network-size", "topology", "An undirected network has 9 vertices and 14 edges. Report its size as one integer.", POSITIVE),
    UnstatedAmbiguityCase("C10", "network-size", "topology", "An undirected network has 9 vertices and 14 edges. Report its edge count as one integer.", NULL),
    UnstatedAmbiguityCase("C11", "compression", "file-storage", "A file is 800 KB before compression and 320 KB after compression. Report compression as one number.", POSITIVE),
    UnstatedAmbiguityCase("C12", "compression", "file-storage", "A file is 800 KB before compression and 320 KB after compression. Report the size reduction in KB as one integer.", NULL),
)

TRUTH_COMMITMENT = hash_payload([case.truth_commitment() for case in CASES])
SPEC_COMMITMENT = {
    "benchmark_version": BENCHMARK_VERSION,
    "theory_baseline": "Cognitive Research Architecture v3.7",
    "methodology_kernel": "v1.1",
    "inherited_role_candidate_state": "ROLE_COMPLEMENTARITY_OBSERVED_COORDINATOR_VALIDATION_REQUIRED",
    "object_before_proxy": {
        "upper_ontology_object": "collective resolution of task-object uncertainty",
        "project_object": "identity-blind semantic coordination over opposed discovery receipts",
        "observable_proxy": "coordinator state versus a frozen fixed-vote comparator",
        "metrics": ["balanced_accuracy", "positive_recall", "null_specificity", "balanced_gain", "cost_ratio"],
    },
    "case_count": len(CASES), "positive_count": 6, "null_count": 6,
    "truth_commitment": TRUTH_COMMITMENT,
    "frozen_comparator": "OR_POSITIVE",
    "frozen_gates": {
        "minimum_balanced_accuracy": 0.75,
        "minimum_positive_recall": 0.75,
        "minimum_null_specificity": 0.75,
        "minimum_balanced_gain_vs_frozen_comparator": 0.08,
        "maximum_uncertain_or_unavailable_rate": 0.25,
        "maximum_provider_call_ratio": 1.25,
        "maximum_token_ratio": 2.5,
    },
    "identity_blinding_required": True,
    "predecessor_label_reuse_forbidden": True,
    "selection_authority": False, "retention_authority": False,
}
HOLDOUT_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def validate_coordinator_holdout_spec(*, cases=CASES, spec=HOLDOUT_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    if spec.get("spec_hash") != hash_payload(commitment) or tuple(cases) != CASES:
        raise ValueError("ambiguity_coordinator_holdout_spec_invalid")
    if (len(cases) != 12 or len({case.item_id for case in cases}) != 12
            or any(term in case.prompt.lower() for case in cases for term in LEAKAGE_TERMS)):
        raise ValueError("ambiguity_coordinator_holdout_surface_invalid")
    predecessor_prompts = {case.prompt for case in PREDECESSOR_CASES}
    if ({case.item_id for case in cases} & {case.item_id for case in PREDECESSOR_CASES}
            or {case.prompt for case in cases} & predecessor_prompts):
        raise ValueError("ambiguity_coordinator_predecessor_reuse_invalid")
    for pair in {case.pair_id for case in cases}:
        if any(sum(case.pair_id == pair and case.expected_state == state for case in cases) != 1
               for state in (POSITIVE, NULL)):
            raise ValueError("ambiguity_coordinator_pairing_invalid")
