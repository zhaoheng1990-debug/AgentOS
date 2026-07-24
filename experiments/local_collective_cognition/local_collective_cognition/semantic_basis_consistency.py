"""Mechanical consistency checks over Provider-issued semantic coordinates."""

from __future__ import annotations

from typing import Any


def semantic_consistency_failures(
    *,
    basis: dict[str, Any],
    synthesis: dict[str, Any],
) -> list[str]:
    records = {
        value["span_id"]: value for value in basis["basis_records"]
    }
    failures: list[str] = []
    mapping = {
        "primary_span_ids": "DECISIVE",
        "corroborating_span_ids": "SUPPORTING",
        "counter_span_ids": "COUNTER",
        "rejected_after_basis_span_ids": "REJECT_AFTER_BASIS",
    }
    for field, expected in mapping.items():
        for span_id in synthesis[field]:
            if records[span_id]["admissibility"] != expected:
                failures.append(
                    f"CONSISTENCY_{field.upper()}_STATE_MISMATCH"
                )
    primary = synthesis["primary_span_ids"]
    if synthesis["decision_state"] == "DECISIVE" and not primary:
        failures.append("CONSISTENCY_DECISIVE_PRIMARY_REQUIRED")
    label = synthesis["predicted_label"]
    if label in {"INCREASED", "DECREASED"}:
        supported = {
            _normalized_effect(records[span_id])
            for span_id in primary
            if records[span_id]["significance_state"] == "SIGNIFICANT"
            and records[span_id]["outcome_binding"] in {"EXACT", "PROXY"}
        }
        if label not in supported:
            failures.append("CONSISTENCY_EFFECT_NOT_SUPPORTED")
    if label == "NO_DIFFERENCE":
        qualifying = [
            records[span_id]
            for span_id in primary
            if records[span_id]["outcome_binding"] in {"EXACT", "PROXY"}
        ]
        if not qualifying or any(
            value["significance_state"] == "SIGNIFICANT"
            and _normalized_effect(value) in {"INCREASED", "DECREASED"}
            for value in qualifying
        ):
            failures.append("CONSISTENCY_NULL_NOT_SUPPORTED")
        if not any(
            value["significance_state"]
            in {"NOT_SIGNIFICANT", "TREND_OR_BORDERLINE"}
            or value["observed_direction"] == "NO_MATERIAL_DIFFERENCE"
            for value in qualifying
        ):
            failures.append("CONSISTENCY_NULL_BASIS_MISSING")
    return sorted(set(failures))


def _normalized_effect(record: dict[str, Any]) -> str | None:
    orientation = record["comparison_orientation"]
    direction = record["observed_direction"]
    if direction not in {"HIGHER", "LOWER"}:
        return None
    if orientation == "INTERVENTION_VS_COMPARATOR":
        return "INCREASED" if direction == "HIGHER" else "DECREASED"
    if orientation == "COMPARATOR_VS_INTERVENTION":
        return "DECREASED" if direction == "HIGHER" else "INCREASED"
    return None
