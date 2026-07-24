"""Truth-blind Kernel policy for bounded structural-prior escalation."""

from __future__ import annotations

import math

from .calibrated_score_receipt import validate_calibrated_score_receipt
from .problem_admission_gate import ProblemAdmissionKernelGate
from .problem_formulation_contracts import validate_problem_definition_receipt
from .provider_telemetry import hash_payload


CONTRASTIVE_TRIGGER_POLICY_VERSION = "contrastive_structure_trigger_policy_v0_2"


class ContrastiveStructureTriggerPolicy:
    def __init__(self, *, max_items=2, confidence_floor=0.5, entropy_floor=0.65):
        if max_items < 0 or not 0 <= confidence_floor <= 1 or not 0 <= entropy_floor <= 1:
            raise ValueError("contrastive_trigger_policy_configuration_invalid")
        self.max_items = max_items
        self.confidence_floor = confidence_floor
        self.entropy_floor = entropy_floor

    def evaluate(self, *, experiment_id, definition_runs):
        records = []
        for run in definition_runs:
            problem = run.result["problem_receipt"]
            decision = run.result["decision_receipt"]
            validate_problem_definition_receipt(problem, task=run.tasks[-1],
                                                decision_receipt=decision)
            validate_calibrated_score_receipt(decision, task=run.tasks[-1])
            consistency = list(ProblemAdmissionKernelGate._definition_reasons(problem))
            probabilities = [item["selected_probability"] for item in decision["decisions"]]
            entropies = [_normalized_entropy(item) for item in decision["decisions"]]
            minimum = min(probabilities)
            mean_confidence = sum(probabilities) / len(probabilities)
            mean_entropy = sum(entropies) / len(entropies)
            eligible = bool(consistency) or minimum < self.confidence_floor or (
                mean_entropy > self.entropy_floor
            )
            priority = 2 * len(consistency) + (1 - mean_confidence) + mean_entropy
            records.append({
                "item_id": problem["item_id"],
                "problem_receipt_hash": problem["receipt_hash"],
                "decision_receipt_hash": decision["receipt_hash"],
                "consistency_reasons": consistency,
                "minimum_selected_probability": round(minimum, 12),
                "mean_selected_probability": round(mean_confidence, 12),
                "mean_normalized_entropy": round(mean_entropy, 12),
                "eligible": eligible, "priority_score": round(priority, 12),
            })
        ranked = sorted(
            (item for item in records if item["eligible"]),
            key=lambda item: (-item["priority_score"], item["item_id"]),
        )
        selected = [item["item_id"] for item in ranked[:self.max_items]]
        committed = {
            "policy_version": CONTRASTIVE_TRIGGER_POLICY_VERSION,
            "experiment_id": experiment_id, "selected_item_ids": selected,
            "candidate_records": records,
            "max_items": self.max_items, "confidence_floor": self.confidence_floor,
            "entropy_floor": self.entropy_floor, "selection_basis": (
                "FORMAL_COHERENCE_PLUS_CONTEXT_CALIBRATED_UNCERTAINTY"
            ),
            "kernel_owned": True, "provider_authority": False,
            "hidden_truth_used": False,
        }
        return {**committed, "receipt_hash": hash_payload(committed)}


def validate_contrastive_trigger_receipt(receipt):
    committed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    selected = receipt.get("selected_item_ids", ())
    candidates = receipt.get("candidate_records", ())
    if (receipt.get("policy_version") != CONTRASTIVE_TRIGGER_POLICY_VERSION
            or receipt.get("receipt_hash") != hash_payload(committed)
            or len(selected) > receipt.get("max_items", -1)
            or len(selected) != len(set(selected))
            or not set(selected).issubset({item.get("item_id") for item in candidates})
            or receipt.get("kernel_owned") is not True
            or receipt.get("provider_authority") is not False
            or receipt.get("hidden_truth_used") is not False):
        raise ValueError("contrastive_trigger_receipt_invalid")


def _normalized_entropy(decision):
    count = len(decision["scores"])
    if count <= 1:
        return 0.0
    return max(0.0, min(1.0, float(decision["entropy"]) / math.log(count)))
