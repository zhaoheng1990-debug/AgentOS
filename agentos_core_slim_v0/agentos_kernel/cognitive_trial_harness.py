"""Frozen held-out finding Harness for equal-protocol cognitive team trials."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any


COGNITIVE_TRIAL_HARNESS_VERSION = "frozen_finding_trial_harness_v0_1"
FINDING_STATES = {"SUPPORTED", "REJECTED", "UNRESOLVED"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class TrialFindingCatalogEntry:
    finding_id: str
    statement: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.finding_id) or not self.statement.strip():
            raise ValueError("trial_finding_catalog_entry_invalid")

    def as_dict(self) -> dict[str, str]:
        return {"finding_id": self.finding_id, "statement": self.statement}


@dataclass(frozen=True)
class TrialFindingTruth:
    finding_id: str
    expected_state: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.finding_id):
            raise ValueError("trial_finding_truth_id_invalid")
        if self.expected_state not in FINDING_STATES:
            raise ValueError(f"trial_finding_truth_state_invalid:{self.expected_state}")


@dataclass(frozen=True)
class CognitiveTrialHarnessReceipt:
    receipt_id: str
    harness_id: str
    trial_id: str
    arm: str
    candidate_output_hash: str
    finding_accuracy: float
    rejection_accuracy: float
    uncertainty_preservation: float
    observed_cbit_gain: float
    errors_exposed: int
    errors_corrected: int
    negative_transfer_opportunities: int
    negative_transfer_intercepts: int
    normalized_cost: float
    convergence_steps: int
    evidence_refs: tuple[str, ...]
    execution_receipt_refs: tuple[str, ...]
    finding_results: tuple[dict[str, Any], ...]
    created_at: str
    receipt_hash: str
    harness_owned: bool = True
    semantic_provider_used: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "harness_id": self.harness_id,
            "trial_id": self.trial_id,
            "arm": self.arm,
            "candidate_output_hash": self.candidate_output_hash,
            "finding_accuracy": self.finding_accuracy,
            "rejection_accuracy": self.rejection_accuracy,
            "uncertainty_preservation": self.uncertainty_preservation,
            "observed_cbit_gain": self.observed_cbit_gain,
            "errors_exposed": self.errors_exposed,
            "errors_corrected": self.errors_corrected,
            "negative_transfer_opportunities": self.negative_transfer_opportunities,
            "negative_transfer_intercepts": self.negative_transfer_intercepts,
            "normalized_cost": self.normalized_cost,
            "convergence_steps": self.convergence_steps,
            "evidence_refs": list(self.evidence_refs),
            "execution_receipt_refs": list(self.execution_receipt_refs),
            "finding_results": list(self.finding_results),
            "created_at": self.created_at,
            "receipt_hash": self.receipt_hash,
            "harness_owned": self.harness_owned,
            "semantic_provider_used": self.semantic_provider_used,
        }


class FrozenFindingTrialHarness:
    """Mechanically score blind candidate classifications against held-out truth."""

    module_id = COGNITIVE_TRIAL_HARNESS_VERSION
    capabilities = ("held_out_finding_classification", "observed_cbit_measurement")

    def __init__(self, harness_id: str, truths: tuple[TrialFindingTruth, ...]) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", harness_id):
            raise ValueError("trial_harness_id_invalid")
        if not truths or len({item.finding_id for item in truths}) != len(truths):
            raise ValueError("trial_harness_truths_invalid")
        self.harness_id = harness_id
        self._truths = {item.finding_id: item.expected_state for item in truths}

    def evaluate(
        self,
        *,
        trial_id: str,
        arm: str,
        candidate_output: dict[str, Any],
        finding_catalog: tuple[TrialFindingCatalogEntry, ...],
        evidence_refs: tuple[str, ...],
        provider_call_count: int,
        max_provider_calls: int,
        convergence_steps: int,
        execution_receipt_refs: tuple[str, ...],
    ) -> CognitiveTrialHarnessReceipt:
        if not all((trial_id, arm, evidence_refs, execution_receipt_refs)):
            raise ValueError("trial_harness_evaluation_identity_incomplete")
        if not isinstance(candidate_output, dict):
            raise ValueError("trial_candidate_output_required")
        catalog_ids = tuple(item.finding_id for item in finding_catalog)
        if not catalog_ids or len(set(catalog_ids)) != len(catalog_ids):
            raise ValueError("trial_finding_catalog_invalid")
        if set(catalog_ids) != set(self._truths):
            raise ValueError("trial_truth_catalog_mismatch")
        if not isinstance(provider_call_count, int) or isinstance(provider_call_count, bool) or provider_call_count < 1:
            raise ValueError("trial_provider_call_count_invalid")
        if not isinstance(max_provider_calls, int) or isinstance(max_provider_calls, bool) or max_provider_calls < 1:
            raise ValueError("trial_provider_budget_invalid")
        if provider_call_count > max_provider_calls:
            raise ValueError("trial_provider_budget_exceeded")
        if not isinstance(convergence_steps, int) or isinstance(convergence_steps, bool) or convergence_steps < 1:
            raise ValueError("trial_convergence_steps_invalid")

        expected_evidence = tuple(evidence_refs)
        candidate_evidence = candidate_output.get("evidence_refs")
        if (
            not isinstance(candidate_evidence, list)
            or len(candidate_evidence) != len(expected_evidence)
            or not all(isinstance(item, str) for item in candidate_evidence)
            or set(candidate_evidence) != set(expected_evidence)
        ):
            raise ValueError("candidate_evidence_surface_mismatch")

        classifications = self._candidate_classifications(candidate_output, set(catalog_ids))
        correct = {
            finding_id: classifications[finding_id] == self._truths[finding_id]
            for finding_id in catalog_ids
        }
        finding_accuracy = sum(correct.values()) / len(catalog_ids)
        rejected_ids = {key for key, value in self._truths.items() if value == "REJECTED"}
        unresolved_ids = {key for key, value in self._truths.items() if value == "UNRESOLVED"}
        non_supported_ids = rejected_ids | unresolved_ids
        rejection_accuracy = (
            sum(correct[item] for item in rejected_ids) / len(rejected_ids) if rejected_ids else 1.0
        )
        uncertainty_preservation = (
            sum(correct[item] for item in unresolved_ids) / len(unresolved_ids) if unresolved_ids else 1.0
        )
        observed_cbit = (
            0.60 * finding_accuracy
            + 0.20 * rejection_accuracy
            + 0.20 * uncertainty_preservation
        )
        finding_results = tuple(
            {
                "finding_id": finding_id,
                "observed_state": classifications[finding_id],
                "correct": correct[finding_id],
            }
            for finding_id in catalog_ids
        )
        created_at = _utc_now()
        committed = {
            "receipt_id": f"harness-{trial_id}-{arm.lower()}",
            "harness_id": self.harness_id,
            "trial_id": trial_id,
            "arm": arm,
            "candidate_output_hash": _hash_payload(candidate_output),
            "finding_accuracy": round(finding_accuracy, 12),
            "rejection_accuracy": round(rejection_accuracy, 12),
            "uncertainty_preservation": round(uncertainty_preservation, 12),
            "observed_cbit_gain": round(observed_cbit, 12),
            "errors_exposed": len(rejected_ids),
            "errors_corrected": sum(correct[item] for item in rejected_ids),
            "negative_transfer_opportunities": len(non_supported_ids),
            "negative_transfer_intercepts": sum(correct[item] for item in non_supported_ids),
            "normalized_cost": round(provider_call_count / max_provider_calls, 12),
            "convergence_steps": convergence_steps,
            "evidence_refs": list(expected_evidence),
            "execution_receipt_refs": list(execution_receipt_refs),
            "finding_results": list(finding_results),
            "created_at": created_at,
            "harness_owned": True,
            "semantic_provider_used": False,
        }
        return CognitiveTrialHarnessReceipt(
            receipt_id=committed["receipt_id"],
            harness_id=self.harness_id,
            trial_id=trial_id,
            arm=arm,
            candidate_output_hash=committed["candidate_output_hash"],
            finding_accuracy=committed["finding_accuracy"],
            rejection_accuracy=committed["rejection_accuracy"],
            uncertainty_preservation=committed["uncertainty_preservation"],
            observed_cbit_gain=committed["observed_cbit_gain"],
            errors_exposed=committed["errors_exposed"],
            errors_corrected=committed["errors_corrected"],
            negative_transfer_opportunities=committed["negative_transfer_opportunities"],
            negative_transfer_intercepts=committed["negative_transfer_intercepts"],
            normalized_cost=committed["normalized_cost"],
            convergence_steps=convergence_steps,
            evidence_refs=expected_evidence,
            execution_receipt_refs=execution_receipt_refs,
            finding_results=finding_results,
            created_at=created_at,
            receipt_hash=_hash_payload(committed),
        )

    @staticmethod
    def _candidate_classifications(
        candidate_output: dict[str, Any],
        catalog_ids: set[str],
    ) -> dict[str, str]:
        fields = {
            "supported_finding_ids": "SUPPORTED",
            "rejected_finding_ids": "REJECTED",
            "unresolved_finding_ids": "UNRESOLVED",
        }
        groups: dict[str, set[str]] = {}
        for field_name in fields:
            values = candidate_output.get(field_name)
            if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                raise ValueError(f"candidate_finding_classification_invalid:{field_name}")
            if len(values) != len(set(values)):
                raise ValueError(f"candidate_finding_classification_duplicate:{field_name}")
            groups[field_name] = set(values)
        all_values = [item for values in groups.values() for item in values]
        if len(all_values) != len(set(all_values)):
            raise ValueError("candidate_finding_classifications_overlap")
        if set(all_values) != catalog_ids:
            raise ValueError("candidate_finding_coverage_mismatch")
        return {
            finding_id: state
            for field_name, state in fields.items()
            for finding_id in groups[field_name]
        }
