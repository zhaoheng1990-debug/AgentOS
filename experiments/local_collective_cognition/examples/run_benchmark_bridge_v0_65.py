"""Run and score the frozen v0.65 benchmark bridge."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.benchmark_bridge_metrics import (  # noqa: E402
    calibration_decision,
    score_arm,
)
from local_collective_cognition.benchmark_bridge_runtime import (  # noqa: E402
    run_one_pass_panel,
    run_staged_panel,
)
from local_collective_cognition.benchmark_bridge_provider import (  # noqa: E402
    build_deepseek_adapter,
)


STAGES = ("a0", "a1", "score")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=STAGES)
    args = parser.parse_args()
    output = REPO_ROOT / "outputs" / "benchmark_bridge_v0_65"
    panel = read(output / "calibration_panel_private.json")
    preregistration = read(output / "preregistration.json")

    if args.stage == "a0":
        run = run_one_pass_panel(
            panel=panel,
            preregistration=preregistration,
            adapter=build_deepseek_adapter(),
        )
        write(output / "a0_one_pass_run.json", run)
        print(json.dumps(_run_summary(run), indent=2, sort_keys=True))
        return 0
    if args.stage == "a1":
        run = run_staged_panel(
            panel=panel,
            preregistration=preregistration,
            adapter=build_deepseek_adapter(),
        )
        write(output / "a1_staged_run.json", run)
        print(json.dumps(_run_summary(run), indent=2, sort_keys=True))
        return 0

    a0 = read(output / "a0_one_pass_run.json")
    a1 = read(output / "a1_staged_run.json")
    a0_score = score_arm(
        panel=panel, preregistration=preregistration, run=a0
    )
    a1_score = score_arm(
        panel=panel, preregistration=preregistration, run=a1
    )
    decision = calibration_decision(
        preregistration=preregistration,
        one_pass_score=a0_score,
        staged_score=a1_score,
    )
    write(output / "a0_score.json", a0_score)
    write(output / "a1_score.json", a1_score)
    write(output / "calibration_decision.json", decision)
    print(json.dumps({
        "a0": _score_summary(a0_score),
        "a1": _score_summary(a1_score),
        "decision": decision["decision"],
        "conditions": decision["conditions"],
        "external_holdout_authorized": decision[
            "external_holdout_authorized"
        ],
    }, indent=2, sort_keys=True))
    return 0


def _run_summary(run: dict) -> dict:
    return {
        "arm_id": run["arm_id"],
        "valid_receipts": len(run["receipts"]),
        "contract_failures": len(run["contract_failures"]),
        "provider_tasks": len(run["task_calls"]),
        "tokens": sum(
            call["token_usage"]["total_tokens"]
            for call in run["task_calls"]
        ),
        "private_gold_exposed": run["private_gold_exposed"],
        "core_write_allowed": run["core_write_allowed"],
    }


def _score_summary(score: dict) -> dict:
    keys = (
        "valid_receipt_count",
        "contract_failure_count",
        "cross_type_overlap_count",
        "label_accuracy",
        "object_binding_accuracy",
        "evidence_precision",
        "evidence_recall",
        "evidence_f1",
        "rationale_token_f1",
        "effective_cbit",
        "physical_total_tokens",
        "effective_cbit_per_1k_tokens",
    )
    return {key: score[key] for key in keys}


if __name__ == "__main__":
    raise SystemExit(main())
