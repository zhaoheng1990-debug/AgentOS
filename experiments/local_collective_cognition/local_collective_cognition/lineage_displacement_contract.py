"""Semantic lineage and pairwise displacement controls for v0.47."""

from __future__ import annotations

import copy

from .admission_opportunity_contract import (
    build_opportunity_delta_view,
    opportunity_delta_schema,
    validate_opportunity_delta,
)
from .provider_telemetry import hash_payload


CONTRACT_VERSION = "lineage_displacement_contract_v0_47"
GATE_VERSION = "lineage_displacement_gate_v0_47"
LANE_BY_OPPORTUNITY = {
    "EFFECT": "EFFECT",
    "INFORMATIVE_NULL": "INFORMATIVE_NULL",
    "QUARANTINE_ALTERNATIVE": "QUARANTINE",
}
ARBITER_DECISIONS = ("KEEP_BASE", "REPLACE", "UNRESOLVED")
PAIRWISE_PREFERENCES = ("BASE", "DELTA", "TIE", "UNRESOLVED")


def build_lineage_bound_delta_view(
    *, raw_receipt, item, qualification_receipt, routing_receipt
):
    view = build_opportunity_delta_view(
        raw_receipt=raw_receipt,
        item=item,
        qualification_receipt=qualification_receipt,
        routing_receipt=routing_receipt,
    )
    bindings = []
    for opportunity in routing_receipt["allowed_opportunities"]:
        commitment = {
            "source_object_id": opportunity["source_object_id"],
            "target_object_id": opportunity["target_object_id"],
            "opportunity_type": opportunity["opportunity_type"],
            "evidence_span_ids": list(
                opportunity["evidence_span_ids"]
            ),
            "relation_truth_state": opportunity[
                "relation_truth_state"
            ],
            "null_information_role": opportunity[
                "null_information_role"
            ],
            "constraint_binding": opportunity[
                "constraint_binding"
            ],
            "expected_cbit": opportunity["expected_cbit"],
            "research_value_disposition": opportunity[
                "research_value_disposition"
            ],
        }
        bindings.append({
            **commitment,
            "opportunity_hash": hash_payload(commitment),
            "required_admission_lane": LANE_BY_OPPORTUNITY[
                opportunity["opportunity_type"]
            ],
        })
    commitment = {
        key: value for key, value in view.items()
        if key != "artifact_hash"
    }
    commitment["view_version"] = "lineage_bound_delta_view_v0_47"
    commitment["opportunity_bindings"] = bindings
    required_spans = {
        span_id
        for value in bindings
        for span_id in value["evidence_span_ids"]
    }
    by_id = {
        value["span_id"]: value for value in item["evidence_spans"]
    }
    ordered_ids = [
        *sorted(required_spans),
        *[
            value["span_id"] for value in view["evidence_spans"]
            if value["span_id"] not in required_spans
        ],
    ]
    commitment["evidence_spans"] = [
        copy.deepcopy(by_id[span_id])
        for span_id in ordered_ids[:4]
    ]
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def lineage_bound_delta_schema(*, item, refs):
    schema = opportunity_delta_schema(item=item, refs=refs)
    schema["required"].extend([
        "source_opportunity_hash",
        "source_opportunity_type",
        "source_opportunity_evidence_span_ids",
        "proposed_admission_lane",
    ])
    schema["properties"].update({
        "source_opportunity_hash": {
            "type": "string",
            "enum": [
                value["opportunity_hash"]
                for value in item["opportunity_bindings"]
            ],
        },
        "source_opportunity_type": {
            "type": "string",
            "enum": list(LANE_BY_OPPORTUNITY),
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
            },
            "required": [
                "source_object_id",
                "target_object_id",
                "source_opportunity_hash",
                "source_opportunity_type",
                "source_opportunity_evidence_span_ids",
                "proposed_admission_lane",
            ],
        }
        for value in item["opportunity_bindings"]
    ]
    return schema


