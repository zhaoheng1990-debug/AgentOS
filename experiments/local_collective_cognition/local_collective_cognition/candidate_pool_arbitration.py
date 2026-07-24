"""Mechanical candidate-pool binding and arbitration for v0.36."""

from __future__ import annotations

import copy

from .provider_telemetry import hash_payload


CONTRACT_VERSION = "candidate_pool_arbitration_v0_36"
SOURCE_IDS = ("BASE", "COUNTER")


def relation_id(candidate):
    return (
        f"REL-{candidate['source_object_id']}-"
        f"{candidate['target_object_id']}"
    )


def build_candidate_pool(
    *, provisional_receipt, counter_receipt, item, replication_id
):
    candidates = []
    for source_id, receipt in (
        ("BASE", provisional_receipt),
        ("COUNTER", counter_receipt),
    ):
        for candidate in receipt["problem_candidates"]:
            source_candidate_id = candidate["candidate_id"]
            candidates.append({
                "pool_candidate_id": (
                    f"{source_id}:{source_candidate_id}"
                ),
                "relation_id": relation_id(candidate),
                "source_id": source_id,
                "source_candidate_id": source_candidate_id,
                "candidate": copy.deepcopy(candidate),
                "source_receipt_hash": hash_payload(receipt),
            })
    candidates.sort(key=lambda value: value["pool_candidate_id"])
    commitment = {
        "contract_version": CONTRACT_VERSION,
        "replication_id": replication_id,
        "case_id": item["case_id"],
        "candidates": candidates,
        "provider_candidate_generation_allowed": False,
        "selector_candidate_rewrite_allowed": False,
        "private_truth_exposed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def arbitration_schema(*, item, pool, refs):
    pool_ids = [
        value["pool_candidate_id"] for value in pool["candidates"]
    ]
    relation_ids = sorted({
        value["relation_id"] for value in pool["candidates"]
    })
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "case_id", "arm_id", "selected_relation_ids",
            "selected_pool_candidate_ids", "selected_problem_pool_id",
            "rationale", "evidence_refs",
        ],
        "properties": {
            "case_id": {
                "type": "string", "enum": [item["case_id"]],
            },
            "arm_id": {
                "type": "string", "enum": ["A2_ARBITRATED"],
            },
            "selected_relation_ids": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "uniqueItems": True,
                "items": {"type": "string", "enum": relation_ids},
            },
            "selected_pool_candidate_ids": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "uniqueItems": True,
                "items": {"type": "string", "enum": pool_ids},
            },
            "selected_problem_pool_id": {
                "type": "string", "enum": pool_ids,
            },
            "rationale": {"type": "string"},
            "evidence_refs": {
                "type": "array",
                "items": {
                    "type": "string", "enum": list(refs),
                },
            },
        },
    }


def validate_arbitration(*, selection, pool, item, refs):
    failures = []
    if not isinstance(selection, dict):
        return ["ARBITRATION_NOT_OBJECT"]
    if selection.get("case_id") != item["case_id"]:
        failures.append("CASE_BINDING_MISMATCH")
    if selection.get("arm_id") != "A2_ARBITRATED":
        failures.append("ARM_BINDING_MISMATCH")
    if selection.get("evidence_refs") != list(refs):
        failures.append("EVIDENCE_SCOPE_MISMATCH")
    pool_ids = selection.get("selected_pool_candidate_ids")
    relation_ids = selection.get("selected_relation_ids")
    by_id = {
        value["pool_candidate_id"]: value
        for value in pool["candidates"]
    }
    if (
        not isinstance(pool_ids, list)
        or len(pool_ids) != 3
        or len(set(pool_ids)) != 3
        or not set(pool_ids).issubset(by_id)
    ):
        failures.append("SELECTED_POOL_IDS_INVALID")
        return failures
    if (
        not isinstance(relation_ids, list)
        or len(relation_ids) != 3
        or len(set(relation_ids)) != 3
    ):
        failures.append("SELECTED_RELATION_IDS_INVALID")
        return failures
    paired_relations = [
        by_id[pool_id]["relation_id"] for pool_id in pool_ids
    ]
    if relation_ids != paired_relations:
        failures.append("POOL_RELATION_BINDING_MISMATCH")
    if selection.get("selected_problem_pool_id") not in pool_ids:
        failures.append("PRIMARY_SELECTION_NOT_INCLUDED")
    return failures


def materialize_arbitrated_receipt(
    *, selection, pool, provisional_receipt, item, refs
):
    failures = validate_arbitration(
        selection=selection, pool=pool, item=item, refs=refs
    )
    if failures:
        raise ValueError(",".join(failures))
    by_id = {
        value["pool_candidate_id"]: value
        for value in pool["candidates"]
    }
    final_candidates = []
    lineage = []
    final_problem_id = None
    for index, pool_id in enumerate(
        selection["selected_pool_candidate_ids"], 1
    ):
        entry = by_id[pool_id]
        final_id = f"C{index}"
        candidate = copy.deepcopy(entry["candidate"])
        candidate["candidate_id"] = final_id
        final_candidates.append(candidate)
        lineage.append({
            "final_candidate_id": final_id,
            "pool_candidate_id": pool_id,
            "relation_id": entry["relation_id"],
            "source_id": entry["source_id"],
            "source_candidate_id": entry["source_candidate_id"],
            "source_receipt_hash": entry["source_receipt_hash"],
        })
        if pool_id == selection["selected_problem_pool_id"]:
            final_problem_id = final_id
    raw = {
        "case_id": item["case_id"],
        "arm_id": "A1_ONTOLOGY",
        "problem_candidates": final_candidates,
        "selected_problem_id": final_problem_id,
        "rationale": selection["rationale"],
        "evidence_refs": list(refs),
        "object_census": copy.deepcopy(
            provisional_receipt["object_census"]
        ),
    }
    receipt_commitment = {
        "contract_version": CONTRACT_VERSION,
        "case_id": item["case_id"],
        "source_pool_hash": pool["artifact_hash"],
        "source_selection_hash": hash_payload(selection),
        "final_raw_receipt_hash": hash_payload(raw),
        "lineage": lineage,
        "selected_problem_final_id": final_problem_id,
        "provider_generated_final_candidates": False,
        "runtime_mechanical_materialization": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    arbitration_receipt = {
        **receipt_commitment,
        "artifact_hash": hash_payload(receipt_commitment),
    }
    return raw, arbitration_receipt
