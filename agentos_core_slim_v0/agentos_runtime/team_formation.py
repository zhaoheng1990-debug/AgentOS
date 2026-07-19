"""Provider-supported, Kernel-authorized cognitive team formation runtime."""

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
    ARM_BEST_MEMBER,
    ARM_DYNAMIC_TEAM,
    ARM_FIXED_TEAM,
    AgentDescriptor,
    AgentRegistry,
    AgentRoleRequirement,
    CreditEvent,
    CreditLedger,
    EnsembleAssignment,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    ProviderBackedRuntimeCognitionLayer,
    ProviderCognitiveTask,
    ProviderTaskRouter,
    TeamCounterfactualEvaluation,
    TeamCounterfactualEvalHarness,
    TeamTrialObservation,
)
from agentos_kernel.provider_execution_plane import STATUS_COMPLETED

from .deliberation import DeliberationEventStore
from .problem_definition import DeliberationSeed


TEAM_FORMATION_RUNTIME_VERSION = "cognitive_team_formation_runtime_v0_1"

TEAM_FORMATION_STATES = {
    "BASELINES_PENDING",
    "BASELINES_READY",
    "TEAM_PROPOSED",
    "TEAM_AUTHORIZED",
    "EVALUATED",
    "FEEDBACK_APPLIED",
}

_AUTHORITY_KEYS = {
    "accepted",
    "execution_authorized",
    "permission_granted",
    "published",
    "route_selection_authority",
}

_BLIND_IDENTITY_KEYS = {
    "agent_id",
    "agent_ids",
    "arm",
    "role_coverage",
    "selected_agent_ids",
    "subject_id",
    "team_id",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _unit(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0.0 <= float(value) <= 1.0
    )


def _contains_authority(value: Any) -> bool:
    if isinstance(value, dict):
        return any(str(key).lower() in _AUTHORITY_KEYS for key in value) or any(
            _contains_authority(item) for item in value.values()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_authority(item) for item in value)
    return False


def _contains_key(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        if any(str(key).lower() in forbidden for key in value):
            return True
        return any(_contains_key(item, forbidden) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_key(item, forbidden) for item in value)
    return False


@dataclass(frozen=True)
class IndependentProblemBaselineReceipt:
    receipt_id: str
    runtime_id: str
    agent_id: str
    provider_id: str
    model_id: str
    context_isolation_key: str
    problem_id: str
    question: str
    research_object: str
    scope: str
    triggering_anomaly: str
    rival_explanations: tuple[str, ...]
    falsifier: str
    required_harnesses: tuple[str, ...]
    expected_cbit_gain: float
    evidence_refs: tuple[str, ...]
    provider_invocation_receipt: dict[str, Any]
    provider_audit: dict[str, Any]
    created_at: str
    receipt_hash: str
    candidate_state: str = "INDEPENDENT_BASELINE_CANDIDATE"
    execution_authorized: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "runtime_id": self.runtime_id,
            "agent_id": self.agent_id,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "context_isolation_key": self.context_isolation_key,
            "problem_id": self.problem_id,
            "question": self.question,
            "research_object": self.research_object,
            "scope": self.scope,
            "triggering_anomaly": self.triggering_anomaly,
            "rival_explanations": list(self.rival_explanations),
            "falsifier": self.falsifier,
            "required_harnesses": list(self.required_harnesses),
            "expected_cbit_gain": self.expected_cbit_gain,
            "evidence_refs": list(self.evidence_refs),
            "provider_invocation_receipt": self.provider_invocation_receipt,
            "provider_audit": self.provider_audit,
            "created_at": self.created_at,
            "receipt_hash": self.receipt_hash,
            "candidate_state": self.candidate_state,
            "execution_authorized": self.execution_authorized,
        }


@dataclass(frozen=True)
class TeamFormationProposal:
    proposal_id: str
    runtime_id: str
    team_id: str
    selected_agent_ids: tuple[str, ...]
    role_coverage: dict[str, str]
    formation_rationale: str
    expected_cbit_gain: float
    independence_risks: tuple[str, ...]
    negative_transfer_risks: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    provider_id: str
    model_id: str
    provider_invocation_receipt: dict[str, Any]
    provider_audit: dict[str, Any]
    created_at: str
    proposal_hash: str
    execution_authorized: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "runtime_id": self.runtime_id,
            "team_id": self.team_id,
            "selected_agent_ids": list(self.selected_agent_ids),
            "role_coverage": self.role_coverage,
            "formation_rationale": self.formation_rationale,
            "expected_cbit_gain": self.expected_cbit_gain,
            "independence_risks": list(self.independence_risks),
            "negative_transfer_risks": list(self.negative_transfer_risks),
            "evidence_refs": list(self.evidence_refs),
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "provider_invocation_receipt": self.provider_invocation_receipt,
            "provider_audit": self.provider_audit,
            "created_at": self.created_at,
            "proposal_hash": self.proposal_hash,
            "execution_authorized": self.execution_authorized,
        }


@dataclass(frozen=True)
class KernelTeamFormationDecision:
    decision_id: str
    team_id: str
    decision: str
    kernel_authorization_ref: str
    proposal_hash: str
    budget: dict[str, Any]
    budget_hash: str
    assignment: EnsembleAssignment
    created_at: str
    decision_hash: str
    execution_authorized: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "team_id": self.team_id,
            "decision": self.decision,
            "kernel_authorization_ref": self.kernel_authorization_ref,
            "proposal_hash": self.proposal_hash,
            "budget": self.budget,
            "budget_hash": self.budget_hash,
            "assignment": self.assignment.as_dict(),
            "created_at": self.created_at,
            "decision_hash": self.decision_hash,
            "execution_authorized": self.execution_authorized,
        }


@dataclass(frozen=True)
class TeamCreditFeedbackReceipt:
    feedback_id: str
    evaluation_hash: str
    individual_subject_id: str
    team_subject_id: str
    individual_credit_event_id: str
    team_credit_event_id: str
    individual_outcome: str
    team_outcome: str
    evidence_refs: tuple[str, ...]
    created_at: str
    feedback_hash: str
    route_selection_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "evaluation_hash": self.evaluation_hash,
            "individual_subject_id": self.individual_subject_id,
            "team_subject_id": self.team_subject_id,
            "individual_credit_event_id": self.individual_credit_event_id,
            "team_credit_event_id": self.team_credit_event_id,
            "individual_outcome": self.individual_outcome,
            "team_outcome": self.team_outcome,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "feedback_hash": self.feedback_hash,
            "route_selection_authority": self.route_selection_authority,
        }


