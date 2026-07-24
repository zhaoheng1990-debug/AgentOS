"""Harness-owned historical outcome receipts for disagreement operators."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class DomainDisagreementRecord:
    domain: str
    total: int
    disagreements: int
    primary_correct: int
    majority_correct: int
    corrections: int
    harms: int
    correction_opportunities: int
    harm_opportunities: int
    correction_posterior: float
    harm_posterior: float
    observed_net_cbit: float

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class DisagreementOperatorReceipt:
    experiment_id: str
    operator_id: str
    source_report_hash: str
    candidate_output_hashes: tuple[str, ...]
    records: tuple[DomainDisagreementRecord, ...]
    evidence_refs: tuple[str, ...]
    truth_commitment: str
    receipt_hash: str
    harness_owned: bool = True
    routing_authority: bool = False

    def _committed_dict(self) -> dict[str, Any]:
        return {
            **{key: value for key, value in self.__dict__.items() if key not in {"candidate_output_hashes", "records", "evidence_refs", "receipt_hash"}},
            "candidate_output_hashes": list(self.candidate_output_hashes),
            "records": [item.as_dict() for item in self.records],
            "evidence_refs": list(self.evidence_refs),
        }

    def __post_init__(self) -> None:
        if self.operator_id != "MAJORITY" or not self.harness_owned or self.routing_authority:
            raise ValueError("disagreement_operator_authority_invalid")
        for value in (self.source_report_hash, self.truth_commitment, self.receipt_hash, *self.candidate_output_hashes):
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("disagreement_operator_hash_invalid")
        if self.receipt_hash != _hash_payload(self._committed_dict()):
            raise ValueError("disagreement_operator_commitment_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "receipt_hash": self.receipt_hash}


def calibrate_disagreement_operator(
    *,
    truths: dict[str, str],
    evidence_refs: tuple[str, ...],
    truth_commitment: str,
    experiment_id: str,
    source_report_hash: str,
    route_decisions: tuple[dict[str, Any], ...],
    majority_answer_vector: dict[str, str],
    solo_answer_vectors: tuple[dict[str, str], ...],
    item_domains: dict[str, str],
) -> DisagreementOperatorReceipt:
    if not re.fullmatch(r"[0-9a-f]{64}", source_report_hash) or set(item_domains) != set(truths):
        raise ValueError("disagreement_operator_source_invalid")
    primary = {item.get("item_id"): str(item.get("primary_answer", "")).strip().upper() for item in route_decisions}
    majority = {key: str(value).strip().upper() for key, value in majority_answer_vector.items()}
    solos = tuple({key: str(value).strip().upper() for key, value in item.items()} for item in solo_answer_vectors)
    if set(primary) != set(truths) or set(majority) != set(truths) or len(solos) < 2 or any(set(item) != set(truths) for item in solos):
        raise ValueError("disagreement_operator_coverage_invalid")
    records = []
    for domain in sorted(set(item_domains.values())):
        ids = [item_id for item_id, value in item_domains.items() if value == domain]
        primary_correct = {item_id: primary[item_id] == truths[item_id] for item_id in ids}
        majority_correct = {item_id: majority[item_id] == truths[item_id] for item_id in ids}
        corrections = sum(not primary_correct[item_id] and majority_correct[item_id] for item_id in ids)
        harms = sum(primary_correct[item_id] and not majority_correct[item_id] for item_id in ids)
        correction_opportunities = sum(not value for value in primary_correct.values())
        harm_opportunities = sum(primary_correct.values())
        records.append(DomainDisagreementRecord(
            domain=domain, total=len(ids),
            disagreements=sum(len({item[item_id] for item in solos}) > 1 for item_id in ids),
            primary_correct=sum(primary_correct.values()), majority_correct=sum(majority_correct.values()),
            corrections=corrections, harms=harms,
            correction_opportunities=correction_opportunities, harm_opportunities=harm_opportunities,
            correction_posterior=round((corrections + 1) / (correction_opportunities + 2), 12),
            harm_posterior=round((harms + 1) / (harm_opportunities + 2), 12),
            observed_net_cbit=round((corrections - harms) / len(ids), 12),
        ))
    committed = {
        "experiment_id": experiment_id,
        "operator_id": "MAJORITY",
        "source_report_hash": source_report_hash,
        "candidate_output_hashes": [_hash_payload(item) for item in solos],
        "records": [item.as_dict() for item in records],
        "evidence_refs": list(evidence_refs),
        "truth_commitment": truth_commitment,
        "harness_owned": True,
        "routing_authority": False,
    }
    return DisagreementOperatorReceipt(
        **{
            **committed,
            "candidate_output_hashes": tuple(committed["candidate_output_hashes"]),
            "records": tuple(records), "evidence_refs": evidence_refs,
            "receipt_hash": _hash_payload(committed),
        }
    )
