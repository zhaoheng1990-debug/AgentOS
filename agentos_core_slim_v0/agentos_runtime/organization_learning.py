"""Provider-supported, Kernel-owned cognitive organization learning runtime."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from agentos_kernel import (
    COMPONENT_VARIANTS,
    EVIDENCE_TIERS,
    FULL_PROTOCOLS,
    ORGANIZATION_PROTOCOL_VARIANTS,
    CreditProfile,
    OrganizationAttributionReport,
    OrganizationLearningEvaluator,
    OrganizationProtocolEvaluation,
    OrganizationTrialRecord,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    ProviderBackedRuntimeCognitionLayer,
    ProviderCognitiveTask,
    ProviderTaskRouter,
)
from agentos_kernel.provider_execution_plane import STATUS_COMPLETED

from .deliberation import DeliberationEventStore


COGNITIVE_ORGANIZATION_LEARNING_VERSION = "cognitive_organization_learning_runtime_v0_1"
ORGANIZATION_LEARNING_STATES = {
    "INITIALIZED",
    "RECORDS_ADMITTED",
    "DIAGNOSED",
    "POLICY_CANDIDATE",
    "EXPERIMENT_PROPOSED",
    "EXPERIMENT_AUTHORIZED",
    "BLOCKED",
}
_PASS_PROVIDER_AUDITS = {
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
}
_AUTHORITY_KEYS = {
    "accepted",
    "execution_authorized",
    "permission_granted",
    "published",
    "route_selection_authority",
}
_DIRECTIONS = {"BENEFICIAL", "HARMFUL", "UNCERTAIN"}
_CAUSAL_STATES = {"IDENTIFIED_MATCHED_ABLATION", "HYPOTHESIS_ONLY"}
_ARM_PROTOCOLS = {
    "BEST_MEMBER": "SOLO",
    "FIXED_TEAM": "FIXED_TEAM",
    "DYNAMIC_TEAM": "DYNAMIC_TEAM",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _contains_key(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        if any(str(key).lower() in forbidden for key in value):
            return True
        return any(_contains_key(item, forbidden) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_key(item, forbidden) for item in value)
    return False


def _unit(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and 0.0 <= float(value) <= 1.0
    )


def organization_records_from_execution_smoke_result(
    payload: dict[str, Any],
    *,
    context_key: str,
    evidence_tier: str,
    trial_group_id: str,
) -> tuple[OrganizationTrialRecord, ...]:
    """Convert one completed alpha.6 smoke result into three admitted learning records."""

    if not isinstance(payload, dict) or payload.get("status") != "PASS":
        raise ValueError("organization_import_requires_passing_execution_smoke")
    gates = payload.get("gates")
    required_gates = {
        "three_arms_completed",
        "all_arm_replays_valid",
        "execution_replay_valid",
        "harness_owns_observed_cbit",
        "hidden_truth_absent_from_provider_inputs",
    }
    if not isinstance(gates, dict) or not all(gates.get(name) is True for name in required_gates):
        raise ValueError("organization_import_execution_gates_incomplete")
    evaluation = payload.get("counterfactual_evaluation")
    receipts = payload.get("harness_receipts")
    if not isinstance(evaluation, dict) or not isinstance(receipts, list) or len(receipts) != 3:
        raise ValueError("organization_import_trial_payload_incomplete")
    by_arm = {item.get("arm"): item for item in receipts if isinstance(item, dict)}
    if set(by_arm) != set(_ARM_PROTOCOLS):
        raise ValueError("organization_import_requires_exact_three_arms")
    evidence_sets = {tuple(item.get("evidence_refs", [])) for item in receipts}
    if len(evidence_sets) != 1 or not next(iter(evidence_sets)):
        raise ValueError("organization_import_evidence_surface_mismatch")
    evidence_refs = next(iter(evidence_sets))
    score_keys = {
        "BEST_MEMBER": "best_member_score",
        "FIXED_TEAM": "fixed_team_score",
        "DYNAMIC_TEAM": "dynamic_team_score",
    }
    source_result_hash = _hash_payload(payload)
    records = []
    for arm, protocol in _ARM_PROTOCOLS.items():
        receipt = by_arm[arm]
        if receipt.get("harness_owned") is not True or receipt.get("semantic_provider_used") is not False:
            raise ValueError("organization_import_harness_ownership_invalid")
        records.append(
            OrganizationTrialRecord.create(
                record_id=f"record-{trial_group_id}-{protocol.lower()}",
                trial_group_id=trial_group_id,
                context_key=context_key,
                evidence_tier=evidence_tier,
                protocol_id=protocol,
                effectiveness_score=evaluation[score_keys[arm]],
                observed_cbit_gain=receipt["observed_cbit_gain"],
                normalized_cost=receipt["normalized_cost"],
                convergence_steps=receipt["convergence_steps"],
                errors_exposed=receipt["errors_exposed"],
                errors_corrected=receipt["errors_corrected"],
                negative_transfer_opportunities=receipt["negative_transfer_opportunities"],
                negative_transfer_intercepts=receipt["negative_transfer_intercepts"],
                evidence_refs=tuple(evidence_refs),
                harness_receipt_ref=f"harness://{receipt['receipt_hash']}",
                execution_result_hash=receipt["candidate_output_hash"],
                source_result_hash=source_result_hash,
                replay_valid=True,
            )
        )
    return tuple(records)


@dataclass(frozen=True)
class OrganizationLearningSeed:
    context_key: str
    evidence_tier: str
    evidence_refs: tuple[str, ...]
    allowed_experiment_variants: tuple[str, ...]
    minimum_repeated_trials: int = 2
    improvement_threshold: float = 0.02

    def __post_init__(self) -> None:
        if not self.context_key or self.evidence_tier not in EVIDENCE_TIERS:
            raise ValueError("organization_learning_seed_scope_invalid")
        if not self.evidence_refs or len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("organization_learning_seed_evidence_invalid")
        if (
            not self.allowed_experiment_variants
            or len(set(self.allowed_experiment_variants)) != len(self.allowed_experiment_variants)
            or not set(self.allowed_experiment_variants).issubset(ORGANIZATION_PROTOCOL_VARIANTS)
        ):
            raise ValueError("organization_learning_seed_variants_invalid")
        if not set(FULL_PROTOCOLS).issubset(self.allowed_experiment_variants):
            raise ValueError("organization_learning_seed_full_protocols_required")
        if (
            not isinstance(self.minimum_repeated_trials, int)
            or isinstance(self.minimum_repeated_trials, bool)
            or self.minimum_repeated_trials < 2
        ):
            raise ValueError("organization_learning_seed_minimum_trials_invalid")
        if not math.isfinite(self.improvement_threshold) or self.improvement_threshold < 0.0:
            raise ValueError("organization_learning_seed_threshold_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {
            "context_key": self.context_key,
            "evidence_tier": self.evidence_tier,
            "evidence_refs": list(self.evidence_refs),
            "allowed_experiment_variants": list(self.allowed_experiment_variants),
            "minimum_repeated_trials": self.minimum_repeated_trials,
            "improvement_threshold": self.improvement_threshold,
        }


@dataclass(frozen=True)
class OrganizationDiagnosisReceipt:
    diagnosis_id: str
    context_key: str
    evidence_tier: str
    attribution: OrganizationAttributionReport
    protocol_evaluation: OrganizationProtocolEvaluation
    failure_modes: tuple[str, ...]
    component_hypotheses: tuple[dict[str, Any], ...]
    coordination_cost_assessment: str
    next_experiment_variants: tuple[str, ...]
    confidence: float
    evidence_refs: tuple[str, ...]
    provider_id: str
    model_id: str
    provider_invocation_receipt_ref: str
    created_at: str
    diagnosis_hash: str
    causal_claims_bounded: bool = True
    final_decision_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "diagnosis_id": self.diagnosis_id,
            "context_key": self.context_key,
            "evidence_tier": self.evidence_tier,
            "attribution": self.attribution.as_dict(),
            "protocol_evaluation": self.protocol_evaluation.as_dict(),
            "failure_modes": list(self.failure_modes),
            "component_hypotheses": list(self.component_hypotheses),
            "coordination_cost_assessment": self.coordination_cost_assessment,
            "next_experiment_variants": list(self.next_experiment_variants),
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "provider_invocation_receipt_ref": self.provider_invocation_receipt_ref,
            "created_at": self.created_at,
            "diagnosis_hash": self.diagnosis_hash,
            "causal_claims_bounded": self.causal_claims_bounded,
            "final_decision_authority": self.final_decision_authority,
        }


@dataclass(frozen=True)
class OrganizationPolicyCandidate:
    policy_id: str
    context_key: str
    evidence_tier: str
    recommendation: str
    incumbent_protocol: str
    protocol_statistics: dict[str, dict[str, Any]]
    complete_trial_group_ids: tuple[str, ...]
    diagnosis_ref: str
    advisory_credit_hash: str
    advisory_exploration_priorities: tuple[str, ...]
    created_at: str
    policy_hash: str
    candidate_state: str = "PENDING_KERNEL_AUTHORIZATION"
    credit_is_advisory: bool = True
    execution_authorized: bool = False
    route_selection_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "context_key": self.context_key,
            "evidence_tier": self.evidence_tier,
            "recommendation": self.recommendation,
            "incumbent_protocol": self.incumbent_protocol,
            "protocol_statistics": self.protocol_statistics,
            "complete_trial_group_ids": list(self.complete_trial_group_ids),
            "diagnosis_ref": self.diagnosis_ref,
            "advisory_credit_hash": self.advisory_credit_hash,
            "advisory_exploration_priorities": list(self.advisory_exploration_priorities),
            "created_at": self.created_at,
            "policy_hash": self.policy_hash,
            "candidate_state": self.candidate_state,
            "credit_is_advisory": self.credit_is_advisory,
            "execution_authorized": self.execution_authorized,
            "route_selection_authority": self.route_selection_authority,
        }


@dataclass(frozen=True)
class OrganizationExperimentPlan:
    plan_id: str
    context_key: str
    evidence_tier: str
    selected_variants: tuple[str, ...]
    rationale_refs: tuple[str, ...]
    policy_ref: str
    budget: dict[str, Any]
    budget_hash: str
    kernel_authorization_ref: str
    created_at: str
    plan_hash: str
    candidate_state: str
    execution_authorized: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "context_key": self.context_key,
            "evidence_tier": self.evidence_tier,
            "selected_variants": list(self.selected_variants),
            "rationale_refs": list(self.rationale_refs),
            "policy_ref": self.policy_ref,
            "budget": self.budget,
            "budget_hash": self.budget_hash,
            "kernel_authorization_ref": self.kernel_authorization_ref,
            "created_at": self.created_at,
            "plan_hash": self.plan_hash,
            "candidate_state": self.candidate_state,
            "execution_authorized": self.execution_authorized,
        }


@dataclass(frozen=True)
class OrganizationLearningSnapshot:
    runtime_id: str
    state: str
    seed: OrganizationLearningSeed
    records: tuple[OrganizationTrialRecord, ...]
    diagnosis: OrganizationDiagnosisReceipt | None
    policy: OrganizationPolicyCandidate | None
    experiment_plan: OrganizationExperimentPlan | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "state": self.state,
            "seed": self.seed.as_dict(),
            "records": [item.as_dict() for item in self.records],
            "diagnosis": self.diagnosis.as_dict() if self.diagnosis else None,
            "policy": self.policy.as_dict() if self.policy else None,
            "experiment_plan": self.experiment_plan.as_dict() if self.experiment_plan else None,
        }


class CognitiveOrganizationLearningRuntime:
    """Learn bounded organization candidates from admitted trial evidence."""

    module_id = COGNITIVE_ORGANIZATION_LEARNING_VERSION
    capabilities = (
        "matched_component_attribution",
        "repeated_protocol_calibration",
        "provider_supported_failure_diagnosis",
        "kernel_authorized_organization_experiments",
    )

    def __init__(
        self,
        *,
        runtime_id: str,
        seed: OrganizationLearningSeed,
        diagnosis_router: ProviderTaskRouter,
        workspace_root: str | Path,
        advisory_credit_profiles: dict[str, CreditProfile | dict[str, Any]] | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime_id):
            raise ValueError("organization_learning_runtime_id_invalid")
        self.runtime_id = runtime_id
        self.seed = seed
        self.diagnosis_router = diagnosis_router
        self._credit_profiles = self._validate_credit_profiles(advisory_credit_profiles or {})
        self._evaluator = OrganizationLearningEvaluator(
            minimum_repeated_trials=seed.minimum_repeated_trials,
            improvement_threshold=seed.improvement_threshold,
        )
        self._cognition = ProviderBackedRuntimeCognitionLayer()
        self._records: tuple[OrganizationTrialRecord, ...] = ()
        self._diagnosis: OrganizationDiagnosisReceipt | None = None
        self._policy: OrganizationPolicyCandidate | None = None
        self._experiment_plan: OrganizationExperimentPlan | None = None
        self.state = "INITIALIZED"
        root = Path(workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self._event_store = DeliberationEventStore(root / "organization-learning-public", runtime_id)
        self._persist(
            "ORGANIZATION_LEARNING_INITIALIZED",
            {
                "context_key": seed.context_key,
                "evidence_tier": seed.evidence_tier,
                "seed_hash": _hash_payload(seed.as_dict()),
                "advisory_credit_hash": _hash_payload(self._credit_profiles),
            },
        )

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    def verify_replay(self) -> dict[str, Any]:
        return self._event_store.verify()

    def admit_records(self, records: tuple[OrganizationTrialRecord, ...]) -> OrganizationLearningSnapshot:
        if self.state != "INITIALIZED":
            raise RuntimeError("organization_learning_record_admission_closed")
        if not records or len({item.record_id for item in records}) != len(records):
            raise ValueError("organization_learning_records_invalid")
        for item in records:
            if item.context_key != self.seed.context_key or item.evidence_tier != self.seed.evidence_tier:
                raise ValueError("organization_learning_record_scope_or_tier_mismatch")
            if tuple(item.evidence_refs) != tuple(self.seed.evidence_refs):
                raise ValueError("organization_learning_record_evidence_mismatch")
            if not item.replay_valid:
                raise ValueError("organization_learning_record_replay_invalid")
        self._records = tuple(records)
        self.state = "RECORDS_ADMITTED"
        self._persist(
            "ORGANIZATION_TRIAL_RECORDS_ADMITTED",
            {"record_hashes": [item.record_hash for item in records]},
        )
        return self.snapshot()

    def diagnose(self) -> OrganizationDiagnosisReceipt:
        if self.state != "RECORDS_ADMITTED":
            raise RuntimeError("organization_diagnosis_requires_admitted_records")
        attribution = self._evaluator.attribute(
            self._records,
            context_key=self.seed.context_key,
            evidence_tier=self.seed.evidence_tier,
        )
        protocol_evaluation = self._evaluator.evaluate_protocols(
            self._records,
            context_key=self.seed.context_key,
            evidence_tier=self.seed.evidence_tier,
        )
        causal_constraints = []
        for item in attribution.components:
            contribution = item.mean_effectiveness_contribution
            required_direction = (
                "BENEFICIAL"
                if contribution is not None and contribution > 0.0
                else "HARMFUL"
                if contribution is not None and contribution < 0.0
                else "UNCERTAIN"
            )
            causal_constraints.append(
                {
                    "component_id": item.component_id,
                    "kernel_identifiability": item.identifiability,
                    "required_provider_causal_status": (
                        "IDENTIFIED_MATCHED_ABLATION"
                        if item.identifiability == "IDENTIFIED_MATCHED_ABLATION"
                        else "HYPOTHESIS_ONLY"
                    ),
                    "mean_effectiveness_contribution": contribution,
                    "required_direction_if_identified": required_direction,
                }
            )
        provider_evidence_values = sorted(
            {*self.seed.evidence_refs, *(item["alias"] for item in self._evidence_aliases())}
        )
        task = ProviderCognitiveTask(
            task_id=f"{self.runtime_id}-diagnosis",
            task_kind="cognitive_organization_failure_diagnosis",
            objective=(
                "Diagnose bounded organization failure hypotheses from admitted metrics. Treat component causality as "
                "identified only where the Kernel report says IDENTIFIED_MATCHED_ABLATION. Propose only registered "
                "variants and cite evidence only with the supplied E1, E2, ... aliases. The Kernel defines every "
                "component contribution as DYNAMIC_TEAM minus its matched ablation: a positive effectiveness "
                "contribution means BENEFICIAL, a negative contribution means HARMFUL, and zero means UNCERTAIN. "
                "Use this exact sign convention; do not reinterpret it. For each IDENTIFIED_MATCHED_ABLATION item, "
                "copy required_provider_causal_status and required_direction_if_identified from "
                "kernel_causal_constraints exactly, then provide a semantic rationale. For NOT_IDENTIFIABLE items, "
                "the required Provider status is HYPOTHESIS_ONLY. Use only supplied evidence aliases or exact "
                "admitted references."
            ),
            inputs={
                "context_key": self.seed.context_key,
                "evidence_tier": self.seed.evidence_tier,
                "protocol_evaluation": protocol_evaluation.as_dict(),
                "matched_attribution": attribution.as_dict(),
                "kernel_causal_constraints": causal_constraints,
                "record_summaries": [self._record_summary(item) for item in self._records],
                "allowed_experiment_variants": list(self.seed.allowed_experiment_variants),
                "advisory_credit_profiles": self._credit_profiles,
                "evidence_aliases": self._evidence_aliases(),
            },
            allowed_evidence=list(self.seed.evidence_refs),
            expected_schema={
                "type": "object",
                "required": [
                    "failure_modes",
                    "component_hypotheses",
                    "coordination_cost_assessment",
                    "next_experiment_variants",
                    "confidence",
                    "evidence_refs",
                ],
                "properties": {
                    "failure_modes": {"type": "array", "items": {"type": "string"}},
                    "component_hypotheses": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": [
                                "component_id",
                                "direction",
                                "causal_status",
                                "rationale",
                                "evidence_refs",
                            ],
                            "properties": {
                                "component_id": {"type": "string", "enum": list(COMPONENT_VARIANTS)},
                                "direction": {"type": "string", "enum": sorted(_DIRECTIONS)},
                                "causal_status": {"type": "string", "enum": sorted(_CAUSAL_STATES)},
                                "rationale": {"type": "string"},
                                "evidence_refs": {
                                    "type": "array",
                                    "items": {"type": "string", "enum": provider_evidence_values},
                                },
                            },
                        },
                    },
                    "coordination_cost_assessment": {"type": "string"},
                    "next_experiment_variants": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(self.seed.allowed_experiment_variants)},
                    },
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "evidence_refs": {
                        "type": "array",
                        "items": {"type": "string", "enum": provider_evidence_values},
                    },
                },
            },
            failure_semantics="keep_organization_policy_open_without_supported_diagnosis",
        )
        envelope = self.diagnosis_router.route(task)
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            self.state = "BLOCKED"
            self._persist(
                "ORGANIZATION_DIAGNOSIS_BLOCKED",
                {
                    "status": envelope.status,
                    "errors": list(envelope.validation_errors),
                    "invocation_receipt": envelope.invocation_receipt.as_dict(),
                },
            )
            raise RuntimeError(f"organization_diagnosis_provider_blocked:{envelope.status}")
        payload = dict(envelope.normalized_result or {})
        errors = self._diagnosis_errors(payload, attribution)
        audit = self._cognition.audit_operation(
            "cognitive_organization_failure_diagnosis",
            {"provider_support_receipt": payload, "provider_support_receipt_hash": _hash_payload(payload)},
        )
        if audit.get("status") not in _PASS_PROVIDER_AUDITS:
            errors.append(f"organization_diagnosis_provider_audit_failed:{audit.get('status')}")
        if errors:
            self._persist(
                "ORGANIZATION_DIAGNOSIS_BLOCKED",
                {"errors": errors, "provider_audit": audit},
            )
            raise ValueError(";".join(errors))
        normalized_evidence_refs = self._resolve_provider_refs(payload["evidence_refs"])
        normalized_hypotheses = []
        for item in payload["component_hypotheses"]:
            normalized = dict(item)
            normalized["provider_cited_evidence_refs"] = list(item["evidence_refs"])
            normalized["evidence_refs"] = list(self._resolve_provider_refs(item["evidence_refs"]))
            normalized_hypotheses.append(normalized)
        created_at = _utc_now()
        invocation = envelope.invocation_receipt.as_dict()
        committed = {
            "diagnosis_id": f"diagnosis-{self.runtime_id}",
            "context_key": self.seed.context_key,
            "evidence_tier": self.seed.evidence_tier,
            "attribution_hash": attribution.report_hash,
            "protocol_evaluation_hash": protocol_evaluation.evaluation_hash,
            "provider_payload_hash": _hash_payload(payload),
            "provider_invocation_receipt_ref": f"provider-invocation://{invocation['receipt_hash']}",
            "created_at": created_at,
        }
        self._diagnosis = OrganizationDiagnosisReceipt(
            diagnosis_id=committed["diagnosis_id"],
            context_key=self.seed.context_key,
            evidence_tier=self.seed.evidence_tier,
            attribution=attribution,
            protocol_evaluation=protocol_evaluation,
            failure_modes=tuple(payload["failure_modes"]),
            component_hypotheses=tuple(normalized_hypotheses),
            coordination_cost_assessment=payload["coordination_cost_assessment"],
            next_experiment_variants=tuple(payload["next_experiment_variants"]),
            confidence=float(payload["confidence"]),
            evidence_refs=tuple(normalized_evidence_refs),
            provider_id=invocation["provider_id"],
            model_id=invocation["model_id"],
            provider_invocation_receipt_ref=committed["provider_invocation_receipt_ref"],
            created_at=created_at,
            diagnosis_hash=_hash_payload(committed),
        )
        self.state = "DIAGNOSED"
        self._persist("ORGANIZATION_DIAGNOSIS_ADMITTED", self._diagnosis.as_dict())
        return self._diagnosis

    def synthesize_policy(self) -> OrganizationPolicyCandidate:
        if self.state != "DIAGNOSED" or self._diagnosis is None:
            raise RuntimeError("organization_policy_requires_admitted_diagnosis")
        evaluation = self._diagnosis.protocol_evaluation
        created_at = _utc_now()
        committed = {
            "policy_id": f"policy-{self.runtime_id}",
            "context_key": self.seed.context_key,
            "evidence_tier": self.seed.evidence_tier,
            "recommendation": evaluation.recommendation,
            "incumbent_protocol": evaluation.incumbent_protocol,
            "protocol_evaluation_hash": evaluation.evaluation_hash,
            "diagnosis_ref": f"organization-diagnosis://{self._diagnosis.diagnosis_hash}",
            "advisory_credit_hash": _hash_payload(self._credit_profiles),
            "advisory_exploration_priorities": self._credit_exploration_priorities(evaluation),
            "created_at": created_at,
            "candidate_state": "PENDING_KERNEL_AUTHORIZATION",
            "execution_authorized": False,
            "route_selection_authority": False,
        }
        self._policy = OrganizationPolicyCandidate(
            policy_id=committed["policy_id"],
            context_key=self.seed.context_key,
            evidence_tier=self.seed.evidence_tier,
            recommendation=evaluation.recommendation,
            incumbent_protocol=evaluation.incumbent_protocol,
            protocol_statistics=evaluation.protocol_statistics,
            complete_trial_group_ids=evaluation.complete_trial_group_ids,
            diagnosis_ref=committed["diagnosis_ref"],
            advisory_credit_hash=committed["advisory_credit_hash"],
            advisory_exploration_priorities=tuple(committed["advisory_exploration_priorities"]),
            created_at=created_at,
            policy_hash=_hash_payload(committed),
        )
        self.state = "POLICY_CANDIDATE"
        self._persist("ORGANIZATION_POLICY_CANDIDATE_CREATED", self._policy.as_dict())
        return self._policy

    def propose_experiment(
        self,
        *,
        max_variants: int,
        experiment_family: str = "ANY",
    ) -> OrganizationExperimentPlan:
        if self.state != "POLICY_CANDIDATE" or self._policy is None or self._diagnosis is None:
            raise RuntimeError("organization_experiment_requires_policy_candidate")
        if not isinstance(max_variants, int) or isinstance(max_variants, bool) or max_variants < 1:
            raise ValueError("organization_experiment_max_variants_invalid")
        if experiment_family not in {"ANY", "MATCHED_ABLATION"}:
            raise ValueError("organization_experiment_family_invalid")
        candidates = list(dict.fromkeys(self._diagnosis.next_experiment_variants))
        if experiment_family == "MATCHED_ABLATION":
            candidates = [item for item in candidates if item.startswith("DYNAMIC_NO_")]
            for variant in COMPONENT_VARIANTS.values():
                if variant in self.seed.allowed_experiment_variants and variant not in candidates:
                    candidates.append(variant)
        elif self._policy.recommendation == "REQUIRE_EXPLORATION":
            complete_count = len(self._policy.complete_trial_group_ids)
            if complete_count < self.seed.minimum_repeated_trials:
                for protocol in FULL_PROTOCOLS:
                    if protocol not in candidates:
                        candidates.append(protocol)
        selected = tuple(candidates[:max_variants])
        if not selected or not set(selected).issubset(self.seed.allowed_experiment_variants):
            raise ValueError("organization_experiment_selected_variants_invalid")
        created_at = _utc_now()
        committed = {
            "plan_id": f"experiment-{self.runtime_id}",
            "context_key": self.seed.context_key,
            "evidence_tier": self.seed.evidence_tier,
            "selected_variants": list(selected),
            "experiment_family": experiment_family,
            "rationale_refs": [
                f"organization-policy://{self._policy.policy_hash}",
                f"organization-diagnosis://{self._diagnosis.diagnosis_hash}",
            ],
            "policy_ref": f"organization-policy://{self._policy.policy_hash}",
            "budget": {},
            "budget_hash": "",
            "kernel_authorization_ref": "",
            "created_at": created_at,
            "candidate_state": "PENDING_KERNEL_AUTHORIZATION",
            "execution_authorized": False,
        }
        self._experiment_plan = OrganizationExperimentPlan(
            plan_id=committed["plan_id"],
            context_key=self.seed.context_key,
            evidence_tier=self.seed.evidence_tier,
            selected_variants=selected,
            rationale_refs=tuple(committed["rationale_refs"]),
            policy_ref=committed["policy_ref"],
            budget={},
            budget_hash="",
            kernel_authorization_ref="",
            created_at=created_at,
            plan_hash=_hash_payload(committed),
            candidate_state="PENDING_KERNEL_AUTHORIZATION",
            execution_authorized=False,
        )
        self.state = "EXPERIMENT_PROPOSED"
        self._persist("ORGANIZATION_EXPERIMENT_PROPOSED", self._experiment_plan.as_dict())
        return self._experiment_plan

    def authorize_experiment(
        self,
        *,
        kernel_authorization_ref: str,
        budget: dict[str, Any],
    ) -> OrganizationExperimentPlan:
        if self.state != "EXPERIMENT_PROPOSED" or self._experiment_plan is None:
            raise RuntimeError("organization_experiment_authorization_requires_proposal")
        if not kernel_authorization_ref.startswith("kernel://"):
            raise ValueError("organization_experiment_kernel_authorization_ref_invalid")
        max_runs = budget.get("max_trial_runs") if isinstance(budget, dict) else None
        max_calls = budget.get("max_provider_calls_per_run") if isinstance(budget, dict) else None
        requires_dynamic_baseline = any(
            variant.startswith("DYNAMIC_NO_")
            for variant in self._experiment_plan.selected_variants
        ) and "DYNAMIC_TEAM" not in self._experiment_plan.selected_variants
        required_runs = len(self._experiment_plan.selected_variants) + int(requires_dynamic_baseline)
        if (
            not isinstance(max_runs, int)
            or isinstance(max_runs, bool)
            or max_runs < required_runs
            or not isinstance(max_calls, int)
            or isinstance(max_calls, bool)
            or max_calls < 1
        ):
            raise ValueError("organization_experiment_budget_invalid")
        created_at = _utc_now()
        budget_hash = _hash_payload(budget)
        committed = {
            "plan_id": self._experiment_plan.plan_id,
            "context_key": self.seed.context_key,
            "evidence_tier": self.seed.evidence_tier,
            "selected_variants": list(self._experiment_plan.selected_variants),
            "rationale_refs": list(self._experiment_plan.rationale_refs),
            "policy_ref": self._experiment_plan.policy_ref,
            "budget": dict(budget),
            "budget_hash": budget_hash,
            "kernel_authorization_ref": kernel_authorization_ref,
            "created_at": created_at,
            "candidate_state": "AUTHORIZED_FOR_EXPERIMENT",
            "execution_authorized": True,
        }
        self._experiment_plan = OrganizationExperimentPlan(
            plan_id=self._experiment_plan.plan_id,
            context_key=self.seed.context_key,
            evidence_tier=self.seed.evidence_tier,
            selected_variants=self._experiment_plan.selected_variants,
            rationale_refs=self._experiment_plan.rationale_refs,
            policy_ref=self._experiment_plan.policy_ref,
            budget=dict(budget),
            budget_hash=budget_hash,
            kernel_authorization_ref=kernel_authorization_ref,
            created_at=created_at,
            plan_hash=_hash_payload(committed),
            candidate_state="AUTHORIZED_FOR_EXPERIMENT",
            execution_authorized=True,
        )
        self.state = "EXPERIMENT_AUTHORIZED"
        self._persist("ORGANIZATION_EXPERIMENT_AUTHORIZED", self._experiment_plan.as_dict())
        return self._experiment_plan

    def snapshot(self) -> OrganizationLearningSnapshot:
        return OrganizationLearningSnapshot(
            runtime_id=self.runtime_id,
            state=self.state,
            seed=self.seed,
            records=self._records,
            diagnosis=self._diagnosis,
            policy=self._policy,
            experiment_plan=self._experiment_plan,
        )

    def _diagnosis_errors(
        self,
        payload: dict[str, Any],
        attribution: OrganizationAttributionReport,
    ) -> list[str]:
        errors: list[str] = []
        if _contains_key(payload, _AUTHORITY_KEYS):
            errors.append("organization_diagnosis_authority_claim_forbidden")
        if not isinstance(payload.get("failure_modes"), list) or not all(
            isinstance(item, str) and item.strip() for item in payload.get("failure_modes", [])
        ):
            errors.append("organization_diagnosis_failure_modes_invalid")
        if not isinstance(payload.get("coordination_cost_assessment"), str) or not payload.get(
            "coordination_cost_assessment", ""
        ).strip():
            errors.append("organization_diagnosis_coordination_assessment_invalid")
        if not _unit(payload.get("confidence")):
            errors.append("organization_diagnosis_confidence_invalid")
        refs = payload.get("evidence_refs")
        if not self._provider_refs_valid(refs):
            errors.append("organization_diagnosis_evidence_refs_invalid")
        variants = payload.get("next_experiment_variants")
        if (
            not isinstance(variants, list)
            or not variants
            or len(set(variants)) != len(variants)
            or not set(variants).issubset(self.seed.allowed_experiment_variants)
        ):
            errors.append("organization_diagnosis_unknown_experiment_variant")
        hypotheses = payload.get("component_hypotheses")
        attribution_by_component = {item.component_id: item for item in attribution.components}
        if not isinstance(hypotheses, list) or not hypotheses:
            errors.append("organization_diagnosis_component_hypotheses_invalid")
            return errors
        seen: set[str] = set()
        for item in hypotheses:
            if not isinstance(item, dict):
                errors.append("organization_diagnosis_component_hypothesis_invalid")
                continue
            component_id = item.get("component_id")
            if component_id not in COMPONENT_VARIANTS or component_id in seen:
                errors.append("organization_diagnosis_component_id_invalid")
                continue
            seen.add(component_id)
            if item.get("direction") not in _DIRECTIONS or item.get("causal_status") not in _CAUSAL_STATES:
                errors.append("organization_diagnosis_component_claim_invalid")
                continue
            if (
                item["causal_status"] == "IDENTIFIED_MATCHED_ABLATION"
                and attribution_by_component[component_id].identifiability != "IDENTIFIED_MATCHED_ABLATION"
            ):
                errors.append("organization_diagnosis_unsupported_causal_claim")
            if item["causal_status"] == "IDENTIFIED_MATCHED_ABLATION":
                contribution = attribution_by_component[component_id].mean_effectiveness_contribution
                expected_direction = (
                    "BENEFICIAL" if contribution is not None and contribution > 0.0
                    else "HARMFUL" if contribution is not None and contribution < 0.0
                    else "UNCERTAIN"
                )
                if item["direction"] != expected_direction:
                    errors.append("organization_diagnosis_causal_direction_conflict")
            item_refs = item.get("evidence_refs")
            if not self._provider_refs_valid(item_refs):
                errors.append("organization_diagnosis_component_evidence_invalid")
        return errors

    def _evidence_aliases(self) -> list[dict[str, str]]:
        return [
            {"alias": f"E{index}", "evidence_ref": ref}
            for index, ref in enumerate(self.seed.evidence_refs, start=1)
        ]

    def _provider_refs_valid(self, refs: Any) -> bool:
        if (
            not isinstance(refs, list)
            or not refs
            or len(refs) != len(set(refs))
            or not all(isinstance(item, str) for item in refs)
        ):
            return False
        admitted = set(self.seed.evidence_refs)
        aliases = {item["alias"] for item in self._evidence_aliases()}
        return set(refs).issubset(admitted | aliases)

    def _resolve_provider_refs(self, refs: list[str]) -> tuple[str, ...]:
        alias_map = {item["alias"]: item["evidence_ref"] for item in self._evidence_aliases()}
        return tuple(alias_map.get(ref, ref) for ref in refs)

    @staticmethod
    def _record_summary(item: OrganizationTrialRecord) -> dict[str, Any]:
        return {
            "record_id": item.record_id,
            "trial_group_id": item.trial_group_id,
            "protocol_id": item.protocol_id,
            "effectiveness_score": item.effectiveness_score,
            "observed_cbit_gain": item.observed_cbit_gain,
            "normalized_cost": item.normalized_cost,
            "convergence_steps": item.convergence_steps,
            "record_hash": item.record_hash,
        }

    @staticmethod
    def _validate_credit_profiles(
        profiles: dict[str, CreditProfile | dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        normalized: dict[str, dict[str, Any]] = {}
        for protocol, profile in profiles.items():
            if protocol not in FULL_PROTOCOLS:
                raise ValueError(f"organization_credit_unknown_protocol:{protocol}")
            payload = profile.as_dict() if isinstance(profile, CreditProfile) else dict(profile)
            if payload.get("advisory_only") is not True or payload.get("selection_authority") is not False:
                raise ValueError("organization_credit_must_be_advisory_only")
            event_count = payload.get("event_count")
            weights = (payload.get("positive_weight"), payload.get("negative_weight"))
            if (
                not isinstance(payload.get("subject_id"), str)
                or not payload["subject_id"]
                or not isinstance(payload.get("subject_kind"), str)
                or not payload["subject_kind"]
                or not isinstance(event_count, int)
                or isinstance(event_count, bool)
                or event_count < 0
                or not all(
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(float(value))
                    and value >= 0.0
                    for value in weights
                )
                or not _unit(payload.get("trust_score"))
                or not _unit(payload.get("confidence"))
            ):
                raise ValueError("organization_credit_profile_invalid")
            normalized[protocol] = payload
        return normalized

    def _credit_exploration_priorities(
        self,
        evaluation: OrganizationProtocolEvaluation,
    ) -> list[str]:
        priorities = []
        for protocol in FULL_PROTOCOLS:
            observed = evaluation.protocol_statistics[protocol].get("mean_effectiveness")
            profile = self._credit_profiles.get(protocol)
            if profile is None:
                score = 1.0
            else:
                trust = float(profile.get("trust_score", 0.5))
                confidence = float(profile.get("confidence", 0.0))
                disagreement = abs((observed if observed is not None else 0.5) - trust)
                score = 0.6 * disagreement + 0.4 * (1.0 - confidence)
            priorities.append((protocol, round(score, 12)))
        priorities.sort(key=lambda item: (-item[1], FULL_PROTOCOLS.index(item[0])))
        return [protocol for protocol, _ in priorities]

    def _persist(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_store.append(event_type, payload)
        self._event_store.write_snapshot(self.snapshot())
