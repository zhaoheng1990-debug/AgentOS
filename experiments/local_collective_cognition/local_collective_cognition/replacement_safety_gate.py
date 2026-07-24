"""Zero-call non-degradation gate for compact-delta replacement."""

from __future__ import annotations

from .provider_telemetry import hash_payload


GATE_VERSION = "replacement_safety_gate_v0_43"


def apply_replacement_safety_gate(
    *,
    provisional_receipt,
    provisional_projection,
    proposed_receipt,
    composition_receipt,
    item,
):
    """Accept only mechanically witnessed or strong focal replacements."""
    selected_ids = {
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
        and value["pool_candidate_id"] not in selected_ids
    ]
    disposition_by_id = {
        f"BASE:{value['candidate_id']}": value["disposition"]
        for value in provisional_projection["candidate_components"]
    }
    counter_selected = counter["pool_candidate_id"] in selected_ids
    dropped_quarantined = any(
        disposition_by_id.get(value["pool_candidate_id"])
        == "QUARANTINED_COMPONENT"
        for value in dropped
    )
    protected_supported_null = any(
        value["provider_candidate_value"]["relation_truth_state"]
        == "SUPPORTED_NULL"
        for value in dropped
    )
    semantic = counter["provider_candidate_value"]
    strong_focal_relation = (
        counter["relation_id"].endswith(
            f"-{item['focal_object_id']}"
        )
        and semantic["relation_truth_state"] == "SUPPORTED_EFFECT"
        and semantic["constraint_binding"] == "ADEQUATE"
        and semantic["expected_cbit"] == "HIGH"
    )
    if not counter_selected:
        accepted = False
        reason = "COUNTER_NOT_SELECTED"
    elif dropped_quarantined:
        accepted = True
        reason = "QUARANTINED_BASE_REPLACEMENT"
    elif protected_supported_null:
        accepted = False
        reason = "SUPPORTED_NULL_PROTECTED"
    elif strong_focal_relation:
        accepted = True
        reason = "STRONG_FOCAL_RELATION"
    else:
        accepted = False
        reason = "NON_DEGRADATION_WITNESS_ABSENT"
    commitment = {
        "gate_version": GATE_VERSION,
        "case_id": item["case_id"],
        "source_provisional_hash": hash_payload(provisional_receipt),
        "source_provisional_projection_hash": provisional_projection[
            "artifact_hash"
        ],
        "source_proposed_hash": hash_payload(proposed_receipt),
        "source_composition_hash": composition_receipt["artifact_hash"],
        "counter_pool_candidate_id": counter["pool_candidate_id"],
        "counter_relation_id": counter["relation_id"],
        "counter_selected_by_composer": counter_selected,
        "dropped_base_pool_candidate_ids": [
            value["pool_candidate_id"] for value in dropped
        ],
        "dropped_base_dispositions": {
            value["pool_candidate_id"]: disposition_by_id.get(
                value["pool_candidate_id"], "MISSING"
            )
            for value in dropped
        },
        "dropped_quarantined": dropped_quarantined,
        "protected_supported_null": protected_supported_null,
        "strong_focal_relation": strong_focal_relation,
        "accepted": accepted,
        "reason": reason,
        "provider_call_added_by_gate": False,
        "private_truth_used": False,
        "provider_selected_final_candidates": False,
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
