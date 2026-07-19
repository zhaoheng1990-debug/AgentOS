"""Profile, Provider judgment, decision, and receipt contracts for Selector calibration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contextual_policy_models import (
    CONTEXTUAL_POLICY_ROLE_MAP,
    hash_payload,
    require_refs,
    require_text,
    require_unit,
)
from .selector_calibration_base import (
    SELECTOR_CALIBRATION_ACTIONS,
    SELECTOR_CALIBRATION_STATES,
    SELECTOR_CALIBRATION_VERSION,
    SELECTOR_DIAGNOSTIC_STATES,
    SELECTOR_DRIFT_DRIVERS,
    require_calibration_hash,
    require_signed_unit,
)
from .selector_calibration_observation import (
    SelectorCalibrationObservation,
    SelectorCalibrationThresholds,
)


@dataclass(frozen=True)
class SelectorCalibrationProfile:
    profile_id: str
    project_scope: str
    context_key: str
    evidence_tier: str
    policy_id: str
    observation_count: int
    independent_source_count: int
    mean_absolute_cbit_error: float
    mean_cbit_bias: float
    mean_absolute_cost_error: float
    mean_cost_bias: float
    cbit_uncertainty_coverage: float
    mean_residual_risk_error: float | None
    mechanical_state: str
    observation_hashes: tuple[str, ...]
    source_result_hashes: tuple[str, ...]
    threshold_hash: str
    profile_hash: str

    def __post_init__(self) -> None:
        for name in ("profile_id", "context_key", "evidence_tier"):
            require_text(f"selector_calibration_profile_{name}", getattr(self, name))
        if not self.project_scope.startswith("project://"):
            raise ValueError("selector_calibration_profile_scope_invalid")
        if self.policy_id not in CONTEXTUAL_POLICY_ROLE_MAP:
            raise ValueError("selector_calibration_profile_policy_invalid")
        if self.observation_count < 1 or self.observation_count != len(self.observation_hashes):
            raise ValueError("selector_calibration_profile_observation_count_invalid")
        if self.independent_source_count != len(self.source_result_hashes):
            raise ValueError("selector_calibration_profile_source_count_invalid")
        if not 1 <= self.independent_source_count <= self.observation_count:
            raise ValueError("selector_calibration_profile_independence_invalid")
        if len(set(self.observation_hashes)) != self.observation_count:
            raise ValueError("selector_calibration_profile_duplicate_observation")
        if len(set(self.source_result_hashes)) != self.independent_source_count:
            raise ValueError("selector_calibration_profile_duplicate_source")
        for name in (
            "mean_absolute_cbit_error",
            "mean_absolute_cost_error",
            "cbit_uncertainty_coverage",
        ):
            require_unit(f"selector_calibration_profile_{name}", getattr(self, name))
        require_signed_unit("selector_calibration_profile_mean_cbit_bias", self.mean_cbit_bias)
        require_signed_unit("selector_calibration_profile_mean_cost_bias", self.mean_cost_bias)
        if self.mean_residual_risk_error is not None:
            require_signed_unit(
                "selector_calibration_profile_mean_residual_risk_error",
                self.mean_residual_risk_error,
            )
        if self.mechanical_state not in SELECTOR_CALIBRATION_STATES:
            raise ValueError("selector_calibration_profile_state_invalid")
        require_calibration_hash("selector_calibration_profile_threshold_hash", self.threshold_hash)
        require_calibration_hash("selector_calibration_profile_hash", self.profile_hash)
        if self.profile_hash != hash_payload(self._committed_dict()):
            raise ValueError("selector_calibration_profile_hash_mismatch")

    @property
    def evidence_ref(self) -> str:
        return f"calibration://selector-profile/{self.profile_hash}"

    @classmethod
    def create(cls, **values: Any) -> "SelectorCalibrationProfile":
        committed = {
            **values,
            "observation_hashes": list(values["observation_hashes"]),
            "source_result_hashes": list(values["source_result_hashes"]),
        }
        return cls(**values, profile_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            key: (list(value) if key in {"observation_hashes", "source_result_hashes"} else value)
            for key, value in self.__dict__.items()
            if key != "profile_hash"
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "profile_hash": self.profile_hash, "evidence_ref": self.evidence_ref}


@dataclass(frozen=True)
class SelectorCalibrationProviderJudgment:
    profile_hash: str
    diagnostic_state: str
    drift_drivers: tuple[str, ...]
    recommended_action: str
    uncertainty: float
    rationale: str
    evidence_refs: tuple[str, ...]
    provider_invocation_receipt: dict[str, Any]
    provider_audit: dict[str, Any]
    judgment_hash: str

    def __post_init__(self) -> None:
        require_calibration_hash("selector_calibration_judgment_profile_hash", self.profile_hash)
        if self.diagnostic_state not in SELECTOR_DIAGNOSTIC_STATES:
            raise ValueError("selector_calibration_diagnostic_state_invalid")
        if len(self.drift_drivers) != len(set(self.drift_drivers)) or not set(
            self.drift_drivers
        ).issubset(SELECTOR_DRIFT_DRIVERS):
            raise ValueError("selector_calibration_drift_drivers_invalid")
        if self.diagnostic_state in {"POSSIBLE_SEMANTIC_DRIFT", "MATERIAL_SEMANTIC_DRIFT"} and not self.drift_drivers:
            raise ValueError("selector_calibration_drift_driver_required")
        if self.recommended_action not in SELECTOR_CALIBRATION_ACTIONS:
            raise ValueError("selector_calibration_recommended_action_invalid")
        valid_actions = {
            "INSUFFICIENT_HISTORY": {"COLLECT_MORE"},
            "NO_SEMANTIC_DRIFT": {"KEEP_CURRENT_CALIBRATION"},
            "POSSIBLE_SEMANTIC_DRIFT": {"REASSESS_CONTEXT_POLICY"},
            "MATERIAL_SEMANTIC_DRIFT": {
                "REASSESS_CONTEXT_POLICY",
                "SUSPEND_PREDICTION_TRUST",
            },
        }
        if self.recommended_action not in valid_actions[self.diagnostic_state]:
            raise ValueError("selector_calibration_diagnostic_action_mismatch")
        require_unit("selector_calibration_judgment_uncertainty", self.uncertainty)
        require_text("selector_calibration_judgment_rationale", self.rationale)
        require_refs("selector_calibration_judgment_evidence_refs", self.evidence_refs)
        require_calibration_hash("selector_calibration_judgment_hash", self.judgment_hash)
        if self.judgment_hash != hash_payload(self._committed_dict()):
            raise ValueError("selector_calibration_judgment_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "SelectorCalibrationProviderJudgment":
        committed = {
            **values,
            "drift_drivers": list(values["drift_drivers"]),
            "evidence_refs": list(values["evidence_refs"]),
        }
        return cls(**values, judgment_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "profile_hash": self.profile_hash,
            "diagnostic_state": self.diagnostic_state,
            "drift_drivers": list(self.drift_drivers),
            "recommended_action": self.recommended_action,
            "uncertainty": self.uncertainty,
            "rationale": self.rationale,
            "evidence_refs": list(self.evidence_refs),
            "provider_invocation_receipt": self.provider_invocation_receipt,
            "provider_audit": self.provider_audit,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "judgment_hash": self.judgment_hash}


@dataclass(frozen=True)
class SelectorCalibrationDecision:
    decision_id: str
    final_state: str
    prediction_trusted: bool
    recalibration_required: bool
    action: str
    reason: str
    kernel_authorization_ref: str
    profile_hash: str
    provider_judgment_hash: str
    threshold_hash: str
    decision_hash: str

    def __post_init__(self) -> None:
        require_text("selector_calibration_decision_id", self.decision_id)
        if self.final_state not in SELECTOR_CALIBRATION_STATES:
            raise ValueError("selector_calibration_decision_state_invalid")
        if self.action not in SELECTOR_CALIBRATION_ACTIONS:
            raise ValueError("selector_calibration_decision_action_invalid")
        require_text("selector_calibration_decision_reason", self.reason)
        if not self.kernel_authorization_ref.startswith("kernel://"):
            raise ValueError("selector_calibration_kernel_authorization_required")
        if self.prediction_trusted != (self.final_state == "CALIBRATED"):
            raise ValueError("selector_calibration_prediction_trust_invalid")
        if self.recalibration_required != (self.final_state in {"WATCH", "DRIFTED"}):
            raise ValueError("selector_calibration_recalibration_state_invalid")
        for name in ("profile_hash", "provider_judgment_hash", "threshold_hash", "decision_hash"):
            require_calibration_hash(f"selector_calibration_decision_{name}", getattr(self, name))
        if self.decision_hash != hash_payload(self._committed_dict()):
            raise ValueError("selector_calibration_decision_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "SelectorCalibrationDecision":
        return cls(**values, decision_hash=hash_payload(values))

    def _committed_dict(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if key != "decision_hash"}

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._committed_dict(),
            "decision_hash": self.decision_hash,
            "global_policy_authority": False,
            "production_activation": False,
        }


@dataclass(frozen=True)
class SelectorCalibrationReceipt:
    calibration_id: str
    runtime_id: str
    observation: SelectorCalibrationObservation
    profile: SelectorCalibrationProfile
    provider_judgment: SelectorCalibrationProviderJudgment
    kernel_decision: SelectorCalibrationDecision
    supersedes_receipt_hash: str
    created_at: str
    receipt_hash: str
    candidate_state: str = "SELECTOR_CALIBRATION_PROJECT_SCOPED"

    def __post_init__(self) -> None:
        for name in ("calibration_id", "runtime_id", "created_at"):
            require_text(f"selector_calibration_receipt_{name}", getattr(self, name))
        if self.candidate_state != "SELECTOR_CALIBRATION_PROJECT_SCOPED":
            raise ValueError("selector_calibration_receipt_candidate_state_invalid")
        if self.observation.observation_hash not in self.profile.observation_hashes:
            raise ValueError("selector_calibration_receipt_observation_profile_mismatch")
        if self.provider_judgment.profile_hash != self.profile.profile_hash:
            raise ValueError("selector_calibration_receipt_provider_profile_mismatch")
        if (
            self.kernel_decision.profile_hash != self.profile.profile_hash
            or self.kernel_decision.provider_judgment_hash != self.provider_judgment.judgment_hash
            or self.kernel_decision.threshold_hash != self.profile.threshold_hash
        ):
            raise ValueError("selector_calibration_receipt_decision_binding_invalid")
        require_calibration_hash(
            "selector_calibration_receipt_supersedes_hash",
            self.supersedes_receipt_hash,
            allow_empty=True,
        )
        require_calibration_hash("selector_calibration_receipt_hash", self.receipt_hash)
        if self.receipt_hash != hash_payload(self._committed_dict()):
            raise ValueError("selector_calibration_receipt_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "SelectorCalibrationReceipt":
        committed = {
            **values,
            "observation": values["observation"].as_dict(),
            "profile": values["profile"].as_dict(),
            "provider_judgment": values["provider_judgment"].as_dict(),
            "kernel_decision": values["kernel_decision"].as_dict(),
            "candidate_state": "SELECTOR_CALIBRATION_PROJECT_SCOPED",
        }
        return cls(**values, receipt_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "calibration_id": self.calibration_id,
            "runtime_id": self.runtime_id,
            "observation": self.observation.as_dict(),
            "profile": self.profile.as_dict(),
            "provider_judgment": self.provider_judgment.as_dict(),
            "kernel_decision": self.kernel_decision.as_dict(),
            "supersedes_receipt_hash": self.supersedes_receipt_hash,
            "created_at": self.created_at,
            "candidate_state": self.candidate_state,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._committed_dict(),
            "receipt_hash": self.receipt_hash,
            "global_policy_authority": False,
            "production_activation": False,
        }
