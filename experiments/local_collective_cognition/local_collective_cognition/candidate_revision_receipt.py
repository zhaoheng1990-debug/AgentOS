"""Harness-owned replay and option binding for Provider candidate revisions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .argument_verification_receipt import MechanicalArgumentVerifier, same_value
from .candidate_revision_contracts import CHOICE_LABELS, REVISION_LABELS
from .provider_telemetry import hash_payload


def _hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class CandidateRevisionReceipt:
    item_id: str
    candidate_id: str
    original_candidate: str
    proposed_candidate: str
    derived_candidate: str
    status: str
    disposition: str
    derived_result: str
    failure_code: str
    expression_hash: str
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
            or not self.harness_owned or self.hidden_truth_used
            or self.receipt_hash != _hash(self._committed())
        ):
            raise ValueError("candidate_revision_receipt_invalid")

    def as_dict(self):
        return {**self._committed(), "receipt_hash": self.receipt_hash}


class CandidateRevisionVerifier:
    def __init__(self, harness) -> None:
        self.replay = MechanicalArgumentVerifier(harness)

    def verify(
        self, *, item_id: str, candidate_id: str, candidate_label: str,
        expression: str = "", proposed_candidate: str = "", argument: dict[str, Any] | None = None,
    ) -> CandidateRevisionReceipt:
        argument = argument or {}
        expression = expression or str(argument.get("expression", ""))
        proposed = proposed_candidate or str(argument.get("proposed_candidate", ""))
        question = self.replay.harness.provider_inputs((item_id,))["questions"][0]
        result = derived = failure = ""
        if proposed == "ABSTAIN":
            status, disposition = "RETRACTED", "RETRACTED"
        else:
            try:
                result, question = self.replay.replay_single(item_id=item_id, expression=expression)
                matches = [
                    item.split(":", 1)[0] for item in question["choices"]
                    if same_value(result, item.split(":", 1)[1].strip())
                ]
                derived = matches[0] if len(matches) == 1 else ""
                if derived != proposed:
                    failure = "DERIVED_RESULT_NOT_BOUND_TO_PROPOSED_CANDIDATE"
                status = "VERIFIED" if derived == proposed else "FAILED"
                disposition = (
                    "SUPPORT" if status == "VERIFIED" and proposed == candidate_label
                    else "REVISE" if status == "VERIFIED" else "INVALID"
                )
            except (ValueError, SyntaxError, ZeroDivisionError) as exc:
                status, disposition = "FAILED", "INVALID"
                failure = type(exc).__name__ + ":" + str(exc)
        committed = {
            "item_id": item_id, "candidate_id": candidate_id,
            "original_candidate": candidate_label, "proposed_candidate": proposed,
            "derived_candidate": derived, "status": status, "disposition": disposition,
            "derived_result": result, "failure_code": failure,
            "expression_hash": hash_payload(expression), "public_question_hash": _hash(question),
            "harness_owned": True, "hidden_truth_used": False,
        }
        return CandidateRevisionReceipt(**committed, receipt_hash=_hash(committed))
