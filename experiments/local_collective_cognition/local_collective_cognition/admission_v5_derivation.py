"""Fail-closed policy derivation from atomic semantic facts."""

from __future__ import annotations

from .admission_v5_facts import semantic_fact_conflicts


def derive_policy_record(fact):
    conflicts = semantic_fact_conflicts(fact)
    support = (
        fact["independent_effect_support"]
        and not conflicts
    )
    context = (
        fact["exact_target_object_mentioned"]
        or fact["target_effect_separately_extractable"]
        or fact["non_effect_context_relevance"]
    )
    if support:
        relation = "EXACT_OBJECT"
        utility = "EFFECT_BEARING"
        disposition = "ADMIT_EVIDENCE"
        bases = list(fact["effect_basis_codes"])
        derivation = "VALIDATED_INDEPENDENT_EFFECT_SUPPORT"
        resolution = "NONE"
    elif context:
        relation = "CONTEXTUAL_OBJECT"
        utility = "CONTEXT_ONLY"
        disposition = "RETAIN_CONTEXT"
        bases = ["NOT_EFFECT_BEARING"]
        derivation = "TARGET_OR_CONTEXT_RELEVANCE"
        resolution = (
            "FAIL_CLOSED_TO_CONTEXT"
            if conflicts
            else "NONE"
        )
    else:
        relation = "IRRELEVANT_OBJECT"
        utility = "NONE"
        disposition = "REJECT"
        bases = ["NOT_EFFECT_BEARING"]
        derivation = "NO_TARGET_UTILITY"
        resolution = (
            "FAIL_CLOSED_TO_REJECT"
            if conflicts
            else "NONE"
        )
    return {
        "span_id": fact["span_id"],
        "object_relation": relation,
        "evidence_utility": utility,
        "disposition": disposition,
        "effect_basis_codes": bases,
        "policy_derivation_basis": derivation,
        "semantic_conflicts": conflicts,
        "conflict_resolution": resolution,
    }
