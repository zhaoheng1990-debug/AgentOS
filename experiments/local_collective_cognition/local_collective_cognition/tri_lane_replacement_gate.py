"""Three-lane zero-call replacement gate v0.44."""

from __future__ import annotations

from .provider_telemetry import hash_payload


GATE_VERSION = "tri_lane_replacement_gate_v0_44"
NULL_TRUTH_STATES = {
    "SUPPORTED_NULL", "WEAK", "INDIRECT", "CONFLICTED",
}


def derive_cross_replication_witnesses(
    *,
    raw_receipts,
    source_replication_id,
    case_id,
    relation_id,
):
    """Return independent replication IDs that proposed the relation."""
    relation = relation_id.removeprefix("REL-").split("-")
    expected = tuple(relation)
    witnesses = set()
    for key, raw in raw_receipts.items():
        parts = key.split(":", 3)
        if len(parts) != 4:
            continue
        rep, _arm, stage, raw_case = parts
        if (
            stage != "STANDARD_COMPACT_DELTA"
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


def apply_tri_lane_replacement_gate(
    *,
    provisional_receipt,
    provisional_projection,
    proposed_receipt,
    composition_receipt,
    item,
    cross_replication_witnesses,
):
    """Route replacement through quarantine, effect, or null lane."""
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
    focal_relation = counter["relation_id"].endswith(
        f"-{item['focal_object_id']}"
    )
    effect_lane = (
        focal_relation
        and semantic["relation_truth_state"] == "SUPPORTED_EFFECT"
        and semantic["constraint_binding"] == "ADEQUATE"
        and semantic["expected_cbit"] == "HIGH"
        and len(cross_replication_witnesses) >= 1
    )
    informative_null_lane = (
        focal_relation
        and semantic["relation_truth_state"] in NULL_TRUTH_STATES
        and semantic["null_information_role"]
        == "RULES_OUT_PLAUSIBLE_CAUSE"
        and semantic["constraint_binding"] == "ADEQUATE"
        and semantic["research_value_disposition"] == "PRIORITIZE"
    )
    if not counter_selected:
        accepted = False
        lane = "NONE"
        reason = "COUNTER_NOT_SELECTED"
    elif dropped_quarantined:
        accepted = True
        lane = "QUARANTINE"
        reason = "QUARANTINED_BASE_REPLACEMENT"
    elif protected_supported_null:
        accepted = False
        lane = "NONE"
        reason = "SUPPORTED_NULL_PROTECTED"
    elif effect_lane:
        accepted = True
        lane = "EFFECT"
        reason = "CROSS_REPLICATED_STRONG_EFFECT"
    elif informative_null_lane:
        accepted = True
        lane = "INFORMATIVE_NULL"
        reason = "INFORMATIVE_NULL_VALUE"
    else:
        accepted = False
        lane = "NONE"
        reason = "TRI_LANE_WITNESS_ABSENT"
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
        "cross_replication_witnesses": list(
            cross_replication_witnesses
        ),
        "cross_replication_witness_count": len(
            cross_replication_witnesses
        ),
        "dropped_quarantined": dropped_quarantined,
        "protected_supported_null": protected_supported_null,
        "effect_lane_eligible": effect_lane,
        "informative_null_lane_eligible": informative_null_lane,
        "accepted": accepted,
        "lane": lane,
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
