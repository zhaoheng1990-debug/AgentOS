"""Harness-owned step and final receipts for iterative derivation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from typing import Any

from .argument_verification_receipt import same_value
from .candidate_revision_contracts import CHOICE_LABELS, REVISION_LABELS
from .provider_telemetry import hash_payload
from .typed_derivation_contracts import BINARY_OPERATORS


def _hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class IterativeStepReceipt:
    item_id: str
    candidate_id: str
    step_id: str
    operator: str
    inputs: tuple[str, ...]
    result: str
    input_state_hash: str
    action_hash: str
    receipt_hash: str
    harness_owned: bool = True
    hidden_truth_used: bool = False

    def _committed(self):
        return {**{key: value for key, value in self.__dict__.items() if key != "receipt_hash"},
                "inputs": list(self.inputs)}

    def __post_init__(self):
        if (not self.step_id.startswith("STEP_") or not self.result or not self.harness_owned
                or self.hidden_truth_used or self.receipt_hash != _hash(self._committed())):
            raise ValueError("iterative_step_receipt_invalid")

    def as_dict(self):
        return {**self._committed(), "receipt_hash": self.receipt_hash}


@dataclass(frozen=True)
class IterativeFinalReceipt:
    item_id: str
    candidate_id: str
    original_candidate: str
    proposed_candidate: str
    derived_candidate: str
    status: str
    disposition: str
    derived_result: str
    selected_step: str
    applied_steps: int
    provider_turns: int
    invalid_actions: int
    trace_hash: str
    public_question_hash: str
    receipt_hash: str
    harness_owned: bool = True
    hidden_truth_used: bool = False

    def _committed(self):
        return {key: value for key, value in self.__dict__.items() if key != "receipt_hash"}

    def __post_init__(self):
        valid = {"VERIFIED": {"SUPPORT", "REVISE"}, "FAILED": {"INVALID"},
                 "RETRACTED": {"RETRACTED"}}
        if (
            self.status not in valid or self.disposition not in valid[self.status]
            or self.original_candidate not in CHOICE_LABELS
            or self.proposed_candidate not in REVISION_LABELS
            or self.derived_candidate not in (*CHOICE_LABELS, "")
            or (self.status == "VERIFIED") != (self.proposed_candidate == self.derived_candidate)
            or (self.status == "RETRACTED") != (self.proposed_candidate == "ABSTAIN")
            or min(self.applied_steps, self.provider_turns, self.invalid_actions) < 0
            or not self.harness_owned or self.hidden_truth_used
            or self.receipt_hash != _hash(self._committed())
        ):
            raise ValueError("iterative_final_receipt_invalid")

    def as_dict(self):
        return {**self._committed(), "receipt_hash": self.receipt_hash}


def execute_step(*, item_id, candidate_id, step_id, action, symbol_values) -> IterativeStepReceipt:
    args = [symbol_values[item] for item in action["inputs"]]
    operator = action["operator"]
    if operator in BINARY_OPERATORS:
        numeric = [_fraction(item) for item in args]
        left, right = numeric
        functions = {"ADD": lambda: left + right, "SUBTRACT": lambda: left - right,
                     "MULTIPLY": lambda: left * right, "DIVIDE": lambda: left / right,
                     "MODULO": lambda: left % right}
        result = _render(functions[operator]())
    else:
        value = str(args[0])
        if len(value) % 2:
            raise ValueError("iterative_derivation_string_arity_invalid")
        if operator == "SWAP_HALVES":
            middle = len(value) // 2
            result = value[middle:] + value[:middle]
        else:
            result = "".join(value[index + 1] + value[index]
                             for index in range(0, len(value), 2))
    committed = {"item_id": item_id, "candidate_id": candidate_id, "step_id": step_id,
                 "operator": operator, "inputs": list(action["inputs"]), "result": result,
                 "input_state_hash": _hash(symbol_values), "action_hash": hash_payload(action),
                 "harness_owned": True, "hidden_truth_used": False}
    return IterativeStepReceipt(**{**committed, "inputs": tuple(action["inputs"]),
                                  "receipt_hash": _hash(committed)})


def finalize_session(*, item_id, candidate_id, original_candidate, action, step_receipts,
                     provider_turns, invalid_actions, question) -> IterativeFinalReceipt:
    proposed = action["proposed_candidate"]
    selected = action["inputs"][0] if action["action"] == "FINALIZE" else ""
    result = next((item.result for item in step_receipts if item.step_id == selected), "")
    matches = [item.split(":", 1)[0] for item in question["choices"]
               if result and same_value(result, item.split(":", 1)[1].strip())]
    derived = matches[0] if len(matches) == 1 else ""
    if action["action"] == "ABSTAIN":
        status, disposition = "RETRACTED", "RETRACTED"
    else:
        status = "VERIFIED" if derived == proposed else "FAILED"
        disposition = ("SUPPORT" if status == "VERIFIED" and proposed == original_candidate
                       else "REVISE" if status == "VERIFIED" else "INVALID")
    committed = {"item_id": item_id, "candidate_id": candidate_id,
                 "original_candidate": original_candidate, "proposed_candidate": proposed,
                 "derived_candidate": derived, "status": status, "disposition": disposition,
                 "derived_result": result, "selected_step": selected,
                 "applied_steps": len(step_receipts), "provider_turns": provider_turns,
                 "invalid_actions": invalid_actions,
                 "trace_hash": _hash([item.as_dict() for item in step_receipts]),
                 "public_question_hash": _hash(question), "harness_owned": True,
                 "hidden_truth_used": False}
    return IterativeFinalReceipt(**committed, receipt_hash=_hash(committed))


def iterative_final_receipt_from_dict(value) -> IterativeFinalReceipt:
    return IterativeFinalReceipt(**value)


class IterativeDerivationVerifier:
    def verify(self, *, item_id, candidate_id, candidate_label, argument, **_):
        receipt = iterative_final_receipt_from_dict(argument["final_receipt"])
        if (receipt.item_id != item_id or receipt.candidate_id != candidate_id
                or receipt.original_candidate != candidate_label):
            raise ValueError("iterative_final_receipt_binding_invalid")
        return receipt


def _fraction(value) -> Fraction:
    try:
        return Fraction(str(value))
    except ValueError as exc:
        raise ValueError("iterative_derivation_numeric_type_invalid") from exc


def _render(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else str(value)
