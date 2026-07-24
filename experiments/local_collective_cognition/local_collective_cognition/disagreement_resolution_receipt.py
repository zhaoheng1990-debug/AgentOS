"""Harness-owned evidence for resolving paid primary-peer disagreements."""

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
class ResolutionEvidenceRecord:
    fingerprint: str
    disagreements: int
    primary_correct: int
    peer_correct: int
    peer_corrections: int
    peer_harms: int
    correction_opportunities: int
    harm_opportunities: int
    prediction_count: int = 0
    mean_predicted_override_net: float = 0.0
    mean_observed_override_net: float = 0.0
    mean_absolute_error: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class DisagreementResolutionEvidenceReceipt:
    experiment_id: str
    source_report_hash: str
    source_operator_credit_hash: str
    disagreement_candidate_hash: str
    records: tuple[ResolutionEvidenceRecord, ...]
    evidence_refs: tuple[str, ...]
    truth_commitment: str
    receipt_hash: str
    harness_owned: bool = True
    routing_authority: bool = False

    def _committed_dict(self) -> dict[str, Any]:
        return {
            **{key: value for key, value in self.__dict__.items() if key not in {"records", "evidence_refs", "receipt_hash"}},
            "records": [item.as_dict() for item in self.records],
            "evidence_refs": list(self.evidence_refs),
        }

    def __post_init__(self) -> None:
        hashes = (
            self.source_report_hash, self.source_operator_credit_hash,
            self.disagreement_candidate_hash, self.truth_commitment, self.receipt_hash,
        )
        if not self.harness_owned or self.routing_authority or any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes):
            raise ValueError("resolution_evidence_authority_invalid")
        if not self.records or self.receipt_hash != _hash_payload(self._committed_dict()):
            raise ValueError("resolution_evidence_commitment_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "receipt_hash": self.receipt_hash}


def calibrate_disagreement_resolution(
    *,
    truths: dict[str, str],
    evidence_refs: tuple[str, ...],
    truth_commitment: str,
    experiment_id: str,
    source_report_hash: str,
    source_operator_credit_hash: str,
    route_decisions: tuple[dict[str, Any], ...],
    resolver_peer_answer_by_item: dict[str, str],
    item_fingerprints: dict[str, str],
    source_actions: tuple[str, ...] = ("PEER_VERIFICATION_RESOLVED",),
) -> DisagreementResolutionEvidenceReceipt:
    if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in (source_report_hash, source_operator_credit_hash)):
        raise ValueError("resolution_evidence_source_hash_invalid")
    if set(item_fingerprints) != set(truths):
        raise ValueError("resolution_evidence_scope_invalid")
    routes = {item["item_id"]: item for item in route_decisions if item.get("action") in source_actions}
    peers = {item_id: str(answer).strip().upper() for item_id, answer in resolver_peer_answer_by_item.items()}
    if not routes or set(routes) != set(peers) or not set(routes).issubset(truths):
        raise ValueError("resolution_evidence_route_coverage_invalid")
    disagreements = []
    for item_id, route in routes.items():
        primary = str(route.get("primary_answer", "")).strip().upper()
        peer = peers[item_id]
        if primary != peer:
            predicted = route.get("resolution_expected_net_cbit")
            disagreements.append((
                item_id, primary, peer,
                float(predicted) if isinstance(predicted, (int, float)) else None,
            ))
    if not disagreements:
        raise ValueError("resolution_evidence_disagreement_missing")
    records = []
    for fingerprint in sorted({item_fingerprints[item_id] for item_id, _, _, _ in disagreements}):
        selected = [item for item in disagreements if item_fingerprints[item[0]] == fingerprint]
        primary_hits = [primary == truths[item_id] for item_id, primary, _, _ in selected]
        peer_hits = [peer == truths[item_id] for item_id, _, peer, _ in selected]
        predictions = [item[3] for item in selected if item[3] is not None]
        observed = [float(peer) - float(primary) for primary, peer in zip(primary_hits, peer_hits)]
        predicted_observed = [actual for item, actual in zip(selected, observed) if item[3] is not None]
        errors = [abs(predicted - actual) for predicted, actual in zip(predictions, predicted_observed)]
        records.append(ResolutionEvidenceRecord(
            fingerprint=fingerprint, disagreements=len(selected),
            primary_correct=sum(primary_hits), peer_correct=sum(peer_hits),
            peer_corrections=sum(not primary and peer for primary, peer in zip(primary_hits, peer_hits)),
            peer_harms=sum(primary and not peer for primary, peer in zip(primary_hits, peer_hits)),
            correction_opportunities=sum(not value for value in primary_hits),
            harm_opportunities=sum(primary_hits),
            prediction_count=len(predictions),
            mean_predicted_override_net=round(sum(predictions) / len(predictions), 12) if predictions else 0.0,
            mean_observed_override_net=round(
                sum(predicted_observed) / len(predicted_observed), 12
            ) if predicted_observed else round(sum(observed) / len(observed), 12),
            mean_absolute_error=round(sum(errors) / len(errors), 12) if errors else 0.0,
        ))
    candidate_hash = _hash_payload(sorted(disagreements))
    committed = {
        "experiment_id": experiment_id, "source_report_hash": source_report_hash,
        "source_operator_credit_hash": source_operator_credit_hash,
        "disagreement_candidate_hash": candidate_hash,
        "records": [item.as_dict() for item in records], "evidence_refs": list(evidence_refs),
        "truth_commitment": truth_commitment, "harness_owned": True, "routing_authority": False,
    }
    return DisagreementResolutionEvidenceReceipt(
        **{**committed, "records": tuple(records), "evidence_refs": evidence_refs,
           "receipt_hash": _hash_payload(committed)}
    )
