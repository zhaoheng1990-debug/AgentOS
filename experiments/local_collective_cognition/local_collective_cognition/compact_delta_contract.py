"""Compact provider contract and Runtime materialization for v0.42."""

from __future__ import annotations

import copy

from .candidate_pool_arbitration import relation_id
from .frontier_partial_admission import TEST_COSTS
from .null_role_candidate_composition import (
    DISCRIMINATING_NULL_ROLES,
    SCORE_MAP,
)
from .provider_telemetry import hash_payload
from .selective_delta_policy import (
    MAXIMUM_DELTA_EVIDENCE_SPANS,
    POLICY_VERSION as QUALIFICATION_POLICY_VERSION,
)


CONTRACT_VERSION = "compact_semantic_delta_v0_42"
VIEW_VERSION = "compact_delta_view_v0_42"
ROUTE_ORIGINS = {
    "MECHANISM": "EVIDENCE",
    "ADVERSARIAL": "COUNTERFACTUAL",
    "COORDINATE_SHIFT": "COORDINATE_SHIFT",
}


def build_compact_delta_view(
    *, raw_receipt, item, qualification_receipt
):
    used_span_ids = {
        span_id
        for candidate in raw_receipt["problem_candidates"]
        for span_id in candidate.get("evidence_span_ids", [])
    }
    ordered_spans = sorted(
        item["evidence_spans"],
        key=lambda value: (
            value["span_id"] in used_span_ids,
            hash_payload([
                CONTRACT_VERSION,
                qualification_receipt["artifact_hash"],
                value["span_id"],
            ]),
        ),
    )
    excluded_relations = sorted(
        (
            {
                "source_object_id": candidate["source_object_id"],
                "target_object_id": candidate["target_object_id"],
            }
            for candidate in raw_receipt["problem_candidates"]
        ),
        key=lambda value: (
            value["source_object_id"], value["target_object_id"]
        ),
    )
    commitment = {
        "view_version": VIEW_VERSION,
        "case_id": item["case_id"],
        "domain": item["domain"],
        "research_goal": item["research_goal"],
        "object_registry": copy.deepcopy(item["object_registry"]),
        "evidence_spans": copy.deepcopy(
            ordered_spans[:MAXIMUM_DELTA_EVIDENCE_SPANS]
        ),
        "excluded_relations": excluded_relations,
        "source_qualification_hash": qualification_receipt[
            "artifact_hash"
        ],
        "source_qualification_policy_version": (
            QUALIFICATION_POLICY_VERSION
        ),
        "private_truth_used": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def compact_delta_schema(*, item, refs):
    object_ids = [
        value["object_id"] for value in item["object_registry"]
    ]
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    properties = {
        "case_id": {
            "type": "string", "enum": [item["case_id"]],
        },
        "source_object_id": {
            "type": "string", "enum": object_ids,
        },
        "target_object_id": {
            "type": "string", "enum": object_ids,
        },
        "question": {"type": "string"},
        "constraint_object_ids": {
            "type": "array",
            "items": {"type": "string", "enum": object_ids},
        },
        "falsifier": {"type": "string"},
        "required_observation": {"type": "string"},
        "evidence_span_ids": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {"type": "string", "enum": span_ids},
        },
        "estimated_test_cost": {
            "type": "string", "enum": list(TEST_COSTS),
        },
        **{
            axis: {"type": "string", "enum": list(mapping)}
            for axis, mapping in SCORE_MAP.items()
        },
        "rationale": {"type": "string"},
        "evidence_refs": {
            "type": "array",
            "items": {"type": "string", "enum": list(refs)},
        },
    }
    pair_exclusions = [
        {
            "not": {
                "properties": {
                    "source_object_id": {
                        "const": value["source_object_id"]
                    },
                    "target_object_id": {
                        "const": value["target_object_id"]
                    },
                },
                "required": [
                    "source_object_id", "target_object_id"
                ],
            }
        }
        for value in item["excluded_relations"]
    ]
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }
    if pair_exclusions:
        schema["allOf"] = pair_exclusions
    return schema


