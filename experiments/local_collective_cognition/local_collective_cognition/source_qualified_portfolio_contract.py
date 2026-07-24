"""Non-destructive active-portfolio displacement controls for v0.51."""

from __future__ import annotations

import copy

from .lineage_displacement_contract import (
    build_pairwise_displacement_view,
)
from .provider_telemetry import hash_payload


CONTRACT_VERSION = "source_qualified_portfolio_contract_v0_51"
GATE_VERSION = "source_qualified_portfolio_gate_v0_51"
PORTFOLIO_DECISIONS = (
    "KEEP_BASE_ACTIVE",
    "ACTIVATE_DELTA",
    "UNRESOLVED",
)
MARGINAL_PREFERENCES = ("BASE", "DELTA", "TIE", "UNRESOLVED")


def build_source_qualified_portfolio_view(
    *,
    item,
    provisional_receipt,
    provisional_projection,
    proposed_receipt,
    composition_receipt,
    lineage_delta,
):
    base_view = build_pairwise_displacement_view(
        item=item,
        provisional_receipt=provisional_receipt,
        provisional_projection=provisional_projection,
        proposed_receipt=proposed_receipt,
        composition_receipt=composition_receipt,
        lineage_delta=lineage_delta,
    )
    if base_view is None:
        return None
    companion_lineage = sorted([
        value for value in composition_receipt["lineage"]
        if value["source_id"] == "BASE"
    ], key=lambda value: value["pool_candidate_id"])
    active_base_ids = [
        value["source_candidate_id"] for value in companion_lineage
    ]
    companions = [
        copy.deepcopy(value)
        for value in provisional_receipt["problem_candidates"]
        if value["candidate_id"] in active_base_ids
    ]
    companions.sort(key=lambda value: value["candidate_id"])
    if len(companions) != 2:
        return None
    selected_pool_ids = {
        value["pool_candidate_id"]
        for value in composition_receipt["lineage"]
    }
    dropped_base = next(
        value for value in composition_receipt["scored_candidates"]
        if value["source_id"] == "BASE"
        and value["pool_candidate_id"] not in selected_pool_ids
    )
    selected_delta = next(
        value for value in composition_receipt["lineage"]
        if value["source_id"] == "COUNTER"
    )
    base_candidate = copy.deepcopy(base_view["base_candidate"])
    base_candidate.pop("candidate_id", None)
    base_candidate["pool_candidate_id"] = dropped_base[
        "pool_candidate_id"
    ]
    delta_candidate = copy.deepcopy(base_view["delta_candidate"])
    delta_candidate.pop("candidate_id", None)
    delta_candidate["pool_candidate_id"] = selected_delta[
        "pool_candidate_id"
    ]
    retained = [
        *[
            f"BASE:{value['candidate_id']}"
            for value in provisional_receipt["problem_candidates"]
        ],
        selected_delta["pool_candidate_id"],
    ]
    commitment = {
        key: copy.deepcopy(value)
        for key, value in base_view.items()
        if key not in {"artifact_hash", "base_candidate", "delta_candidate"}
    }
    commitment.update({
        "view_version": CONTRACT_VERSION,
        "active_portfolio_capacity": 3,
        "displacement_scope": "ACTIVE_PORTFOLIO_ONLY",
        "base_retention_state": "PRESERVED_CANDIDATE",
        "delta_retention_state": "PRESERVED_CANDIDATE",
        "retained_candidate_pool_ids": retained,
        "dropped_base_pool_id": dropped_base["pool_candidate_id"],
        "delta_pool_id": selected_delta["pool_candidate_id"],
        "base_candidate": base_candidate,
        "delta_candidate": delta_candidate,
        "fixed_active_companions": [{
            "pool_candidate_id": lineage["pool_candidate_id"],
            "candidate": {
                key: copy.deepcopy(value)
                for key, value in next(
                    candidate for candidate in companions
                    if candidate["candidate_id"]
                    == lineage["source_candidate_id"]
                ).items()
                if key != "candidate_id"
            },
        } for lineage in companion_lineage],
        "fixed_active_companion_pool_ids": [
            value["pool_candidate_id"] for value in companion_lineage
        ],
        "permanent_deletion_cost": "ZERO",
        "decision_target": (
            "WHICH_CANDIDATE_OCCUPIES_THE_THIRD_ACTIVE_SLOT_NOW"
        ),
        "positive_effect_has_categorical_priority": False,
        "informative_null_can_have_higher_marginal_cbit": True,
        "private_truth_used": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    })
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def source_qualified_portfolio_schema(*, item, refs):
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    counter_relation = (
        f"REL-{item['delta_candidate']['source_object_id']}-"
        f"{item['delta_candidate']['target_object_id']}"
    )
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "source_portfolio_view_hash": {
            "type": "string", "enum": [item["artifact_hash"]],
        },
        "source_opportunity_hash": {
            "type": "string",
            "enum": [item["source_opportunity_hash"]],
        },
        "dropped_base_pool_id": {
            "type": "string",
            "enum": [item["dropped_base_pool_id"]],
        },
        "delta_pool_id": {
            "type": "string",
            "enum": [item["delta_pool_id"]],
        },
        "counter_relation_id": {
            "type": "string", "enum": [counter_relation],
        },
        "active_portfolio_capacity": {
            "type": "integer", "enum": [3],
        },
        "fixed_active_companion_pool_ids": {
            "type": "array",
            "enum": [item["fixed_active_companion_pool_ids"]],
            "items": {"type": "string"},
        },
        "displacement_scope": {
            "type": "string", "enum": ["ACTIVE_PORTFOLIO_ONLY"],
        },
        "base_candidate_retained": {
            "type": "boolean", "enum": [True],
        },
        "delta_candidate_retained": {
            "type": "boolean", "enum": [True],
        },
        "portfolio_scope_understood": {
            "type": "boolean", "enum": [True],
        },
        "portfolio_decision": {
            "type": "string", "enum": list(PORTFOLIO_DECISIONS),
        },
        "marginal_information_preference": {
            "type": "string", "enum": list(MARGINAL_PREFERENCES),
        },
        "opportunity_lineage_consistent": {"type": "boolean"},
        "delta_has_higher_marginal_cbit": {"type": "boolean"},
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


