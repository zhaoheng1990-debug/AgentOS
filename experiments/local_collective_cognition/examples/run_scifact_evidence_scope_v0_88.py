"""Freeze and execute the paired v0.88 SciFact evidence-scope screen."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.factorized_benchmarks.scifact_v0_88_evaluation import (  # noqa: E402
    evaluate_paired_run,
)
from local_collective_cognition.factorized_benchmarks.scifact_v0_88_holdout import (  # noqa: E402
    build_preregistration,
    freeze_holdout,
    public_holdout,
)
from local_collective_cognition.factorized_benchmarks.scifact_v0_88_provider import (  # noqa: E402
    build_deepseek_v0_88_adapter,
)
from local_collective_cognition.factorized_benchmarks.scifact_v0_88_runtime import (  # noqa: E402
    run_claim_scope_panel,
    run_direct_baseline,
    run_evidence_set_panel,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=("freeze", "baseline", "evidence", "scope", "score"),
        required=True,
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=ROOT / "outputs" / "v0_86_scifact_data.tar.gz",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "outputs" / "scifact_evidence_scope_v0_88",
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
    adapter = build_deepseek_v0_88_adapter()
    if args.stage == "baseline":
        run = run_direct_baseline(
            panel=panel,
            preregistration=preregistration,
            adapter=adapter,
        )
        _write(args.output_dir / "baseline_run.json", run)
        _print_run(run)
        return
    if args.stage == "evidence":
        run = run_evidence_set_panel(
            panel=panel,
            preregistration=preregistration,
            adapter=adapter,
        )
        _write(args.output_dir / "evidence_run.json", run)
        _print_run(run)
        return
    if args.stage == "scope":
        run = run_claim_scope_panel(
            panel=panel,
            preregistration=preregistration,
            evidence_run=_read(args.output_dir / "evidence_run.json"),
            adapter=adapter,
        )
        _write(args.output_dir / "scope_run.json", run)
        _print_run(run)
        return
    evaluation = evaluate_paired_run(
        panel=panel,
        preregistration=preregistration,
        baseline_run=_read(args.output_dir / "baseline_run.json"),
        evidence_run=_read(args.output_dir / "evidence_run.json"),
        scope_run=_read(args.output_dir / "scope_run.json"),
    )
    _write(args.output_dir / "evaluation.json", evaluation)
    print(json.dumps({
        key: evaluation[key] for key in (
            "baseline",
            "candidate",
            "paired_sentence_f1_delta",
            "scope_conflict_case_count",
            "scope_conflict_abstention_compliance",
            "failure_count",
            "physical_attempt_count",
            "physical_total_tokens",
            "gate_conditions",
            "development_decision",
            "external_acceptance_eligible",
        )
    }, indent=2))


def _print_run(run: dict) -> None:
    print(json.dumps({
        "arm_id": run["arm_id"],
        "valid_receipts": len(run["receipts"]),
        "compiled_candidates": len(run["compiled_candidates"]),
        "failures": len(run["failures"]),
        "tasks": len(run["task_calls"]),
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
