"""Matched wide and responsibility-bounded prompts for R4 v0.3K."""

from __future__ import annotations

import json

from .comparison_prompts import FACTOR_DEFINITIONS
from .factor_contracts import INFORMATION_EFFECTS, TRANSFORM_STATUSES
from .inference_prompts import ATTRIBUTE_DEFINITIONS
from .role_cases import (
    EFFECT_ATTRIBUTES,
    FORWARD_ORDER,
    PROVENANCE_ATTRIBUTES,
    REVERSE_ORDER,
    ROLE_CASES,
    WIDE_ATTRIBUTES,
)
from .transform_contracts import (
    ADDED_UNCERTAINTIES,
    LINEAGE_COUPLINGS,
    SOURCE_IDENTITIES,
    TARGET_CLAIM_RELATIONS,
)


SYSTEM_PROMPT = (
    "You are a semantic evidence analyst. Infer only the requested typed "
    "attributes from admitted case evidence. Preserve unknowns. Do not output "
    "relations, actions, revalidation decisions, acceptance, retention, or "
    "publication state. Return JSON only."
)

ALLOWED_VALUES = {
    "source_identity": SOURCE_IDENTITIES,
    "lineage_coupling": LINEAGE_COUPLINGS,
    "transform_status": TRANSFORM_STATUSES,
    "information_effect": INFORMATION_EFFECTS,
    "added_uncertainty": ADDED_UNCERTAINTIES,
    "target_claim_relation": TARGET_CLAIM_RELATIONS,
}
ATTRIBUTE_DEFINITION_MAP = {
    **{
        name: ATTRIBUTE_DEFINITIONS[name]
        for name in (
            "source_identity",
            "lineage_coupling",
            "added_uncertainty",
            "target_claim_relation",
        )
    },
    **FACTOR_DEFINITIONS,
}
ATTRIBUTES_BY_SCOPE = {
    "wide": WIDE_ATTRIBUTES,
    "provenance": PROVENANCE_ATTRIBUTES,
    "effect": EFFECT_ATTRIBUTES,
}


def role_prompt(scope: str, reverse: bool) -> str:
    if scope not in ATTRIBUTES_BY_SCOPE:
        raise ValueError(f"unknown role scope: {scope}")
    attributes = ATTRIBUTES_BY_SCOPE[scope]
    by_id = {case.case_id: case for case in ROLE_CASES}
    order = REVERSE_ORDER if reverse else FORWARD_ORDER
    payload = {
        "allowed_values": {name: ALLOWED_VALUES[name] for name in attributes},
        "attribute_definitions": {
            name: ATTRIBUTE_DEFINITION_MAP[name] for name in attributes
        },
        "required_receipt_schema": {
            "case_id": "CASE_ID",
            **{name: "ONE_ALLOWED_VALUE" for name in attributes},
            "attribute_evidence_refs": {
                name: ["one or more admitted case-local evidence refs"]
                for name in attributes
            },
            "missing_facts": [],
        },
        "cases": [by_id[case_id].public_dict() for case_id in order],
    }
    return (
        "Return exactly one receipt per case in a JSON object containing one "
        "receipt collection. Cite only direct case-local evidence for each "
        "attribute. Do not emit any Runtime decision field.\n"
        + json.dumps(payload, ensure_ascii=True, sort_keys=True)
    )
