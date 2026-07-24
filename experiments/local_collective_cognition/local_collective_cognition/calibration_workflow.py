"""Generate or replay the calibration evidence used by protocol v0.4."""

from __future__ import annotations

from typing import Any

from .benchmark_routing_calibration import RoutingCalibrationReceipt
from .collective_protocol import LocalCollectiveCognitionProtocol, RoleRun


def run_routing_calibration(
    *,
    base: LocalCollectiveCognitionProtocol,
    calibration_id: str,
    item_domains: dict[str, str],
    cached_runs: tuple[RoleRun, ...] = (),
) -> tuple[tuple[RoleRun, ...], tuple[Any, ...], RoutingCalibrationReceipt]:
    if cached_runs:
        runs = cached_runs
    else:
        runs = tuple(
            base.execute_role(
                role_id=f"routing-calibration-{index + 1}",
                adapter=adapter,
                task_kind="pilot_solo_answer",
                objective=base._answer_objective("Solve independently for routing calibration. Report honest confidence."),
                round_context={"role": "routing_calibration", "peer_outputs": "withheld"},
                itemwise=True,
            )
            for index, adapter in enumerate(base.small_adapters.values())
        )
    if {run.model_id for run in runs} != set(base.small_adapters):
        raise ValueError("routing_calibration_run_coverage_invalid")
    arms = tuple(
        base.score_arm(calibration_id, f"CALIBRATION_{run.model_id}", (run,), run.result, 1)
        for run in runs
    )
    candidates = tuple(
        _candidate_payload(base, run, arm)
        for run, arm in zip(runs, arms, strict=True)
    )
    receipt = base.harness.calibrate_routing(
        calibration_id=calibration_id,
        candidates=candidates,
        item_domains=item_domains,
    )
    return runs, arms, receipt


def _candidate_payload(base: LocalCollectiveCognitionProtocol, run: RoleRun, arm: Any) -> dict[str, Any]:
    answers = []
    for item in run.result["answers"]:
        item_run = base.slice_item_run(run, item["item_id"])
        answers.append({
            "item_id": item["item_id"],
            "answer": item["answer"],
            "confidence": item["confidence"],
            "had_structured_retry": any(event.status == "FAILED" for event in item_run.telemetry),
        })
    return {
        "model_id": run.model_id,
        "answers": answers,
        "source_harness_receipt_hash": arm.harness_receipt.receipt_hash,
        "provider_calls": len(arm.telemetry),
        "total_tokens": arm.total_tokens,
    }
