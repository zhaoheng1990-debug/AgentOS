"""Observable structural fingerprints shared by the local holdout series."""

from __future__ import annotations


PREFIX_TO_FINGERPRINT = {
    "arithmetic": "arithmetic_expression",
    "logic": "quantifier_syllogism",
    "schedule": "partial_order_schedule",
    "implication": "implication_chain",
    "modular": "congruence_constraint",
    "probability": "without_replacement_probability",
    "sets": "inclusion_exclusion",
    "sequence": "difference_sequence",
    "rate": "constant_rate",
    "bayes": "bayesian_posterior",
    "code": "iterative_state_update",
    "string": "symbolic_string_transform",
    "causal": "causal_identification",
    "percent": "percentage_calculation",
    "ratio": "proportional_allocation",
    "average": "arithmetic_mean",
    "unit": "unit_rate",
}

FINGERPRINT_TO_DOMAIN = {
    "quantifier_syllogism": "formal",
    "partial_order_schedule": "formal",
    "implication_chain": "formal",
    "congruence_constraint": "quantitative",
    "without_replacement_probability": "quantitative",
    "inclusion_exclusion": "quantitative",
    "difference_sequence": "quantitative",
    "constant_rate": "quantitative",
    "bayesian_posterior": "quantitative",
    "iterative_state_update": "procedural",
    "symbolic_string_transform": "procedural",
    "causal_identification": "causal",
}

EXPERIMENTAL_FINGERPRINT_TO_DOMAIN = {
    "arithmetic_expression": "quantitative",
    "percentage_calculation": "quantitative",
    "proportional_allocation": "quantitative",
    "arithmetic_mean": "quantitative",
    "unit_rate": "quantitative",
}


def fingerprint_for_item(item_id: str) -> str:
    prefix = item_id.split("-", 1)[0]
    try:
        return PREFIX_TO_FINGERPRINT[prefix]
    except KeyError as exc:
        raise ValueError("task_fingerprint_prefix_unknown") from exc


def build_item_fingerprints(item_ids: tuple[str, ...]) -> dict[str, str]:
    fingerprints = {item_id: fingerprint_for_item(item_id) for item_id in item_ids}
    if len(fingerprints) != len(item_ids):
        raise ValueError("task_fingerprint_item_ids_invalid")
    return fingerprints


def validate_fingerprint_domains(item_domains: dict[str, str], item_fingerprints: dict[str, str]) -> None:
    if set(item_domains) != set(item_fingerprints):
        raise ValueError("task_fingerprint_coverage_invalid")
    domains = {**FINGERPRINT_TO_DOMAIN, **EXPERIMENTAL_FINGERPRINT_TO_DOMAIN}
    if any(domains[fingerprint] != item_domains[item_id] for item_id, fingerprint in item_fingerprints.items()):
        raise ValueError("task_fingerprint_domain_binding_invalid")