def validate_source_qualified_portfolio(*, receipt, item, refs):
    if not isinstance(receipt, dict):
        return ["PORTFOLIO_RECEIPT_NOT_OBJECT"]
    expected = {
        "case_id": item["case_id"],
        "source_portfolio_view_hash": item["artifact_hash"],
        "source_opportunity_hash": item["source_opportunity_hash"],
        "dropped_base_pool_id": item["dropped_base_pool_id"],
        "delta_pool_id": item["delta_pool_id"],
        "counter_relation_id": (
            f"REL-{item['delta_candidate']['source_object_id']}-"
            f"{item['delta_candidate']['target_object_id']}"
        ),
        "active_portfolio_capacity": 3,
        "fixed_active_companion_pool_ids": item[
            "fixed_active_companion_pool_ids"
        ],
        "displacement_scope": "ACTIVE_PORTFOLIO_ONLY",
        "base_candidate_retained": True,
        "delta_candidate_retained": True,
        "portfolio_scope_understood": True,
        "evidence_refs": list(refs),
    }
    failures = [
        f"PORTFOLIO_{field.upper()}_MISMATCH"
        for field, value in expected.items()
        if receipt.get(field) != value
    ]
    fixed_pool_ids = receipt.get("fixed_active_companion_pool_ids")
    if not isinstance(fixed_pool_ids, list):
        fixed_pool_ids = []
    source_qualified_ids = [
        receipt.get("dropped_base_pool_id"),
        receipt.get("delta_pool_id"),
        *fixed_pool_ids,
    ]
    if (
        any(
            not isinstance(value, str) or ":" not in value
            for value in source_qualified_ids
        )
        or not str(receipt.get("dropped_base_pool_id", "")).startswith(
            "BASE:"
        )
        or not str(receipt.get("delta_pool_id", "")).startswith(
            "COUNTER:"
        )
        or any(
            not str(value).startswith("BASE:")
            for value in fixed_pool_ids
        )
    ):
        failures.append("PORTFOLIO_SOURCE_QUALIFIED_ID_INVALID")
    if receipt.get("portfolio_decision") not in PORTFOLIO_DECISIONS:
        failures.append("PORTFOLIO_DECISION_INVALID")
    if (
        receipt.get("marginal_information_preference")
        not in MARGINAL_PREFERENCES
    ):
        failures.append("PORTFOLIO_MARGINAL_PREFERENCE_INVALID")
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
        failures.append("PORTFOLIO_EVIDENCE_BINDING_INVALID")
    return failures


def apply_source_qualified_portfolio_gate(
    *,
    provisional_receipt,
    proposed_receipt,
    composition_receipt,
    portfolio_receipt,
    portfolio_view,
    lineage_delta,
    cross_replication_witnesses,
):
    lane = lineage_delta["proposed_admission_lane"]
    arbiter_approved = (
        portfolio_receipt["portfolio_decision"] == "ACTIVATE_DELTA"
        and portfolio_receipt["marginal_information_preference"] == "DELTA"
        and portfolio_receipt["opportunity_lineage_consistent"] is True
        and portfolio_receipt["delta_has_higher_marginal_cbit"] is True
        and portfolio_receipt["portfolio_scope_understood"] is True
        and portfolio_receipt["base_candidate_retained"] is True
        and portfolio_receipt["delta_candidate_retained"] is True
    )
    lane_eligible = (
        lane == "QUARANTINE"
        and portfolio_view["base_candidate_disposition"]
        == "QUARANTINED_COMPONENT"
    ) or (
        lane == "EFFECT"
        and len(cross_replication_witnesses) >= 1
    ) or lane == "INFORMATIVE_NULL"
    protected = (
        portfolio_view["base_candidate"].get(
            "candidate_value", {}
        ).get("relation_truth_state") == "SUPPORTED_NULL"
    )
    accepted = bool(
        arbiter_approved and lane_eligible and not protected
    )
    if not arbiter_approved:
        reason = "PORTFOLIO_ACTIVATION_NOT_APPROVED"
    elif protected:
        reason = "SUPPORTED_NULL_PROTECTED"
    elif not lane_eligible:
        reason = "BOUND_LANE_REQUIREMENT_NOT_MET"
    else:
        reason = "MARGINAL_CBIT_PORTFOLIO_ACTIVATION"
    commitment = {
        "gate_version": GATE_VERSION,
        "case_id": portfolio_view["case_id"],
        "source_provisional_hash": hash_payload(provisional_receipt),
        "source_proposed_hash": hash_payload(proposed_receipt),
        "source_composition_hash": composition_receipt["artifact_hash"],
        "source_portfolio_view_hash": portfolio_view["artifact_hash"],
        "source_portfolio_receipt_hash": hash_payload(portfolio_receipt),
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
        "active_portfolio_capacity": 3,
        "displacement_scope": "ACTIVE_PORTFOLIO_ONLY",
        "base_candidate_retained": True,
        "delta_candidate_retained": True,
        "permanent_deletion_performed": False,
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
