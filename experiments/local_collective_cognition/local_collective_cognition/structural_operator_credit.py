"""Hierarchical operator credit with separate immediate and information value."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from math import sqrt
from typing import Any

from .structural_operator_receipt import StructuralOperatorEvidenceReceipt


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class StructuralOperatorCredit:
    fingerprint: str
    domain: str
    operator_id: str
    correction_posterior: float
    harm_posterior: float
    disagreement_posterior: float
    effective_observations: float
    future_information_cbit: float

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class StructuralOperatorCreditSnapshot:
    source_receipt_hash: str
    records: tuple[StructuralOperatorCredit, ...]
    snapshot_hash: str
    experiment_only: bool = True
    core_baseline_authority: bool = False

    def get(self, fingerprint: str, operator_id: str) -> StructuralOperatorCredit:
        try:
            return next(item for item in self.records if item.fingerprint == fingerprint and item.operator_id == operator_id)
        except StopIteration as exc:
            raise ValueError("structural_operator_credit_missing") from exc

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "source_receipt_hash": self.source_receipt_hash,
            "records": [item.as_dict() for item in self.records],
            "experiment_only": self.experiment_only,
            "core_baseline_authority": self.core_baseline_authority,
        }

    def __post_init__(self) -> None:
        if self.snapshot_hash != _hash_payload(self._committed_dict()):
            raise ValueError("structural_operator_credit_commitment_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "snapshot_hash": self.snapshot_hash}


def build_structural_operator_credit(
    *,
    receipt: StructuralOperatorEvidenceReceipt,
    fingerprint_domains: dict[str, str],
    domain_prior_strength: float = 3.0,
    fingerprint_prior_strength: float = 2.0,
) -> StructuralOperatorCreditSnapshot:
    if set(fingerprint_domains) != {item.fingerprint for item in receipt.records}:
        raise ValueError("structural_operator_credit_scope_invalid")
    credits = []
    for operator_id, prefix in (("PEER_SECOND", "peer"), ("MAJORITY", "majority")):
        global_values = _aggregate(receipt.records, prefix)
        global_correction = _posterior(global_values[0], global_values[1], 0.5, 2.0)
        global_harm = _posterior(global_values[2], global_values[3], 0.5, 2.0)
        global_disagreement = _posterior(global_values[4], global_values[5], 0.5, 2.0)
        domain_posteriors = {}
        for domain in sorted(set(fingerprint_domains.values())):
            selected = tuple(item for item in receipt.records if fingerprint_domains[item.fingerprint] == domain)
            values = _aggregate(selected, prefix)
            domain_posteriors[domain] = (
                _posterior(values[0], values[1], global_correction, domain_prior_strength),
                _posterior(values[2], values[3], global_harm, domain_prior_strength),
                _posterior(values[4], values[5], global_disagreement, domain_prior_strength),
            )
        for record in sorted(receipt.records, key=lambda item: item.fingerprint):
            domain = fingerprint_domains[record.fingerprint]
            correction, correction_total, harm, harm_total, disagreements, total = _aggregate((record,), prefix)
            domain_correction, domain_harm, domain_disagreement = domain_posteriors[domain]
            correction_posterior = _posterior(correction, correction_total, domain_correction, fingerprint_prior_strength)
            harm_posterior = _posterior(harm, harm_total, domain_harm, fingerprint_prior_strength)
            disagreement_posterior = _posterior(disagreements, total, domain_disagreement, fingerprint_prior_strength)
            effective = float(total)
            information = disagreement_posterior * _uncertainty_reduction(
                correction_posterior, harm_posterior, effective
            )
            credits.append(StructuralOperatorCredit(
                fingerprint=record.fingerprint, domain=domain, operator_id=operator_id,
                correction_posterior=correction_posterior, harm_posterior=harm_posterior,
                disagreement_posterior=disagreement_posterior,
                effective_observations=effective, future_information_cbit=round(information, 12),
            ))
    committed = {
        "source_receipt_hash": receipt.receipt_hash,
        "records": [item.as_dict() for item in credits],
        "experiment_only": True,
        "core_baseline_authority": False,
    }
    return StructuralOperatorCreditSnapshot(
        source_receipt_hash=receipt.receipt_hash, records=tuple(credits),
        snapshot_hash=_hash_payload(committed),
    )


def _aggregate(records, prefix: str) -> tuple[int, int, int, int, int, int]:
    return (
        sum(getattr(item, f"{prefix}_corrections") for item in records),
        sum(getattr(item, f"{prefix}_correction_opportunities") for item in records),
        sum(getattr(item, f"{prefix}_harms") for item in records),
        sum(getattr(item, f"{prefix}_harm_opportunities") for item in records),
        sum(getattr(item, f"{prefix}_disagreements") for item in records),
        sum(item.total for item in records),
    )


def _posterior(successes: float, total: float, prior: float, strength: float) -> float:
    return round((successes + strength * prior) / (total + strength), 12)


def _uncertainty_reduction(correction: float, harm: float, effective: float) -> float:
    current = 0.5 * (
        sqrt(correction * (1.0 - correction) / (effective + 2.0))
        + sqrt(harm * (1.0 - harm) / (effective + 2.0))
    )
    next_value = 0.5 * (
        sqrt(correction * (1.0 - correction) / (effective + 3.0))
        + sqrt(harm * (1.0 - harm) / (effective + 3.0))
    )
    return current - next_value
