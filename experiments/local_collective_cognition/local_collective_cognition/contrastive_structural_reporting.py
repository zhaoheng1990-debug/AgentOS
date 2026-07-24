"""Mechanical reporting helpers for the contrastive-structure pilot."""

from __future__ import annotations


def audit_packet_quality(harness, packets):
    prompts = {item["item_id"]: item["prompt"] for item in
               harness.provider_inputs(tuple(packets))["questions"]}
    restatements = [item_id for item_id, packet in packets.items()
                    if packet["contrastive_packet"].strip().casefold()
                    == prompts[item_id].strip().casefold()]
    return {
        "audit_method": "MECHANICAL_EXACT_TEXT_ABSENCE_CHECK",
        "packet_items": len(packets),
        "exact_public_prompt_restatements": restatements,
        "independent_provider_semantic_quality_receipt_present": False,
        "semantic_quality_claim_authorized": False,
    }


def item_record(item_id, proposer_id, control, revision, packet, work_fn):
    return {
        "item_id": item_id, "proposer_model_id": proposer_id,
        "triggered": revision is not None, "contrastive_packet": packet,
        "control_problem": control.result,
        "final_problem": (revision or control).result,
        "control_work": work_fn(control),
        "incremental_revision_work": work_fn(revision) if revision else None,
    }


def selected_effect(audit, selected_ids):
    pairs = [item for item in audit["paired_items"] if item["item_id"] in selected_ids]
    return {
        "selected_items": len(pairs),
        "control_field_matches": sum(item["control_field_matches"] for item in pairs),
        "final_field_matches": sum(item["treatment_field_matches"] for item in pairs),
        "field_match_gain": sum(item["treatment_field_matches"]
                                - item["control_field_matches"] for item in pairs),
        "improved_items": sum(item["treatment_field_matches"] > item["control_field_matches"]
                              for item in pairs),
        "harmed_items": sum(item["treatment_field_matches"] < item["control_field_matches"]
                            for item in pairs),
    }
