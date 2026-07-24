"""Run and score the frozen v0.68 calibration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.benchmark_bridge_provider import (  # noqa: E402
    build_deepseek_adapter,
)
from local_collective_cognition.relational_contrast_metrics import (  # noqa: E402
    calibration_decision,
    score_relational_contrast,
)
from local_collective_cognition.relational_contrast_protocol import (  # noqa: E402
    validate_relational_preregistration,
)
from local_collective_cognition.relational_contrast_runtime import (  # noqa: E402
    run_relational_contrast_panel,
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("candidate", "score"))
    args = parser.parse_args()
    output = REPO_ROOT / "outputs" / "relational_contrast_v0_68"
    panel = read(output / "calibration_private.json")
    prereg = read(output / "calibration_preregistration.json")
    validate_relational_preregistration(prereg)
    if args.stage == "candidate":
        run = run_relational_contrast_panel(
            panel=panel,
            preregistration=prereg,
            admission_receipts=panel["source_admission_receipts"],
            adapter=build_deepseek_adapter(),
        )
        write(output / "calibration_candidate_run.json", run)
        print(json.dumps(_run_summary(run), indent=2, sort_keys=True))
        return 0
    run = read(output / "calibration_candidate_run.json")
    score = score_relational_contrast(
        panel=panel,
        preregistration=prereg,
        baseline_run=panel["baseline_projection"],
        candidate_run=run,
    )
    decision = calibration_decision(preregistration=prereg, score=score)
    write(output / "calibration_score.json", score)
    write(output / "calibration_decision.json", decision)
    print(json.dumps({
        "baseline": _score(score["baseline"]),
        "candidate": _score(score["candidate"]),
        "corrected_case_ids": score["corrected_case_ids"],
        "harmed_case_ids": score["harmed_case_ids"],
        "unresolved_case_ids": score["unresolved_case_ids"],
        "conditions": decision["conditions"],
        "decision": decision["decision"],
        "fresh_holdout_authorized": decision["fresh_holdout_authorized"],
    }, indent=2, sort_keys=True))
    return 0


def _run_summary(run: dict) -> dict:
    return {
        "frame_receipts": len(run["frame_receipts"]),
        "basis_receipts": len(run["basis_receipts"]),
        "compiled_receipts": len(run["receipts"]),
        "contract_failures": len(run["contract_failures"]),
        "compiler_failures": len(run["compiler_failures"]),
        "provider_tasks": len(run["task_calls"]),
        "tokens": sum(
            call["token_usage"]["total_tokens"]
            for call in run["task_calls"]
        ),
    }


def _score(value: dict) -> dict:
    keys = (
        "valid_receipt_count",
        "label_accuracy",
        "evidence_f1",
        "rationale_token_f1",
        "effective_cbit",
        "physical_total_tokens",
    )
    return {key: value[key] for key in keys}


if __name__ == "__main__":
    raise SystemExit(main())
