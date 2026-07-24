"""Harness-owned context evidence for primary-peer disagreement outcomes."""

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
class ContextOutcomeRecord:
    item_id: str
    fingerprint: str
    primary_model_id: str
    peer_model_id: str
    third_model_id: str
    support_topology: str
    outcome: str

    def __post_init__(self) -> None:
        if self.support_topology not in {"THIRD_SUPPORTS_PRIMARY", "THIRD_SUPPORTS_PEER", "ALL_DIFFER"}:
            raise ValueError("context_outcome_topology_invalid")
        if self.outcome not in {"CORRECTION", "HARM", "NO_EFFECT"}:
            raise ValueError("context_outcome_class_invalid")

    def as_dict(self) -> dict[str, str]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class ContextResolutionEvidenceReceipt:
    experiment_id: str
    source_report_hash: str
    source_credit_hash: str
    context_candidate_hash: str
    records: tuple[ContextOutcomeRecord, ...]
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
        hashes = (self.source_report_hash, self.source_credit_hash, self.context_candidate_hash, self.truth_commitment, self.receipt_hash)
        if not self.harness_owned or self.routing_authority or any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in hashes):
            raise ValueError("context_resolution_authority_invalid")
        if not self.records or self.receipt_hash != _hash_payload(self._committed_dict()):
            raise ValueError("context_resolution_commitment_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "receipt_hash": self.receipt_hash}


def calibrate_resolution_context(
    *,
    truths: dict[str, str],
    evidence_refs: tuple[str, ...],
    truth_commitment: str,
    experiment_id: str,
    source_report_hash: str,
    source_credit_hash: str,
    route_decisions: tuple[dict[str, Any], ...],
    solo_answer_vectors: dict[str, dict[str, str]],
    item_fingerprints: dict[str, str],
    context_source_actions: tuple[str, ...],
) -> ContextResolutionEvidenceReceipt:
    if any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in (source_report_hash, source_credit_hash)):
        raise ValueError("context_resolution_source_hash_invalid")
    if set(item_fingerprints) != set(truths) or len(solo_answer_vectors) != 3:
        raise ValueError("context_resolution_scope_invalid")
    records = []
    committed_answers = []
    for route in route_decisions:
        if route.get("action") not in context_source_actions:
            continue
        item_id = route["item_id"]
        primary_id = route["primary_model_id"]
        peer_id = route["reviewer_model_id"]
        third_ids = set(solo_answer_vectors) - {primary_id, peer_id}
        if item_id not in truths or len(third_ids) != 1:
            raise ValueError("context_resolution_route_binding_invalid")
        third_id = third_ids.pop()
        primary = str(route["primary_answer"]).strip().upper()
        peer = str(solo_answer_vectors[peer_id][item_id]).strip().upper()
        third = str(solo_answer_vectors[third_id][item_id]).strip().upper()
        if primary == peer:
            continue
        topology = "THIRD_SUPPORTS_PEER" if third == peer else "THIRD_SUPPORTS_PRIMARY" if third == primary else "ALL_DIFFER"
        truth = truths[item_id]
        outcome = "CORRECTION" if peer == truth and primary != truth else "HARM" if primary == truth and peer != truth else "NO_EFFECT"
        records.append(ContextOutcomeRecord(
            item_id=item_id, fingerprint=item_fingerprints[item_id],
            primary_model_id=primary_id, peer_model_id=peer_id, third_model_id=third_id,
            support_topology=topology, outcome=outcome,
        ))
        committed_answers.append((item_id, primary_id, peer_id, third_id, primary, peer, third))
    if not records:
        raise ValueError("context_resolution_disagreements_missing")
    committed = {
        "experiment_id": experiment_id, "source_report_hash": source_report_hash,
        "source_credit_hash": source_credit_hash,
        "context_candidate_hash": _hash_payload(sorted(committed_answers)),
        "records": [item.as_dict() for item in records], "evidence_refs": list(evidence_refs),
        "truth_commitment": truth_commitment, "harness_owned": True, "routing_authority": False,
    }
    return ContextResolutionEvidenceReceipt(
        **{**committed, "records": tuple(records), "evidence_refs": evidence_refs,
           "receipt_hash": _hash_payload(committed)}
    )