def validate_lineage_bound_delta(*, delta, item, refs):
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
        return [*failures, "LINEAGE_BINDING_MISSING"]
    checks = {
        "source_opportunity_hash": binding["opportunity_hash"],
        "source_opportunity_type": binding["opportunity_type"],
        "source_opportunity_evidence_span_ids": binding[
            "evidence_span_ids"
        ],
        "proposed_admission_lane": binding[
            "required_admission_lane"
        ],
    }
    for field, expected in checks.items():
        if delta.get(field) != expected:
            failures.append(f"LINEAGE_{field.upper()}_MISMATCH")
    if not set(binding["evidence_span_ids"]).issubset(
        set(delta.get("evidence_span_ids", []))
    ):
        failures.append("LINEAGE_WARRANT_NOT_PRESERVED")
    lane = binding["required_admission_lane"]
    if lane == "EFFECT" and not (
        delta.get("relation_truth_state") == "SUPPORTED_EFFECT"
        and delta.get("constraint_binding") == "ADEQUATE"
        and delta.get("expected_cbit") == "HIGH"
    ):
        failures.append("EFFECT_LINEAGE_SEMANTICS_INVALID")
    if lane == "INFORMATIVE_NULL" and not (
        delta.get("null_information_role")
        == "RULES_OUT_PLAUSIBLE_CAUSE"
        and delta.get("constraint_binding") == "ADEQUATE"
        and delta.get("research_value_disposition") == "PRIORITIZE"
    ):
        failures.append("INFORMATIVE_NULL_LINEAGE_SEMANTICS_INVALID")
    if lane == "QUARANTINE" and (
        delta.get("relation_truth_state")
        in {"SUPPORTED_EFFECT", "SUPPORTED_NULL"}
        or delta.get("research_value_disposition") == "PRIORITIZE"
    ):
        failures.append("QUARANTINE_LINEAGE_STRENGTHENING_FORBIDDEN")
    return failures


