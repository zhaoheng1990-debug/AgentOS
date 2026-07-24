"""Hash-bound contracts for critique and revision of a problem object."""

from __future__ import annotations

from .calibrated_score_receipt import validate_calibrated_score_receipt
from .problem_formulation_contracts import validate_problem_definition_receipt
from .provider_telemetry import hash_payload


PROBLEM_CRITIQUE_VERSION = "provider_backed_problem_critique_v0_25"
PROBLEM_REVISION_VERSION = "provider_backed_problem_revision_v0_25"
CRITIQUE_DIMENSIONS = (
    "MODE", "FAMILY", "TARGET", "CONSTRAINT", "WHOLE_OBJECT", "NO_MATERIAL_FLAW",
)
REVISION_SELECTIONS = ("ORIGINAL", "CRITIC_REVISION", "ABSTAIN")


def critique_schema(item_id, thread_id):
    return {
        "type": "object", "additionalProperties": False,
        "required": ["item_id", "thread_id", "critique_dimension", "evidence_refs",
                     "decision_receipt", "suggested_problem_receipt", "critique_receipt"],
        "properties": {
            "item_id": {"const": item_id}, "thread_id": {"const": thread_id},
            "critique_dimension": {"enum": list(CRITIQUE_DIMENSIONS)},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "decision_receipt": {"type": "object"},
            "suggested_problem_receipt": {"type": "object"},
            "critique_receipt": {"type": "object"},
        },
    }


def revision_schema(item_id, thread_id):
    return {
        "type": "object", "additionalProperties": False,
        "required": ["item_id", "thread_id", "selection", "evidence_refs",
                     "decision_receipt", "final_problem_receipt", "revision_receipt"],
        "properties": {
            "item_id": {"const": item_id}, "thread_id": {"const": thread_id},
            "selection": {"enum": list(REVISION_SELECTIONS)},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "decision_receipt": {"type": "object"},
            "final_problem_receipt": {"type": "object"},
            "revision_receipt": {"type": "object"},
        },
    }


def build_critique_receipt(*, task, thread_id, source_problem, suggested_problem,
                           critique_dimension, decision_receipt, provider_id, model_id):
    committed = {
        "receipt_version": PROBLEM_CRITIQUE_VERSION,
        "item_id": source_problem["item_id"], "thread_id": thread_id,
        "source_problem_hash": source_problem["receipt_hash"],
        "suggested_problem_hash": suggested_problem["receipt_hash"],
        "critique_dimension": critique_dimension,
        "decision_receipt_hash": decision_receipt["receipt_hash"],
        "provider_task_contract_hash": task.contract_hash(),
        "provider_id": provider_id, "model_id": model_id,
        "evidence_refs": list(task.allowed_evidence),
        "provider_backed": True, "hidden_truth_used": False,
    }
    return {**committed, "receipt_hash": hash_payload(committed)}


def build_revision_receipt(*, task, thread_id, source_problem, critique_receipt,
                           suggested_problem, selection, final_problem,
                           decision_receipt, provider_id, model_id):
    committed = {
        "receipt_version": PROBLEM_REVISION_VERSION,
        "item_id": source_problem["item_id"], "thread_id": thread_id,
        "source_problem_hash": source_problem["receipt_hash"],
        "critique_receipt_hash": critique_receipt["receipt_hash"],
        "suggested_problem_hash": suggested_problem["receipt_hash"],
        "selection": selection, "final_problem_hash": final_problem["receipt_hash"],
        "decision_receipt_hash": decision_receipt["receipt_hash"],
        "provider_task_contract_hash": task.contract_hash(),
        "provider_id": provider_id, "model_id": model_id,
        "evidence_refs": list(task.allowed_evidence),
        "provider_backed": True, "hidden_truth_used": False,
    }
    return {**committed, "receipt_hash": hash_payload(committed)}


def validate_critique_receipt(receipt, *, task=None, decision_receipt=None,
                              source_problem=None, suggested_problem=None):
    _validate(receipt, PROBLEM_CRITIQUE_VERSION)
    if (receipt["critique_dimension"] not in CRITIQUE_DIMENSIONS
            or receipt["provider_backed"] is not True
            or receipt["hidden_truth_used"] is not False):
        raise ValueError("problem_critique_binding_invalid")
    _validate_task_and_decision(receipt, task, decision_receipt)
    if source_problem and receipt["source_problem_hash"] != source_problem["receipt_hash"]:
        raise ValueError("problem_critique_source_binding_invalid")
    if suggested_problem and receipt["suggested_problem_hash"] != suggested_problem["receipt_hash"]:
        raise ValueError("problem_critique_suggestion_binding_invalid")


def validate_revision_receipt(receipt, *, task=None, decision_receipt=None,
                              source_problem=None, critique_receipt=None,
                              suggested_problem=None, final_problem=None):
    _validate(receipt, PROBLEM_REVISION_VERSION)
    if (receipt["selection"] not in REVISION_SELECTIONS
            or receipt["provider_backed"] is not True
            or receipt["hidden_truth_used"] is not False):
        raise ValueError("problem_revision_binding_invalid")
    _validate_task_and_decision(receipt, task, decision_receipt)
    bindings = (("source_problem_hash", source_problem),
                ("critique_receipt_hash", critique_receipt),
                ("suggested_problem_hash", suggested_problem),
                ("final_problem_hash", final_problem))
    if any(value and receipt[key] != value["receipt_hash"] for key, value in bindings):
        raise ValueError("problem_revision_lineage_binding_invalid")


def validate_dialogue_objects(source_problem, suggested_problem, final_problem):
    for problem in (source_problem, suggested_problem, final_problem):
        validate_problem_definition_receipt(problem)
    if len({item["item_id"] for item in (source_problem, suggested_problem, final_problem)}) != 1:
        raise ValueError("problem_dialogue_item_binding_invalid")


def _validate_task_and_decision(receipt, task, decision_receipt):
    if task and (receipt["item_id"] != task.inputs["benchmark_item_ids"][0]
                 or receipt["provider_task_contract_hash"] != task.contract_hash()):
        raise ValueError("problem_dialogue_task_binding_invalid")
    if decision_receipt:
        validate_calibrated_score_receipt(decision_receipt, task=task)
        if receipt["decision_receipt_hash"] != decision_receipt["receipt_hash"]:
            raise ValueError("problem_dialogue_decision_binding_invalid")


def _validate(receipt, version):
    if not isinstance(receipt, dict) or receipt.get("receipt_version") != version:
        raise ValueError("problem_dialogue_receipt_shape_invalid")
    committed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if receipt.get("receipt_hash") != hash_payload(committed):
        raise ValueError("problem_dialogue_receipt_hash_invalid")
