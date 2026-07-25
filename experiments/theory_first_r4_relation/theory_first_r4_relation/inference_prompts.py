"""Frozen attribute-only prompt for R4 v0.3G."""

from __future__ import annotations

import json

from .inference_cases import ATTRIBUTE_NAMES, INFERENCE_CASES
from .transform_contracts import (
    ADDED_UNCERTAINTIES,
    INFORMATION_RELATIONS,
    LINEAGE_COUPLINGS,
    SOURCE_IDENTITIES,
    TARGET_CLAIM_RELATIONS,
)


SYSTEM_PROMPT = (
    "You are a semantic evidence analyst. Infer only the requested typed "
    "attributes from each case's admitted evidence. Do not decide whether to "
    "combine, block, deduplicate, accept, retain, or publish evidence. Preserve "
    "unknowns when material facts are missing. Return JSON only."
)


ATTRIBUTE_DEFINITIONS = {
    "source_identity": {
        "SAME_SOURCE": "both packets encode the same source item or observation",
        "PARTIAL_SOURCE": "one source is a strict subset or partial overlap of the other",
        "DISTINCT_SOURCE": "the packets encode distinct source items",
        "UNKNOWN_SOURCE": "available facts do not determine source identity",
    },
    "lineage_coupling": {
        "SAME_PIPELINE": "the packets share a derivation, collection, or processing pipeline",
        "SEPARATE_PIPELINES": "their relevant pipelines are independent",
        "UNKNOWN_PIPELINE": "pipeline coupling is materially unknown",
        "NOT_APPLICABLE": "pipeline coupling is not needed for this described relation",
    },
    "information_relation": {
        "VERIFIED_GLOBAL_EQUIVALENCE": "a verified transform preserves all information and is reversible",
        "VERIFIED_CLAIM_EQUIVALENCE": "a verified transform preserves all information relevant to the stated claim",
        "INFORMATION_REDUCING": "the transform removes target-relevant or potentially relevant information",
        "INFORMATION_AUGMENTING": "the transform adds derived information beyond representation change",
        "UNVERIFIED_TRANSFORM": "a transformation is asserted but its relevant behavior is not verified",
        "NOT_APPLICABLE": "neither packet is a transformation of the other",
    },
    "added_uncertainty": {
        "IMMATERIAL_FOR_CLAIM": "added uncertainty is explicitly below the stated claim tolerance",
        "MATERIAL_FOR_CLAIM": "added uncertainty can change the stated claim",
        "UNKNOWN_UNCERTAINTY": "added uncertainty is materially unknown",
        "NOT_APPLICABLE": "no transformation uncertainty applies",
    },
    "target_claim_relation": {
        "SAME_TARGET_CLAIM": "both packets are used for the same claim",
        "DIFFERENT_TARGET_CLAIM": "the packets are used for different claims",
        "UNKNOWN_TARGET_CLAIM": "the claim relationship is materially unknown",
    },
}


CASE_ORDER = (
    "R43G-01",
    "R43G-08",
    "R43G-03",
    "R43G-10",
    "R43G-05",
    "R43G-12",
    "R43G-02",
    "R43G-07",
    "R43G-04",
    "R43G-09",
    "R43G-06",
    "R43G-11",
)


def inference_batch_prompt() -> str:
    by_id = {case.case_id: case for case in INFERENCE_CASES}
    payload = {
        "allowed_values": {
            "source_identity": SOURCE_IDENTITIES,
            "lineage_coupling": LINEAGE_COUPLINGS,
            "information_relation": INFORMATION_RELATIONS,
            "added_uncertainty": ADDED_UNCERTAINTIES,
            "target_claim_relation": TARGET_CLAIM_RELATIONS,
        },
        "attribute_definitions": ATTRIBUTE_DEFINITIONS,
        "required_receipt_schema": {
            "case_id": "CASE_ID",
            "source_identity": "ONE_ALLOWED_VALUE",
            "lineage_coupling": "ONE_ALLOWED_VALUE",
            "information_relation": "ONE_ALLOWED_VALUE",
            "added_uncertainty": "ONE_ALLOWED_VALUE",
            "target_claim_relation": "ONE_ALLOWED_VALUE",
            "attribute_evidence_refs": {
                name: ["one or more admitted case-local evidence refs"]
                for name in ATTRIBUTE_NAMES
            },
            "missing_facts": [],
        },
        "cases": [by_id[case_id].public_dict() for case_id in CASE_ORDER],
    }
    return (
        "Return exactly one receipt for every case in a JSON object containing "
        "one receipt collection. For each attribute, cite only case-local "
        "evidence_refs that directly support the selected value. A statement "
        "that documents missing information can support an UNKNOWN value. Do "
        "not output relation states or Runtime actions.\n"
        + json.dumps(payload, ensure_ascii=True, sort_keys=True)
    )

