"""Provider-backed problem-definition and coordination contracts."""

from __future__ import annotations

from .calibrated_score_receipt import validate_calibrated_score_receipt
from .plan_intent_contracts import PLAN_INTENT_MODES
from .provider_telemetry import hash_payload


PROBLEM_DEFINITION_VERSION = "provider_backed_problem_definition_v0_24"
PROBLEM_COORDINATION_VERSION = "provider_backed_problem_coordination_v0_24"
NUMERIC_FAMILIES = (
    "ARITHMETIC_COMPOSITION", "RATE_SCALING", "PERCENTAGE", "SET_COMPLEMENT",
    "WITHOUT_REPLACEMENT", "BAYES_POSTERIOR", "MODULAR_REMAINDER",
    "RATIO_ALLOCATION", "ARITHMETIC_MEAN", "ITERATIVE_UPDATE", "UNIT_DISTANCE",
)
STRING_FAMILIES = ("STRING_COMPOSITION",)
TARGET_KINDS = (
    "FINAL_SCALAR", "SCALED_QUANTITY", "COMPLEMENT_COUNT", "PROBABILITY",
    "POSTERIOR_PROBABILITY", "REMAINDER", "ALLOCATED_SHARE", "MEAN",
    "FINAL_STATE", "TRANSFORMED_STRING", "DISTANCE",
)
CRITICAL_CONSTRAINTS = (
    "NONE", "CONSTANT_RATE", "PERCENT_NORMALIZATION", "INCLUSION_EXCLUSION",
    "WITHOUT_REPLACEMENT", "COMPLEMENT_EVENT", "BASE_RATE_AND_FALSE_POSITIVE",
    "DIVISION_REMAINDER", "RATIO_NORMALIZATION", "CARDINALITY_NORMALIZATION",
    "ORDER_SENSITIVE", "UNIT_COMPOSITION",
)


def problem_definition_schema(item_id, problem_candidate_id):
    return {"type": "object", "additionalProperties": False,
            "required": ["item_id", "problem_candidate_id", "intent_mode", "problem_family",
                         "target_kind", "critical_constraint", "evidence_refs",
                         "decision_receipt", "problem_receipt"],
            "properties": {
                "item_id": {"const": item_id},
                "problem_candidate_id": {"const": problem_candidate_id},
                "intent_mode": {"type": "string", "enum": list(PLAN_INTENT_MODES)},
                "problem_family": {"type": "string"}, "target_kind": {"type": "string"},
                "critical_constraint": {"type": "string"},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
                "decision_receipt": {"type": "object"}, "problem_receipt": {"type": "object"},
            }}


