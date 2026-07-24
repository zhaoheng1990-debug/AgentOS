"""Provider-backed global derivation-plan contracts and hash binding."""

from __future__ import annotations

from .iterative_derivation_contracts import iterative_action_schema, validate_iterative_action
from .provider_telemetry import hash_payload
from .typed_derivation_contracts import BINARY_OPERATORS, UNARY_OPERATORS


PLAN_INTENT_VERSION = "provider_backed_global_plan_intent_v0_23"
PLAN_INTENT_MODES = ("NUMERIC_DERIVATION", "STRING_TRANSFORMATION", "ABSTAIN")


def plan_action_schema(item_id, candidate_id, available_symbols):
    schema = iterative_action_schema(item_id, candidate_id, available_symbols)
    schema["required"].extend(("intent_mode", "decision_receipt"))
    schema["properties"].update({
        "intent_mode": {"type": "string", "enum": list(PLAN_INTENT_MODES)},
        "decision_receipt": {"type": "object"},
    })
    return schema


def validate_plan_action(result, *, item_id, candidate_id, evidence_refs, available_symbols):
    if result.get("intent_mode") not in PLAN_INTENT_MODES or not isinstance(
        result.get("decision_receipt"), dict
    ):
        raise ValueError("plan_intent_action_extension_invalid")
    action = {key: value for key, value in result.items()
              if key not in {"intent_mode", "decision_receipt"}}
    validate_iterative_action(
        action, item_id=item_id, candidate_id=candidate_id,
        evidence_refs=evidence_refs, available_symbols=available_symbols,
    )
    return action


def build_plan_intent_receipt(*, item_id, candidate_id, original_candidate, intent_mode,
                              planned_actions, terminal_action, score_receipts, tasks,
                              preview_receipts, evidence_refs, initial_state,
                              provider_id, model_id, input_tokens):
    committed = {
        "receipt_version": PLAN_INTENT_VERSION, "item_id": item_id,
        "candidate_id": candidate_id, "original_candidate": original_candidate,
        "intent_mode": intent_mode, "planned_actions": list(planned_actions),
        "terminal_action": dict(terminal_action),
        "decision_receipt_hashes": [item["receipt_hash"] for item in score_receipts],
        "provider_task_contract_hashes": [item.contract_hash() for item in tasks],
        "provider_id": provider_id, "model_id": model_id,
        "evidence_refs": list(evidence_refs), "initial_state_hash": hash_payload(initial_state),
        "preview_trace_hash": hash_payload([item.as_dict() for item in preview_receipts]),
        "turns": len(score_receipts),
        "inference_passes": sum(item["inference_passes"] for item in score_receipts),
        "input_tokens": int(input_tokens), "provider_backed": True,
        "kernel_assembled": True, "hidden_truth_used": False,
    }
    return {**committed, "receipt_hash": hash_payload(committed)}


def validate_plan_intent_receipt(receipt):
    required = {"receipt_version", "item_id", "candidate_id", "original_candidate",
                "intent_mode", "planned_actions", "terminal_action",
                "decision_receipt_hashes", "provider_task_contract_hashes", "provider_id",
                "model_id", "evidence_refs", "initial_state_hash", "preview_trace_hash",
                "turns", "inference_passes", "input_tokens", "provider_backed",
                "kernel_assembled", "hidden_truth_used", "receipt_hash"}
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise ValueError("plan_intent_receipt_shape_invalid")
    committed = {key: receipt[key] for key in receipt if key != "receipt_hash"}
    if (receipt["receipt_version"] != PLAN_INTENT_VERSION
            or receipt["receipt_hash"] != hash_payload(committed)
            or receipt["intent_mode"] not in PLAN_INTENT_MODES
            or receipt["turns"] != len(receipt["decision_receipt_hashes"])
            or receipt["turns"] != len(receipt["provider_task_contract_hashes"])
            or min(receipt["turns"], receipt["inference_passes"], receipt["input_tokens"]) < 0
            or not receipt["provider_id"] or not receipt["model_id"]
            or receipt["provider_backed"] is not True or receipt["kernel_assembled"] is not True
            or receipt["hidden_truth_used"] is not False):
        raise ValueError("plan_intent_receipt_binding_invalid")
    if any(item.get("action") != "APPLY" for item in receipt["planned_actions"]):
        raise ValueError("plan_intent_planned_action_invalid")
    terminal = receipt["terminal_action"]
    if terminal.get("action") not in {"FINALIZE", "ABSTAIN"}:
        raise ValueError("plan_intent_terminal_action_invalid")
    operators = [item["operator"] for item in receipt["planned_actions"]]
    allowed = BINARY_OPERATORS if receipt["intent_mode"] == "NUMERIC_DERIVATION" else UNARY_OPERATORS
    if receipt["intent_mode"] != "ABSTAIN" and any(item not in allowed for item in operators):
        raise ValueError("plan_intent_mode_operator_mismatch")
    if receipt["intent_mode"] == "ABSTAIN" and (operators or terminal["action"] != "ABSTAIN"):
        raise ValueError("plan_intent_abstain_mode_invalid")
