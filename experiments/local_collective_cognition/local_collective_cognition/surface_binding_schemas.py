"""Provider schema for v0.71 candidate-ID binding."""

from .benchmark_bridge_contracts import admission_partition
from .provider_telemetry import hash_payload
from .relation_witness_schemas import OBSERVED_RELATIONS
from .relational_contrast_types import (
    COORDINATE_BINDINGS,
    EVIDENCE_RELEVANCE,
    EVIDENCE_ROLES,
    REFERENCE_IDS,
    SIGNIFICANCE_STATES,
    SUBJECT_IDS,
)


def surface_binding_schema(*, item, admission, arm_catalog, frame, catalog, refs):
    admitted, _ = admission_partition(admission)
    ids = [value["candidate_id"] for value in catalog["candidates"]]
    record = _object({
        "span_id": {"type": "string", "enum": admitted},
        "evidence_relevance": {"type": "string", "enum": list(EVIDENCE_RELEVANCE)},
        "subject_group_id": {"type": "string", "enum": list(SUBJECT_IDS)},
        "reference_group_id": {"type": "string", "enum": list(REFERENCE_IDS)},
        "subject_surface_candidate_id": {
            "type": "string", "enum": ["IMPLICIT_SUBJECT", *ids]
        },
        "relation_surface_candidate_id": {"type": "string", "enum": ids},
        "timepoint_binding": {"type": "string", "enum": list(COORDINATE_BINDINGS)},
        "measurement_binding": {"type": "string", "enum": list(COORDINATE_BINDINGS)},
        "observed_relation": {"type": "string", "enum": list(OBSERVED_RELATIONS)},
        "significance_state": {"type": "string", "enum": list(SIGNIFICANCE_STATES)},
        "evidence_role": {"type": "string", "enum": list(EVIDENCE_ROLES)},
        "rationale": {"type": "string"},
    })
    return _object({
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {"type": "string", "enum": ["A7_SURFACE_ID_BINDING"]},
        "source_item_hash": {"type": "string", "enum": [hash_payload(item)]},
        "source_admission_hash": {"type": "string", "enum": [hash_payload(admission)]},
        "source_arm_catalog_hash": {"type": "string", "enum": [arm_catalog["catalog_hash"]]},
        "source_frame_hash": {"type": "string", "enum": [hash_payload(frame)]},
        "source_surface_catalog_hash": {"type": "string", "enum": [catalog["catalog_hash"]]},
        "all_admitted_spans_assessed": {"type": "boolean", "enum": [True]},
        "basis_records": {
            "type": "array",
            "minItems": len(admitted),
            "maxItems": len(admitted),
            "items": record,
        },
        "evidence_refs": {
            "type": "array",
            "minItems": len(refs),
            "maxItems": len(refs),
            "items": {"type": "string", "enum": list(refs)},
        },
    })


def _object(properties):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }
