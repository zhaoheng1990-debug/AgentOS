"""Mechanical grounding contracts for v0.69."""

from __future__ import annotations

from typing import Any

from .benchmark_bridge_contracts import admission_partition
from .benchmark_bridge_tasks import evidence_refs
from .provider_telemetry import hash_payload
from .relation_witness_schemas import OBSERVED_RELATIONS
from .relational_contrast_contracts import validate_relational_frame
from .relational_contrast_types import (
    COORDINATE_BINDINGS,
    EVIDENCE_RELEVANCE,
    EVIDENCE_ROLES,
    REFERENCE_IDS,
    SIGNIFICANCE_STATES,
    SUBJECT_IDS,
)


def validate_witness_frame(
    *, receipt, item, admission, catalog, refs
) -> list[str]:
    failures = validate_relational_frame(
        receipt=receipt,
        item=item,
        admission=admission,
        catalog=catalog,
        refs=refs,
    )
    admitted, _ = admission_partition(admission)
    text = " ".join(
        span["text"] for span in item["candidate_spans"]
        if span["span_id"] in set(admitted)
    ).casefold()
    canonical = {
        value["arm_id"]: value["canonical_text"].casefold()
        for value in catalog["arms"]
    }
    for field, arm_id in (
        ("intervention_aliases", "FOCAL_INTERVENTION"),
        ("comparator_aliases", "FOCAL_COMPARATOR"),
    ):
        aliases = receipt.get(field, [])
        if not any(
            alias.casefold() in text
            or alias.casefold() == canonical[arm_id]
            for alias in aliases if isinstance(alias, str)
        ):
            failures.append(f"WITNESS_{field.upper()}_UNGROUNDED")
    return sorted(set(failures))


def validate_witness_basis(
    *, receipt, item, admission, catalog, frame, refs
) -> list[str]:
    failures: list[str] = []
    expected = {
        "case_id": item["case_id"],
        "mechanism": "A5_RELATION_WITNESS_BASIS",
        "source_item_hash": hash_payload(item),
        "source_admission_hash": hash_payload(admission),
        "source_arm_catalog_hash": catalog["catalog_hash"],
        "source_frame_hash": hash_payload(frame),
        "evidence_refs": list(refs),
    }
    for field, value in expected.items():
        if receipt.get(field) != value:
            failures.append(f"WITNESS_{field.upper()}_MISMATCH")
    if receipt.get("frame_consumed") is not True:
        failures.append("WITNESS_FRAME_NOT_CONSUMED")
    records = receipt.get("basis_records")
    if not isinstance(records, list):
        return sorted(set([*failures, "WITNESS_BASIS_NOT_ARRAY"]))
    admitted, _ = admission_partition(admission)
    ids = [record.get("span_id") for record in records]
    if len(ids) != len(set(ids)) or set(ids) != set(admitted):
        failures.append("WITNESS_SPAN_COVERAGE_INVALID")
    spans = {
        span["span_id"]: span["text"]
        for span in item["candidate_spans"]
    }
    aliases = {
        "FOCAL_INTERVENTION": frame["intervention_aliases"],
        "FOCAL_COMPARATOR": frame["comparator_aliases"],
    }
    for record in records:
        failures.extend(_record_failures(record, spans, aliases))
    return sorted(set(failures))


def _record_failures(record, spans, aliases) -> list[str]:
    failures: list[str] = []
    checks = (
        ("evidence_relevance", EVIDENCE_RELEVANCE),
        ("subject_group_id", SUBJECT_IDS),
        ("reference_group_id", REFERENCE_IDS),
        ("timepoint_binding", COORDINATE_BINDINGS),
        ("measurement_binding", COORDINATE_BINDINGS),
        ("observed_relation", OBSERVED_RELATIONS),
        ("significance_state", SIGNIFICANCE_STATES),
        ("evidence_role", EVIDENCE_ROLES),
    )
    for field, allowed in checks:
        if record.get(field) not in allowed:
            failures.append(f"WITNESS_{field.upper()}_INVALID")
    text = spans.get(record.get("span_id"), "").casefold()
    relation_surface = record.get("relation_surface")
    if not isinstance(relation_surface, str) or (
        relation_surface.casefold() not in text
    ):
        failures.append("WITNESS_RELATION_SURFACE_UNGROUNDED")
    mode = record.get("subject_surface_mode")
    surface = record.get("subject_surface")
    subject = record.get("subject_group_id")
    if mode == "EXPLICIT_ALIAS":
        if (
            not isinstance(surface, str)
            or not surface
            or surface.casefold() not in text
            or subject not in aliases
            or surface.casefold()
            not in {value.casefold() for value in aliases.get(subject, [])}
        ):
            failures.append("WITNESS_SUBJECT_ALIAS_UNGROUNDED")
    elif mode == "FRAME_IMPLICIT":
        if surface != "" or record.get("observed_relation") != (
            "NO_COMPARATIVE_EFFECT_REPORTED"
        ):
            failures.append("WITNESS_IMPLICIT_SUBJECT_INVALID")
    else:
        failures.append("WITNESS_SUBJECT_SURFACE_MODE_INVALID")
    exact = (
        record.get("evidence_relevance") == "EXACT_OBJECT"
        and record.get("timepoint_binding") not in {"DIFFERENT", "UNRESOLVED"}
        and record.get("measurement_binding")
        not in {"DIFFERENT", "UNRESOLVED"}
    )
    if exact and record.get("evidence_role") == "EXCLUDE_UNRELATED":
        failures.append("WITNESS_EXACT_EVIDENCE_EXCLUDED")
    return failures
