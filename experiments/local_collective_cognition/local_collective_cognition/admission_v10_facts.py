"""Study-relation graph facts and witnesses for v0.85."""

from __future__ import annotations


BINDING_RELATIONS = (
    "TARGET_INTERVENTION_ALIAS",
    "TARGET_COMPARATOR_ALIAS",
    "TARGET_CONTRAST_COREFERENCE",
    "TARGET_OUTCOME_ALIAS",
    "COMPOSITE_OUTCOME_ALIAS",
    "RELATED_OUTCOME_ALIAS",
    "NON_TARGET_ARM",
)
COMPARISON_RELATIONS = (
    "TARGET_CONTRAST",
    "TARGET_SINGLE_ARM",
    "NON_TARGET_CONTRAST",
    "UNRESOLVED",
)
OUTCOME_RELATIONS = (
    "EXACT_TARGET_OUTCOME",
    "COMPOSITE_CONTAINS_TARGET",
    "RELATED_OUTCOME",
    "DIFFERENT_OUTCOME",
    "NOT_STATED",
)
EFFECT_RELATIONS = (
    "INDEPENDENT_COMPARATIVE_EFFECT",
    "TARGET_RELATED_CONTEXT",
    "NO_EFFECT_STATEMENT",
)
POOLING_RELATIONS = (
    "DIRECT_ARM_COMPARISON",
    "NONSEPARABLE_AGGREGATE",
    "NOT_APPLICABLE",
)
COREFERENCE_RELATIONS = (
    "SUPPORTED",
    "CONTRADICTED",
    "UNRESOLVED",
)
BINDING_FIELDS = (
    "binding_id",
    "surface_form",
    "relation",
    "anchor_quote",
    "rationale",
)
SPAN_FACT_FIELDS = (
    "span_id",
    "binding_refs",
    "comparison_relation",
    "outcome_relation",
    "effect_relation",
    "pooling_relation",
    "coreference_relation",
    "effect_anchor_quote",
    "relation_anchor_quote",
    "rationale",
)


def structural_binding_violations(binding):
    failures = []
    if set(binding) != set(BINDING_FIELDS):
        failures.append("ADMISSION_V10_BINDING_SHAPE_INVALID")
    if not isinstance(binding.get("binding_id"), str):
        failures.append("ADMISSION_V10_BINDING_ID_INVALID")
    if not isinstance(binding.get("surface_form"), str):
        failures.append("ADMISSION_V10_BINDING_SURFACE_INVALID")
    if binding.get("relation") not in BINDING_RELATIONS:
        failures.append("ADMISSION_V10_BINDING_RELATION_INVALID")
    for field in ("anchor_quote", "rationale"):
        if not isinstance(binding.get(field), str) or not binding[field].strip():
            failures.append(f"ADMISSION_V10_BINDING_{field.upper()}_INVALID")
    return sorted(set(failures))


def structural_span_fact_violations(fact):
    failures = []
    if set(fact) != set(SPAN_FACT_FIELDS):
        failures.append("ADMISSION_V10_SPAN_FACT_SHAPE_INVALID")
    refs = fact.get("binding_refs")
    if (
        not isinstance(refs, list)
        or len(refs) != len(set(refs))
        or not all(isinstance(value, str) for value in refs)
    ):
        failures.append("ADMISSION_V10_BINDING_REFS_INVALID")
    enums = {
        "comparison_relation": COMPARISON_RELATIONS,
        "outcome_relation": OUTCOME_RELATIONS,
        "effect_relation": EFFECT_RELATIONS,
        "pooling_relation": POOLING_RELATIONS,
        "coreference_relation": COREFERENCE_RELATIONS,
    }
    for field, allowed in enums.items():
        if fact.get(field) not in allowed:
            failures.append(f"ADMISSION_V10_{field.upper()}_INVALID")
    for field in ("effect_anchor_quote", "relation_anchor_quote", "rationale"):
        if not isinstance(fact.get(field), str):
            failures.append(f"ADMISSION_V10_{field.upper()}_INVALID")
    if isinstance(fact.get("rationale"), str) and not fact["rationale"].strip():
        failures.append("ADMISSION_V10_RATIONALE_MISSING")
    return sorted(set(failures))


