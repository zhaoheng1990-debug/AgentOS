"""Exact-context matched evidence aggregation for organization policies."""

from __future__ import annotations

from statistics import mean
from typing import Any

from .contextual_policy_models import (
    CONTEXTUAL_POLICY_IDS,
    MatchedPolicyEvidence,
    hash_payload,
)
from .organization_learning_eval import EVIDENCE_TIERS, OrganizationTrialRecord


CONTEXTUAL_POLICY_COMPARATORS = {
    "SOLO": "DYNAMIC_TEAM",
    "FIXED_TEAM": "SOLO",
    "DYNAMIC_TEAM": "SOLO",
    "DYNAMIC_NO_COORDINATOR": "DYNAMIC_TEAM",
    "DYNAMIC_NO_REVIEWER": "DYNAMIC_TEAM",
    "DYNAMIC_NO_REPLICATOR": "DYNAMIC_TEAM",
    "DYNAMIC_NO_SYNTHESIZER": "DYNAMIC_TEAM",
}


class ContextualMatchedEvidenceEvaluator:
    """Aggregate only paired observations on an identical trial surface."""

    def __init__(self, *, minimum_matched_pairs: int = 2) -> None:
        if (
            not isinstance(minimum_matched_pairs, int)
            or isinstance(minimum_matched_pairs, bool)
            or minimum_matched_pairs < 2
        ):
            raise ValueError("contextual_policy_minimum_matched_pairs_invalid")
        self.minimum_matched_pairs = minimum_matched_pairs

    def evaluate(
        self,
        records: tuple[OrganizationTrialRecord, ...],
        *,
        context_key: str,
        evidence_tier: str,
    ) -> tuple[MatchedPolicyEvidence, ...]:
        if not context_key:
            raise ValueError("contextual_policy_context_key_required")
        if evidence_tier not in EVIDENCE_TIERS:
            raise ValueError("contextual_policy_evidence_tier_invalid")
        scoped = tuple(
            record
            for record in records
            if record.context_key == context_key and record.evidence_tier == evidence_tier
        )
        by_group = self._by_group(scoped)
        return tuple(
            self._evaluate_policy(policy_id, context_key, evidence_tier, by_group)
            for policy_id in CONTEXTUAL_POLICY_IDS
        )

    def _evaluate_policy(
        self,
        policy_id: str,
        context_key: str,
        evidence_tier: str,
        by_group: dict[str, dict[str, OrganizationTrialRecord]],
    ) -> MatchedPolicyEvidence:
        comparator_id = CONTEXTUAL_POLICY_COMPARATORS[policy_id]
        pairs = []
        source_hashes = set()
        for group_id, protocols in sorted(by_group.items()):
            candidate = protocols.get(policy_id)
            comparator = protocols.get(comparator_id)
            if candidate is None or comparator is None:
                continue
            self._validate_pair_surface(group_id, policy_id, candidate, comparator)
            if candidate.source_result_hash in source_hashes:
                raise ValueError(
                    f"contextual_policy_duplicate_matched_source:{policy_id}:{candidate.source_result_hash}"
                )
            source_hashes.add(candidate.source_result_hash)
            pairs.append((group_id, candidate, comparator))
        sufficient = len(pairs) >= self.minimum_matched_pairs
        candidate_records = [candidate for _, candidate, _ in pairs]
        evidence_refs = tuple(
            dict.fromkeys(ref for record in candidate_records for ref in record.evidence_refs)
        )
        record_hashes = tuple(
            sorted(
                record.record_hash
                for _, candidate, comparator in pairs
                for record in (candidate, comparator)
            )
        )
        metrics = self._metrics(pairs) if pairs else self._empty_metrics()
        committed = {
            "policy_id": policy_id,
            "context_key": context_key,
            "evidence_tier": evidence_tier,
            "comparator_policy_id": comparator_id,
            "matched_trial_group_ids": [group_id for group_id, _, _ in pairs],
            "record_hashes": list(record_hashes),
            "minimum_matched_pairs": self.minimum_matched_pairs,
            **metrics,
        }
        return MatchedPolicyEvidence(
            policy_id=policy_id,
            context_key=context_key,
            evidence_tier=evidence_tier,
            comparator_policy_id=comparator_id,
            minimum_matched_pairs=self.minimum_matched_pairs,
            matched_pair_count=len(pairs),
            unique_source_count=len(source_hashes),
            sufficient_matched_evidence=sufficient,
            matched_trial_group_ids=tuple(group_id for group_id, _, _ in pairs),
            evidence_refs=evidence_refs,
            record_hashes=record_hashes,
            evidence_hash=hash_payload(committed),
            **metrics,
        )

    @staticmethod
    def _metrics(
        pairs: list[tuple[str, OrganizationTrialRecord, OrganizationTrialRecord]],
    ) -> dict[str, float | None]:
        candidates = [candidate for _, candidate, _ in pairs]
        interception_rates = [
            candidate.negative_transfer_intercepts / candidate.negative_transfer_opportunities
            for candidate in candidates
            if candidate.negative_transfer_opportunities > 0
        ]
        return {
            "mean_effectiveness": mean(item.effectiveness_score for item in candidates),
            "mean_observed_cbit": mean(item.observed_cbit_gain for item in candidates),
            "mean_normalized_cost": mean(item.normalized_cost for item in candidates),
            "mean_effectiveness_delta": mean(
                candidate.effectiveness_score - comparator.effectiveness_score
                for _, candidate, comparator in pairs
            ),
            "mean_cbit_delta": mean(
                candidate.observed_cbit_gain - comparator.observed_cbit_gain
                for _, candidate, comparator in pairs
            ),
            "mean_cost_delta": mean(
                candidate.normalized_cost - comparator.normalized_cost
                for _, candidate, comparator in pairs
            ),
            "mean_negative_transfer_interception": (
                mean(interception_rates) if interception_rates else None
            ),
        }

    @staticmethod
    def _empty_metrics() -> dict[str, None]:
        return {
            "mean_effectiveness": None,
            "mean_observed_cbit": None,
            "mean_normalized_cost": None,
            "mean_effectiveness_delta": None,
            "mean_cbit_delta": None,
            "mean_cost_delta": None,
            "mean_negative_transfer_interception": None,
        }

    @staticmethod
    def _by_group(
        records: tuple[OrganizationTrialRecord, ...],
    ) -> dict[str, dict[str, OrganizationTrialRecord]]:
        grouped: dict[str, dict[str, OrganizationTrialRecord]] = {}
        for record in records:
            protocols = grouped.setdefault(record.trial_group_id, {})
            if record.protocol_id in protocols:
                raise ValueError(
                    f"contextual_policy_duplicate_protocol_record:{record.trial_group_id}:{record.protocol_id}"
                )
            protocols[record.protocol_id] = record
        return grouped

    @staticmethod
    def _validate_pair_surface(
        group_id: str,
        policy_id: str,
        candidate: OrganizationTrialRecord,
        comparator: OrganizationTrialRecord,
    ) -> None:
        if (
            candidate.source_result_hash != comparator.source_result_hash
            or candidate.evidence_refs != comparator.evidence_refs
        ):
            raise ValueError(f"contextual_policy_matched_surface_mismatch:{group_id}:{policy_id}")
