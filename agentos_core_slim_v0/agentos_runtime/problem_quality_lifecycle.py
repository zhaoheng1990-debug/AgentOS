"""Provider-supported problem quality evaluation, trial, and feedback lifecycle."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from agentos_kernel import (
    AgendaFeedback,
    CascadingInvalidationGraph,
    CreditEvent,
    CreditLedger,
    KnowledgeNode,
    OpenProblem,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    ProblemQualityEvaluation,
    ProblemQualityEvalHarness,
    ProblemQualityObservation,
    ProviderBackedRuntimeCognitionLayer,
    ProviderCognitiveTask,
    ProviderTaskRouter,
    SOURCE_GROUP,
)
from agentos_kernel.provider_execution_plane import STATUS_COMPLETED

from .deliberation import DeliberationEventStore
from .problem_definition import DeliberationSeed


PROBLEM_QUALITY_LIFECYCLE_VERSION = "problem_quality_lifecycle_runtime_v0_1"

LIFECYCLE_STATES = {
    "PENDING_AGENDA_REVIEW",
    "APPROVED_FOR_TRIAL",
    "ACTIVE",
    "RESOLVED",
    "PARTIAL",
    "INVALIDATED",
}
TERMINAL_STATES = {"RESOLVED", "PARTIAL", "INVALIDATED"}

_QUALITY_FIELDS = (
    "evidence_grounding",
    "premise_soundness",
    "novelty",
    "falsifiability",
    "discriminatory_power",
    "harness_feasibility",
    "expected_cbit_gain",
    "normalized_cost",
    "negative_transfer_risk",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _is_unit_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0.0 <= float(value) <= 1.0
    )


@dataclass(frozen=True)
class ProblemTrialPlan:
    trial_id: str
    problem_id: str
    required_harnesses: tuple[str, ...]
    measurable_outcomes: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    budget: dict[str, Any]
    rollback_ref: str
    created_at: str = field(default_factory=_utc_now)
    plan_hash: str = ""

    def __post_init__(self) -> None:
        if not all((self.trial_id, self.problem_id, self.rollback_ref)):
            raise ValueError("problem_trial_plan_identity_incomplete")
        if not self.required_harnesses:
            raise ValueError("problem_trial_plan_harnesses_required")
        if not self.measurable_outcomes:
            raise ValueError("problem_trial_plan_measurable_outcomes_required")
        if not self.stop_conditions:
            raise ValueError("problem_trial_plan_stop_conditions_required")
        if not isinstance(self.budget, dict) or not self.budget:
            raise ValueError("problem_trial_plan_budget_required")

    @classmethod
    def create(cls, **values: Any) -> "ProblemTrialPlan":
        created_at = _utc_now()
        committed = {**values, "created_at": created_at}
        return cls(**values, created_at=created_at, plan_hash=_hash_payload(committed))

    def as_dict(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "problem_id": self.problem_id,
            "required_harnesses": list(self.required_harnesses),
            "measurable_outcomes": list(self.measurable_outcomes),
            "stop_conditions": list(self.stop_conditions),
            "budget": self.budget,
            "rollback_ref": self.rollback_ref,
            "created_at": self.created_at,
            "plan_hash": self.plan_hash,
        }


@dataclass(frozen=True)
class ProblemTrialAuthorization:
    trial_id: str
    previous_state: str
    next_state: str
    kernel_authorization_ref: str
    evaluation_hash: str
    plan_hash: str
    receipt_hash: str
    execution_authorized: bool = False

    @classmethod
    def create(
        cls,
        *,
        trial_id: str,
        previous_state: str,
        next_state: str,
        kernel_authorization_ref: str,
        evaluation_hash: str,
        plan_hash: str,
        execution_authorized: bool = False,
    ) -> "ProblemTrialAuthorization":
        payload = {
            "trial_id": trial_id,
            "previous_state": previous_state,
            "next_state": next_state,
            "kernel_authorization_ref": kernel_authorization_ref,
            "evaluation_hash": evaluation_hash,
            "plan_hash": plan_hash,
            "execution_authorized": execution_authorized,
        }
        return cls(**payload, receipt_hash=_hash_payload(payload))

    def as_dict(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "previous_state": self.previous_state,
            "next_state": self.next_state,
            "kernel_authorization_ref": self.kernel_authorization_ref,
            "evaluation_hash": self.evaluation_hash,
            "plan_hash": self.plan_hash,
            "receipt_hash": self.receipt_hash,
            "execution_authorized": self.execution_authorized,
        }


@dataclass(frozen=True)
class ProblemQualityRejectionReceipt:
    rejection_id: str
    problem_id: str
    evaluation_hash: str
    quality_gate_failures: tuple[str, ...]
    reason: str
    kernel_adjudication_ref: str
    evidence_refs: tuple[str, ...]
    created_at: str
    rejection_hash: str
    execution_authorized: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "rejection_id": self.rejection_id,
            "problem_id": self.problem_id,
            "evaluation_hash": self.evaluation_hash,
            "quality_gate_failures": list(self.quality_gate_failures),
            "reason": self.reason,
            "kernel_adjudication_ref": self.kernel_adjudication_ref,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "rejection_hash": self.rejection_hash,
            "execution_authorized": self.execution_authorized,
        }


@dataclass(frozen=True)
class ProblemOutcomeReceipt:
    outcome_id: str
    trial_id: str
    problem_id: str
    trial_resolution: str
    observed_cbit_gain: float
    expected_cbit_gain: float
    prediction_error: float
    rival_explanations_reduced: tuple[str, ...]
    problem_survived: bool
    residual_problems: tuple[OpenProblem, ...]
    normalized_cost: float
    negative_transfer_signal: float
    independent_replication: dict[str, Any]
    interpretation: str
    evidence_refs: tuple[str, ...]
    harness_receipt_refs: tuple[str, ...]
    provider_id: str
    model_id: str
    provider_invocation_receipt: dict[str, Any]
    provider_audit: dict[str, Any]
    created_at: str
    outcome_hash: str
    candidate_only: bool = True
    publication_authorized: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "trial_id": self.trial_id,
            "problem_id": self.problem_id,
            "trial_resolution": self.trial_resolution,
            "observed_cbit_gain": self.observed_cbit_gain,
            "expected_cbit_gain": self.expected_cbit_gain,
            "prediction_error": self.prediction_error,
            "rival_explanations_reduced": list(self.rival_explanations_reduced),
            "problem_survived": self.problem_survived,
            "residual_problems": [item.__dict__ for item in self.residual_problems],
            "normalized_cost": self.normalized_cost,
            "negative_transfer_signal": self.negative_transfer_signal,
            "independent_replication": self.independent_replication,
            "interpretation": self.interpretation,
            "evidence_refs": list(self.evidence_refs),
            "harness_receipt_refs": list(self.harness_receipt_refs),
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "provider_invocation_receipt": self.provider_invocation_receipt,
            "provider_audit": self.provider_audit,
            "created_at": self.created_at,
            "outcome_hash": self.outcome_hash,
            "candidate_only": self.candidate_only,
            "publication_authorized": self.publication_authorized,
        }


@dataclass(frozen=True)
class FeedbackCreditSubject:
    subject_id: str
    subject_kind: str

    def __post_init__(self) -> None:
        if not self.subject_id or self.subject_kind not in {"agent", "provider", "operator"}:
            raise ValueError("feedback_credit_subject_invalid")


@dataclass(frozen=True)
class ProblemQualityFeedbackReceipt:
    feedback_id: str
    problem_id: str
    trial_id: str
    agenda_resolution: str
    residual_problem_ids: tuple[str, ...]
    credit_event_ids: tuple[str, ...]
    invalidation_receipt: dict[str, Any] | None
    expected_cbit_gain: float
    observed_cbit_gain: float | None
    prediction_error: float | None
    evidence_refs: tuple[str, ...]
    created_at: str
    feedback_hash: str
    route_selection_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "problem_id": self.problem_id,
            "trial_id": self.trial_id,
            "agenda_resolution": self.agenda_resolution,
            "residual_problem_ids": list(self.residual_problem_ids),
            "credit_event_ids": list(self.credit_event_ids),
            "invalidation_receipt": self.invalidation_receipt,
            "expected_cbit_gain": self.expected_cbit_gain,
            "observed_cbit_gain": self.observed_cbit_gain,
            "prediction_error": self.prediction_error,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "feedback_hash": self.feedback_hash,
            "route_selection_authority": self.route_selection_authority,
        }


@dataclass(frozen=True)
class ProblemQualityLifecycleSnapshot:
    lifecycle_id: str
    problem_id: str
    state: str
    observations: tuple[ProblemQualityObservation, ...]
    evaluation: ProblemQualityEvaluation | None
    trial_plan: ProblemTrialPlan | None
    authorizations: tuple[ProblemTrialAuthorization, ...]
    active_harness_receipt_refs: tuple[str, ...]
    rejection: ProblemQualityRejectionReceipt | None
    outcome: ProblemOutcomeReceipt | None
    feedback: ProblemQualityFeedbackReceipt | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "lifecycle_id": self.lifecycle_id,
            "problem_id": self.problem_id,
            "state": self.state,
            "observations": [item.as_dict() for item in self.observations],
            "evaluation": self.evaluation.as_dict() if self.evaluation else None,
            "trial_plan": self.trial_plan.as_dict() if self.trial_plan else None,
            "authorizations": [item.as_dict() for item in self.authorizations],
            "active_harness_receipt_refs": list(self.active_harness_receipt_refs),
            "rejection": self.rejection.as_dict() if self.rejection else None,
            "outcome": self.outcome.as_dict() if self.outcome else None,
            "feedback": self.feedback.as_dict() if self.feedback else None,
        }


class ProblemQualityLifecycleRuntime:
    """Kernel-owned lifecycle from pending agenda candidate to trial feedback."""

    module_id = PROBLEM_QUALITY_LIFECYCLE_VERSION
    capabilities = (
        "provider_backed_problem_quality_assessment",
        "prospective_baseline_comparison",
        "kernel_authorized_problem_trial",
        "outcome_feedback",
    )

    def __init__(
        self,
        *,
        lifecycle_id: str,
        seed: DeliberationSeed,
        provider_router: ProviderTaskRouter,
        workspace_root: str | Path,
        admitted_evidence_refs: tuple[str, ...] | None = None,
        evidence_payload: dict[str, Any] | None = None,
        improvement_threshold: float = 0.02,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", lifecycle_id):
            raise ValueError("problem_quality_lifecycle_id_invalid")
        if seed.candidate_state != "PENDING_AGENDA_REVIEW" or seed.execution_authorized:
            raise ValueError("problem_quality_lifecycle_requires_pending_nonexecuting_seed")
        self.lifecycle_id = lifecycle_id
        self.seed = seed
        self.provider_router = provider_router
        self.state = "PENDING_AGENDA_REVIEW"
        self._admitted_evidence_refs = tuple(
            dict.fromkeys(admitted_evidence_refs if admitted_evidence_refs is not None else seed.evidence_refs)
        )
        if not self._admitted_evidence_refs or not set(seed.evidence_refs).issubset(self._admitted_evidence_refs):
            raise ValueError("problem_quality_seed_evidence_not_admitted")
        self._evidence_payload = dict(evidence_payload or {})
        self._cognition_layer = ProviderBackedRuntimeCognitionLayer()
        self._eval_harness = ProblemQualityEvalHarness(improvement_threshold=improvement_threshold)
        self._observations: list[ProblemQualityObservation] = []
        self._evaluation: ProblemQualityEvaluation | None = None
        self._trial_plan: ProblemTrialPlan | None = None
        self._authorizations: list[ProblemTrialAuthorization] = []
        self._active_harness_receipt_refs: tuple[str, ...] = ()
        self._rejection: ProblemQualityRejectionReceipt | None = None
        self._outcome: ProblemOutcomeReceipt | None = None
        self._feedback: ProblemQualityFeedbackReceipt | None = None
        self._event_store = DeliberationEventStore(workspace_root, lifecycle_id)
        self._persist(
            "PROBLEM_QUALITY_LIFECYCLE_INITIALIZED",
            {
                "problem_id": seed.source_problem_id,
                "seed_hash": seed.seed_hash,
                "candidate_state": seed.candidate_state,
                "execution_authorized": False,
                "evidence_payload_hash": _hash_payload(self._evidence_payload),
            },
        )

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    def verify_replay(self) -> dict[str, Any]:
        return self._event_store.verify()

    def assess_problem(
        self,
        *,
        candidate_id: str,
        source_kind: str,
        source_subject_id: str,
        problem_statement: str,
        evidence_refs: tuple[str, ...],
    ) -> ProblemQualityObservation:
        if self.state != "PENDING_AGENDA_REVIEW" or self._evaluation is not None:
            raise RuntimeError("problem_quality_assessment_window_closed")
        if not all((candidate_id, source_kind, source_subject_id, problem_statement)):
            raise ValueError("problem_quality_candidate_identity_incomplete")
        if any(item.candidate_id == candidate_id for item in self._observations):
            raise ValueError(f"duplicate_problem_quality_candidate_id:{candidate_id}")
        if source_kind == SOURCE_GROUP:
            if candidate_id != self.seed.source_problem_id or problem_statement != self.seed.objective:
                raise ValueError("group_problem_must_match_deliberation_seed")
        if not evidence_refs or not set(evidence_refs).issubset(self._admitted_evidence_refs):
            raise ValueError("problem_quality_evidence_not_admitted")

        blind_id = f"blind-{_hash_payload([self.lifecycle_id, candidate_id])[:16]}"
        task = ProviderCognitiveTask(
            task_id=f"{self.lifecycle_id}-quality-{len(self._observations) + 1}",
            task_kind="problem_quality_assessment",
            objective=(
                "Assess this problem candidate prospectively and independently. "
                "Use only admitted evidence and copy evidence_refs exactly from allowed_evidence_refs. "
                "Every numeric quality or risk field must be a finite number in the inclusive 0.0 to 1.0 interval. "
                "Do not infer whether it came from a group, member, or human."
            ),
            inputs={
                "candidate_id": blind_id,
                "problem_statement": problem_statement,
                "scope": self.seed.project_scope,
                "project_evidence": self._evidence_payload,
                "allowed_evidence_refs": list(evidence_refs),
            },
            allowed_evidence=list(evidence_refs),
            expected_schema={
                "type": "object",
                "required": [
                    "candidate_id",
                    "scope",
                    *_QUALITY_FIELDS,
                    "assessment_rationale",
                    "evidence_refs",
                ],
                "properties": {
                    "candidate_id": {"type": "string", "enum": [blind_id]},
                    "scope": {"type": "string", "enum": [self.seed.project_scope]},
                    **{name: {"type": "number", "minimum": 0.0, "maximum": 1.0} for name in _QUALITY_FIELDS},
                    "assessment_rationale": {"type": "string"},
                    "evidence_refs": {"type": "array"},
                },
            },
            failure_semantics="keep_problem_pending_without_quality_observation",
        )
        envelope = self.provider_router.route(task)
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            self._persist(
                "PROBLEM_QUALITY_ASSESSMENT_BLOCKED",
                {
                    "candidate_id_hash": _hash_payload(candidate_id),
                    "status": envelope.status,
                    "validation_errors": list(envelope.validation_errors),
                    "invocation_receipt": envelope.invocation_receipt.as_dict(),
                },
            )
            raise RuntimeError(f"problem_quality_provider_blocked:{envelope.status}")
        payload = dict(envelope.normalized_result or {})
        errors = self._quality_payload_errors(payload, blind_id, evidence_refs)
        audit = self._cognition_layer.audit_operation(
            "problem_quality_assessment",
            {
                "provider_support_receipt": payload,
                "provider_support_receipt_hash": _hash_payload(payload),
                "semantic_consistency_assertions": [
                    {"assertion_id": "candidate", "path": "candidate_id", "operator": "equals", "expected": blind_id},
                    {"assertion_id": "scope", "path": "scope", "operator": "equals", "expected": self.seed.project_scope},
                ],
            },
        )
        if audit["status"] != PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT:
            errors.append(f"problem_quality_provider_audit_failed:{audit['status']}")
        if errors:
            self._persist(
                "PROBLEM_QUALITY_ASSESSMENT_BLOCKED",
                {
                    "candidate_id_hash": _hash_payload(candidate_id),
                    "errors": errors,
                    "provider_audit": audit,
                    "invocation_receipt": envelope.invocation_receipt.as_dict(),
                },
            )
            raise ValueError(";".join(errors))

        invocation = envelope.invocation_receipt.as_dict()
        observation = ProblemQualityObservation(
            observation_id=f"observation-{self.lifecycle_id}-{len(self._observations) + 1}",
            candidate_id=candidate_id,
            source_kind=source_kind,
            source_subject_id=source_subject_id,
            problem_statement=problem_statement,
            scope=self.seed.project_scope,
            evidence_refs=tuple(payload["evidence_refs"]),
            provider_id=envelope.invocation_receipt.provider_id,
            model_id=envelope.invocation_receipt.model_id,
            provider_support_receipt_ref=f"provider-invocation://{invocation['receipt_hash']}",
            **{name: float(payload[name]) for name in _QUALITY_FIELDS},
            assessment_rationale=str(payload["assessment_rationale"]),
        )
        self._observations.append(observation)
        self._persist(
            "PROBLEM_QUALITY_OBSERVATION_ADMITTED",
            {
                "observation": observation.as_dict(),
                "provider_audit": audit,
                "provider_invocation_receipt": invocation,
            },
        )
        return observation

    def freeze_prospective_evaluation(self) -> ProblemQualityEvaluation:
        if self.state != "PENDING_AGENDA_REVIEW":
            raise RuntimeError("problem_quality_evaluation_requires_pending_state")
        if self._evaluation is not None:
            raise RuntimeError("problem_quality_evaluation_already_frozen")
        self._evaluation = self._eval_harness.evaluate(
            f"evaluation-{self.lifecycle_id}",
            tuple(self._observations),
        )
        self._persist("PROBLEM_QUALITY_EVALUATION_FROZEN", self._evaluation.as_dict())
        return self._evaluation

    def approve_for_trial(
        self,
        *,
        trial_plan: ProblemTrialPlan,
        kernel_authorization_ref: str,
    ) -> ProblemTrialAuthorization:
        if self.state != "PENDING_AGENDA_REVIEW" or self._evaluation is None:
            raise RuntimeError("problem_trial_approval_requires_frozen_pending_evaluation")
        if not kernel_authorization_ref:
            raise ValueError("problem_trial_kernel_authorization_required")
        if trial_plan.problem_id != self.seed.source_problem_id:
            raise ValueError("problem_trial_plan_problem_mismatch")
        if not set(self.seed.required_harnesses).issubset(trial_plan.required_harnesses):
            raise ValueError("problem_trial_plan_missing_seed_harness")
        if not self._evaluation.group_trial_gate_passed:
            raise ValueError("problem_trial_quality_gate_failed")
        authorization = ProblemTrialAuthorization.create(
            trial_id=trial_plan.trial_id,
            previous_state=self.state,
            next_state="APPROVED_FOR_TRIAL",
            kernel_authorization_ref=kernel_authorization_ref,
            evaluation_hash=self._evaluation.evaluation_hash,
            plan_hash=trial_plan.plan_hash,
        )
        self._trial_plan = trial_plan
        self._authorizations.append(authorization)
        self.state = "APPROVED_FOR_TRIAL"
        self._persist("PROBLEM_TRIAL_APPROVED", authorization.as_dict())
        return authorization

    def reject_for_trial(
        self,
        *,
        reason: str,
        kernel_adjudication_ref: str,
        evidence_refs: tuple[str, ...],
    ) -> ProblemQualityRejectionReceipt:
        if self.state != "PENDING_AGENDA_REVIEW" or self._evaluation is None:
            raise RuntimeError("problem_quality_rejection_requires_frozen_pending_evaluation")
        if self._evaluation.group_trial_gate_passed:
            raise ValueError("problem_quality_rejection_requires_failed_quality_gate")
        if not reason or not kernel_adjudication_ref or not evidence_refs:
            raise ValueError("problem_quality_rejection_adjudication_and_evidence_required")
        if not set(evidence_refs).issubset(self._admitted_evidence_refs):
            raise ValueError("problem_quality_rejection_evidence_not_admitted")
        created_at = _utc_now()
        committed = {
            "rejection_id": f"rejection-{self.lifecycle_id}",
            "problem_id": self.seed.source_problem_id,
            "evaluation_hash": self._evaluation.evaluation_hash,
            "quality_gate_failures": list(self._evaluation.group_trial_gate_failures),
            "reason": reason,
            "kernel_adjudication_ref": kernel_adjudication_ref,
            "evidence_refs": list(evidence_refs),
            "created_at": created_at,
            "execution_authorized": False,
        }
        self._rejection = ProblemQualityRejectionReceipt(
            rejection_id=committed["rejection_id"],
            problem_id=committed["problem_id"],
            evaluation_hash=committed["evaluation_hash"],
            quality_gate_failures=tuple(committed["quality_gate_failures"]),
            reason=reason,
            kernel_adjudication_ref=kernel_adjudication_ref,
            evidence_refs=evidence_refs,
            created_at=created_at,
            rejection_hash=_hash_payload(committed),
        )
        self.state = "INVALIDATED"
        self._persist("PROBLEM_TRIAL_REJECTED_BY_QUALITY_GATE", self._rejection.as_dict())
        return self._rejection

    def activate_trial(
        self,
        *,
        kernel_execution_authorization_ref: str,
        harness_execution_receipts: dict[str, str],
    ) -> ProblemTrialAuthorization:
        if self.state != "APPROVED_FOR_TRIAL" or self._trial_plan is None or self._evaluation is None:
            raise RuntimeError("problem_trial_activation_requires_approved_trial")
        if not kernel_execution_authorization_ref:
            raise ValueError("problem_trial_execution_authorization_required")
        if not isinstance(harness_execution_receipts, dict):
            raise ValueError("problem_trial_harness_receipts_required")
        missing = set(self._trial_plan.required_harnesses) - set(harness_execution_receipts)
        if missing or any(not harness_execution_receipts.get(name) for name in self._trial_plan.required_harnesses):
            raise ValueError("problem_trial_required_harness_receipt_missing")
        refs = tuple(harness_execution_receipts[name] for name in self._trial_plan.required_harnesses)
        if len(set(refs)) != len(refs):
            raise ValueError("problem_trial_harness_receipts_not_independent")
        authorization = ProblemTrialAuthorization.create(
            trial_id=self._trial_plan.trial_id,
            previous_state=self.state,
            next_state="ACTIVE",
            kernel_authorization_ref=kernel_execution_authorization_ref,
            evaluation_hash=self._evaluation.evaluation_hash,
            plan_hash=self._trial_plan.plan_hash,
            execution_authorized=True,
        )
        self._active_harness_receipt_refs = refs
        self._authorizations.append(authorization)
        self.state = "ACTIVE"
        self._persist(
            "PROBLEM_TRIAL_ACTIVATED",
            {**authorization.as_dict(), "harness_execution_receipts": harness_execution_receipts},
        )
        return authorization

    def record_outcome(
        self,
        *,
        trial_evidence_refs: tuple[str, ...],
        harness_result_summary: dict[str, Any],
        independent_harness_receipt_ref: str,
    ) -> ProblemOutcomeReceipt:
        if self.state != "ACTIVE" or self._trial_plan is None or self._evaluation is None:
            raise RuntimeError("problem_outcome_requires_active_trial")
        if not trial_evidence_refs or not independent_harness_receipt_ref:
            raise ValueError("problem_outcome_trial_evidence_and_replication_required")
        if independent_harness_receipt_ref not in self._active_harness_receipt_refs:
            raise ValueError("problem_outcome_replication_receipt_not_authorized")
        if not isinstance(harness_result_summary, dict) or not harness_result_summary:
            raise ValueError("problem_outcome_harness_summary_required")
        cbit_measurement = harness_result_summary.get("observed_cbit_measurement")
        if (
            not isinstance(cbit_measurement, dict)
            or not _is_unit_number(cbit_measurement.get("value"))
            or not str(cbit_measurement.get("measurement_method", "")).strip()
            or not isinstance(cbit_measurement.get("components"), dict)
        ):
            raise ValueError("problem_outcome_harness_cbit_measurement_invalid")
        harness_observed_cbit = float(cbit_measurement["value"])
        allowed_evidence = tuple(dict.fromkeys((*self._admitted_evidence_refs, *trial_evidence_refs)))
        task = ProviderCognitiveTask(
            task_id=f"{self.lifecycle_id}-outcome",
            task_kind="problem_trial_outcome_interpretation",
            objective=(
                "Interpret the authorized independent Harness trial without granting publication or promotion authority. "
                "Copy evidence_refs exactly from allowed_evidence_refs. Every numeric metric must be a finite number "
                "in the inclusive 0.0 to 1.0 interval. If trial_resolution is PARTIAL, every residual problem must "
                f"have a new problem_id prefixed RESIDUAL_ and must not reuse {self.seed.source_problem_id}. "
                "List a rival in rival_explanations_reduced only when evidence eliminated it; a reduced rival must "
                "not reappear in any residual problem. Use an empty array when no rival was eliminated. Set "
                "observed_cbit_gain exactly to harness_result_summary.observed_cbit_measurement.value. Set "
                "problem_survived=true for RESOLVED or PARTIAL and false only for INVALIDATED."
            ),
            inputs={
                "problem_id": self.seed.source_problem_id,
                "problem_statement": self.seed.objective,
                "rival_explanations": list(self.seed.rival_explanations),
                "prospective_expected_cbit_gain": self.seed.expected_cbit_gain,
                "trial_plan": self._trial_plan.as_dict(),
                "harness_result_summary": harness_result_summary,
                "authorized_harness_receipt_refs": list(self._active_harness_receipt_refs),
                "independent_harness_receipt_ref": independent_harness_receipt_ref,
                "allowed_evidence_refs": list(allowed_evidence),
            },
            allowed_evidence=list(allowed_evidence),
            expected_schema={
                "type": "object",
                "required": [
                    "trial_resolution",
                    "observed_cbit_gain",
                    "rival_explanations_reduced",
                    "problem_survived",
                    "residual_problems",
                    "normalized_cost",
                    "negative_transfer_signal",
                    "independent_replication",
                    "interpretation",
                    "evidence_refs",
                ],
                "properties": {
                    "trial_resolution": {"type": "string", "enum": sorted(TERMINAL_STATES)},
                    "observed_cbit_gain": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "enum": [harness_observed_cbit],
                    },
                    "rival_explanations_reduced": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(self.seed.rival_explanations)},
                    },
                    "problem_survived": {"type": "boolean"},
                    "residual_problems": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": [
                                "problem_id",
                                "statement",
                                "research_object",
                                "scope",
                                "evidence_refs",
                                "rival_explanations",
                            ],
                            "properties": {
                                "problem_id": {"type": "string", "pattern": "^RESIDUAL_[A-Za-z0-9_.-]+$"},
                                "statement": {"type": "string"},
                                "research_object": {"type": "string"},
                                "scope": {"type": "string", "enum": [self.seed.project_scope]},
                                "evidence_refs": {
                                    "type": "array",
                                    "items": {"type": "string", "enum": list(allowed_evidence)},
                                },
                                "rival_explanations": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                    },
                    "normalized_cost": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "negative_transfer_signal": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "independent_replication": {
                        "type": "object",
                        "required": ["performed", "harness_receipt_ref", "outcome"],
                        "properties": {
                            "performed": {"type": "boolean", "enum": [True]},
                            "harness_receipt_ref": {
                                "type": "string",
                                "enum": [independent_harness_receipt_ref],
                            },
                            "outcome": {"type": "string"},
                        },
                    },
                    "interpretation": {"type": "string"},
                    "evidence_refs": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(allowed_evidence)},
                    },
                },
            },
            failure_semantics="keep_trial_active_without_outcome_interpretation",
        )
        envelope = self.provider_router.route(task)
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            self._persist(
                "PROBLEM_OUTCOME_BLOCKED",
                {
                    "status": envelope.status,
                    "validation_errors": list(envelope.validation_errors),
                    "invocation_receipt": envelope.invocation_receipt.as_dict(),
                },
            )
            raise RuntimeError(f"problem_outcome_provider_blocked:{envelope.status}")
        payload = dict(envelope.normalized_result or {})
        errors, residuals = self._outcome_payload_errors(
            payload,
            allowed_evidence,
            independent_harness_receipt_ref,
            harness_observed_cbit,
        )
        audit = self._cognition_layer.audit_operation(
            "problem_trial_outcome_interpretation",
            {
                "provider_support_receipt": payload,
                "provider_support_receipt_hash": _hash_payload(payload),
                "semantic_consistency_assertions": [
                    {
                        "assertion_id": "observed-cbit",
                        "path": "observed_cbit_gain",
                        "operator": "equals",
                        "expected": harness_observed_cbit,
                        "evidence_refs": list(trial_evidence_refs),
                    }
                ],
            },
        )
        if not str(audit.get("status", "")).startswith("PASS_PROVIDER_SUPPORT_RECEIPT"):
            errors.append(f"problem_outcome_provider_audit_failed:{audit.get('status')}")
        if errors:
            self._persist(
                "PROBLEM_OUTCOME_BLOCKED",
                {
                    "errors": errors,
                    "provider_audit": audit,
                    "invocation_receipt": envelope.invocation_receipt.as_dict(),
                },
            )
            raise ValueError(";".join(errors))

        created_at = _utc_now()
        observed = float(payload["observed_cbit_gain"])
        expected = self.seed.expected_cbit_gain
        committed = {
            "outcome_id": f"outcome-{self.lifecycle_id}",
            "trial_id": self._trial_plan.trial_id,
            "problem_id": self.seed.source_problem_id,
            "trial_resolution": payload["trial_resolution"],
            "observed_cbit_gain": observed,
            "expected_cbit_gain": expected,
            "prediction_error": round(abs(expected - observed), 12),
            "rival_explanations_reduced": payload["rival_explanations_reduced"],
            "problem_survived": payload["problem_survived"],
            "residual_problems": [item.__dict__ for item in residuals],
            "normalized_cost": float(payload["normalized_cost"]),
            "negative_transfer_signal": float(payload["negative_transfer_signal"]),
            "independent_replication": payload["independent_replication"],
            "interpretation": payload["interpretation"],
            "evidence_refs": payload["evidence_refs"],
            "harness_receipt_refs": list(self._active_harness_receipt_refs),
            "provider_id": envelope.invocation_receipt.provider_id,
            "model_id": envelope.invocation_receipt.model_id,
            "provider_invocation_receipt": envelope.invocation_receipt.as_dict(),
            "provider_audit": audit,
            "created_at": created_at,
            "candidate_only": True,
            "publication_authorized": False,
        }
        self._outcome = ProblemOutcomeReceipt(
            outcome_id=committed["outcome_id"],
            trial_id=committed["trial_id"],
            problem_id=committed["problem_id"],
            trial_resolution=committed["trial_resolution"],
            observed_cbit_gain=committed["observed_cbit_gain"],
            expected_cbit_gain=committed["expected_cbit_gain"],
            prediction_error=committed["prediction_error"],
            residual_problems=residuals,
            rival_explanations_reduced=tuple(payload["rival_explanations_reduced"]),
            problem_survived=committed["problem_survived"],
            normalized_cost=committed["normalized_cost"],
            negative_transfer_signal=committed["negative_transfer_signal"],
            independent_replication=committed["independent_replication"],
            interpretation=committed["interpretation"],
            evidence_refs=tuple(payload["evidence_refs"]),
            harness_receipt_refs=self._active_harness_receipt_refs,
            provider_id=committed["provider_id"],
            model_id=committed["model_id"],
            provider_invocation_receipt=committed["provider_invocation_receipt"],
            provider_audit=committed["provider_audit"],
            created_at=committed["created_at"],
            outcome_hash=_hash_payload(committed),
            candidate_only=True,
            publication_authorized=False,
        )
        self.state = str(payload["trial_resolution"])
        self._persist("PROBLEM_OUTCOME_RECORDED", self._outcome.as_dict())
        return self._outcome

    def apply_feedback(
        self,
        *,
        agenda_feedback_sink: Any,
        credit_ledger: CreditLedger,
        invalidation_graph: CascadingInvalidationGraph,
        credit_subjects: tuple[FeedbackCreditSubject, ...],
        problem_node_id: str | None = None,
    ) -> ProblemQualityFeedbackReceipt:
        if self.state not in TERMINAL_STATES or (self._outcome is None and self._rejection is None):
            raise RuntimeError("problem_feedback_requires_terminal_outcome")
        if self._feedback is not None:
            raise RuntimeError("problem_feedback_already_applied")
        if not credit_subjects:
            raise ValueError("problem_feedback_credit_subjects_required")
        if self._outcome is not None:
            trial_id = self._outcome.trial_id
            resolution = self._outcome.trial_resolution
            observed_cbit = self._outcome.observed_cbit_gain
            expected_cbit = self._outcome.expected_cbit_gain
            prediction_error = self._outcome.prediction_error
            evidence_refs = self._outcome.evidence_refs
            residual_problems = self._outcome.residual_problems
            adjudication_ref = f"problem-outcome://{self._outcome.outcome_hash}"
        else:
            assert self._rejection is not None
            trial_id = "NO_TRIAL_QUALITY_REJECTION"
            resolution = "INVALIDATED"
            observed_cbit = None
            expected_cbit = self.seed.expected_cbit_gain
            prediction_error = None
            evidence_refs = self._rejection.evidence_refs
            residual_problems = ()
            adjudication_ref = f"problem-quality-rejection://{self._rejection.rejection_hash}"
        feedback = AgendaFeedback(
            candidate_id=f"agenda-{self.seed.source_problem_id}",
            problem_resolution=resolution,
            observed_cbit_gain=observed_cbit,
            evidence_refs=evidence_refs,
            provider_support_receipt_ref=adjudication_ref,
            residual_problems=residual_problems,
        )
        residual_ids = tuple(agenda_feedback_sink.record_agenda_feedback(feedback))

        credit_event_ids: list[str] = []
        if prediction_error is None:
            calibrated = False
            outcome_name = "PROBLEM_QUALITY_GATE_REJECTED"
            weight = 1.0
        else:
            calibrated = prediction_error <= 0.2 and self.state != "INVALIDATED"
            outcome_name = "PROBLEM_FORECAST_CALIBRATED" if calibrated else "PROBLEM_FORECAST_MISALIGNED"
            weight = max(
                0.01,
                min(1.0, 1.0 - prediction_error if calibrated else max(prediction_error, 0.5)),
            )
        for index, subject in enumerate(credit_subjects, start=1):
            event_id = f"problem-quality-{self.lifecycle_id}-{index}"
            credit_ledger.append(
                CreditEvent(
                    event_id=event_id,
                    subject_id=subject.subject_id,
                    subject_kind=subject.subject_kind,
                    outcome=outcome_name,
                    adjudication_ref=adjudication_ref,
                    evidence_refs=evidence_refs,
                    weight=round(weight, 12),
                    source_claim_id=self.seed.source_problem_id,
                )
            )
            credit_event_ids.append(event_id)

        node_id = problem_node_id or f"problem://{self.seed.source_problem_id}"
        try:
            invalidation_graph.node(node_id)
        except KeyError:
            invalidation_graph.register_node(
                KnowledgeNode(
                    node_id=node_id,
                    node_type="problem",
                    scope=self.seed.project_scope,
                    evidence_refs=self.seed.evidence_refs,
                )
            )
        invalidation_receipt = None
        if self.state == "INVALIDATED":
            invalidation_receipt = invalidation_graph.invalidate(
                node_id,
                reason="independent_problem_trial_invalidated_problem_candidate",
                adjudication_ref=adjudication_ref,
                evidence_refs=evidence_refs,
            ).as_dict()

        created_at = _utc_now()
        committed = {
            "feedback_id": f"feedback-{self.lifecycle_id}",
            "problem_id": self.seed.source_problem_id,
            "trial_id": trial_id,
            "agenda_resolution": resolution,
            "residual_problem_ids": list(residual_ids),
            "credit_event_ids": credit_event_ids,
            "invalidation_receipt": invalidation_receipt,
            "expected_cbit_gain": expected_cbit,
            "observed_cbit_gain": observed_cbit,
            "prediction_error": prediction_error,
            "evidence_refs": list(evidence_refs),
            "created_at": created_at,
            "route_selection_authority": False,
        }
        self._feedback = ProblemQualityFeedbackReceipt(
            feedback_id=committed["feedback_id"],
            problem_id=committed["problem_id"],
            trial_id=committed["trial_id"],
            agenda_resolution=committed["agenda_resolution"],
            residual_problem_ids=residual_ids,
            credit_event_ids=tuple(credit_event_ids),
            invalidation_receipt=invalidation_receipt,
            expected_cbit_gain=committed["expected_cbit_gain"],
            observed_cbit_gain=committed["observed_cbit_gain"],
            prediction_error=committed["prediction_error"],
            evidence_refs=evidence_refs,
            created_at=committed["created_at"],
            feedback_hash=_hash_payload(committed),
            route_selection_authority=False,
        )
        self._persist("PROBLEM_QUALITY_FEEDBACK_APPLIED", self._feedback.as_dict())
        return self._feedback

    def snapshot(self) -> ProblemQualityLifecycleSnapshot:
        return ProblemQualityLifecycleSnapshot(
            lifecycle_id=self.lifecycle_id,
            problem_id=self.seed.source_problem_id,
            state=self.state,
            observations=tuple(self._observations),
            evaluation=self._evaluation,
            trial_plan=self._trial_plan,
            authorizations=tuple(self._authorizations),
            active_harness_receipt_refs=self._active_harness_receipt_refs,
            rejection=self._rejection,
            outcome=self._outcome,
            feedback=self._feedback,
        )

    def _quality_payload_errors(
        self,
        payload: dict[str, Any],
        blind_id: str,
        evidence_refs: tuple[str, ...],
    ) -> list[str]:
        errors: list[str] = []
        if payload.get("candidate_id") != blind_id:
            errors.append("problem_quality_blind_candidate_id_mismatch")
        if payload.get("scope") != self.seed.project_scope:
            errors.append("problem_quality_scope_mismatch")
        for field_name in _QUALITY_FIELDS:
            if not _is_unit_number(payload.get(field_name)):
                errors.append(f"problem_quality_metric_invalid:{field_name}")
        if not str(payload.get("assessment_rationale", "")).strip():
            errors.append("problem_quality_assessment_rationale_required")
        refs = payload.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            errors.append("problem_quality_provider_evidence_required")
        elif not set(refs).issubset(evidence_refs):
            errors.append("problem_quality_provider_evidence_not_admitted")
        return errors

    def _outcome_payload_errors(
        self,
        payload: dict[str, Any],
        allowed_evidence: tuple[str, ...],
        independent_harness_receipt_ref: str,
        harness_observed_cbit: float,
    ) -> tuple[list[str], tuple[OpenProblem, ...]]:
        errors: list[str] = []
        if payload.get("trial_resolution") not in TERMINAL_STATES:
            errors.append("problem_outcome_resolution_invalid")
        for field_name in ("observed_cbit_gain", "normalized_cost", "negative_transfer_signal"):
            if not _is_unit_number(payload.get(field_name)):
                errors.append(f"problem_outcome_metric_invalid:{field_name}")
        if _is_unit_number(payload.get("observed_cbit_gain")) and float(payload["observed_cbit_gain"]) != harness_observed_cbit:
            errors.append("problem_outcome_observed_cbit_mismatch_harness_measurement")
        survived = payload.get("problem_survived")
        if not isinstance(survived, bool):
            errors.append("problem_outcome_survival_boolean_required")
        if payload.get("trial_resolution") == "INVALIDATED" and survived is not False:
            errors.append("invalidated_problem_cannot_be_marked_survived")
        if payload.get("trial_resolution") in {"RESOLVED", "PARTIAL"} and survived is not True:
            errors.append("surviving_problem_required_for_resolved_or_partial_outcome")
        reduced = payload.get("rival_explanations_reduced")
        if not isinstance(reduced, list) or any(item not in self.seed.rival_explanations for item in reduced):
            errors.append("problem_outcome_rival_reduction_not_from_seed_set")
        refs = payload.get("evidence_refs")
        if not isinstance(refs, list) or not refs or not set(refs).issubset(allowed_evidence):
            errors.append("problem_outcome_evidence_not_admitted")
        replication = payload.get("independent_replication")
        if (
            not isinstance(replication, dict)
            or replication.get("performed") is not True
            or replication.get("harness_receipt_ref") != independent_harness_receipt_ref
            or not str(replication.get("outcome", "")).strip()
        ):
            errors.append("problem_outcome_independent_replication_invalid")
        if not str(payload.get("interpretation", "")).strip():
            errors.append("problem_outcome_interpretation_required")

        residuals: list[OpenProblem] = []
        residual_payloads = payload.get("residual_problems")
        if not isinstance(residual_payloads, list):
            errors.append("problem_outcome_residual_problems_must_be_array")
            return errors, ()
        if payload.get("trial_resolution") == "PARTIAL" and not residual_payloads:
            errors.append("partial_problem_outcome_requires_residual_problem")
        residual_ids: set[str] = set()
        for index, item in enumerate(residual_payloads):
            if not isinstance(item, dict):
                errors.append(f"problem_outcome_residual_not_object:{index}")
                continue
            required = {"problem_id", "statement", "research_object", "scope", "evidence_refs", "rival_explanations"}
            missing = required - set(item)
            if missing:
                errors.extend(f"problem_outcome_residual_missing_field:{index}:{name}" for name in sorted(missing))
                continue
            problem_id = str(item["problem_id"])
            if (
                problem_id == self.seed.source_problem_id
                or problem_id in residual_ids
                or not re.fullmatch(r"RESIDUAL_[A-Za-z0-9_.-]+", problem_id)
            ):
                errors.append(f"problem_outcome_residual_id_invalid:{problem_id}")
                continue
            residual_ids.add(problem_id)
            if item["scope"] != self.seed.project_scope:
                errors.append(f"problem_outcome_residual_scope_mismatch:{problem_id}")
                continue
            item_refs = item["evidence_refs"]
            if not isinstance(item_refs, list) or not item_refs or not set(item_refs).issubset(allowed_evidence):
                errors.append(f"problem_outcome_residual_evidence_not_admitted:{problem_id}")
                continue
            try:
                residuals.append(
                    OpenProblem(
                        problem_id=problem_id,
                        statement=str(item["statement"]),
                        research_object=str(item["research_object"]),
                        scope=str(item["scope"]),
                        evidence_refs=tuple(item_refs),
                        rival_explanations=tuple(str(value) for value in item["rival_explanations"]),
                    )
                )
            except ValueError as exc:
                errors.append(f"problem_outcome_residual_invalid:{problem_id}:{exc}")
        residual_rivals = {
            rival
            for residual in residuals
            for rival in residual.rival_explanations
        }
        for rival in reduced if isinstance(reduced, list) else []:
            if rival in residual_rivals:
                errors.append("problem_outcome_reduced_rival_reappears_in_residual_problem")
        return errors, tuple(residuals)

    def _persist(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_store.append(event_type, payload)
        self._event_store.write_snapshot(self.snapshot())
