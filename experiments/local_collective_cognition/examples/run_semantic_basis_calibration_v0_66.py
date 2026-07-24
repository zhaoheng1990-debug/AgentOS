"""Run the frozen v0.66 semantic-basis calibration."""

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
from local_collective_cognition.semantic_basis_metrics import (  # noqa: E402
    calibration_decision,
    score_semantic_basis,
)
from local_collective_cognition.semantic_basis_protocol import (  # noqa: E402
    validate_semantic_basis_preregistration,
)
from local_collective_cognition.semantic_basis_runtime import (  # noqa: E402
    run_semantic_basis_panel,
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("candidate", "score"))
    args = parser.parse_args()
    output = REPO_ROOT / "outputs" / "semantic_basis_v0_66"
    panel = read(output / "calibration_private.json")
    preregistration = read(output / "calibration_preregistration.json")
    validate_semantic_basis_preregistration(preregistration)
    if args.stage == "candidate":
        run = run_semantic_basis_panel(
            panel=panel,
            preregistration=preregistration,
            admission_receipts=panel["source_admission_receipts"],
            adapter=build_deepseek_adapter(),
        )
        write(output / "calibration_candidate_run.json", run)
        print(json.dumps(_run_summary(run), indent=2, sort_keys=True))
        return 0
    run = read(output / "calibration_candidate_run.json")
    score = score_semantic_basis(
        panel=panel,
        preregistration=preregistration,
        baseline_run=panel["baseline_projection"],
        candidate_run=run,
    )
    decision = calibration_decision(
        preregistration=preregistration, score=score
    )
    write(output / "calibration_score.json", score)
    write(output / "calibration_decision.json", decision)
    print(json.dumps({
        "baseline": _score_summary(score["baseline"]),
        "candidate": _score_summary(score["candidate"]),
        "corrected_case_ids": score["corrected_case_ids"],
        "harmed_case_ids": score["harmed_case_ids"],
        "unresolved_case_ids": score["unresolved_case_ids"],
        "candidate_total_failure_count": score[
            "candidate_total_failure_count"
        ],
        "conditions": decision["conditions"],
        "decision": decision["decision"],
        "fresh_holdout_authorized": decision[
            "fresh_holdout_authorized"
        ],
    }, indent=2, sort_keys=True))
    return 0


def _run_summary(run: dict) -> dict:
    return {
        "basis_receipts": len(run["basis_receipts"]),
        "synthesis_receipts": len(run["receipts"]),
        "contract_failures": len(run["contract_failures"]),
        "semantic_consistency_failures": len(
            run["semantic_consistency_failures"]
        ),
        "provider_tasks": len(run["task_calls"]),
        "tokens": sum(
            call["token_usage"]["total_tokens"]
            for call in run["task_calls"]
        ),
        "private_gold_exposed": run["private_gold_exposed"],
    }


def _score_summary(score: dict) -> dict:
    keys = (
        "valid_receipt_count",
        "contract_failure_count",
        "label_accuracy",
        "evidence_f1",
        "rationale_token_f1",
        "effective_cbit",
        "physical_total_tokens",
        "effective_cbit_per_1k_tokens",
    )
    return {key: score[key] for key in keys}


if __name__ == "__main__":
    raise SystemExit(main())
