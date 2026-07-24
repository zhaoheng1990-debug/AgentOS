"""Validation and aggregation for context-calibrated semantic score receipts."""

from __future__ import annotations

import math
import re

from .provider_telemetry import hash_payload


CALIBRATED_SCORE_RECEIPT_VERSION = "context_calibrated_score_receipt_v0_23"


def build_calibrated_score_receipt(*, task, channel_hash, decisions, selected_value,
                                   provider_id, model_id):
    committed = {
        "receipt_version": CALIBRATED_SCORE_RECEIPT_VERSION,
        "task_id": task.task_id, "task_kind": task.task_kind,
        "task_contract_hash": task.contract_hash(), "provider_id": provider_id,
        "model_id": model_id, "channel_hash": channel_hash,
        "decisions": list(decisions), "selected_value": selected_value,
        "inference_passes": sum(item["inference_passes"] for item in decisions),
        "menu_option_total": sum(len(item["scores"]) for item in decisions),
        "calibration_method": "CONTEXT_LOG_PROB_MINUS_CONTENT_FREE_LABEL_PRIOR",
        "provider_backed": True, "adapter_owned": True, "hidden_truth_used": False,
    }
    return {**committed, "receipt_hash": hash_payload(committed)}


def validate_calibrated_score_receipt(receipt, *, task=None):
    required = {"receipt_version", "task_id", "task_kind", "task_contract_hash",
                "provider_id", "model_id", "channel_hash", "decisions", "selected_value",
                "inference_passes", "menu_option_total", "calibration_method",
                "provider_backed", "adapter_owned", "hidden_truth_used", "receipt_hash"}
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise ValueError("calibrated_score_receipt_shape_invalid")
    committed = {key: receipt[key] for key in receipt if key != "receipt_hash"}
    if (receipt["receipt_version"] != CALIBRATED_SCORE_RECEIPT_VERSION
            or receipt["receipt_hash"] != hash_payload(committed)
            or receipt["inference_passes"] != sum(item.get("inference_passes", 0)
                                                  for item in receipt["decisions"])
            or receipt["menu_option_total"] != sum(len(item.get("scores", ()))
                                                   for item in receipt["decisions"])
            or receipt["provider_backed"] is not True or receipt["adapter_owned"] is not True
            or receipt["hidden_truth_used"] is not False):
        raise ValueError("calibrated_score_receipt_binding_invalid")
    if (not receipt["provider_id"] or not receipt["model_id"] or not receipt["selected_value"]
            or not re.fullmatch(r"[0-9a-f]{64}", receipt["channel_hash"])):
        raise ValueError("calibrated_score_receipt_identity_invalid")
    for decision in receipt["decisions"]:
        _validate_decision(decision, receipt["model_id"])
    if task and (receipt["task_id"] != task.task_id
                 or receipt["task_kind"] != task.task_kind
                 or receipt["task_contract_hash"] != task.contract_hash()):
        raise ValueError("calibrated_score_receipt_task_binding_invalid")


def _validate_decision(decision, model_id):
    required = {"stage", "selected", "selected_probability", "margin", "entropy",
                "scores", "input_tokens", "latency_ms", "inference_passes",
                "calibration_ref", "calibration_cached"}
    if not isinstance(decision, dict) or set(decision) != required:
        raise ValueError("calibrated_score_decision_shape_invalid")
    scores = decision["scores"]
    score_keys = {"option", "label", "probability", "context_probability",
                  "prior_probability", "calibrated_log_ratio"}
    if not scores or any(set(item) != score_keys for item in scores):
        raise ValueError("calibrated_score_distribution_shape_invalid")
    options, probabilities = ([item["option"] for item in scores],
                              [item["probability"] for item in scores])
    numeric = [value for item in scores for value in (
        item["probability"], item["context_probability"], item["prior_probability"],
        item["calibrated_log_ratio"],
    )]
    if (len(options) != len(set(options)) or decision["selected"] not in options
            or any(not isinstance(value, (int, float)) or isinstance(value, bool)
                   or not math.isfinite(value) for value in numeric)
            or abs(sum(probabilities) - 1.0) > 1e-6
            or abs(sum(item["context_probability"] for item in scores) - 1.0) > 1e-6
            or abs(sum(item["prior_probability"] for item in scores) - 1.0) > 1e-6):
        raise ValueError("calibrated_score_distribution_invalid")
    selected = probabilities[options.index(decision["selected"])]
    ranked = sorted(probabilities, reverse=True)
    margin = ranked[0] - (ranked[1] if len(ranked) > 1 else 0.0)
    expected_calibration_ref = hash_payload({
        "model_id": model_id, "menu_size": len(scores),
        "probabilities": [item["prior_probability"] for item in scores],
    })
    if (selected != ranked[0] or abs(selected - decision["selected_probability"]) > 1e-6
            or abs(margin - decision["margin"]) > 1e-6
            or decision["inference_passes"] not in {1, 2}
            or decision["calibration_cached"] != (decision["inference_passes"] == 1)
            or decision["calibration_ref"] != expected_calibration_ref):
        raise ValueError("calibrated_score_selection_invalid")
