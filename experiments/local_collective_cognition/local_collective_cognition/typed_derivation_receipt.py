"""Harness execution receipt for typed derivation plans."""

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
class TypedDerivationReceipt:
    item_id: str
    candidate_id: str
    original_candidate: str
    proposed_candidate: str
    derived_candidate: str
    status: str
    disposition: str
    derived_result: str
    failure_code: str
    executed_steps: int
    plan_hash: str
    scaffold_hash: str
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
            or self.executed_steps < 0 or not self.harness_owned or self.hidden_truth_used
            or self.receipt_hash != _hash(self._committed())
        ):
            raise ValueError("typed_derivation_receipt_invalid")

    def as_dict(self):
        return {**self._committed(), "receipt_hash": self.receipt_hash}


class TypedDerivationVerifier:
    def __init__(self, harness) -> None:
        self.harness = harness

    def verify(self, *, item_id: str, candidate_id: str, candidate_label: str,
               argument: dict[str, Any], **_) -> TypedDerivationReceipt:
        proposed = argument["proposed_candidate"]
        scaffold = self.harness.derivation_scaffold(item_id)
        question = self.harness.provider_inputs((item_id,))["questions"][0]
        result = derived = failure = ""
        executed = 0
        if proposed == "ABSTAIN":
            status, disposition = "RETRACTED", "RETRACTED"
        else:
            try:
                result, executed = self._execute(argument["steps"], scaffold)
                matches = [item.split(":", 1)[0] for item in question["choices"]
                           if same_value(result, item.split(":", 1)[1].strip())]
                derived = matches[0] if len(matches) == 1 else ""
                if derived != proposed:
                    failure = "DERIVED_RESULT_NOT_BOUND_TO_PROPOSED_CANDIDATE"
                status = "VERIFIED" if derived == proposed else "FAILED"
                disposition = ("SUPPORT" if status == "VERIFIED" and proposed == candidate_label
                               else "REVISE" if status == "VERIFIED" else "INVALID")
            except (ValueError, ZeroDivisionError) as exc:
                status, disposition = "FAILED", "INVALID"
                failure = type(exc).__name__ + ":" + str(exc)
        committed = {
            "item_id": item_id, "candidate_id": candidate_id,
            "original_candidate": candidate_label, "proposed_candidate": proposed,
            "derived_candidate": derived, "status": status, "disposition": disposition,
            "derived_result": result, "failure_code": failure, "executed_steps": executed,
            "plan_hash": hash_payload(argument), "scaffold_hash": _hash(scaffold),
            "public_question_hash": _hash(question), "harness_owned": True, "hidden_truth_used": False,
        }
        return TypedDerivationReceipt(**committed, receipt_hash=_hash(committed))

    @staticmethod
    def _execute(steps, scaffold) -> tuple[str, int]:
        values: dict[str, Fraction | str] = {
            key: Fraction(value) if _numeric(value) else value for key, value in scaffold.items()
        }
        for step in steps:
            args = [values[item] for item in step["inputs"]]
            op = step["operator"]
            if op in BINARY_OPERATORS:
                if any(not isinstance(item, Fraction) for item in args):
                    raise ValueError("typed_derivation_numeric_type_invalid")
                left, right = args
                functions = {"ADD": lambda: left + right, "SUBTRACT": lambda: left - right,
                             "MULTIPLY": lambda: left * right, "DIVIDE": lambda: left / right,
                             "MODULO": lambda: left % right}
                value = functions[op]()
            else:
                value = str(args[0])
                if len(value) % 2:
                    raise ValueError("typed_derivation_string_arity_invalid")
                if op == "SWAP_HALVES":
                    middle = len(value) // 2
                    value = value[middle:] + value[:middle]
                else:
                    value = "".join(value[index + 1] + value[index]
                                    for index in range(0, len(value), 2))
            values[step["step_id"]] = value
        final = values[steps[-1]["step_id"]]
        return (str(final.numerator) if isinstance(final, Fraction) and final.denominator == 1
                else str(final)), len(steps)


def _numeric(value: str) -> bool:
    try:
        Fraction(value)
        return True
    except ValueError:
        return False
