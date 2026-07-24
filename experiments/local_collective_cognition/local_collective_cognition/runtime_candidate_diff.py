"""Runtime-owned candidate diff and derived revision receipts."""

from __future__ import annotations

import copy

from .collaborative_stability_experiment import exact_three_schema
from .provider_telemetry import hash_payload


DIFF_VERSION = "runtime_candidate_diff_v0_35"
CANDIDATE_FIELDS = (
    "candidate_id", "lane", "question", "source_object_id",
    "target_object_id", "constraint_object_ids", "epistemic_basis",
    "structural_origin", "falsifier", "required_observation",
    "evidence_span_ids", "estimated_test_cost",
)


def runtime_diff_revision_schema(*, item, refs, provisional_receipt):
    schema = copy.deepcopy(exact_three_schema(
        item=item, arm_id="A1_ONTOLOGY", refs=refs,
    ))
    candidate_ids = [
        value["candidate_id"]
        for value in provisional_receipt["problem_candidates"]
    ]
    schema["properties"]["problem_candidates"]["items"]["properties"][
        "candidate_id"
    ] = {"type": "string", "enum": candidate_ids}
    schema["required"].append("revision_summary")
    schema["properties"]["revision_summary"] = {"type": "string"}
    return schema


def derive_candidate_diff(
    *, provisional_receipt, final_receipt, trigger, item
):
    original_values = provisional_receipt.get("problem_candidates", [])
    final_values = final_receipt.get("problem_candidates", [])
    original = {
        value.get("candidate_id"): value
        for value in original_values if isinstance(value, dict)
    }
    final = {
        value.get("candidate_id"): value
        for value in final_values if isinstance(value, dict)
    }
    failures = []
    if (
        len(original_values) != 3
        or len(original) != 3
        or len(final_values) != 3
        or len(final) != 3
        or set(original) != set(final)
    ):
        failures.append("CANDIDATE_SLOT_SET_MISMATCH")
    actions = []
    for candidate_id in sorted(set(original) & set(final)):
        before = original[candidate_id]
        after = final[candidate_id]
        changed_fields = [
            field for field in CANDIDATE_FIELDS
            if before.get(field) != after.get(field)
        ]
        relation_changed = any(
            field in changed_fields
            for field in ("source_object_id", "target_object_id")
        )
        if not changed_fields:
            action = "KEEP"
        elif relation_changed:
            action = "REPLACE"
        else:
            action = "REVISE"
        actions.append({
            "candidate_id": candidate_id,
            "action": action,
            "changed_fields": changed_fields,
            "relation_changed": relation_changed,
            "final_evidence_span_ids": list(
                after.get("evidence_span_ids", [])
            ),
        })
    commitment = {
        "diff_version": DIFF_VERSION,
        "case_id": item["case_id"],
        "source_provisional_receipt_hash": hash_payload(
            provisional_receipt
        ),
        "source_final_receipt_hash": hash_payload(final_receipt),
        "source_trigger_receipt_hash": trigger["artifact_hash"],
        "inherited_route_id": trigger["route_id"],
        "private_truth_used": False,
        "provider_declared_action_used": False,
        "provider_declared_route_used": False,
        "revision_actions": actions,
        "failures": failures,
        "candidate_slot_set_preserved": not failures,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_candidate_diff(
    *, receipt, provisional_receipt, final_receipt, trigger, item
):
    expected = derive_candidate_diff(
        provisional_receipt=provisional_receipt,
        final_receipt=final_receipt,
        trigger=trigger,
        item=item,
    )
    if receipt != expected:
        raise ValueError("runtime_candidate_diff_invalid")
