"""Matched arm prompts for R4 v0.3J."""

from __future__ import annotations

import json

from .comparison_cases import (
    COMPARISON_CASES,
    FACTORIZED_ATTRIBUTES,
    FORWARD_ORDER,
    LEGACY_ATTRIBUTES,
    REVERSE_ORDER,
)
from .factor_contracts import INFORMATION_EFFECTS, TRANSFORM_STATUSES
from .inference_prompts import ATTRIBUTE_DEFINITIONS
from .transform_contracts import (
    ADDED_UNCERTAINTIES,
    INFORMATION_RELATIONS,
    LINEAGE_COUPLINGS,
    SOURCE_IDENTITIES,
    TARGET_CLAIM_RELATIONS,
)


SYSTEM_PROMPT = (
    "You are a semantic evidence analyst. Infer only the requested typed "
    "attributes from admitted case evidence. Preserve unknowns. Do not output "
    "relations, actions, revalidation decisions, acceptance, or retention. "
    "Return JSON only."
)
SHARED_ALLOWED = {
    "source_identity": SOURCE_IDENTITIES,
    "lineage_coupling": LINEAGE_COUPLINGS,
    "added_uncertainty": ADDED_UNCERTAINTIES,
    "target_claim_relation": TARGET_CLAIM_RELATIONS,
}
FACTOR_DEFINITIONS = {
    "transform_status": {
        "NO_TRANSFORM": "the packets are explicitly not transformations of one another",
        "VERIFIED_TRANSFORM": "a transformation and its relevant behavior are verified",
        "ASSERTED_UNVERIFIED_TRANSFORM": "a transformation is asserted but not verified",
        "UNKNOWN_TRANSFORM_APPLICABILITY": "whether a transformation relation exists is unknown",
    },
    "information_effect": {
        "GLOBAL_EQUIVALENT": "verified reversible full-domain information preservation",
        "CLAIM_EQUIVALENT": "verified preservation limited to the stated claim",
        "INFORMATION_REDUCING": "information is removed",
        "INFORMATION_AUGMENTING": "derived information is added",
        "UNKNOWN_EFFECT": "the information effect is unknown",
        "NOT_APPLICABLE": "no transformation information effect applies",
    },
}


def comparison_prompt(arm: str, reverse: bool) -> str:
    by_id = {case.case_id: case for case in COMPARISON_CASES}
    order = REVERSE_ORDER if reverse else FORWARD_ORDER
    if arm == "legacy":
        attributes = LEGACY_ATTRIBUTES
        allowed = SHARED_ALLOWED | {"information_relation": INFORMATION_RELATIONS}
        definitions = {
            name: ATTRIBUTE_DEFINITIONS[name] for name in LEGACY_ATTRIBUTES
        }
    elif arm == "factorized":
        attributes = FACTORIZED_ATTRIBUTES
        allowed = SHARED_ALLOWED | {
            "transform_status": TRANSFORM_STATUSES,
            "information_effect": INFORMATION_EFFECTS,
        }
        definitions = {
            **{
                name: ATTRIBUTE_DEFINITIONS[name]
                for name in SHARED_ALLOWED
            },
            **FACTOR_DEFINITIONS,
        }
    else:
        raise ValueError(f"unknown comparison arm: {arm}")
    schema = {
        "case_id": "CASE_ID",
        **{name: "ONE_ALLOWED_VALUE" for name in attributes},
        "attribute_evidence_refs": {
            name: ["one or more admitted case-local evidence refs"]
            for name in attributes
        },
        "missing_facts": [],
    }
    payload = {
        "allowed_values": allowed,
        "attribute_definitions": definitions,
        "required_receipt_schema": schema,
        "cases": [by_id[case_id].public_dict() for case_id in order],
    }
    return (
        "Return exactly one receipt per case in a JSON object containing one "
        "receipt collection. Cite only direct case-local evidence for each "
        "attribute. Do not emit any Runtime decision field.\n"
        + json.dumps(payload, ensure_ascii=True, sort_keys=True)
    )
