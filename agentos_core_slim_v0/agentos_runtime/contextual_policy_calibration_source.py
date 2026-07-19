"""Read-only calibration source port and strong control-surface resolver."""

from __future__ import annotations

from typing import Any, Protocol

from agentos_kernel import (
    CONTEXTUAL_POLICY_IDS,
    ContextualPolicyCalibrationControl,
    SelectorCalibrationReceipt,
)
from .selector_calibration_contracts import selector_calibration_scope_key


class SelectorCalibrationControlSource(Protocol):
    def latest(
        self, *, context_key: str, evidence_tier: str, policy_id: str
    ) -> SelectorCalibrationReceipt | None: ...

    def verify_replay(self) -> dict[str, Any]: ...


def resolve_calibration_controls(
    *,
    source: SelectorCalibrationControlSource | None,
    project_scope: str,
    context_key: str,
    evidence_tier: str,
) -> tuple[ContextualPolicyCalibrationControl, ...]:
    if source is None:
        return tuple(
            ContextualPolicyCalibrationControl.unmonitored(
                project_scope=project_scope,
                context_key=context_key,
                evidence_tier=evidence_tier,
                policy_id=policy_id,
            )
            for policy_id in CONTEXTUAL_POLICY_IDS
        )
    replay = source.verify_replay()
    if replay.get("valid") is not True:
        raise ValueError("contextual_policy_calibration_source_replay_invalid")
    latest_hashes = replay.get("latest_receipt_hashes")
    if not isinstance(latest_hashes, dict):
        raise ValueError("contextual_policy_calibration_source_latest_map_missing")
    controls = []
    for policy_id in CONTEXTUAL_POLICY_IDS:
        receipt = source.latest(
            context_key=context_key,
            evidence_tier=evidence_tier,
            policy_id=policy_id,
        )
        scope_key = selector_calibration_scope_key(
            context_key=context_key,
            evidence_tier=evidence_tier,
            policy_id=policy_id,
        )
        expected_hash = latest_hashes.get(scope_key)
        if receipt is None:
            if expected_hash is not None:
                raise ValueError("contextual_policy_calibration_source_latest_receipt_missing")
            controls.append(
                ContextualPolicyCalibrationControl.no_observation(
                    project_scope=project_scope,
                    context_key=context_key,
                    evidence_tier=evidence_tier,
                    policy_id=policy_id,
                )
            )
            continue
        if expected_hash != receipt.receipt_hash:
            raise ValueError("contextual_policy_calibration_source_latest_receipt_mismatch")
        _validate_receipt(
            receipt,
            project_scope=project_scope,
            context_key=context_key,
            evidence_tier=evidence_tier,
            policy_id=policy_id,
        )
        controls.append(ContextualPolicyCalibrationControl.from_receipt(receipt))
    return tuple(controls)


def _validate_receipt(
    receipt: SelectorCalibrationReceipt,
    *,
    project_scope: str,
    context_key: str,
    evidence_tier: str,
    policy_id: str,
) -> None:
    observation = receipt.observation
    profile = receipt.profile
    decision = receipt.kernel_decision
    if receipt.candidate_state != "SELECTOR_CALIBRATION_PROJECT_SCOPED":
        raise ValueError("contextual_policy_calibration_candidate_state_invalid")
    if (
        observation.project_scope != project_scope
        or observation.context_key != context_key
        or observation.evidence_tier != evidence_tier
        or observation.policy_id != policy_id
    ):
        raise ValueError("contextual_policy_calibration_receipt_scope_mismatch")
    if (
        profile.project_scope != project_scope
        or profile.context_key != context_key
        or profile.evidence_tier != evidence_tier
        or profile.policy_id != policy_id
    ):
        raise ValueError("contextual_policy_calibration_profile_scope_mismatch")
    if (
        decision.profile_hash != profile.profile_hash
        or receipt.provider_judgment.profile_hash != profile.profile_hash
        or decision.provider_judgment_hash != receipt.provider_judgment.judgment_hash
    ):
        raise ValueError("contextual_policy_calibration_internal_binding_invalid")
    allowed_final_states = {
        "INSUFFICIENT_HISTORY": {"INSUFFICIENT_HISTORY"},
        "CALIBRATED": {"CALIBRATED", "WATCH"},
        "WATCH": {"WATCH"},
        "DRIFTED": {"DRIFTED"},
    }[profile.mechanical_state]
    if decision.final_state not in allowed_final_states:
        raise ValueError("contextual_policy_calibration_state_transition_invalid")
    if decision.final_state != "INSUFFICIENT_HISTORY" and (
        profile.observation_count < 2 or profile.independent_source_count < 2
    ):
        raise ValueError("contextual_policy_calibration_independent_history_insufficient")
