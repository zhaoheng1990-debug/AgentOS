"""Contracts for isolated negative-evidence receipt auditors."""

from __future__ import annotations


AUDIT_VERSION = "negative_evidence_specialist_audit_v0_1"
AUDIT_STATES = ("PASS", "VETO", "UNCERTAIN")
LIVE_AMBIGUITY_AUDIT = "LIVE_AMBIGUITY"
FABRICATION_AUDIT = "FABRICATION_DEPENDENCE"
AUDIT_KINDS = (LIVE_AMBIGUITY_AUDIT, FABRICATION_AUDIT)
TASK_KINDS = {
    LIVE_AMBIGUITY_AUDIT: "negative_evidence_live_ambiguity_audit",
    FABRICATION_AUDIT: "negative_evidence_fabrication_audit",
}


def specialist_audit_schema(batch_id, audit_kind, candidate_ids):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["batch_id", "audit_kind", "assessments", "evidence_refs"],
        "properties": {
            "batch_id": {"type": "string", "enum": [batch_id]},
            "audit_kind": {"type": "string", "enum": [audit_kind]},
            "assessments": {
                "type": "array",
                "minItems": len(candidate_ids),
                "maxItems": len(candidate_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "blind_candidate_id", "state", "evidence_basis",
                        "counterfactual", "confidence",
                    ],
                    "properties": {
                        "blind_candidate_id": {
                            "type": "string", "enum": list(candidate_ids),
                        },
                        "state": {"type": "string", "enum": list(AUDIT_STATES)},
                        "evidence_basis": {"type": "string"},
                        "counterfactual": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def validate_specialist_audit(payload, *, batch_id, audit_kind, candidate_ids,
                              evidence_refs):
    required = {"batch_id", "audit_kind", "assessments", "evidence_refs"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("negative_evidence_audit_shape_invalid")
    if (
        payload["batch_id"] != batch_id
        or payload["audit_kind"] != audit_kind
        or payload["evidence_refs"] != list(evidence_refs)
    ):
        raise ValueError("negative_evidence_audit_binding_invalid")
    assessments = payload["assessments"]
    if not isinstance(assessments, list) or len(assessments) != len(candidate_ids):
        raise ValueError("negative_evidence_audit_count_invalid")
    observed = []
    item_keys = {
        "blind_candidate_id", "state", "evidence_basis", "counterfactual", "confidence",
    }
    for item in assessments:
        if not isinstance(item, dict) or set(item) != item_keys:
            raise ValueError("negative_evidence_audit_assessment_shape_invalid")
        observed.append(item["blind_candidate_id"])
        if item["state"] not in AUDIT_STATES:
            raise ValueError("negative_evidence_audit_state_invalid")
        if not item["evidence_basis"].strip() or not item["counterfactual"].strip():
            raise ValueError("negative_evidence_audit_reason_required")
        confidence = item["confidence"]
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0 <= confidence <= 1
        ):
            raise ValueError("negative_evidence_audit_confidence_invalid")
    if len(observed) != len(set(observed)) or set(observed) != set(candidate_ids):
        raise ValueError("negative_evidence_audit_candidate_binding_invalid")
