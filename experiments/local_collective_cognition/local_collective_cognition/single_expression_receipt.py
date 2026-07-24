"""Harness-derived replay details for a single Provider expression."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .argument_verification_receipt import MechanicalArgumentVerifier, same_value
from .provider_telemetry import hash_payload


def _hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class SingleExpressionReceipt:
    item_id: str
    candidate_id: str
    status: str
    derived_result: str
    conclusion_bound: bool
    failure_code: str
    expression_hash: str
    public_question_hash: str
    receipt_hash: str
    harness_owned: bool = True
    hidden_truth_used: bool = False

    def _committed(self):
        return {key: value for key, value in self.__dict__.items() if key != "receipt_hash"}

    def __post_init__(self):
        if (
            self.status not in {"VERIFIED", "FAILED"} or not self.harness_owned
            or self.hidden_truth_used or self.receipt_hash != _hash(self._committed())
        ):
            raise ValueError("single_expression_receipt_invalid")

    def as_dict(self):
        return {**self._committed(), "receipt_hash": self.receipt_hash}


class SingleExpressionVerifier:
    def __init__(self, harness) -> None:
        self.replay = MechanicalArgumentVerifier(harness)

    def verify(
        self, *, item_id: str, candidate_id: str, candidate_label: str,
        expression: str = "", argument: dict[str, Any] | None = None,
    ):
        expression = expression or str((argument or {}).get("expression", ""))
        result, failure = "", ""
        try:
            result, question = self.replay.replay_single(item_id=item_id, expression=expression)
            choice = next(
                (item.split(":", 1)[1].strip() for item in question["choices"]
                 if item.startswith(candidate_label + ":")), "",
            )
            bound = same_value(result, choice)
            if not bound:
                failure = "DERIVED_RESULT_NOT_BOUND_TO_CANDIDATE"
        except (ValueError, SyntaxError, ZeroDivisionError) as exc:
            question = self.replay.harness.provider_inputs((item_id,))["questions"][0]
            bound, failure = False, type(exc).__name__ + ":" + str(exc)
        committed = {
            "item_id": item_id, "candidate_id": candidate_id,
            "status": "VERIFIED" if bound else "FAILED", "derived_result": result,
            "conclusion_bound": bound, "failure_code": failure,
            "expression_hash": hash_payload(expression), "public_question_hash": _hash(question),
            "harness_owned": True, "hidden_truth_used": False,
        }
        return SingleExpressionReceipt(**committed, receipt_hash=_hash(committed))
