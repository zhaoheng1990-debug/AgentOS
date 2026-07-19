"""Read-only calibration source and strong control resolver."""

from __future__ import annotations

from typing import Protocol

from agentos_kernel import (
    AntiAdditiveCalibrationControl,
    AntiAdditiveCalibrationReceipt,
    AntiAdditiveChangeCandidate,
)

from .anti_additive_calibration_repository import anti_additive_calibration_scope_key


class AntiAdditiveCalibrationSource(Protocol):
    def latest_calibration_receipt(
        self, *, project_scope: str, change_kind: str, target_type: str
    ) -> AntiAdditiveCalibrationReceipt | None: ...

    def verify_replay(self) -> dict[str, object]: ...


def resolve_anti_additive_calibration_control(
    *, source: AntiAdditiveCalibrationSource | None, candidate: AntiAdditiveChangeCandidate
) -> AntiAdditiveCalibrationControl:
    if source is None:
        return AntiAdditiveCalibrationControl.unmonitored(
            project_scope=candidate.project_scope,
            change_kind=candidate.change_kind,
            target_type=candidate.target_type,
        )
    replay = source.verify_replay()
    if not replay.get("valid"):
        raise ValueError("anti_additive_calibration_source_replay_invalid")
    receipt = source.latest_calibration_receipt(
        project_scope=candidate.project_scope,
        change_kind=candidate.change_kind,
        target_type=candidate.target_type,
    )
    if receipt is None:
        return AntiAdditiveCalibrationControl.no_observation(
            project_scope=candidate.project_scope,
            change_kind=candidate.change_kind,
            target_type=candidate.target_type,
        )
    key = anti_additive_calibration_scope_key(
        candidate.project_scope, candidate.change_kind, candidate.target_type
    )
    if replay.get("latest_receipt_hashes", {}).get(key) != receipt.receipt_hash:
        raise ValueError("anti_additive_calibration_source_receipt_not_latest")
    if receipt.decision.profile_hash != receipt.profile.profile_hash:
        raise ValueError("anti_additive_calibration_source_profile_binding_invalid")
    state = receipt.decision.state
    mode = {
        "INSUFFICIENT_HISTORY": "EXPLORATION_ONLY",
        "CALIBRATED": "TRUSTED",
        "WATCH": "EXPLORATION_ONLY",
        "DRIFTED": "BLOCKED",
    }[state]
    return AntiAdditiveCalibrationControl.create(
        project_scope=candidate.project_scope,
        change_kind=candidate.change_kind,
        target_type=candidate.target_type,
        source_configured=True,
        calibration_state=state,
        control_mode=mode,
        calibration_receipt_hash=receipt.receipt_hash,
        profile_hash=receipt.profile.profile_hash,
        decision_hash=receipt.decision.decision_hash,
        observation_count=receipt.profile.observation_count,
        independent_source_count=receipt.profile.independent_source_count,
        reason=f"anti_additive_calibration_control_{state.lower()}",
    )
