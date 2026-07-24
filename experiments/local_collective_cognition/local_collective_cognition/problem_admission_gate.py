"""Kernel-owned problem admission and problem-to-plan binding gates."""

from __future__ import annotations

from dataclasses import dataclass

from .plan_intent_contracts import validate_plan_intent_receipt
from .problem_formulation_contracts import (
    semantic_problem_fields, validate_coordination_receipt, validate_problem_definition_receipt,
)
from .provider_telemetry import hash_payload
from .typed_derivation_contracts import BINARY_OPERATORS, UNARY_OPERATORS


PROBLEM_ADMISSION_GATE_VERSION = "problem_admission_kernel_gate_v0_24"
PLAN_PROBLEM_BINDING_VERSION = "problem_plan_binding_kernel_gate_v0_24"

FAMILY_TARGETS = {
    "ARITHMETIC_COMPOSITION": "FINAL_SCALAR", "RATE_SCALING": "SCALED_QUANTITY",
    "PERCENTAGE": "SCALED_QUANTITY", "SET_COMPLEMENT": "COMPLEMENT_COUNT",
    "WITHOUT_REPLACEMENT": "PROBABILITY", "BAYES_POSTERIOR": "POSTERIOR_PROBABILITY",
    "MODULAR_REMAINDER": "REMAINDER", "RATIO_ALLOCATION": "ALLOCATED_SHARE",
    "ARITHMETIC_MEAN": "MEAN", "ITERATIVE_UPDATE": "FINAL_STATE",
    "STRING_COMPOSITION": "TRANSFORMED_STRING", "UNIT_DISTANCE": "DISTANCE",
}
FAMILY_CONSTRAINTS = {
    "ARITHMETIC_COMPOSITION": {"NONE", "ORDER_SENSITIVE"},
    "RATE_SCALING": {"CONSTANT_RATE"}, "PERCENTAGE": {"PERCENT_NORMALIZATION"},
    "SET_COMPLEMENT": {"INCLUSION_EXCLUSION"},
    "WITHOUT_REPLACEMENT": {"WITHOUT_REPLACEMENT", "COMPLEMENT_EVENT"},
    "BAYES_POSTERIOR": {"BASE_RATE_AND_FALSE_POSITIVE"},
    "MODULAR_REMAINDER": {"DIVISION_REMAINDER"},
    "RATIO_ALLOCATION": {"RATIO_NORMALIZATION"},
    "ARITHMETIC_MEAN": {"CARDINALITY_NORMALIZATION"},
    "ITERATIVE_UPDATE": {"ORDER_SENSITIVE"}, "STRING_COMPOSITION": {"ORDER_SENSITIVE"},
    "UNIT_DISTANCE": {"UNIT_COMPOSITION"},
}
FAMILY_OPERATORS = {
    "ARITHMETIC_COMPOSITION": set(BINARY_OPERATORS),
    "RATE_SCALING": {"DIVIDE", "MULTIPLY"}, "PERCENTAGE": {"DIVIDE", "MULTIPLY"},
    "SET_COMPLEMENT": {"ADD", "SUBTRACT"},
    "WITHOUT_REPLACEMENT": {"ADD", "SUBTRACT", "MULTIPLY", "DIVIDE"},
    "BAYES_POSTERIOR": {"ADD", "SUBTRACT", "MULTIPLY", "DIVIDE"},
    "MODULAR_REMAINDER": {"MODULO"},
    "RATIO_ALLOCATION": {"ADD", "MULTIPLY", "DIVIDE"},
    "ARITHMETIC_MEAN": {"ADD", "DIVIDE"},
    "ITERATIVE_UPDATE": {"ADD", "MULTIPLY"},
    "STRING_COMPOSITION": set(UNARY_OPERATORS), "UNIT_DISTANCE": {"MULTIPLY"},
}


@dataclass(frozen=True)
class ProblemFormulationBudget:
    max_inference_passes: int = 20
    max_input_tokens: int = 12000
    coordinator_confidence_floor: float = 0.65


