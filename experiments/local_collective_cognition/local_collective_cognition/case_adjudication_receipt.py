"""Harness-owned outcomes for current-case disagreement adjudication."""

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
class CaseAdjudicationOutcomeRecord:
    item_id: str
    fingerprint: str
    primary_model_id: str
    peer_model_id: str
    judge_model_id: str
    support_topology: str
    selected_candidate: str
    adjudicability: str
    confidence: float
    actual_outcome: str
    peer_counterfactual_outcome: str

    def __post_init__(self) -> None:
        if self.support_topology not in {"THIRD_SUPPORTS_PRIMARY", "THIRD_SUPPORTS_PEER", "ALL_DIFFER"}:
            raise ValueError("case_adjudication_topology_invalid")
        if self.selected_candidate not in {"CANDIDATE_1", "CANDIDATE_2", "ABSTAIN"}:
            raise ValueError("case_adjudication_selection_invalid")
        if self.adjudicability not in {"ADJUDICABLE", "AMBIGUOUS", "PROVIDER_FAILED"}:
            raise ValueError("case_adjudication_state_invalid")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("case_adjudication_confidence_invalid")
        if self.actual_outcome not in {"CORRECTION", "HARM", "NO_EFFECT"}:
            raise ValueError("case_adjudication_actual_outcome_invalid")
        if self.peer_counterfactual_outcome not in {"CORRECTION", "HARM", "NO_EFFECT"}:
            raise ValueError("case_adjudication_counterfactual_invalid")

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class CaseAdjudicationEvidenceReceipt:
    experiment_id: str
    calibration_receipt_hash: str
    case_candidate_hash: str
    benchmark_total: int
    records: tuple[CaseAdjudicationOutcomeRecord, ...]
    evidence_refs: tuple[str, ...]
    truth_commitment: str
    receipt_hash: str
    harness_owned: bool = True
    routing_authority: bool = False

    @property
    def corrections(self) -> int:
        return sum(item.actual_outcome == "CORRECTION" for item in self.records)

    @property
    def harms(self) -> int:
        return sum(item.actual_outcome == "HARM" for item in self.records)

    @property
    def observed_net_cbit(self) -> float:
        return round((self.corrections - self.harms) / self.benchmark_total, 12)

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "calibration_receipt_hash": self.calibration_receipt_hash,
            "case_candidate_hash": self.case_candidate_hash,
            "benchmark_total": self.benchmark_total,
            "records": [item.as_dict() for item in self.records],
            "evidence_refs": list(self.evidence_refs),
            "truth_commitment": self.truth_commitment,
            "harness_owned": self.harness_owned,
            "routing_authority": self.routing_authority,
        }

    def __post_init__(self) -> None:
        hashes = (self.calibration_receipt_hash, self.case_candidate_hash, self.truth_commitment)
        if self.benchmark_total < 1 or not self.harness_owned or self.routing_authority or any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in hashes):
            raise ValueError("case_adjudication_receipt_authority_invalid")
        if self.receipt_hash != _hash_payload(self._committed_dict()):
            raise ValueError("case_adjudication_receipt_commitment_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._committed_dict(), "corrections": self.corrections,
            "harms": self.harms, "observed_net_cbit": self.observed_net_cbit,
            "receipt_hash": self.receipt_hash,
        }


def calibrate_case_adjudication(
    *, truths: dict[str, str], evidence_refs: tuple[str, ...], truth_commitment: str,
    experiment_id: str, calibration_receipt_hash: str,
    route_decisions: tuple[dict[str, Any], ...], solo_answer_vectors: dict[str, dict[str, str]],
    item_fingerprints: dict[str, str], case_adjudication_source_actions: tuple[str, ...],
) -> CaseAdjudicationEvidenceReceipt:
    if not re.fullmatch(r"[0-9a-f]{64}", calibration_receipt_hash):
        raise ValueError("case_adjudication_calibration_hash_invalid")
    if set(item_fingerprints) != set(truths) or len(solo_answer_vectors) != 3:
        raise ValueError("case_adjudication_scope_invalid")
    records, commitments = [], []
    for route in route_decisions:
        if route.get("action") not in case_adjudication_source_actions or not route.get("case_adjudication_used"):
            continue
        item_id = route["item_id"]
        primary_id, peer_id = route["primary_model_id"], route["reviewer_model_id"]
        primary = str(route["primary_answer"]).strip().upper()
        peer = str(solo_answer_vectors[peer_id][item_id]).strip().upper()
        final = str(route["final_answer"]).strip().upper()
        truth = truths[item_id]
        records.append(CaseAdjudicationOutcomeRecord(
            item_id=item_id, fingerprint=item_fingerprints[item_id],
            primary_model_id=primary_id, peer_model_id=peer_id,
            judge_model_id=route["case_judge_model_id"],
            support_topology=route["context_support_topology"],
            selected_candidate=route["case_selected_candidate"],
            adjudicability=route["case_adjudicability"], confidence=float(route["case_confidence"]),
            actual_outcome=_outcome(primary, final, truth),
            peer_counterfactual_outcome=_outcome(primary, peer, truth),
        ))
        commitments.append((
            item_id, primary_id, peer_id, route["case_judge_model_id"],
            route["case_argument_hashes"], route["case_judgment_hash"], primary, peer, final,
        ))
    committed = {
        "experiment_id": experiment_id, "calibration_receipt_hash": calibration_receipt_hash,
        "case_candidate_hash": _hash_payload(commitments),
        "benchmark_total": len(truths),
        "records": [item.as_dict() for item in records], "evidence_refs": list(evidence_refs),
        "truth_commitment": truth_commitment, "harness_owned": True, "routing_authority": False,
    }
    return CaseAdjudicationEvidenceReceipt(
        **{**committed, "records": tuple(records), "evidence_refs": evidence_refs,
           "receipt_hash": _hash_payload(committed)}
    )


def _outcome(primary: str, candidate: str, truth: str) -> str:
    if candidate == truth and primary != truth:
        return "CORRECTION"
    if primary == truth and candidate != truth:
        return "HARM"
    return "NO_EFFECT"
