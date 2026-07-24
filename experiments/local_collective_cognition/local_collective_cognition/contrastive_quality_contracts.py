"""Provider-backed semantic quality receipts for contrastive structure packets."""

from __future__ import annotations

from .calibrated_score_receipt import validate_calibrated_score_receipt
from .provider_telemetry import hash_payload


QUALITY_TASK_KIND = "pilot_structure_packet_quality"
QUALITY_RECEIPT_VERSION = "contrastive_packet_quality_receipt_v0_3"
QUALITY_CRITERIA = (
    "RIVAL_STRUCTURES", "DECISIVE_CONTRAST",
    "DISCRIMINATING_QUESTION", "NON_RESTATEMENT",
)
QUALITY_VALUES = ("PRESENT", "ABSENT", "UNCERTAIN")


def quality_schema(item_id):
    return {
        "type": "object", "additionalProperties": False,
        "required": ["item_id", "criteria", "evidence_refs",
                     "decision_receipt", "quality_receipt"],
        "properties": {
            "item_id": {"type": "string", "enum": [item_id]},
            "criteria": {"type": "object"},
            "evidence_refs": {"type": "array", "minItems": 1,
                              "items": {"type": "string"}},
            "decision_receipt": {"type": "object"},
            "quality_receipt": {"type": "object"},
        },
    }


def build_quality_receipt(*, task, packet, batch_receipt_hash, criteria,
                          decision_receipt, provider_id, model_id):
    committed = {
        "receipt_version": QUALITY_RECEIPT_VERSION,
        "item_id": task.inputs["benchmark_item_ids"][0],
        "packet_hash": hash_payload(packet),
        "batch_receipt_hash": batch_receipt_hash,
        "criteria": dict(criteria),
        "decision_receipt_hash": decision_receipt["receipt_hash"],
        "provider_task_contract_hash": task.contract_hash(),
        "provider_id": provider_id, "model_id": model_id,
        "evidence_refs": list(task.allowed_evidence),
        "state": "CANDIDATE", "provider_backed": True,
        "runtime_authority": True, "provider_authority": False,
        "hidden_truth_used": False,
    }
    return {**committed, "receipt_hash": hash_payload(committed)}


def validate_quality_receipt(receipt, *, task=None, packet=None,
                             decision_receipt=None, batch_receipt_hash=None):
    required = {
        "receipt_version", "item_id", "packet_hash", "batch_receipt_hash",
        "criteria", "decision_receipt_hash", "provider_task_contract_hash",
        "provider_id", "model_id", "evidence_refs", "state", "provider_backed",
        "runtime_authority", "provider_authority", "hidden_truth_used", "receipt_hash",
    }
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise ValueError("contrastive_quality_receipt_shape_invalid")
    committed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    criteria = receipt["criteria"]
    if (receipt["receipt_version"] != QUALITY_RECEIPT_VERSION
            or receipt["receipt_hash"] != hash_payload(committed)
            or set(criteria) != set(QUALITY_CRITERIA)
            or any(value not in QUALITY_VALUES for value in criteria.values())
            or receipt["state"] != "CANDIDATE"
            or receipt["provider_backed"] is not True
            or receipt["runtime_authority"] is not True
            or receipt["provider_authority"] is not False
            or receipt["hidden_truth_used"] is not False):
        raise ValueError("contrastive_quality_receipt_binding_invalid")
    if packet is not None and receipt["packet_hash"] != hash_payload(packet):
        raise ValueError("contrastive_quality_packet_binding_invalid")
    if batch_receipt_hash and receipt["batch_receipt_hash"] != batch_receipt_hash:
        raise ValueError("contrastive_quality_batch_binding_invalid")
    if decision_receipt:
        validate_calibrated_score_receipt(decision_receipt, task=task)
        if receipt["decision_receipt_hash"] != decision_receipt["receipt_hash"]:
            raise ValueError("contrastive_quality_decision_binding_invalid")
    if task and (receipt["item_id"] != task.inputs["benchmark_item_ids"][0]
                 or receipt["provider_task_contract_hash"] != task.contract_hash()
                 or receipt["evidence_refs"] != list(task.allowed_evidence)):
        raise ValueError("contrastive_quality_task_binding_invalid")
