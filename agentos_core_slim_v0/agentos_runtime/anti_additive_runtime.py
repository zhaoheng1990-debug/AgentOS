"""Thin Provider-backed orchestration for Anti-Additive Methodology reviews."""

from __future__ import annotations

import re
from pathlib import Path

from agentos_kernel import (
    AntiAdditiveChangeCandidate,
    AntiAdditiveMethodologyGate,
    AntiAdditiveMethodologyPolicy,
    AntiAdditiveMethodologyReceipt,
    CognitiveWorkControlDecision,
    ProviderTaskRouter,
)

from .anti_additive_provider import AntiAdditiveProviderAdvisor
from .anti_additive_repository import AntiAdditiveMethodologyRepository
from .anti_additive_calibration_source import (
    AntiAdditiveCalibrationSource,
    resolve_anti_additive_calibration_control,
)


class AntiAdditiveMethodologyRuntime:
    """Keep semantic support, Kernel authority, and replay as separate modules."""

    module_id = "anti_additive_methodology_runtime_v0_1"
    capabilities = (
        "provider_supported_first_principles_audit",
        "kernel_owned_patch_accumulation_gate",
        "object_upgrade_and_abstraction_cost_control",
        "project_scoped_receipt_replay",
    )

    def __init__(
        self,
        *,
        runtime_id: str,
        project_scope: str,
        provider_router: ProviderTaskRouter,
        workspace_root: str | Path,
        gate: AntiAdditiveMethodologyGate | None = None,
        policy: AntiAdditiveMethodologyPolicy | None = None,
        calibration_source: AntiAdditiveCalibrationSource | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime_id):
            raise ValueError("anti_additive_runtime_id_invalid")
        if not project_scope.startswith("project://"):
            raise ValueError("anti_additive_runtime_project_scope_invalid")
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self.gate = gate or AntiAdditiveMethodologyGate()
        self.policy = policy or AntiAdditiveMethodologyPolicy()
        self.calibration_source = calibration_source
        self._repository = AntiAdditiveMethodologyRepository(
            runtime_id=runtime_id,
            project_scope=project_scope,
            workspace_root=workspace_root,
        )
        self._provider = AntiAdditiveProviderAdvisor(
            runtime_id=runtime_id,
            provider_router=provider_router,
            event_sink=self._repository.persist_event,
        )

    @property
    def public_store_path(self) -> Path:
        return self._repository.public_store_path

    def review_change(
        self,
        *,
        candidate: AntiAdditiveChangeCandidate,
        kernel_authorization_ref: str,
        cognitive_work_control: CognitiveWorkControlDecision | None = None,
    ) -> AntiAdditiveMethodologyReceipt:
        if candidate.project_scope != self.project_scope:
            raise ValueError("anti_additive_runtime_cross_scope_candidate")
        judgment = self._provider.assess(candidate)
        calibration_control = resolve_anti_additive_calibration_control(
            source=self.calibration_source,
            candidate=candidate,
        )
        receipt = self.gate.review(
            candidate=candidate,
            judgment=judgment,
            policy=self.policy,
            kernel_authorization_ref=kernel_authorization_ref,
            calibration_control=calibration_control,
            cognitive_work_control=cognitive_work_control,
        )
        self._repository.persist_receipt(receipt)
        return receipt

    def verify_replay(self) -> dict[str, object]:
        return self._repository.verify_replay()

    def methodology_receipt(self, *, audit_id: str, project_scope: str):
        return self._repository.methodology_receipt(audit_id=audit_id, project_scope=project_scope)
