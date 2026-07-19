"""Kernel-authorized matched cognitive-organization ablation execution."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

from agentos_kernel import (
    AgentDescriptor,
    AgentRegistry,
    CognitiveTrialHarnessReceipt,
    FrozenFindingTrialHarness,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    ProviderBackedRuntimeCognitionLayer,
    ProviderCognitiveTask,
    ProviderTaskRouter,
    OrganizationTrialRecord,
)
from agentos_kernel.provider_execution_plane import STATUS_COMPLETED

from .cognitive_roles import CognitiveAgent, standard_role_contract
from .coordination import CognitiveCoordinationRuntime
from .deliberation import CognitiveAgentRuntimeAdapter, CognitiveDeliberationSession, DeliberationEventStore
from .organization_learning import OrganizationExperimentPlan
from .team_execution import CognitiveExecutionTrialSpec
from .team_formation import CognitiveTeamFormationRuntime


COGNITIVE_ORGANIZATION_ABLATION_VERSION = "cognitive_organization_ablation_runtime_v0_2"
SUPPORTED_ABLATION_VARIANTS = {
    "DYNAMIC_NO_COORDINATOR",
    "DYNAMIC_NO_REVIEWER",
    "DYNAMIC_NO_REPLICATOR",
    "DYNAMIC_NO_SYNTHESIZER",
}
PROTOCOL_COMPONENT_OMISSIONS = {
    "DYNAMIC_TEAM": (),
    "DYNAMIC_NO_COORDINATOR": ("COORDINATOR",),
    "DYNAMIC_NO_REVIEWER": ("ADVERSARIAL_REVIEWER",),
    "DYNAMIC_NO_REPLICATOR": ("REPLICATOR",),
    "DYNAMIC_NO_SYNTHESIZER": ("SYNTHESIZER",),
}
_ROLE_OMISSIONS = {"ADVERSARIAL_REVIEWER", "REPLICATOR", "SYNTHESIZER"}
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
_CANDIDATE_FIELDS = (
    "answer",
    "supported_finding_ids",
    "rejected_finding_ids",
    "unresolved_finding_ids",
    "rival_explanations",
    "falsifier",
    "evidence_refs",
    "uncertainties",
)
_MECHANICAL_FIELDS = (
    "observed_cbit_gain",
    "errors_exposed",
    "errors_corrected",
    "negative_transfer_opportunities",
    "negative_transfer_intercepts",
    "normalized_cost",
    "convergence_steps",
)


def organization_records_from_ablation_smoke_result(
    payload: dict[str, Any],
    *,
    context_key: str,
    evidence_tier: str,
    trial_group_id: str,
) -> tuple[OrganizationTrialRecord, ...]:
    """Convert one passing matched-ablation bundle into organization learning records."""

    if not isinstance(payload, dict) or payload.get("status") != "PASS":
        raise ValueError("organization_ablation_import_requires_passing_smoke")
    gates = payload.get("gates")
    required_gates = {
        "authorized_protocols_completed",
        "all_protocol_replays_valid",
        "ablation_replay_valid",
        "evidence_surface_equal",
        "harness_owns_observed_cbit",
        "hidden_truth_absent_from_provider_inputs",
        "provider_budget_respected",
        "semantic_assessment_blinded",
        "one_component_omitted_per_variant",
    }
    if not isinstance(gates, dict) or not all(gates.get(name) is True for name in required_gates):
        raise ValueError("organization_ablation_import_gates_incomplete")
    observations = payload.get("ablation_observations")
    selected = tuple(payload.get("selected_variants", ()))
    expected_protocols = {"DYNAMIC_TEAM", *selected}
    if (
        not isinstance(observations, list)
        or len(observations) != len(expected_protocols)
        or {item.get("protocol_id") for item in observations if isinstance(item, dict)} != expected_protocols
    ):
        raise ValueError("organization_ablation_import_protocol_set_mismatch")
    evidence_surfaces = {
        tuple(item.get("evidence_refs", ()))
        for item in observations
        if isinstance(item, dict)
    }
    if len(evidence_surfaces) != 1 or not next(iter(evidence_surfaces)):
        raise ValueError("organization_ablation_import_evidence_surface_mismatch")
    evidence_refs = next(iter(evidence_surfaces))
    source_result_hash = _hash_payload(payload)
    records = []
    for item in observations:
        receipt = item.get("harness_receipt")
        if not isinstance(receipt, dict) or receipt.get("harness_owned") is not True or receipt.get(
            "semantic_provider_used"
        ) is not False:
            raise ValueError("organization_ablation_import_harness_ownership_invalid")
        records.append(
            OrganizationTrialRecord.create(
                record_id=f"record-{trial_group_id}-{item['protocol_id'].lower()}",
                trial_group_id=trial_group_id,
                context_key=context_key,
                evidence_tier=evidence_tier,
                protocol_id=item["protocol_id"],
                effectiveness_score=item["effectiveness_score"],
                observed_cbit_gain=receipt["observed_cbit_gain"],
                normalized_cost=receipt["normalized_cost"],
                convergence_steps=receipt["convergence_steps"],
                errors_exposed=receipt["errors_exposed"],
                errors_corrected=receipt["errors_corrected"],
                negative_transfer_opportunities=receipt["negative_transfer_opportunities"],
                negative_transfer_intercepts=receipt["negative_transfer_intercepts"],
                evidence_refs=tuple(item["evidence_refs"]),
                harness_receipt_ref=f"harness://{receipt['receipt_hash']}",
                execution_result_hash=item["result_hash"],
                source_result_hash=source_result_hash,
                replay_valid=True,
            )
        )
    return tuple(records)


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
        "required": list(_CANDIDATE_FIELDS),
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
class OrganizationAblationProtocolResult:
    result_id: str
    protocol_id: str
    omitted_components: tuple[str, ...]
    agent_ids: tuple[str, ...]
    context_isolation_keys: tuple[str, ...]
    candidate_output: dict[str, Any]
    formal_messages: tuple[dict[str, Any], ...]
    execution_receipts: tuple[dict[str, Any], ...]
    execution_receipt_refs: tuple[str, ...]
    provider_call_count: int
    convergence_steps: int
    coordination_receipt_count: int
    coordinator_agent_id: str
    replay_verification: dict[str, Any]
    created_at: str
    result_hash: str
    execution_authorized: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "protocol_id": self.protocol_id,
            "omitted_components": list(self.omitted_components),
            "agent_ids": list(self.agent_ids),
            "context_isolation_keys": list(self.context_isolation_keys),
            "candidate_output": self.candidate_output,
            "formal_messages": list(self.formal_messages),
            "execution_receipts": list(self.execution_receipts),
            "execution_receipt_refs": list(self.execution_receipt_refs),
            "provider_call_count": self.provider_call_count,
            "convergence_steps": self.convergence_steps,
            "coordination_receipt_count": self.coordination_receipt_count,
            "coordinator_agent_id": self.coordinator_agent_id,
            "replay_verification": self.replay_verification,
            "created_at": self.created_at,
            "result_hash": self.result_hash,
            "execution_authorized": self.execution_authorized,
        }


@dataclass(frozen=True)
class OrganizationAblationObservation:
    observation_id: str
    protocol_id: str
    result_hash: str
    quality_score: float
    effectiveness_score: float
    harness_receipt: CognitiveTrialHarnessReceipt
    semantic_assessment_receipt_ref: str
    blind_candidate_id: str
    provider_cited_evidence_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    observation_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "protocol_id": self.protocol_id,
            "result_hash": self.result_hash,
            "quality_score": self.quality_score,
            "effectiveness_score": self.effectiveness_score,
            "harness_receipt": self.harness_receipt.as_dict(),
            "semantic_assessment_receipt_ref": self.semantic_assessment_receipt_ref,
            "blind_candidate_id": self.blind_candidate_id,
            "provider_cited_evidence_refs": list(self.provider_cited_evidence_refs),
            "evidence_refs": list(self.evidence_refs),
            "observation_hash": self.observation_hash,
        }


@dataclass(frozen=True)
class CognitiveOrganizationAblationSnapshot:
    runtime_id: str
    state: str
    experiment_plan_hash: str
    protocol_results: tuple[OrganizationAblationProtocolResult, ...]
    observations: tuple[OrganizationAblationObservation, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "state": self.state,
            "experiment_plan_hash": self.experiment_plan_hash,
            "protocol_results": [item.as_dict() for item in self.protocol_results],
            "observations": [item.as_dict() for item in self.observations],
        }


AblationCoordinationRuntimeFactory = Callable[
    [str, Path, tuple[str, ...], str], CognitiveCoordinationRuntime
]


class CognitiveOrganizationAblationRuntime:
    """Execute one-component-at-a-time organization variants under one frozen trial."""

    module_id = COGNITIVE_ORGANIZATION_ABLATION_VERSION
    capabilities = (
        "kernel_authorized_matched_ablation_execution",
        "blind_ablation_semantic_assessment",
        "harness_owned_ablation_metrics",
        "replayable_ablation_bundle",
    )

    def __init__(
        self,
        *,
        runtime_id: str,
        experiment_plan: OrganizationExperimentPlan,
        formation_runtime: CognitiveTeamFormationRuntime,
        registry: AgentRegistry,
        trial_spec: CognitiveExecutionTrialSpec,
        team_adapters: dict[str, CognitiveAgentRuntimeAdapter],
        normalization_router: ProviderTaskRouter,
        semantic_assessment_router: ProviderTaskRouter,
        trial_harness: FrozenFindingTrialHarness,
        workspace_root: str | Path,
        coordination_runtime_factory: AblationCoordinationRuntimeFactory | None,
        unsynthesized_normalization_router: ProviderTaskRouter | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime_id):
            raise ValueError("organization_ablation_runtime_id_invalid")
        if (
            experiment_plan.execution_authorized is not True
            or experiment_plan.candidate_state != "AUTHORIZED_FOR_EXPERIMENT"
            or not experiment_plan.kernel_authorization_ref.startswith("kernel://")
        ):
            raise ValueError("organization_ablation_requires_kernel_authorized_plan")
        selected = tuple(experiment_plan.selected_variants)
        if not selected or len(set(selected)) != len(selected) or not set(selected).issubset(
            SUPPORTED_ABLATION_VARIANTS
        ):
            raise ValueError("organization_ablation_selected_variants_unsupported")
        max_runs = experiment_plan.budget.get("max_trial_runs")
        max_calls = experiment_plan.budget.get("max_provider_calls_per_run")
        if not isinstance(max_runs, int) or isinstance(max_runs, bool) or max_runs < len(selected) + 1:
            raise ValueError("ablation_budget_must_cover_baseline_and_variants")
        if (
            not isinstance(max_calls, int)
            or isinstance(max_calls, bool)
            or max_calls < 1
            or max_calls < trial_spec.budget["max_provider_calls_per_arm"]
        ):
            raise ValueError("organization_ablation_provider_budget_invalid")
        formation = formation_runtime.snapshot()
        if formation.state != "TEAM_AUTHORIZED" or formation.proposal is None or formation.decision is None:
            raise ValueError("organization_ablation_requires_authorized_dynamic_team")
        if trial_spec.project_scope != formation_runtime.seed.project_scope:
            raise ValueError("organization_ablation_trial_scope_mismatch")
        if trial_spec.evidence_refs != formation_runtime.admitted_evidence_refs:
            raise ValueError("organization_ablation_trial_evidence_mismatch")
        if trial_spec.budget_hash != formation.decision.budget_hash:
            raise ValueError("organization_ablation_trial_budget_mismatch")
        dynamic_ids = formation.proposal.selected_agent_ids
        missing = set(dynamic_ids) - set(team_adapters)
        if missing:
            raise ValueError(f"organization_ablation_team_adapters_missing:{sorted(missing)}")
        synthesizers = [registry.get(agent_id) for agent_id in dynamic_ids if registry.get(agent_id).role == "SYNTHESIZER"]
        if len(synthesizers) != 1:
            raise ValueError("organization_ablation_requires_one_synthesizer")
        generators = [
            registry.get(agent_id)
            for agent_id in dynamic_ids
            if registry.get(agent_id).role == "HYPOTHESIS_GENERATOR"
        ]
        if len(generators) != 1:
            raise ValueError("organization_ablation_requires_one_generator")
        if "DYNAMIC_NO_SYNTHESIZER" in selected and unsynthesized_normalization_router is None:
            raise ValueError("organization_ablation_unsynthesized_normalizer_required")
        if coordination_runtime_factory is None and set(selected) != {"DYNAMIC_NO_COORDINATOR"}:
            raise ValueError("organization_ablation_coordinator_factory_required")

        self.runtime_id = runtime_id
        self.experiment_plan = experiment_plan
        self.formation_runtime = formation_runtime
        self.registry = registry
        self.trial_spec = trial_spec
        self.team_adapters = {agent_id: team_adapters[agent_id] for agent_id in dynamic_ids}
        self.normalization_router = normalization_router
        self.unsynthesized_normalization_router = unsynthesized_normalization_router
        self.semantic_assessment_router = semantic_assessment_router
        self.trial_harness = trial_harness
        self.coordination_runtime_factory = coordination_runtime_factory
        self.dynamic_agent_ids = tuple(dynamic_ids)
        self.synthesizer = synthesizers[0]
        self.generator = generators[0]
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.state = "READY"
        self._results: list[OrganizationAblationProtocolResult] = []
        self._observations: list[OrganizationAblationObservation] = []
        self._protocol_stores: dict[str, DeliberationEventStore] = {}
        self._cognition = ProviderBackedRuntimeCognitionLayer()
        self._event_store = DeliberationEventStore(self.workspace_root / "ablation-public", runtime_id)
        self._persist(
            "ORGANIZATION_ABLATION_INITIALIZED",
            {
                "experiment_plan_hash": experiment_plan.plan_hash,
                "selected_variants": list(selected),
                "trial_spec_hash": _hash_payload(trial_spec.as_dict()),
                "formation_decision_hash": formation.decision.decision_hash,
            },
        )

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    def verify_replay(self) -> dict[str, Any]:
        return self._event_store.verify()

    def verify_protocol_replays(self) -> dict[str, dict[str, Any]]:
        return {protocol: store.verify() for protocol, store in self._protocol_stores.items()}

    def execute_protocols(self) -> CognitiveOrganizationAblationSnapshot:
        if self.state != "READY":
            raise RuntimeError("organization_ablation_execution_window_closed")
        protocols = ("DYNAMIC_TEAM", *self.experiment_plan.selected_variants)
        try:
            self._results = [self._execute_protocol(protocol, index) for index, protocol in enumerate(protocols)]
        except Exception as exc:
            self.state = "BLOCKED"
            self._persist(
                "ORGANIZATION_ABLATION_EXECUTION_BLOCKED",
                {"error_type": type(exc).__name__, "error": str(exc)[:500]},
            )
            raise
        self.state = "PROTOCOLS_EXECUTED"
        self._persist(
            "ORGANIZATION_ABLATION_PROTOCOLS_EXECUTED",
            {"result_hashes": [item.result_hash for item in self._results]},
        )
        return self.snapshot()

    def evaluate_protocols(self) -> CognitiveOrganizationAblationSnapshot:
        if self.state != "PROTOCOLS_EXECUTED":
            raise RuntimeError("organization_ablation_evaluation_requires_execution")
        replay = self.verify_protocol_replays()
        expected = {item.protocol_id for item in self._results}
        if set(replay) != expected or not all(item["valid"] for item in replay.values()):
            raise ValueError("organization_ablation_protocol_replay_invalid")
        observations = []
        for index, result in enumerate(self._results):
            receipt = self.trial_harness.evaluate(
                trial_id=self.trial_spec.trial_id,
                arm=result.protocol_id,
                candidate_output=result.candidate_output,
                finding_catalog=self.trial_spec.finding_catalog,
                evidence_refs=self.trial_spec.evidence_refs,
                provider_call_count=result.provider_call_count,
                max_provider_calls=self.trial_spec.budget["max_provider_calls_per_arm"],
                convergence_steps=result.convergence_steps,
                execution_receipt_refs=result.execution_receipt_refs,
            )
            observations.append(self._assess_blind(result, receipt, index))
        self._observations = observations
        self.state = "EVALUATED"
        self._persist(
            "ORGANIZATION_ABLATION_EVALUATED",
            {"observation_hashes": [item.observation_hash for item in observations]},
        )
        return self.snapshot()

    def snapshot(self) -> CognitiveOrganizationAblationSnapshot:
        return CognitiveOrganizationAblationSnapshot(
            runtime_id=self.runtime_id,
            state=self.state,
            experiment_plan_hash=self.experiment_plan.plan_hash,
            protocol_results=tuple(self._results),
            observations=tuple(self._observations),
        )

    def _execute_protocol(self, protocol_id: str, index: int) -> OrganizationAblationProtocolResult:
        omitted_components = PROTOCOL_COMPONENT_OMISSIONS[protocol_id]
        omitted_roles = tuple(item for item in omitted_components if item in _ROLE_OMISSIONS)
        descriptors = tuple(
            self.registry.get(agent_id)
            for agent_id in self.dynamic_agent_ids
            if self.registry.get(agent_id).role not in omitted_roles
        )
        agents = tuple(self._cognitive_agent(item, protocol_id) for item in descriptors)
        coordinator = None
        if "COORDINATOR" not in omitted_components:
            if self.coordination_runtime_factory is None:
                raise ValueError("organization_ablation_coordinator_factory_required")
            coordinator = self.coordination_runtime_factory(
                protocol_id,
                self.workspace_root / f"protocol-{index}" / "coordinator",
                omitted_roles,
                self.experiment_plan.kernel_authorization_ref,
            )
        blind_session_id = f"abl-{index}-{_hash_payload([self.runtime_id, index])[:12]}"
        session = CognitiveDeliberationSession(
            session_id=blind_session_id,
            objective=self.trial_spec.objective,
            project_scope=self.trial_spec.project_scope,
            frozen_gate_refs=self.trial_spec.frozen_gate_refs,
            evidence_refs=self.trial_spec.evidence_refs,
            evidence_payload=self.trial_spec.evidence_payload,
            agents=agents,
            adapters={item.agent_id: self.team_adapters[item.agent_id] for item in descriptors},
            workspace_root=self.workspace_root / f"protocol-{index}" / "private",
            kernel_authorization_ref=(
                f"{self.experiment_plan.kernel_authorization_ref}/protocol-{index}"
            ),
            coordination_runtime=coordinator,
            authorized_omitted_roles=omitted_roles,
            ablation_authorization_ref=(
                self.experiment_plan.kernel_authorization_ref if omitted_roles else ""
            ),
        )
        snapshot = session.run_to_candidate(
            max_retries_per_stage=self.trial_spec.budget.get("max_retries_per_stage", 0)
        )
        if snapshot.stage != "CANDIDATE" or snapshot.candidate_state != "PENDING_EPISTEMIC_REVIEW":
            raise RuntimeError(f"organization_ablation_protocol_not_candidate:{protocol_id}:{snapshot.stage}")
        unsynthesized = "SYNTHESIZER" in omitted_components
        if unsynthesized:
            normalization_messages = [
                item.as_dict() for item in snapshot.messages if item.message_type == "HYPOTHESIS_PROPOSAL"
            ]
            normalization_router = self.unsynthesized_normalization_router
            normalization_descriptor = self.generator
            normalization_objective = (
                "Project only the admitted Generator proposal into the frozen candidate schema. Do not read, "
                "integrate, or simulate Reviewer, Replicator, Coordinator, or Synthesizer judgments. Classify every "
                "public finding exactly once, preserve uncertainty, add no evidence, and cite only supplied aliases. "
                "Return non-empty answer and falsifier strings; derive the falsifier from the Generator proposal's "
                "falsifiable_predictions without inventing a new judgment."
            )
            projection_mode = "UNSYNTHESIZED_GENERATOR_PROPOSAL"
        else:
            normalization_messages = [item.as_dict() for item in snapshot.messages]
            normalization_router = self.normalization_router
            normalization_descriptor = self.synthesizer
            normalization_objective = (
                "Normalize the admitted formal receipts into one bounded candidate. Classify every public finding "
                "exactly once without adding evidence or final-state authority. Cite evidence only with the supplied "
                "E1, E2, ... aliases."
            )
            projection_mode = "BOUNDED_SYNTHESIS_NORMALIZATION"
        task = ProviderCognitiveTask(
            task_id=f"{self.runtime_id}-normalize-{index}",
            task_kind="team_trial_output_normalization",
            objective=normalization_objective,
            inputs={
                **self._provider_trial_inputs(),
                "projection_mode": projection_mode,
                "formal_messages": normalization_messages,
                "execution_receipt_refs": [item.receipt_hash for item in snapshot.execution_receipts],
            },
            allowed_evidence=list(self.trial_spec.evidence_refs),
            expected_schema=_candidate_schema(),
            budget=self.trial_spec.budget,
            failure_semantics="block_ablation_protocol_without_normalized_candidate",
        )
        if normalization_router is None:
            raise ValueError("organization_ablation_unsynthesized_normalizer_required")
        envelope = normalization_router.route(task)
        candidate = self._admit_candidate(
            envelope,
            normalization_descriptor,
            "team_trial_output_normalization",
        )
        invocation = envelope.invocation_receipt.as_dict()
        execution_receipts = tuple(item.as_dict() for item in snapshot.execution_receipts)
        coordination_receipts = tuple(item.as_dict() for item in snapshot.coordination_receipts)
        provider_calls = len(execution_receipts) + len(coordination_receipts) + 1
        if provider_calls > self.trial_spec.budget["max_provider_calls_per_arm"]:
            raise ValueError(f"organization_ablation_provider_budget_exceeded:{protocol_id}")
        store = DeliberationEventStore(session.public_store_path.parent, session.public_store_path.name)
        normalization_event = store.append(
            "ORGANIZATION_ABLATION_NORMALIZED",
            {
                "blind_protocol_slot": index,
                "candidate_output_hash": _hash_payload(candidate),
                "projection_mode": projection_mode,
                "provider_invocation_receipt": invocation,
            },
        )
        store.write_snapshot(session.snapshot())
        self._protocol_stores[protocol_id] = store
        receipt_refs = tuple(
            [f"execution://{item.receipt_hash}" for item in snapshot.execution_receipts]
            + [f"coordination://{item.receipt_hash}" for item in snapshot.coordination_receipts]
            + [f"provider-invocation://{invocation['receipt_hash']}"]
            + [f"deliberation-event://{normalization_event['event_hash']}"]
        )
        contexts = tuple(item.context_isolation_key for item in descriptors)
        created_at = _utc_now()
        committed = {
            "result_id": f"result-{self.runtime_id}-{index}",
            "protocol_id": protocol_id,
            "omitted_components": list(omitted_components),
            "agent_ids": [item.agent_id for item in descriptors],
            "context_isolation_keys": list(contexts),
            "candidate_output_hash": _hash_payload(candidate),
            "execution_receipt_refs": list(receipt_refs),
            "provider_call_count": provider_calls,
            "convergence_steps": provider_calls,
            "coordination_receipt_count": len(coordination_receipts),
            "coordinator_agent_id": coordinator.coordinator.agent_id if coordinator else "",
            "replay_verification": store.verify(),
            "created_at": created_at,
            "execution_authorized": True,
        }
        return OrganizationAblationProtocolResult(
            result_id=committed["result_id"],
            protocol_id=protocol_id,
            omitted_components=tuple(omitted_components),
            agent_ids=tuple(item.agent_id for item in descriptors),
            context_isolation_keys=contexts,
            candidate_output=candidate,
            formal_messages=tuple(item.as_dict() for item in snapshot.messages),
            execution_receipts=(*execution_receipts, *coordination_receipts, invocation),
            execution_receipt_refs=receipt_refs,
            provider_call_count=provider_calls,
            convergence_steps=provider_calls,
            coordination_receipt_count=len(coordination_receipts),
            coordinator_agent_id=committed["coordinator_agent_id"],
            replay_verification=committed["replay_verification"],
            created_at=created_at,
            result_hash=_hash_payload(committed),
        )

    def _assess_blind(
        self,
        result: OrganizationAblationProtocolResult,
        harness_receipt: CognitiveTrialHarnessReceipt,
        index: int,
    ) -> OrganizationAblationObservation:
        mechanical = {name: getattr(harness_receipt, name) for name in _MECHANICAL_FIELDS}
        blind_id = f"blind-{_hash_payload([self.runtime_id, self.trial_spec.trial_id, index])[:16]}"
        task = ProviderCognitiveTask(
            task_id=f"{self.runtime_id}-blind-assessment-{index}",
            task_kind="team_trial_semantic_assessment",
            objective=(
                "Assess this anonymous candidate's epistemic quality. Do not infer its organization. Copy every "
                "Harness-owned metric exactly and cite evidence only with the supplied E1, E2, ... aliases. "
                "Return quality_score as a finite decimal between 0.0 and 1.0 inclusive; never use a 0-100 scale."
            ),
            inputs={
                "trial_id": self.trial_spec.trial_id,
                "blind_arm_id": blind_id,
                "harness_protocol_id": self.trial_harness.module_id,
                "budget_hash": self.trial_spec.budget_hash,
                "harness_receipt_ref": f"harness://{harness_receipt.receipt_hash}",
                "harness_owned_metrics": mechanical,
                "semantic_artifact": result.candidate_output,
                "allowed_evidence_refs": list(self.trial_spec.evidence_refs),
                "evidence_aliases": self._evidence_aliases(),
            },
            allowed_evidence=list(self.trial_spec.evidence_refs),
            expected_schema={
                "type": "object",
                "required": ["blind_arm_id", "quality_score", *_MECHANICAL_FIELDS, "evidence_refs"],
                "properties": {
                    "blind_arm_id": {"type": "string"},
                    "quality_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
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
            budget=self.trial_spec.budget,
            failure_semantics="block_ablation_observation_without_blind_semantic_assessment",
        )
        envelope = self.semantic_assessment_router.route(task)
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            raise RuntimeError(f"organization_ablation_assessment_provider_blocked:{envelope.status}")
        payload = dict(envelope.normalized_result or {})
        errors = self._assessment_errors(payload, blind_id, mechanical)
        audit = self._cognition.audit_operation(
            "team_trial_semantic_assessment",
            {"provider_support_receipt": payload, "provider_support_receipt_hash": _hash_payload(payload)},
        )
        if audit.get("status") not in _PASS_PROVIDER_AUDITS:
            errors.append(f"organization_ablation_assessment_audit_failed:{audit.get('status')}")
        if errors:
            raise ValueError(";".join(errors))
        invocation = envelope.invocation_receipt.as_dict()
        quality = float(payload["quality_score"])
        effectiveness = self._effectiveness(quality, mechanical)
        committed = {
            "observation_id": f"observation-{self.runtime_id}-{index}",
            "protocol_id": result.protocol_id,
            "result_hash": result.result_hash,
            "quality_score": quality,
            "effectiveness_score": effectiveness,
            "harness_receipt_hash": harness_receipt.receipt_hash,
            "semantic_assessment_receipt_ref": f"provider-receipt://{invocation['receipt_hash']}",
            "blind_candidate_id": blind_id,
            "provider_cited_evidence_refs": list(payload["evidence_refs"]),
            "evidence_refs": list(self.trial_spec.evidence_refs),
        }
        return OrganizationAblationObservation(
            observation_id=committed["observation_id"],
            protocol_id=result.protocol_id,
            result_hash=result.result_hash,
            quality_score=quality,
            effectiveness_score=effectiveness,
            harness_receipt=harness_receipt,
            semantic_assessment_receipt_ref=committed["semantic_assessment_receipt_ref"],
            blind_candidate_id=blind_id,
            provider_cited_evidence_refs=tuple(payload["evidence_refs"]),
            evidence_refs=self.trial_spec.evidence_refs,
            observation_hash=_hash_payload(committed),
        )

    def _admit_candidate(
        self,
        envelope: Any,
        descriptor: AgentDescriptor,
        operation_id: str,
    ) -> dict[str, Any]:
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            raise RuntimeError(f"organization_ablation_candidate_provider_blocked:{envelope.status}")
        if (
            envelope.invocation_receipt.provider_id != descriptor.provider_id
            or envelope.invocation_receipt.model_id != descriptor.model_id
        ):
            raise ValueError("organization_ablation_normalizer_provider_binding_mismatch")
        candidate = dict(envelope.normalized_result or {})
        errors = self._candidate_errors(candidate)
        audit = self._cognition.audit_operation(
            operation_id,
            {"provider_support_receipt": candidate, "provider_support_receipt_hash": _hash_payload(candidate)},
        )
        if audit.get("status") not in _PASS_PROVIDER_AUDITS:
            errors.append(f"organization_ablation_candidate_audit_failed:{audit.get('status')}")
        if errors:
            raise ValueError(";".join(errors))
        candidate["provider_cited_evidence_refs"] = list(candidate["evidence_refs"])
        candidate["evidence_refs"] = list(self.trial_spec.evidence_refs)
        return candidate

    def _candidate_errors(self, candidate: dict[str, Any]) -> list[str]:
        errors = []
        for name in ("answer", "falsifier"):
            if not isinstance(candidate.get(name), str) or not candidate[name].strip():
                errors.append(f"organization_ablation_candidate_string_required:{name}")
        arrays = (
            "supported_finding_ids",
            "rejected_finding_ids",
            "unresolved_finding_ids",
            "rival_explanations",
            "evidence_refs",
            "uncertainties",
        )
        for name in arrays:
            if not isinstance(candidate.get(name), list) or not all(isinstance(item, str) for item in candidate[name]):
                errors.append(f"organization_ablation_candidate_string_array_required:{name}")
        if errors:
            return errors
        classifications = [
            *candidate["supported_finding_ids"],
            *candidate["rejected_finding_ids"],
            *candidate["unresolved_finding_ids"],
        ]
        catalog = {item.finding_id for item in self.trial_spec.finding_catalog}
        if len(classifications) != len(set(classifications)):
            errors.append("organization_ablation_candidate_classification_overlap")
        if set(classifications) != catalog:
            errors.append("organization_ablation_candidate_coverage_mismatch")
        refs = candidate["evidence_refs"]
        allowed_refs = set(self.trial_spec.evidence_refs) | set(self._evidence_alias_map())
        if not refs or len(refs) != len(set(refs)) or not set(refs).issubset(allowed_refs):
            errors.append("organization_ablation_candidate_evidence_invalid")
        if _contains_key(candidate, _AUTHORITY_KEYS):
            errors.append("organization_ablation_candidate_authority_forbidden")
        if _contains_key(candidate, _HIDDEN_TRUTH_KEYS):
            errors.append("organization_ablation_candidate_hidden_truth_forbidden")
        return errors

    def _assessment_errors(self, payload: dict[str, Any], blind_id: str, mechanical: dict[str, Any]) -> list[str]:
        errors = []
        quality = payload.get("quality_score")
        if (
            not isinstance(quality, (int, float))
            or isinstance(quality, bool)
            or not math.isfinite(float(quality))
            or not 0.0 <= float(quality) <= 1.0
        ):
            errors.append("organization_ablation_quality_score_invalid")
        if payload.get("blind_arm_id") != blind_id:
            errors.append("organization_ablation_blind_id_mismatch")
        for name, expected in mechanical.items():
            if payload.get(name) != expected:
                errors.append(f"organization_ablation_harness_metric_override:{name}")
        refs = payload.get("evidence_refs")
        resolved_refs = self._resolve_provider_refs(refs) if isinstance(refs, list) else ()
        if (
            not isinstance(refs, list)
            or not refs
            or len(refs) != len(set(refs))
            or not set(resolved_refs).issubset(self.trial_spec.evidence_refs)
        ):
            errors.append("organization_ablation_assessment_evidence_mismatch")
        if _contains_key(payload, _AUTHORITY_KEYS | _HIDDEN_TRUTH_KEYS):
            errors.append("organization_ablation_assessment_forbidden_claim")
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

    def _evidence_alias_map(self) -> dict[str, str]:
        return {item["alias"]: item["evidence_ref"] for item in self._evidence_aliases()}

    def _resolve_provider_refs(self, refs: list[str]) -> tuple[str, ...]:
        aliases = self._evidence_alias_map()
        return tuple(aliases.get(ref, ref) for ref in refs)

    def _cognitive_agent(self, descriptor: AgentDescriptor, protocol_id: str) -> CognitiveAgent:
        namespace = f"abl-{_hash_payload([self.runtime_id, protocol_id, descriptor.agent_id])[:16]}"
        return CognitiveAgent(
            descriptor=descriptor,
            contract=standard_role_contract(descriptor.role),
            model_id=descriptor.model_id,
            private_memory_namespace=namespace,
            harness_capabilities=(descriptor.harness_id, *descriptor.capabilities),
            credit_subject_id=f"credit-{protocol_id.lower()}-{descriptor.agent_id}",
        )

    @staticmethod
    def _effectiveness(quality: float, mechanical: dict[str, Any]) -> float:
        correction = (
            mechanical["errors_corrected"] / mechanical["errors_exposed"]
            if mechanical["errors_exposed"]
            else 0.0
        )
        interception = (
            mechanical["negative_transfer_intercepts"] / mechanical["negative_transfer_opportunities"]
            if mechanical["negative_transfer_opportunities"]
            else 0.0
        )
        score = (
            0.45 * quality
            + 0.35 * mechanical["observed_cbit_gain"]
            + 0.10 * correction
            + 0.10 * interception
            - 0.15 * mechanical["normalized_cost"]
        )
        return round(max(0.0, min(1.0, score)), 12)

    def _persist(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_store.append(event_type, payload)
        self._event_store.write_snapshot(self.snapshot())
