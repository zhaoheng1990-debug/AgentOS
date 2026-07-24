"""Decision-blind evidence-first arbitration controls for v0.54."""

from __future__ import annotations

import copy

from .provider_telemetry import hash_payload


CONTRACT_VERSION = "evidence_first_arbitration_contract_v0_54"
GATE_VERSION = "evidence_first_arbitration_gate_v0_54"
AUDIT_ROLES = ("BLIND_EVIDENCE_AUDITOR", "BLIND_EVIDENCE_SKEPTIC")
EVIDENCE_STATES = (
    "RESOLVED_EFFECT",
    "RESOLVED_NULL",
    "PARTIALLY_RESOLVED",
    "UNRESOLVED_TESTABLE",
    "WEAK_UNTESTED",
)
ORDINAL_LEVELS = ("HIGH", "MEDIUM", "LOW", "UNRESOLVED")
PREFERENCES = ("BASE", "DELTA", "TIE", "UNRESOLVED")


def build_blind_evidence_view(*, portfolio_view):
    commitment = {
        "view_version": CONTRACT_VERSION,
        "case_id": portfolio_view["case_id"],
        "source_portfolio_view_hash": portfolio_view["artifact_hash"],
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
        "evidence_spans": copy.deepcopy(
            portfolio_view["evidence_spans"]
        ),
        "displacement_scope": "ACTIVE_PORTFOLIO_ONLY",
        "initial_decision_available": False,
        "initial_rationale_available": False,
        "other_audit_receipt_available": False,
        "resolved_evidence_counts_as_realized_cbit": True,
        "same_truth_state_is_not_relation_redundancy": True,
        "private_truth_used": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def blind_evidence_schema(*, item, role, refs):
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "audit_role": {"type": "string", "enum": [role]},
        "source_blind_view_hash": {
            "type": "string", "enum": [item["artifact_hash"]],
        },
        "source_portfolio_view_hash": {
            "type": "string",
            "enum": [item["source_portfolio_view_hash"]],
        },
        "dropped_base_pool_id": {
            "type": "string",
            "enum": [item["dropped_base_pool_id"]],
        },
        "delta_pool_id": {
            "type": "string", "enum": [item["delta_pool_id"]],
        },
        "base_evidence_state": {
            "type": "string", "enum": list(EVIDENCE_STATES),
        },
        "delta_evidence_state": {
            "type": "string", "enum": list(EVIDENCE_STATES),
        },
        "base_realized_information_gain": {
            "type": "string", "enum": list(ORDINAL_LEVELS),
        },
        "delta_realized_information_gain": {
            "type": "string", "enum": list(ORDINAL_LEVELS),
        },
        "base_future_test_option_value": {
            "type": "string", "enum": list(ORDINAL_LEVELS),
        },
        "delta_future_test_option_value": {
            "type": "string", "enum": list(ORDINAL_LEVELS),
        },
        "base_relation_redundancy": {
            "type": "string", "enum": list(ORDINAL_LEVELS),
        },
        "delta_relation_redundancy": {
            "type": "string", "enum": list(ORDINAL_LEVELS),
        },
        "resolved_evidence_counts_as_realized_cbit": {
            "type": "boolean", "enum": [True],
        },
        "same_truth_state_is_not_relation_redundancy": {
            "type": "boolean", "enum": [True],
        },
        "marginal_information_preference": {
            "type": "string", "enum": list(PREFERENCES),
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


def validate_blind_evidence_receipt(*, receipt, item, role, refs):
    if not isinstance(receipt, dict):
        return ["BLIND_EVIDENCE_RECEIPT_NOT_OBJECT"]
    expected = {
        "case_id": item["case_id"],
        "audit_role": role,
        "source_blind_view_hash": item["artifact_hash"],
        "source_portfolio_view_hash": item[
            "source_portfolio_view_hash"
        ],
        "dropped_base_pool_id": item["dropped_base_pool_id"],
        "delta_pool_id": item["delta_pool_id"],
        "resolved_evidence_counts_as_realized_cbit": True,
        "same_truth_state_is_not_relation_redundancy": True,
        "evidence_refs": list(refs),
    }
    failures = [
        f"BLIND_EVIDENCE_{field.upper()}_MISMATCH"
        for field, value in expected.items()
        if receipt.get(field) != value
    ]
    if receipt.get("marginal_information_preference") not in PREFERENCES:
        failures.append("BLIND_EVIDENCE_PREFERENCE_INVALID")
    if (
        receipt.get("marginal_information_preference") == "DELTA"
        and receipt.get(
            "delta_has_higher_evidence_bound_marginal_cbit"
        ) is not True
    ):
        failures.append("BLIND_EVIDENCE_DELTA_PREFERENCE_UNSUPPORTED")
    allowed = {
        value["span_id"] for value in item["evidence_spans"]
    }
    spans = receipt.get("evidence_span_ids")
    if (
        not isinstance(spans, list)
        or not spans
        or len(set(spans)) != len(spans)
        or not set(spans).issubset(allowed)
    ):
        failures.append("BLIND_EVIDENCE_BINDING_INVALID")
    return failures


def apply_evidence_first_gate(
    *,
    provisional_receipt,
    proposed_receipt,
    composition_receipt,
    portfolio_view,
    lineage_delta,
    cross_replication_witnesses,
    initial_receipt,
    blind_receipts,
):
    lane = lineage_delta["proposed_admission_lane"]
    direct_approved = (
        initial_receipt["portfolio_decision"] == "ACTIVATE_DELTA"
        and initial_receipt["marginal_information_preference"] == "DELTA"
        and initial_receipt["opportunity_lineage_consistent"] is True
        and initial_receipt["delta_has_higher_marginal_cbit"] is True
    )
    blind_consensus = bool(
        len(blind_receipts) == len(AUDIT_ROLES)
        and {
            value["audit_role"] for value in blind_receipts
        } == set(AUDIT_ROLES)
        and all(
            value["marginal_information_preference"] == "DELTA"
            and value[
                "delta_has_higher_evidence_bound_marginal_cbit"
            ] is True
            and value[
                "resolved_evidence_counts_as_realized_cbit"
            ] is True
            and value[
                "same_truth_state_is_not_relation_redundancy"
            ] is True
            for value in blind_receipts
        )
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
    approved = direct_approved or blind_consensus
    accepted = bool(approved and lane_eligible and not protected)
    if not approved:
        reason = "EVIDENCE_FIRST_ACTIVATION_NOT_APPROVED"
    elif protected:
        reason = "SUPPORTED_NULL_PROTECTED"
    elif not lane_eligible:
        reason = "BOUND_LANE_REQUIREMENT_NOT_MET"
    elif blind_consensus and not direct_approved:
        reason = "BLIND_EVIDENCE_CONSENSUS_ACTIVATION"
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
        "source_blind_receipt_hashes": sorted(
            hash_payload(value) for value in blind_receipts
        ),
        "source_opportunity_hash": lineage_delta[
            "source_opportunity_hash"
        ],
        "bound_lane": lane,
        "direct_arbiter_approved": direct_approved,
        "blind_evidence_consensus": blind_consensus,
        "blind_roles_cannot_activate_directly": True,
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
