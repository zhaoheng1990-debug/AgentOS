"""Full semantic lineage binding for review-ready deltas v0.48."""

from __future__ import annotations

from .admission_opportunity_contract import (
    opportunity_delta_schema,
    validate_opportunity_delta,
)
from .lineage_displacement_contract import (
    LANE_BY_OPPORTUNITY,
    build_lineage_bound_delta_view,
)


CONTRACT_VERSION = "review_ready_lineage_contract_v0_48"
BOUND_AXES = (
    "relation_truth_state",
    "null_information_role",
    "constraint_binding",
    "expected_cbit",
    "research_value_disposition",
)


def build_review_ready_delta_view(
    *, raw_receipt, item, qualification_receipt, routing_receipt
):
    view = build_lineage_bound_delta_view(
        raw_receipt=raw_receipt,
        item=item,
        qualification_receipt=qualification_receipt,
        routing_receipt=routing_receipt,
    )
    commitment = {
        key: value for key, value in view.items()
        if key != "artifact_hash"
    }
    commitment["view_version"] = "review_ready_delta_view_v0_48"
    from .provider_telemetry import hash_payload
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def review_ready_delta_schema(*, item, refs):
    schema = opportunity_delta_schema(item=item, refs=refs)
    lineage_fields = [
        "source_opportunity_hash",
        "source_opportunity_type",
        "source_opportunity_evidence_span_ids",
        "proposed_admission_lane",
        *[f"source_opportunity_{axis}" for axis in BOUND_AXES],
    ]
    schema["required"].extend(lineage_fields)
    schema["properties"].update({
        "source_opportunity_hash": {
            "type": "string",
            "enum": [
                value["opportunity_hash"]
                for value in item["opportunity_bindings"]
            ],
        },
        "source_opportunity_type": {
            "type": "string", "enum": list(LANE_BY_OPPORTUNITY),
        },
        "source_opportunity_evidence_span_ids": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": [
                    value["span_id"]
                    for value in item["evidence_spans"]
                ],
            },
        },
        "proposed_admission_lane": {
            "type": "string",
            "enum": list(set(LANE_BY_OPPORTUNITY.values())),
        },
    })
    for axis in BOUND_AXES:
        values = {
            value[axis] for value in item["opportunity_bindings"]
        }
        schema["properties"][f"source_opportunity_{axis}"] = {
            "type": "string", "enum": sorted(values),
        }
    schema["anyOf"] = [
        {
            "properties": {
                "source_object_id": {
                    "const": value["source_object_id"],
                },
                "target_object_id": {
                    "const": value["target_object_id"],
                },
                "source_opportunity_hash": {
                    "const": value["opportunity_hash"],
                },
                "source_opportunity_type": {
                    "const": value["opportunity_type"],
                },
                "source_opportunity_evidence_span_ids": {
                    "const": value["evidence_span_ids"],
                },
                "proposed_admission_lane": {
                    "const": value["required_admission_lane"],
                },
                **{
                    f"source_opportunity_{axis}": {
                        "const": value[axis],
                    }
                    for axis in BOUND_AXES
                },
            },
            "required": [
                "source_object_id",
                "target_object_id",
                *lineage_fields,
            ],
        }
        for value in item["opportunity_bindings"]
    ]
    return schema


def validate_review_ready_delta(*, delta, item, refs):
    failures = validate_opportunity_delta(
        delta=delta, item=item, refs=refs
    )
    if not isinstance(delta, dict):
        return failures
    binding = next((
        value for value in item.get("opportunity_bindings", [])
        if value["source_object_id"] == delta.get("source_object_id")
        and value["target_object_id"] == delta.get("target_object_id")
    ), None)
    if binding is None:
        return [*failures, "REVIEW_LINEAGE_BINDING_MISSING"]
    exact = {
        "source_opportunity_hash": binding["opportunity_hash"],
        "source_opportunity_type": binding["opportunity_type"],
        "source_opportunity_evidence_span_ids": binding[
            "evidence_span_ids"
        ],
        "proposed_admission_lane": binding[
            "required_admission_lane"
        ],
        **{
            f"source_opportunity_{axis}": binding[axis]
            for axis in BOUND_AXES
        },
    }
    for field, expected in exact.items():
        if delta.get(field) != expected:
            failures.append(f"REVIEW_LINEAGE_{field.upper()}_MISMATCH")
    if not set(binding["evidence_span_ids"]).issubset(
        set(delta.get("evidence_span_ids", []))
    ):
        failures.append("REVIEW_LINEAGE_WARRANT_NOT_PRESERVED")
    for axis in BOUND_AXES:
        if delta.get(axis) != binding[axis]:
            failures.append(
                f"REVIEW_LINEAGE_SEMANTIC_AXIS_DRIFT:{axis}"
            )
    return failures

