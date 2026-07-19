"""Runtime snapshot for problem-structure admission."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentos_kernel import ProblemStructureAdmissionReceipt


PROBLEM_STRUCTURE_ADMISSION_RUNTIME_VERSION = "problem_structure_admission_runtime_v0_1"


@dataclass(frozen=True)
class ProblemStructureAdmissionSnapshot:
    runtime_id: str
    project_scope: str
    receipts: tuple[ProblemStructureAdmissionReceipt, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "project_scope": self.project_scope,
            "receipts": [item.as_dict() for item in self.receipts],
        }
