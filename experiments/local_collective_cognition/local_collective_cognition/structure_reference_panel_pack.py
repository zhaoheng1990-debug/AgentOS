"""Build two independently aliased blind annotation packs and a private manifest."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structure_reference_panel_contracts import (
    LANE_SPECS, PANEL_VERSION, annotation_response_contract,
)
from .structure_semantic_judge_contracts import RUBRIC


def build_reference_panel(*, semantic_artifact):
    source_hash = semantic_artifact["artifact_hash"]
    panel_id = "structure-panel-" + hash_payload([PANEL_VERSION, source_hash])[:16]
    candidates = _source_candidates(semantic_artifact["blind_surface"])
    packs, lane_bindings = [], {}
    for lane_id, provider, model in LANE_SPECS:
        items, bindings = [], {}
        for candidate in candidates:
            annotation_id = "annotation-" + hash_payload([
                PANEL_VERSION, source_hash, lane_id, candidate["blind_candidate_id"],
            ])[:18]
            items.append({
                "annotation_id": annotation_id,
                "public_prompt": candidate["public_prompt"],
                "contrastive_packet": candidate["contrastive_packet"],
            })
            bindings[annotation_id] = candidate["blind_candidate_id"]
        items.sort(key=lambda item: hash_payload([lane_id, item["annotation_id"]]))
        commitment = {
            "panel_version": PANEL_VERSION,
            "panel_id": panel_id,
            "lane_id": lane_id,
            "expected_annotator": {"provider": provider, "model": model},
            "source_identity": "WITHHELD",
            "prior_scores": "WITHHELD",
            "candidate_order": "LANE_SPECIFIC_HASH_RANDOMIZED",
            "rubric": RUBRIC,
            "instructions": (
                "Assess every packet independently against its public prompt. Do not compare packets, infer source, "
                "use prior model reputation, solve the numeric task, or claim ground-truth authority. Preserve UNCERTAIN."
            ),
            "items": items,
            "response_contract": annotation_response_contract(),
        }
        packs.append({**commitment, "pack_hash": hash_payload(commitment)})
        lane_bindings[lane_id] = bindings
    manifest_commitment = {
        "panel_version": PANEL_VERSION,
        "panel_id": panel_id,
        "source_semantic_artifact_hash": source_hash,
        "source_semantic_report_hash": semantic_artifact["report"]["report_hash"],
        "rubric_hash": hash_payload(RUBRIC),
        "lane_pack_hashes": {pack["lane_id"]: pack["pack_hash"] for pack in packs},
        "private_lane_bindings": lane_bindings,
        "private_source_bindings": semantic_artifact["blind_surface"]["bindings"],
        "private_prior_semantic_trials": semantic_artifact["report"]["trials"],
        "candidate_count": len(candidates),
        "criterion_count": len(RUBRIC),
        "reference_state": "AWAITING_MODEL_ANNOTATIONS",
        "ground_truth_claim": False,
        "retention_authority": False,
    }
    manifest = {**manifest_commitment, "manifest_hash": hash_payload(manifest_commitment)}
    return tuple(packs), manifest


def validate_reference_panel(*, packs, manifest, semantic_artifact=None):
    manifest_commitment = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if manifest.get("manifest_hash") != hash_payload(manifest_commitment):
        raise ValueError("reference_panel_manifest_hash_invalid")
    if (len(packs) != len(LANE_SPECS)
            or {(pack.get("lane_id"), pack.get("expected_annotator", {}).get("provider"),
                 pack.get("expected_annotator", {}).get("model")) for pack in packs}
            != set(LANE_SPECS)):
        raise ValueError("reference_panel_lane_surface_invalid")
    for pack in packs:
        commitment = {key: value for key, value in pack.items() if key != "pack_hash"}
        if (pack.get("pack_hash") != hash_payload(commitment)
                or pack.get("panel_id") != manifest["panel_id"]
                or manifest["lane_pack_hashes"].get(pack["lane_id"]) != pack["pack_hash"]):
            raise ValueError("reference_panel_pack_binding_invalid")
        ids = {item["annotation_id"] for item in pack["items"]}
        if ids != set(manifest["private_lane_bindings"][pack["lane_id"]]):
            raise ValueError("reference_panel_alias_binding_invalid")
    if semantic_artifact is not None:
        expected_packs, expected_manifest = build_reference_panel(semantic_artifact=semantic_artifact)
        if tuple(packs) != expected_packs or manifest != expected_manifest:
            raise ValueError("reference_panel_semantics_invalid")


def _source_candidates(surface):
    candidates = []
    for batch in surface["batches"]:
        for item in batch["public_candidates"]:
            candidates.append({
                "blind_candidate_id": item["blind_candidate_id"],
                "public_prompt": item.get("public_prompt", batch.get("public_prompt")),
                "contrastive_packet": item["contrastive_packet"],
            })
    return candidates
