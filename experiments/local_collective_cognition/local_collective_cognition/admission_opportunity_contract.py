"""Provider-supported admission opportunity routing for v0.46."""

from __future__ import annotations

import copy
from collections import Counter

from .candidate_pool_arbitration import relation_id
from .compact_delta_contract import (
    build_compact_delta_view,
    compact_delta_schema,
    validate_compact_delta,
)
from .null_role_candidate_composition import (
    SCORE_MAP,
    null_role_valued_exact_three_schema,
    validate_null_role_valued_receipt,
)
from .provider_telemetry import hash_payload


CONTRACT_VERSION = "admission_opportunity_contract_v0_46"
ROUTING_VERSION = "admission_opportunity_routing_v0_46"
MAXIMUM_OPPORTUNITIES = 2
OPPORTUNITY_TYPES = (
    "EFFECT",
    "INFORMATIVE_NULL",
    "QUARANTINE_ALTERNATIVE",
)


def opportunity_enriched_exact_three_schema(*, item, arm_id, refs):
    schema = copy.deepcopy(
        null_role_valued_exact_three_schema(
            item=item, arm_id=arm_id, refs=refs
        )
    )
    object_ids = [
        value["object_id"] for value in item["object_registry"]
    ]
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    opportunity = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "source_object_id",
            "target_object_id",
            "opportunity_type",
            "relation_truth_state",
            "null_information_role",
            "constraint_binding",
            "expected_cbit",
            "research_value_disposition",
            "evidence_span_ids",
            "rationale",
        ],
        "properties": {
            "source_object_id": {
                "type": "string", "enum": object_ids,
            },
            "target_object_id": {
                "type": "string", "enum": object_ids,
            },
            "opportunity_type": {
                "type": "string", "enum": list(OPPORTUNITY_TYPES),
            },
            **{
                axis: {"type": "string", "enum": list(SCORE_MAP[axis])}
                for axis in (
                    "relation_truth_state",
                    "null_information_role",
                    "constraint_binding",
                    "expected_cbit",
                    "research_value_disposition",
                )
            },
            "evidence_span_ids": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {"type": "string", "enum": span_ids},
            },
            "rationale": {"type": "string"},
        },
    }
    schema["required"].append("admission_opportunities")
    schema["properties"]["admission_opportunities"] = {
        "type": "array",
        "maxItems": MAXIMUM_OPPORTUNITIES,
        "items": opportunity,
    }
    return schema


def validate_opportunity_enriched_receipt(*, raw_receipt, item, refs):
    failures = validate_null_role_valued_receipt(
        raw_receipt=raw_receipt, item=item, refs=refs
    )
    if not isinstance(raw_receipt, dict):
        return failures
    opportunities = raw_receipt.get("admission_opportunities")
    if (
        not isinstance(opportunities, list)
        or len(opportunities) > MAXIMUM_OPPORTUNITIES
    ):
        return [*failures, "ADMISSION_OPPORTUNITIES_INVALID"]
    object_ids = {
        value["object_id"] for value in item["object_registry"]
    }
    span_ids = {
        value["span_id"] for value in item["evidence_spans"]
    }
    excluded = {
        relation_id(value)
        for value in raw_receipt.get("problem_candidates", [])
        if isinstance(value, dict)
    }
    seen = set()
    required = {
        "source_object_id",
        "target_object_id",
        "opportunity_type",
        "relation_truth_state",
        "null_information_role",
        "constraint_binding",
        "expected_cbit",
        "research_value_disposition",
        "evidence_span_ids",
        "rationale",
    }
    for index, value in enumerate(opportunities):
        prefix = f"OPPORTUNITY_{index + 1}"
        if not isinstance(value, dict) or set(value) != required:
            failures.append(f"{prefix}_FIELDS_INVALID")
            continue
        source = value["source_object_id"]
        target = value["target_object_id"]
        current_relation = f"{source}->{target}"
        if (
            source not in object_ids
            or target not in object_ids
            or source == target
        ):
            failures.append(f"{prefix}_OBJECT_BINDING_INVALID")
        if current_relation in excluded:
            failures.append(f"{prefix}_DUPLICATES_BASE")
        if current_relation in seen:
            failures.append(f"{prefix}_DUPLICATE")
        seen.add(current_relation)
        if value["opportunity_type"] not in OPPORTUNITY_TYPES:
            failures.append(f"{prefix}_TYPE_INVALID")
        for axis in (
            "relation_truth_state",
            "null_information_role",
            "constraint_binding",
            "expected_cbit",
            "research_value_disposition",
        ):
            if value[axis] not in SCORE_MAP[axis]:
                failures.append(f"{prefix}_{axis.upper()}_INVALID")
        spans = value["evidence_span_ids"]
        if (
            not spans
            or len(set(spans)) != len(spans)
            or not set(spans).issubset(span_ids)
        ):
            failures.append(f"{prefix}_EVIDENCE_BINDING_INVALID")
    return failures


