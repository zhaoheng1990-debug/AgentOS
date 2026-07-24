"""Candidate, promotion, and hierarchical credit for disagreement resolution."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .disagreement_resolution_receipt import DisagreementResolutionEvidenceReceipt
from .task_fingerprints import FINGERPRINT_TO_DOMAIN


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ResolutionEvidenceCandidate:
    source_receipt_hash: str
    source_report_hash: str
    candidate_hash: str
    candidate_only: bool = True
    routing_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class ResolutionPromotionReceipt:
    candidate_hash: str
    validation_ref: str
    status: str
    receipt_hash: str
    experiment_only: bool = True
    core_baseline_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class ResolutionCredit:
    fingerprint: str
    domain: str
    correction_posterior: float
    harm_posterior: float
    expected_override_net_cbit: float
    effective_disagreements: int
    evidence_level: str

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class ResolutionCreditSnapshot:
    source_receipt_hash: str
    promotion_receipt_hash: str
    records: tuple[ResolutionCredit, ...]
    snapshot_hash: str
    experiment_only: bool = True
    core_baseline_authority: bool = False

    def get(self, fingerprint: str) -> ResolutionCredit:
        try:
            return next(item for item in self.records if item.fingerprint == fingerprint)
        except StopIteration as exc:
            raise ValueError("resolution_credit_missing") from exc

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "source_receipt_hash": self.source_receipt_hash,
            "promotion_receipt_hash": self.promotion_receipt_hash,
            "records": [item.as_dict() for item in self.records],
            "experiment_only": self.experiment_only,
            "core_baseline_authority": self.core_baseline_authority,
        }

    def __post_init__(self) -> None:
        if self.snapshot_hash != _hash_payload(self._committed_dict()):
            raise ValueError("resolution_credit_snapshot_commitment_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "snapshot_hash": self.snapshot_hash}


class DisagreementResolutionLifecycle:
    def __init__(self, *, receipt: DisagreementResolutionEvidenceReceipt) -> None:
        self.receipt = receipt
        self.candidate: ResolutionEvidenceCandidate | None = None
        self.promotion: ResolutionPromotionReceipt | None = None

    def ingest_candidate(self) -> ResolutionEvidenceCandidate:
        committed = {
            "source_receipt_hash": self.receipt.receipt_hash,
            "source_report_hash": self.receipt.source_report_hash,
            "candidate_only": True,
            "routing_authority": False,
        }
        self.candidate = ResolutionEvidenceCandidate(**committed, candidate_hash=_hash_payload(committed))
        return self.candidate

    def promote(self, *, candidate_hash: str, validation_ref: str) -> ResolutionPromotionReceipt:
        if self.candidate is None or candidate_hash != self.candidate.candidate_hash or not re.fullmatch(r"[0-9a-f]{64}", validation_ref):
            raise ValueError("resolution_promotion_binding_invalid")
        committed = {
            "candidate_hash": candidate_hash, "validation_ref": validation_ref,
            "status": "PROMOTED_FOR_EXPERIMENT", "experiment_only": True,
            "core_baseline_authority": False,
        }
        self.promotion = ResolutionPromotionReceipt(**committed, receipt_hash=_hash_payload(committed))
        return self.promotion

    def snapshot(self, *, domain_strength: float = 3.0, fingerprint_strength: float = 2.0) -> ResolutionCreditSnapshot:
        if self.candidate is None or self.promotion is None:
            raise ValueError("resolution_snapshot_promotion_required")
        records = {item.fingerprint: item for item in self.receipt.records}
        global_values = _aggregate(tuple(records.values()))
        global_correction = _posterior(global_values[0], global_values[1], 0.5, 2.0)
        global_harm = _posterior(global_values[2], global_values[3], 0.5, 2.0)
        domain_values = {}
        for domain in sorted(set(FINGERPRINT_TO_DOMAIN.values())):
            selected = tuple(item for name, item in records.items() if FINGERPRINT_TO_DOMAIN[name] == domain)
            values = _aggregate(selected)
            domain_values[domain] = (
                _posterior(values[0], values[1], global_correction, domain_strength),
                _posterior(values[2], values[3], global_harm, domain_strength),
                sum(item.disagreements for item in selected),
            )
        credits = []
        for fingerprint, domain in sorted(FINGERPRINT_TO_DOMAIN.items()):
            record = records.get(fingerprint)
            values = _aggregate((record,) if record else ())
            domain_correction, domain_harm, domain_total = domain_values[domain]
            correction = _posterior(values[0], values[1], domain_correction, fingerprint_strength)
            harm = _posterior(values[2], values[3], domain_harm, fingerprint_strength)
            evidence_level = "FINGERPRINT" if record else "DOMAIN" if domain_total else "GLOBAL"
            credits.append(ResolutionCredit(
                fingerprint=fingerprint, domain=domain,
                correction_posterior=correction, harm_posterior=harm,
                expected_override_net_cbit=round(correction - harm, 12),
                effective_disagreements=record.disagreements if record else 0,
                evidence_level=evidence_level,
            ))
        committed = {
            "source_receipt_hash": self.receipt.receipt_hash,
            "promotion_receipt_hash": self.promotion.receipt_hash,
            "records": [item.as_dict() for item in credits],
            "experiment_only": True, "core_baseline_authority": False,
        }
        return ResolutionCreditSnapshot(
            source_receipt_hash=self.receipt.receipt_hash,
            promotion_receipt_hash=self.promotion.receipt_hash,
            records=tuple(credits), snapshot_hash=_hash_payload(committed),
        )


def _aggregate(records) -> tuple[int, int, int, int]:
    return (
        sum(item.peer_corrections for item in records),
        sum(item.correction_opportunities for item in records),
        sum(item.peer_harms for item in records),
        sum(item.harm_opportunities for item in records),
    )


def _posterior(successes: float, total: float, prior: float, strength: float) -> float:
    return round((successes + strength * prior) / (total + strength), 12)
