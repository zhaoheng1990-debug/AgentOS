"""Freeze, run, and score the v0.87 SciFact semantic-warrant screen."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.factorized_benchmarks.scifact_v0_87_evaluation import (  # noqa: E402
    evaluate_warrant_run,
)
from local_collective_cognition.factorized_benchmarks.scifact_v0_87_holdout import (  # noqa: E402
    build_preregistration,
    freeze_holdout,
    public_holdout,
)
from local_collective_cognition.factorized_benchmarks.scifact_v0_87_provider import (  # noqa: E402
    build_deepseek_warrant_adapter,
)
from local_collective_cognition.factorized_benchmarks.scifact_v0_87_runtime import (  # noqa: E402
    run_warrant_panel,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("freeze", "run", "score"), required=True)
    parser.add_argument(
        "--archive",
        type=Path,
        default=ROOT / "outputs" / "v0_86_scifact_data.tar.gz",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "outputs" / "scifact_warrant_v0_87",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.stage == "freeze":
        panel = freeze_holdout(args.archive)
        preregistration = build_preregistration(panel)
        _write(args.output_dir / "holdout_private.json", panel)
        _write(args.output_dir / "holdout_public.json", public_holdout(panel))
        _write(args.output_dir / "preregistration.json", preregistration)
        print(json.dumps({
            "holdout_hash": panel["artifact_hash"],
            "preregistration_hash": preregistration["artifact_hash"],
            "case_count": panel["case_count"],
            "label_balance": panel["label_balance"],
            "provider_calls": 0,
        }, indent=2))
        return
    panel = _read(args.output_dir / "holdout_private.json")
    preregistration = _read(args.output_dir / "preregistration.json")
    if args.stage == "run":
        run = run_warrant_panel(
            panel=panel,
            preregistration=preregistration,
            adapter=build_deepseek_warrant_adapter(),
        )
        _write(args.output_dir / "warrant_run.json", run)
        print(json.dumps({
            "valid_receipts": len(run["receipts"]),
            "failures": len(run["failures"]),
            "tasks": len(run["task_calls"]),
        }, indent=2))
        return
    evaluation = evaluate_warrant_run(
        panel=panel,
        preregistration=preregistration,
        run=_read(args.output_dir / "warrant_run.json"),
    )
    _write(args.output_dir / "evaluation.json", evaluation)
    print(json.dumps({
        key: evaluation[key] for key in (
            "case_count",
            "valid_receipt_count",
            "failure_count",
            "label_accuracy",
            "macro_rationale_f1",
            "joint_success_rate",
            "harmful_compiled_candidate_count",
            "abstention_rate",
            "physical_attempt_count",
            "physical_total_tokens",
            "gate_conditions",
            "development_decision",
            "external_acceptance_eligible",
        )
    }, indent=2))


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
