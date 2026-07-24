"""Frozen materiality and receipt-quality contract for hard-null coordination."""

from __future__ import annotations

from .unstated_ambiguity_holdout import NULL, POSITIVE


TASK_KIND = "pilot_hard_null_ambiguity_coordination"
STATES = (POSITIVE, NULL, "UNCERTAIN")
POSITIONS = ("POSITION_A", "POSITION_B")
QUALITY_STATES = (
    "USABLE_MATERIAL_SUPPORT",
    "USABLE_NULL_SUPPORT",
    "SEMANTICALLY_COLLAPSED",
    "UNGROUNDED_OR_INVENTED",
    "INCOMPLETE",
    "UNRESOLVED",
)
MATERIALITY_BASES = (
    "MATERIAL_RIVALRY",
    "EXPLICITLY_DISAMBIGUATED",
    "ONLY_ONE_GROUNDED_INTERPRETATION",
    "UNRESOLVED",
)


def hard_null_coordinator_schema(batch_id, item_ids, evidence_refs):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["batch_id", "decisions", "evidence_refs"],
        "properties": {
            "batch_id": {"type": "string", "enum": [batch_id]},
            "decisions": {
                "type": "array",
                "minItems": len(item_ids),
                "maxItems": len(item_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "coordination_item_id",
                        "receipt_assessments",
                        "materiality_basis",
                        "prompt_disambiguates",
                        "final_state",
                        "confidence",
                        "decision_note",
                    ],
                    "properties": {
                        "coordination_item_id": {
                            "type": "string", "enum": list(item_ids),
                        },
                        "receipt_assessments": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": [
                                    "position", "quality_state", "task_grounded",
                                    "rivals_distinct", "output_sensitive",
                                ],
                                "properties": {
                                    "position": {"type": "string", "enum": list(POSITIONS)},
                                    "quality_state": {
                                        "type": "string", "enum": list(QUALITY_STATES),
                                    },
                                    "task_grounded": {"type": "boolean"},
                                    "rivals_distinct": {"type": "boolean"},
                                    "output_sensitive": {"type": "boolean"},
                                },
                            },
                        },
                        "materiality_basis": {
                            "type": "string", "enum": list(MATERIALITY_BASES),
                        },
                        "prompt_disambiguates": {"type": "boolean"},
                        "final_state": {"type": "string", "enum": list(STATES)},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "decision_note": {"type": "string", "maxLength": 500},
                    },
                },
            },
            "evidence_refs": {
                "type": "array",
                "minItems": len(evidence_refs),
                "maxItems": len(evidence_refs),
                "items": {"type": "string", "enum": list(evidence_refs)},
            },
        },
    }


def validate_hard_null_coordinator_payload(payload, *, batch_id, item_ids, evidence_refs):
    if not isinstance(payload, dict) or set(payload) != {
        "batch_id", "decisions", "evidence_refs",
    }:
        raise ValueError("hard_null_coordinator_payload_shape_invalid")
    if payload["batch_id"] != batch_id or payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("hard_null_coordinator_payload_binding_invalid")
    decisions = payload["decisions"]
    if not isinstance(decisions, list) or len(decisions) != len(item_ids):
        raise ValueError("hard_null_coordinator_decision_count_invalid")
    observed = []
    required = {
        "coordination_item_id", "receipt_assessments", "materiality_basis",
        "prompt_disambiguates", "final_state", "confidence", "decision_note",
    }
    for decision in decisions:
        if not isinstance(decision, dict) or set(decision) != required:
            raise ValueError("hard_null_coordinator_decision_shape_invalid")
        observed.append(decision["coordination_item_id"])
        _validate_decision(decision)
    if len(observed) != len(set(observed)) or set(observed) != set(item_ids):
        raise ValueError("hard_null_coordinator_item_binding_invalid")


def _validate_decision(decision):
    confidence = decision["confidence"]
    if (
        decision["final_state"] not in STATES
        or decision["materiality_basis"] not in MATERIALITY_BASES
        or not isinstance(decision["prompt_disambiguates"], bool)
        or not isinstance(confidence, (int, float))
        or isinstance(confidence, bool)
        or not 0 <= confidence <= 1
        or not isinstance(decision["decision_note"], str)
        or not decision["decision_note"].strip()
    ):
        raise ValueError("hard_null_coordinator_decision_value_invalid")
    assessments = decision["receipt_assessments"]
    if not isinstance(assessments, list) or len(assessments) != 2:
        raise ValueError("hard_null_receipt_assessment_count_invalid")
    positions = []
    for assessment in assessments:
        _validate_receipt_assessment(assessment)
        positions.append(assessment["position"])
    if set(positions) != set(POSITIONS) or len(set(positions)) != 2:
        raise ValueError("hard_null_receipt_position_binding_invalid")

    material_support = any(
        item["quality_state"] == "USABLE_MATERIAL_SUPPORT" for item in assessments
    )
    state = decision["final_state"]
    basis = decision["materiality_basis"]
    disambiguates = decision["prompt_disambiguates"]
    if state == POSITIVE and not (
        material_support and basis == "MATERIAL_RIVALRY" and not disambiguates
    ):
        raise ValueError("hard_null_positive_requires_material_support")
    if state == NULL and not (
        not material_support
        and basis in {"EXPLICITLY_DISAMBIGUATED", "ONLY_ONE_GROUNDED_INTERPRETATION"}
    ):
        raise ValueError("hard_null_null_requires_nonmaterial_basis")
    if basis == "EXPLICITLY_DISAMBIGUATED" and not disambiguates:
        raise ValueError("hard_null_disambiguation_flag_required")
    if state == "UNCERTAIN" and basis != "UNRESOLVED":
        raise ValueError("hard_null_uncertain_requires_unresolved_basis")


def _validate_receipt_assessment(assessment):
    required = {
        "position", "quality_state", "task_grounded", "rivals_distinct",
        "output_sensitive",
    }
    if not isinstance(assessment, dict) or set(assessment) != required:
        raise ValueError("hard_null_receipt_assessment_shape_invalid")
    quality = assessment["quality_state"]
    flags = (
        assessment["task_grounded"], assessment["rivals_distinct"],
        assessment["output_sensitive"],
    )
    if (
        assessment["position"] not in POSITIONS
        or quality not in QUALITY_STATES
        or any(not isinstance(flag, bool) for flag in flags)
    ):
        raise ValueError("hard_null_receipt_assessment_value_invalid")
    if quality == "USABLE_MATERIAL_SUPPORT" and not all(flags):
        raise ValueError("hard_null_material_receipt_quality_inconsistent")
    if quality == "USABLE_NULL_SUPPORT" and not (
        assessment["task_grounded"]
        and not assessment["rivals_distinct"]
        and not assessment["output_sensitive"]
    ):
        raise ValueError("hard_null_null_receipt_quality_inconsistent")
    if quality == "SEMANTICALLY_COLLAPSED" and assessment["rivals_distinct"]:
        raise ValueError("hard_null_collapsed_receipt_quality_inconsistent")
    if quality == "UNGROUNDED_OR_INVENTED" and assessment["task_grounded"]:
        raise ValueError("hard_null_ungrounded_receipt_quality_inconsistent")
