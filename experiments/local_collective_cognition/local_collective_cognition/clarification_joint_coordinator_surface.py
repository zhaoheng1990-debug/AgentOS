"""Build the identity-blind observed-conflict surface for v0.12."""

from __future__ import annotations

from .clarification_semantic_basis_panel import validate_semantic_basis_adjudication_response, validate_semantic_basis_reference
from .clarification_semantic_basis_holdout import validate_semantic_basis_holdout_artifact
from .provider_telemetry import hash_payload


SURFACE_VERSION = "clarification_joint_coordinator_surface_v0_12"


def build_joint_coordinator_surface(*, corpus_artifact, panel_reference, adjudication_pack, adjudication_response):
    validate_semantic_basis_holdout_artifact(corpus_artifact)
    validate_semantic_basis_reference(panel_reference)
    validate_semantic_basis_adjudication_response(adjudication_response, pack=adjudication_pack)
    public_cases = {case["blind_case_id"]: case for batch in corpus_artifact["public_surface"]["batches"] for case in batch["public_cases"]}
    decisions = {item["adjudication_id"]: item for item in adjudication_response["decisions"]}
    conflicts = []
    for record in panel_reference["cross_axis_inconsistency_records"]:
        blind_id = record["blind_case_id"]
        matches = [item for item in adjudication_pack["items"] if item["criterion"] == "SELECTION_BASIS" and item["public_prompt"] == public_cases[blind_id]["public_prompt"]]
        if len(matches) != 1:
            raise ValueError("joint_coordinator_adjudication_binding_invalid")
        item = matches[0]
        decision = decisions[item["adjudication_id"]]
        conflict_id = "joint-conflict-" + hash_payload([SURFACE_VERSION, panel_reference["artifact_hash"], blind_id])[:18]
        conflicts.append({
            "conflict_id": conflict_id,
            "public_prompt": public_cases[blind_id]["public_prompt"],
            "candidate_a": public_cases[blind_id]["candidate_a"],
            "candidate_b": public_cases[blind_id]["candidate_b"],
            "locked_consensus_axes": {
                "SELECTED_OBJECT": record["criteria"]["SELECTED_OBJECT"],
                "PRAGMATIC_PREFERENCE": record["criteria"]["PRAGMATIC_PREFERENCE"],
                "AXIS_ASSESSMENT_COMPLETE": record["criteria"]["AXIS_ASSESSMENT_COMPLETE"],
            },
            "consensus_support": {"independent_positions": 2, "agreement": "UNANIMOUS"},
            "basis_positions": item["positions"],
            "local_adjudication": {"selected_state": decision["selected_state"], "decision_basis": decision["decision_basis"], "confidence": decision["confidence"], "rationale": decision["rationale"]},
            "current_violation": record["violation"],
        })
    conflicts.sort(key=lambda item: hash_payload([SURFACE_VERSION, item["conflict_id"]]))
    commitment = {
        "surface_version": SURFACE_VERSION,
        "source_corpus_hash": corpus_artifact["artifact_hash"],
        "source_panel_reference_hash": panel_reference["artifact_hash"],
        "source_adjudication_pack_hash": adjudication_pack["pack_hash"],
        "source_adjudication_response_hash": hash_payload(adjudication_response),
        "source_identity": "WITHHELD",
        "construction_labels": "WITHHELD",
        "deepseek_predictions": "WITHHELD",
        "prior_scores": "WITHHELD",
        "public_conflicts": conflicts,
        "observed_conflict_count": len(conflicts),
        "generalization_holdout": False,
        "selection_authority": False,
        "retention_authority": False,
    }
    return {**commitment, "surface_hash": hash_payload(commitment)}


def validate_joint_coordinator_surface(surface, *, corpus_artifact=None, panel_reference=None, adjudication_pack=None, adjudication_response=None):
    commitment = {key: value for key, value in surface.items() if key != "surface_hash"}
    if surface.get("surface_hash") != hash_payload(commitment) or surface.get("surface_version") != SURFACE_VERSION or surface.get("observed_conflict_count") != len(surface.get("public_conflicts", [])):
        raise ValueError("joint_coordinator_surface_invalid")
    if any(key in str(surface["public_conflicts"]).casefold() for key in ("gpt-5.6", "gemini-3.1", "openai", "google")):
        raise ValueError("joint_coordinator_identity_leak")
    supplied = (corpus_artifact, panel_reference, adjudication_pack, adjudication_response)
    if any(value is not None for value in supplied):
        if not all(value is not None for value in supplied) or surface != build_joint_coordinator_surface(corpus_artifact=corpus_artifact, panel_reference=panel_reference, adjudication_pack=adjudication_pack, adjudication_response=adjudication_response):
            raise ValueError("joint_coordinator_surface_semantics_invalid")
