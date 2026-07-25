"""Freeze, run, and score typed evidence admission v0.76."""

import argparse
import json
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.admission_v2_calibration import (  # noqa: E402
    EXCLUDED_SURFACE_CALIBRATION_CASE_IDS,
    build_calibration_projection,
    public_projection,
    score_calibration,
    validate_calibration_projection,
)
from local_collective_cognition.admission_v2_protocol import (  # noqa: E402
    build_preregistration,
    validate_preregistration,
)
from local_collective_cognition.admission_v2_runtime import (  # noqa: E402
    run_typed_admission_panel,
)
from local_collective_cognition.benchmark_bridge_provider import build_deepseek_adapter  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


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
        choices=("freeze", "candidate", "score"),
    )
    stage = parser.parse_args().stage
    source = ROOT / "outputs" / "benchmark_bridge_v0_65"
    output = ROOT / "outputs" / "admission_v2_v0_76"
    output.mkdir(parents=True, exist_ok=True)

    if stage == "freeze":
        panel = build_calibration_projection(
            panels=(
                read(source / "calibration_panel_private.json"),
                read(source / "holdout_panel_private.json"),
            ),
            runs=(
                read(source / "a1_staged_run.json"),
                read(source / "holdout_a1_run.json"),
            ),
            excluded_case_ids=EXCLUDED_SURFACE_CALIBRATION_CASE_IDS,
        )
        validate_calibration_projection(panel)
        source_block = read(
            ROOT
            / "outputs"
            / "fresh_holdout_v0_75"
            / "holdout_block_decision.json"
        )
        preregistration = build_preregistration(
            panel=panel,
            source_block=source_block,
        )
        write(output / "calibration_private.json", panel)
        write(output / "calibration_public.json", public_projection(panel))
        write(
            output / "calibration_preregistration.json",
            preregistration,
        )
        print(json.dumps({
            "panel_hash": panel["artifact_hash"],
            "preregistration_hash": preregistration["artifact_hash"],
            "case_count": panel["case_count"],
            "label_balance": panel["label_balance"],
            "context_challenge_cases": sum(
                value["old_contextual_record_count"] > 0
                for value in panel["selection_metadata"].values()
            ),
            "v0_75_holdout_reused": False,
            "provider_calls": 0,
        }, indent=2))
        return

    panel = read(output / "calibration_private.json")
    preregistration = read(
        output / "calibration_preregistration.json"
    )
    validate_calibration_projection(panel)
    validate_preregistration(preregistration)
    if stage == "candidate":
        run = run_typed_admission_panel(
            panel=panel,
            preregistration=preregistration,
            adapter=build_deepseek_adapter(),
        )
        write(output / "calibration_candidate_run.json", run)
        print(json.dumps({
            "receipts": len(run["receipts"]),
            "partitions": len(run["partitions"]),
            "contract_failures": len(run["contract_failures"]),
            "compiler_failures": len(run["compiler_failures"]),
            "tasks": len(run["task_calls"]),
        }, indent=2))
        return

    run = read(output / "calibration_candidate_run.json")
    score = score_calibration(panel=panel, run=run)
    gate = preregistration["calibration_gate"]
    baseline = score["baseline"]
    candidate = score["candidate"]
    conditions = {
        "valid_receipts": (
            candidate["valid_receipt_count"]
            >= gate["valid_receipts_min"]
        ),
        "failures": candidate["failure_count"] <= gate["failures_max"],
        "complete_partitions": (
            candidate["complete_partition_count"]
            >= gate["complete_partitions_min"]
        ),
        "false_no_applicable": (
            candidate["false_no_applicable_count"]
            <= gate["false_no_applicable_max"]
        ),
        "context_retention": (
            candidate["context_span_count"]
            >= gate["context_spans_min"]
        ),
        "evidence_precision": (
            candidate["evidence_precision"]
            >= baseline["evidence_precision"]
        ),
        "evidence_recall": (
            candidate["evidence_recall"]
            >= baseline["evidence_recall"]
        ),
        "evidence_f1": (
            candidate["evidence_f1"] >= baseline["evidence_f1"]
        ),
        "no_harms": (
            len(score["harmed_case_ids"])
            <= gate["harmed_cases_max"]
        ),
        "task_budget": (
            candidate["provider_task_count"]
            <= preregistration["maximum_provider_tasks"]
        ),
        "attempt_budget": (
            candidate["physical_attempt_count"]
            <= preregistration["maximum_physical_attempts"]
        ),
        "token_budget": (
            candidate["physical_total_tokens"]
            <= preregistration["hard_token_ceiling"]
        ),
    }
    passed = all(conditions.values())
    decision = {
        "decision_version": "admission_v2_decision_v0_76",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_score_hash": score["artifact_hash"],
        "conditions": conditions,
        "decision": (
            "PASS_ADMISSION_V2_CALIBRATION"
            if passed
            else "REJECT_ADMISSION_V2_CALIBRATION"
        ),
        "new_holdout_design_authorized": passed,
        "v0_75_holdout_reexecution_allowed": False,
        "fresh_generalization_claim": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    decision = {
        **decision,
        "artifact_hash": hash_payload(decision),
    }
    write(output / "calibration_score.json", score)
    write(output / "calibration_decision.json", decision)
    print(json.dumps({
        "baseline": _summary(baseline),
        "candidate": _summary(candidate),
        "improved": score["improved_case_ids"],
        "harmed": score["harmed_case_ids"],
        "conditions": conditions,
        "decision": decision["decision"],
        "new_holdout_design_authorized": passed,
    }, indent=2))


def _summary(value):
    return {
        key: value[key]
        for key in (
            "valid_receipt_count",
            "failure_count",
            "evidence_precision",
            "evidence_recall",
            "evidence_f1",
            "context_span_count",
            "complete_partition_count",
            "false_no_applicable_count",
            "provider_task_count",
            "physical_total_tokens",
        )
    }


if __name__ == "__main__":
    main()
