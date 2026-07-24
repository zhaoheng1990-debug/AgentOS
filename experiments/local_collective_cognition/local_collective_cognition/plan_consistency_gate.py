"""Kernel-owned replay, consistency, and budget gate for global plan intent."""

from __future__ import annotations

from dataclasses import dataclass

from .plan_intent_contracts import validate_plan_intent_receipt
from .provider_telemetry import hash_payload


PLAN_CONSISTENCY_GATE_VERSION = "plan_consistency_kernel_gate_v0_23"


@dataclass(frozen=True)
class PlanIntentBudget:
    max_turns: int = 5
    max_inference_passes: int = 24
    max_input_tokens: int = 14000

    def __post_init__(self):
        if min(self.max_turns, self.max_inference_passes, self.max_input_tokens) < 1:
            raise ValueError("plan_intent_budget_invalid")


@dataclass(frozen=True)
class PlanGateOutcome:
    status: str
    reasons: tuple[str, ...]
    replay_receipts: tuple
    final_receipt: object | None
    gate_receipt: dict


class PlanConsistencyKernelGate:
    def __init__(self, harness, *, budget=None):
        self.harness = harness
        self.budget = budget or PlanIntentBudget()

    def evaluate(self, *, receipt, preview_receipts):
        validate_plan_intent_receipt(receipt)
        reasons = self._budget_reasons(receipt)
        scaffold = dict(self.harness.derivation_scaffold(receipt["item_id"]))
        if hash_payload(scaffold) != receipt["initial_state_hash"]:
            reasons.append("INITIAL_STATE_HASH_MISMATCH")
        if hash_payload([item.as_dict() for item in preview_receipts]) != receipt["preview_trace_hash"]:
            reasons.append("PREVIEW_TRACE_HASH_MISMATCH")
        replay = []
        if not reasons:
            for index, action in enumerate(receipt["planned_actions"], 1):
                step = self.harness.execute_derivation_step(
                    item_id=receipt["item_id"], candidate_id=receipt["candidate_id"],
                    step_id=f"STEP_{index}", action=action, symbol_values=scaffold,
                )
                replay.append(step)
                scaffold[step.step_id] = step.result
            if [item.as_dict() for item in replay] != [item.as_dict() for item in preview_receipts]:
                reasons.append("PLAN_REPLAY_DIVERGED")
        terminal = receipt["terminal_action"]
        expected_step = f"STEP_{len(receipt['planned_actions'])}"
        if (terminal["action"] == "FINALIZE"
                and (not receipt["planned_actions"] or terminal["inputs"] != [expected_step])):
            reasons.append("FINAL_RESULT_NOT_LAST_PLANNED_STEP")
        status = "BLOCK" if reasons else "ALLOW"
        final = None
        if status == "ALLOW":
            final = self.harness.finalize_derivation_session(
                item_id=receipt["item_id"], candidate_id=receipt["candidate_id"],
                original_candidate=receipt["original_candidate"], action=terminal,
                step_receipts=tuple(replay), provider_turns=receipt["turns"],
                invalid_actions=0,
            )
        gate_receipt = self._gate_receipt(receipt, status, reasons, replay, final)
        return PlanGateOutcome(status, tuple(reasons), tuple(replay), final, gate_receipt)

    def budget_stop_receipt(self, *, item_id, candidate_id, turns, inference_passes,
                            input_tokens, reason):
        committed = {
            "gate_version": PLAN_CONSISTENCY_GATE_VERSION,
            "item_id": item_id, "candidate_id": candidate_id,
            "status": "BLOCK", "reason": reason, "turns": turns,
            "inference_passes": inference_passes, "input_tokens": input_tokens,
            "budget": self.budget.__dict__, "kernel_owned": True,
            "provider_authority": False, "hidden_truth_used": False,
        }
        return {**committed, "receipt_hash": hash_payload(committed)}

    def _budget_reasons(self, receipt):
        reasons = []
        if receipt["turns"] > self.budget.max_turns:
            reasons.append("PLAN_TURN_BUDGET_EXCEEDED")
        if receipt["inference_passes"] > self.budget.max_inference_passes:
            reasons.append("PLAN_INFERENCE_BUDGET_EXCEEDED")
        if receipt["input_tokens"] > self.budget.max_input_tokens:
            reasons.append("PLAN_INPUT_TOKEN_BUDGET_EXCEEDED")
        return reasons

    def _gate_receipt(self, plan, status, reasons, replay, final):
        committed = {
            "gate_version": PLAN_CONSISTENCY_GATE_VERSION,
            "plan_receipt_hash": plan["receipt_hash"], "status": status,
            "reasons": list(reasons), "budget": self.budget.__dict__,
            "replay_trace_hash": hash_payload([item.as_dict() for item in replay]),
            "final_receipt_hash": final.receipt_hash if final else "",
            "kernel_owned": True, "provider_authority": False, "hidden_truth_used": False,
        }
        return {**committed, "receipt_hash": hash_payload(committed)}
