"""Kernel-owned admission gate for Provider-backed packet quality."""

from __future__ import annotations

from .contrastive_quality_contracts import QUALITY_CRITERIA, validate_quality_receipt
from .contrastive_structural_contracts import validate_contrastive_batch_receipt
from .contrastive_trigger_policy import validate_contrastive_trigger_receipt
from .provider_telemetry import hash_payload


QUALITY_GATE_VERSION = "contrastive_packet_quality_kernel_gate_v0_3"


class ContrastivePacketQualityGate:
    def evaluate(self, *, trigger_receipt, batch_receipt, batch_payload, packet,
                 quality_receipt, public_prompt, proposer_model_id):
        validate_contrastive_trigger_receipt(trigger_receipt)
        validate_contrastive_batch_receipt(
            batch_receipt, payload=batch_payload,
            trigger_receipt_hash=trigger_receipt["receipt_hash"],
        )
        validate_quality_receipt(
            quality_receipt, packet=packet,
            batch_receipt_hash=batch_receipt["receipt_hash"],
        )
        reasons = []
        selected = trigger_receipt["selected_item_ids"]
        if selected != [packet["item_id"]] or batch_receipt["item_ids"] != selected:
            reasons.append("QUALITY_SINGLE_ITEM_LINEAGE_INVALID")
        if packet["contrastive_packet"].strip().casefold() == public_prompt.strip().casefold():
            reasons.append("QUALITY_EXACT_PUBLIC_PROMPT_RESTATEMENT")
        for criterion in QUALITY_CRITERIA:
            if quality_receipt["criteria"][criterion] != "PRESENT":
                reasons.append("QUALITY_PROVIDER_" + criterion + "_NOT_PRESENT")
        if quality_receipt["model_id"] in {
            proposer_model_id, batch_receipt["model_id"],
        }:
            reasons.append("QUALITY_JUDGE_ROLE_NOT_INDEPENDENT")
        committed = {
            "gate_version": QUALITY_GATE_VERSION, "item_id": packet["item_id"],
            "status": "BLOCK" if reasons else "ALLOW", "reasons": reasons,
            "trigger_receipt_hash": trigger_receipt["receipt_hash"],
            "batch_receipt_hash": batch_receipt["receipt_hash"],
            "quality_receipt_hash": quality_receipt["receipt_hash"],
            "packet_hash": hash_payload(packet),
            "mechanical_restatement_check": True,
            "provider_semantic_criteria_required": list(QUALITY_CRITERIA),
            "kernel_owned": True, "provider_authority": False,
            "hidden_truth_used": False,
        }
        return {**committed, "receipt_hash": hash_payload(committed)}


def validate_quality_gate_receipt(receipt):
    committed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if (receipt.get("gate_version") != QUALITY_GATE_VERSION
            or receipt.get("receipt_hash") != hash_payload(committed)
            or receipt.get("status") not in {"ALLOW", "BLOCK"}
            or receipt.get("kernel_owned") is not True
            or receipt.get("provider_authority") is not False
            or receipt.get("hidden_truth_used") is not False):
        raise ValueError("contrastive_quality_gate_receipt_invalid")
