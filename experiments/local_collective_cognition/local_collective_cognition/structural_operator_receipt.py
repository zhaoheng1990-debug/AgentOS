"""Harness-owned evidence for structural peer and majority operators."""

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
class StructuralOperatorEvidence:
    fingerprint: str
    total: int
    primary_correct: int
    peer_disagreements: int
    peer_corrections: int
    peer_harms: int
    peer_correction_opportunities: int
    peer_harm_opportunities: int
    majority_disagreements: int
    majority_corrections: int
    majority_harms: int
    majority_correction_opportunities: int
    majority_harm_opportunities: int

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class StructuralOperatorEvidenceReceipt:
    experiment_id: str
    source_report_hash: str
    source_profile_hash: str
    candidate_output_hashes: tuple[tuple[str, str], ...]
    records: tuple[StructuralOperatorEvidence, ...]
    evidence_refs: tuple[str, ...]
    truth_commitment: str
    receipt_hash: str
    harness_owned: bool = True
    routing_authority: bool = False

    def _committed_dict(self) -> dict[str, Any]:
        return {
            **{key: value for key, value in self.__dict__.items() if key not in {"candidate_output_hashes", "records", "evidence_refs", "receipt_hash"}},
            "candidate_output_hashes": [list(item) for item in self.candidate_output_hashes],
            "records": [item.as_dict() for item in self.records],
            "evidence_refs": list(self.evidence_refs),
        }

    def __post_init__(self) -> None:
        hashes = (self.source_report_hash, self.source_profile_hash, self.truth_commitment, self.receipt_hash)
        if not self.harness_owned or self.routing_authority or any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes):
            raise ValueError("structural_operator_receipt_authority_invalid")
        if len({item.fingerprint for item in self.records}) != len(self.records):
            raise ValueError("structural_operator_receipt_fingerprints_invalid")
        if self.receipt_hash != _hash_payload(self._committed_dict()):
            raise ValueError("structural_operator_receipt_commitment_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "receipt_hash": self.receipt_hash}


def calibrate_structural_operators(
    *,
    truths: dict[str, str],
    evidence_refs: tuple[str, ...],
    truth_commitment: str,
    experiment_id: str,
    source_report_hash: str,
    source_profile_hash: str,
    route_decisions: tuple[dict[str, Any], ...],
    second_model_by_item: dict[str, str],
    majority_answer_vector: dict[str, str],
    solo_answer_vectors: dict[str, dict[str, str]],
    item_fingerprints: dict[str, str],
) -> StructuralOperatorEvidenceReceipt:
    if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in (source_report_hash, source_profile_hash)):
        raise ValueError("structural_operator_source_hash_invalid")
    if set(item_fingerprints) != set(truths) or set(second_model_by_item) != set(truths):
        raise ValueError("structural_operator_source_coverage_invalid")
    solos = {
        model_id: {item_id: str(answer).strip().upper() for item_id, answer in answers.items()}
        for model_id, answers in solo_answer_vectors.items()
    }
    if len(solos) < 3 or any(set(answers) != set(truths) for answers in solos.values()):
        raise ValueError("structural_operator_solo_coverage_invalid")
    routes = {item["item_id"]: item for item in route_decisions}
    majority = {item_id: str(answer).strip().upper() for item_id, answer in majority_answer_vector.items()}
    if set(routes) != set(truths) or set(majority) != set(truths):
        raise ValueError("structural_operator_route_coverage_invalid")
    records = []
    for fingerprint in sorted(set(item_fingerprints.values())):
        ids = [item_id for item_id, value in item_fingerprints.items() if value == fingerprint]
        primary_correct = 0
        peer_disagreements = majority_disagreements = 0
        peer_corrections = peer_harms = majority_corrections = majority_harms = 0
        for item_id in ids:
            route = routes[item_id]
            primary_model = route["primary_model_id"]
            second_model = second_model_by_item[item_id]
            if primary_model not in solos or second_model not in solos or primary_model == second_model:
                raise ValueError("structural_operator_model_binding_invalid")
            primary = str(route["primary_answer"]).strip().upper()
            peer = solos[second_model][item_id]
            if primary != solos[primary_model][item_id]:
                raise ValueError("structural_operator_primary_answer_binding_invalid")
            truth = truths[item_id]
            primary_hit, peer_hit, majority_hit = primary == truth, peer == truth, majority[item_id] == truth
            primary_correct += primary_hit
            peer_disagreements += peer != primary
            majority_disagreements += majority[item_id] != primary
            peer_corrections += not primary_hit and peer_hit
            peer_harms += primary_hit and not peer_hit
            majority_corrections += not primary_hit and majority_hit
            majority_harms += primary_hit and not majority_hit
        records.append(StructuralOperatorEvidence(
            fingerprint=fingerprint, total=len(ids), primary_correct=primary_correct,
            peer_disagreements=peer_disagreements, peer_corrections=peer_corrections, peer_harms=peer_harms,
            peer_correction_opportunities=len(ids) - primary_correct, peer_harm_opportunities=primary_correct,
            majority_disagreements=majority_disagreements, majority_corrections=majority_corrections,
            majority_harms=majority_harms, majority_correction_opportunities=len(ids) - primary_correct,
            majority_harm_opportunities=primary_correct,
        ))
    candidate_hashes = tuple(sorted((model_id, _hash_payload(answers)) for model_id, answers in solos.items()))
    committed = {
        "experiment_id": experiment_id, "source_report_hash": source_report_hash,
        "source_profile_hash": source_profile_hash,
        "candidate_output_hashes": [list(item) for item in candidate_hashes],
        "records": [item.as_dict() for item in records], "evidence_refs": list(evidence_refs),
        "truth_commitment": truth_commitment, "harness_owned": True, "routing_authority": False,
    }
    return StructuralOperatorEvidenceReceipt(
        **{**committed, "candidate_output_hashes": candidate_hashes, "records": tuple(records),
           "evidence_refs": evidence_refs, "receipt_hash": _hash_payload(committed)}
    )
