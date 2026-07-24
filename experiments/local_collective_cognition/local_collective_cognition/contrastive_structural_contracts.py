"""Contracts for compact, candidate-only contrastive structure packets."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CONTRASTIVE_BATCH_RECEIPT_VERSION = "contrastive_structure_batch_receipt_v0_2"
PACKET_FIELDS = (
    "item_id", "contrastive_packet",
)
SCHEMA_COPY_METADATA_KEYS = frozenset({
    "additionalProperties", "properties", "required", "type",
})


def contrastive_batch_schema(item_ids):
    properties = {
        f"item_{index}_packet": {
            "type": "string", "minLength": 1, "maxLength": 1000,
        }
        for index in range(1, len(item_ids) + 1)
    }
    return {
        "type": "object", "additionalProperties": False,
        "required": list(properties), "properties": properties,
    }


def normalize_contrastive_batch_payload(provider_payload, *, item_ids, evidence_refs):
    failures = contrastive_batch_transport_failures(provider_payload, item_ids=item_ids)
    if failures:
        raise ValueError(failures[0])
    packets = []
    for index, item_id in enumerate(item_ids, 1):
        packet = _decode_packet(provider_payload[f"item_{index}_packet"], item_id)
        packets.append(packet)
    normalized = {"packets": packets, "evidence_refs": list(evidence_refs)}
    validate_contrastive_batch_payload(
        normalized, item_ids=item_ids, evidence_refs=evidence_refs,
    )
    return normalized


def contrastive_batch_transport_failures(provider_payload, *, item_ids):
    expected = {f"item_{index}_packet" for index in range(1, len(item_ids) + 1)}
    if not isinstance(provider_payload, dict):
        return ("contrastive_structure_provider_payload_shape_invalid",)
    observed = set(provider_payload)
    if expected - observed or observed - expected - SCHEMA_COPY_METADATA_KEYS:
        return ("contrastive_structure_provider_payload_shape_invalid",)
    for name in expected:
        value = provider_payload[name]
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 1000:
            return ("contrastive_structure_provider_packet_type_invalid",)
    return ()


def _decode_packet(value, item_id):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("contrastive_structure_provider_packet_type_invalid")
    return {"item_id": item_id, "contrastive_packet": value.strip()}


def validate_contrastive_batch_payload(payload, *, item_ids, evidence_refs):
    if not isinstance(payload, dict) or set(payload) != {"packets", "evidence_refs"}:
        raise ValueError("contrastive_structure_payload_shape_invalid")
    packets = payload["packets"]
    if (not isinstance(packets, list) or len(packets) != len(item_ids)
            or payload["evidence_refs"] != list(evidence_refs)):
        raise ValueError("contrastive_structure_payload_scope_invalid")
    observed = []
    for packet in packets:
        if not isinstance(packet, dict) or set(packet) != set(PACKET_FIELDS):
            raise ValueError("contrastive_structure_packet_shape_invalid")
        observed.append(packet["item_id"])
        texts = [packet[name].strip() if isinstance(packet[name], str) else ""
                 for name in PACKET_FIELDS[1:]]
        if not all(texts) or any(len(value) > 1000 for value in texts):
            raise ValueError("contrastive_structure_packet_content_invalid")
    if tuple(observed) != tuple(item_ids) or len(set(observed)) != len(observed):
        raise ValueError("contrastive_structure_packet_item_binding_invalid")


def build_contrastive_batch_receipt(*, task, payload, trigger_receipt_hash,
                                    provider_id, model_id, provider_payload=None):
    committed = {
        "receipt_version": CONTRASTIVE_BATCH_RECEIPT_VERSION,
        "item_ids": list(task.inputs["benchmark_item_ids"]),
        "provider_task_contract_hash": task.contract_hash(),
        "trigger_receipt_hash": trigger_receipt_hash,
        "packet_payload_hash": hash_payload(payload),
        "provider_output_hash": hash_payload(provider_payload or payload),
        "provider_id": provider_id, "model_id": model_id,
        "evidence_refs": list(task.allowed_evidence),
        "state": "EPHEMERAL_CANDIDATE", "provider_backed": True,
        "runtime_authority": True, "provider_authority": False,
        "hidden_truth_used": False, "retention_authorized": False,
    }
    return {**committed, "receipt_hash": hash_payload(committed)}


def validate_contrastive_batch_receipt(receipt, *, task=None, payload=None,
                                       trigger_receipt_hash=None, provider_payload=None):
    required = {
        "receipt_version", "item_ids", "provider_task_contract_hash",
        "trigger_receipt_hash", "packet_payload_hash", "provider_output_hash",
        "provider_id", "model_id",
        "evidence_refs", "state", "provider_backed", "runtime_authority",
        "provider_authority", "hidden_truth_used", "retention_authorized", "receipt_hash",
    }
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise ValueError("contrastive_structure_receipt_shape_invalid")
    committed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if (receipt["receipt_version"] != CONTRASTIVE_BATCH_RECEIPT_VERSION
            or receipt["receipt_hash"] != hash_payload(committed)
            or receipt["state"] != "EPHEMERAL_CANDIDATE"
            or receipt["provider_backed"] is not True
            or receipt["runtime_authority"] is not True
            or receipt["provider_authority"] is not False
            or receipt["hidden_truth_used"] is not False
            or receipt["retention_authorized"] is not False):
        raise ValueError("contrastive_structure_receipt_binding_invalid")
    if payload is not None and receipt["packet_payload_hash"] != hash_payload(payload):
        raise ValueError("contrastive_structure_payload_binding_invalid")
    if (provider_payload is not None
            and receipt["provider_output_hash"] != hash_payload(provider_payload)):
        raise ValueError("contrastive_structure_provider_output_binding_invalid")
    if trigger_receipt_hash and receipt["trigger_receipt_hash"] != trigger_receipt_hash:
        raise ValueError("contrastive_structure_trigger_binding_invalid")
    if task and (receipt["item_ids"] != task.inputs["benchmark_item_ids"]
                 or receipt["provider_task_contract_hash"] != task.contract_hash()
                 or receipt["evidence_refs"] != list(task.allowed_evidence)):
        raise ValueError("contrastive_structure_task_binding_invalid")
