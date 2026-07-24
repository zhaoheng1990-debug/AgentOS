"""Thin Provider-backed orchestration for cognitive-work accounting."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from agentos_kernel import ProviderBackedRuntimeCognitionLayer, ProviderTaskRouter
from agentos_kernel.cognitive_work_eval import CognitiveWorkEvaluator
from agentos_kernel.cognitive_work_models import CognitiveWorkBudget, CognitiveWorkRoundObservation

from .cognitive_work_contracts import (
    COGNITIVE_WORK_RUNTIME_VERSION,
    CognitiveWorkRoundReceipt,
    CognitiveWorkSnapshot,
    utc_now,
)
from .cognitive_work_provider import CognitiveWorkProviderAdvisor
from .cognitive_work_repository import CognitiveWorkRepository


class CognitiveWorkAccountingRuntime:
    """Account exact work, request semantic support, and retain Kernel control."""

    module_id = COGNITIVE_WORK_RUNTIME_VERSION
    capabilities = (
        "exact_cognitive_work_accounting",
        "provider_supported_round_diagnostics",
        "kernel_owned_marginal_cbit_control",
        "project_scoped_append_only_replay",
    )

    def __init__(
        self,
        *,
        runtime_id: str,
        project_scope: str,
        provider_router: ProviderTaskRouter,
        budget: CognitiveWorkBudget,
        workspace_root: str | Path,
        evaluator: CognitiveWorkEvaluator | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime_id):
            raise ValueError("cognitive_work_runtime_id_invalid")
        if not project_scope.startswith("project://"):
            raise ValueError("cognitive_work_runtime_scope_invalid")
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self.budget = budget
        self.evaluator = evaluator or CognitiveWorkEvaluator()
        self._cognition = ProviderBackedRuntimeCognitionLayer()
        self._repository = CognitiveWorkRepository(
            runtime_id=runtime_id,
            project_scope=project_scope,
            workspace_root=workspace_root,
        )
        self._provider = CognitiveWorkProviderAdvisor(
            runtime_id=runtime_id,
            provider_router=provider_router,
            event_sink=self._repository.persist_event,
        )

    @property
    def public_store_path(self) -> Path:
        return self._repository.public_store_path

    def account_round(
        self,
        *,
        receipt_id: str,
        observation: CognitiveWorkRoundObservation,
        kernel_authorization_ref: str,
    ) -> CognitiveWorkRoundReceipt:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", receipt_id):
            raise ValueError("cognitive_work_receipt_id_invalid")
        if observation.project_scope != self.project_scope:
            raise ValueError("cognitive_work_runtime_cross_scope_observation")
        try:
            prior = self._repository.receipts(observation.trajectory_id)
            assessment, invocation, audit = self._provider.assess(
                observation,
                prior_control=prior[-1].kernel_control.as_dict() if prior else None,
            )
            observations = tuple(item.observation for item in prior) + (observation,)
            assessments = tuple(item.semantic_assessment for item in prior) + (assessment,)
            provider_hashes = tuple(
                item.provider_invocation_receipt["receipt_hash"] for item in prior
            ) + (invocation["receipt_hash"],)
            control = self.evaluator.evaluate(
                decision_id=f"{receipt_id}-kernel",
                observations=observations,
                assessments=assessments,
                provider_receipt_hashes=provider_hashes,
                budget=self.budget,
                kernel_authorization_ref=kernel_authorization_ref,
            )
            mechanical_audit = self._cognition.audit_operation(
                "cognitive_work_trajectory_accounting",
                {"kernel_control": control.as_dict(), "budget": self.budget.as_dict()},
            )
            receipt = CognitiveWorkRoundReceipt.create(
                receipt_id=receipt_id,
                runtime_id=self.runtime_id,
                observation=observation,
                semantic_assessment=assessment,
                provider_invocation_receipt=invocation,
                provider_audit=audit,
                mechanical_audit=mechanical_audit,
                kernel_control=control,
                budget=self.budget,
                created_at=utc_now(),
            )
            self._repository.save(receipt)
            return receipt
        except Exception as exc:
            self._repository.persist_event(
                "COGNITIVE_WORK_ACCOUNTING_BLOCKED",
                {
                    "receipt_id": receipt_id,
                    "observation_hash": observation.observation_hash,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                },
            )
            raise

    def latest_control(self, trajectory_id: str):
        return self._repository.latest_control(trajectory_id)

    def snapshot(self) -> CognitiveWorkSnapshot:
        return self._repository.snapshot()

    def verify_replay(self) -> dict[str, Any]:
        return self._repository.verify_replay()
