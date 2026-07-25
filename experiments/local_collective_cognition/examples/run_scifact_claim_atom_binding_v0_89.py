"""Freeze and execute the paired SciFact binding-veto v0.89 screen."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.factorized_benchmarks.scifact_v0_89_base_runtime import (  # noqa: E402
    run_claim_scope_panel,
    run_evidence_set_panel,
)
from local_collective_cognition.factorized_benchmarks.scifact_v0_89_binding_runtime import (  # noqa: E402
    compile_binding_veto_panel,
    run_binding_challenge_panel,
    run_claim_atom_binding_panel,
)
from local_collective_cognition.factorized_benchmarks.scifact_v0_89_evaluation import (  # noqa: E402
    evaluate_binding_veto_run,
)
from local_collective_cognition.factorized_benchmarks.scifact_v0_89_holdout import (  # noqa: E402
    build_preregistration,
    freeze_holdout,
    public_holdout,
)
from local_collective_cognition.factorized_benchmarks.scifact_v0_89_provider import (  # noqa: E402
    build_deepseek_v0_89_adapter,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=(
            "freeze",
            "evidence",
            "scope",
            "binding",
            "challenge",
            "compile",
            "score",
        ),
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
        default=ROOT / "outputs" / "scifact_claim_atom_binding_v0_89",
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
    if args.stage == "compile":
        run = compile_binding_veto_panel(
            panel=panel,
            preregistration=preregistration,
            evidence_run=_read(args.output_dir / "evidence_run.json"),
            scope_run=_read(args.output_dir / "scope_run.json"),
            binding_run=_read(args.output_dir / "binding_run.json"),
            challenge_run=_read(args.output_dir / "challenge_run.json"),
        )
        _write(args.output_dir / "candidate_run.json", run)
        _print_run(run)
        return
    if args.stage == "score":
        evaluation = evaluate_binding_veto_run(
            panel=panel,
            preregistration=preregistration,
            evidence_run=_read(args.output_dir / "evidence_run.json"),
            scope_run=_read(args.output_dir / "scope_run.json"),
            binding_run=_read(args.output_dir / "binding_run.json"),
            challenge_run=_read(args.output_dir / "challenge_run.json"),
            candidate_run=_read(args.output_dir / "candidate_run.json"),
        )
        _write(args.output_dir / "evaluation.json", evaluation)
        _print_evaluation(evaluation)
        return
    adapter = build_deepseek_v0_89_adapter()
    evidence_run = (
        _read(args.output_dir / "evidence_run.json")
        if args.stage != "evidence"
        else None
    )
    if args.stage == "evidence":
        run = run_evidence_set_panel(
            panel=panel,
            preregistration=preregistration,
            adapter=adapter,
        )
        target = "evidence_run.json"
    elif args.stage == "scope":
        run = run_claim_scope_panel(
            panel=panel,
            preregistration=preregistration,
            evidence_run=evidence_run,
            adapter=adapter,
        )
        target = "scope_run.json"
    elif args.stage == "binding":
        run = run_claim_atom_binding_panel(
            panel=panel,
            preregistration=preregistration,
            evidence_run=evidence_run,
            adapter=adapter,
        )
        target = "binding_run.json"
    else:
        run = run_binding_challenge_panel(
            panel=panel,
            preregistration=preregistration,
            evidence_run=evidence_run,
            adapter=adapter,
        )
        target = "challenge_run.json"
    _write(args.output_dir / target, run)
    _print_run(run)


def _print_run(run: dict) -> None:
    print(json.dumps({
        "arm_id": run["arm_id"],
        "valid_receipts": len(run["receipts"]),
        "compiled_candidates": len(run["compiled_candidates"]),
        "failures": len(run["failures"]),
        "tasks": len(run["task_calls"]),
    }, indent=2))


def _print_evaluation(value: dict) -> None:
    print(json.dumps({
        key: value[key] for key in (
            "baseline",
            "candidate",
            "paired",
            "harmful_strong_candidate_reduction",
            "sentence_precision_delta",
            "sentence_f1_delta",
            "label_accuracy_delta",
            "failure_count",
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
