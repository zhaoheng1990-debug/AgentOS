"""Runtime policy derivation from context-utility witnesses."""

from __future__ import annotations

from .admission_v6_facts import (
    context_fact_conflicts,
    effect_fact_conflicts,
    semantic_fact_conflicts,
)


def derive_policy_record(fact, *, span_text):
    effect_conflicts = effect_fact_conflicts(fact)
    context_conflicts = context_fact_conflicts(
        fact,
        span_text=span_text,
    )
    support = fact["independent_effect_support"] and not effect_conflicts
    intrinsic_target_context = (
        fact["exact_target_object_mentioned"]
        or fact["target_effect_separately_extractable"]
    )
    witnessed_context = (
        fact["context_utility_code"] != "NO_TARGET_UTILITY"
        and fact["context_changes_downstream_decision"]
        and not context_conflicts
    )
    if support:
        relation = "EXACT_OBJECT"
        utility = "EFFECT_BEARING"
        disposition = "ADMIT_EVIDENCE"
        bases = list(fact["effect_basis_codes"])
        derivation = "VALIDATED_INDEPENDENT_EFFECT_SUPPORT"
    elif intrinsic_target_context:
        relation = "CONTEXTUAL_OBJECT"
        utility = "TARGET_LOCAL_CONTEXT"
        disposition = "RETAIN_CONTEXT"
        bases = ["NOT_EFFECT_BEARING"]
        derivation = "INTRINSIC_TARGET_CONTEXT"
    elif witnessed_context:
        relation = "CONTEXTUAL_OBJECT"
        utility = fact["context_utility_code"]
        disposition = "RETAIN_CONTEXT"
        bases = ["NOT_EFFECT_BEARING"]
        derivation = "GROUNDED_CONTEXT_UTILITY_WITNESS"
    else:
        relation = "IRRELEVANT_OBJECT"
        utility = "NONE"
        disposition = "REJECT"
        bases = ["NOT_EFFECT_BEARING"]
        derivation = "NO_VALIDATED_TARGET_UTILITY"
    conflicts = semantic_fact_conflicts(fact, span_text=span_text)
    return {
        "span_id": fact["span_id"],
        "object_relation": relation,
        "evidence_utility": utility,
        "disposition": disposition,
        "effect_basis_codes": bases,
        "context_utility_code": fact["context_utility_code"],
        "utility_anchor_quote": fact["utility_anchor_quote"],
        "policy_derivation_basis": derivation,
        "effect_semantic_conflicts": effect_conflicts,
        "context_semantic_conflicts": context_conflicts,
        "semantic_conflicts": conflicts,
        "conflict_resolution": (
            "EFFECT_PRIORITY_CONTEXT_CONFLICT_IGNORED"
            if support and context_conflicts
            else "FAIL_CLOSED_TO_CONTEXT"
            if not support and intrinsic_target_context and conflicts
            else "FAIL_CLOSED_TO_REJECT"
            if disposition == "REJECT" and conflicts
            else "NONE"
        ),
    }
