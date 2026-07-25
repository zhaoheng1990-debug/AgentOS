"""Freeze, execute, and score the one-shot v0.75 fresh holdout."""

import argparse
import json
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.benchmark_bridge_metrics import score_arm  # noqa: E402
from local_collective_cognition.benchmark_bridge_provider import build_deepseek_adapter  # noqa: E402
from local_collective_cognition.benchmark_bridge_runtime import run_staged_panel  # noqa: E402
from local_collective_cognition.fresh_holdout_metrics import (  # noqa: E402
    build_candidate_cost_view,
    paired_outcome_summary,
)
from local_collective_cognition.fresh_holdout_protocol import (  # noqa: E402
    build_preregistration,
    validate_preregistration,
)
from local_collective_cognition.grouped_alias_surface_runtime import (  # noqa: E402
    run_grouped_alias_surface_panel,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.selection_retention_fresh_provider_helpers import (  # noqa: E402
    physical_attempts,
    token_count,
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        required=True,
        choices=("freeze", "baseline", "candidate", "score"),
    )
    stage = parser.parse_args().stage
    source = ROOT / "outputs" / "grouped_alias_surface_v0_74"
    output = ROOT / "outputs" / "fresh_holdout_v0_75"
    output.mkdir(parents=True, exist_ok=True)

    if stage == "freeze":
        panel = read(source / "holdout_private.json")
        calibration_preregistration = read(
            source / "calibration_preregistration.json"
        )
        calibration_decision = read(
            source / "calibration_decision.json"
        )
        preregistration = build_preregistration(
            panel=panel,
            calibration_preregistration=calibration_preregistration,
            calibration_decision=calibration_decision,
        )
        write(output / "holdout_private.json", panel)
        write(
            output / "holdout_public.json",
            read(source / "holdout_public.json"),
        )
        write(output / "holdout_preregistration.json", preregistration)
        print(json.dumps({
            "preregistration_hash": preregistration["artifact_hash"],
            "holdout_hash": panel["artifact_hash"],
            "calibration_decision_hash": (
                calibration_decision["artifact_hash"]
            ),
            "provider_calls": 0,
        }, indent=2))
        return

    panel = read(output / "holdout_private.json")
    preregistration = read(output / "holdout_preregistration.json")
    validate_preregistration(preregistration)
    if stage == "baseline":
        run = run_staged_panel(
            panel=panel,
            preregistration=preregistration,
            adapter=build_deepseek_adapter(),
        )
        write(output / "baseline_run.json", run)
        print(json.dumps({
            "admission_receipts": len(run["admission_receipts"]),
            "baseline_receipts": len(run["receipts"]),
            "contract_failures": len(run["contract_failures"]),
            "tasks": len(run["task_calls"]),
            "physical_attempts": physical_attempts(run["task_calls"]),
            "tokens": token_count(run["task_calls"]),
        }, indent=2))
        return

    baseline_run = read(output / "baseline_run.json")
    if stage == "candidate":
        case_ids = {
            item["case_id"]
            for item in panel["public_surface"]["items"]
        }
        if set(baseline_run["admission_receipts"]) != case_ids:
            raise ValueError("fresh_holdout_admission_coverage_incomplete")
        run = run_grouped_alias_surface_panel(
            panel=panel,
            preregistration=preregistration,
            admission_receipts=baseline_run["admission_receipts"],
            adapter=build_deepseek_adapter(),
        )
        write(output / "candidate_run.json", run)
        print(json.dumps({
            "candidate_receipts": len(run["receipts"]),
            "contract_failures": len(run["contract_failures"]),
            "compiler_failures": len(run["compiler_failures"]),
            "tasks": len(run["task_calls"]),
            "physical_attempts": physical_attempts(run["task_calls"]),
            "tokens": token_count(run["task_calls"]),
            "grouped_catalogs": sum(
                any(
                    arm["group_split_applied"]
                    for arm in value["arms"]
                )
                for value in run[
                    "frame_validation_metadata"
                ].values()
            ),
        }, indent=2))
        return

    candidate_run = read(output / "candidate_run.json")
    candidate_cost_view = build_candidate_cost_view(
        baseline_run=baseline_run,
        candidate_run=candidate_run,
    )
    baseline_score = score_arm(
        panel=panel,
        preregistration=preregistration,
        run=baseline_run,
    )
    candidate_score = score_arm(
        panel=panel,
        preregistration=preregistration,
        run=candidate_cost_view,
    )
    comparison = paired_outcome_summary(
        baseline_score=baseline_score,
        candidate_score=candidate_score,
    )
    total_calls = [
        *baseline_run["task_calls"],
        *candidate_run["task_calls"],
    ]
    cost = {
        "cost_version": "fresh_holdout_cost_v0_75",
        "baseline_tasks": len(baseline_run["task_calls"]),
        "candidate_incremental_tasks": len(
            candidate_run["task_calls"]
        ),
        "candidate_path_tasks": len(
            candidate_cost_view["task_calls"]
        ),
        "total_experiment_tasks": len(total_calls),
        "total_physical_attempts": physical_attempts(total_calls),
        "total_physical_tokens": token_count(total_calls),
    }
    cost = {**cost, "artifact_hash": hash_payload(cost)}
    gate = preregistration["primary_gate"]
    candidate_failure_count = (
        len(candidate_run["contract_failures"])
        + len(candidate_run["compiler_failures"])
    )
    conditions = {
        "admission_coverage": (
            len(baseline_run["admission_receipts"])
            >= gate["admission_receipts_min"]
        ),
        "candidate_valid_receipts": (
            candidate_score["valid_receipt_count"]
            >= gate["candidate_valid_receipts_min"]
        ),
        "candidate_failures": (
            candidate_failure_count
            <= gate["candidate_failures_max"]
        ),
        "label_accuracy": (
            candidate_score["label_accuracy"]
            >= baseline_score["label_accuracy"]
        ),
        "evidence_f1": (
            candidate_score["evidence_f1"]
            >= baseline_score["evidence_f1"]
        ),
        "rationale_token_f1": (
            candidate_score["rationale_token_f1"]
            >= baseline_score["rationale_token_f1"]
        ),
        "effective_cbit": (
            candidate_score["effective_cbit"]
            > baseline_score["effective_cbit"]
        ),
        "net_label_corrections": (
            comparison["net_label_corrections"]
            >= gate["net_label_corrections_min"]
        ),
        "baseline_task_budget": (
            cost["baseline_tasks"]
            <= preregistration["maximum_baseline_tasks"]
        ),
        "candidate_incremental_task_budget": (
            cost["candidate_incremental_tasks"]
            <= preregistration["maximum_candidate_incremental_tasks"]
        ),
        "candidate_path_task_budget": (
            cost["candidate_path_tasks"]
            <= preregistration["maximum_candidate_path_tasks"]
        ),
        "total_task_budget": (
            cost["total_experiment_tasks"]
            <= preregistration["maximum_total_experiment_tasks"]
        ),
        "attempt_budget": (
            cost["total_physical_attempts"]
            <= preregistration["maximum_total_physical_attempts"]
        ),
        "token_budget": (
            cost["total_physical_tokens"]
            <= preregistration["hard_total_token_ceiling"]
        ),
    }
    primary_passed = all(conditions.values())
    confidence_condition = (
        comparison["effective_cbit_delta_bootstrap_95"]["lower"] > 0
    )
    if primary_passed and confidence_condition:
        decision_name = "PASS_FRESH_HOLDOUT_WITH_CONFIDENCE"
    elif primary_passed:
        decision_name = "PASS_FRESH_HOLDOUT_DIRECTIONAL_ONLY"
    else:
        decision_name = "REJECT_FRESH_HOLDOUT_TRANSFER"
    decision = {
        "decision_version": "fresh_holdout_decision_v0_75",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_baseline_score_hash": baseline_score["artifact_hash"],
        "source_candidate_score_hash": candidate_score["artifact_hash"],
        "source_comparison_hash": comparison["artifact_hash"],
        "source_cost_hash": cost["artifact_hash"],
        "conditions": conditions,
        "confidence_condition": confidence_condition,
        "decision": decision_name,
        "fresh_generalization_supported": primary_passed,
        "confidence_supported": (
            primary_passed and confidence_condition
        ),
        "holdout_reexecution_allowed": False,
        "holdout_driven_mechanism_change_allowed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    decision = {
        **decision,
        "artifact_hash": hash_payload(decision),
    }
    write(output / "candidate_cost_view.json", candidate_cost_view)
    write(output / "baseline_score.json", baseline_score)
    write(output / "candidate_score.json", candidate_score)
    write(output / "paired_comparison.json", comparison)
    write(output / "cost_accounting.json", cost)
    write(output / "holdout_decision.json", decision)
    print(json.dumps({
        "baseline": _score_summary(baseline_score),
        "candidate": _score_summary(candidate_score),
        "corrected": comparison["corrected_case_ids"],
        "harmed": comparison["harmed_case_ids"],
        "paired": {
            "label_accuracy_delta": comparison[
                "label_accuracy_delta"
            ],
            "effective_cbit_delta": comparison[
                "effective_cbit_delta"
            ],
            "effective_cbit_delta_bootstrap_95": comparison[
                "effective_cbit_delta_bootstrap_95"
            ],
            "label_discordance_exact_p": comparison[
                "label_discordance_exact_p"
            ],
        },
        "cost": cost,
        "conditions": conditions,
        "confidence_condition": confidence_condition,
        "decision": decision_name,
    }, indent=2))


def _score_summary(score):
    return {
        key: score[key]
        for key in (
            "valid_receipt_count",
            "contract_failure_count",
            "label_accuracy",
            "evidence_f1",
            "rationale_token_f1",
            "effective_cbit",
            "provider_task_count",
            "physical_total_tokens",
        )
    }


if __name__ == "__main__":
    main()
