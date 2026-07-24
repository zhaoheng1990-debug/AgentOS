"""Promoted multi-cycle evidence and calibrated disagreement-resolution credit."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .disagreement_resolution_lifecycle import (
    ResolutionCredit,
    ResolutionEvidenceCandidate,
    ResolutionPromotionReceipt,
)
from .disagreement_resolution_receipt import DisagreementResolutionEvidenceReceipt
from .task_fingerprints import FINGERPRINT_TO_DOMAIN


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class MultiCycleResolutionCreditSnapshot:
    source_receipt_hashes: tuple[str, ...]
    promotion_receipt_hashes: tuple[str, ...]
    records: tuple[ResolutionCredit, ...]
    prediction_count: int
    mean_predicted_override_net: float
    mean_observed_override_net: float
    mean_absolute_error: float
    snapshot_hash: str
    experiment_only: bool = True
    core_baseline_authority: bool = False

    def get(self, fingerprint: str) -> ResolutionCredit:
        try:
            return next(item for item in self.records if item.fingerprint == fingerprint)
        except StopIteration as exc:
            raise ValueError("multi_cycle_resolution_credit_missing") from exc

    def _committed_dict(self) -> dict[str, Any]:
        return {
            **{key: value for key, value in self.__dict__.items() if key not in {
                "source_receipt_hashes", "promotion_receipt_hashes", "records", "snapshot_hash",
            }},
            "source_receipt_hashes": list(self.source_receipt_hashes),
            "promotion_receipt_hashes": list(self.promotion_receipt_hashes),
            "records": [item.as_dict() for item in self.records],
        }

    def __post_init__(self) -> None:
        if self.snapshot_hash != _hash_payload(self._committed_dict()):
            raise ValueError("multi_cycle_resolution_snapshot_commitment_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "snapshot_hash": self.snapshot_hash}


class MultiCycleResolutionLifecycle:
    def __init__(self) -> None:
        self._receipts: dict[str, DisagreementResolutionEvidenceReceipt] = {}
        self._candidates: dict[str, ResolutionEvidenceCandidate] = {}
        self._promotions: dict[str, ResolutionPromotionReceipt] = {}

    def ingest_candidate(self, receipt: DisagreementResolutionEvidenceReceipt) -> ResolutionEvidenceCandidate:
        if receipt.receipt_hash in self._receipts:
            raise ValueError("multi_cycle_resolution_receipt_duplicate")
        committed = {
            "source_receipt_hash": receipt.receipt_hash,
            "source_report_hash": receipt.source_report_hash,
            "candidate_only": True,
            "routing_authority": False,
        }
        candidate = ResolutionEvidenceCandidate(**committed, candidate_hash=_hash_payload(committed))
        self._receipts[receipt.receipt_hash] = receipt
        self._candidates[candidate.candidate_hash] = candidate
        return candidate

    def promote(self, *, candidate_hash: str, validation_ref: str) -> ResolutionPromotionReceipt:
        candidate = self._candidates.get(candidate_hash)
        if candidate is None or not re.fullmatch(r"[0-9a-f]{64}", validation_ref):
            raise ValueError("multi_cycle_resolution_promotion_binding_invalid")
        if candidate_hash in self._promotions:
            raise ValueError("multi_cycle_resolution_promotion_duplicate")
        committed = {
            "candidate_hash": candidate_hash,
            "validation_ref": validation_ref,
            "status": "PROMOTED_FOR_EXPERIMENT",
            "experiment_only": True,
            "core_baseline_authority": False,
        }
        promotion = ResolutionPromotionReceipt(**committed, receipt_hash=_hash_payload(committed))
        self._promotions[candidate_hash] = promotion
        return promotion

    def snapshot(self) -> MultiCycleResolutionCreditSnapshot:
        if not self._receipts or set(self._candidates) != set(self._promotions):
            raise ValueError("multi_cycle_resolution_promotions_incomplete")
        receipts = tuple(self._receipts.values())
        records = _build_credit(receipts)
        predictions = [
            (item.prediction_count, item.mean_predicted_override_net,
             item.mean_observed_override_net, item.mean_absolute_error)
            for receipt in receipts for item in receipt.records if item.prediction_count
        ]
        prediction_count = sum(item[0] for item in predictions)
        weighted = lambda index: round(sum(count * item[index] for count, *item in predictions) / prediction_count, 12) if prediction_count else 0.0
        committed = {
            "source_receipt_hashes": [item.receipt_hash for item in receipts],
            "promotion_receipt_hashes": [item.receipt_hash for item in self._promotions.values()],
            "records": [item.as_dict() for item in records],
            "prediction_count": prediction_count,
            "mean_predicted_override_net": weighted(0),
            "mean_observed_override_net": weighted(1),
            "mean_absolute_error": weighted(2),
            "experiment_only": True,
            "core_baseline_authority": False,
        }
        return MultiCycleResolutionCreditSnapshot(
            **{**committed,
               "source_receipt_hashes": tuple(committed["source_receipt_hashes"]),
               "promotion_receipt_hashes": tuple(committed["promotion_receipt_hashes"]),
               "records": records, "snapshot_hash": _hash_payload(committed)}
        )


def _build_credit(receipts) -> tuple[ResolutionCredit, ...]:
    by_fingerprint = {
        name: tuple(item for receipt in receipts for item in receipt.records if item.fingerprint == name)
        for name in FINGERPRINT_TO_DOMAIN
    }
    global_values = _aggregate(tuple(item for records in by_fingerprint.values() for item in records))
    global_correction = _posterior(global_values[0], global_values[1], 0.5, 2.0)
    global_harm = _posterior(global_values[2], global_values[3], 0.5, 2.0)
    domain_values = {}
    for domain in set(FINGERPRINT_TO_DOMAIN.values()):
        selected = tuple(item for name, records in by_fingerprint.items() if FINGERPRINT_TO_DOMAIN[name] == domain for item in records)
        values = _aggregate(selected)
        domain_values[domain] = (_posterior(values[0], values[1], global_correction, 3.0), _posterior(values[2], values[3], global_harm, 3.0), sum(item.disagreements for item in selected))
    credits = []
    for fingerprint, domain in sorted(FINGERPRINT_TO_DOMAIN.items()):
        selected = by_fingerprint[fingerprint]
        values = _aggregate(selected)
        domain_correction, domain_harm, domain_total = domain_values[domain]
        correction = _posterior(values[0], values[1], domain_correction, 2.0)
        harm = _posterior(values[2], values[3], domain_harm, 2.0)
        credits.append(ResolutionCredit(
            fingerprint=fingerprint, domain=domain, correction_posterior=correction,
            harm_posterior=harm, expected_override_net_cbit=round(correction - harm, 12),
            effective_disagreements=sum(item.disagreements for item in selected),
            evidence_level="FINGERPRINT" if selected else "DOMAIN" if domain_total else "GLOBAL",
        ))
    return tuple(credits)


def _aggregate(records) -> tuple[int, int, int, int]:
    return tuple(sum(getattr(item, name) for item in records) for name in (
        "peer_corrections", "correction_opportunities", "peer_harms", "harm_opportunities",
    ))


def _posterior(successes: float, total: float, prior: float, strength: float) -> float:
    return round((successes + strength * prior) / (total + strength), 12)