def build_pairwise_displacement_view(
    *,
    item,
    provisional_receipt,
    provisional_projection,
    proposed_receipt,
    composition_receipt,
    lineage_delta,
):
    selected = {
        value["pool_candidate_id"]
        for value in composition_receipt["lineage"]
    }
    counter = next(
        value for value in composition_receipt["scored_candidates"]
        if value["source_id"] == "COUNTER"
    )
    dropped = [
        value for value in composition_receipt["scored_candidates"]
        if value["source_id"] == "BASE"
        and value["pool_candidate_id"] not in selected
    ]
    if counter["pool_candidate_id"] not in selected or len(dropped) != 1:
        return None
    dropped_id = dropped[0]["source_candidate_id"]
    base_candidate = next(
        value for value in provisional_receipt["problem_candidates"]
        if value["candidate_id"] == dropped_id
    )
    delta_candidate = next(
        value for value in proposed_receipt["problem_candidates"]
        if value["source_object_id"]
        == lineage_delta["source_object_id"]
        and value["target_object_id"]
        == lineage_delta["target_object_id"]
    )
    dispositions = {
        value["candidate_id"]: value["disposition"]
        for value in provisional_projection["candidate_components"]
    }
    commitment = {
        "view_version": "pairwise_displacement_view_v0_47",
        "case_id": item["case_id"],
        "domain": item["domain"],
        "research_goal": item["research_goal"],
        "focal_object_id": item["focal_object_id"],
        "evidence_spans": copy.deepcopy(item["evidence_spans"]),
        "source_opportunity_hash": lineage_delta[
            "source_opportunity_hash"
        ],
        "source_opportunity_type": lineage_delta[
            "source_opportunity_type"
        ],
        "proposed_admission_lane": lineage_delta[
            "proposed_admission_lane"
        ],
        "base_candidate": copy.deepcopy(base_candidate),
        "base_candidate_disposition": dispositions.get(
            dropped_id, "MISSING"
        ),
        "delta_candidate": copy.deepcopy(delta_candidate),
        "private_truth_used": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def pairwise_displacement_schema(*, item, refs):
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "source_opportunity_hash": {
            "type": "string",
            "enum": [item["source_opportunity_hash"]],
        },
        "dropped_base_candidate_id": {
            "type": "string",
            "enum": [item["base_candidate"]["candidate_id"]],
        },
        "counter_relation_id": {
            "type": "string",
            "enum": [
                (
                    f"REL-{item['delta_candidate']['source_object_id']}-"
                    f"{item['delta_candidate']['target_object_id']}"
                )
            ],
        },
        "decision": {
            "type": "string", "enum": list(ARBITER_DECISIONS),
        },
        "pairwise_information_preference": {
            "type": "string", "enum": list(PAIRWISE_PREFERENCES),
        },
        "opportunity_lineage_consistent": {"type": "boolean"},
        "delta_materially_stronger": {"type": "boolean"},
        "evidence_span_ids": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {"type": "string", "enum": span_ids},
        },
        "rationale": {"type": "string"},
        "evidence_refs": {
            "type": "array",
            "items": {"type": "string", "enum": list(refs)},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def validate_pairwise_displacement(*, receipt, item, refs):
    failures = []
    if not isinstance(receipt, dict):
        return ["PAIRWISE_RECEIPT_NOT_OBJECT"]
    expected = {
        "case_id": item["case_id"],
        "source_opportunity_hash": item["source_opportunity_hash"],
        "dropped_base_candidate_id": item[
            "base_candidate"
        ]["candidate_id"],
        "counter_relation_id": (
            f"REL-{item['delta_candidate']['source_object_id']}-"
            f"{item['delta_candidate']['target_object_id']}"
        ),
        "evidence_refs": list(refs),
    }
    for field, value in expected.items():
        if receipt.get(field) != value:
            failures.append(f"PAIRWISE_{field.upper()}_MISMATCH")
    if receipt.get("decision") not in ARBITER_DECISIONS:
        failures.append("PAIRWISE_DECISION_INVALID")
    if (
        receipt.get("pairwise_information_preference")
        not in PAIRWISE_PREFERENCES
    ):
        failures.append("PAIRWISE_PREFERENCE_INVALID")
    allowed_spans = {
        value["span_id"] for value in item["evidence_spans"]
    }
    spans = receipt.get("evidence_span_ids")
    if (
        not isinstance(spans, list)
        or not spans
        or len(set(spans)) != len(spans)
        or not set(spans).issubset(allowed_spans)
    ):
        failures.append("PAIRWISE_EVIDENCE_BINDING_INVALID")
    return failures


def derive_current_stage_witnesses(
    *,
    raw_receipts,
    source_replication_id,
    case_id,
    relation_id,
    standard_stage,
):
    expected = tuple(
        relation_id.removeprefix("REL-").split("-")
    )
    witnesses = set()
    for key, raw in raw_receipts.items():
        parts = key.split(":", 3)
        if len(parts) != 4:
            continue
        rep, _arm, stage, raw_case = parts
        if (
            stage != standard_stage
            or raw_case != case_id
            or rep == source_replication_id
        ):
            continue
        if any(
            (
                value["source_object_id"],
                value["target_object_id"],
            ) == expected
            for value in raw.get("problem_candidates", ())
        ):
            witnesses.add(rep)
    return sorted(witnesses)


def apply_lineage_displacement_gate(
    *,
    provisional_receipt,
    proposed_receipt,
    composition_receipt,
    pairwise_receipt,
    pairwise_view,
    lineage_delta,
    cross_replication_witnesses,
):
    lane = lineage_delta["proposed_admission_lane"]
    arbiter_approved = (
        pairwise_receipt["decision"] == "REPLACE"
        and pairwise_receipt["pairwise_information_preference"] == "DELTA"
        and pairwise_receipt["opportunity_lineage_consistent"] is True
        and pairwise_receipt["delta_materially_stronger"] is True
    )
    lane_eligible = (
        lane == "QUARANTINE"
        and pairwise_view["base_candidate_disposition"]
        == "QUARANTINED_COMPONENT"
    ) or (
        lane == "EFFECT"
        and len(cross_replication_witnesses) >= 1
    ) or lane == "INFORMATIVE_NULL"
    protected = (
        pairwise_view["base_candidate"].get(
            "candidate_value", {}
        ).get("relation_truth_state") == "SUPPORTED_NULL"
    )
    accepted = bool(
        arbiter_approved and lane_eligible and not protected
    )
    if not arbiter_approved:
        reason = "PAIRWISE_REPLACEMENT_NOT_APPROVED"
    elif protected:
        reason = "SUPPORTED_NULL_PROTECTED"
    elif not lane_eligible:
        reason = "BOUND_LANE_REQUIREMENT_NOT_MET"
    else:
        reason = "LINEAGE_BOUND_PAIRWISE_REPLACEMENT"
    commitment = {
        "gate_version": GATE_VERSION,
        "case_id": pairwise_view["case_id"],
        "source_provisional_hash": hash_payload(provisional_receipt),
        "source_proposed_hash": hash_payload(proposed_receipt),
        "source_composition_hash": composition_receipt["artifact_hash"],
        "source_pairwise_view_hash": pairwise_view["artifact_hash"],
        "source_pairwise_receipt_hash": hash_payload(pairwise_receipt),
        "source_opportunity_hash": lineage_delta[
            "source_opportunity_hash"
        ],
        "bound_lane": lane,
        "arbiter_approved": arbiter_approved,
        "lane_eligible": lane_eligible,
        "protected_supported_null": protected,
        "cross_replication_witnesses": list(
            cross_replication_witnesses
        ),
        "accepted": accepted,
        "lane": lane if accepted else "NONE",
        "reason": reason,
        "private_truth_used": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    receipt = {
        **commitment, "artifact_hash": hash_payload(commitment)
    }
    if accepted:
        return proposed_receipt, composition_receipt, receipt
    return provisional_receipt, None, receipt

