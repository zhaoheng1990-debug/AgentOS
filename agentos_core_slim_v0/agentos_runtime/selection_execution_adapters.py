"""Adapters from existing execution runtimes to strong policy outcomes."""

from __future__ import annotations

from typing import Protocol

from agentos_kernel import (
    ARM_BEST_MEMBER,
    ARM_DYNAMIC_TEAM,
    ARM_FIXED_TEAM,
    AgentDescriptor,
    CONTEXTUAL_POLICY_COMPARATORS,
    CONTEXTUAL_POLICY_ROLE_MAP,
    ExecutedProtocolFootprint,
    PolicyExecutionBundle,
    PolicyExecutionOutcome,
    SelectionExecutionRequest,
)
from agentos_kernel.contextual_policy_models import hash_payload

from .organization_ablation import CognitiveOrganizationAblationRuntime
from .team_execution import CognitiveTeamExecutionRuntime


_ARM_PROTOCOL = {
    ARM_BEST_MEMBER: "SOLO",
    ARM_FIXED_TEAM: "FIXED_TEAM",
    ARM_DYNAMIC_TEAM: "DYNAMIC_TEAM",
}
_TEAM_SCORE_FIELD = {
    "SOLO": "best_member_score",
    "FIXED_TEAM": "fixed_team_score",
    "DYNAMIC_TEAM": "dynamic_team_score",
}


class SelectionPolicyExecutionAdapter(Protocol):
    adapter_id: str

    def execute(self, request: SelectionExecutionRequest) -> PolicyExecutionBundle:
        """Execute the selected policy and its matched comparator."""


