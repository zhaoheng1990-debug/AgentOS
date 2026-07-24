"""Candidate-only receipts for Provider-synthesized structural priors."""

from __future__ import annotations

from .provider_telemetry import hash_payload


STRUCTURAL_PRIOR_TASK_KIND = "pilot_object_structure_expansion"
STRUCTURAL_PRIOR_RECEIPT_VERSION = "ephemeral_structural_prior_receipt_v0_1"


def structural_prior_schema(item_id):
    return {
        "type": "object", "additionalProperties": False,
        "required": ["item_id", "structure_summary", "entities", "relations",
                     "invariants", "boundary_conditions", "discriminating_question",
                     "evidence_refs"],
        "properties": {
            "item_id": {"type": "string", "enum": [item_id]},
            "structure_summary": {"type": "string", "minLength": 1},
            "entities": {"type": "array", "minItems": 1,
                         "items": {"type": "string"}},
            "relations": {"type": "array", "minItems": 1,
                          "items": {"type": "string"}},
            "invariants": {"type": "array", "minItems": 1,
                           "items": {"type": "string"}},
            "boundary_conditions": {"type": "array", "minItems": 1,
                                    "items": {"type": "string"}},
            "discriminating_question": {"type": "string", "minLength": 1},
            "evidence_refs": {"type": "array", "minItems": 1,
                              "items": {"type": "string"}},
        },
    }


def build_structural_prior_receipt(*, task, payload, provider_id, model_id):
    committed = {
        "receipt_version": STRUCTURAL_PRIOR_RECEIPT_VERSION,
        "item_id": task.inputs["benchmark_item_ids"][0],
        "provider_task_contract_hash": task.contract_hash(),
        "structural_payload_hash": hash_payload(payload),
        "provider_id": provider_id, "model_id": model_id,
        "evidence_refs": list(task.allowed_evidence),
        "state": "EPHEMERAL_CANDIDATE", "provider_backed": True,
        "runtime_authority": True, "provider_authority": False,
        "hidden_truth_used": False, "retention_authorized": False,
    }
    return {**committed, "receipt_hash": hash_payload(committed)}


def validate_structural_prior_receipt(receipt, *, payload=None, task=None):
    required = {
        "receipt_version", "item_id", "provider_task_contract_hash",
        "structural_payload_hash", "provider_id", "model_id", "evidence_refs",
        "state", "provider_backed", "runtime_authority", "provider_authority",
        "hidden_truth_used", "retention_authorized", "receipt_hash",
    }
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise ValueError("structural_prior_receipt_shape_invalid")
    committed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if (receipt["receipt_version"] != STRUCTURAL_PRIOR_RECEIPT_VERSION
            or receipt["receipt_hash"] != hash_payload(committed)
            or receipt["state"] != "EPHEMERAL_CANDIDATE"
            or receipt["provider_backed"] is not True
            or receipt["runtime_authority"] is not True
            or receipt["provider_authority"] is not False
            or receipt["hidden_truth_used"] is not False
            or receipt["retention_authorized"] is not False):
        raise ValueError("structural_prior_receipt_binding_invalid")
    if payload is not None and receipt["structural_payload_hash"] != hash_payload(payload):
        raise ValueError("structural_prior_payload_binding_invalid")
    if task and (receipt["item_id"] != task.inputs["benchmark_item_ids"][0]
                 or receipt["provider_task_contract_hash"] != task.contract_hash()
                 or receipt["evidence_refs"] != list(task.allowed_evidence)):
        raise ValueError("structural_prior_task_binding_invalid")
