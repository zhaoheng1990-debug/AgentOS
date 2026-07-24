"""Experiment-only hierarchical credit over Harness-owned fingerprint receipts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from hashlib import sha256
from math import sqrt
from typing import Any

from .benchmark_reliability import BenchmarkReliabilityReceipt
from .routing_calibration import CalibratedModelProfile
from .task_fingerprints import FINGERPRINT_TO_DOMAIN


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class FingerprintCycleCandidate:
    cycle_id: str
    sequence: int
    source_report_hash: str
    truth_commitment: str
    receipt_hashes: tuple[str, ...]
    candidate_hash: str
    candidate_only: bool = True
    routing_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "receipt_hashes": list(self.receipt_hashes)}


@dataclass(frozen=True)
class FingerprintPromotionReceipt:
    candidate_hash: str
    source_report_hash: str
    status: str
    receipt_hash: str
    experiment_only: bool = True
    core_baseline_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class HierarchicalFingerprintProfile:
    model_id: str
    global_posterior: float
    domain_scores: tuple[tuple[str, float, float], ...]
    fingerprint_scores: tuple[tuple[str, str, float, float], ...]
    effective_observations: float
    receipt_hash: str
    _base: CalibratedModelProfile = field(repr=False, compare=False)

    def domain_reliability(self, domain: str) -> float:
        return next((score for name, score, _ in self.domain_scores if name == domain), self.global_posterior)

    def context_reliability(self, context: str, domain: str) -> float:
        return next(
            (score for fingerprint, bound_domain, score, _ in self.fingerprint_scores if fingerprint == context and bound_domain == domain),
            self.domain_reliability(domain),
        )

    def calibrated_success(self, domain: str, confidence: float, had_retry: bool) -> float:
        return self.calibrated_success_for_context("", domain, confidence, had_retry)

    def calibrated_success_for_context(self, context: str, domain: str, confidence: float, had_retry: bool) -> float:
        probability = (
            0.70 * self.context_reliability(context, domain)
            + 0.18 * self._base.confidence_reliability(confidence)
            + 0.12 * self._base.retry_reliability(had_retry)
        )
        return round(min(1.0, max(0.0, probability)), 12)

    def expected_work(self) -> float:
        return self._base.expected_work()

    def effective_for_context(self, context: str) -> float:
        return next((effective for fingerprint, _, _, effective in self.fingerprint_scores if fingerprint == context), 0.0)

    def uncertainty(self, context: str, domain: str) -> float:
        probability = self.context_reliability(context, domain)
        effective = self.effective_for_context(context)
        return round(sqrt(probability * (1.0 - probability) / max(effective + 2.0, 2.0)), 12)

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "global_posterior": self.global_posterior,
            "domain_scores": [list(item) for item in self.domain_scores],
            "fingerprint_scores": [list(item) for item in self.fingerprint_scores],
            "effective_observations": self.effective_observations,
            "receipt_hash": self.receipt_hash,
            "advisory_only": True,
            "selection_authority": False,
        }


class HierarchicalFingerprintCreditLedger:
    def __init__(self, *, base_profiles: dict[str, CalibratedModelProfile]) -> None:
        if len(base_profiles) < 2:
            raise ValueError("fingerprint_credit_base_profiles_invalid")
        self.base_profiles = dict(base_profiles)
        self._candidates: dict[str, tuple[FingerprintCycleCandidate, tuple[BenchmarkReliabilityReceipt, ...]]] = {}
        self._promotions: dict[str, FingerprintPromotionReceipt] = {}

    def ingest_candidate(
        self,
        *,
        cycle_id: str,
        sequence: int,
        source_report_hash: str,
        receipts: tuple[BenchmarkReliabilityReceipt, ...],
    ) -> FingerprintCycleCandidate:
        if not cycle_id or sequence < 1 or not re.fullmatch(r"[0-9a-f]{64}", source_report_hash):
            raise ValueError("fingerprint_credit_candidate_source_invalid")
        if {item.model_id for item in receipts} != set(self.base_profiles):
            raise ValueError("fingerprint_credit_model_coverage_invalid")
        expected = set(FINGERPRINT_TO_DOMAIN)
        if any({record[0] for record in item.domain_scores} != expected for item in receipts):
            raise ValueError("fingerprint_credit_receipt_coverage_invalid")
        commitments = {item.truth_commitment for item in receipts}
        if len(commitments) != 1:
            raise ValueError("fingerprint_credit_truth_binding_invalid")
        committed = {
            "cycle_id": cycle_id,
            "sequence": sequence,
            "source_report_hash": source_report_hash,
            "truth_commitment": next(iter(commitments)),
            "receipt_hashes": sorted(item.receipt_hash for item in receipts),
            "candidate_only": True,
            "routing_authority": False,
        }
        candidate = FingerprintCycleCandidate(
            **{**committed, "receipt_hashes": tuple(committed["receipt_hashes"]), "candidate_hash": _hash_payload(committed)}
        )
        self._candidates[candidate.candidate_hash] = (candidate, receipts)
        return candidate

    def promote(self, *, candidate_hash: str, source_report_hash: str) -> FingerprintPromotionReceipt:
        if candidate_hash not in self._candidates:
            raise ValueError("fingerprint_credit_promotion_candidate_missing")
        candidate = self._candidates[candidate_hash][0]
        if source_report_hash != candidate.source_report_hash:
            raise ValueError("fingerprint_credit_promotion_source_mismatch")
        committed = {
            "candidate_hash": candidate_hash,
            "source_report_hash": source_report_hash,
            "status": "PROMOTED_FOR_EXPERIMENT",
            "experiment_only": True,
            "core_baseline_authority": False,
        }
        receipt = FingerprintPromotionReceipt(**committed, receipt_hash=_hash_payload(committed))
        self._promotions[candidate_hash] = receipt
        return receipt

    def snapshot(
        self,
        *,
        decay: float = 0.72,
        domain_prior_strength: float = 2.0,
        fingerprint_prior_strength: float = 2.0,
    ) -> tuple[dict[str, HierarchicalFingerprintProfile], dict[str, Any]]:
        if not 0.0 < decay <= 1.0 or not self._promotions:
            raise ValueError("fingerprint_credit_snapshot_state_invalid")
        promoted = sorted((self._candidates[key] for key in self._promotions), key=lambda item: item[0].sequence)
        if len({candidate.sequence for candidate, _ in promoted}) != len(promoted):
            raise ValueError("fingerprint_credit_sequence_invalid")
        latest_sequence = promoted[-1][0].sequence
        statistics = []
        for model_id in sorted(self.base_profiles):
            observations = self._weighted_observations(model_id, promoted, latest_sequence, decay)
            total_correct = sum(value[0] for value in observations.values())
            total_effective = sum(value[1] for value in observations.values())
            global_posterior = (total_correct + 1.0) / (total_effective + 2.0)
            domain_scores = []
            for domain in sorted(set(FINGERPRINT_TO_DOMAIN.values())):
                selected = [observations[name] for name, bound in FINGERPRINT_TO_DOMAIN.items() if bound == domain]
                correct, total = sum(item[0] for item in selected), sum(item[1] for item in selected)
                posterior = (correct + domain_prior_strength * global_posterior) / (total + domain_prior_strength)
                domain_scores.append((domain, round(posterior, 12), round(total, 12)))
            fingerprint_scores = []
            for fingerprint, domain in sorted(FINGERPRINT_TO_DOMAIN.items()):
                correct, total = observations[fingerprint]
                domain_posterior = next(item[1] for item in domain_scores if item[0] == domain)
                posterior = (correct + fingerprint_prior_strength * domain_posterior) / (total + fingerprint_prior_strength)
                fingerprint_scores.append((fingerprint, domain, round(posterior, 12), round(total, 12)))
            statistics.append({
                "model_id": model_id,
                "global_posterior": round(global_posterior, 12),
                "domain_scores": [list(item) for item in domain_scores],
                "fingerprint_scores": [list(item) for item in fingerprint_scores],
                "effective_observations": round(total_effective, 12),
            })
        committed = {
            "module": "hierarchical_fingerprint_credit_v0_1",
            "decay": decay,
            "domain_prior_strength": domain_prior_strength,
            "fingerprint_prior_strength": fingerprint_prior_strength,
            "promotion_receipt_hashes": [self._promotions[key].receipt_hash for key in self._promotions],
            "source_report_hashes": [candidate.source_report_hash for candidate, _ in promoted],
            "model_statistics": statistics,
            "harness_owned_receipts_only": True,
            "candidate_only_inputs_promoted_explicitly": True,
            "experiment_only": True,
            "core_baseline_authority": False,
        }
        snapshot_hash = _hash_payload(committed)
        profiles = {
            item["model_id"]: HierarchicalFingerprintProfile(
                model_id=item["model_id"],
                global_posterior=item["global_posterior"],
                domain_scores=tuple(tuple(value) for value in item["domain_scores"]),
                fingerprint_scores=tuple(tuple(value) for value in item["fingerprint_scores"]),
                effective_observations=item["effective_observations"],
                receipt_hash=snapshot_hash,
                _base=self.base_profiles[item["model_id"]],
            )
            for item in statistics
        }
        return profiles, {**committed, "snapshot_hash": snapshot_hash}

    @staticmethod
    def _weighted_observations(model_id, promoted, latest_sequence, decay):
        values = {fingerprint: [0.0, 0.0] for fingerprint in FINGERPRINT_TO_DOMAIN}
        for candidate, receipts in promoted:
            receipt = next(item for item in receipts if item.model_id == model_id)
            weight = decay ** (latest_sequence - candidate.sequence)
            for fingerprint, correct, total, _ in receipt.domain_scores:
                values[fingerprint][0] += weight * correct
                values[fingerprint][1] += weight * total
        return {key: tuple(value) for key, value in values.items()}


def build_micro_probe_schedule(
    *,
    item_domains: dict[str, str],
    item_fingerprints: dict[str, str],
    profiles: dict[str, HierarchicalFingerprintProfile],
    budget: int = 3,
    maximum_rank_gap: float = 0.15,
    maximum_effective_observations: float = 4.0,
) -> dict[str, str]:
    if budget < 0 or budget > len(item_domains) or set(item_domains) != set(item_fingerprints):
        raise ValueError("fingerprint_probe_schedule_inputs_invalid")
    candidates = []
    minimum_work = min(profile.expected_work() for profile in profiles.values())
    for item_id, fingerprint in item_fingerprints.items():
        domain = item_domains[item_id]
        ranked = sorted(
            profiles.values(),
            key=lambda profile: (
                0.75 * profile.context_reliability(fingerprint, domain)
                + 0.25 * profile.global_posterior
                - 0.04 * (profile.expected_work() / minimum_work - 1.0),
                profile.model_id,
            ),
            reverse=True,
        )
        utilities = [
            0.75 * profile.context_reliability(fingerprint, domain)
            + 0.25 * profile.global_posterior
            - 0.04 * (profile.expected_work() / minimum_work - 1.0)
            for profile in ranked[:2]
        ]
        gap = utilities[0] - utilities[1]
        effective = min(ranked[0].effective_for_context(fingerprint), ranked[1].effective_for_context(fingerprint))
        uncertainty = max(item.uncertainty(fingerprint, domain) for item in ranked[:2])
        if gap <= maximum_rank_gap and effective <= maximum_effective_observations:
            candidates.append((uncertainty, -gap, item_id, ranked[1].model_id))
    return {item_id: peer_model for _, _, item_id, peer_model in sorted(candidates, reverse=True)[:budget]}
