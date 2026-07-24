"""Preserve an honestly disclosed context-compromised K3 response as shadow evidence."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structure_reference_panel_contracts import JUDGE_CRITERIA, JUDGE_STATES, K3_SPEC, PANEL_VERSION
from .structure_reference_panel_disagreement import validate_adjudication_bundle


FALSE_ATTESTATIONS = (
    "pack_only_context", "annotator_identity_unavailable", "source_identity_unavailable",
    "prior_scores_unavailable", "external_pairing_not_used",
)


def build_compromised_shadow(*, response, source_zip_sha256, response_entry_sha256,
                             adjudication_pack, adjudication_manifest, panel_packs,
                             panel_manifest, annotation_responses, prior_shadow):
    validate_adjudication_bundle(
        pack=adjudication_pack, manifest=adjudication_manifest,
        panel_packs=panel_packs, panel_manifest=panel_manifest,
        responses=annotation_responses,
    )
    _validate_response(response, adjudication_pack)
    _validate_prior_shadow(prior_shadow, panel_manifest)
    decisions = {item["adjudication_id"]: item for item in response["decisions"]}
    cells = {
        (item["blind_candidate_id"], item["criterion"]): item["selected_state"]
        for item in adjudication_manifest["agreement_records"]
    }
    for adjudication_id, binding in adjudication_manifest["private_disagreement_bindings"].items():
        cells[(binding["blind_candidate_id"], binding["criterion"])] = decisions[adjudication_id]["selected_state"]
    labels = [{
        "blind_candidate_id": blind_id,
        "criteria": {criterion: cells[(blind_id, criterion)] for criterion in JUDGE_CRITERIA},
    } for blind_id in sorted({key[0] for key in cells})]
    prior_decisions = {item["adjudication_id"]: item for item in prior_shadow["shadow_decisions"]}
    flips = [{
        "adjudication_id": adjudication_id,
        "prior_state": prior_decisions[adjudication_id]["selected_state"],
        "compromised_response_state": decision["selected_state"],
    } for adjudication_id, decision in decisions.items()
        if prior_decisions[adjudication_id]["selected_state"] != decision["selected_state"]]
    old_verdicts = _strict_verdicts(prior_shadow["labels"])
    new_verdicts = _strict_verdicts(labels)
    commitment = {
        "panel_id": panel_manifest["panel_id"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "source_zip_sha256": source_zip_sha256, "response_entry_sha256": response_entry_sha256,
        "response_hash": hash_payload(response), "prior_shadow_hash": prior_shadow["artifact_hash"],
        "blinding_status": response["blinding_attestation"]["blinding_status"],
        "blinding_disclosure": response["blinding_attestation"]["disclosure"],
        "definition_sensitivity_note": response["definition_sensitivity_note"],
        "shadow_decisions": sorted(response["decisions"], key=lambda item: item["adjudication_id"]),
        "labels": labels, "label_count": len(cells),
        "dispute_flip_count": len(flips), "dispute_count": len(decisions),
        "dispute_flip_rate": len(flips) / len(decisions), "dispute_flips": flips,
        "packet_verdict_change_count": sum(old_verdicts[key] != new_verdicts[key] for key in old_verdicts),
        "semantic_surface_valid": True, "protocol_compliant": False,
        "protocol_failures": [f"FALSE_{name.upper()}" for name in FALSE_ATTESTATIONS],
        "candidate_state": "CONTEXT_COMPROMISED_ADJUDICATION_SHADOW_CANDIDATE",
        "ground_truth_claim": False, "human_gold_claim": False,
        "selection_authority": False, "retention_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _validate_response(response, pack):
    expected_keys = {
        "panel_version", "panel_id", "adjudication_pack_hash", "adjudicator_provider",
        "adjudicator_model", "adjudication_session_ref", "blinding_attestation",
        "decisions", "definition_sensitivity_note",
    }
    if not isinstance(response, dict) or set(response) != expected_keys:
        raise ValueError("compromised_adjudication_response_shape_invalid")
    if (response["panel_version"] != PANEL_VERSION or response["panel_id"] != pack["panel_id"]
            or response["adjudication_pack_hash"] != pack["pack_hash"]
            or (response["adjudicator_provider"], response["adjudicator_model"]) != K3_SPEC):
        raise ValueError("compromised_adjudication_response_binding_invalid")
    attestation = response["blinding_attestation"]
    if (not isinstance(attestation, dict) or any(attestation.get(key) is not False for key in FALSE_ATTESTATIONS)
            or attestation.get("blinding_status") != "COMPROMISED_BY_SESSION_CONTEXT"
            or not isinstance(attestation.get("disclosure"), str) or not attestation["disclosure"].strip()):
        raise ValueError("compromised_adjudication_disclosure_invalid")
    items = {item["adjudication_id"]: item for item in pack["items"]}
    decisions = response["decisions"]
    if not isinstance(decisions, list) or len(decisions) != len(items):
        raise ValueError("compromised_adjudication_decision_count_invalid")
    observed = []
    fields = {"adjudication_id", "selected_state", "decision_basis", "confidence", "rationale"}
    for decision in decisions:
        if not isinstance(decision, dict) or set(decision) != fields:
            raise ValueError("compromised_adjudication_decision_shape_invalid")
        observed.append(decision["adjudication_id"])
        item = items.get(decision["adjudication_id"])
        positions = {position["position_id"]: position["state"] for position in item["positions"]} if item else {}
        if (decision["selected_state"] not in JUDGE_STATES
                or decision["decision_basis"] not in positions
                or positions[decision["decision_basis"]] != decision["selected_state"]
                or not isinstance(decision["confidence"], (int, float))
                or isinstance(decision["confidence"], bool) or not 0 <= decision["confidence"] <= 1
                or not isinstance(decision["rationale"], str) or not decision["rationale"].strip()):
            raise ValueError("compromised_adjudication_decision_invalid")
    if len(observed) != len(set(observed)) or set(observed) != set(items):
        raise ValueError("compromised_adjudication_id_binding_invalid")


def _validate_prior_shadow(artifact, manifest):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if (artifact.get("artifact_hash") != hash_payload(commitment)
            or artifact.get("panel_id") != manifest["panel_id"]
            or artifact.get("candidate_state") != "IDENTITY_AWARE_SHADOW_REFERENCE_CANDIDATE"):
        raise ValueError("compromised_adjudication_prior_shadow_invalid")


def _strict_verdicts(labels):
    return {
        item["blind_candidate_id"]: all(state == "PRESENT" for state in item["criteria"].values())
        for item in labels
    }
