"""Kernel-gated four-role cognitive deliberation runtime."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol

from agentos_kernel import (
    BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT,
    BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    ProviderBackedRuntimeCognitionLayer,
)

from .cognitive_roles import (
    CognitiveAgent,
    CognitiveMessage,
    PrivateAgentWorkspace,
)


COGNITIVE_DELIBERATION_VERSION = "cognitive_deliberation_session_v0_4"

SESSION_STAGES = (
    "COORDINATION",
    "GENERATION",
    "REVIEW",
    "REPLICATION",
    "SYNTHESIS",
    "CANDIDATE",
    "BLOCKED",
)

_STAGE_ROLE = {
    "GENERATION": "HYPOTHESIS_GENERATOR",
    "REVIEW": "ADVERSARIAL_REVIEWER",
    "REPLICATION": "REPLICATOR",
    "SYNTHESIS": "SYNTHESIZER",
}

_NEXT_STAGE = {
    "GENERATION": "REVIEW",
    "REVIEW": "REPLICATION",
    "REPLICATION": "SYNTHESIS",
    "SYNTHESIS": "CANDIDATE",
}

_ORDERED_EXECUTION_STAGES = ("GENERATION", "REVIEW", "REPLICATION", "SYNTHESIS")
_ABLATION_OMITTABLE_ROLES = {"ADVERSARIAL_REVIEWER", "REPLICATOR", "SYNTHESIZER"}

_AGENT_AUTHORITY_KEYS = {
    "accepted",
    "asset_promotion_authorized",
    "execution_authorized",
    "final_candidate_state",
    "permission_granted",
    "published",
}

_PASS_PROVIDER_AUDITS = {
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _message_ref(message: CognitiveMessage) -> str:
    return f"message://{message.message_id}/{message.message_hash}"


@dataclass(frozen=True)
class CognitiveContextView:
    session_id: str
    objective: str
    project_scope: str
    role: str
    context_isolation_key: str
    private_workspace_descriptor: dict[str, str]
    frozen_gate_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    evidence_payload: dict[str, Any]
    input_messages: tuple[CognitiveMessage, ...]
    excluded_message_refs: tuple[str, ...]
    coordination_state: dict[str, Any] = field(default_factory=dict)
    runtime_state: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "objective": self.objective,
            "project_scope": self.project_scope,
            "role": self.role,
            "context_isolation_key": self.context_isolation_key,
            "private_workspace_descriptor": self.private_workspace_descriptor,
            "frozen_gate_refs": list(self.frozen_gate_refs),
            "evidence_refs": list(self.evidence_refs),
            "evidence_payload": self.evidence_payload,
            "input_messages": [message.as_dict() for message in self.input_messages],
            "excluded_message_refs": list(self.excluded_message_refs),
            "coordination_state": self.coordination_state,
            "runtime_state": self.runtime_state,
        }

    @property
    def context_hash(self) -> str:
        return _hash_payload(self.as_dict())


@dataclass(frozen=True)
class CognitiveWorkOrder:
    work_order_id: str
    session_id: str
    agent_id: str
    role: str
    stage: str
    objective: str
    role_contract_id: str
    input_message_refs: tuple[str, ...]
    allowed_evidence_refs: tuple[str, ...]
    output_schema: dict[str, Any]
    kernel_authorization_ref: str
    semantic_consistency_assertions: tuple[dict[str, Any], ...] = ()

    @property
    def work_order_hash(self) -> str:
        return _hash_payload(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "work_order_id": self.work_order_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "stage": self.stage,
            "objective": self.objective,
            "role_contract_id": self.role_contract_id,
            "input_message_refs": list(self.input_message_refs),
            "allowed_evidence_refs": list(self.allowed_evidence_refs),
            "output_schema": self.output_schema,
            "kernel_authorization_ref": self.kernel_authorization_ref,
            "semantic_consistency_assertions": list(self.semantic_consistency_assertions),
        }


@dataclass(frozen=True)
class AgentAdapterResult:
    status: str
    provider_support_receipt: dict[str, Any] | None
    provider_id: str
    model_id: str
    invocation_receipt_ref: str
    validation_errors: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()
    provider_envelope: dict[str, Any] | None = None


class CognitiveAgentRuntimeAdapter(Protocol):
    adapter_id: str

    def invoke(
        self,
        cognitive_agent: CognitiveAgent,
        work_order: CognitiveWorkOrder,
        context_view: CognitiveContextView,
        private_workspace: PrivateAgentWorkspace,
    ) -> AgentAdapterResult:
        """Execute one bounded role without owning Kernel state transitions."""


@dataclass(frozen=True)
class CognitiveExecutionReceipt:
    receipt_id: str
    session_id: str
    work_order_id: str
    agent_id: str
    role: str
    stage: str
    status: str
    context_hash: str
    work_order_hash: str
    provider_id: str
    model_id: str
    invocation_receipt_ref: str
    provider_audit: dict[str, Any]
    provider_invocation_receipt: dict[str, Any] = field(default_factory=dict)
    message_ref: str = ""
    errors: tuple[str, ...] = ()
    created_at: str = field(default_factory=_utc_now)
    receipt_hash: str = ""

    @classmethod
    def create(cls, **values: Any) -> "CognitiveExecutionReceipt":
        created_at = _utc_now()
        committed = {**values, "created_at": created_at}
        return cls(**values, created_at=created_at, receipt_hash=_hash_payload(committed))

    def as_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "session_id": self.session_id,
            "work_order_id": self.work_order_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "stage": self.stage,
            "status": self.status,
            "context_hash": self.context_hash,
            "work_order_hash": self.work_order_hash,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "invocation_receipt_ref": self.invocation_receipt_ref,
            "provider_audit": self.provider_audit,
            "provider_invocation_receipt": self.provider_invocation_receipt,
            "message_ref": self.message_ref,
            "errors": list(self.errors),
            "created_at": self.created_at,
            "receipt_hash": self.receipt_hash,
        }


@dataclass(frozen=True)
class DeliberationSnapshot:
    session_id: str
    stage: str
    candidate_state: str
    messages: tuple[CognitiveMessage, ...]
    execution_receipts: tuple[CognitiveExecutionReceipt, ...]
    blocked_stage: str = ""
    coordination_proposals: tuple[Any, ...] = ()
    coordination_receipts: tuple[CognitiveExecutionReceipt, ...] = ()
    coordination_block_reason: str = ""
    authorized_omitted_roles: tuple[str, ...] = ()
    ablation_authorization_ref: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "stage": self.stage,
            "candidate_state": self.candidate_state,
            "blocked_stage": self.blocked_stage,
            "coordination_block_reason": self.coordination_block_reason,
            "authorized_omitted_roles": list(self.authorized_omitted_roles),
            "ablation_authorization_ref": self.ablation_authorization_ref,
            "messages": [message.as_dict() for message in self.messages],
            "execution_receipts": [receipt.as_dict() for receipt in self.execution_receipts],
            "coordination_proposals": [proposal.as_dict() for proposal in self.coordination_proposals],
            "coordination_receipts": [receipt.as_dict() for receipt in self.coordination_receipts],
        }


class DeliberationEventStore:
    """Public hash-chained session events and latest replay snapshot."""

    def __init__(self, root: str | Path, session_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", session_id):
            raise ValueError("deliberation_session_id_path_invalid")
        self.root = Path(root).resolve()
        self.path = (self.root / session_id).resolve()
        if self.root not in self.path.parents:
            raise ValueError("deliberation_store_path_escape")
        self.path.mkdir(parents=True, exist_ok=True)
        self.events_path = self.path / "events.jsonl"
        self.snapshot_path = self.path / "snapshot.json"

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        events = self.events()
        event = {
            "event_index": len(events),
            "event_type": event_type,
            "payload": payload,
            "previous_event_hash": events[-1]["event_hash"] if events else "",
            "created_at": _utc_now(),
        }
        event["event_hash"] = _hash_payload(event)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
        return event

    def write_snapshot(self, snapshot: DeliberationSnapshot) -> dict[str, Any]:
        payload = snapshot.as_dict()
        record = {
            "snapshot": payload,
            "snapshot_hash": _hash_payload(payload),
            "updated_at": _utc_now(),
        }
        self.snapshot_path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        return record

    def events(self) -> tuple[dict[str, Any], ...]:
        if not self.events_path.exists():
            return ()
        return tuple(json.loads(line) for line in self.events_path.read_text(encoding="utf-8").splitlines() if line)

    def verify(self) -> dict[str, Any]:
        events = self.events()
        previous_hash = ""
        failures: list[str] = []
        for index, event in enumerate(events):
            committed = dict(event)
            recorded_hash = committed.pop("event_hash", "")
            if event.get("event_index") != index:
                failures.append(f"event_index_mismatch:{index}")
            if event.get("previous_event_hash") != previous_hash:
                failures.append(f"event_chain_mismatch:{index}")
            if _hash_payload(committed) != recorded_hash:
                failures.append(f"event_hash_mismatch:{index}")
            previous_hash = recorded_hash
        if not self.snapshot_path.exists():
            failures.append("snapshot_missing")
        else:
            record = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
            if _hash_payload(record.get("snapshot")) != record.get("snapshot_hash"):
                failures.append("snapshot_hash_mismatch")
        return {
            "valid": not failures,
            "event_count": len(events),
            "failures": failures,
            "head_event_hash": previous_hash,
        }


class CognitiveDeliberationSession:
    """Four-role organization with explicit information barriers and Kernel gates."""

    module_id = COGNITIVE_DELIBERATION_VERSION
    capabilities = ("four_role_cognitive_deliberation", "formal_receipt_exchange")

    @classmethod
    def from_deliberation_seed(
        cls,
        *,
        seed: Any,
        session_id: str,
        frozen_gate_refs: tuple[str, ...],
        agents: tuple[CognitiveAgent, ...],
        adapters: dict[str, CognitiveAgentRuntimeAdapter],
        workspace_root: str | Path,
        kernel_authorization_ref: str,
        coordination_runtime: Any | None = None,
        evidence_payload_overrides: dict[str, Any] | None = None,
        consistency_assertions_by_role: dict[str, tuple[dict[str, Any], ...]] | None = None,
        authorized_omitted_roles: tuple[str, ...] = (),
        ablation_authorization_ref: str = "",
    ) -> "CognitiveDeliberationSession":
        if getattr(seed, "candidate_state", "") != "PENDING_AGENDA_REVIEW":
            raise ValueError("deliberation_seed_not_pending_agenda_review")
        if getattr(seed, "execution_authorized", True) is not False:
            raise ValueError("deliberation_seed_must_not_carry_execution_authority")
        intake = seed.as_coordination_intake()
        evidence_payload = dict(intake["evidence_payload"])
        evidence_payload.update(evidence_payload_overrides or {})
        return cls(
            session_id=session_id,
            objective=intake["objective"],
            project_scope=intake["project_scope"],
            frozen_gate_refs=frozen_gate_refs,
            evidence_refs=tuple(intake["evidence_refs"]),
            evidence_payload=evidence_payload,
            agents=agents,
            adapters=adapters,
            workspace_root=workspace_root,
            kernel_authorization_ref=kernel_authorization_ref,
            consistency_assertions_by_role=consistency_assertions_by_role,
            coordination_runtime=coordination_runtime,
            authorized_omitted_roles=authorized_omitted_roles,
            ablation_authorization_ref=ablation_authorization_ref,
        )

    def __init__(
        self,
        *,
        session_id: str,
        objective: str,
        project_scope: str,
        frozen_gate_refs: tuple[str, ...],
        evidence_refs: tuple[str, ...],
        evidence_payload: dict[str, Any] | None = None,
        agents: tuple[CognitiveAgent, ...],
        adapters: dict[str, CognitiveAgentRuntimeAdapter],
        workspace_root: str | Path,
        kernel_authorization_ref: str,
        consistency_assertions_by_role: dict[str, tuple[dict[str, Any], ...]] | None = None,
        coordination_runtime: Any | None = None,
        authorized_omitted_roles: tuple[str, ...] = (),
        ablation_authorization_ref: str = "",
    ) -> None:
        if not all((session_id, objective, project_scope, kernel_authorization_ref)):
            raise ValueError("deliberation_session_identity_incomplete")
        if not frozen_gate_refs or not evidence_refs:
            raise ValueError("deliberation_frozen_gates_and_evidence_required")
        omitted = tuple(authorized_omitted_roles)
        if len(omitted) > 1 or not set(omitted).issubset(_ABLATION_OMITTABLE_ROLES):
            raise ValueError("deliberation_ablation_omitted_roles_invalid")
        if omitted and not ablation_authorization_ref.startswith("kernel://"):
            raise ValueError("deliberation_role_omission_not_authorized")
        if not omitted and ablation_authorization_ref:
            raise ValueError("deliberation_ablation_authorization_without_omission")
        self.session_id = session_id
        self.objective = objective
        self.project_scope = project_scope
        self.frozen_gate_refs = tuple(frozen_gate_refs)
        self.evidence_refs = tuple(evidence_refs)
        self.evidence_payload = dict(evidence_payload or {})
        self.kernel_authorization_ref = kernel_authorization_ref
        self.authorized_omitted_roles = omitted
        self.ablation_authorization_ref = ablation_authorization_ref
        self._active_stages = tuple(
            stage for stage in _ORDERED_EXECUTION_STAGES if _STAGE_ROLE[stage] not in omitted
        )
        self._agents = {agent.role: agent for agent in agents}
        self._adapters = dict(adapters)
        self._consistency_assertions = dict(consistency_assertions_by_role or {})
        self._messages: list[CognitiveMessage] = []
        self._receipts: list[CognitiveExecutionReceipt] = []
        self._coordination_runtime = coordination_runtime
        self._coordination_proposals: list[Any] = []
        self._coordination_receipts: list[CognitiveExecutionReceipt] = []
        self._coordination_origin_stage = "INTAKE" if coordination_runtime else ""
        self._coordination_block_reason = ""
        self._role_execution_counts = {role: 0 for role in _STAGE_ROLE.values()}
        self._stage = "COORDINATION" if coordination_runtime else self._active_stages[0]
        self._blocked_stage = ""
        self._candidate_state = "NOT_FORMED"
        self._cognition_layer = ProviderBackedRuntimeCognitionLayer()
        self._validate_team(agents)
        self._workspaces = {
            agent.agent_id: PrivateAgentWorkspace(workspace_root, agent.agent_id, agent.private_memory_namespace)
            for agent in agents
        }
        public_root = Path(workspace_root).resolve().parent / "deliberation-public"
        self._event_store = DeliberationEventStore(public_root, session_id)
        self._persist(
            "SESSION_INITIALIZED",
            {
                "kernel_authorization_ref": kernel_authorization_ref,
                "authorized_omitted_roles": list(self.authorized_omitted_roles),
                "ablation_authorization_ref": self.ablation_authorization_ref,
            },
        )

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    def verify_replay(self) -> dict[str, Any]:
        return self._event_store.verify()

    def execute_current(self) -> DeliberationSnapshot:
        if self._stage == "BLOCKED":
            raise RuntimeError("deliberation_blocked_use_retry_blocked")
        if self._stage == "CANDIDATE":
            return self.snapshot()
        if self._stage == "COORDINATION":
            return self._execute_coordination()
        stage = self._stage
        role = _STAGE_ROLE[stage]
        agent = self._agents[role]
        contract = agent.contract
        workspace = self._workspaces[agent.agent_id]
        input_messages, excluded_refs = self._select_input_messages(contract.allowed_input_message_types)
        input_refs = tuple(_message_ref(message) for message in input_messages)
        allowed_evidence = tuple(dict.fromkeys((*self.evidence_refs, *self.frozen_gate_refs, *input_refs)))
        context = CognitiveContextView(
            session_id=self.session_id,
            objective=self.objective,
            project_scope=self.project_scope,
            role=role,
            context_isolation_key=agent.descriptor.context_isolation_key,
            private_workspace_descriptor=workspace.public_descriptor(),
            frozen_gate_refs=self.frozen_gate_refs,
            evidence_refs=self.evidence_refs,
            evidence_payload=self.evidence_payload,
            input_messages=input_messages,
            excluded_message_refs=excluded_refs,
        )
        work_order = CognitiveWorkOrder(
            work_order_id=f"{self.session_id}-{stage.lower()}-{len(self._receipts) + 1}",
            session_id=self.session_id,
            agent_id=agent.agent_id,
            role=role,
            stage=stage,
            objective=contract.purpose,
            role_contract_id=contract.contract_id,
            input_message_refs=input_refs,
            allowed_evidence_refs=allowed_evidence,
            output_schema=contract.expected_schema(),
            kernel_authorization_ref=self.kernel_authorization_ref,
            semantic_consistency_assertions=self._consistency_assertions.get(role, ()),
        )
        workspace.append(agent.agent_id, "WORK_ORDER_RECEIVED", {"work_order": work_order.as_dict()})
        try:
            result = self._adapters[agent.agent_id].invoke(agent, work_order, context, workspace)
        except Exception as exc:
            return self._block(stage, agent, work_order, context, None, {}, (f"agent_adapter_error:{type(exc).__name__}:{exc}",))

        errors, provider_audit = self._validate_result(agent, work_order, result)
        if errors:
            return self._block(stage, agent, work_order, context, result, provider_audit, tuple(errors))

        payload = result.provider_support_receipt or {}
        message = CognitiveMessage.create(
            message_id=f"{self.session_id}-{contract.output_message_type.lower()}-{len(self._messages) + 1}",
            session_id=self.session_id,
            sender_agent_id=agent.agent_id,
            sender_role=role,
            message_type=contract.output_message_type,
            payload=payload,
            evidence_refs=tuple(payload["evidence_refs"]),
            parent_message_refs=input_refs,
        )
        receipt = CognitiveExecutionReceipt.create(
            receipt_id=f"execution-{self.session_id}-{len(self._receipts) + 1}",
            session_id=self.session_id,
            work_order_id=work_order.work_order_id,
            agent_id=agent.agent_id,
            role=role,
            stage=stage,
            status="COMPLETED",
            context_hash=context.context_hash,
            work_order_hash=work_order.work_order_hash,
            provider_id=result.provider_id,
            model_id=result.model_id,
            invocation_receipt_ref=result.invocation_receipt_ref,
            provider_audit=provider_audit,
            provider_invocation_receipt=(result.provider_envelope or {}).get("invocation_receipt", {}),
            message_ref=_message_ref(message),
        )
        self._messages.append(message)
        self._receipts.append(receipt)
        self._role_execution_counts[role] += 1
        workspace.append(
            agent.agent_id,
            "FORMAL_MESSAGE_EMITTED",
            {"message_ref": receipt.message_ref, "execution_receipt_hash": receipt.receipt_hash},
        )
        if self._coordination_runtime is not None:
            self._coordination_origin_stage = stage
            self._stage = "COORDINATION"
        else:
            self._stage = self._next_active_stage(stage)
            if self._stage == "CANDIDATE":
                self._candidate_state = "PENDING_EPISTEMIC_REVIEW"
        self._persist(
            "ROLE_COMPLETED",
            {
                "stage": stage,
                "role": role,
                "message_ref": receipt.message_ref,
                "execution_receipt_hash": receipt.receipt_hash,
                "next_stage": self._stage,
            },
        )
        return self.snapshot()

    def retry_blocked(self) -> DeliberationSnapshot:
        if self._stage != "BLOCKED" or not self._blocked_stage:
            raise RuntimeError("deliberation_not_blocked")
        if self._blocked_stage == "COORDINATION":
            self._stage = "COORDINATION"
            self._blocked_stage = ""
            self._coordination_block_reason = ""
            return self.execute_current()
        self._stage = self._blocked_stage
        self._blocked_stage = ""
        return self.execute_current()

    def run_to_candidate(self, *, max_retries_per_stage: int = 0) -> DeliberationSnapshot:
        if max_retries_per_stage < 0:
            raise ValueError("max_retries_per_stage_must_be_nonnegative")
        retries: dict[str, int] = {}
        while self._stage != "CANDIDATE":
            if self._stage == "BLOCKED":
                blocked_stage = self._blocked_stage
                retry_key = (
                    f"COORDINATION:{self._coordination_origin_stage}"
                    if blocked_stage == "COORDINATION"
                    else blocked_stage
                )
                used = retries.get(retry_key, 0)
                if used >= max_retries_per_stage:
                    break
                retries[retry_key] = used + 1
                self.retry_blocked()
                continue
            self.execute_current()
        return self.snapshot()

    def snapshot(self) -> DeliberationSnapshot:
        return DeliberationSnapshot(
            session_id=self.session_id,
            stage=self._stage,
            candidate_state=self._candidate_state,
            messages=tuple(self._messages),
            execution_receipts=tuple(self._receipts),
            blocked_stage=self._blocked_stage,
            coordination_proposals=tuple(self._coordination_proposals),
            coordination_receipts=tuple(self._coordination_receipts),
            coordination_block_reason=self._coordination_block_reason,
            authorized_omitted_roles=self.authorized_omitted_roles,
            ablation_authorization_ref=self.ablation_authorization_ref,
        )

    def _validate_team(self, agents: tuple[CognitiveAgent, ...]) -> None:
        expected_roles = set(_STAGE_ROLE.values()) - set(self.authorized_omitted_roles)
        expected_count = len(expected_roles)
        if set(self._agents) != expected_roles or len(agents) != expected_count:
            if self.authorized_omitted_roles:
                raise ValueError("ablation_session_role_set_mismatch")
            raise ValueError("first_stage_requires_exactly_four_cognitive_roles")
        if len({agent.agent_id for agent in agents}) != expected_count:
            raise ValueError("cognitive_team_agent_identity_not_isolated")
        if len({agent.descriptor.context_isolation_key for agent in agents}) != expected_count:
            raise ValueError("cognitive_team_context_not_isolated")
        if len({agent.private_memory_namespace for agent in agents}) != expected_count:
            raise ValueError("cognitive_team_private_memory_not_isolated")
        if len({agent.credit_subject_id for agent in agents}) != expected_count:
            raise ValueError("cognitive_team_credit_identity_not_isolated")
        if any(self.project_scope not in agent.descriptor.allowed_evidence_scopes for agent in agents):
            raise ValueError("cognitive_agent_project_scope_not_allowed")
        if set(self._adapters) != {agent.agent_id for agent in agents}:
            raise ValueError("cognitive_agent_adapter_binding_incomplete")
        if self._coordination_runtime is not None:
            coordinator = self._coordination_runtime.coordinator
            if tuple(getattr(self._coordination_runtime, "authorized_omitted_roles", ())) != self.authorized_omitted_roles:
                raise ValueError("coordination_ablation_contract_mismatch")
            if coordinator.role != "COORDINATOR":
                raise ValueError("cognitive_coordination_requires_coordinator_role")
            if coordinator.agent_id in {agent.agent_id for agent in agents}:
                raise ValueError("coordinator_agent_identity_not_isolated")
            if coordinator.descriptor.context_isolation_key in {
                agent.descriptor.context_isolation_key for agent in agents
            }:
                raise ValueError("coordinator_context_not_isolated")
            if coordinator.private_memory_namespace in {agent.private_memory_namespace for agent in agents}:
                raise ValueError("coordinator_private_memory_not_isolated")
            if coordinator.credit_subject_id in {agent.credit_subject_id for agent in agents}:
                raise ValueError("coordinator_credit_identity_not_isolated")
            if self.project_scope not in coordinator.descriptor.allowed_evidence_scopes:
                raise ValueError("coordinator_project_scope_not_allowed")

    def _next_active_stage(self, stage: str) -> str:
        index = self._active_stages.index(stage)
        return self._active_stages[index + 1] if index + 1 < len(self._active_stages) else "CANDIDATE"

    def _execute_coordination(self) -> DeliberationSnapshot:
        if self._coordination_runtime is None:
            raise RuntimeError("coordination_runtime_not_configured")
        decision = self._coordination_runtime.coordinate(
            session_id=self.session_id,
            objective=self.objective,
            project_scope=self.project_scope,
            frozen_gate_refs=self.frozen_gate_refs,
            evidence_refs=self.evidence_refs,
            evidence_payload=self.evidence_payload,
            messages=tuple(self._messages),
            role_execution_counts=dict(self._role_execution_counts),
            current_stage=self._coordination_origin_stage,
            kernel_authorization_ref=self.kernel_authorization_ref,
        )
        self._coordination_receipts.append(decision.receipt)
        if decision.proposal is not None:
            self._coordination_proposals.append(decision.proposal)
        if decision.status == "APPLIED":
            self._stage = decision.next_stage
            self._blocked_stage = ""
            self._coordination_block_reason = ""
            if self._stage == "CANDIDATE":
                self._candidate_state = "PENDING_EPISTEMIC_REVIEW"
            self._persist(
                "COORDINATION_APPLIED",
                {
                    "origin_stage": self._coordination_origin_stage,
                    "next_stage": decision.next_stage,
                    "proposal_hash": decision.proposal.proposal_hash if decision.proposal else "",
                    "coordination_receipt_hash": decision.receipt.receipt_hash,
                },
            )
            return self.snapshot()
        self._stage = "BLOCKED"
        self._blocked_stage = "COORDINATION"
        self._coordination_block_reason = ";".join(decision.errors)
        self._persist(
            "COORDINATION_BLOCKED",
            {
                "origin_stage": self._coordination_origin_stage,
                "coordination_receipt_hash": decision.receipt.receipt_hash,
                "errors": list(decision.errors),
            },
        )
        return self.snapshot()

    def _select_input_messages(
        self,
        allowed_types: tuple[str, ...],
    ) -> tuple[tuple[CognitiveMessage, ...], tuple[str, ...]]:
        selected = tuple(message for message in self._messages if message.message_type in allowed_types)
        excluded = tuple(_message_ref(message) for message in self._messages if message.message_type not in allowed_types)
        return selected, excluded

    def _validate_result(
        self,
        agent: CognitiveAgent,
        work_order: CognitiveWorkOrder,
        result: AgentAdapterResult,
    ) -> tuple[list[str], dict[str, Any]]:
        errors = list(result.validation_errors)
        if result.status != "COMPLETED":
            errors.append(f"agent_adapter_status:{result.status}")
        if result.status == "COMPLETED" and (
            result.provider_id != agent.descriptor.provider_id or result.model_id != agent.model_id
        ):
            errors.append("agent_provider_binding_mismatch")
        if not result.invocation_receipt_ref:
            errors.append("provider_invocation_receipt_ref_required")
        payload = result.provider_support_receipt
        if not isinstance(payload, dict):
            errors.append("provider_support_receipt_required")
            return errors, {}
        errors.extend(_validate_schema(work_order.output_schema, payload))
        if _contains_authority_key(payload):
            errors.append("agent_final_state_authority_forbidden")
        provider_evidence = payload.get("evidence_refs")
        if isinstance(provider_evidence, list) and any(
            ref not in work_order.allowed_evidence_refs for ref in provider_evidence
        ):
            errors.append("provider_evidence_ref_not_admitted")
        record: dict[str, Any] = {"provider_support_receipt": payload}
        if work_order.semantic_consistency_assertions:
            record["semantic_consistency_assertions"] = work_order.semantic_consistency_assertions
        provider_audit = self._cognition_layer.audit_operation(agent.contract.provider_operation_id, record)
        if provider_audit["status"] not in _PASS_PROVIDER_AUDITS:
            missing = provider_audit.get("missing_provider_outputs", [])
            suffix = f":missing={','.join(missing)}" if missing else ""
            errors.append(f"provider_support_audit:{provider_audit['status']}{suffix}")
        return list(dict.fromkeys(errors)), provider_audit

    def _block(
        self,
        stage: str,
        agent: CognitiveAgent,
        work_order: CognitiveWorkOrder,
        context: CognitiveContextView,
        result: AgentAdapterResult | None,
        provider_audit: dict[str, Any],
        errors: tuple[str, ...],
    ) -> DeliberationSnapshot:
        receipt = CognitiveExecutionReceipt.create(
            receipt_id=f"execution-{self.session_id}-{len(self._receipts) + 1}",
            session_id=self.session_id,
            work_order_id=work_order.work_order_id,
            agent_id=agent.agent_id,
            role=agent.role,
            stage=stage,
            status="BLOCKED",
            context_hash=context.context_hash,
            work_order_hash=work_order.work_order_hash,
            provider_id=result.provider_id if result else agent.descriptor.provider_id,
            model_id=result.model_id if result else agent.model_id,
            invocation_receipt_ref=result.invocation_receipt_ref if result else "",
            provider_audit=provider_audit,
            provider_invocation_receipt=(result.provider_envelope or {}).get("invocation_receipt", {}) if result else {},
            errors=errors,
        )
        self._receipts.append(receipt)
        self._workspaces[agent.agent_id].append(
            agent.agent_id,
            "EXECUTION_BLOCKED",
            {"errors": list(errors), "execution_receipt_hash": receipt.receipt_hash},
        )
        self._blocked_stage = stage
        self._stage = "BLOCKED"
        self._persist(
            "ROLE_BLOCKED",
            {
                "stage": stage,
                "role": agent.role,
                "execution_receipt_hash": receipt.receipt_hash,
                "errors": list(errors),
            },
        )
        return self.snapshot()

    def _persist(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_store.append(event_type, payload)
        self._event_store.write_snapshot(self.snapshot())


def _contains_authority_key(value: Any) -> bool:
    if isinstance(value, dict):
        if any(str(key).lower() in _AGENT_AUTHORITY_KEYS for key in value):
            return True
        return any(_contains_authority_key(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_authority_key(item) for item in value)
    return False


def _validate_schema(schema: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in schema.get("required", []):
        if field_name not in payload:
            errors.append(f"missing_required_field:{field_name}")
    for field_name, spec in (schema.get("properties") or {}).items():
        if field_name not in payload:
            continue
        value = payload[field_name]
        expected_type = spec.get("type")
        valid_type = {
            "array": isinstance(value, list),
            "object": isinstance(value, dict),
            "string": isinstance(value, str),
            "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
        }.get(expected_type, True)
        if not valid_type:
            errors.append(f"field_type_mismatch:{field_name}:{expected_type}")
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"field_enum_mismatch:{field_name}")
    return errors
