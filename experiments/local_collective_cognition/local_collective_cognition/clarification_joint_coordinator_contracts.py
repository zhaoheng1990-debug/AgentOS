"""Joint cross-axis semantic coordinator contract v0.12."""

from __future__ import annotations


JOINT_COORDINATOR_VERSION = "clarification_joint_coordinator_v0_12"
JOINT_COORDINATOR_TASK_KIND = "clarification_joint_cross_axis_coordination"
SELECTIONS = ("CANDIDATE_A", "CANDIDATE_B", "NONE", "UNCERTAIN")
BASES = ("LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT", "PRAGMATIC_DEFAULT", "NO_PREFERENCE", "UNCERTAIN")
COMPLETENESS = ("COMPLETE", "INCOMPLETE", "UNCERTAIN")
AXES = ("SELECTED_OBJECT", "PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE")
DISPOSITIONS = ("PRESERVE_CONSENSUS_REPAIR", "REOPEN_CONSENSUS_AXIS", "DECLARE_ONTOLOGY_CONFLICT", "UNRESOLVED")


def joint_coordinator_schema(batch_id, conflict_ids):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["batch_id", "decisions", "evidence_refs"],
        "properties": {
            "batch_id": {"type": "string", "enum": [batch_id]},
            "decisions": {
                "type": "array", "minItems": len(conflict_ids), "maxItems": len(conflict_ids),
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["conflict_id", "disposition", "final_selected_object", "final_selection_basis", "final_pragmatic_preference", "final_assessment_completeness", "preserved_consensus_axes", "reopened_consensus_axes", "evidence_quote", "decision_basis", "confidence"],
                    "properties": {
                        "conflict_id": {"type": "string", "enum": list(conflict_ids)},
                        "disposition": {"type": "string", "enum": list(DISPOSITIONS)},
                        "final_selected_object": {"type": "string", "enum": list(SELECTIONS)},
                        "final_selection_basis": {"type": "string", "enum": list(BASES)},
                        "final_pragmatic_preference": {"type": "string", "enum": list(SELECTIONS)},
                        "final_assessment_completeness": {"type": "string", "enum": list(COMPLETENESS)},
                        "preserved_consensus_axes": {"type": "array", "items": {"type": "string", "enum": list(AXES)}},
                        "reopened_consensus_axes": {"type": "array", "items": {"type": "string", "enum": list(AXES)}},
                        "evidence_quote": {"type": "string"},
                        "decision_basis": {"type": "string", "maxLength": 800},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def validate_joint_coordinator_payload(payload, *, batch_id, public_conflicts, evidence_refs):
    if not isinstance(payload, dict) or set(payload) != {"batch_id", "decisions", "evidence_refs"}:
        raise ValueError("joint_coordinator_payload_shape_invalid")
    if payload["batch_id"] != batch_id or payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("joint_coordinator_payload_binding_invalid")
    conflicts = {item["conflict_id"]: item for item in public_conflicts}
    decisions = payload["decisions"]
    if not isinstance(decisions, list) or len(decisions) != len(conflicts):
        raise ValueError("joint_coordinator_decision_count_invalid")
    required = {"conflict_id", "disposition", "final_selected_object", "final_selection_basis", "final_pragmatic_preference", "final_assessment_completeness", "preserved_consensus_axes", "reopened_consensus_axes", "evidence_quote", "decision_basis", "confidence"}
    observed = []
    for item in decisions:
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError("joint_coordinator_decision_shape_invalid")
        conflict_id = item["conflict_id"]
        observed.append(conflict_id)
        confidence = item["confidence"]
        if conflict_id not in conflicts or item["disposition"] not in DISPOSITIONS or item["final_selected_object"] not in SELECTIONS or item["final_selection_basis"] not in BASES or item["final_pragmatic_preference"] not in SELECTIONS or item["final_assessment_completeness"] not in COMPLETENESS:
            raise ValueError("joint_coordinator_decision_value_invalid")
        preserved, reopened = item["preserved_consensus_axes"], item["reopened_consensus_axes"]
        if not isinstance(preserved, list) or not isinstance(reopened, list) or len(preserved) != len(set(preserved)) or len(reopened) != len(set(reopened)) or any(axis not in AXES for axis in preserved + reopened) or set(preserved) & set(reopened):
            raise ValueError("joint_coordinator_axis_declaration_invalid")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1 or not isinstance(item["decision_basis"], str) or not item["decision_basis"].strip():
            raise ValueError("joint_coordinator_decision_metadata_invalid")
        quote = item["evidence_quote"].strip()
        if quote != "NONE" and (not quote or quote.casefold() not in conflicts[conflict_id]["public_prompt"].casefold()):
            raise ValueError("joint_coordinator_evidence_quote_unbound")
    if len(observed) != len(set(observed)) or set(observed) != set(conflicts):
        raise ValueError("joint_coordinator_conflict_binding_invalid")


def assess_joint_decision(decision, *, locked_consensus_axes):
    final = {
        "SELECTED_OBJECT": decision["final_selected_object"],
        "PRAGMATIC_PREFERENCE": decision["final_pragmatic_preference"],
        "AXIS_ASSESSMENT_COMPLETE": decision["final_assessment_completeness"],
    }
    changed = sorted(axis for axis in AXES if final[axis] != locked_consensus_axes[axis])
    coherence = semantic_tuple_violations(
        selected=decision["final_selected_object"], basis=decision["final_selection_basis"],
        preference=decision["final_pragmatic_preference"], completeness=decision["final_assessment_completeness"],
    )
    disposition = decision["disposition"]
    if disposition == "PRESERVE_CONSENSUS_REPAIR":
        accepted = not changed and not coherence and set(decision["preserved_consensus_axes"]) == set(AXES) and not decision["reopened_consensus_axes"]
        state = "COHERENT_REPAIR_CANDIDATE" if accepted else "INVALID_PRESERVATION_PROPOSAL"
    elif disposition == "REOPEN_CONSENSUS_AXIS":
        declared = sorted(decision["reopened_consensus_axes"])
        accepted = bool(changed) and changed == declared and not coherence
        state = "REOPEN_REQUIRES_NEW_PANEL" if accepted else "INVALID_REOPEN_PROPOSAL"
    elif disposition == "DECLARE_ONTOLOGY_CONFLICT":
        accepted, state = False, "ONTOLOGY_CONFLICT_RETAINED"
    else:
        accepted, state = False, "UNRESOLVED_RETAINED"
    return {"mechanical_state": state, "coherent": not coherence, "coherence_violations": coherence, "changed_consensus_axes": changed, "proposal_accepted": accepted}


def semantic_tuple_violations(*, selected, basis, preference, completeness):
    violations = []
    if basis in ("LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT") and selected not in ("CANDIDATE_A", "CANDIDATE_B"):
        violations.append("HARD_BASIS_WITHOUT_SELECTED_OBJECT")
    if basis == "PRAGMATIC_DEFAULT" and (selected != "NONE" or preference not in ("CANDIDATE_A", "CANDIDATE_B")):
        violations.append("PRAGMATIC_BASIS_AXIS_MISMATCH")
    if basis == "NO_PREFERENCE" and (selected != "NONE" or preference != "NONE"):
        violations.append("NO_PREFERENCE_AXIS_MISMATCH")
    if completeness == "INCOMPLETE" and basis != "UNCERTAIN":
        violations.append("INCOMPLETE_ASSESSMENT_WITH_DECISIVE_BASIS")
    return violations