def validate_compact_delta(*, delta, item, refs):
    failures = []
    if not isinstance(delta, dict):
        return ["COMPACT_DELTA_NOT_OBJECT"]
    if delta.get("case_id") != item["case_id"]:
        failures.append("CASE_BINDING_MISMATCH")
    if delta.get("evidence_refs") != list(refs):
        failures.append("EVIDENCE_SCOPE_MISMATCH")
    source = delta.get("source_object_id")
    target = delta.get("target_object_id")
    objects = {
        value["object_id"] for value in item["object_registry"]
    }
    if source not in objects or target not in objects or source == target:
        failures.append("DELTA_OBJECT_BINDING_INVALID")
    pair = {
        "source_object_id": source,
        "target_object_id": target,
    }
    if pair in item["excluded_relations"]:
        failures.append("DELTA_RELATION_NOT_DISTINCT")
    spans = delta.get("evidence_span_ids")
    allowed_spans = {
        value["span_id"] for value in item["evidence_spans"]
    }
    if (
        not isinstance(spans, list)
        or not spans
        or len(set(spans)) != len(spans)
        or not set(spans).issubset(allowed_spans)
    ):
        failures.append("DELTA_EVIDENCE_BINDING_INVALID")
    for axis, mapping in SCORE_MAP.items():
        if delta.get(axis) not in mapping:
            failures.append(f"DELTA_VALUE_AXIS_INVALID:{axis}")
    truth_state = delta.get("relation_truth_state")
    null_role = delta.get("null_information_role")
    if (
        truth_state == "SUPPORTED_NULL"
        and null_role == "NOT_APPLICABLE"
    ):
        failures.append("SUPPORTED_NULL_INFORMATION_ROLE_MISSING")
    if (
        truth_state == "SUPPORTED_NULL"
        and null_role in DISCRIMINATING_NULL_ROLES
        and delta.get("research_value_disposition") == "DISCARD"
    ):
        failures.append("DISCRIMINATING_NULL_DISCARDED")
    if (
        truth_state == "SUPPORTED_NULL"
        and null_role in DISCRIMINATING_NULL_ROLES
        and delta.get("expected_cbit") == "NEGATIVE"
    ):
        failures.append("DISCRIMINATING_NULL_NEGATIVE_CBIT")
    return failures


def materialize_compact_delta(
    *, delta, item, refs, route_id
):
    failures = validate_compact_delta(
        delta=delta, item=item, refs=refs
    )
    if failures:
        raise ValueError(",".join(failures))
    value = {
        axis: delta[axis] for axis in SCORE_MAP
    }
    value["evidence_span_ids"] = list(delta["evidence_span_ids"])
    value["rationale"] = delta["rationale"]
    candidate = {
        "candidate_id": "C1",
        "lane": "FRONTIER",
        "question": delta["question"],
        "source_object_id": delta["source_object_id"],
        "target_object_id": delta["target_object_id"],
        "constraint_object_ids": list(delta["constraint_object_ids"]),
        "epistemic_basis": "SPECULATIVE",
        "structural_origin": ROUTE_ORIGINS[route_id],
        "falsifier": delta["falsifier"],
        "required_observation": delta["required_observation"],
        "evidence_span_ids": list(delta["evidence_span_ids"]),
        "estimated_test_cost": delta["estimated_test_cost"],
        "candidate_value": value,
    }
    raw = {
        "case_id": item["case_id"],
        "arm_id": "A1_ONTOLOGY",
        "problem_candidates": [candidate],
        "selected_problem_id": "C1",
        "rationale": delta["rationale"],
        "evidence_refs": list(refs),
    }
    commitment = {
        "contract_version": CONTRACT_VERSION,
        "case_id": item["case_id"],
        "source_delta_hash": hash_payload(delta),
        "source_view_hash": item["artifact_hash"],
        "route_id": route_id,
        "relation_id": relation_id(candidate),
        "materialized_raw_hash": hash_payload(raw),
        "runtime_only_fields": {
            "candidate_id": "C1",
            "lane": "FRONTIER",
            "epistemic_basis": "SPECULATIVE",
            "structural_origin": ROUTE_ORIGINS[route_id],
        },
        "semantic_fields_copied_without_rewrite": True,
        "private_truth_used": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    receipt = {
        **commitment, "artifact_hash": hash_payload(commitment)
    }
    return raw, receipt
