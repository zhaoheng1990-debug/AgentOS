"""Hash-bound receipts for Provider-backed bounded semantic decisions."""

from __future__ import annotations

import math
import re

from .provider_telemetry import hash_payload


SCORE_RECEIPT_VERSION = "hierarchical_enum_score_receipt_v0_22"


def build_score_receipt(*, task, channel_hash, decisions, selected_value):
    committed = {
        "receipt_version": SCORE_RECEIPT_VERSION, "task_id": task.task_id,
        "task_kind": task.task_kind, "task_contract_hash": task.contract_hash(),
        "provider_id": "", "model_id": "", "channel_hash": channel_hash,
        "decisions": list(decisions), "selected_value": selected_value,
        "inference_passes": len(decisions),
        "menu_option_total": sum(len(item["scores"]) for item in decisions),
        "provider_backed": True, "adapter_owned": True, "hidden_truth_used": False,
    }
    return {**committed, "receipt_hash": hash_payload(committed)}


def bind_score_receipt(receipt, *, provider_id, model_id):
    committed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    committed.update({"provider_id": provider_id, "model_id": model_id})
    return {**committed, "receipt_hash": hash_payload(committed)}


def validate_score_receipt(receipt, *, task=None):
    required = {"receipt_version", "task_id", "task_kind", "task_contract_hash",
                "provider_id", "model_id", "channel_hash", "decisions", "selected_value",
                "inference_passes", "menu_option_total", "provider_backed", "adapter_owned",
                "hidden_truth_used", "receipt_hash"}
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise ValueError("hierarchical_score_receipt_shape_invalid")
    committed = {key: receipt[key] for key in receipt if key != "receipt_hash"}
    if (receipt["receipt_version"] != SCORE_RECEIPT_VERSION
            or receipt["receipt_hash"] != hash_payload(committed)
            or receipt["inference_passes"] != len(receipt["decisions"])
            or receipt["menu_option_total"] != sum(len(item.get("scores", ()))
                                                   for item in receipt["decisions"])
            or receipt["provider_backed"] is not True or receipt["adapter_owned"] is not True
            or receipt["hidden_truth_used"] is not False):
        raise ValueError("hierarchical_score_receipt_binding_invalid")
    if (not receipt["provider_id"] or not receipt["model_id"] or not receipt["selected_value"]
            or not re.fullmatch(r"[0-9a-f]{64}", receipt["channel_hash"])):
        raise ValueError("hierarchical_score_receipt_identity_invalid")
    for decision in receipt["decisions"]:
        _validate_decision(decision)
    if task and (receipt["task_id"] != task.task_id
                 or receipt["task_kind"] != task.task_kind
                 or receipt["task_contract_hash"] != task.contract_hash()):
        raise ValueError("hierarchical_score_receipt_task_binding_invalid")


def _validate_decision(decision):
    required = {"stage", "selected", "selected_probability", "margin", "entropy",
                "scores", "input_tokens", "latency_ms"}
    if not isinstance(decision, dict) or set(decision) != required or not decision["stage"]:
        raise ValueError("hierarchical_score_decision_shape_invalid")
    scores = decision["scores"]
    if (not isinstance(scores, list) or not scores
            or any(set(item) != {"option", "label", "probability"} for item in scores)):
        raise ValueError("hierarchical_score_distribution_shape_invalid")
    options = [item["option"] for item in scores]
    probabilities = [item["probability"] for item in scores]
    if (len(options) != len(set(options)) or decision["selected"] not in options
            or any(not isinstance(value, (int, float)) or isinstance(value, bool)
                   or not math.isfinite(value) or value < 0.0 for value in probabilities)
            or abs(sum(probabilities) - 1.0) > 1e-6):
        raise ValueError("hierarchical_score_distribution_invalid")
    selected = probabilities[options.index(decision["selected"])]
    ranked = sorted(probabilities, reverse=True)
    expected_margin = ranked[0] - (ranked[1] if len(ranked) > 1 else 0.0)
    if (abs(selected - decision["selected_probability"]) > 1e-6
            or selected != ranked[0] or abs(decision["margin"] - expected_margin) > 1e-6
            or not isinstance(decision["input_tokens"], int) or decision["input_tokens"] < 1
            or not isinstance(decision["latency_ms"], int) or decision["latency_ms"] < 0):
        raise ValueError("hierarchical_score_selection_invalid")
