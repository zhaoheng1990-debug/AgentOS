"""Cross-cycle reliability evidence, promotion, decay, and drift snapshots."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from hashlib import sha256
from math import sqrt
from typing import Any

from .benchmark_reliability import BenchmarkReliabilityReceipt
from .benchmark_routing_calibration import RoutingCalibrationReceipt
from .routing_calibration import CalibratedModelProfile


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ReliabilityCycleCandidate:
    cycle_id: str
    sequence: int
    benchmark_truth_commitment: str
    receipt_hashes: tuple[str, ...]
    candidate_hash: str
    candidate_only: bool = True
    routing_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "receipt_hashes": list(self.receipt_hashes)}


@dataclass(frozen=True)
class ReliabilityPromotionReceipt:
    cycle_candidate_hash: str
    validation_ref: str
    status: str
    receipt_hash: str
    experiment_only: bool = True
    core_baseline_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class LifecycleModelProfile:
    model_id: str
    global_posterior: float
    domain_scores: tuple[tuple[str, float, float], ...]
    effective_observations: float
    drift_magnitude: float
    rank_changed: bool
    receipt_hash: str
    _base: CalibratedModelProfile = field(repr=False, compare=False)

    def domain_reliability(self, domain: str) -> float:
        return next((item[1] for item in self.domain_scores if item[0] == domain), self.global_posterior)

    def calibrated_success(self, domain: str, confidence: float, had_retry: bool) -> float:
        probability = (
            0.60 * self.domain_reliability(domain)
            + 0.25 * self._base.confidence_reliability(confidence)
            + 0.15 * self._base.retry_reliability(had_retry)
        )
        return round(min(1.0, max(0.0, probability)), 12)

    def expected_work(self) -> float:
        return self._base.expected_work()

    def uncertainty(self, domain: str) -> float:
        effective = next((item[2] for item in self.domain_scores if item[0] == domain), self.effective_observations)
        return round(1.0 / sqrt(max(effective, 0.25)) + self.drift_magnitude, 12)

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "global_posterior": self.global_posterior,
            "domain_scores": [[domain, score, effective] for domain, score, effective in self.domain_scores],
            "effective_observations": self.effective_observations,
            "drift_magnitude": self.drift_magnitude,
            "rank_changed": self.rank_changed,
            "receipt_hash": self.receipt_hash,
            "advisory_only": True,
            "selection_authority": False,
        }


class ReliabilityLifecycleLedger:
    def __init__(
        self,
        *,
        calibration_receipt: RoutingCalibrationReceipt,
        base_profiles: dict[str, CalibratedModelProfile],
    ) -> None:
        if set(base_profiles) != {item.model_id for item in calibration_receipt.model_records}:
            raise ValueError("reliability_lifecycle_base_coverage_invalid")
        self.calibration_receipt = calibration_receipt
        self.base_profiles = dict(base_profiles)
        self._candidates: dict[str, tuple[ReliabilityCycleCandidate, tuple[BenchmarkReliabilityReceipt, ...]]] = {}
        self._promotions: dict[str, ReliabilityPromotionReceipt] = {}

    def ingest_candidate(self, *, cycle_id: str, sequence: int, diagnostics: dict[str, Any]) -> ReliabilityCycleCandidate:
        if not diagnostics.get("candidate_only") or diagnostics.get("routing_authority") is not False:
            raise ValueError("reliability_lifecycle_candidate_authority_invalid")
        receipts = tuple(self._receipt_from_dict(item) for item in diagnostics.get("receipts", ()))
        if {item.model_id for item in receipts} != set(self.base_profiles):
            raise ValueError("reliability_lifecycle_candidate_model_coverage_invalid")
        commitments = {item.truth_commitment for item in receipts}
        if len(commitments) != 1 or next(iter(commitments)) == self.calibration_receipt.truth_commitment:
            raise ValueError("reliability_lifecycle_candidate_scope_invalid")
        committed = {
            "cycle_id": cycle_id,
            "sequence": sequence,
            "benchmark_truth_commitment": next(iter(commitments)),
            "receipt_hashes": [item.receipt_hash for item in receipts],
            "candidate_only": True,
            "routing_authority": False,
        }
        candidate = ReliabilityCycleCandidate(
            cycle_id=cycle_id, sequence=sequence,
            benchmark_truth_commitment=committed["benchmark_truth_commitment"],
            receipt_hashes=tuple(committed["receipt_hashes"]),
            candidate_hash=_hash_payload(committed),
        )
        self._candidates[candidate.candidate_hash] = (candidate, receipts)
        return candidate

    def promote(self, *, candidate_hash: str, validation_ref: str) -> ReliabilityPromotionReceipt:
        if candidate_hash not in self._candidates or not re.fullmatch(r"[0-9a-f]{64}", validation_ref):
            raise ValueError("reliability_lifecycle_promotion_binding_invalid")
        committed = {
            "cycle_candidate_hash": candidate_hash,
            "validation_ref": validation_ref,
            "status": "PROMOTED_FOR_EXPERIMENT",
            "experiment_only": True,
            "core_baseline_authority": False,
        }
        receipt = ReliabilityPromotionReceipt(**committed, receipt_hash=_hash_payload(committed))
        self._promotions[candidate_hash] = receipt
        return receipt

    def snapshot(self, *, decay: float = 0.55) -> tuple[dict[str, LifecycleModelProfile], dict[str, Any]]:
        if not 0.0 < decay <= 1.0 or not self._promotions:
            raise ValueError("reliability_lifecycle_snapshot_state_invalid")
        promoted = sorted(
            (self._candidates[item] for item in self._promotions),
            key=lambda value: value[0].sequence,
        )
        latest_sequence = promoted[-1][0].sequence
        baseline_rates = self._baseline_rates()
        newest_rates = self._receipt_rates(promoted[-1][1])
        baseline_ranks = self._ranks({model: values["global"] for model, values in baseline_rates.items()})
        newest_ranks = self._ranks({model: values["global"] for model, values in newest_rates.items()})
        statistics = []
        for model_id in sorted(self.base_profiles):
            domain_values = []
            for domain in sorted(item[0] for item in self.base_profiles[model_id].domain_scores):
                base_record = next(item for item in self.calibration_receipt.model_records if item.model_id == model_id)
                base_domain = next(item for item in base_record.domain_scores if item[0] == domain)
                weighted_correct = decay ** (latest_sequence + 1) * base_domain[1]
                weighted_total = decay ** (latest_sequence + 1) * base_domain[2]
                for candidate, receipts in promoted:
                    receipt = next(item for item in receipts if item.model_id == model_id)
                    record = next(item for item in receipt.domain_scores if item[0] == domain)
                    weight = decay ** (latest_sequence - candidate.sequence)
                    weighted_correct += weight * record[1]
                    weighted_total += weight * record[2]
                posterior = (weighted_correct + 1.0) / (weighted_total + 2.0)
                domain_values.append((domain, round(posterior, 12), round(weighted_total, 12)))
            total_effective = sum(item[2] for item in domain_values)
            global_posterior = sum(item[1] * item[2] for item in domain_values) / total_effective
            drift = abs(newest_rates[model_id]["global"] - baseline_rates[model_id]["global"])
            statistics.append({
                "model_id": model_id,
                "global_posterior": round(global_posterior, 12),
                "domain_scores": [[item[0], item[1], item[2]] for item in domain_values],
                "effective_observations": round(total_effective, 12),
                "drift_magnitude": round(drift, 12),
                "rank_changed": baseline_ranks[model_id] != newest_ranks[model_id],
            })
        committed = {
            "module": "reliability_lifecycle_snapshot_v0_1",
            "calibration_receipt_hash": self.calibration_receipt.receipt_hash,
            "promotion_receipt_hashes": [self._promotions[item].receipt_hash for item in self._promotions],
            "decay": decay,
            "model_statistics": statistics,
            "candidate_only_inputs_promoted_explicitly": True,
            "experiment_only": True,
            "core_baseline_authority": False,
        }
        snapshot_hash = _hash_payload(committed)
        profiles = {
            item["model_id"]: LifecycleModelProfile(
                model_id=item["model_id"], global_posterior=item["global_posterior"],
                domain_scores=tuple(tuple(value) for value in item["domain_scores"]),
                effective_observations=item["effective_observations"],
                drift_magnitude=item["drift_magnitude"], rank_changed=item["rank_changed"],
                receipt_hash=snapshot_hash, _base=self.base_profiles[item["model_id"]],
            )
            for item in statistics
        }
        return profiles, {**committed, "snapshot_hash": snapshot_hash}

    def _baseline_rates(self) -> dict[str, dict[str, float]]:
        return {
            item.model_id: {
                "global": item.correct / item.total,
                **{domain: correct / total for domain, correct, total, _ in item.domain_scores},
            }
            for item in self.calibration_receipt.model_records
        }

    @staticmethod
    def _receipt_rates(receipts: tuple[BenchmarkReliabilityReceipt, ...]) -> dict[str, dict[str, float]]:
        return {
            item.model_id: {
                "global": sum(record[1] for record in item.domain_scores) / sum(record[2] for record in item.domain_scores),
                **{domain: score for domain, _, _, score in item.domain_scores},
            }
            for item in receipts
        }

    @staticmethod
    def _ranks(values: dict[str, float]) -> dict[str, int]:
        ordered = sorted(values, key=lambda model_id: (values[model_id], model_id), reverse=True)
        return {model_id: index + 1 for index, model_id in enumerate(ordered)}

    @staticmethod
    def _receipt_from_dict(payload: dict[str, Any]) -> BenchmarkReliabilityReceipt:
        return BenchmarkReliabilityReceipt(
            **{
                **payload,
                "domain_scores": tuple(tuple(item) for item in payload["domain_scores"]),
                "evidence_refs": tuple(payload["evidence_refs"]),
            }
        )


def build_shadow_exploration_schedule(
    *,
    item_domains: dict[str, str],
    profiles: dict[str, LifecycleModelProfile],
    budget: int = 2,
) -> dict[str, str]:
    if budget < 0 or budget > len(item_domains):
        raise ValueError("reliability_exploration_budget_invalid")
    minimum_work = min(item.expected_work() for item in profiles.values())
    candidates = []
    for item_id, domain in item_domains.items():
        primary = max(
            profiles.values(),
            key=lambda item: (
                0.75 * item.domain_reliability(domain) + 0.25 * item.global_posterior
                - 0.04 * (item.expected_work() / minimum_work - 1.0),
                item.model_id,
            ),
        )
        alternatives = [item for item in profiles.values() if item.model_id != primary.model_id]
        explorer = max(alternatives, key=lambda item: (item.uncertainty(domain), item.model_id))
        candidates.append((explorer.uncertainty(domain), item_id, explorer.model_id))
    schedule = {}
    used_models = set()
    ordered = sorted(candidates, reverse=True)
    for _, item_id, model_id in ordered:
        if len(schedule) >= budget:
            break
        if model_id not in used_models:
            schedule[item_id] = model_id
            used_models.add(model_id)
    for _, item_id, model_id in ordered:
        if len(schedule) >= budget:
            break
        if item_id not in schedule:
            schedule[item_id] = model_id
    return schedule
