"""Provider-backed veto warrants with Runtime-owned execution authority."""

from __future__ import annotations


WARRANT_VERSION = "negative_evidence_veto_warrant_v0_5"
WARRANT_TASK_KIND = "negative_evidence_veto_warrant_audit"
PROVIDER_STATES = ("PASS", "VETO", "UNCERTAIN")
WARRANT_KINDS = (
    "NONE",
    "EXPLICIT_FIXATION",
    "RIVAL_INVALID",
    "RIVALS_EQUIVALENT",
    "QUESTION_INEFFECTIVE_ONLY",
    "UNCERTAIN",
)
RIVAL_RELATIONS = (
    "BOTH_VALID_DISTINCT",
    "RIVAL_A_INVALID",
    "RIVAL_B_INVALID",
    "EQUIVALENT",
    "UNCERTAIN",
)
QUESTION_EFFECTS = ("DISCRIMINATES", "DOES_NOT_DISCRIMINATE", "UNCERTAIN")
RUNTIME_WARRANT_STATES = (
    "EXECUTABLE_VETO",
    "NO_EXECUTABLE_VETO",
    "NON_EXECUTABLE_VETO",
    "UNCERTAIN",
)


def warrant_schema(batch_id, candidate_ids):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["batch_id", "assessments", "evidence_refs"],
        "properties": {
            "batch_id": {"type": "string", "enum": [batch_id]},
            "assessments": {
                "type": "array",
                "minItems": len(candidate_ids),
                "maxItems": len(candidate_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "blind_candidate_id",
                        "provider_state",
                        "warrant_kind",
                        "decisive_quote",
                        "rival_relation",
                        "question_effect",
                        "evidence_basis",
                        "counterfactual",
                        "confidence",
                    ],
                    "properties": {
                        "blind_candidate_id": {"type": "string", "enum": list(candidate_ids)},
                        "provider_state": {"type": "string", "enum": list(PROVIDER_STATES)},
                        "warrant_kind": {"type": "string", "enum": list(WARRANT_KINDS)},
                        "decisive_quote": {"type": "string"},
                        "rival_relation": {"type": "string", "enum": list(RIVAL_RELATIONS)},
                        "question_effect": {"type": "string", "enum": list(QUESTION_EFFECTS)},
                        "evidence_basis": {"type": "string"},
                        "counterfactual": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def validate_warrant(payload, *, batch_id, candidate_ids, evidence_refs):
    required = {"batch_id", "assessments", "evidence_refs"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("negative_warrant_shape_invalid")
    if payload["batch_id"] != batch_id or payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("negative_warrant_binding_invalid")
    assessments = payload["assessments"]
    if not isinstance(assessments, list) or len(assessments) != len(candidate_ids):
        raise ValueError("negative_warrant_count_invalid")
    keys = {
        "blind_candidate_id", "provider_state", "warrant_kind", "decisive_quote",
        "rival_relation", "question_effect", "evidence_basis", "counterfactual",
        "confidence",
    }
    observed = []
    for item in assessments:
        if not isinstance(item, dict) or set(item) != keys:
            raise ValueError("negative_warrant_item_shape_invalid")
        observed.append(item["blind_candidate_id"])
        if (
            item["provider_state"] not in PROVIDER_STATES
            or item["warrant_kind"] not in WARRANT_KINDS
            or item["rival_relation"] not in RIVAL_RELATIONS
            or item["question_effect"] not in QUESTION_EFFECTS
            or not item["evidence_basis"].strip()
            or not item["counterfactual"].strip()
        ):
            raise ValueError("negative_warrant_value_invalid")
        confidence = item["confidence"]
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            raise ValueError("negative_warrant_confidence_invalid")
        _validate_semantic_consistency(item)
    if len(observed) != len(set(observed)) or set(observed) != set(candidate_ids):
        raise ValueError("negative_warrant_candidate_binding_invalid")


def derive_runtime_warrant_state(assessment, *, public_prompt):
    """Apply only frozen execution rules; semantic warrant selection stays Provider-owned."""
    state = assessment["provider_state"]
    kind = assessment["warrant_kind"]
    if state == "UNCERTAIN":
        return "UNCERTAIN"
    if state == "PASS":
        return "NO_EXECUTABLE_VETO"
    if kind == "EXPLICIT_FIXATION":
        quote = assessment["decisive_quote"].strip()
        return "EXECUTABLE_VETO" if quote and quote in public_prompt else "NON_EXECUTABLE_VETO"
    if kind == "RIVAL_INVALID" and assessment["rival_relation"] in {"RIVAL_A_INVALID", "RIVAL_B_INVALID"}:
        return "EXECUTABLE_VETO"
    if kind == "RIVALS_EQUIVALENT" and assessment["rival_relation"] == "EQUIVALENT":
        return "EXECUTABLE_VETO"
    return "NON_EXECUTABLE_VETO"


def _validate_semantic_consistency(item):
    state = item["provider_state"]
    kind = item["warrant_kind"]
    quote = item["decisive_quote"].strip()
    if state == "PASS" and kind != "NONE":
        raise ValueError("negative_warrant_pass_kind_invalid")
    if state == "UNCERTAIN" and kind != "UNCERTAIN":
        raise ValueError("negative_warrant_uncertain_kind_invalid")
    if state == "VETO" and kind in {"NONE", "UNCERTAIN"}:
        raise ValueError("negative_warrant_veto_kind_invalid")
    if kind == "EXPLICIT_FIXATION" and not quote:
        raise ValueError("negative_warrant_quote_required")
    if kind != "EXPLICIT_FIXATION" and quote:
        raise ValueError("negative_warrant_quote_forbidden")
    if kind == "RIVAL_INVALID" and item["rival_relation"] not in {"RIVAL_A_INVALID", "RIVAL_B_INVALID"}:
        raise ValueError("negative_warrant_invalid_rival_mismatch")
    if kind == "RIVALS_EQUIVALENT" and item["rival_relation"] != "EQUIVALENT":
        raise ValueError("negative_warrant_equivalence_mismatch")
    if kind == "QUESTION_INEFFECTIVE_ONLY" and item["question_effect"] != "DOES_NOT_DISCRIMINATE":
        raise ValueError("negative_warrant_question_mismatch")
