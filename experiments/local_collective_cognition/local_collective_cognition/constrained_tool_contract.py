"""Canonical binding between compact tool DSL calls and typed action results."""

from __future__ import annotations

from .candidate_revision_contracts import CHOICE_LABELS
from .typed_derivation_contracts import OPERATORS


def canonical_tool_call(result):
    required = {"item_id", "candidate_id", "action", "operator", "inputs",
                "proposed_candidate", "evidence_refs"}
    if set(result) != required or not result["item_id"] or not result["candidate_id"]:
        raise ValueError("constrained_tool_result_shape_invalid")
    action, operator, inputs = result["action"], result["operator"], result["inputs"]
    if (not isinstance(inputs, list) or any(not isinstance(item, str) for item in inputs)
            or not isinstance(result["evidence_refs"], list) or not result["evidence_refs"]):
        raise ValueError("constrained_tool_result_values_invalid")
    if action == "APPLY":
        if operator not in OPERATORS or result["proposed_candidate"] != "PENDING" or not inputs:
            raise ValueError("constrained_tool_apply_binding_invalid")
        return f"APPLY({operator},{','.join(inputs)})"
    if action == "FINALIZE":
        if (operator != "NONE" or len(inputs) != 1 or not inputs[0].startswith("STEP_")
                or result["proposed_candidate"] not in CHOICE_LABELS):
            raise ValueError("constrained_tool_finalize_binding_invalid")
        return f"FINALIZE({inputs[0]},{result['proposed_candidate']})"
    if action == "ABSTAIN" and operator == "NONE" and not inputs \
            and result["proposed_candidate"] == "ABSTAIN":
        return "ABSTAIN()"
    raise ValueError("constrained_tool_action_binding_invalid")
