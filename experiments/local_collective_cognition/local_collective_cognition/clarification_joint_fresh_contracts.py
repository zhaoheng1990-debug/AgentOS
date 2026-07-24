"""De-redundant per-axis coordination contract v0.13."""

from __future__ import annotations

from .clarification_joint_coordinator_contracts import AXES, BASES, COMPLETENESS, SELECTIONS, semantic_tuple_violations


FRESH_COORDINATOR_VERSION = "clarification_joint_fresh_v0_13"
FRESH_COORDINATOR_TASK_KIND = "clarification_joint_fresh_coordination"
ACTIONS = ("PRESERVE", "REOPEN")
BASIS_ACTIONS = ("PRESERVE", "REVISE")


def fresh_coordinator_schema(batch_id, conflict_ids):
    return {
        "type": "object", "additionalProperties": False,
        "required": ["batch_id", "decisions", "evidence_refs"],
        "properties": {
            "batch_id": {"type": "string", "enum": [batch_id]},
            "decisions": {"type": "array", "minItems": len(conflict_ids), "maxItems": len(conflict_ids), "items": {
                "type": "object", "additionalProperties": False,
                "required": ["conflict_id", "consensus_axis_actions", "local_basis_action", "final_selected_object", "final_selection_basis", "final_pragmatic_preference", "final_assessment_completeness", "evidence_quote", "decision_basis", "confidence"],
                "properties": {
                    "conflict_id": {"type": "string", "enum": list(conflict_ids)},
                    "consensus_axis_actions": {"type": "object", "additionalProperties": False, "required": list(AXES), "properties": {axis: {"type": "string", "enum": list(ACTIONS)} for axis in AXES}},
                    "local_basis_action": {"type": "string", "enum": list(BASIS_ACTIONS)},
                    "final_selected_object": {"type": "string", "enum": list(SELECTIONS)},
                    "final_selection_basis": {"type": "string", "enum": list(BASES)},
                    "final_pragmatic_preference": {"type": "string", "enum": list(SELECTIONS)},
                    "final_assessment_completeness": {"type": "string", "enum": list(COMPLETENESS)},
                    "evidence_quote": {"type": "string"}, "decision_basis": {"type": "string", "maxLength": 800},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            }},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def validate_fresh_coordinator_payload(payload, *, batch, evidence_refs):
    if not isinstance(payload, dict) or set(payload) != {"batch_id", "decisions", "evidence_refs"}:
        raise ValueError("joint_fresh_payload_shape_invalid")
    if payload["batch_id"] != batch["batch_id"] or payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("joint_fresh_payload_binding_invalid")
    conflicts = {item["conflict_id"]: item for item in batch["conflicts"]}
    items = payload["decisions"]
    if not isinstance(items, list) or len(items) != len(conflicts):
        raise ValueError("joint_fresh_decision_count_invalid")
    required = {"conflict_id", "consensus_axis_actions", "local_basis_action", "final_selected_object", "final_selection_basis", "final_pragmatic_preference", "final_assessment_completeness", "evidence_quote", "decision_basis", "confidence"}
    observed = []
    for item in items:
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError("joint_fresh_decision_shape_invalid")
        conflict_id = item["conflict_id"]
        observed.append(conflict_id)
        actions = item["consensus_axis_actions"]
        confidence = item["confidence"]
        if conflict_id not in conflicts or not isinstance(actions, dict) or set(actions) != set(AXES) or any(value not in ACTIONS for value in actions.values()) or item["local_basis_action"] not in BASIS_ACTIONS or item["final_selected_object"] not in SELECTIONS or item["final_selection_basis"] not in BASES or item["final_pragmatic_preference"] not in SELECTIONS or item["final_assessment_completeness"] not in COMPLETENESS:
            raise ValueError("joint_fresh_decision_value_invalid")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1 or not isinstance(item["decision_basis"], str) or not item["decision_basis"].strip():
            raise ValueError("joint_fresh_decision_metadata_invalid")
        quote = item["evidence_quote"].strip()
        if quote != "NONE" and (not quote or quote.casefold() not in conflicts[conflict_id]["public_prompt"].casefold()):
            raise ValueError("joint_fresh_evidence_quote_unbound")
    if len(observed) != len(set(observed)) or set(observed) != set(conflicts):
        raise ValueError("joint_fresh_conflict_binding_invalid")


def assess_fresh_decision(decision, *, conflict):
    final_axes = {"SELECTED_OBJECT": decision["final_selected_object"], "PRAGMATIC_PREFERENCE": decision["final_pragmatic_preference"], "AXIS_ASSESSMENT_COMPLETE": decision["final_assessment_completeness"]}
    changed = sorted(axis for axis in AXES if final_axes[axis] != conflict["locked_consensus_axes"][axis])
    declared = sorted(axis for axis, action in decision["consensus_axis_actions"].items() if action == "REOPEN")
    basis_changed = decision["final_selection_basis"] != conflict["local_basis_outcome"]["selection_basis"]
    action_valid = changed == declared and basis_changed == (decision["local_basis_action"] == "REVISE")
    violations = semantic_tuple_violations(selected=decision["final_selected_object"], basis=decision["final_selection_basis"], preference=decision["final_pragmatic_preference"], completeness=decision["final_assessment_completeness"])
    if not action_valid:
        state = "INVALID_ACTION_DECLARATION"
    elif violations:
        state = "INCOHERENT_TUPLE"
    elif changed:
        state = "REOPEN_REQUIRES_PANEL"
    else:
        state = "COHERENT_PRESERVATION_CANDIDATE"
    return {"mechanical_state": state, "action_declaration_valid": action_valid, "coherent": not violations, "coherence_violations": violations, "changed_consensus_axes": changed, "declared_reopen_axes": declared, "basis_changed": basis_changed, "governance_valid": action_valid and not violations}
