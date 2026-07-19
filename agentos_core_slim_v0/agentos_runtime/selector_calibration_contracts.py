"""Runtime snapshot contract for Selector calibration receipts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentos_kernel import SelectorCalibrationReceipt
from agentos_kernel.contextual_policy_models import hash_payload


SELECTOR_CALIBRATION_RUNTIME_VERSION = "selector_calibration_drift_runtime_v0_1"


def selector_calibration_scope_key(*, context_key: str, evidence_tier: str, policy_id: str) -> str:
    return hash_payload(
        {"context_key": context_key, "evidence_tier": evidence_tier, "policy_id": policy_id}
    )


@dataclass(frozen=True)
class SelectorCalibrationSnapshot:
    runtime_id: str
    project_scope: str
    receipts: tuple[SelectorCalibrationReceipt, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "project_scope": self.project_scope,
            "receipts": [item.as_dict() for item in self.receipts],
        }
