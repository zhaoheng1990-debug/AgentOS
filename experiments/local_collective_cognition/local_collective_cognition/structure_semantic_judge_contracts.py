"""Frozen Provider contract for blind semantic assessment of structure packets."""

from __future__ import annotations


JUDGE_VERSION = "structure_packet_semantic_judge_v0_1"
JUDGE_TASK_KIND = "pilot_structure_packet_semantic_judgment"
JUDGE_STATES = ("PRESENT", "UNCERTAIN", "ABSENT")
JUDGE_CRITERIA = (
    "RIVAL_A_OBJECT_FIT",
    "RIVAL_B_OBJECT_FIT",
    "RIVALS_STRUCTURALLY_DISTINCT",
    "CONTRAST_NAMES_DECISIVE_VARIABLE",
    "QUESTION_RESOLVES_AMBIGUITY",
    "NO_INVENTED_FACT_OR_SOLUTION_DEPENDENCE",
)
RUBRIC = {
    "RIVAL_A_OBJECT_FIT": "RIVAL_A is a plausible interpretation of the underspecified requested object.",
    "RIVAL_B_OBJECT_FIT": "RIVAL_B is a second plausible interpretation of that same underspecification.",
    "RIVALS_STRUCTURALLY_DISTINCT": "The rivals differ in object, unit, boundary, direction, or operation.",
    "CONTRAST_NAMES_DECISIVE_VARIABLE": "CONTRAST identifies what changes between the rival structures.",
    "QUESTION_RESOLVES_AMBIGUITY": "The question would distinguish which rival object the requester intends.",
    "NO_INVENTED_FACT_OR_SOLUTION_DEPENDENCE": "The packet does not rely on invented facts or require its numeric solution.",
}


def semantic_judge_schema(batch_id, candidate_ids):
    criterion_properties = {
        criterion: {"type": "string", "enum": list(JUDGE_STATES)}
        for criterion in JUDGE_CRITERIA
    }
    return {
        "type": "object", "additionalProperties": False,
        "required": ["batch_id", "assessments", "evidence_refs"],
        "properties": {
            "batch_id": {"type": "string", "enum": [batch_id]},
            "assessments": {
                "type": "array", "minItems": len(candidate_ids), "maxItems": len(candidate_ids),
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["blind_candidate_id", "criteria", "confidence", "audit_note", "fatal_issue"],
                    "properties": {
                        "blind_candidate_id": {"type": "string", "enum": list(candidate_ids)},
                        "criteria": {
                            "type": "object", "additionalProperties": False,
                            "required": list(JUDGE_CRITERIA), "properties": criterion_properties,
                        },
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "audit_note": {"type": "string"},
                        "fatal_issue": {"type": "string"},
                    },
                },
            },
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def validate_semantic_judgment(payload, *, batch_id, candidate_ids, evidence_refs):
    if not isinstance(payload, dict) or set(payload) != {"batch_id", "assessments", "evidence_refs"}:
        raise ValueError("semantic_judgment_shape_invalid")
    if payload["batch_id"] != batch_id or payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("semantic_judgment_batch_or_evidence_binding_invalid")
    assessments = payload["assessments"]
    if not isinstance(assessments, list) or len(assessments) != len(candidate_ids):
        raise ValueError("semantic_judgment_assessment_count_invalid")
    observed = []
    required = {"blind_candidate_id", "criteria", "confidence", "audit_note", "fatal_issue"}
    for item in assessments:
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError("semantic_judgment_assessment_shape_invalid")
        observed.append(item["blind_candidate_id"])
        criteria = item["criteria"]
        confidence = item["confidence"]
        if (set(criteria) != set(JUDGE_CRITERIA)
                or any(value not in JUDGE_STATES for value in criteria.values())):
            raise ValueError("semantic_judgment_criteria_invalid")
        if (not isinstance(confidence, (int, float)) or isinstance(confidence, bool)
                or not 0 <= confidence <= 1):
            raise ValueError("semantic_judgment_confidence_invalid")
        if not isinstance(item["audit_note"], str) or not item["audit_note"].strip():
            raise ValueError("semantic_judgment_audit_note_required")
        if not isinstance(item["fatal_issue"], str):
            raise ValueError("semantic_judgment_fatal_issue_invalid")
    if len(observed) != len(set(observed)) or set(observed) != set(candidate_ids):
        raise ValueError("semantic_judgment_candidate_binding_invalid")
