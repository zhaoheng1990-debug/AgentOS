"""Build a counterbalanced identity-blind surface from two discovery roles."""

from __future__ import annotations

from .ambiguity_coordinator_holdout import CASES, HOLDOUT_SPEC, validate_coordinator_holdout_spec
from .provider_telemetry import hash_payload


SURFACE_VERSION = "ambiguity_coordinator_blind_surface_v0_1"
COMPACT_SURFACE_VERSION = "ambiguity_coordinator_blind_surface_v0_2"
FIRST_POSITION_ROLE = (
    "PROPOSER", "PROPOSER", "SKEPTIC", "SKEPTIC", "SKEPTIC", "SKEPTIC",
    "PROPOSER", "PROPOSER", "PROPOSER", "SKEPTIC", "SKEPTIC", "PROPOSER",
)


def build_coordinator_surface(*, role_artifact, model_runs, batch_size=6):
    validate_coordinator_holdout_spec()
    if batch_size not in {3, 6}:
        raise ValueError("ambiguity_coordinator_surface_batch_size_invalid")
    _validate_hash(role_artifact, "role_artifact")
    roles = role_artifact["role_candidates"]
    proposer_id = roles["ambiguity_proposer"]["model_id"]
    skeptic_id = roles["null_skeptic"]["model_id"]
    runs = {run["model_id"]: run for run in model_runs}
    if set(runs) != {proposer_id, skeptic_id}:
        raise ValueError("ambiguity_coordinator_role_run_surface_invalid")
    if (runs[proposer_id]["provider_id"] != roles["ambiguity_proposer"]["provider_id"]
            or runs[skeptic_id]["provider_id"] != roles["null_skeptic"]["provider_id"]):
        raise ValueError("ambiguity_coordinator_role_provider_binding_invalid")
    indexed = {model_id: {trial["item_id"]: trial for trial in run["trials"]}
               for model_id, run in runs.items()}
    if any(set(trials) != {case.item_id for case in CASES} for trials in indexed.values()):
        raise ValueError("ambiguity_coordinator_trial_surface_invalid")
    items, bindings = [], {}
    for index, case in enumerate(CASES):
        first_role = FIRST_POSITION_ROLE[index]
        ordered = (("PROPOSER", proposer_id), ("SKEPTIC", skeptic_id))
        if first_role == "SKEPTIC":
            ordered = tuple(reversed(ordered))
        positions, item_bindings = [], {}
        for position, (role, model_id) in zip(("POSITION_A", "POSITION_B"), ordered):
            positions.append(_anonymous_receipt(position, indexed[model_id][case.item_id]))
            item_bindings[position] = {"role": role, "model_id": model_id,
                                       "model_run_hash": runs[model_id]["model_run_hash"]}
        coordination_id = f"coord-{hash_payload({'item_id': case.item_id, 'spec': HOLDOUT_SPEC['spec_hash']})[:16]}"
        items.append({"coordination_item_id": coordination_id, "public_task": case.public_input(),
                      "anonymous_receipts": positions})
        bindings[coordination_id] = {"source_item_id": case.item_id, "positions": item_bindings}
    batches = [{"batch_id": f"coord-batch-{index // batch_size + 1:02d}",
                "items": items[index:index + batch_size]}
               for index in range(0, len(items), batch_size)]
    commitment = {
        "surface_version": SURFACE_VERSION if batch_size == 6 else COMPACT_SURFACE_VERSION,
        "holdout_spec_hash": HOLDOUT_SPEC["spec_hash"],
        "role_artifact_hash": role_artifact["artifact_hash"],
        "public_batches": batches, "private_position_bindings": bindings,
        "source_identity_exposed": False, "prior_scores_exposed": False,
        "hidden_truth_exposed": False, "position_schedule": list(FIRST_POSITION_ROLE),
    }
    if batch_size != 6:
        commitment["batch_size"] = batch_size
    return {**commitment, "surface_hash": hash_payload(commitment)}


def validate_coordinator_surface(surface, *, role_artifact, model_runs):
    commitment = {key: value for key, value in surface.items() if key != "surface_hash"}
    if surface.get("surface_hash") != hash_payload(commitment):
        raise ValueError("ambiguity_coordinator_surface_hash_invalid")
    if surface != build_coordinator_surface(
            role_artifact=role_artifact, model_runs=model_runs,
            batch_size=surface.get("batch_size", 6)):
        raise ValueError("ambiguity_coordinator_surface_semantics_invalid")


def _anonymous_receipt(position, trial):
    source = trial.get("provider_payload") or {}
    return {
        "position": position,
        "discovery_state": trial["outcome"]["observed_state"],
        "rival_a": str(source.get("rival_a") or ""),
        "rival_b": str(source.get("rival_b") or ""),
        "decisive_contrast": str(source.get("decisive_contrast") or ""),
        "discriminating_question": str(source.get("discriminating_question") or ""),
        "confidence": source.get("confidence") if isinstance(source.get("confidence"), (int, float)) else None,
        "packet_contract_valid": trial["outcome"]["packet_contract_valid"],
        "provider_status": trial["outcome"]["provider_status"],
    }


def _validate_hash(artifact, name):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError(f"ambiguity_coordinator_{name}_hash_invalid")
