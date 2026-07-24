"""Promoted pair, topology, and fingerprint credit for disagreement context."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .context_resolution_receipt import ContextOutcomeRecord, ContextResolutionEvidenceReceipt
from .disagreement_resolution_lifecycle import ResolutionEvidenceCandidate, ResolutionPromotionReceipt


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ContextFeatureCredit:
    feature_type: str
    feature_key: str
    corrections: int
    harms: int
    no_effects: int
    correction_posterior: float
    harm_posterior: float
    expected_net_cbit: float

    @property
    def total(self) -> int:
        return self.corrections + self.harms + self.no_effects

    def as_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "total": self.total}


@dataclass(frozen=True)
class ContextResolutionSignal:
    fingerprint: str
    pair_key: str
    support_topology: str
    pair_expected_net: float
    topology_expected_net: float
    fingerprint_expected_net: float
    expected_net_cbit: float
    pair_correction_surplus: int
    pair_evidence_count: int
    override_evidence_eligible: bool

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class ContextResolutionCreditSnapshot:
    source_receipt_hashes: tuple[str, ...]
    promotion_receipt_hashes: tuple[str, ...]
    global_credit: ContextFeatureCredit
    pair_credits: tuple[ContextFeatureCredit, ...]
    topology_credits: tuple[ContextFeatureCredit, ...]
    fingerprint_credits: tuple[ContextFeatureCredit, ...]
    snapshot_hash: str
    experiment_only: bool = True
    core_baseline_authority: bool = False

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "source_receipt_hashes": list(self.source_receipt_hashes),
            "promotion_receipt_hashes": list(self.promotion_receipt_hashes),
            "global_credit": self.global_credit.as_dict(),
            "pair_credits": [item.as_dict() for item in self.pair_credits],
            "topology_credits": [item.as_dict() for item in self.topology_credits],
            "fingerprint_credits": [item.as_dict() for item in self.fingerprint_credits],
            "experiment_only": self.experiment_only,
            "core_baseline_authority": self.core_baseline_authority,
        }

    def __post_init__(self) -> None:
        if self.snapshot_hash != _hash_payload(self._committed_dict()):
            raise ValueError("context_resolution_snapshot_commitment_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "snapshot_hash": self.snapshot_hash}

    def pair_credit(self, primary_model_id: str, peer_model_id: str) -> ContextFeatureCredit:
        return _find(self.pair_credits, f"{primary_model_id}->{peer_model_id}", self.global_credit)

    def resolve(self, *, fingerprint: str, primary_model_id: str, peer_model_id: str, support_topology: str) -> ContextResolutionSignal:
        pair_key = f"{primary_model_id}->{peer_model_id}"
        pair = self.pair_credit(primary_model_id, peer_model_id)
        topology = _find(self.topology_credits, support_topology, self.global_credit)
        fingerprint_credit = _find(self.fingerprint_credits, fingerprint, self.global_credit)
        expected = round(
            0.60 * pair.expected_net_cbit
            + 0.25 * topology.expected_net_cbit
            + 0.15 * fingerprint_credit.expected_net_cbit,
            12,
        )
        surplus = pair.corrections - pair.harms
        return ContextResolutionSignal(
            fingerprint=fingerprint, pair_key=pair_key, support_topology=support_topology,
            pair_expected_net=pair.expected_net_cbit,
            topology_expected_net=topology.expected_net_cbit,
            fingerprint_expected_net=fingerprint_credit.expected_net_cbit,
            expected_net_cbit=expected, pair_correction_surplus=surplus,
            pair_evidence_count=pair.total if pair.feature_type == "PAIR" else 0,
            override_evidence_eligible=pair.feature_type == "PAIR" and pair.corrections >= 1 and surplus > 0,
        )


class ContextResolutionLifecycle:
    def __init__(self) -> None:
        self._receipts = {}
        self._candidates = {}
        self._promotions = {}

    def ingest_candidate(self, receipt: ContextResolutionEvidenceReceipt) -> ResolutionEvidenceCandidate:
        if receipt.receipt_hash in self._receipts:
            raise ValueError("context_resolution_receipt_duplicate")
        committed = {
            "source_receipt_hash": receipt.receipt_hash,
            "source_report_hash": receipt.source_report_hash,
            "candidate_only": True, "routing_authority": False,
        }
        candidate = ResolutionEvidenceCandidate(**committed, candidate_hash=_hash_payload(committed))
        self._receipts[receipt.receipt_hash] = receipt
        self._candidates[candidate.candidate_hash] = candidate
        return candidate

    def promote(self, *, candidate_hash: str, validation_ref: str) -> ResolutionPromotionReceipt:
        if candidate_hash not in self._candidates or candidate_hash in self._promotions or not re.fullmatch(r"[0-9a-f]{64}", validation_ref):
            raise ValueError("context_resolution_promotion_binding_invalid")
        committed = {
            "candidate_hash": candidate_hash, "validation_ref": validation_ref,
            "status": "PROMOTED_FOR_EXPERIMENT", "experiment_only": True,
            "core_baseline_authority": False,
        }
        promotion = ResolutionPromotionReceipt(**committed, receipt_hash=_hash_payload(committed))
        self._promotions[candidate_hash] = promotion
        return promotion

    def snapshot(self) -> ContextResolutionCreditSnapshot:
        if not self._receipts or set(self._candidates) != set(self._promotions):
            raise ValueError("context_resolution_promotions_incomplete")
        records = tuple(item for receipt in self._receipts.values() for item in receipt.records)
        global_credit = _credit("GLOBAL", "ALL", records, None)
        pair_credits = _grouped_credit("PAIR", records, lambda item: f"{item.primary_model_id}->{item.peer_model_id}", global_credit)
        topology_credits = _grouped_credit("TOPOLOGY", records, lambda item: item.support_topology, global_credit)
        fingerprint_credits = _grouped_credit("FINGERPRINT", records, lambda item: item.fingerprint, global_credit)
        committed = {
            "source_receipt_hashes": list(self._receipts),
            "promotion_receipt_hashes": [item.receipt_hash for item in self._promotions.values()],
            "global_credit": global_credit.as_dict(),
            "pair_credits": [item.as_dict() for item in pair_credits],
            "topology_credits": [item.as_dict() for item in topology_credits],
            "fingerprint_credits": [item.as_dict() for item in fingerprint_credits],
            "experiment_only": True, "core_baseline_authority": False,
        }
        return ContextResolutionCreditSnapshot(
            **{**committed,
               "source_receipt_hashes": tuple(committed["source_receipt_hashes"]),
               "promotion_receipt_hashes": tuple(committed["promotion_receipt_hashes"]),
               "global_credit": global_credit, "pair_credits": pair_credits,
               "topology_credits": topology_credits, "fingerprint_credits": fingerprint_credits,
               "snapshot_hash": _hash_payload(committed)}
        )


def _grouped_credit(feature_type, records, key_fn, global_credit):
    keys = sorted({key_fn(item) for item in records})
    return tuple(_credit(feature_type, key, tuple(item for item in records if key_fn(item) == key), global_credit) for key in keys)


def _credit(feature_type: str, key: str, records: tuple[ContextOutcomeRecord, ...], prior) -> ContextFeatureCredit:
    corrections = sum(item.outcome == "CORRECTION" for item in records)
    harms = sum(item.outcome == "HARM" for item in records)
    no_effects = len(records) - corrections - harms
    if prior is None:
        correction = round((corrections + 1.0) / (len(records) + 3.0), 12)
        harm = round((harms + 1.0) / (len(records) + 3.0), 12)
    else:
        correction = round((corrections + 3.0 * prior.correction_posterior) / (len(records) + 3.0), 12)
        harm = round((harms + 3.0 * prior.harm_posterior) / (len(records) + 3.0), 12)
    return ContextFeatureCredit(
        feature_type=feature_type, feature_key=key, corrections=corrections, harms=harms,
        no_effects=no_effects, correction_posterior=correction, harm_posterior=harm,
        expected_net_cbit=round(correction - harm, 12),
    )


def _find(records, key, fallback):
    return next((item for item in records if item.feature_key == key), fallback)