@dataclass(frozen=True)
class TeamFormationSnapshot:
    runtime_id: str
    state: str
    independent_baselines: tuple[IndependentProblemBaselineReceipt, ...]
    proposal: TeamFormationProposal | None
    decision: KernelTeamFormationDecision | None
    trial_observations: tuple[TeamTrialObservation, ...]
    evaluation: TeamCounterfactualEvaluation | None
    feedback: TeamCreditFeedbackReceipt | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "state": self.state,
            "independent_baselines": [item.as_dict() for item in self.independent_baselines],
            "proposal": self.proposal.as_dict() if self.proposal else None,
            "decision": self.decision.as_dict() if self.decision else None,
            "trial_observations": [item.as_dict() for item in self.trial_observations],
            "evaluation": self.evaluation.as_dict() if self.evaluation else None,
            "feedback": self.feedback.as_dict() if self.feedback else None,
        }


class CognitiveTeamFormationRuntime:
    """Independent baselines, provider proposal, Kernel team gate, and feedback."""

    module_id = TEAM_FORMATION_RUNTIME_VERSION
    capabilities = (
        "independent_problem_baselines",
        "provider_backed_team_proposal",
        "kernel_authorized_team_formation",
        "three_arm_counterfactual_evaluation",
        "separate_individual_and_team_credit",
    )

    def __init__(
        self,
        *,
        runtime_id: str,
        seed: DeliberationSeed,
        registry: AgentRegistry,
        baseline_agent_ids: tuple[str, ...],
        baseline_routers: dict[str, ProviderTaskRouter],
        formation_router: ProviderTaskRouter,
        trial_assessment_router: ProviderTaskRouter,
        required_roles: tuple[AgentRoleRequirement, ...],
        fixed_team_id: str,
        fixed_team_agent_ids: tuple[str, ...],
        workspace_root: str | Path,
        evidence_payload: dict[str, Any],
        admitted_evidence_refs: tuple[str, ...] | None = None,
        advisory_credit_profiles: dict[str, dict[str, Any]] | None = None,
        minimum_provider_diversity: int = 2,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime_id):
            raise ValueError("team_formation_runtime_id_invalid")
        if seed.execution_authorized or seed.candidate_state != "PENDING_AGENDA_REVIEW":
            raise ValueError("team_formation_requires_pending_nonexecuting_seed")
        if len(baseline_agent_ids) < 2 or len(set(baseline_agent_ids)) != len(baseline_agent_ids):
            raise ValueError("team_formation_requires_distinct_independent_baseline_agents")
        if not required_roles or len({item.role for item in required_roles}) != len(required_roles):
            raise ValueError("team_formation_required_roles_invalid")
        if minimum_provider_diversity < 1:
            raise ValueError("team_formation_provider_diversity_invalid")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", fixed_team_id):
            raise ValueError("fixed_team_id_invalid")
        self.runtime_id = runtime_id
        self.seed = seed
        self.registry = registry
        self.baseline_agent_ids = baseline_agent_ids
        self.baseline_routers = dict(baseline_routers)
        self.formation_router = formation_router
        self.trial_assessment_router = trial_assessment_router
        self.required_roles = required_roles
        self.fixed_team_id = fixed_team_id
        self.fixed_team_agent_ids = fixed_team_agent_ids
        self.evidence_payload = dict(evidence_payload)
        self.admitted_evidence_refs = tuple(
            dict.fromkeys(admitted_evidence_refs if admitted_evidence_refs is not None else seed.evidence_refs)
        )
        if not set(seed.evidence_refs).issubset(self.admitted_evidence_refs):
            raise ValueError("team_formation_seed_evidence_not_admitted")
        self.advisory_credit_profiles = dict(advisory_credit_profiles or {})
        self.minimum_provider_diversity = minimum_provider_diversity
        self.state = "BASELINES_PENDING"
        self._baselines: list[IndependentProblemBaselineReceipt] = []
        self._proposal: TeamFormationProposal | None = None
        self._decision: KernelTeamFormationDecision | None = None
        self._trial_observations: dict[str, TeamTrialObservation] = {}
        self._evaluation: TeamCounterfactualEvaluation | None = None
        self._feedback: TeamCreditFeedbackReceipt | None = None
        self._cognition = ProviderBackedRuntimeCognitionLayer()
        self._eval_harness = TeamCounterfactualEvalHarness()
        self._validate_baseline_bindings()
        self._validate_fixed_team()
        self._event_store = DeliberationEventStore(workspace_root, runtime_id)
        self._persist(
            "TEAM_FORMATION_RUNTIME_INITIALIZED",
            {
                "seed_hash": seed.seed_hash,
                "baseline_agent_ids": list(baseline_agent_ids),
                "fixed_team_agent_ids": list(fixed_team_agent_ids),
                "fixed_team_id": fixed_team_id,
                "required_roles": [item.role for item in required_roles],
                "evidence_payload_hash": _hash_payload(self.evidence_payload),
            },
        )

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    def verify_replay(self) -> dict[str, Any]:
        return self._event_store.verify()

    def generate_independent_baselines(self) -> tuple[IndependentProblemBaselineReceipt, ...]:
        if self.state != "BASELINES_PENDING":
            raise RuntimeError("independent_baseline_generation_window_closed")
        generated: list[IndependentProblemBaselineReceipt] = []
        questions: set[str] = set()
        for index, agent_id in enumerate(self.baseline_agent_ids, start=1):
            agent = self.registry.get(agent_id)
            blind_id = f"member-{_hash_payload([self.runtime_id, agent_id])[:12]}"
            task = ProviderCognitiveTask(
                task_id=f"{self.runtime_id}-baseline-{index}",
                task_kind="independent_problem_baseline_generation",
                objective=(
                    "Generate exactly one falsifiable research problem from admitted evidence. You are isolated: no peer, "
                    "group, or selected problem candidate is visible. Copy scope and evidence refs exactly from inputs."
                ),
                inputs={
                    "blind_member_id": blind_id,
                    "discovery_objective": (
                        "Identify the next high-value research problem from unresolved evidence without receiving a candidate question."
                    ),
                    "scope": self.seed.project_scope,
                    "project_evidence": self.evidence_payload,
                    "allowed_evidence_refs": list(self.admitted_evidence_refs),
                    "seeded_problem_questions": [],
                },
                allowed_evidence=list(self.admitted_evidence_refs),
                expected_schema={
                    "type": "object",
                    "required": [
                        "problem_id",
                        "question",
                        "research_object",
                        "scope",
                        "triggering_anomaly",
                        "rival_explanations",
                        "falsifier",
                        "required_harnesses",
                        "expected_cbit_gain",
                        "evidence_refs",
                    ],
                    "properties": {
                        "problem_id": {"type": "string"},
                        "question": {"type": "string"},
                        "research_object": {"type": "string"},
                        "scope": {"type": "string", "enum": [self.seed.project_scope]},
                        "triggering_anomaly": {"type": "string"},
                        "rival_explanations": {"type": "array", "items": {"type": "string"}},
                        "falsifier": {"type": "string"},
                        "required_harnesses": {"type": "array", "items": {"type": "string"}},
                        "expected_cbit_gain": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    },
                },
                failure_semantics="keep_independent_member_baseline_missing",
            )
            envelope = self.baseline_routers[agent_id].route(task)
            if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
                self._persist(
                    "INDEPENDENT_BASELINE_BLOCKED",
                    {
                        "agent_id": agent_id,
                        "status": envelope.status,
                        "errors": list(envelope.validation_errors),
                        "invocation_receipt": envelope.invocation_receipt.as_dict(),
                    },
                )
                raise RuntimeError(f"independent_baseline_provider_blocked:{agent_id}:{envelope.status}")
            payload = dict(envelope.normalized_result or {})
            errors = self._baseline_errors(
                agent,
                payload,
                questions,
                provider_id=envelope.invocation_receipt.provider_id,
                model_id=envelope.invocation_receipt.model_id,
            )
            audit = self._cognition.audit_operation(
                "independent_problem_baseline_generation",
                {
                    "provider_support_receipt": payload,
                    "provider_support_receipt_hash": _hash_payload(payload),
                    "semantic_consistency_assertions": [
                        {
                            "assertion_id": "scope",
                            "path": "scope",
                            "operator": "equals",
                            "expected": self.seed.project_scope,
                        }
                    ],
                },
            )
            if audit["status"] != PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT:
                errors.append(f"independent_baseline_provider_audit_failed:{audit['status']}")
            if errors:
                self._persist(
                    "INDEPENDENT_BASELINE_BLOCKED",
                    {
                        "agent_id": agent_id,
                        "errors": errors,
                        "provider_audit": audit,
                        "invocation_receipt": envelope.invocation_receipt.as_dict(),
                    },
                )
                raise ValueError(";".join(errors))
            created_at = _utc_now()
            invocation = envelope.invocation_receipt.as_dict()
            committed = {
                "receipt_id": f"baseline-{self.runtime_id}-{index}",
                "runtime_id": self.runtime_id,
                "agent_id": agent_id,
                "provider_id": envelope.invocation_receipt.provider_id,
                "model_id": envelope.invocation_receipt.model_id,
                "context_isolation_key": agent.context_isolation_key,
                "problem_id": payload["problem_id"],
                "question": payload["question"],
                "research_object": payload["research_object"],
                "scope": payload["scope"],
                "triggering_anomaly": payload["triggering_anomaly"],
                "rival_explanations": payload["rival_explanations"],
                "falsifier": payload["falsifier"],
                "required_harnesses": payload["required_harnesses"],
                "expected_cbit_gain": float(payload["expected_cbit_gain"]),
                "evidence_refs": list(self.admitted_evidence_refs),
                "provider_invocation_receipt": invocation,
                "provider_audit": audit,
                "created_at": created_at,
                "candidate_state": "INDEPENDENT_BASELINE_CANDIDATE",
                "execution_authorized": False,
            }
            receipt = IndependentProblemBaselineReceipt(
                receipt_id=committed["receipt_id"],
                runtime_id=self.runtime_id,
                agent_id=agent_id,
                provider_id=committed["provider_id"],
                model_id=committed["model_id"],
                context_isolation_key=agent.context_isolation_key,
                problem_id=str(payload["problem_id"]),
                question=str(payload["question"]),
                research_object=str(payload["research_object"]),
                scope=str(payload["scope"]),
                triggering_anomaly=str(payload["triggering_anomaly"]),
                rival_explanations=tuple(str(item) for item in payload["rival_explanations"]),
                falsifier=str(payload["falsifier"]),
                required_harnesses=tuple(str(item) for item in payload["required_harnesses"]),
                expected_cbit_gain=float(payload["expected_cbit_gain"]),
                evidence_refs=self.admitted_evidence_refs,
                provider_invocation_receipt=invocation,
                provider_audit=audit,
                created_at=created_at,
                receipt_hash=_hash_payload(committed),
            )
            generated.append(receipt)
            questions.add(receipt.question)
        self._baselines = generated
        self.state = "BASELINES_READY"
        self._persist(
            "INDEPENDENT_BASELINES_COMPLETED",
            {
                "baseline_receipt_hashes": [item.receipt_hash for item in generated],
                "agent_ids": [item.agent_id for item in generated],
            },
        )
        return tuple(generated)

    def propose_team(self, *, team_id: str) -> TeamFormationProposal:
        if self.state != "BASELINES_READY":
            raise RuntimeError("team_proposal_requires_independent_baselines")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", team_id):
            raise ValueError("team_id_invalid")
        eligible = self._eligible_agents()
        task = ProviderCognitiveTask(
            task_id=f"{self.runtime_id}-team-proposal",
            task_kind="cognitive_team_formation_proposal",
            objective=(
                "Propose one agent for every required role. Use only registered agent IDs. Optimize problem fit and "
                "independence without granting execution authority. Copy admitted evidence refs exactly."
            ),
            inputs={
                "team_id": team_id,
                "problem": {
                    "problem_id": self.seed.source_problem_id,
                    "objective": self.seed.objective,
                    "research_object": self.seed.research_object,
                    "required_harnesses": list(self.seed.required_harnesses),
                    "expected_cbit_gain": self.seed.expected_cbit_gain,
                },
                "required_roles": [
                    {"role": item.role, "required_capabilities": list(item.required_capabilities)}
                    for item in self.required_roles
                ],
                "minimum_provider_diversity": self.minimum_provider_diversity,
                "registered_agents": [self._public_agent_profile(item) for item in eligible],
                "advisory_credit_profiles": self.advisory_credit_profiles,
                "independent_baseline_receipt_refs": [
                    f"baseline://{item.receipt_hash}" for item in self._baselines
                ],
                "allowed_evidence_refs": list(self.admitted_evidence_refs),
            },
            allowed_evidence=list(self.admitted_evidence_refs),
            expected_schema={
                "type": "object",
                "required": [
                    "selected_agent_ids",
                    "role_coverage",
                    "formation_rationale",
                    "expected_cbit_gain",
                    "independence_risks",
                    "negative_transfer_risks",
                    "evidence_refs",
                ],
                "properties": {
                    "selected_agent_ids": {"type": "array", "items": {"type": "string"}},
                    "role_coverage": {"type": "object", "additionalProperties": {"type": "string"}},
                    "formation_rationale": {"type": "string"},
                    "expected_cbit_gain": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "independence_risks": {"type": "array", "items": {"type": "string"}},
                    "negative_transfer_risks": {"type": "array", "items": {"type": "string"}},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                },
            },
            failure_semantics="keep_team_unformed_without_valid_proposal",
        )
        envelope = self.formation_router.route(task)
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            self._persist(
                "TEAM_PROPOSAL_BLOCKED",
                {"status": envelope.status, "invocation_receipt": envelope.invocation_receipt.as_dict()},
            )
            raise RuntimeError(f"team_proposal_provider_blocked:{envelope.status}")
        payload = dict(envelope.normalized_result or {})
        errors = self._proposal_errors(payload, eligible)
        audit = self._cognition.audit_operation(
            "cognitive_team_formation_proposal",
            {"provider_support_receipt": payload, "provider_support_receipt_hash": _hash_payload(payload)},
        )
        if not str(audit.get("status", "")).startswith("PASS_PROVIDER_SUPPORT_RECEIPT"):
            errors.append(f"team_proposal_provider_audit_failed:{audit.get('status')}")
        if errors:
            self._persist(
                "TEAM_PROPOSAL_BLOCKED",
                {
                    "errors": errors,
                    "provider_audit": audit,
                    "invocation_receipt": envelope.invocation_receipt.as_dict(),
                },
            )
            raise ValueError(";".join(errors))
        role_coverage = dict(payload["role_coverage"])
        selected_agent_ids = [role_coverage[item.role] for item in self.required_roles]
        created_at = _utc_now()
        invocation = envelope.invocation_receipt.as_dict()
        committed = {
            "proposal_id": f"proposal-{self.runtime_id}",
            "runtime_id": self.runtime_id,
            "team_id": team_id,
            "selected_agent_ids": selected_agent_ids,
            "role_coverage": role_coverage,
            "formation_rationale": payload["formation_rationale"],
            "expected_cbit_gain": float(payload["expected_cbit_gain"]),
            "independence_risks": payload["independence_risks"],
            "negative_transfer_risks": payload["negative_transfer_risks"],
            "evidence_refs": list(self.admitted_evidence_refs),
            "provider_id": envelope.invocation_receipt.provider_id,
            "model_id": envelope.invocation_receipt.model_id,
            "provider_invocation_receipt": invocation,
            "provider_audit": audit,
            "created_at": created_at,
            "execution_authorized": False,
        }
        self._proposal = TeamFormationProposal(
            proposal_id=committed["proposal_id"],
            runtime_id=self.runtime_id,
            team_id=team_id,
            selected_agent_ids=tuple(selected_agent_ids),
            role_coverage=role_coverage,
            formation_rationale=str(payload["formation_rationale"]),
            expected_cbit_gain=float(payload["expected_cbit_gain"]),
            independence_risks=tuple(str(item) for item in payload["independence_risks"]),
            negative_transfer_risks=tuple(str(item) for item in payload["negative_transfer_risks"]),
            evidence_refs=self.admitted_evidence_refs,
            provider_id=committed["provider_id"],
            model_id=committed["model_id"],
            provider_invocation_receipt=invocation,
            provider_audit=audit,
            created_at=created_at,
            proposal_hash=_hash_payload(committed),
        )
        self.state = "TEAM_PROPOSED"
        self._persist("TEAM_PROPOSAL_ADMITTED", self._proposal.as_dict())
        return self._proposal

    def authorize_team(
        self,
        *,
        kernel_authorization_ref: str,
        budget: dict[str, Any],
    ) -> KernelTeamFormationDecision:
        if self.state != "TEAM_PROPOSED" or self._proposal is None:
            raise RuntimeError("team_authorization_requires_admitted_proposal")
        if not kernel_authorization_ref or not isinstance(budget, dict) or not budget:
            raise ValueError("team_authorization_kernel_ref_and_budget_required")
        agents = tuple(self.registry.get(agent_id) for agent_id in self._proposal.selected_agent_ids)
        assignment = EnsembleAssignment(
            team_id=self._proposal.team_id,
            agents=agents,
            context_isolated=len({item.context_isolation_key for item in agents}) == len(agents),
            execution_authorized=True,
        )
        if not assignment.context_isolated:
            raise ValueError("team_authorization_context_isolation_failed")
        created_at = _utc_now()
        budget_hash = _hash_payload(budget)
        committed = {
            "decision_id": f"decision-{self.runtime_id}",
            "team_id": self._proposal.team_id,
            "decision": "AUTHORIZED",
            "kernel_authorization_ref": kernel_authorization_ref,
            "proposal_hash": self._proposal.proposal_hash,
            "budget": budget,
            "budget_hash": budget_hash,
            "assignment": assignment.as_dict(),
            "created_at": created_at,
            "execution_authorized": True,
        }
        self._decision = KernelTeamFormationDecision(
            decision_id=committed["decision_id"],
            team_id=self._proposal.team_id,
            decision="AUTHORIZED",
            kernel_authorization_ref=kernel_authorization_ref,
            proposal_hash=self._proposal.proposal_hash,
            budget=dict(budget),
            budget_hash=budget_hash,
            assignment=assignment,
            created_at=created_at,
            decision_hash=_hash_payload(committed),
        )
        self.state = "TEAM_AUTHORIZED"
        self._persist("TEAM_AUTHORIZED", self._decision.as_dict())
        return self._decision

    def evaluate_counterfactual(
        self,
        observations: tuple[TeamTrialObservation, ...],
    ) -> TeamCounterfactualEvaluation:
        if self.state != "TEAM_AUTHORIZED" or self._decision is None:
            raise RuntimeError("team_counterfactual_requires_authorized_team")
        dynamic = next((item for item in observations if item.arm == ARM_DYNAMIC_TEAM), None)
        fixed = next((item for item in observations if item.arm == ARM_FIXED_TEAM), None)
        member = next((item for item in observations if item.arm == ARM_BEST_MEMBER), None)
        if dynamic is None or fixed is None or member is None:
            raise ValueError("team_counterfactual_arm_missing")
        for item in observations:
            self._validate_arm_identity(item.arm, item.subject_id, item.agent_ids)
        if any(item.budget_hash != self._decision.budget_hash for item in observations):
            raise ValueError("team_counterfactual_not_using_authorized_budget")
        if any(tuple(item.evidence_refs) != tuple(self.admitted_evidence_refs) for item in observations):
            raise ValueError("team_counterfactual_not_using_admitted_evidence")
        for item in observations:
            recorded = self._trial_observations.get(item.arm)
            if recorded is None or _hash_payload(recorded.as_dict()) != _hash_payload(item.as_dict()):
                raise ValueError(f"team_counterfactual_observation_not_provider_backed:{item.arm}")
        self._evaluation = self._eval_harness.evaluate(
            f"evaluation-{self.runtime_id}",
            observations,
        )
        self.state = "EVALUATED"
        self._persist("TEAM_COUNTERFACTUAL_EVALUATED", self._evaluation.as_dict())
        return self._evaluation

    def assess_trial_arm(
        self,
        *,
        trial_id: str,
        arm: str,
        subject_id: str,
        agent_ids: tuple[str, ...],
        harness_protocol_id: str,
        budget_hash: str,
        harness_receipt_ref: str,
        harness_summary: dict[str, Any],
        semantic_artifact: dict[str, Any],
    ) -> TeamTrialObservation:
        if self.state != "TEAM_AUTHORIZED" or self._decision is None:
            raise RuntimeError("team_trial_assessment_requires_authorized_team")
        if arm in self._trial_observations:
            raise RuntimeError(f"team_trial_arm_already_assessed:{arm}")
        if budget_hash != self._decision.budget_hash:
            raise ValueError("team_trial_assessment_budget_mismatch")
        if not all((trial_id, subject_id, agent_ids, harness_protocol_id, harness_receipt_ref)):
            raise ValueError("team_trial_assessment_identity_incomplete")
        self._validate_arm_identity(arm, subject_id, agent_ids)
        if not isinstance(semantic_artifact, dict) or not semantic_artifact:
            raise ValueError("team_trial_semantic_artifact_required")
        if _contains_key(semantic_artifact, _BLIND_IDENTITY_KEYS) or _contains_key(
            harness_summary, _BLIND_IDENTITY_KEYS
        ):
            raise ValueError("team_trial_blind_identity_leak")
        if _contains_authority(semantic_artifact):
            raise ValueError("team_trial_semantic_artifact_authority_forbidden")
        mechanical = self._mechanical_trial_metrics(harness_summary)
        blind_arm_id = f"blind-{_hash_payload([self.runtime_id, trial_id, arm])[:16]}"
        task = ProviderCognitiveTask(
            task_id=f"{self.runtime_id}-trial-{arm.lower()}",
            task_kind="team_trial_semantic_assessment",
            objective=(
                "Assess the epistemic quality of this blinded candidate. Do not infer its source. Copy every "
                "Harness-owned metric and admitted evidence ref exactly."
            ),
            inputs={
                "trial_id": trial_id,
                "blind_arm_id": blind_arm_id,
                "harness_protocol_id": harness_protocol_id,
                "budget_hash": budget_hash,
                "harness_receipt_ref": harness_receipt_ref,
                "harness_summary": harness_summary,
                "harness_owned_metrics": mechanical,
                "semantic_artifact": semantic_artifact,
                "allowed_evidence_refs": list(self.admitted_evidence_refs),
            },
            allowed_evidence=list(self.admitted_evidence_refs),
            expected_schema={
                "type": "object",
                "required": [
                    "blind_arm_id",
                    "quality_score",
                    "observed_cbit_gain",
                    "errors_exposed",
                    "errors_corrected",
                    "negative_transfer_opportunities",
                    "negative_transfer_intercepts",
                    "normalized_cost",
                    "convergence_steps",
                    "evidence_refs",
                ],
                "properties": {
                    "blind_arm_id": {"type": "string"},
                    "quality_score": {"type": "number"},
                    "observed_cbit_gain": {"type": "number"},
                    "errors_exposed": {"type": "integer"},
                    "errors_corrected": {"type": "integer"},
                    "negative_transfer_opportunities": {"type": "integer"},
                    "negative_transfer_intercepts": {"type": "integer"},
                    "normalized_cost": {"type": "number"},
                    "convergence_steps": {"type": "integer"},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                },
            },
            budget=self._decision.budget,
            failure_semantics="do_not_compare_team_arm_without_provider_backed_semantic_assessment",
        )
        envelope = self.trial_assessment_router.route(task)
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            self._persist(
                "TEAM_TRIAL_ASSESSMENT_BLOCKED",
                {
                    "arm": arm,
                    "status": envelope.status,
                    "errors": list(envelope.validation_errors),
                    "invocation_receipt": envelope.invocation_receipt.as_dict(),
                },
            )
            raise RuntimeError(f"team_trial_assessment_provider_blocked:{arm}:{envelope.status}")
        payload = dict(envelope.normalized_result or {})
        errors = self._trial_assessment_errors(payload, blind_arm_id, mechanical)
        audit = self._cognition.audit_operation(
            "team_trial_semantic_assessment",
            {"provider_support_receipt": payload, "provider_support_receipt_hash": _hash_payload(payload)},
        )
        if not str(audit.get("status", "")).startswith("PASS_PROVIDER_SUPPORT_RECEIPT"):
            errors.append(f"team_trial_provider_audit_failed:{audit.get('status')}")
        if errors:
            self._persist(
                "TEAM_TRIAL_ASSESSMENT_BLOCKED",
                {
                    "arm": arm,
                    "errors": errors,
                    "provider_audit": audit,
                    "invocation_receipt": envelope.invocation_receipt.as_dict(),
                },
            )
            raise ValueError(";".join(errors))
        invocation = envelope.invocation_receipt.as_dict()
        observation = TeamTrialObservation(
            observation_id=f"observation-{self.runtime_id}-{arm.lower()}",
            trial_id=trial_id,
            arm=arm,
            subject_id=subject_id,
            agent_ids=agent_ids,
            quality_score=float(payload["quality_score"]),
            observed_cbit_gain=float(payload["observed_cbit_gain"]),
            errors_exposed=int(payload["errors_exposed"]),
            errors_corrected=int(payload["errors_corrected"]),
            negative_transfer_opportunities=int(payload["negative_transfer_opportunities"]),
            negative_transfer_intercepts=int(payload["negative_transfer_intercepts"]),
            normalized_cost=float(payload["normalized_cost"]),
            convergence_steps=int(payload["convergence_steps"]),
            evidence_refs=self.admitted_evidence_refs,
            harness_protocol_id=harness_protocol_id,
            budget_hash=budget_hash,
            harness_receipt_ref=harness_receipt_ref,
            semantic_assessment_receipt_ref=f"provider-receipt://{invocation['receipt_hash']}",
        )
        self._trial_observations[arm] = observation
        self._persist(
            "TEAM_TRIAL_ARM_ASSESSED",
            {
                "observation": observation.as_dict(),
                "provider_invocation_receipt": invocation,
                "provider_audit": audit,
                "mechanical_metrics_hash": _hash_payload(mechanical),
            },
        )
        return observation

    def apply_credit_feedback(self, credit_ledger: CreditLedger) -> TeamCreditFeedbackReceipt:
        if self.state != "EVALUATED" or self._evaluation is None:
            raise RuntimeError("team_credit_feedback_requires_evaluation")
        if self._feedback is not None:
            raise RuntimeError("team_credit_feedback_already_applied")
        individual_outcome = (
            "INDEPENDENT_BASELINE_VALIDATED"
            if self._evaluation.best_member_score >= 0.5
            else "INDEPENDENT_BASELINE_UNDERPERFORMED"
        )
        team_verdicts = {
            self._evaluation.verdict_vs_best_member,
            self._evaluation.verdict_vs_fixed_team,
        }
        if "UNDERPERFORMS" in team_verdicts:
            team_outcome = "TEAM_COMPOSITION_UNDERPERFORMED"
        elif "OUTPERFORMS" in team_verdicts:
            team_outcome = "TEAM_COMPOSITION_VALIDATED"
        else:
            team_outcome = "TEAM_COMPOSITION_INCONCLUSIVE"
        individual_event_id = f"team-formation-individual-{self.runtime_id}"
        team_event_id = f"team-formation-combination-{self.runtime_id}"
        adjudication_ref = f"team-evaluation://{self._evaluation.evaluation_hash}"
        for event_id in (individual_event_id, team_event_id):
            if credit_ledger.has_event(event_id):
                raise ValueError(f"team_credit_feedback_event_already_exists:{event_id}")
        for subject_id, subject_kind in (
            (self._evaluation.best_member_subject_id, "agent"),
            (self._evaluation.dynamic_team_subject_id, "team"),
        ):
            profile = credit_ledger.profile(subject_id)
            if profile.event_count and profile.subject_kind != subject_kind:
                raise ValueError(f"team_credit_feedback_subject_kind_conflict:{subject_id}")
        credit_ledger.append(
            CreditEvent(
                event_id=individual_event_id,
                subject_id=self._evaluation.best_member_subject_id,
                subject_kind="agent",
                outcome=individual_outcome,
                adjudication_ref=adjudication_ref,
                evidence_refs=self._evaluation.evidence_refs,
                weight=max(0.01, self._evaluation.best_member_score),
                source_claim_id=self.seed.source_problem_id,
            )
        )
        team_weight = max(
            0.01,
            min(
                1.0,
                abs(self._evaluation.delta_dynamic_vs_best_member)
                + abs(self._evaluation.delta_dynamic_vs_fixed_team),
            ),
        )
        credit_ledger.append(
            CreditEvent(
                event_id=team_event_id,
                subject_id=self._evaluation.dynamic_team_subject_id,
                subject_kind="team",
                outcome=team_outcome,
                adjudication_ref=adjudication_ref,
                evidence_refs=self._evaluation.evidence_refs,
                weight=team_weight,
                source_claim_id=self.seed.source_problem_id,
            )
        )
        created_at = _utc_now()
        committed = {
            "feedback_id": f"feedback-{self.runtime_id}",
            "evaluation_hash": self._evaluation.evaluation_hash,
            "individual_subject_id": self._evaluation.best_member_subject_id,
            "team_subject_id": self._evaluation.dynamic_team_subject_id,
            "individual_credit_event_id": individual_event_id,
            "team_credit_event_id": team_event_id,
            "individual_outcome": individual_outcome,
            "team_outcome": team_outcome,
            "evidence_refs": list(self._evaluation.evidence_refs),
            "created_at": created_at,
            "route_selection_authority": False,
        }
        self._feedback = TeamCreditFeedbackReceipt(
            feedback_id=committed["feedback_id"],
            evaluation_hash=self._evaluation.evaluation_hash,
            individual_subject_id=self._evaluation.best_member_subject_id,
            team_subject_id=self._evaluation.dynamic_team_subject_id,
            individual_credit_event_id=individual_event_id,
            team_credit_event_id=team_event_id,
            individual_outcome=individual_outcome,
            team_outcome=team_outcome,
            evidence_refs=self._evaluation.evidence_refs,
            created_at=created_at,
            feedback_hash=_hash_payload(committed),
        )
        self.state = "FEEDBACK_APPLIED"
        self._persist("TEAM_CREDIT_FEEDBACK_APPLIED", self._feedback.as_dict())
        return self._feedback

    def snapshot(self) -> TeamFormationSnapshot:
        return TeamFormationSnapshot(
            runtime_id=self.runtime_id,
            state=self.state,
            independent_baselines=tuple(self._baselines),
            proposal=self._proposal,
            decision=self._decision,
            trial_observations=tuple(self._trial_observations.values()),
            evaluation=self._evaluation,
            feedback=self._feedback,
        )

    def _validate_baseline_bindings(self) -> None:
        agents = [self.registry.get(agent_id) for agent_id in self.baseline_agent_ids]
        if any(agent.role != "PROBLEM_FRAMER" for agent in agents):
            raise ValueError("independent_baseline_agents_must_be_problem_framers")
        if len({agent.context_isolation_key for agent in agents}) != len(agents):
            raise ValueError("independent_baseline_contexts_not_isolated")
        if set(self.baseline_agent_ids) != set(self.baseline_routers):
            raise ValueError("independent_baseline_router_binding_incomplete")
        if any(self.seed.project_scope not in agent.allowed_evidence_scopes for agent in agents):
            raise ValueError("independent_baseline_agent_scope_mismatch")

    def _validate_fixed_team(self) -> None:
        if len(self.fixed_team_agent_ids) != len(self.required_roles):
            raise ValueError("fixed_team_size_mismatch")
        agents = [self.registry.get(agent_id) for agent_id in self.fixed_team_agent_ids]
        if {agent.role for agent in agents} != {item.role for item in self.required_roles}:
            raise ValueError("fixed_team_role_coverage_mismatch")
        if len({agent.context_isolation_key for agent in agents}) != len(agents):
            raise ValueError("fixed_team_context_not_isolated")

    def _baseline_errors(
        self,
        agent: AgentDescriptor,
        payload: dict[str, Any],
        existing_questions: set[str],
        *,
        provider_id: str,
        model_id: str,
    ) -> list[str]:
        errors: list[str] = []
        if agent.provider_id != provider_id:
            errors.append("independent_baseline_agent_provider_binding_mismatch")
        if agent.model_id and agent.model_id != model_id:
            errors.append("independent_baseline_agent_model_binding_mismatch")
        if payload.get("scope") != self.seed.project_scope:
            errors.append("independent_baseline_scope_mismatch")
        if _contains_authority(payload):
            errors.append("independent_baseline_authority_claim_forbidden")
        for field_name in ("problem_id", "question", "research_object", "triggering_anomaly", "falsifier"):
            value = payload.get(field_name)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"independent_baseline_field_required:{field_name}")
        if isinstance(payload.get("question"), str) and payload["question"] in existing_questions:
            errors.append("independent_baseline_question_not_unique")
        if (
            not isinstance(payload.get("rival_explanations"), list)
            or not payload["rival_explanations"]
            or not all(isinstance(item, str) and item.strip() for item in payload["rival_explanations"])
        ):
            errors.append("independent_baseline_rivals_required")
        if (
            not isinstance(payload.get("required_harnesses"), list)
            or not payload["required_harnesses"]
            or not all(isinstance(item, str) and item.strip() for item in payload["required_harnesses"])
        ):
            errors.append("independent_baseline_harnesses_required")
        if not _unit(payload.get("expected_cbit_gain")):
            errors.append("independent_baseline_expected_cbit_invalid")
        refs = payload.get("evidence_refs")
        if (
            not isinstance(refs, list)
            or not all(isinstance(item, str) for item in refs)
            or len(refs) != len(self.admitted_evidence_refs)
            or (set(refs) if all(isinstance(item, str) for item in refs) else set())
            != set(self.admitted_evidence_refs)
        ):
            errors.append("independent_baseline_evidence_not_admitted")
        return errors

    def _eligible_agents(self) -> tuple[AgentDescriptor, ...]:
        eligible: list[AgentDescriptor] = []
        for requirement in self.required_roles:
            eligible.extend(self.registry.candidates(requirement))
        unique = {item.agent_id: item for item in eligible}
        return tuple(unique[key] for key in sorted(unique))

    def _proposal_errors(
        self,
        payload: dict[str, Any],
        eligible: tuple[AgentDescriptor, ...],
    ) -> list[str]:
        errors: list[str] = []
        selected = payload.get("selected_agent_ids")
        coverage = payload.get("role_coverage")
        eligible_map = {item.agent_id: item for item in eligible}
        required_role_map = {item.role: item for item in self.required_roles}
        if (
            not isinstance(selected, list)
            or len(selected) != len(self.required_roles)
            or not all(isinstance(item, str) and item for item in selected)
        ):
            return ["team_proposal_selected_agent_count_mismatch"]
        if len(set(selected)) != len(selected):
            errors.append("team_proposal_agent_ids_not_unique")
        if any(agent_id not in eligible_map for agent_id in selected):
            errors.append("team_proposal_unknown_or_ineligible_agent")
        coverage_is_string_map = isinstance(coverage, dict) and all(
            isinstance(key, str) and isinstance(value, str) and value
            for key, value in coverage.items()
        )
        if not coverage_is_string_map or set(coverage) != set(required_role_map):
            errors.append("team_proposal_role_coverage_incomplete")
        elif set(coverage.values()) != set(selected):
            errors.append("team_proposal_role_coverage_agent_set_mismatch")
        selected_agents = [eligible_map[item] for item in selected if item in eligible_map]
        if len(selected_agents) == len(selected):
            if any(coverage.get(agent.role) != agent.agent_id for agent in selected_agents):
                errors.append("team_proposal_role_assignment_mismatch")
            if len({item.context_isolation_key for item in selected_agents}) != len(selected_agents):
                errors.append("team_proposal_context_not_isolated")
            if len({item.provider_id for item in selected_agents}) < self.minimum_provider_diversity:
                errors.append("team_proposal_provider_diversity_below_floor")
            for agent in selected_agents:
                requirement = required_role_map[agent.role]
                if not set(requirement.required_capabilities).issubset(agent.capabilities):
                    errors.append(f"team_proposal_capability_missing:{agent.agent_id}")
                if self.seed.project_scope not in agent.allowed_evidence_scopes:
                    errors.append(f"team_proposal_scope_mismatch:{agent.agent_id}")
                if requirement.require_distinct_provider and sum(
                    item.provider_id == agent.provider_id for item in selected_agents
                ) != 1:
                    errors.append(f"team_proposal_distinct_provider_required:{agent.agent_id}")
        if not str(payload.get("formation_rationale", "")).strip():
            errors.append("team_proposal_rationale_required")
        if not _unit(payload.get("expected_cbit_gain")):
            errors.append("team_proposal_expected_cbit_invalid")
        for field_name in ("independence_risks", "negative_transfer_risks"):
            if not isinstance(payload.get(field_name), list) or not all(
                isinstance(item, str) for item in payload[field_name]
            ):
                errors.append(f"team_proposal_array_required:{field_name}")
        refs = payload.get("evidence_refs")
        if (
            not isinstance(refs, list)
            or not all(isinstance(item, str) for item in refs)
            or len(refs) != len(self.admitted_evidence_refs)
            or (set(refs) if all(isinstance(item, str) for item in refs) else set())
            != set(self.admitted_evidence_refs)
        ):
            errors.append("team_proposal_evidence_not_admitted")
        if _contains_authority(payload):
            errors.append("team_proposal_authority_claim_forbidden")
        return errors

    def _public_agent_profile(self, agent: AgentDescriptor) -> dict[str, Any]:
        return {
            "agent_id": agent.agent_id,
            "role": agent.role,
            "capabilities": list(agent.capabilities),
            "runner_id": agent.runner_id,
            "harness_id": agent.harness_id,
            "provider_id": agent.provider_id,
            "model_id": agent.model_id,
            "context_isolation_key": agent.context_isolation_key,
            "allowed_evidence_scopes": list(agent.allowed_evidence_scopes),
            "advisory_credit_profile": self.advisory_credit_profiles.get(agent.agent_id, {}),
        }

    def _mechanical_trial_metrics(self, harness_summary: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(harness_summary, dict):
            raise ValueError("team_trial_harness_summary_required")
        required = (
            "observed_cbit_gain",
            "errors_exposed",
            "errors_corrected",
            "negative_transfer_opportunities",
            "negative_transfer_intercepts",
            "normalized_cost",
            "convergence_steps",
        )
        if any(name not in harness_summary for name in required):
            raise ValueError("team_trial_harness_mechanical_metrics_incomplete")
        if not _unit(harness_summary["observed_cbit_gain"]):
            raise ValueError("team_trial_harness_cbit_invalid")
        if not _unit(harness_summary["normalized_cost"]):
            raise ValueError("team_trial_harness_cost_invalid")
        steps = harness_summary["convergence_steps"]
        if not isinstance(steps, int) or isinstance(steps, bool) or steps < 0:
            raise ValueError("team_trial_harness_convergence_steps_invalid")
        for name in (
            "errors_exposed",
            "errors_corrected",
            "negative_transfer_opportunities",
            "negative_transfer_intercepts",
        ):
            value = harness_summary[name]
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"team_trial_harness_count_invalid:{name}")
        if harness_summary["errors_corrected"] > harness_summary["errors_exposed"]:
            raise ValueError("team_trial_harness_corrections_exceed_exposed")
        if harness_summary["negative_transfer_intercepts"] > harness_summary[
            "negative_transfer_opportunities"
        ]:
            raise ValueError("team_trial_harness_intercepts_exceed_opportunities")
        return {
            "observed_cbit_gain": float(harness_summary["observed_cbit_gain"]),
            "errors_exposed": harness_summary["errors_exposed"],
            "errors_corrected": harness_summary["errors_corrected"],
            "negative_transfer_opportunities": harness_summary["negative_transfer_opportunities"],
            "negative_transfer_intercepts": harness_summary["negative_transfer_intercepts"],
            "normalized_cost": float(harness_summary["normalized_cost"]),
            "convergence_steps": steps,
        }

    def _validate_arm_identity(
        self,
        arm: str,
        subject_id: str,
        agent_ids: tuple[str, ...],
    ) -> None:
        if self._proposal is None:
            raise RuntimeError("team_trial_identity_requires_team_proposal")
        if arm == ARM_BEST_MEMBER:
            if subject_id not in {item.agent_id for item in self._baselines}:
                raise ValueError("best_member_observation_not_independent_baseline_agent")
            if agent_ids != (subject_id,):
                raise ValueError("best_member_observation_subject_assignment_mismatch")
            return
        if arm == ARM_FIXED_TEAM:
            if subject_id != self.fixed_team_id:
                raise ValueError("fixed_team_observation_subject_mismatch")
            if agent_ids != self.fixed_team_agent_ids:
                raise ValueError("fixed_team_observation_assignment_mismatch")
            return
        if arm == ARM_DYNAMIC_TEAM:
            if subject_id != self._proposal.team_id:
                raise ValueError("dynamic_team_observation_subject_mismatch")
            if agent_ids != self._proposal.selected_agent_ids:
                raise ValueError("dynamic_team_observation_assignment_mismatch")
            return
        raise ValueError(f"unknown_team_trial_arm:{arm}")

    def _trial_assessment_errors(
        self,
        payload: dict[str, Any],
        blind_arm_id: str,
        mechanical: dict[str, Any],
    ) -> list[str]:
        errors: list[str] = []
        if payload.get("blind_arm_id") != blind_arm_id:
            errors.append("team_trial_assessment_arm_mismatch")
        if _contains_authority(payload):
            errors.append("team_trial_assessment_authority_claim_forbidden")
        for name in ("quality_score", "observed_cbit_gain", "normalized_cost"):
            if not _unit(payload.get(name)):
                errors.append(f"team_trial_assessment_metric_invalid:{name}")
        for name in (
            "errors_exposed",
            "errors_corrected",
            "negative_transfer_opportunities",
            "negative_transfer_intercepts",
            "convergence_steps",
        ):
            value = payload.get(name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"team_trial_assessment_count_invalid:{name}")
        if payload.get("errors_corrected", 0) > payload.get("errors_exposed", 0):
            errors.append("team_trial_assessment_corrections_exceed_exposed")
        if payload.get("negative_transfer_intercepts", 0) > payload.get(
            "negative_transfer_opportunities", 0
        ):
            errors.append("team_trial_assessment_intercepts_exceed_opportunities")
        for name, expected in mechanical.items():
            if payload.get(name) != expected:
                errors.append(f"team_trial_assessment_harness_metric_mismatch:{name}")
        refs = payload.get("evidence_refs")
        if (
            not isinstance(refs, list)
            or not all(isinstance(item, str) for item in refs)
            or len(refs) != len(self.admitted_evidence_refs)
            or (set(refs) if all(isinstance(item, str) for item in refs) else set())
            != set(self.admitted_evidence_refs)
        ):
            errors.append("team_trial_assessment_evidence_mismatch")
        return errors

    def _persist(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_store.append(event_type, payload)
        self._event_store.write_snapshot(self.snapshot())
