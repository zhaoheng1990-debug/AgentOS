"""Deterministic evaluation for cognitive organization learning."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


ORGANIZATION_LEARNING_EVAL_VERSION = "cognitive_organization_learning_eval_v0_1"

FULL_PROTOCOLS = ("SOLO", "FIXED_TEAM", "DYNAMIC_TEAM")
COMPONENT_VARIANTS = {
    "COORDINATOR": "DYNAMIC_NO_COORDINATOR",
    "ADVERSARIAL_REVIEWER": "DYNAMIC_NO_REVIEWER",
    "REPLICATOR": "DYNAMIC_NO_REPLICATOR",
    "SYNTHESIZER": "DYNAMIC_NO_SYNTHESIZER",
}
ORGANIZATION_PROTOCOL_VARIANTS = {*FULL_PROTOCOLS, *COMPONENT_VARIANTS.values()}
EVIDENCE_TIERS = {"LIVE_PROJECT", "SCRIPTED_FIXTURE"}


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _unit(name: str, value: Any) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or not 0.0 <= float(value) <= 1.0
    ):
        raise ValueError(f"{name}_outside_unit_interval")


def _nonnegative_integer(name: str, value: Any) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name}_must_be_nonnegative_integer")


@dataclass(frozen=True)
class OrganizationTrialRecord:
    record_id: str
    trial_group_id: str
    context_key: str
    evidence_tier: str
    protocol_id: str
    effectiveness_score: float
    observed_cbit_gain: float
    normalized_cost: float
    convergence_steps: int
    errors_exposed: int
    errors_corrected: int
    negative_transfer_opportunities: int
    negative_transfer_intercepts: int
    evidence_refs: tuple[str, ...]
    harness_receipt_ref: str
    execution_result_hash: str
    source_result_hash: str
    replay_valid: bool
    record_hash: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.record_id):
            raise ValueError("organization_trial_record_id_invalid")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.trial_group_id):
            raise ValueError("organization_trial_group_id_invalid")
        if not self.context_key or not self.harness_receipt_ref:
            raise ValueError("organization_trial_record_identity_incomplete")
        if self.evidence_tier not in EVIDENCE_TIERS:
            raise ValueError(f"organization_trial_evidence_tier_invalid:{self.evidence_tier}")
        if self.protocol_id not in ORGANIZATION_PROTOCOL_VARIANTS:
            raise ValueError(f"organization_trial_protocol_invalid:{self.protocol_id}")
        for name in ("effectiveness_score", "observed_cbit_gain", "normalized_cost"):
            _unit(name, getattr(self, name))
        for name in (
            "convergence_steps",
            "errors_exposed",
            "errors_corrected",
            "negative_transfer_opportunities",
            "negative_transfer_intercepts",
        ):
            _nonnegative_integer(name, getattr(self, name))
        if self.convergence_steps < 1:
            raise ValueError("organization_trial_convergence_steps_required")
        if self.errors_corrected > self.errors_exposed:
            raise ValueError("organization_trial_errors_corrected_exceed_exposed")
        if self.negative_transfer_intercepts > self.negative_transfer_opportunities:
            raise ValueError("organization_trial_intercepts_exceed_opportunities")
        if not self.evidence_refs or len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("organization_trial_evidence_refs_invalid")
        for name in ("execution_result_hash", "source_result_hash", "record_hash"):
            if not re.fullmatch(r"[0-9a-f]{64}", getattr(self, name)):
                raise ValueError(f"organization_trial_{name}_invalid")
        if self.replay_valid is not True:
            raise ValueError("organization_trial_replay_must_be_valid")
        if self.record_hash != _hash_payload(self._committed_dict()):
            raise ValueError("organization_trial_record_hash_mismatch")

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        trial_group_id: str,
        context_key: str,
        evidence_tier: str,
        protocol_id: str,
        effectiveness_score: float,
        observed_cbit_gain: float,
        normalized_cost: float,
        convergence_steps: int,
        errors_exposed: int,
        errors_corrected: int,
        negative_transfer_opportunities: int,
        negative_transfer_intercepts: int,
        evidence_refs: tuple[str, ...],
        harness_receipt_ref: str,
        execution_result_hash: str,
        source_result_hash: str,
        replay_valid: bool,
    ) -> "OrganizationTrialRecord":
        committed = {
            "record_id": record_id,
            "trial_group_id": trial_group_id,
            "context_key": context_key,
            "evidence_tier": evidence_tier,
            "protocol_id": protocol_id,
            "effectiveness_score": float(effectiveness_score),
            "observed_cbit_gain": float(observed_cbit_gain),
            "normalized_cost": float(normalized_cost),
            "convergence_steps": convergence_steps,
            "errors_exposed": errors_exposed,
            "errors_corrected": errors_corrected,
            "negative_transfer_opportunities": negative_transfer_opportunities,
            "negative_transfer_intercepts": negative_transfer_intercepts,
            "evidence_refs": list(evidence_refs),
            "harness_receipt_ref": harness_receipt_ref,
            "execution_result_hash": execution_result_hash,
            "source_result_hash": source_result_hash,
            "replay_valid": replay_valid,
        }
        return cls(
            record_id=record_id,
            trial_group_id=trial_group_id,
            context_key=context_key,
            evidence_tier=evidence_tier,
            protocol_id=protocol_id,
            effectiveness_score=float(effectiveness_score),
            observed_cbit_gain=float(observed_cbit_gain),
            normalized_cost=float(normalized_cost),
            convergence_steps=convergence_steps,
            errors_exposed=errors_exposed,
            errors_corrected=errors_corrected,
            negative_transfer_opportunities=negative_transfer_opportunities,
            negative_transfer_intercepts=negative_transfer_intercepts,
            evidence_refs=tuple(evidence_refs),
            harness_receipt_ref=harness_receipt_ref,
            execution_result_hash=execution_result_hash,
            source_result_hash=source_result_hash,
            replay_valid=replay_valid,
            record_hash=_hash_payload(committed),
        )

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "trial_group_id": self.trial_group_id,
            "context_key": self.context_key,
            "evidence_tier": self.evidence_tier,
            "protocol_id": self.protocol_id,
            "effectiveness_score": self.effectiveness_score,
            "observed_cbit_gain": self.observed_cbit_gain,
            "normalized_cost": self.normalized_cost,
            "convergence_steps": self.convergence_steps,
            "errors_exposed": self.errors_exposed,
            "errors_corrected": self.errors_corrected,
            "negative_transfer_opportunities": self.negative_transfer_opportunities,
            "negative_transfer_intercepts": self.negative_transfer_intercepts,
            "evidence_refs": list(self.evidence_refs),
            "harness_receipt_ref": self.harness_receipt_ref,
            "execution_result_hash": self.execution_result_hash,
            "source_result_hash": self.source_result_hash,
            "replay_valid": self.replay_valid,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "record_hash": self.record_hash}


@dataclass(frozen=True)
class OrganizationComponentAttribution:
    component_id: str
    ablation_variant: str
    matched_pair_count: int
    mean_effectiveness_contribution: float | None
    mean_cbit_contribution: float | None
    mean_cost_contribution: float | None
    identifiability: str
    matched_trial_group_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "ablation_variant": self.ablation_variant,
            "matched_pair_count": self.matched_pair_count,
            "mean_effectiveness_contribution": self.mean_effectiveness_contribution,
            "mean_cbit_contribution": self.mean_cbit_contribution,
            "mean_cost_contribution": self.mean_cost_contribution,
            "identifiability": self.identifiability,
            "matched_trial_group_ids": list(self.matched_trial_group_ids),
        }


@dataclass(frozen=True)
class OrganizationAttributionReport:
    context_key: str
    evidence_tier: str
    components: tuple[OrganizationComponentAttribution, ...]
    report_hash: str
    causal_claims_require_matched_ablation: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "context_key": self.context_key,
            "evidence_tier": self.evidence_tier,
            "components": [item.as_dict() for item in self.components],
            "report_hash": self.report_hash,
            "causal_claims_require_matched_ablation": self.causal_claims_require_matched_ablation,
        }


@dataclass(frozen=True)
class OrganizationProtocolEvaluation:
    context_key: str
    evidence_tier: str
    complete_trial_group_ids: tuple[str, ...]
    protocol_statistics: dict[str, dict[str, Any]]
    recommendation: str
    incumbent_protocol: str
    sufficient_repeated_evidence: bool
    evaluation_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "context_key": self.context_key,
            "evidence_tier": self.evidence_tier,
            "complete_trial_group_ids": list(self.complete_trial_group_ids),
            "protocol_statistics": self.protocol_statistics,
            "recommendation": self.recommendation,
            "incumbent_protocol": self.incumbent_protocol,
            "sufficient_repeated_evidence": self.sufficient_repeated_evidence,
            "evaluation_hash": self.evaluation_hash,
        }


class OrganizationLearningEvaluator:
    """Compute matched component effects and repeated protocol evidence."""

    module_id = ORGANIZATION_LEARNING_EVAL_VERSION
    capabilities = ("matched_organization_attribution", "repeated_protocol_evaluation")

    def __init__(self, *, minimum_repeated_trials: int = 2, improvement_threshold: float = 0.02) -> None:
        if (
            not isinstance(minimum_repeated_trials, int)
            or isinstance(minimum_repeated_trials, bool)
            or minimum_repeated_trials < 2
        ):
            raise ValueError("organization_learning_minimum_trials_invalid")
        if not math.isfinite(improvement_threshold) or improvement_threshold < 0.0:
            raise ValueError("organization_learning_improvement_threshold_invalid")
        self.minimum_repeated_trials = minimum_repeated_trials
        self.improvement_threshold = float(improvement_threshold)

    def attribute(
        self,
        records: tuple[OrganizationTrialRecord, ...],
        *,
        context_key: str,
        evidence_tier: str,
    ) -> OrganizationAttributionReport:
        scoped = self._scoped_records(records, context_key, evidence_tier)
        by_group = self._by_group(scoped)
        components = []
        for component_id, variant in COMPONENT_VARIANTS.items():
            pairs = []
            seen_source_hashes: set[str] = set()
            for group_id, protocols in by_group.items():
                full = protocols.get("DYNAMIC_TEAM")
                ablated = protocols.get(variant)
                if full is not None and ablated is not None:
                    if (
                        full.source_result_hash != ablated.source_result_hash
                        or full.evidence_refs != ablated.evidence_refs
                    ):
                        raise ValueError(
                            f"organization_learning_ablation_pair_surface_mismatch:{group_id}:{variant}"
                        )
                    if full.source_result_hash in seen_source_hashes:
                        raise ValueError(
                            f"organization_learning_duplicate_ablation_source:{component_id}:"
                            f"{full.source_result_hash}"
                        )
                    seen_source_hashes.add(full.source_result_hash)
                    pairs.append((group_id, full, ablated))
            identifiable = len(pairs) >= self.minimum_repeated_trials
            components.append(
                OrganizationComponentAttribution(
                    component_id=component_id,
                    ablation_variant=variant,
                    matched_pair_count=len(pairs),
                    mean_effectiveness_contribution=(
                        self._mean([full.effectiveness_score - ablated.effectiveness_score for _, full, ablated in pairs])
                        if identifiable
                        else None
                    ),
                    mean_cbit_contribution=(
                        self._mean([full.observed_cbit_gain - ablated.observed_cbit_gain for _, full, ablated in pairs])
                        if identifiable
                        else None
                    ),
                    mean_cost_contribution=(
                        self._mean([full.normalized_cost - ablated.normalized_cost for _, full, ablated in pairs])
                        if identifiable
                        else None
                    ),
                    identifiability=("IDENTIFIED_MATCHED_ABLATION" if identifiable else "NOT_IDENTIFIABLE"),
                    matched_trial_group_ids=tuple(group_id for group_id, _, _ in pairs),
                )
            )
        committed = {
            "context_key": context_key,
            "evidence_tier": evidence_tier,
            "components": [item.as_dict() for item in components],
            "record_hashes": sorted(item.record_hash for item in scoped),
        }
        return OrganizationAttributionReport(
            context_key=context_key,
            evidence_tier=evidence_tier,
            components=tuple(components),
            report_hash=_hash_payload(committed),
        )

    def evaluate_protocols(
        self,
        records: tuple[OrganizationTrialRecord, ...],
        *,
        context_key: str,
        evidence_tier: str,
    ) -> OrganizationProtocolEvaluation:
        scoped = self._scoped_records(records, context_key, evidence_tier)
        by_group = self._by_group(scoped)
        complete_ids = self._complete_group_ids(by_group)
        statistics: dict[str, dict[str, Any]] = {}
        for protocol in FULL_PROTOCOLS:
            samples = [by_group[group_id][protocol] for group_id in complete_ids]
            statistics[protocol] = {
                "sample_count": len(samples),
                "mean_effectiveness": self._mean([item.effectiveness_score for item in samples]) if samples else None,
                "mean_observed_cbit": self._mean([item.observed_cbit_gain for item in samples]) if samples else None,
                "mean_normalized_cost": self._mean([item.normalized_cost for item in samples]) if samples else None,
                "mean_convergence_steps": self._mean([float(item.convergence_steps) for item in samples]) if samples else None,
            }
        ranked = sorted(
            (
                (protocol, stats["mean_effectiveness"])
                for protocol, stats in statistics.items()
                if stats["mean_effectiveness"] is not None
            ),
            key=lambda item: (-item[1], FULL_PROTOCOLS.index(item[0])),
        )
        incumbent = ranked[0][0] if ranked else ""
        sufficient = len(complete_ids) >= self.minimum_repeated_trials
        recommendation = "REQUIRE_EXPLORATION"
        if sufficient and len(ranked) >= 2 and ranked[0][1] - ranked[1][1] > self.improvement_threshold:
            recommendation = incumbent
        committed = {
            "context_key": context_key,
            "evidence_tier": evidence_tier,
            "complete_trial_group_ids": list(complete_ids),
            "protocol_statistics": statistics,
            "recommendation": recommendation,
            "incumbent_protocol": incumbent,
            "minimum_repeated_trials": self.minimum_repeated_trials,
            "improvement_threshold": self.improvement_threshold,
        }
        return OrganizationProtocolEvaluation(
            context_key=context_key,
            evidence_tier=evidence_tier,
            complete_trial_group_ids=complete_ids,
            protocol_statistics=statistics,
            recommendation=recommendation,
            incumbent_protocol=incumbent,
            sufficient_repeated_evidence=sufficient,
            evaluation_hash=_hash_payload(committed),
        )

    @staticmethod
    def _scoped_records(
        records: tuple[OrganizationTrialRecord, ...], context_key: str, evidence_tier: str
    ) -> tuple[OrganizationTrialRecord, ...]:
        if not context_key or evidence_tier not in EVIDENCE_TIERS:
            raise ValueError("organization_learning_scope_invalid")
        return tuple(
            item for item in records if item.context_key == context_key and item.evidence_tier == evidence_tier
        )

    @staticmethod
    def _by_group(
        records: tuple[OrganizationTrialRecord, ...],
    ) -> dict[str, dict[str, OrganizationTrialRecord]]:
        result: dict[str, dict[str, OrganizationTrialRecord]] = {}
        for item in records:
            protocols = result.setdefault(item.trial_group_id, {})
            if item.protocol_id in protocols:
                raise ValueError(
                    f"organization_learning_duplicate_group_protocol:{item.trial_group_id}:{item.protocol_id}"
                )
            protocols[item.protocol_id] = item
        return result

    @staticmethod
    def _complete_group_ids(
        by_group: dict[str, dict[str, OrganizationTrialRecord]],
    ) -> tuple[str, ...]:
        complete_ids = []
        seen_source_hashes: set[str] = set()
        for group_id in sorted(by_group):
            protocols = by_group[group_id]
            if not set(FULL_PROTOCOLS).issubset(protocols):
                continue
            arms = [protocols[protocol] for protocol in FULL_PROTOCOLS]
            source_hashes = {item.source_result_hash for item in arms}
            evidence_surfaces = {item.evidence_refs for item in arms}
            if len(source_hashes) != 1 or len(evidence_surfaces) != 1:
                raise ValueError(f"organization_learning_complete_group_surface_mismatch:{group_id}")
            source_hash = next(iter(source_hashes))
            if source_hash in seen_source_hashes:
                raise ValueError(f"organization_learning_duplicate_complete_source:{source_hash}")
            seen_source_hashes.add(source_hash)
            complete_ids.append(group_id)
        return tuple(complete_ids)

    @staticmethod
    def _mean(values: list[float]) -> float:
        return round(sum(values) / len(values), 12)
