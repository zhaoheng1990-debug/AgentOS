"""Frozen response contracts for the three-model reference panel."""

from __future__ import annotations

from .structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_STATES


PANEL_VERSION = "structure_model_reference_panel_v0_1"
ADJUDICATION_VERSION = "structure_model_reference_adjudication_v0_1"
LANE_SPECS = (
    ("annotation-lane-a", "OpenAI", "GPT-5.6"),
    ("annotation-lane-b", "Google", "Gemini-3.1"),
)
K3_SPEC = ("Moonshot", "Kimi-K3")


def annotation_response_contract():
    return {
        "required_top_level": [
            "panel_version", "panel_id", "lane_id", "pack_hash",
            "annotator_provider", "annotator_model", "annotation_session_ref", "labels",
        ],
        "required_label_fields": [
            "annotation_id", "criteria", "criterion_notes", "confidence",
        ],
        "criteria": list(JUDGE_CRITERIA),
        "allowed_states": list(JUDGE_STATES),
        "instruction": (
            "Return one JSON object only. Copy identity fields exactly. Supply one label per annotation_id, "
            "all six criteria, one short note per criterion, and confidence from 0 to 1."
        ),
    }


def validate_annotation_response(response, *, pack):
    required = set(annotation_response_contract()["required_top_level"])
    if not isinstance(response, dict) or set(response) != required:
        raise ValueError("reference_annotation_response_shape_invalid")
    expected = {
        "panel_version": PANEL_VERSION,
        "panel_id": pack["panel_id"],
        "lane_id": pack["lane_id"],
        "pack_hash": pack["pack_hash"],
        "annotator_provider": pack["expected_annotator"]["provider"],
        "annotator_model": pack["expected_annotator"]["model"],
    }
    if any(response.get(key) != value for key, value in expected.items()):
        raise ValueError("reference_annotation_response_binding_invalid")
    if not isinstance(response["annotation_session_ref"], str) or not response["annotation_session_ref"].strip():
        raise ValueError("reference_annotation_session_ref_required")
    labels = response["labels"]
    expected_ids = {item["annotation_id"] for item in pack["items"]}
    if not isinstance(labels, list) or len(labels) != len(expected_ids):
        raise ValueError("reference_annotation_label_count_invalid")
    observed = []
    label_fields = set(annotation_response_contract()["required_label_fields"])
    for label in labels:
        if not isinstance(label, dict) or set(label) != label_fields:
            raise ValueError("reference_annotation_label_shape_invalid")
        observed.append(label["annotation_id"])
        criteria = label["criteria"]
        if (not isinstance(criteria, dict)
                or set(criteria) != set(JUDGE_CRITERIA)
                or any(value not in JUDGE_STATES for value in label["criteria"].values())):
            raise ValueError("reference_annotation_criteria_invalid")
        notes = label["criterion_notes"]
        if (not isinstance(notes, dict)
                or set(notes) != set(JUDGE_CRITERIA)
                or any(not isinstance(note, str) or not note.strip() or len(note) > 500
                       for note in notes.values())):
            raise ValueError("reference_annotation_criterion_notes_invalid")
        confidence = label["confidence"]
        if (not isinstance(confidence, (int, float)) or isinstance(confidence, bool)
                or not 0 <= confidence <= 1):
            raise ValueError("reference_annotation_confidence_invalid")
    if len(observed) != len(set(observed)) or set(observed) != expected_ids:
        raise ValueError("reference_annotation_id_binding_invalid")


def adjudication_response_contract():
    return {
        "required_top_level": [
            "panel_version", "panel_id", "adjudication_pack_hash", "adjudicator_provider",
            "adjudicator_model", "adjudication_session_ref", "blinding_attestation", "decisions",
        ],
        "required_decision_fields": [
            "adjudication_id", "selected_state", "decision_basis", "confidence", "rationale",
        ],
        "allowed_states": list(JUDGE_STATES),
        "allowed_bases": ["POSITION_1", "POSITION_2", "INDEPENDENT_REASSESSMENT", "UNRESOLVED"],
        "required_blinding_attestation": {
            "pack_only_context": True,
            "annotator_identity_unavailable": True,
            "source_identity_unavailable": True,
            "prior_scores_unavailable": True,
            "external_pairing_not_used": True,
        },
    }


def validate_adjudication_response(response, *, pack):
    contract = adjudication_response_contract()
    if not isinstance(response, dict) or set(response) != set(contract["required_top_level"]):
        raise ValueError("reference_adjudication_response_shape_invalid")
    expected = {
        "panel_version": PANEL_VERSION, "panel_id": pack["panel_id"],
        "adjudication_pack_hash": pack["pack_hash"],
        "adjudicator_provider": K3_SPEC[0], "adjudicator_model": K3_SPEC[1],
    }
    if any(response.get(key) != value for key, value in expected.items()):
        raise ValueError("reference_adjudication_response_binding_invalid")
    if not isinstance(response["adjudication_session_ref"], str) or not response["adjudication_session_ref"].strip():
        raise ValueError("reference_adjudication_session_ref_required")
    if response["blinding_attestation"] != contract["required_blinding_attestation"]:
        raise ValueError("reference_adjudication_blinding_attestation_invalid")
    expected_ids = {item["adjudication_id"] for item in pack["items"]}
    decisions = response["decisions"]
    if not isinstance(decisions, list) or len(decisions) != len(expected_ids):
        raise ValueError("reference_adjudication_decision_count_invalid")
    item_index = {item["adjudication_id"]: item for item in pack["items"]}
    observed = []
    for decision in decisions:
        if not isinstance(decision, dict) or set(decision) != set(contract["required_decision_fields"]):
            raise ValueError("reference_adjudication_decision_shape_invalid")
        observed.append(decision["adjudication_id"])
        if (decision["selected_state"] not in JUDGE_STATES
                or decision["decision_basis"] not in contract["allowed_bases"]
                or not isinstance(decision["rationale"], str) or not decision["rationale"].strip()):
            raise ValueError("reference_adjudication_decision_invalid")
        confidence = decision["confidence"]
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            raise ValueError("reference_adjudication_confidence_invalid")
        item = item_index.get(decision["adjudication_id"])
        positions = {position["position_id"]: position["state"] for position in item["positions"]} if item else {}
        basis = decision["decision_basis"]
        if (basis in positions and decision["selected_state"] != positions[basis]):
            raise ValueError("reference_adjudication_position_state_invalid")
        if basis == "UNRESOLVED" and decision["selected_state"] != "UNCERTAIN":
            raise ValueError("reference_adjudication_unresolved_state_invalid")
    if len(observed) != len(set(observed)) or set(observed) != expected_ids:
        raise ValueError("reference_adjudication_id_binding_invalid")
