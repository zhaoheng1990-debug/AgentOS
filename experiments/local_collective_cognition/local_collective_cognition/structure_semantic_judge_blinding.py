"""Deterministic source blinding for semantic structure-packet assessment."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structure_elicitor_fresh_holdout import CASES


BLINDING_VERSION = "structure_packet_semantic_blinding_v0_1"


def build_blind_surface(fresh_artifact, *, cases=CASES):
    prompts = {case.item_id: case.prompt for case in cases}
    model_ids = tuple(run["model_id"] for run in fresh_artifact["model_runs"])
    batches, bindings, excluded = [], {}, []
    for item_id, prompt in prompts.items():
        public_candidates = []
        for run in fresh_artifact["model_runs"]:
            trial = next(item for item in run["trials"] if item["item_id"] == item_id)
            packet = trial.get("packet")
            source = {
                "model_id": run["model_id"], "item_id": item_id,
                "outcome_hash": trial["outcome"]["outcome_hash"],
                "mechanical_quality_score": trial["outcome"]["quality_score"],
                "provider_status": trial["outcome"]["provider_status"],
            }
            if not packet or not str(packet.get("contrastive_packet", "")).strip():
                excluded.append({**source, "reason": "SOURCE_PACKET_UNAVAILABLE"})
                continue
            packet_text = str(packet["contrastive_packet"])
            if any(model_id.casefold() in packet_text.casefold() for model_id in model_ids):
                excluded.append({**source, "reason": "SOURCE_IDENTITY_LEAK"})
                continue
            blind_id = "blind-" + hash_payload([
                BLINDING_VERSION, fresh_artifact["artifact_hash"], item_id, source["outcome_hash"],
            ])[:16]
            public_candidates.append({
                "blind_candidate_id": blind_id,
                "contrastive_packet": packet_text,
            })
            bindings[blind_id] = {**source, "packet_hash": hash_payload(packet)}
        public_candidates.sort(key=lambda item: hash_payload([
            BLINDING_VERSION, fresh_artifact["artifact_hash"], item_id,
            item["blind_candidate_id"],
        ]))
        batch_id = "semantic-batch-" + hash_payload([
            BLINDING_VERSION, fresh_artifact["artifact_hash"], item_id,
        ])[:16]
        batches.append({
            "batch_id": batch_id,
            "public_prompt": prompt,
            "public_candidates": public_candidates,
        })
    commitment = {
        "blinding_version": BLINDING_VERSION,
        "source_artifact_hash": fresh_artifact["artifact_hash"],
        "batches": batches,
        "bindings": bindings,
        "excluded_trials": excluded,
    }
    return {**commitment, "surface_hash": hash_payload(commitment)}


def validate_blind_surface(surface):
    committed = {key: value for key, value in surface.items() if key != "surface_hash"}
    if surface.get("surface_hash") != hash_payload(committed):
        raise ValueError("semantic_blind_surface_hash_invalid")
    public_ids = []
    for batch in surface["batches"]:
        if set(batch) != {"batch_id", "public_prompt", "public_candidates"}:
            raise ValueError("semantic_blind_batch_shape_invalid")
        for candidate in batch["public_candidates"]:
            if set(candidate) != {"blind_candidate_id", "contrastive_packet"}:
                raise ValueError("semantic_blind_candidate_shape_invalid")
            public_ids.append(candidate["blind_candidate_id"])
    if len(public_ids) != len(set(public_ids)) or set(public_ids) != set(surface["bindings"]):
        raise ValueError("semantic_blind_candidate_binding_invalid")
