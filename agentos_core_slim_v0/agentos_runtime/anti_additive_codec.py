"""Pure reconstruction helpers for persisted Anti-Additive receipts."""

from __future__ import annotations

from typing import Any

from agentos_kernel import (
    AntiAdditiveCalibrationControl,
    AntiAdditiveChangeCandidate,
    AntiAdditiveMethodologyDecision,
    AntiAdditiveMethodologyReceipt,
    AntiAdditiveProviderJudgment,
    AntiAdditiveTriggerAssessment,
)


def anti_additive_receipt_from_dict(payload: dict[str, Any]) -> AntiAdditiveMethodologyReceipt:
    candidate_payload = payload["candidate"]
    candidate = AntiAdditiveChangeCandidate(
        **{
            **candidate_payload,
            "evidence_refs": tuple(candidate_payload["evidence_refs"]),
        }
    )
    judgment_payload = payload["provider_judgment"]
    triggers = tuple(
        AntiAdditiveTriggerAssessment(
            **{
                **item,
                "evidence_refs": tuple(item["evidence_refs"]),
            }
        )
        for item in judgment_payload["trigger_assessments"]
    )
    judgment = AntiAdditiveProviderJudgment(
        **{
            **judgment_payload,
            "trigger_assessments": triggers,
            "evidence_refs": tuple(judgment_payload["evidence_refs"]),
        }
    )
    decision_payload = payload["decision"]
    decision = AntiAdditiveMethodologyDecision(
        **{
            **decision_payload,
            "active_trigger_ids": tuple(decision_payload["active_trigger_ids"]),
            "calibration_control": AntiAdditiveCalibrationControl(
                **decision_payload["calibration_control"]
            ),
        }
    )
    return AntiAdditiveMethodologyReceipt(
        candidate=candidate,
        provider_judgment=judgment,
        decision=decision,
        created_at=payload["created_at"],
        receipt_hash=payload["receipt_hash"],
    )
