"""Local policy derivation from minimal Provider semantic facts."""

from __future__ import annotations


def derive_policy_record(fact):
    scope = fact["outcome_scope"]
    support = fact["independent_effect_support"]
    context = fact["non_effect_context_relevance"]
    if scope == "TARGET_SEPARATELY_REPORTED":
        relation = "EXACT_OBJECT"
    elif scope == "TARGET_COMPONENT_OF_COMPOSITE":
        relation = "CONTEXTUAL_OBJECT"
    elif context:
        relation = "CONTEXTUAL_OBJECT"
    else:
        relation = "IRRELEVANT_OBJECT"
    context_retained = (
        scope in {
            "TARGET_SEPARATELY_REPORTED",
            "TARGET_COMPONENT_OF_COMPOSITE",
        }
        or context
    )
    if support:
        utility = "EFFECT_BEARING"
        disposition = "ADMIT_EVIDENCE"
        basis = "INDEPENDENT_EFFECT_SUPPORT"
    elif context_retained:
        utility = "CONTEXT_ONLY"
        disposition = "RETAIN_CONTEXT"
        basis = "TARGET_OR_CONTEXT_RELEVANCE"
    else:
        utility = "NONE"
        disposition = "REJECT"
        basis = "NO_TARGET_UTILITY"
    return {
        "span_id": fact["span_id"],
        "object_relation": relation,
        "evidence_utility": utility,
        "disposition": disposition,
        "effect_basis_codes": list(fact["effect_basis_codes"]),
        "policy_derivation_basis": basis,
    }
