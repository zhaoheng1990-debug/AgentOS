"""Aggregate Harness gate for correction opportunity without item disclosure."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


def _hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class ArgumentOpportunityReceipt:
    experiment_id: str
    scheduled_pairs: int
    disagreements: int
    primary_error_opportunities: int
    peer_correction_opportunities: int
    peer_harm_opportunities: int
    gate_passed: bool
    pair_candidate_hash: str
    truth_commitment: str
    receipt_hash: str
    harness_owned: bool = True
    item_identity_disclosed: bool = False
    routing_authority: bool = False
    gate_basis: str = "PEER_CORRECTION_OPPORTUNITY"

    def _committed(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if key != "receipt_hash"}

    def __post_init__(self) -> None:
        counts = (
            self.scheduled_pairs, self.disagreements, self.primary_error_opportunities,
            self.peer_correction_opportunities, self.peer_harm_opportunities,
        )
        if (
            not self.experiment_id or any(item < 0 for item in counts)
            or not self.harness_owned or self.item_identity_disclosed or self.routing_authority
            or self.gate_basis not in {"PEER_CORRECTION_OPPORTUNITY", "PRIMARY_ERROR_OPPORTUNITY"}
            or self.gate_passed != (
                self.peer_correction_opportunities > 0
                if self.gate_basis == "PEER_CORRECTION_OPPORTUNITY"
                else self.primary_error_opportunities > 0
            )
            or any(not re.fullmatch(r"[0-9a-f]{64}", item)
                   for item in (self.pair_candidate_hash, self.truth_commitment))
            or self.receipt_hash != _hash(self._committed())
        ):
            raise ValueError("argument_opportunity_receipt_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed(), "receipt_hash": self.receipt_hash}


def build_argument_opportunity_receipt(
    *, experiment_id: str, pairs: tuple[dict[str, str], ...],
    truths: dict[str, str], truth_commitment: str,
) -> ArgumentOpportunityReceipt:
    required = {"item_id", "primary_model_id", "peer_model_id", "primary_answer", "peer_answer"}
    if any(set(item) != required or item["item_id"] not in truths for item in pairs):
        raise ValueError("argument_opportunity_pair_invalid")
    disagreements = primary_errors = corrections = harms = 0
    commitment_rows = []
    for item in pairs:
        truth = truths[item["item_id"]]
        primary, peer = item["primary_answer"], item["peer_answer"]
        disagreements += primary != peer
        primary_errors += primary != truth
        corrections += primary != truth and peer == truth
        harms += primary == truth and peer != truth
        commitment_rows.append(tuple(item[key] for key in sorted(required)))
    committed = {
        "experiment_id": experiment_id, "scheduled_pairs": len(pairs),
        "disagreements": disagreements, "primary_error_opportunities": primary_errors,
        "peer_correction_opportunities": corrections, "peer_harm_opportunities": harms,
        "gate_passed": corrections > 0, "pair_candidate_hash": _hash(commitment_rows),
        "truth_commitment": truth_commitment, "harness_owned": True,
        "item_identity_disclosed": False, "routing_authority": False,
        "gate_basis": "PEER_CORRECTION_OPPORTUNITY",
    }
    return ArgumentOpportunityReceipt(**committed, receipt_hash=_hash(committed))
