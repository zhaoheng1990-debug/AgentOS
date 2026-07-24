"""Independent same-stage EFFECT witness contract for v0.55."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CONTRACT_VERSION = "independent_effect_witness_contract_v0_55"


def derive_independent_effect_witnesses(
    *,
    raw_receipts,
    lineage_valid_keys,
    source_replication_id,
    arm_id,
    case_id,
    source_object_id,
    target_object_id,
):
    valid = set(lineage_valid_keys)
    witnesses = []
    for key, receipt in sorted(raw_receipts.items()):
        parts = key.split(":", 3)
        if len(parts) != 4:
            continue
        rep, receipt_arm, stage, receipt_case = parts
        if (
            rep == source_replication_id
            or receipt_arm != arm_id
            or stage != "PROVIDER_COMPACT_DELTA"
            or receipt_case != case_id
            or f"{rep}:{receipt_arm}:{receipt_case}" not in valid
            or receipt.get("proposed_admission_lane") != "EFFECT"
            or receipt.get("source_opportunity_type") != "EFFECT"
            or receipt.get("source_object_id") != source_object_id
            or receipt.get("target_object_id") != target_object_id
        ):
            continue
        commitment = {
            "witness_version": CONTRACT_VERSION,
            "case_id": case_id,
            "source_replication_id": source_replication_id,
            "witness_replication_id": rep,
            "arm_id": arm_id,
            "source_object_id": source_object_id,
            "target_object_id": target_object_id,
            "source_witness_receipt_hash": hash_payload(receipt),
            "source_opportunity_hash": receipt[
                "source_opportunity_hash"
            ],
            "source_evidence_span_ids": list(
                receipt["source_opportunity_evidence_span_ids"]
            ),
            "witness_lineage_contract_valid": True,
            "same_stage_independent_context_required": True,
            "private_truth_used": False,
            "selection_authority": False,
            "retention_authority": False,
            "production_authority": False,
        }
        witnesses.append({
            **commitment, "artifact_hash": hash_payload(commitment)
        })
    return witnesses