class ProblemAdmissionKernelGate:
    def __init__(self, *, budget=None):
        self.budget = budget or ProblemFormulationBudget()

    def evaluate(self, *, candidate_receipts, coordination_receipt, inference_passes,
                 input_tokens):
        candidates = list(candidate_receipts)
        if len(candidates) != 2:
            raise ValueError("problem_candidate_count_invalid")
        for item in candidates:
            validate_problem_definition_receipt(item)
        validate_coordination_receipt(coordination_receipt, candidate_receipts=candidates)
        reasons = []
        valid = [self._definition_reasons(item) for item in candidates]
        if inference_passes > self.budget.max_inference_passes:
            reasons.append("PROBLEM_INFERENCE_BUDGET_EXCEEDED")
        if input_tokens > self.budget.max_input_tokens:
            reasons.append("PROBLEM_INPUT_TOKEN_BUDGET_EXCEEDED")
        consensus = semantic_problem_fields(candidates[0]) == semantic_problem_fields(candidates[1])
        selected_index = 0 if consensus else self._selected_index(coordination_receipt, reasons)
        if selected_index is not None:
            reasons.extend(valid[selected_index])
        selected = candidates[selected_index] if selected_index is not None else None
        status = "BLOCK" if reasons or selected is None else "ALLOW"
        committed = {
            "gate_version": PROBLEM_ADMISSION_GATE_VERSION,
            "item_id": candidates[0]["item_id"], "status": status, "reasons": reasons,
            "candidate_receipt_hashes": [item["receipt_hash"] for item in candidates],
            "coordination_receipt_hash": coordination_receipt["receipt_hash"],
            "selected_problem": selected or {}, "consensus_admission": consensus,
            "inference_passes": inference_passes, "input_tokens": input_tokens,
            "budget": self.budget.__dict__, "kernel_owned": True,
            "provider_authority": False, "hidden_truth_used": False,
        }
        return {**committed, "receipt_hash": hash_payload(committed)}

    def bind_plan(self, *, admission_receipt, plan_receipt):
        validate_plan_intent_receipt(plan_receipt)
        reasons, problem = [], admission_receipt.get("selected_problem", {})
        if not self._hash_valid(admission_receipt) or admission_receipt.get("status") != "ALLOW":
            reasons.append("PROBLEM_ADMISSION_INVALID")
        else:
            try:
                validate_problem_definition_receipt(problem)
            except (KeyError, ValueError):
                reasons.append("PROBLEM_ADMISSION_SELECTED_RECEIPT_INVALID")
            if problem.get("receipt_hash") not in admission_receipt.get(
                "candidate_receipt_hashes", ()
            ):
                reasons.append("PROBLEM_ADMISSION_SELECTION_LINEAGE_INVALID")
            if problem.get("item_id") != plan_receipt["item_id"]:
                reasons.append("PROBLEM_PLAN_ITEM_MISMATCH")
        if problem and problem["intent_mode"] != plan_receipt["intent_mode"]:
            reasons.append("PROBLEM_PLAN_MODE_MISMATCH")
        allowed = FAMILY_OPERATORS.get(problem.get("problem_family"), set())
        operators = {item["operator"] for item in plan_receipt["planned_actions"]}
        if operators - allowed:
            reasons.append("PROBLEM_PLAN_OPERATOR_MISMATCH")
        committed = {
            "binding_version": PLAN_PROBLEM_BINDING_VERSION,
            "item_id": plan_receipt["item_id"], "status": "BLOCK" if reasons else "ALLOW",
            "reasons": reasons, "problem_admission_hash": admission_receipt.get("receipt_hash", ""),
            "plan_intent_hash": plan_receipt["receipt_hash"],
            "operator_set": sorted(operators), "allowed_operator_set": sorted(allowed),
            "kernel_owned": True, "provider_authority": False, "hidden_truth_used": False,
        }
        return {**committed, "receipt_hash": hash_payload(committed)}

    def _selected_index(self, coordination, reasons):
        selected = coordination["selected_problem_candidate"]
        if selected == "ABSTAIN":
            reasons.append("PROBLEM_COORDINATOR_ABSTAINED")
            return None
        if coordination["confidence"] < self.budget.coordinator_confidence_floor:
            reasons.append("PROBLEM_COORDINATOR_CONFIDENCE_BELOW_FLOOR")
            return None
        return 0 if selected == "PROBLEM_1" else 1

    @staticmethod
    def _definition_reasons(problem):
        family = problem["problem_family"]
        if problem["intent_mode"] == "ABSTAIN":
            return (["PROBLEM_DEFINITION_ABSTAINED"]
                    if semantic_problem_fields(problem) == ("ABSTAIN",) * 4
                    else ["PROBLEM_ABSTAIN_FIELDS_INVALID"])
        reasons = []
        expected_mode = "STRING_TRANSFORMATION" if family == "STRING_COMPOSITION" else "NUMERIC_DERIVATION"
        if problem["intent_mode"] != expected_mode:
            reasons.append("PROBLEM_MODE_FAMILY_MISMATCH")
        if FAMILY_TARGETS.get(family) != problem["target_kind"]:
            reasons.append("PROBLEM_FAMILY_TARGET_MISMATCH")
        if problem["critical_constraint"] not in FAMILY_CONSTRAINTS.get(family, set()):
            reasons.append("PROBLEM_FAMILY_CONSTRAINT_MISMATCH")
        return reasons

    @staticmethod
    def _hash_valid(receipt):
        committed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
        return receipt.get("receipt_hash") == hash_payload(committed)
