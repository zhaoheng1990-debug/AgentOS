"""Build a candidate-only reference label artifact from the three-model panel."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structure_reference_panel_contracts import (
    JUDGE_CRITERIA, PANEL_VERSION, validate_adjudication_response,
)
from .structure_reference_panel_disagreement import validate_adjudication_bundle


def build_reference_candidate(*, adjudication_pack, adjudication_manifest,
                              panel_packs, panel_manifest, annotation_responses,
                              response=None):
    validate_adjudication_bundle(
        pack=adjudication_pack, manifest=adjudication_manifest,
        panel_packs=panel_packs, panel_manifest=panel_manifest,
        responses=annotation_responses,
    )
    if adjudication_pack["items"]:
        if response is None:
            raise ValueError("reference_adjudication_response_required")
        validate_adjudication_response(response, pack=adjudication_pack)
    elif response is not None:
        validate_adjudication_response(response, pack=adjudication_pack)
    decisions = {
        item["adjudication_id"]: item for item in (response or {"decisions": []})["decisions"]
    }
    cells = {}
    for record in adjudication_manifest["agreement_records"]:
        key = (record["blind_candidate_id"], record["criterion"])
        cells[key] = {
            "state": record["selected_state"], "source": "GPT_GEMINI_AGREEMENT",
            "confidence": sum(record["lane_confidences"].values()) / len(record["lane_confidences"]),
        }
    for adjudication_id, binding in adjudication_manifest["private_disagreement_bindings"].items():
        decision = decisions[adjudication_id]
        key = (binding["blind_candidate_id"], binding["criterion"])
        cells[key] = {
            "state": decision["selected_state"], "source": "KIMI_K3_ADJUDICATION",
            "confidence": decision["confidence"], "decision_basis": decision["decision_basis"],
        }
    blind_ids = sorted({key[0] for key in cells})
    expected = {(blind_id, criterion) for blind_id in blind_ids for criterion in JUDGE_CRITERIA}
    if set(cells) != expected or len(cells) != adjudication_manifest["total_label_count"]:
        raise ValueError("reference_candidate_label_surface_incomplete")
    labels = [{
        "blind_candidate_id": blind_id,
        "criteria": {criterion: cells[(blind_id, criterion)]["state"] for criterion in JUDGE_CRITERIA},
        "criterion_sources": {
            criterion: cells[(blind_id, criterion)]["source"] for criterion in JUDGE_CRITERIA
        },
        "criterion_confidence": {
            criterion: cells[(blind_id, criterion)]["confidence"] for criterion in JUDGE_CRITERIA
        },
    } for blind_id in blind_ids]
    source_counts = {
        source: sum(cell["source"] == source for cell in cells.values())
        for source in ("GPT_GEMINI_AGREEMENT", "KIMI_K3_ADJUDICATION")
    }
    commitment = {
        "panel_version": PANEL_VERSION, "panel_id": adjudication_pack["panel_id"],
        "panel_manifest_hash": adjudication_manifest["panel_manifest_hash"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_response_hash": hash_payload(response) if response is not None else None,
        "labels": labels, "label_count": len(cells), "source_counts": source_counts,
        "uncertain_label_count": sum(cell["state"] == "UNCERTAIN" for cell in cells.values()),
        "adjudicator_unresolved_count": sum(
            decision.get("decision_basis") == "UNRESOLVED" for decision in decisions.values()
        ),
        "candidate_state": "MODEL_PANEL_REFERENCE_CANDIDATE",
        "ground_truth_claim": False, "human_gold_claim": False,
        "selection_authority": False, "retention_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_reference_candidate(artifact, *, adjudication_pack,
                                 adjudication_manifest, panel_packs,
                                 panel_manifest, annotation_responses,
                                 response=None):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("reference_candidate_artifact_hash_invalid")
    expected = build_reference_candidate(
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest, panel_packs=panel_packs,
        panel_manifest=panel_manifest, annotation_responses=annotation_responses,
        response=response,
    )
    if artifact != expected:
        raise ValueError("reference_candidate_artifact_semantics_invalid")
