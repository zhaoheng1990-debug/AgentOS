"""Identity-blind surface for the independent hard-null holdout."""

from __future__ import annotations

from .ambiguity_hard_null_holdout import (
    CASES,
    HOLDOUT_SPEC,
    MATERIALITY_CONTROL_HASH,
    RECEIPT_QUALITY_CONTROL_HASH,
    validate_hard_null_holdout_spec,
)
from .provider_telemetry import hash_payload


SURFACE_VERSION = "ambiguity_hard_null_blind_surface_v0_1"
FIRST_POSITION_ROLE = (
    "PROPOSER", "PROPOSER", "SKEPTIC", "SKEPTIC",
    "PROPOSER", "PROPOSER", "SKEPTIC", "SKEPTIC",
    "PROPOSER", "PROPOSER", "SKEPTIC", "SKEPTIC",
    "PROPOSER", "PROPOSER", "SKEPTIC", "SKEPTIC",
)


def build_hard_null_surface(*, role_artifact, model_runs, batch_size=4):
    validate_hard_null_holdout_spec()
    if batch_size != 4:
        raise ValueError("hard_null_surface_batch_size_frozen")
    _validate_hash(role_artifact, "role_artifact")
    roles = role_artifact["role_candidates"]
    proposer_id = roles["ambiguity_proposer"]["model_id"]
    skeptic_id = roles["null_skeptic"]["model_id"]
    runs = {run["model_id"]: run for run in model_runs}
    if set(runs) != {proposer_id, skeptic_id}:
        raise ValueError("hard_null_role_run_surface_invalid")
    if (
        runs[proposer_id]["provider_id"] != roles["ambiguity_proposer"]["provider_id"]
        or runs[skeptic_id]["provider_id"] != roles["null_skeptic"]["provider_id"]
    ):
        raise ValueError("hard_null_role_provider_binding_invalid")
    indexed = {
        model_id: {trial["item_id"]: trial for trial in run["trials"]}
        for model_id, run in runs.items()
    }
    case_ids = {case.item_id for case in CASES}
    if any(set(trials) != case_ids for trials in indexed.values()):
        raise ValueError("hard_null_trial_surface_invalid")

    items, bindings = [], {}
    for index, case in enumerate(CASES):
        ordered = (("PROPOSER", proposer_id), ("SKEPTIC", skeptic_id))
        if FIRST_POSITION_ROLE[index] == "SKEPTIC":
            ordered = tuple(reversed(ordered))
        receipts, item_bindings = [], {}
        for position, (role, model_id) in zip(("POSITION_A", "POSITION_B"), ordered):
            receipts.append(_anonymous_receipt(position, indexed[model_id][case.item_id]))
            item_bindings[position] = {
                "role": role,
                "model_id": model_id,
                "model_run_hash": runs[model_id]["model_run_hash"],
            }
        coordination_id = "hard-null-" + hash_payload({
            "item_id": case.item_id, "spec": HOLDOUT_SPEC["spec_hash"],
        })[:16]
        items.append({
            "coordination_item_id": coordination_id,
            "public_task": case.public_input(),
            "anonymous_receipts": receipts,
        })
        bindings[coordination_id] = {
            "source_item_id": case.item_id,
            "positions": item_bindings,
        }
    batches = [
        {
            "batch_id": f"hard-null-batch-{index // batch_size + 1:02d}",
            "items": items[index:index + batch_size],
        }
        for index in range(0, len(items), batch_size)
    ]
    commitment = {
        "surface_version": SURFACE_VERSION,
        "holdout_spec_hash": HOLDOUT_SPEC["spec_hash"],
        "materiality_control_hash": MATERIALITY_CONTROL_HASH,
        "receipt_quality_control_hash": RECEIPT_QUALITY_CONTROL_HASH,
        "role_artifact_hash": role_artifact["artifact_hash"],
        "public_batches": batches,
        "private_position_bindings": bindings,
        "source_identity_exposed": False,
        "predecessor_labels_exposed": False,
        "hidden_truth_exposed": False,
        "position_schedule": list(FIRST_POSITION_ROLE),
        "batch_size": batch_size,
    }
    return {**commitment, "surface_hash": hash_payload(commitment)}


def validate_hard_null_surface(surface, *, role_artifact, model_runs):
    commitment = {key: value for key, value in surface.items() if key != "surface_hash"}
    if surface.get("surface_hash") != hash_payload(commitment):
        raise ValueError("hard_null_surface_hash_invalid")
    if surface != build_hard_null_surface(
        role_artifact=role_artifact,
        model_runs=model_runs,
        batch_size=surface.get("batch_size", 4),
    ):
        raise ValueError("hard_null_surface_semantics_invalid")


def _anonymous_receipt(position, trial):
    source = trial.get("provider_payload") or {}
    return {
        "position": position,
        "discovery_state": trial["outcome"]["observed_state"],
        "rival_a": str(source.get("rival_a") or ""),
        "rival_b": str(source.get("rival_b") or ""),
        "decisive_contrast": str(source.get("decisive_contrast") or ""),
        "discriminating_question": str(source.get("discriminating_question") or ""),
        "confidence": (
            source.get("confidence")
            if isinstance(source.get("confidence"), (int, float)) else None
        ),
        "packet_contract_valid": trial["outcome"]["packet_contract_valid"],
        "provider_status": trial["outcome"]["provider_status"],
    }


def _validate_hash(artifact, name):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError(f"hard_null_{name}_hash_invalid")
