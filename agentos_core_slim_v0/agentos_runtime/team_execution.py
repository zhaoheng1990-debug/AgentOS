"""Kernel-authorized three-arm cognitive team execution and trial runtime."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

from agentos_kernel import (
    ARM_BEST_MEMBER,
    ARM_DYNAMIC_TEAM,
    ARM_FIXED_TEAM,
    AgentDescriptor,
    AgentRegistry,
    CognitiveTrialHarnessReceipt,
    CreditEvent,
    CreditLedger,
    FrozenFindingTrialHarness,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    ProviderBackedRuntimeCognitionLayer,
    ProviderCognitiveTask,
    ProviderTaskRouter,
    TeamCounterfactualEvaluation,
    TrialFindingCatalogEntry,
)
from agentos_kernel.provider_execution_plane import STATUS_COMPLETED

from .cognitive_roles import CognitiveAgent, standard_role_contract
from .coordination import CognitiveCoordinationRuntime
from .deliberation import CognitiveAgentRuntimeAdapter, CognitiveDeliberationSession, DeliberationEventStore
from .team_formation import CognitiveTeamFormationRuntime, TeamCreditFeedbackReceipt


COGNITIVE_TEAM_EXECUTION_VERSION = "cognitive_team_execution_trial_runtime_v0_2"
EXECUTION_STATES = {"READY", "ARMS_EXECUTED", "EVALUATED", "FEEDBACK_APPLIED", "BLOCKED"}
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
_HIDDEN_TRUTH_KEYS = {"expected_state", "ground_truth", "trial_truth", "truths"}
_CANDIDATE_REQUIRED = (
    "answer",
    "supported_finding_ids",
    "rejected_finding_ids",
    "unresolved_finding_ids",
    "rival_explanations",
    "falsifier",
    "evidence_refs",
    "uncertainties",
)


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


def _candidate_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": list(_CANDIDATE_REQUIRED),
        "properties": {
            "answer": {"type": "string", "minLength": 1},
            "supported_finding_ids": {"type": "array", "items": {"type": "string"}},
            "rejected_finding_ids": {"type": "array", "items": {"type": "string"}},
            "unresolved_finding_ids": {"type": "array", "items": {"type": "string"}},
            "rival_explanations": {"type": "array", "items": {"type": "string"}},
            "falsifier": {"type": "string", "minLength": 1},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "uncertainties": {"type": "array", "items": {"type": "string"}},
        },
    }


@dataclass(frozen=True)
class CognitiveExecutionTrialSpec:
    trial_id: str
    objective: str
    project_scope: str
    evidence_refs: tuple[str, ...]
    evidence_payload: dict[str, Any]
    finding_catalog: tuple[TrialFindingCatalogEntry, ...]
    frozen_gate_refs: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    budget: dict[str, Any]
    kernel_authorization_ref: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.trial_id):
            raise ValueError("execution_trial_id_invalid")
        if not all((self.objective, self.project_scope, self.kernel_authorization_ref)):
            raise ValueError("execution_trial_identity_incomplete")
        if not self.evidence_refs or len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("execution_trial_evidence_invalid")
        if not self.finding_catalog or len({item.finding_id for item in self.finding_catalog}) != len(
            self.finding_catalog
        ):
            raise ValueError("execution_trial_finding_catalog_invalid")
        if not self.frozen_gate_refs or not self.stop_conditions:
            raise ValueError("execution_trial_gates_and_stop_conditions_required")
        max_calls = self.budget.get("max_provider_calls_per_arm")
        retries = self.budget.get("max_retries_per_stage", 0)
        if not isinstance(max_calls, int) or isinstance(max_calls, bool) or max_calls < 1:
            raise ValueError("execution_trial_provider_budget_invalid")
        if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0:
            raise ValueError("execution_trial_retry_budget_invalid")
        if _contains_key(self.evidence_payload, _HIDDEN_TRUTH_KEYS):
            raise ValueError("execution_trial_hidden_truth_in_provider_evidence")

    @property
    def budget_hash(self) -> str:
        return _hash_payload(self.budget)

    def as_dict(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "objective": self.objective,
            "project_scope": self.project_scope,
            "evidence_refs": list(self.evidence_refs),
            "evidence_payload": self.evidence_payload,
            "finding_catalog": [item.as_dict() for item in self.finding_catalog],
            "frozen_gate_refs": list(self.frozen_gate_refs),
            "stop_conditions": list(self.stop_conditions),
            "budget": self.budget,
            "kernel_authorization_ref": self.kernel_authorization_ref,
            "budget_hash": self.budget_hash,
        }


@dataclass(frozen=True)
class CognitiveArmExecutionResult:
    result_id: str
    execution_id: str
    trial_id: str
    arm: str
    subject_id: str
    agent_ids: tuple[str, ...]
    context_isolation_keys: tuple[str, ...]
    candidate_output: dict[str, Any]
    formal_messages: tuple[dict[str, Any], ...]
    execution_receipts: tuple[dict[str, Any], ...]
    execution_receipt_refs: tuple[str, ...]
    provider_call_count: int
    convergence_steps: int
    replay_verification: dict[str, Any]
    coordinator_agent_id: str
    coordinator_protocol_hash: str
    coordination_receipt_count: int
    created_at: str
    result_hash: str
    status: str = "COMPLETED"
    context_isolated: bool = True
    execution_authorized: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "execution_id": self.execution_id,
            "trial_id": self.trial_id,
            "arm": self.arm,
            "subject_id": self.subject_id,
            "agent_ids": list(self.agent_ids),
            "context_isolation_keys": list(self.context_isolation_keys),
            "candidate_output": self.candidate_output,
            "formal_messages": list(self.formal_messages),
            "execution_receipts": list(self.execution_receipts),
            "execution_receipt_refs": list(self.execution_receipt_refs),
            "provider_call_count": self.provider_call_count,
            "convergence_steps": self.convergence_steps,
            "replay_verification": self.replay_verification,
            "coordinator_agent_id": self.coordinator_agent_id,
            "coordinator_protocol_hash": self.coordinator_protocol_hash,
            "coordination_receipt_count": self.coordination_receipt_count,
            "created_at": self.created_at,
            "result_hash": self.result_hash,
            "status": self.status,
            "context_isolated": self.context_isolated,
            "execution_authorized": self.execution_authorized,
        }


@dataclass(frozen=True)
class ExecutionTrialFeedbackReceipt:
    feedback_id: str
    evaluation_hash: str
    formation_feedback_hash: str
    fixed_team_event_id: str
    formation_provider_event_id: str
    fixed_team_outcome: str
    formation_provider_outcome: str
    evidence_refs: tuple[str, ...]
    created_at: str
    feedback_hash: str
    route_selection_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "evaluation_hash": self.evaluation_hash,
            "formation_feedback_hash": self.formation_feedback_hash,
            "fixed_team_event_id": self.fixed_team_event_id,
            "formation_provider_event_id": self.formation_provider_event_id,
            "fixed_team_outcome": self.fixed_team_outcome,
            "formation_provider_outcome": self.formation_provider_outcome,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "feedback_hash": self.feedback_hash,
            "route_selection_authority": self.route_selection_authority,
        }


@dataclass(frozen=True)
class CognitiveTeamExecutionSnapshot:
    execution_id: str
    state: str
    best_member_agent_id: str
    arm_results: tuple[CognitiveArmExecutionResult, ...]
    harness_receipts: tuple[CognitiveTrialHarnessReceipt, ...]
    evaluation: TeamCounterfactualEvaluation | None
    feedback: ExecutionTrialFeedbackReceipt | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "state": self.state,
            "best_member_agent_id": self.best_member_agent_id,
            "arm_results": [item.as_dict() for item in self.arm_results],
            "harness_receipts": [item.as_dict() for item in self.harness_receipts],
            "evaluation": self.evaluation.as_dict() if self.evaluation else None,
            "feedback": self.feedback.as_dict() if self.feedback else None,
        }


CoordinationRuntimeFactory = Callable[[str, Path], CognitiveCoordinationRuntime]


class CognitiveTeamExecutionRuntime:
    """Execute authorized solo/fixed/dynamic arms and measure held-out performance."""

    module_id = COGNITIVE_TEAM_EXECUTION_VERSION
    capabilities = (
        "authorized_team_execution_bridge",
        "isolated_three_arm_execution",
        "held_out_observed_cbit",
        "individual_team_and_formation_credit",
    )

    def __init__(
        self,
        *,
        execution_id: str,
        formation_runtime: CognitiveTeamFormationRuntime,
        registry: AgentRegistry,
        trial_spec: CognitiveExecutionTrialSpec,
        team_adapters: dict[str, CognitiveAgentRuntimeAdapter],
        solo_routers: dict[str, ProviderTaskRouter],
        normalization_routers: dict[str, ProviderTaskRouter],
        trial_harness: FrozenFindingTrialHarness,
        workspace_root: str | Path,
        coordination_runtime_factory: CoordinationRuntimeFactory | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", execution_id):
            raise ValueError("cognitive_team_execution_id_invalid")
        formation = formation_runtime.snapshot()
        if formation.state != "TEAM_AUTHORIZED" or formation.decision is None or formation.proposal is None:
            raise ValueError("execution_requires_kernel_authorized_team_formation")
        if trial_spec.budget_hash != formation.decision.budget_hash:
            raise ValueError("execution_trial_budget_not_kernel_authorized")
        if trial_spec.project_scope != formation_runtime.seed.project_scope:
            raise ValueError("execution_trial_scope_not_formation_scope")
        if trial_spec.evidence_refs != formation_runtime.admitted_evidence_refs:
            raise ValueError("execution_trial_evidence_not_formation_evidence")
        dynamic_ids = formation.proposal.selected_agent_ids
        fixed_ids = formation_runtime.fixed_team_agent_ids
        required_team_ids = set((*dynamic_ids, *fixed_ids))
        if set(team_adapters) != required_team_ids:
            raise ValueError("execution_team_adapter_binding_incomplete")
        synthesizer_ids = {
            registry.get(agent_id).agent_id
            for agent_id in required_team_ids
            if registry.get(agent_id).role == "SYNTHESIZER"
        }
        if set(normalization_routers) != synthesizer_ids:
            raise ValueError("execution_normalization_router_binding_incomplete")
        baseline_ids = {item.agent_id for item in formation.independent_baselines}
        if not solo_routers or not set(solo_routers).issubset(baseline_ids):
            raise ValueError("execution_solo_router_binding_invalid")
        self.execution_id = execution_id
        self.formation_runtime = formation_runtime
        self.registry = registry
        self.trial_spec = trial_spec
        self.team_adapters = dict(team_adapters)
        self.solo_routers = dict(solo_routers)
        self.normalization_routers = dict(normalization_routers)
        self.trial_harness = trial_harness
        self.coordination_runtime_factory = coordination_runtime_factory
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.state = "READY"
        self._best_member_agent_id = ""
        self._arm_results: list[CognitiveArmExecutionResult] = []
        self._harness_receipts: list[CognitiveTrialHarnessReceipt] = []
        self._evaluation: TeamCounterfactualEvaluation | None = None
        self._feedback: ExecutionTrialFeedbackReceipt | None = None
        self._arm_event_stores: dict[str, DeliberationEventStore] = {}
        self._cognition = ProviderBackedRuntimeCognitionLayer()
        self._event_store = DeliberationEventStore(self.workspace_root / "execution-public", execution_id)
        self._persist(
            "COGNITIVE_TEAM_EXECUTION_INITIALIZED",
            {
                "formation_decision_hash": formation.decision.decision_hash,
                "trial_spec_hash": _hash_payload(trial_spec.as_dict()),
                "budget_hash": trial_spec.budget_hash,
            },
        )

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    def verify_replay(self) -> dict[str, Any]:
        return self._event_store.verify()

    def verify_arm_replays(self) -> dict[str, dict[str, Any]]:
        return {arm: store.verify() for arm, store in self._arm_event_stores.items()}

    def execute_arms(self, *, best_member_agent_id: str) -> CognitiveTeamExecutionSnapshot:
        if self.state != "READY":
            raise RuntimeError("cognitive_team_execution_window_closed")
        baseline_ids = {item.agent_id for item in self.formation_runtime.snapshot().independent_baselines}
        if best_member_agent_id not in baseline_ids:
            raise ValueError("execution_best_member_not_independent_baseline")
        if best_member_agent_id not in self.solo_routers:
            raise ValueError("execution_best_member_router_missing")
        self._best_member_agent_id = best_member_agent_id
        formation = self.formation_runtime.snapshot()
        try:
            results = [
                self._execute_solo(best_member_agent_id),
                self._execute_team(
                    ARM_FIXED_TEAM,
                    self.formation_runtime.fixed_team_id,
                    self.formation_runtime.fixed_team_agent_ids,
                ),
                self._execute_team(
                    ARM_DYNAMIC_TEAM,
                    formation.proposal.team_id,
                    formation.proposal.selected_agent_ids,
                ),
            ]
            team_results = [item for item in results if item.arm != ARM_BEST_MEMBER]
            if len({item.coordinator_protocol_hash for item in team_results}) != 1:
                raise ValueError("execution_team_coordinator_protocol_mismatch")
        except Exception as exc:
            self.state = "BLOCKED"
            self._persist(
                "COGNITIVE_TEAM_EXECUTION_BLOCKED",
                {"error_type": type(exc).__name__, "error": str(exc)[:500]},
            )
            raise
        self._arm_results = results
        self.state = "ARMS_EXECUTED"
        self._persist(
            "COGNITIVE_TRIAL_ARMS_EXECUTED",
            {"arm_result_hashes": [item.result_hash for item in results]},
        )
        return self.snapshot()

    def evaluate_arms(self) -> TeamCounterfactualEvaluation:
        if self.state != "ARMS_EXECUTED":
            raise RuntimeError("cognitive_trial_evaluation_requires_executed_arms")
        replay_results = self.verify_arm_replays()
        expected_arms = {ARM_BEST_MEMBER, ARM_FIXED_TEAM, ARM_DYNAMIC_TEAM}
        if set(replay_results) != expected_arms or not all(item["valid"] for item in replay_results.values()):
            raise ValueError("execution_arm_replay_invalid")
        max_calls = self.trial_spec.budget["max_provider_calls_per_arm"]
        receipts: list[CognitiveTrialHarnessReceipt] = []
        observations = []
        for result in self._arm_results:
            receipt = self.trial_harness.evaluate(
                trial_id=self.trial_spec.trial_id,
                arm=result.arm,
                candidate_output=result.candidate_output,
                finding_catalog=self.trial_spec.finding_catalog,
                evidence_refs=self.trial_spec.evidence_refs,
                provider_call_count=result.provider_call_count,
                max_provider_calls=max_calls,
                convergence_steps=result.convergence_steps,
                execution_receipt_refs=result.execution_receipt_refs,
            )
            receipts.append(receipt)
            observations.append(
                self.formation_runtime.assess_trial_arm(
                    trial_id=self.trial_spec.trial_id,
                    arm=result.arm,
                    subject_id=result.subject_id,
                    agent_ids=result.agent_ids,
                    harness_protocol_id=self.trial_harness.module_id,
                    budget_hash=self.trial_spec.budget_hash,
                    harness_receipt_ref=f"harness://{receipt.receipt_hash}",
                    harness_summary={
                        "observed_cbit_gain": receipt.observed_cbit_gain,
                        "errors_exposed": receipt.errors_exposed,
                        "errors_corrected": receipt.errors_corrected,
                        "negative_transfer_opportunities": receipt.negative_transfer_opportunities,
                        "negative_transfer_intercepts": receipt.negative_transfer_intercepts,
                        "normalized_cost": receipt.normalized_cost,
                        "convergence_steps": receipt.convergence_steps,
                        "finding_accuracy": receipt.finding_accuracy,
                        "rejection_accuracy": receipt.rejection_accuracy,
                        "uncertainty_preservation": receipt.uncertainty_preservation,
                        "candidate_output_hash": receipt.candidate_output_hash,
                    },
                    semantic_artifact=result.candidate_output,
                )
            )
        self._harness_receipts = receipts
        self._evaluation = self.formation_runtime.evaluate_counterfactual(tuple(observations))
        self.state = "EVALUATED"
        self._persist(
            "COGNITIVE_TRIAL_EVALUATED",
            {
                "harness_receipt_hashes": [item.receipt_hash for item in receipts],
                "evaluation_hash": self._evaluation.evaluation_hash,
            },
        )
        return self._evaluation

    def apply_credit_feedback(self, credit_ledger: CreditLedger) -> ExecutionTrialFeedbackReceipt:
        if self.state != "EVALUATED" or self._evaluation is None:
            raise RuntimeError("execution_trial_credit_requires_evaluation")
        fixed_event_id = f"execution-fixed-team-{self.execution_id}"
        provider_event_id = f"execution-formation-provider-{self.execution_id}"
        formation_event_ids = (
            f"team-formation-individual-{self.formation_runtime.runtime_id}",
            f"team-formation-combination-{self.formation_runtime.runtime_id}",
        )
        formation = self.formation_runtime.snapshot()
        subjects = (
            (self._evaluation.best_member_subject_id, "agent"),
            (self._evaluation.dynamic_team_subject_id, "team"),
            (self.formation_runtime.fixed_team_id, "team"),
            (formation.proposal.provider_id, "provider"),
        )
        for event_id in (*formation_event_ids, fixed_event_id, provider_event_id):
            if credit_ledger.has_event(event_id):
                raise ValueError(f"execution_trial_credit_event_already_exists:{event_id}")
        for subject_id, kind in subjects:
            profile = credit_ledger.profile(subject_id)
            if profile.event_count and profile.subject_kind != kind:
                raise ValueError(f"execution_trial_credit_subject_kind_conflict:{subject_id}")

        fixed_delta = round(self._evaluation.fixed_team_score - self._evaluation.best_member_score, 12)
        fixed_outcome = self._relative_outcome(
            fixed_delta,
            "FIXED_TEAM_EXECUTION_VALIDATED",
            "FIXED_TEAM_EXECUTION_UNDERPERFORMED",
            "FIXED_TEAM_EXECUTION_INCONCLUSIVE",
        )
        formation_outcome = self._formation_outcome(self._evaluation)
        formation_feedback: TeamCreditFeedbackReceipt = self.formation_runtime.apply_credit_feedback(credit_ledger)
        adjudication_ref = f"team-evaluation://{self._evaluation.evaluation_hash}"
        credit_ledger.append(
            CreditEvent(
                event_id=fixed_event_id,
                subject_id=self.formation_runtime.fixed_team_id,
                subject_kind="team",
                outcome=fixed_outcome,
                adjudication_ref=adjudication_ref,
                evidence_refs=self._evaluation.evidence_refs,
                weight=max(0.01, min(1.0, abs(fixed_delta))),
                source_claim_id=self.formation_runtime.seed.source_problem_id,
            )
        )
        provider_weight = max(
            0.01,
            min(
                1.0,
                abs(self._evaluation.delta_dynamic_vs_best_member)
                + abs(self._evaluation.delta_dynamic_vs_fixed_team),
            ),
        )
        credit_ledger.append(
            CreditEvent(
                event_id=provider_event_id,
                subject_id=formation.proposal.provider_id,
                subject_kind="provider",
                outcome=formation_outcome,
                adjudication_ref=adjudication_ref,
                evidence_refs=self._evaluation.evidence_refs,
                weight=provider_weight,
                source_claim_id=self.formation_runtime.seed.source_problem_id,
            )
        )
        created_at = _utc_now()
        committed = {
            "feedback_id": f"execution-feedback-{self.execution_id}",
            "evaluation_hash": self._evaluation.evaluation_hash,
            "formation_feedback_hash": formation_feedback.feedback_hash,
            "fixed_team_event_id": fixed_event_id,
            "formation_provider_event_id": provider_event_id,
            "fixed_team_outcome": fixed_outcome,
            "formation_provider_outcome": formation_outcome,
            "evidence_refs": list(self._evaluation.evidence_refs),
            "created_at": created_at,
            "route_selection_authority": False,
        }
        self._feedback = ExecutionTrialFeedbackReceipt(
            feedback_id=committed["feedback_id"],
            evaluation_hash=self._evaluation.evaluation_hash,
            formation_feedback_hash=formation_feedback.feedback_hash,
            fixed_team_event_id=fixed_event_id,
            formation_provider_event_id=provider_event_id,
            fixed_team_outcome=fixed_outcome,
            formation_provider_outcome=formation_outcome,
            evidence_refs=self._evaluation.evidence_refs,
            created_at=created_at,
            feedback_hash=_hash_payload(committed),
        )
        self.state = "FEEDBACK_APPLIED"
        self._persist("COGNITIVE_TRIAL_CREDIT_APPLIED", self._feedback.as_dict())
        return self._feedback

    def snapshot(self) -> CognitiveTeamExecutionSnapshot:
        return CognitiveTeamExecutionSnapshot(
            execution_id=self.execution_id,
            state=self.state,
            best_member_agent_id=self._best_member_agent_id,
            arm_results=tuple(self._arm_results),
            harness_receipts=tuple(self._harness_receipts),
            evaluation=self._evaluation,
            feedback=self._feedback,
        )

    def _execute_solo(self, agent_id: str) -> CognitiveArmExecutionResult:
        descriptor = self.registry.get(agent_id)
        task = ProviderCognitiveTask(
            task_id=f"{self.execution_id}-solo",
            task_kind="solo_cognitive_trial",
            objective=(
                "Independently answer the trial and classify every public finding ID exactly once. Preserve rejected "
                "and unresolved states; do not claim execution or publication authority."
            ),
            inputs=self._provider_trial_inputs(),
            allowed_evidence=list(self.trial_spec.evidence_refs),
            expected_schema=_candidate_schema(),
            budget=self.trial_spec.budget,
            failure_semantics="block_best_member_arm_without_provider_candidate",
        )
        envelope = self.solo_routers[agent_id].route(task)
        candidate = self._admit_provider_candidate(envelope, descriptor, "solo_cognitive_trial")
        invocation = envelope.invocation_receipt.as_dict()
        store = DeliberationEventStore(
            self.workspace_root / ARM_BEST_MEMBER.lower() / "public",
            f"{self.execution_id}-solo",
        )
        event = store.append(
            "SOLO_COGNITIVE_TRIAL_COMPLETED",
            {
                "agent_id": descriptor.agent_id,
                "provider_id": descriptor.provider_id,
                "model_id": descriptor.model_id,
                "candidate_output": candidate,
                "invocation_receipt": invocation,
            },
        )
        store.write_snapshot(self.snapshot())
        self._arm_event_stores[ARM_BEST_MEMBER] = store
        return self._arm_result(
            arm=ARM_BEST_MEMBER,
            subject_id=agent_id,
            descriptors=(descriptor,),
            candidate=candidate,
            messages=(),
            receipts=(invocation,),
            receipt_refs=(
                f"provider-invocation://{invocation['receipt_hash']}",
                f"deliberation-event://{event['event_hash']}",
            ),
            provider_calls=1,
            convergence_steps=1,
            replay=store.verify(),
            coordinator=None,
            coordination_receipt_count=0,
        )

    def _execute_team(
        self,
        arm: str,
        subject_id: str,
        agent_ids: tuple[str, ...],
    ) -> CognitiveArmExecutionResult:
        descriptors = tuple(self.registry.get(agent_id) for agent_id in agent_ids)
        agents = tuple(self._cognitive_agent(item, arm) for item in descriptors)
        coordinator = (
            self.coordination_runtime_factory(arm, self.workspace_root / arm.lower() / "coordinator")
            if self.coordination_runtime_factory
            else None
        )
        session = CognitiveDeliberationSession(
            session_id=f"{self.execution_id}-{arm.lower()}",
            objective=self.trial_spec.objective,
            project_scope=self.trial_spec.project_scope,
            frozen_gate_refs=self.trial_spec.frozen_gate_refs,
            evidence_refs=self.trial_spec.evidence_refs,
            evidence_payload=self.trial_spec.evidence_payload,
            agents=agents,
            adapters={agent_id: self.team_adapters[agent_id] for agent_id in agent_ids},
            workspace_root=self.workspace_root / arm.lower() / "private",
            kernel_authorization_ref=f"{self.trial_spec.kernel_authorization_ref}/{arm.lower()}",
            coordination_runtime=coordinator,
        )
        snapshot = session.run_to_candidate(
            max_retries_per_stage=self.trial_spec.budget.get("max_retries_per_stage", 0)
        )
        if snapshot.stage != "CANDIDATE" or snapshot.candidate_state != "PENDING_EPISTEMIC_REVIEW":
            raise RuntimeError(f"execution_team_arm_not_candidate:{arm}:{snapshot.stage}")
        self._arm_event_stores[arm] = DeliberationEventStore(
            session.public_store_path.parent,
            session.public_store_path.name,
        )
        synthesizer = next(item for item in descriptors if item.role == "SYNTHESIZER")
        task = ProviderCognitiveTask(
            task_id=f"{self.execution_id}-{arm.lower()}-normalize",
            task_kind="team_trial_output_normalization",
            objective=(
                "Normalize the formal team receipts into one candidate. Classify every public finding ID exactly once "
                "without adding evidence or final-state authority. Cite evidence only with supplied E1, E2, ... aliases."
            ),
            inputs={
                **self._provider_trial_inputs(),
                "formal_messages": [item.as_dict() for item in snapshot.messages],
                "execution_receipt_refs": [item.receipt_hash for item in snapshot.execution_receipts],
            },
            allowed_evidence=list(self.trial_spec.evidence_refs),
            expected_schema=_candidate_schema(),
            budget=self.trial_spec.budget,
            failure_semantics="block_team_arm_without_normalized_candidate",
        )
        envelope = self.normalization_routers[synthesizer.agent_id].route(task)
        candidate = self._admit_provider_candidate(envelope, synthesizer, "team_trial_output_normalization")
        invocation = envelope.invocation_receipt.as_dict()
        execution_receipts = tuple(item.as_dict() for item in snapshot.execution_receipts)
        coordination_receipts = tuple(item.as_dict() for item in snapshot.coordination_receipts)
        provider_calls = len(execution_receipts) + len(coordination_receipts) + 1
        max_calls = self.trial_spec.budget["max_provider_calls_per_arm"]
        if provider_calls > max_calls:
            raise ValueError(f"execution_arm_provider_budget_exceeded:{arm}:{provider_calls}:{max_calls}")
        receipt_refs = tuple(
            [f"execution://{item.receipt_hash}" for item in snapshot.execution_receipts]
            + [f"coordination://{item.receipt_hash}" for item in snapshot.coordination_receipts]
            + [f"provider-invocation://{invocation['receipt_hash']}"]
        )
        return self._arm_result(
            arm=arm,
            subject_id=subject_id,
            descriptors=descriptors,
            candidate=candidate,
            messages=tuple(item.as_dict() for item in snapshot.messages),
            receipts=(*execution_receipts, *coordination_receipts, invocation),
            receipt_refs=receipt_refs,
            provider_calls=provider_calls,
            convergence_steps=provider_calls,
            replay=session.verify_replay(),
            coordinator=coordinator,
            coordination_receipt_count=len(coordination_receipts),
        )

    def _admit_provider_candidate(
        self,
        envelope: Any,
        descriptor: AgentDescriptor,
        operation_id: str,
    ) -> dict[str, Any]:
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            raise RuntimeError(f"execution_candidate_provider_blocked:{operation_id}:{envelope.status}")
        if (
            envelope.invocation_receipt.provider_id != descriptor.provider_id
            or envelope.invocation_receipt.model_id != descriptor.model_id
        ):
            raise ValueError(f"execution_candidate_provider_binding_mismatch:{descriptor.agent_id}")
        candidate = dict(envelope.normalized_result or {})
        errors = self._candidate_errors(candidate)
        audit = self._cognition.audit_operation(
            operation_id,
            {"provider_support_receipt": candidate, "provider_support_receipt_hash": _hash_payload(candidate)},
        )
        if audit.get("status") not in _PASS_PROVIDER_AUDITS:
            errors.append(f"execution_candidate_provider_audit_failed:{audit.get('status')}")
        if errors:
            raise ValueError(";".join(errors))
        candidate["provider_cited_evidence_refs"] = list(candidate["evidence_refs"])
        candidate["evidence_refs"] = list(self.trial_spec.evidence_refs)
        return candidate

    def _candidate_errors(self, candidate: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        for name in ("answer", "falsifier"):
            if not isinstance(candidate.get(name), str) or not candidate[name].strip():
                errors.append(f"execution_candidate_string_required:{name}")
        array_fields = (
            "supported_finding_ids",
            "rejected_finding_ids",
            "unresolved_finding_ids",
            "rival_explanations",
            "evidence_refs",
            "uncertainties",
        )
        for name in array_fields:
            if not isinstance(candidate.get(name), list) or not all(
                isinstance(item, str) for item in candidate[name]
            ):
                errors.append(f"execution_candidate_string_array_required:{name}")
        if errors:
            return errors
        groups = [
            candidate["supported_finding_ids"],
            candidate["rejected_finding_ids"],
            candidate["unresolved_finding_ids"],
        ]
        flattened = [item for group in groups for item in group]
        catalog_ids = {item.finding_id for item in self.trial_spec.finding_catalog}
        if len(flattened) != len(set(flattened)):
            errors.append("execution_candidate_finding_classifications_overlap")
        if set(flattened) != catalog_ids:
            errors.append("execution_candidate_finding_coverage_mismatch")
        refs = candidate["evidence_refs"]
        resolved_refs = self._resolve_provider_refs(refs)
        if not refs or len(refs) != len(set(refs)):
            errors.append("execution_candidate_evidence_refs_invalid")
        elif not set(resolved_refs).issubset(self.trial_spec.evidence_refs):
            errors.append("execution_candidate_unadmitted_evidence_ref")
        if _contains_key(candidate, _AUTHORITY_KEYS):
            errors.append("execution_candidate_authority_forbidden")
        if _contains_key(candidate, _HIDDEN_TRUTH_KEYS):
            errors.append("execution_candidate_hidden_truth_forbidden")
        return errors

    def _provider_trial_inputs(self) -> dict[str, Any]:
        return {
            "objective": self.trial_spec.objective,
            "project_scope": self.trial_spec.project_scope,
            "evidence_payload": self.trial_spec.evidence_payload,
            "finding_catalog": [item.as_dict() for item in self.trial_spec.finding_catalog],
            "frozen_gate_refs": list(self.trial_spec.frozen_gate_refs),
            "stop_conditions": list(self.trial_spec.stop_conditions),
            "allowed_evidence_refs": list(self.trial_spec.evidence_refs),
            "evidence_aliases": self._evidence_aliases(),
            "budget": self.trial_spec.budget,
        }

    def _evidence_aliases(self) -> list[dict[str, str]]:
        return [
            {"alias": f"E{index}", "evidence_ref": ref}
            for index, ref in enumerate(self.trial_spec.evidence_refs, start=1)
        ]

    def _resolve_provider_refs(self, refs: list[str]) -> tuple[str, ...]:
        aliases = {item["alias"]: item["evidence_ref"] for item in self._evidence_aliases()}
        return tuple(aliases.get(ref, ref) for ref in refs)

    def _cognitive_agent(self, descriptor: AgentDescriptor, arm: str) -> CognitiveAgent:
        if not descriptor.model_id:
            raise ValueError(f"execution_agent_model_binding_required:{descriptor.agent_id}")
        return CognitiveAgent(
            descriptor=descriptor,
            contract=standard_role_contract(descriptor.role),
            model_id=descriptor.model_id,
            private_memory_namespace=f"{self.execution_id}-{arm.lower()}-{descriptor.agent_id}",
            harness_capabilities=(descriptor.harness_id, *descriptor.capabilities),
            credit_subject_id=f"credit-{descriptor.agent_id}",
        )

    def _arm_result(
        self,
        *,
        arm: str,
        subject_id: str,
        descriptors: tuple[AgentDescriptor, ...],
        candidate: dict[str, Any],
        messages: tuple[dict[str, Any], ...],
        receipts: tuple[dict[str, Any], ...],
        receipt_refs: tuple[str, ...],
        provider_calls: int,
        convergence_steps: int,
        replay: dict[str, Any],
        coordinator: CognitiveCoordinationRuntime | None,
        coordination_receipt_count: int,
    ) -> CognitiveArmExecutionResult:
        contexts = tuple(item.context_isolation_key for item in descriptors)
        if len(set(contexts)) != len(contexts):
            raise ValueError(f"execution_arm_context_not_isolated:{arm}")
        coordinator_agent_id = coordinator.coordinator.agent_id if coordinator else ""
        coordinator_protocol_hash = self._coordinator_protocol_hash(coordinator)
        created_at = _utc_now()
        committed = {
            "result_id": f"arm-result-{self.execution_id}-{arm.lower()}",
            "execution_id": self.execution_id,
            "trial_id": self.trial_spec.trial_id,
            "arm": arm,
            "subject_id": subject_id,
            "agent_ids": [item.agent_id for item in descriptors],
            "context_isolation_keys": list(contexts),
            "candidate_output": candidate,
            "execution_receipt_refs": list(receipt_refs),
            "provider_call_count": provider_calls,
            "convergence_steps": convergence_steps,
            "replay_verification": replay,
            "coordinator_agent_id": coordinator_agent_id,
            "coordinator_protocol_hash": coordinator_protocol_hash,
            "coordination_receipt_count": coordination_receipt_count,
            "created_at": created_at,
            "status": "COMPLETED",
            "context_isolated": True,
            "execution_authorized": True,
        }
        return CognitiveArmExecutionResult(
            result_id=committed["result_id"],
            execution_id=self.execution_id,
            trial_id=self.trial_spec.trial_id,
            arm=arm,
            subject_id=subject_id,
            agent_ids=tuple(item.agent_id for item in descriptors),
            context_isolation_keys=contexts,
            candidate_output=candidate,
            formal_messages=messages,
            execution_receipts=receipts,
            execution_receipt_refs=receipt_refs,
            provider_call_count=provider_calls,
            convergence_steps=convergence_steps,
            replay_verification=replay,
            coordinator_agent_id=coordinator_agent_id,
            coordinator_protocol_hash=coordinator_protocol_hash,
            coordination_receipt_count=coordination_receipt_count,
            created_at=created_at,
            result_hash=_hash_payload(committed),
        )

    @staticmethod
    def _coordinator_protocol_hash(coordinator: CognitiveCoordinationRuntime | None) -> str:
        if coordinator is None:
            return _hash_payload({"coordination": "disabled_equal_fixed_protocol"})
        agent = coordinator.coordinator
        return _hash_payload(
            {
                "role": agent.role,
                "role_contract_id": agent.contract.contract_id,
                "provider_id": agent.descriptor.provider_id,
                "model_id": agent.model_id,
                "harness_id": agent.descriptor.harness_id,
                "capabilities": list(agent.descriptor.capabilities),
                "max_cycles": coordinator.max_cycles,
                "max_role_executions_per_role": coordinator.max_role_executions_per_role,
            }
        )

    @staticmethod
    def _relative_outcome(delta: float, positive: str, negative: str, neutral: str) -> str:
        if delta > 0.02:
            return positive
        if delta < -0.02:
            return negative
        return neutral

    @staticmethod
    def _formation_outcome(evaluation: TeamCounterfactualEvaluation) -> str:
        verdicts = {evaluation.verdict_vs_best_member, evaluation.verdict_vs_fixed_team}
        if "UNDERPERFORMS" in verdicts:
            return "TEAM_FORMATION_FORECAST_MISALIGNED"
        if "OUTPERFORMS" in verdicts:
            return "TEAM_FORMATION_FORECAST_CALIBRATED"
        return "TEAM_FORMATION_FORECAST_INCONCLUSIVE"

    def _persist(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_store.append(event_type, payload)
        self._event_store.write_snapshot(self.snapshot())
