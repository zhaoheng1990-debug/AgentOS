"""Mechanical metrics for local collective-cognition pilot runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentos_kernel import CognitionRunObservation, GroupCognitionEvalHarness

from .frozen_answer_harness import FrozenAnswerBenchmarkReceipt
from .provider_telemetry import ProviderInvocationTelemetry


PILOT_PROTOCOL_VERSION = "local_collective_cognition_pilot_protocol_v0_2"


@dataclass(frozen=True)
class PilotArmReport:
    arm_id: str
    rounds: int
    model_ids: tuple[str, ...]
    answer_vector: tuple[tuple[str, str], ...]
    harness_receipt: FrozenAnswerBenchmarkReceipt
    telemetry: tuple[ProviderInvocationTelemetry, ...]
    task_ids: tuple[str, ...]

    @property
    def total_tokens(self) -> int:
        return sum(item.input_tokens + item.output_tokens for item in self.telemetry)

    def as_dict(self) -> dict[str, Any]:
        return {
            "arm_id": self.arm_id,
            "rounds": self.rounds,
            "model_ids": list(self.model_ids),
            "answer_vector": dict(self.answer_vector),
            "correct_count": self.harness_receipt.correct_count,
            "total_count": self.harness_receipt.total_count,
            "score": self.harness_receipt.exact_accuracy,
            "observed_cbit": self.harness_receipt.observed_cbit_gain,
            "provider_calls": len(self.telemetry),
            "failed_attempts": sum(item.status == "FAILED" for item in self.telemetry),
            "input_tokens": sum(item.input_tokens for item in self.telemetry),
            "output_tokens": sum(item.output_tokens for item in self.telemetry),
            "total_tokens": self.total_tokens,
            "latency_ms": sum(item.latency_ms for item in self.telemetry),
            "task_ids": list(self.task_ids),
            "harness_receipt_hash": self.harness_receipt.receipt_hash,
        }


def build_pilot_report(
    *,
    experiment_id: str,
    solo_arms: tuple[PilotArmReport, ...],
    majority_arm: PilotArmReport,
    iterative_arm: PilotArmReport,
    baseline_arm: PilotArmReport,
    disagreement_count: int,
) -> dict[str, Any]:
    best = max(solo_arms, key=lambda item: (item.harness_receipt.exact_accuracy, -item.total_tokens))
    members = tuple(_observation(item) for item in solo_arms)
    evaluator = GroupCognitionEvalHarness()
    majority_eval = evaluator.evaluate(experiment_id + "-majority", members, _observation(majority_arm))
    iterative_eval = evaluator.evaluate(experiment_id + "-iterative", members, _observation(iterative_arm))
    quality_parity = iterative_arm.harness_receipt.exact_accuracy == baseline_arm.harness_receipt.exact_accuracy
    work_ratio = (
        round(iterative_arm.total_tokens / baseline_arm.total_tokens, 6)
        if quality_parity and baseline_arm.total_tokens
        else None
    )
    if not quality_parity:
        hypothesis_status = "NOT_ESTIMABLE_QUALITY_NOT_EQUAL"
    elif iterative_arm.total_tokens > baseline_arm.total_tokens and len(iterative_arm.telemetry) > len(baseline_arm.telemetry):
        hypothesis_status = "CONSISTENT_WITH_WORK_AMPLIFICATION_HYPOTHESIS"
    else:
        hypothesis_status = "WORK_AMPLIFICATION_NOT_OBSERVED"
    return {
        "experiment_id": experiment_id,
        "protocol": {
            "protocol_version": PILOT_PROTOCOL_VERSION,
            "benchmark": "local-reasoning-pilot-v0-1",
            "equal_per_item_provider_contract": True,
            "deterministic_decoding": True,
            "shared_independent_proposals": True,
            "provider_truth_exposure_detected": False,
            "claim_boundary": "single_workstation_pilot_not_a_scaling_law",
        },
        "solo_arms": [item.as_dict() for item in solo_arms],
        "best_small_model": best.as_dict(),
        "majority_arm": majority_arm.as_dict(),
        "iterative_arm": iterative_arm.as_dict(),
        "deepseek_32b_arm": baseline_arm.as_dict(),
        "group_evaluations": {
            "majority_vs_best_member": majority_eval.as_dict(),
            "iterative_vs_best_member": iterative_eval.as_dict(),
        },
        "comparisons": {
            "disagreement_items_after_independent_round": disagreement_count,
            "majority_score_delta_vs_best": round(majority_arm.harness_receipt.exact_accuracy - best.harness_receipt.exact_accuracy, 12),
            "iterative_score_delta_vs_best": round(iterative_arm.harness_receipt.exact_accuracy - best.harness_receipt.exact_accuracy, 12),
            "iterative_score_delta_vs_majority": round(iterative_arm.harness_receipt.exact_accuracy - majority_arm.harness_receipt.exact_accuracy, 12),
            "iterative_score_delta_vs_32b": round(iterative_arm.harness_receipt.exact_accuracy - baseline_arm.harness_receipt.exact_accuracy, 12),
            "iterative_token_ratio_vs_best": round(iterative_arm.total_tokens / best.total_tokens, 6) if best.total_tokens else None,
            "iterative_call_ratio_vs_best": round(len(iterative_arm.telemetry) / len(best.telemetry), 6),
            "iterative_token_ratio_vs_32b_at_equal_score": work_ratio,
            "hypothesis_status": hypothesis_status,
        },
    }


def _observation(arm: PilotArmReport) -> CognitionRunObservation:
    return CognitionRunObservation(
        subject_id=arm.arm_id,
        quality_score=arm.harness_receipt.exact_accuracy,
        hypotheses=tuple(f"{item_id}:{answer}" for item_id, answer in arm.answer_vector),
        errors_exposed=arm.harness_receipt.total_count,
        errors_corrected=arm.harness_receipt.correct_count,
        candidates_admitted=arm.harness_receipt.total_count,
        candidates_survived=arm.harness_receipt.correct_count,
        convergence_steps=arm.rounds,
        evidence_refs=arm.harness_receipt.evidence_refs,
    )