class TeamExecutionPolicyAdapter:
    """Use the existing three-arm runtime for SOLO/FIXED/DYNAMIC policies."""

    def __init__(
        self,
        *,
        adapter_id: str,
        runtime: CognitiveTeamExecutionRuntime,
        best_member_agent_id: str,
        coordinator_descriptors: dict[str, AgentDescriptor] | None = None,
    ) -> None:
        self.adapter_id = adapter_id
        self.runtime = runtime
        self.best_member_agent_id = best_member_agent_id
        self.coordinator_descriptors = dict(coordinator_descriptors or {})

    def execute(self, request: SelectionExecutionRequest) -> PolicyExecutionBundle:
        if request.selected_policy_id not in {"SOLO", "FIXED_TEAM", "DYNAMIC_TEAM"}:
            raise ValueError("team_execution_adapter_policy_unsupported")
        self._validate_trial(request)
        self._validate_budget(request)
        self.runtime.execute_arms(best_member_agent_id=self.best_member_agent_id)
        evaluation = self.runtime.evaluate_arms()
        snapshot = self.runtime.snapshot()
        by_arm = {item.arm: item for item in snapshot.arm_results}
        receipts = {item.arm: item for item in snapshot.harness_receipts}
        executed_protocols = tuple(
            ExecutedProtocolFootprint.create(
                protocol_id=_ARM_PROTOCOL[result.arm],
                provider_call_count=result.provider_call_count,
                normalized_cost=receipts[result.arm].normalized_cost,
                execution_result_hash=result.result_hash,
                harness_receipt_hash=receipts[result.arm].receipt_hash,
            )
            for result in snapshot.arm_results
        )
        replay = self._replay()
        source_hash = hash_payload(
            {"snapshot": snapshot.as_dict(), "replay": replay, "request_hash": request.request_hash}
        )
        required = {
            request.selected_policy_id,
            CONTEXTUAL_POLICY_COMPARATORS[request.selected_policy_id],
        }
        outcomes = tuple(
            self._outcome(
                request=request,
                protocol_id=protocol_id,
                result=by_arm[self._arm_for(protocol_id)],
                receipt=receipts[self._arm_for(protocol_id)],
                effectiveness_score=getattr(evaluation, _TEAM_SCORE_FIELD[protocol_id]),
                source_hash=source_hash,
            )
            for protocol_id in sorted(required)
        )
        return PolicyExecutionBundle.create(
            bridge_run_id=request.bridge_run_id,
            selection_receipt_hash=request.selection_receipt_hash,
            selected_policy_id=request.selected_policy_id,
            execution_adapter_id=self.adapter_id,
            outcomes=outcomes,
            executed_protocols=executed_protocols,
            execution_replay=replay,
        )

    def _validate_trial(self, request: SelectionExecutionRequest) -> None:
        trial = self.runtime.trial_spec
        if (
            trial.trial_id != request.trial_id
            or trial.project_scope != request.project_scope
            or trial.evidence_refs != request.trial_evidence_refs
        ):
            raise ValueError("team_execution_adapter_trial_binding_mismatch")

    def _validate_budget(self, request: SelectionExecutionRequest) -> None:
        protocol_runs = 3
        max_calls_per_arm = self.runtime.trial_spec.budget["max_provider_calls_per_arm"]
        if request.execution_budget.max_protocol_runs < protocol_runs:
            raise ValueError("team_execution_adapter_protocol_budget_insufficient")
        if request.execution_budget.max_provider_calls_total < protocol_runs * max_calls_per_arm:
            raise ValueError("team_execution_adapter_provider_budget_insufficient")

    def _replay(self) -> dict:
        runtime_replay = self.runtime.verify_replay()
        arm_replays = self.runtime.verify_arm_replays()
        valid = runtime_replay.get("valid") is True and arm_replays and all(
            item.get("valid") is True for item in arm_replays.values()
        )
        return {"valid": valid, "runtime": runtime_replay, "arms": arm_replays}

    def _outcome(self, *, request, protocol_id, result, receipt, effectiveness_score, source_hash):
        roles = CONTEXTUAL_POLICY_ROLE_MAP[protocol_id]
        agent_ids = tuple(result.agent_ids)
        if "COORDINATOR" in roles:
            if not result.coordinator_agent_id:
                raise ValueError(f"team_execution_adapter_coordinator_missing:{protocol_id}")
            agent_ids = (*agent_ids, result.coordinator_agent_id)
        elif result.coordinator_agent_id:
            raise ValueError(f"team_execution_adapter_unselected_coordinator:{protocol_id}")
        if len(agent_ids) != len(roles):
            raise ValueError(f"team_execution_adapter_role_cardinality_mismatch:{protocol_id}")
        descriptors = [self.runtime.registry.get(agent_id) for agent_id in result.agent_ids]
        if result.coordinator_agent_id:
            coordinator = self.coordinator_descriptors.get(protocol_id)
            if coordinator is None or coordinator.agent_id != result.coordinator_agent_id:
                raise ValueError(f"team_execution_adapter_coordinator_binding_missing:{protocol_id}")
            descriptors.append(coordinator)
        self._validate_harness(receipt, request)
        return PolicyExecutionOutcome.create(
            outcome_id=f"outcome-{request.bridge_run_id}-{protocol_id.lower()}",
            protocol_id=protocol_id,
            agent_ids=agent_ids,
            roles=roles,
            agent_binding_hash=hash_payload([self._agent_dict(item) for item in descriptors]),
            project_scope=request.project_scope,
            context_key=request.context_key,
            evidence_tier=request.evidence_tier,
            trial_group_id=request.trial_group_id,
            trial_id=request.trial_id,
            trial_surface_hash=request.trial_surface_hash,
            evidence_refs=request.trial_evidence_refs,
            effectiveness_score=effectiveness_score,
            observed_cbit_gain=receipt.observed_cbit_gain,
            normalized_cost=receipt.normalized_cost,
            provider_call_count=result.provider_call_count,
            convergence_steps=receipt.convergence_steps,
            errors_exposed=receipt.errors_exposed,
            errors_corrected=receipt.errors_corrected,
            negative_transfer_opportunities=receipt.negative_transfer_opportunities,
            negative_transfer_intercepts=receipt.negative_transfer_intercepts,
            harness_receipt_ref=f"harness://{receipt.receipt_hash}",
            harness_receipt_hash=receipt.receipt_hash,
            execution_result_hash=result.result_hash,
            source_result_hash=source_hash,
            replay_valid=True,
        )

    @staticmethod
    def _validate_harness(receipt, request) -> None:
        if receipt.harness_owned is not True or receipt.semantic_provider_used is not False:
            raise ValueError("team_execution_adapter_harness_ownership_invalid")
        if receipt.trial_id != request.trial_id or receipt.evidence_refs != request.trial_evidence_refs:
            raise ValueError("team_execution_adapter_harness_binding_mismatch")

    @staticmethod
    def _agent_dict(agent: AgentDescriptor) -> dict:
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
        }

    @staticmethod
    def _arm_for(protocol_id: str) -> str:
        return next(arm for arm, protocol in _ARM_PROTOCOL.items() if protocol == protocol_id)