def coordination_schema(item_id):
    return {"type": "object", "additionalProperties": False,
            "required": ["item_id", "selected_problem_candidate", "confidence",
                         "evidence_refs", "decision_receipt", "coordination_receipt"],
            "properties": {
                "item_id": {"const": item_id},
                "selected_problem_candidate": {
                    "type": "string", "enum": ["PROBLEM_1", "PROBLEM_2", "ABSTAIN"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
                "decision_receipt": {"type": "object"},
                "coordination_receipt": {"type": "object"},
            }}


def build_problem_definition_receipt(*, task, problem_candidate_id, intent_mode,
                                     problem_family, target_kind, critical_constraint,
                                     decision_receipt, provider_id, model_id):
    committed = {
        "receipt_version": PROBLEM_DEFINITION_VERSION,
        "item_id": task.inputs["benchmark_item_ids"][0],
        "problem_candidate_id": problem_candidate_id, "intent_mode": intent_mode,
        "problem_family": problem_family, "target_kind": target_kind,
        "critical_constraint": critical_constraint,
        "decision_receipt_hash": decision_receipt["receipt_hash"],
        "provider_task_contract_hash": task.contract_hash(),
        "provider_id": provider_id, "model_id": model_id,
        "evidence_refs": list(task.allowed_evidence),
        "provider_backed": True, "hidden_truth_used": False,
    }
    return {**committed, "receipt_hash": hash_payload(committed)}


def build_coordination_receipt(*, task, candidate_receipts, selected_candidate, confidence,
                               decision_receipt, provider_id, model_id):
    committed = {
        "receipt_version": PROBLEM_COORDINATION_VERSION,
        "item_id": task.inputs["benchmark_item_ids"][0],
        "candidate_receipt_hashes": [item["receipt_hash"] for item in candidate_receipts],
        "selected_problem_candidate": selected_candidate, "confidence": float(confidence),
        "decision_receipt_hash": decision_receipt["receipt_hash"],
        "provider_task_contract_hash": task.contract_hash(),
        "provider_id": provider_id, "model_id": model_id,
        "evidence_refs": list(task.allowed_evidence),
        "provider_backed": True, "hidden_truth_used": False,
    }
    return {**committed, "receipt_hash": hash_payload(committed)}


def validate_problem_definition_receipt(receipt, *, task=None, decision_receipt=None):
    _validate_hash_bound(receipt, PROBLEM_DEFINITION_VERSION)
    if (receipt["intent_mode"] not in PLAN_INTENT_MODES
            or receipt["problem_family"] not in (*NUMERIC_FAMILIES, *STRING_FAMILIES, "ABSTAIN")
            or receipt["target_kind"] not in (*TARGET_KINDS, "ABSTAIN")
            or receipt["critical_constraint"] not in (*CRITICAL_CONSTRAINTS, "ABSTAIN")
            or receipt["provider_backed"] is not True or receipt["hidden_truth_used"] is not False):
        raise ValueError("problem_definition_binding_invalid")
    if task and (receipt["item_id"] != task.inputs["benchmark_item_ids"][0]
                 or receipt["provider_task_contract_hash"] != task.contract_hash()):
        raise ValueError("problem_definition_task_binding_invalid")
    if decision_receipt:
        validate_calibrated_score_receipt(decision_receipt, task=task)
        if receipt["decision_receipt_hash"] != decision_receipt["receipt_hash"]:
            raise ValueError("problem_definition_decision_binding_invalid")


def validate_coordination_receipt(receipt, *, task=None, decision_receipt=None,
                                  candidate_receipts=None):
    _validate_hash_bound(receipt, PROBLEM_COORDINATION_VERSION)
    if (receipt["selected_problem_candidate"] not in {"PROBLEM_1", "PROBLEM_2", "ABSTAIN"}
            or not 0 <= receipt["confidence"] <= 1
            or receipt["provider_backed"] is not True or receipt["hidden_truth_used"] is not False):
        raise ValueError("problem_coordination_binding_invalid")
    if task and (receipt["item_id"] != task.inputs["benchmark_item_ids"][0]
                 or receipt["provider_task_contract_hash"] != task.contract_hash()):
        raise ValueError("problem_coordination_task_binding_invalid")
    if decision_receipt:
        validate_calibrated_score_receipt(decision_receipt, task=task)
        if receipt["decision_receipt_hash"] != decision_receipt["receipt_hash"]:
            raise ValueError("problem_coordination_decision_binding_invalid")
    if candidate_receipts and receipt["candidate_receipt_hashes"] != [
        item["receipt_hash"] for item in candidate_receipts
    ]:
        raise ValueError("problem_coordination_candidate_binding_invalid")


def semantic_problem_fields(receipt):
    return tuple(receipt[key] for key in (
        "intent_mode", "problem_family", "target_kind", "critical_constraint",
    ))


def _validate_hash_bound(receipt, version):
    if not isinstance(receipt, dict) or receipt.get("receipt_version") != version:
        raise ValueError("problem_receipt_shape_invalid")
    committed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if receipt.get("receipt_hash") != hash_payload(committed):
        raise ValueError("problem_receipt_hash_invalid")