def derive_admission_opportunity_receipt(
    *,
    key,
    raw_receipt,
    item,
    qualification_receipt,
    all_standard_receipts,
):
    rep, _, case_id = key.split(":", 2)
    primary = {item["focal_object_id"]}
    base_relations = {
        relation_id(value) for value in raw_receipt["problem_candidates"]
    }
    case_opportunities = []
    occurrence = Counter()
    for other_key, other_raw in all_standard_receipts.items():
        other_rep, _, other_stage, other_case = other_key.split(":", 3)
        if other_stage != "STANDARD_OPPORTUNITY" or other_case != case_id:
            continue
        for value in other_raw.get("admission_opportunities", []):
            relation = (
                f"{value['source_object_id']}->{value['target_object_id']}"
            )
            occurrence[relation] += 1
            case_opportunities.append((other_rep, value))
    candidates = []
    for source_rep, value in case_opportunities:
        relation = (
            f"{value['source_object_id']}->{value['target_object_id']}"
        )
        focal = bool(
            {
                value["source_object_id"],
                value["target_object_id"],
            } & primary
        )
        own = source_rep == rep
        lane_ready = _lane_ready(value)
        recurrent = occurrence[relation] >= 2
        if (
            relation in base_relations
            or not focal
            or not lane_ready
            or not (own or recurrent)
        ):
            continue
        candidates.append({
            **copy.deepcopy(value),
            "relation_id": relation,
            "source_replication_id": source_rep,
            "cross_replication_occurrence_count": occurrence[relation],
            "own_receipt_opportunity": own,
        })
    best = {}
    for value in candidates:
        incumbent = best.get(value["relation_id"])
        rank = (
            value["own_receipt_opportunity"],
            value["cross_replication_occurrence_count"],
            value["expected_cbit"] == "HIGH",
            value["constraint_binding"] == "ADEQUATE",
            hash_payload([ROUTING_VERSION, key, value["relation_id"]]),
        )
        if incumbent is None or rank > incumbent[0]:
            best[value["relation_id"]] = (rank, value)
    selected = [
        value for _, value in sorted(
            best.values(), key=lambda pair: pair[0], reverse=True
        )[:MAXIMUM_OPPORTUNITIES]
    ]
    commitment = {
        "routing_version": ROUTING_VERSION,
        "case_id": case_id,
        "replication_id": rep,
        "source_standard_receipt_hash": hash_payload(raw_receipt),
        "source_qualification_hash": qualification_receipt["artifact_hash"],
        "qualified": qualification_receipt["qualified"],
        "allowed_opportunities": selected,
        "allowed_relations": [
            {
                "source_object_id": value["source_object_id"],
                "target_object_id": value["target_object_id"],
            }
            for value in selected
        ],
        "delta_call_authorized": bool(
            qualification_receipt["qualified"] and selected
        ),
        "reason": (
            "QUALIFIED_ADMISSION_OPPORTUNITY"
            if qualification_receipt["qualified"] and selected
            else (
                "QUALIFICATION_FAILED"
                if not qualification_receipt["qualified"]
                else "NO_ADMISSION_READY_OPPORTUNITY"
            )
        ),
        "private_truth_used": False,
        "provider_call_added_by_routing": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def build_opportunity_delta_view(
    *, raw_receipt, item, qualification_receipt, routing_receipt
):
    view = build_compact_delta_view(
        raw_receipt=raw_receipt,
        item=item,
        qualification_receipt=qualification_receipt,
    )
    commitment = {
        key: value for key, value in view.items()
        if key != "artifact_hash"
    }
    commitment["allowed_relations"] = copy.deepcopy(
        routing_receipt["allowed_relations"]
    )
    commitment["source_opportunity_routing_hash"] = (
        routing_receipt["artifact_hash"]
    )
    commitment["view_version"] = "opportunity_delta_view_v0_46"
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def opportunity_delta_schema(*, item, refs):
    schema = compact_delta_schema(item=item, refs=refs)
    allowed = item.get("allowed_relations", [])
    schema["anyOf"] = [
        {
            "properties": {
                "source_object_id": {
                    "const": value["source_object_id"],
                },
                "target_object_id": {
                    "const": value["target_object_id"],
                },
            },
            "required": ["source_object_id", "target_object_id"],
        }
        for value in allowed
    ]
    return schema


def validate_opportunity_delta(*, delta, item, refs):
    failures = validate_compact_delta(
        delta=delta, item=item, refs=refs
    )
    pair = {
        "source_object_id": delta.get("source_object_id"),
        "target_object_id": delta.get("target_object_id"),
    } if isinstance(delta, dict) else None
    if pair not in item.get("allowed_relations", []):
        failures.append("DELTA_RELATION_OUTSIDE_OPPORTUNITY_SET")
    return failures


def _lane_ready(value):
    if (
        value["opportunity_type"] == "EFFECT"
        and value["relation_truth_state"] == "SUPPORTED_EFFECT"
        and value["constraint_binding"] == "ADEQUATE"
        and value["expected_cbit"] == "HIGH"
        and value["research_value_disposition"] == "PRIORITIZE"
    ):
        return True
    if (
        value["opportunity_type"] == "INFORMATIVE_NULL"
        and value["null_information_role"]
        == "RULES_OUT_PLAUSIBLE_CAUSE"
        and value["constraint_binding"] == "ADEQUATE"
        and value["expected_cbit"] in {"HIGH", "MEDIUM"}
        and value["research_value_disposition"] == "PRIORITIZE"
    ):
        return True
    return (
        value["opportunity_type"] == "QUARANTINE_ALTERNATIVE"
        and value["constraint_binding"] in {"ADEQUATE", "PARTIAL"}
        and value["expected_cbit"] in {"HIGH", "MEDIUM"}
        and value["research_value_disposition"] in {"PRIORITIZE", "RETAIN"}
    )
