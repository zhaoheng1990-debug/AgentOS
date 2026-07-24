"""Selective rejection challenge and coordination controls for v0.52."""

from __future__ import annotations

import copy

from .provider_telemetry import hash_payload


CONTRACT_VERSION = "selective_rejection_contract_v0_52"
GATE_VERSION = "selective_rejection_gate_v0_52"
CHALLENGE_DECISIONS = (
    "UPHOLD_REJECTION",
    "REOPEN_DELTA",
    "UNRESOLVED",
)
COORDINATION_DECISIONS = (
    "KEEP_BASE_ACTIVE",
    "ACTIVATE_DELTA",
    "UNRESOLVED",
)
MARGINAL_PREFERENCES = ("BASE", "DELTA", "TIE", "UNRESOLVED")
ORDINAL_LEVELS = ("HIGH", "MEDIUM", "LOW", "UNRESOLVED")
EVIDENCE_LEVELS = ("DIRECT", "PARTIAL", "WEAK", "UNRESOLVED")


def build_rejection_challenge_view(*, portfolio_view, initial_receipt):
    if (
        initial_receipt.get("portfolio_decision")
        == "ACTIVATE_DELTA"
        or initial_receipt.get("source_portfolio_view_hash")
        != portfolio_view.get("artifact_hash")
    ):
        return None
    commitment = {
        "view_version": CONTRACT_VERSION,
        "case_id": portfolio_view["case_id"],
        "source_portfolio_view_hash": portfolio_view["artifact_hash"],
        "source_initial_receipt_hash": hash_payload(initial_receipt),
        "dropped_base_pool_id": portfolio_view["dropped_base_pool_id"],
        "delta_pool_id": portfolio_view["delta_pool_id"],
        "base_candidate": copy.deepcopy(
            portfolio_view["base_candidate"]
        ),
        "delta_candidate": copy.deepcopy(
            portfolio_view["delta_candidate"]
        ),
        "fixed_active_companions": copy.deepcopy(
            portfolio_view["fixed_active_companions"]
        ),
        "initial_portfolio_decision": initial_receipt[
            "portfolio_decision"
        ],
        "initial_marginal_preference": initial_receipt[
            "marginal_information_preference"
        ],
        "initial_rationale": initial_receipt["rationale"],
        "initial_evidence_span_ids": list(
            initial_receipt["evidence_span_ids"]
        ),
        "evidence_spans": copy.deepcopy(
            portfolio_view["evidence_spans"]
        ),
        "displacement_scope": "ACTIVE_PORTFOLIO_ONLY",
        "challenge_scope": "REJECTED_DELTA_ONLY",
        "challenge_cannot_activate_directly": True,
        "private_truth_used": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def rejection_challenge_schema(*, item, refs):
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "source_challenge_view_hash": {
            "type": "string", "enum": [item["artifact_hash"]],
        },
        "source_portfolio_view_hash": {
            "type": "string",
            "enum": [item["source_portfolio_view_hash"]],
        },
        "source_initial_receipt_hash": {
            "type": "string",
            "enum": [item["source_initial_receipt_hash"]],
        },
        "dropped_base_pool_id": {
            "type": "string",
            "enum": [item["dropped_base_pool_id"]],
        },
        "delta_pool_id": {
            "type": "string", "enum": [item["delta_pool_id"]],
        },
        "initial_portfolio_decision": {
            "type": "string",
            "enum": [item["initial_portfolio_decision"]],
        },
        "initial_marginal_preference": {
            "type": "string",
            "enum": [item["initial_marginal_preference"]],
        },
        "base_evidence_resolution": {
            "type": "string", "enum": list(EVIDENCE_LEVELS),
        },
        "delta_evidence_resolution": {
            "type": "string", "enum": list(EVIDENCE_LEVELS),
        },
        "base_hypothesis_space_reduction": {
            "type": "string", "enum": list(ORDINAL_LEVELS),
        },
        "delta_hypothesis_space_reduction": {
            "type": "string", "enum": list(ORDINAL_LEVELS),
        },
        "base_portfolio_redundancy": {
            "type": "string", "enum": list(ORDINAL_LEVELS),
        },
        "delta_portfolio_redundancy": {
            "type": "string", "enum": list(ORDINAL_LEVELS),
        },
        "novelty_without_evidence_detected": {"type": "boolean"},
        "relation_state_category_bias_detected": {"type": "boolean"},
        "challenge_decision": {
            "type": "string", "enum": list(CHALLENGE_DECISIONS),
        },
        "delta_has_higher_evidence_bound_marginal_cbit": {
            "type": "boolean",
        },
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


def validate_rejection_challenge(*, receipt, item, refs):
    if not isinstance(receipt, dict):
        return ["REJECTION_CHALLENGE_NOT_OBJECT"]
    expected = {
        "case_id": item["case_id"],
        "source_challenge_view_hash": item["artifact_hash"],
        "source_portfolio_view_hash": item[
            "source_portfolio_view_hash"
        ],
        "source_initial_receipt_hash": item[
            "source_initial_receipt_hash"
        ],
        "dropped_base_pool_id": item["dropped_base_pool_id"],
        "delta_pool_id": item["delta_pool_id"],
        "initial_portfolio_decision": item[
            "initial_portfolio_decision"
        ],
        "initial_marginal_preference": item[
            "initial_marginal_preference"
        ],
        "evidence_refs": list(refs),
    }
    failures = [
        f"REJECTION_CHALLENGE_{field.upper()}_MISMATCH"
        for field, value in expected.items()
        if receipt.get(field) != value
    ]
    if receipt.get("challenge_decision") not in CHALLENGE_DECISIONS:
        failures.append("REJECTION_CHALLENGE_DECISION_INVALID")
    if (
        receipt.get("challenge_decision") == "REOPEN_DELTA"
        and receipt.get(
            "delta_has_higher_evidence_bound_marginal_cbit"
        ) is not True
    ):
        failures.append("REJECTION_CHALLENGE_REOPEN_UNSUPPORTED")
    _validate_evidence_binding(
        failures, receipt=receipt, item=item,
        prefix="REJECTION_CHALLENGE",
    )
    return failures


def build_rejection_coordination_view(
    *, challenge_view, challenge_receipt
):
    if challenge_receipt.get("challenge_decision") != "REOPEN_DELTA":
        return None
    commitment = {
        "view_version": CONTRACT_VERSION,
        "case_id": challenge_view["case_id"],
        "source_portfolio_view_hash": challenge_view[
            "source_portfolio_view_hash"
        ],
        "source_initial_receipt_hash": challenge_view[
            "source_initial_receipt_hash"
        ],
        "source_challenge_view_hash": challenge_view["artifact_hash"],
        "source_challenge_receipt_hash": hash_payload(
            challenge_receipt
        ),
        "dropped_base_pool_id": challenge_view[
            "dropped_base_pool_id"
        ],
        "delta_pool_id": challenge_view["delta_pool_id"],
        "base_candidate": copy.deepcopy(
            challenge_view["base_candidate"]
        ),
        "delta_candidate": copy.deepcopy(
            challenge_view["delta_candidate"]
        ),
        "fixed_active_companions": copy.deepcopy(
            challenge_view["fixed_active_companions"]
        ),
        "initial_portfolio_decision": challenge_view[
            "initial_portfolio_decision"
        ],
        "initial_marginal_preference": challenge_view[
            "initial_marginal_preference"
        ],
        "initial_rationale": challenge_view["initial_rationale"],
        "challenge_receipt": copy.deepcopy(challenge_receipt),
        "evidence_spans": copy.deepcopy(
            challenge_view["evidence_spans"]
        ),
        "challenge_cannot_activate_directly": True,
        "coordination_required_before_activation": True,
        "private_truth_used": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def rejection_coordination_schema(*, item, refs):
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "source_coordination_view_hash": {
            "type": "string", "enum": [item["artifact_hash"]],
        },
        "source_portfolio_view_hash": {
            "type": "string",
            "enum": [item["source_portfolio_view_hash"]],
        },
        "source_initial_receipt_hash": {
            "type": "string",
            "enum": [item["source_initial_receipt_hash"]],
        },
        "source_challenge_receipt_hash": {
            "type": "string",
            "enum": [item["source_challenge_receipt_hash"]],
        },
        "dropped_base_pool_id": {
            "type": "string",
            "enum": [item["dropped_base_pool_id"]],
        },
        "delta_pool_id": {
            "type": "string", "enum": [item["delta_pool_id"]],
        },
        "initial_portfolio_decision": {
            "type": "string",
            "enum": [item["initial_portfolio_decision"]],
        },
        "challenge_decision": {
            "type": "string", "enum": ["REOPEN_DELTA"],
        },
        "coordination_decision": {
            "type": "string", "enum": list(COORDINATION_DECISIONS),
        },
        "marginal_information_preference": {
            "type": "string", "enum": list(MARGINAL_PREFERENCES),
        },
        "evidence_conflict_resolved": {"type": "boolean"},
        "novelty_not_used_as_standalone_value": {"type": "boolean"},
        "relation_state_category_priority_forbidden": {
            "type": "boolean", "enum": [True],
        },
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


def validate_rejection_coordination(*, receipt, item, refs):
    if not isinstance(receipt, dict):
        return ["REJECTION_COORDINATION_NOT_OBJECT"]
    expected = {
        "case_id": item["case_id"],
        "source_coordination_view_hash": item["artifact_hash"],
        "source_portfolio_view_hash": item[
            "source_portfolio_view_hash"
        ],
        "source_initial_receipt_hash": item[
            "source_initial_receipt_hash"
        ],
        "source_challenge_receipt_hash": item[
            "source_challenge_receipt_hash"
        ],
        "dropped_base_pool_id": item["dropped_base_pool_id"],
        "delta_pool_id": item["delta_pool_id"],
        "initial_portfolio_decision": item[
            "initial_portfolio_decision"
        ],
        "challenge_decision": "REOPEN_DELTA",
        "relation_state_category_priority_forbidden": True,
        "evidence_refs": list(refs),
    }
    failures = [
        f"REJECTION_COORDINATION_{field.upper()}_MISMATCH"
        for field, value in expected.items()
        if receipt.get(field) != value
    ]
    if (
        receipt.get("coordination_decision")
        not in COORDINATION_DECISIONS
    ):
        failures.append("REJECTION_COORDINATION_DECISION_INVALID")
    if (
        receipt.get("coordination_decision") == "ACTIVATE_DELTA"
        and (
            receipt.get("marginal_information_preference") != "DELTA"
            or receipt.get("evidence_conflict_resolved") is not True
            or receipt.get(
                "novelty_not_used_as_standalone_value"
            ) is not True
            or receipt.get("delta_has_higher_marginal_cbit") is not True
        )
    ):
        failures.append("REJECTION_COORDINATION_ACTIVATION_UNSUPPORTED")
    _validate_evidence_binding(
        failures, receipt=receipt, item=item,
        prefix="REJECTION_COORDINATION",
    )
    return failures


def apply_selective_rejection_gate(
    *,
    provisional_receipt,
    proposed_receipt,
    composition_receipt,
    portfolio_view,
    lineage_delta,
    cross_replication_witnesses,
    initial_receipt,
    challenge_receipt,
    coordination_receipt,
):
    lane = lineage_delta["proposed_admission_lane"]
    direct_approved = (
        initial_receipt["portfolio_decision"] == "ACTIVATE_DELTA"
        and initial_receipt["marginal_information_preference"] == "DELTA"
        and initial_receipt["opportunity_lineage_consistent"] is True
        and initial_receipt["delta_has_higher_marginal_cbit"] is True
    )
    coordinated_approved = bool(
        not direct_approved
        and challenge_receipt
        and challenge_receipt["challenge_decision"] == "REOPEN_DELTA"
        and challenge_receipt[
            "delta_has_higher_evidence_bound_marginal_cbit"
        ] is True
        and coordination_receipt
        and coordination_receipt["coordination_decision"]
        == "ACTIVATE_DELTA"
        and coordination_receipt["marginal_information_preference"]
        == "DELTA"
        and coordination_receipt["evidence_conflict_resolved"] is True
        and coordination_receipt[
            "novelty_not_used_as_standalone_value"
        ] is True
        and coordination_receipt[
            "relation_state_category_priority_forbidden"
        ] is True
        and coordination_receipt["delta_has_higher_marginal_cbit"]
        is True
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
    approved = direct_approved or coordinated_approved
    accepted = bool(approved and lane_eligible and not protected)
    if not approved:
        reason = "SELECTIVE_ACTIVATION_NOT_APPROVED"
    elif protected:
        reason = "SUPPORTED_NULL_PROTECTED"
    elif not lane_eligible:
        reason = "BOUND_LANE_REQUIREMENT_NOT_MET"
    elif coordinated_approved:
        reason = "CHALLENGE_COORDINATED_MARGINAL_CBIT_ACTIVATION"
    else:
        reason = "DIRECT_MARGINAL_CBIT_PORTFOLIO_ACTIVATION"
    commitment = {
        "gate_version": GATE_VERSION,
        "case_id": portfolio_view["case_id"],
        "source_provisional_hash": hash_payload(provisional_receipt),
        "source_proposed_hash": hash_payload(proposed_receipt),
        "source_composition_hash": composition_receipt["artifact_hash"],
        "source_portfolio_view_hash": portfolio_view["artifact_hash"],
        "source_initial_receipt_hash": hash_payload(initial_receipt),
        "source_challenge_receipt_hash": (
            hash_payload(challenge_receipt)
            if challenge_receipt else None
        ),
        "source_coordination_receipt_hash": (
            hash_payload(coordination_receipt)
            if coordination_receipt else None
        ),
        "source_opportunity_hash": lineage_delta[
            "source_opportunity_hash"
        ],
        "bound_lane": lane,
        "direct_arbiter_approved": direct_approved,
        "challenge_reopened": bool(
            challenge_receipt
            and challenge_receipt["challenge_decision"]
            == "REOPEN_DELTA"
        ),
        "coordinator_approved": coordinated_approved,
        "challenge_cannot_activate_directly": True,
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


def _validate_evidence_binding(failures, *, receipt, item, prefix):
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
        failures.append(f"{prefix}_EVIDENCE_BINDING_INVALID")