class AblationExecutionPolicyAdapter:
    """Use the existing matched-ablation runtime for omission policies."""

    def __init__(
        self,
        *,
        adapter_id: str,
        runtime: CognitiveOrganizationAblationRuntime,
        coordinator_descriptors: dict[str, AgentDescriptor] | None = None,
    ) -> None:
        self.adapter_id = adapter_id
        self.runtime = runtime
        self.coordinator_descriptors = dict(coordinator_descriptors or {})

    def execute(self, request: SelectionExecutionRequest) -> PolicyExecutionBundle:
        if request.selected_policy_id not in CONTEXTUAL_POLICY_COMPARATORS or not request.selected_policy_id.startswith(
            "DYNAMIC_NO_"
        ):
            raise ValueError("ablation_execution_adapter_policy_unsupported")
        self._validate_trial(request)
        if request.selected_policy_id not in self.runtime.experiment_plan.selected_variants:
            raise ValueError("ablation_execution_adapter_variant_not_authorized")
        self._validate_budget(request)
        self.runtime.execute_protocols()
        snapshot = self.runtime.evaluate_protocols()
        by_protocol = {item.protocol_id: item for item in snapshot.protocol_results}
        observations = {item.protocol_id: item for item in snapshot.observations}
        executed_protocols = tuple(
            ExecutedProtocolFootprint.create(
                protocol_id=result.protocol_id,
                provider_call_count=result.provider_call_count,
                normalized_cost=observations[result.protocol_id].harness_receipt.normalized_cost,
                execution_result_hash=result.result_hash,
                harness_receipt_hash=observations[result.protocol_id].harness_receipt.receipt_hash,
            )
            for result in snapshot.protocol_results
        )
        replay = self._replay()
        source_hash = hash_payload(
            {"snapshot": snapshot.as_dict(), "replay": replay, "request_hash": request.request_hash}
        )
        required = {request.selected_policy_id, "DYNAMIC_TEAM"}
        outcomes = tuple(
            self._outcome(
                request=request,
                result=by_protocol[protocol_id],
                observation=observations[protocol_id],
                source_hash=source_hash,
            )
            for protocol_id in sorted(required)
        )
        return PolicyExecutionBundle.create(
            bridge_run_id=request.bridge_run_id,
            selection_receipt_hash=request.selection_receipt_hash,
            selected_policy_id=request.selected_policy_id,
            execution_adapter_id=self.adapter_id,
            outcomes=outcomes,
            executed_protocols=executed_protocols,
            execution_replay=replay,
        )

    def _validate_trial(self, request: SelectionExecutionRequest) -> None:
        trial = self.runtime.trial_spec
        if (
            trial.trial_id != request.trial_id
            or trial.project_scope != request.project_scope
            or trial.evidence_refs != request.trial_evidence_refs
        ):
            raise ValueError("ablation_execution_adapter_trial_binding_mismatch")

    def _validate_budget(self, request: SelectionExecutionRequest) -> None:
        protocol_runs = len(self.runtime.experiment_plan.selected_variants) + 1
        max_calls_per_run = self.runtime.experiment_plan.budget["max_provider_calls_per_run"]
        if request.execution_budget.max_protocol_runs < protocol_runs:
            raise ValueError("ablation_execution_adapter_protocol_budget_insufficient")
        if request.execution_budget.max_provider_calls_total < protocol_runs * max_calls_per_run:
            raise ValueError("ablation_execution_adapter_provider_budget_insufficient")

    def _replay(self) -> dict:
        runtime_replay = self.runtime.verify_replay()
        protocol_replays = self.runtime.verify_protocol_replays()
        valid = runtime_replay.get("valid") is True and protocol_replays and all(
            item.get("valid") is True for item in protocol_replays.values()
        )
        return {"valid": valid, "runtime": runtime_replay, "protocols": protocol_replays}

    def _outcome(self, *, request, result, observation, source_hash):
        protocol_id = result.protocol_id
        roles = CONTEXTUAL_POLICY_ROLE_MAP[protocol_id]
        agent_ids = tuple(result.agent_ids)
        if "COORDINATOR" in roles:
            if not result.coordinator_agent_id:
                raise ValueError(f"ablation_execution_adapter_coordinator_missing:{protocol_id}")
            agent_ids = (*agent_ids, result.coordinator_agent_id)
        elif result.coordinator_agent_id:
            raise ValueError(f"ablation_execution_adapter_unselected_coordinator:{protocol_id}")
        receipt = observation.harness_receipt
        if receipt.harness_owned is not True or receipt.semantic_provider_used is not False:
            raise ValueError("ablation_execution_adapter_harness_ownership_invalid")
        if receipt.trial_id != request.trial_id or receipt.evidence_refs != request.trial_evidence_refs:
            raise ValueError("ablation_execution_adapter_harness_binding_mismatch")
        descriptors = [self.runtime.registry.get(agent_id) for agent_id in result.agent_ids]
        if result.coordinator_agent_id:
            coordinator = self.coordinator_descriptors.get(protocol_id)
            if coordinator is None or coordinator.agent_id != result.coordinator_agent_id:
                raise ValueError(f"ablation_execution_adapter_coordinator_binding_missing:{protocol_id}")
            descriptors.append(coordinator)
        return PolicyExecutionOutcome.create(
            outcome_id=f"outcome-{request.bridge_run_id}-{protocol_id.lower()}",
            protocol_id=protocol_id,
            agent_ids=agent_ids,
            roles=roles,
            agent_binding_hash=hash_payload([TeamExecutionPolicyAdapter._agent_dict(item) for item in descriptors]),
            project_scope=request.project_scope,
            context_key=request.context_key,
            evidence_tier=request.evidence_tier,
            trial_group_id=request.trial_group_id,
            trial_id=request.trial_id,
            trial_surface_hash=request.trial_surface_hash,
            evidence_refs=request.trial_evidence_refs,
            effectiveness_score=observation.effectiveness_score,
            observed_cbit_gain=receipt.observed_cbit_gain,
            normalized_cost=receipt.normalized_cost,
            provider_call_count=result.provider_call_count,
            convergence_steps=receipt.convergence_steps,
            errors_exposed=receipt.errors_exposed,
            errors_corrected=receipt.errors_corrected,
            negative_transfer_opportunities=receipt.negative_transfer_opportunities,
            negative_transfer_intercepts=receipt.negative_transfer_intercepts,
            harness_receipt_ref=f"harness://{receipt.receipt_hash}",
            harness_receipt_hash=receipt.receipt_hash,
            execution_result_hash=result.result_hash,
            source_result_hash=source_hash,
            replay_valid=True,
        )
