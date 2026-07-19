"""Shared constants and validators for Selector calibration contracts."""

from __future__ import annotations

import math
import re
from typing import Any


SELECTOR_CALIBRATION_VERSION = "selector_calibration_drift_kernel_v0_1"
SELECTOR_CALIBRATION_STATES = (
    "INSUFFICIENT_HISTORY",
    "CALIBRATED",
    "WATCH",
    "DRIFTED",
)
SELECTOR_DIAGNOSTIC_STATES = (
    "INSUFFICIENT_HISTORY",
    "NO_SEMANTIC_DRIFT",
    "POSSIBLE_SEMANTIC_DRIFT",
    "MATERIAL_SEMANTIC_DRIFT",
)
SELECTOR_DRIFT_DRIVERS = (
    "SCOPE_CHANGE",
    "EVIDENCE_CHANGE",
    "MODEL_CHANGE",
    "HARNESS_CHANGE",
    "SYSTEMATIC_CBIT_BIAS",
    "SYSTEMATIC_COST_BIAS",
    "RESIDUAL_RISK_MISMATCH",
    "UNKNOWN",
)
SELECTOR_CALIBRATION_ACTIONS = (
    "COLLECT_MORE",
    "KEEP_CURRENT_CALIBRATION",
    "REASSESS_CONTEXT_POLICY",
    "SUSPEND_PREDICTION_TRUST",
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def require_calibration_hash(name: str, value: str, *, allow_empty: bool = False) -> None:
    if allow_empty and value == "":
        return
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{name}_invalid")


def require_signed_unit(name: str, value: Any) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or not -1.0 <= float(value) <= 1.0
    ):
        raise ValueError(f"{name}_outside_signed_unit_interval")
    return float(value)