def semantic_graph_conflicts(*, bindings, facts, spans):
    conflicts = []
    corpus = " ".join(" ".join(text.split()) for text in spans.values())
    normalized_corpus = corpus.casefold()
    binding_index = {value["binding_id"]: value for value in bindings}
    if len(binding_index) != len(bindings):
        conflicts.append("DUPLICATE_BINDING_ID")
    for binding in bindings:
        anchor = " ".join(binding["anchor_quote"].split())
        surface = " ".join(binding["surface_form"].split())
        if anchor.casefold() not in normalized_corpus:
            conflicts.append(
                f"{binding['binding_id']}:BINDING_ANCHOR_NOT_GROUNDED"
            )
        if surface.casefold() not in anchor.casefold():
            conflicts.append(
                f"{binding['binding_id']}:SURFACE_NOT_IN_BINDING_ANCHOR"
            )
    for fact in facts:
        span_id = fact["span_id"]
        text = " ".join(spans[span_id].split()).casefold()
        refs = set(fact["binding_refs"])
        unknown = refs - set(binding_index)
        if unknown:
            conflicts.append(f"{span_id}:UNKNOWN_BINDING_REF")
            continue
        relations = {
            binding_index[ref]["relation"] for ref in refs
        }
        if (
            fact["comparison_relation"] == "TARGET_CONTRAST"
            and not (
                "TARGET_CONTRAST_COREFERENCE" in relations
                or {
                    "TARGET_INTERVENTION_ALIAS",
                    "TARGET_COMPARATOR_ALIAS",
                }.issubset(relations)
            )
        ):
            conflicts.append(f"{span_id}:TARGET_CONTRAST_BINDING_MISSING")
        expected_outcome_binding = {
            "EXACT_TARGET_OUTCOME": "TARGET_OUTCOME_ALIAS",
            "COMPOSITE_CONTAINS_TARGET": "COMPOSITE_OUTCOME_ALIAS",
            "RELATED_OUTCOME": "RELATED_OUTCOME_ALIAS",
        }.get(fact["outcome_relation"])
        if (
            expected_outcome_binding
            and expected_outcome_binding not in relations
        ):
            conflicts.append(f"{span_id}:OUTCOME_BINDING_MISSING")
        effect_quote = " ".join(fact["effect_anchor_quote"].split())
        if fact["effect_relation"] == "INDEPENDENT_COMPARATIVE_EFFECT":
            if not effect_quote:
                conflicts.append(f"{span_id}:EFFECT_ANCHOR_MISSING")
            elif effect_quote.casefold() not in text:
                conflicts.append(f"{span_id}:EFFECT_ANCHOR_NOT_GROUNDED")
        elif effect_quote:
            conflicts.append(f"{span_id}:UNEXPECTED_EFFECT_ANCHOR")
        relation_quote = " ".join(fact["relation_anchor_quote"].split())
        if not relation_quote:
            conflicts.append(f"{span_id}:RELATION_ANCHOR_MISSING")
        elif relation_quote.casefold() not in text:
            conflicts.append(f"{span_id}:RELATION_ANCHOR_NOT_GROUNDED")
    return sorted(set(conflicts))


def evidence_witness(*, fact, bindings, spans, all_facts):
    return (
        fact["comparison_relation"] == "TARGET_CONTRAST"
        and fact["outcome_relation"] == "EXACT_TARGET_OUTCOME"
        and fact["effect_relation"] == "INDEPENDENT_COMPARATIVE_EFFECT"
        and fact["pooling_relation"] == "DIRECT_ARM_COMPARISON"
        and fact["coreference_relation"] == "SUPPORTED"
        and not semantic_graph_conflicts(
            bindings=bindings,
            facts=all_facts,
            spans=spans,
        )
    )


def context_witness(*, fact, bindings, spans, all_facts):
    negative = (
        fact["comparison_relation"] == "NON_TARGET_CONTRAST"
        or fact["outcome_relation"] == "DIFFERENT_OUTCOME"
        or fact["coreference_relation"] == "CONTRADICTED"
    )
    contextual = (
        fact["comparison_relation"] == "TARGET_SINGLE_ARM"
        or fact["outcome_relation"] in {
            "COMPOSITE_CONTAINS_TARGET",
            "RELATED_OUTCOME",
        }
        or fact["effect_relation"] == "TARGET_RELATED_CONTEXT"
        or (
            fact["outcome_relation"] == "EXACT_TARGET_OUTCOME"
            and fact["effect_relation"] == "NO_EFFECT_STATEMENT"
        )
        or fact["pooling_relation"] == "NONSEPARABLE_AGGREGATE"
    )
    return (
        not negative
        and contextual
        and fact["coreference_relation"] != "UNRESOLVED"
        and not semantic_graph_conflicts(
            bindings=bindings,
            facts=all_facts,
            spans=spans,
        )
    )
