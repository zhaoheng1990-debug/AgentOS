"""Typed Provider failure carrying all charged current-case work."""

from __future__ import annotations

from typing import Any

from .collective_protocol import RoleRun
from .failure_receipt_accounting import summarize_failed_session_receipts
from .failure_decision_accounting import failed_decision_artifacts
from .failure_problem_accounting import failed_problem_artifacts
from .failure_work_accounting import summarize_failed_session_work
from .provider_telemetry import hash_payload


class DisagreementCaseProviderFailure(RuntimeError):
    def __init__(self, *, stage: str, run: RoleRun, failures: tuple[str, ...]) -> None:
        super().__init__("disagreement_case_provider_failed:" + stage)
        self.stage = stage
        self.runs = (run,)
        self.failures = failures

    def prepend(self, runs: tuple[RoleRun, ...]) -> "DisagreementCaseProviderFailure":
        self.runs = (*runs, *self.runs)
        return self

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage, "failures": list(self.failures),
            "model_ids": [item.model_id for item in self.runs],
            "result_shapes": [sorted(item.result) for item in self.runs],
            "result_hashes": [hash_payload(item.result) for item in self.runs],
            "task_ids": [task.task_id for run in self.runs for task in run.tasks],
            "task_contract_hashes": [task.contract_hash() for run in self.runs for task in run.tasks],
            "telemetry_errors": [item.error_type for run in self.runs
                                 for item in run.telemetry if item.error_type],
            "provider_calls": sum(len(run.telemetry) for run in self.runs),
            "total_tokens": sum(item.input_tokens + item.output_tokens for run in self.runs for item in run.telemetry),
            **summarize_failed_session_work(self.runs),
            **summarize_failed_session_receipts(self.runs),
            **failed_decision_artifacts(self.runs),
            **failed_problem_artifacts(self.runs),
        }
