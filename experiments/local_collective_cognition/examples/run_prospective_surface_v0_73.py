"""Freeze, run, and score the v0.73 prospective surface runtime."""

import argparse
import json
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.benchmark_bridge_metrics import score_arm  # noqa: E402
from local_collective_cognition.benchmark_bridge_provider import build_deepseek_adapter  # noqa: E402
from local_collective_cognition.prospective_surface_protocol import (  # noqa: E402
    build_preregistration,
    validate_preregistration,
)
from local_collective_cognition.prospective_surface_runtime import (  # noqa: E402
    run_prospective_surface_panel,
)
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
    source = ROOT / "outputs" / "surface_binding_v0_71"
    output = ROOT / "outputs" / "prospective_surface_v0_73"
    output.mkdir(parents=True, exist_ok=True)

    if stage == "freeze":
        panel = read(source / "calibration_private.json")
        holdout = read(source / "holdout_private.json")
        preregistration = build_preregistration(
            panel=panel,
            holdout=holdout,
        )
        for name in (
            "calibration_private.json",
            "calibration_public.json",
            "holdout_private.json",
            "holdout_public.json",
        ):
            write(output / name, read(source / name))
        write(
            output / "calibration_preregistration.json",
            preregistration,
        )
        print(json.dumps({
            "preregistration_hash": preregistration["artifact_hash"],
            "holdout_hash": holdout["artifact_hash"],
            "provider_calls": 0,
        }, indent=2))
        return

    panel = read(output / "calibration_private.json")
    preregistration = read(
        output / "calibration_preregistration.json"
    )
    validate_preregistration(preregistration)
    if stage == "candidate":
        run = run_prospective_surface_panel(
            panel=panel,
            preregistration=preregistration,
            admission_receipts=panel["source_admission_receipts"],
            adapter=build_deepseek_adapter(),
        )
        write(output / "calibration_candidate_run.json", run)
        print(json.dumps({
            "receipts": len(run["receipts"]),
            "contract_failures": len(run["contract_failures"]),
            "compiler_failures": len(run["compiler_failures"]),
            "tasks": len(run["task_calls"]),
            "projection_changes": sum(
                len(value["changes"])
                for value in run["projection_receipts"].values()
            ),
        }, indent=2))
        return

    run = read(output / "calibration_candidate_run.json")
    baseline = score_arm(
        panel=panel,
        preregistration=preregistration,
        run=panel["baseline_projection"],
    )
    candidate = score_arm(
        panel=panel,
        preregistration=preregistration,
        run=run,
    )
    baseline_cases = {
        value["case_id"]: value for value in baseline["cases"]
    }
    candidate_cases = {
        value["case_id"]: value for value in candidate["cases"]
    }
    corrected = sorted(
        case_id
        for case_id, value in candidate_cases.items()
        if not baseline_cases[case_id]["label_correct"]
        and value["label_correct"]
    )
    harmed = sorted(
        case_id
        for case_id, value in candidate_cases.items()
        if baseline_cases[case_id]["label_correct"]
        and not value["label_correct"]
    )
    gate = preregistration["calibration_gate"]
    labels = {
        value["case_id"]: value["predicted_label"]
        for value in candidate["cases"]
    }
    total_failures = (
        len(run["contract_failures"])
        + len(run["compiler_failures"])
    )
    conditions = {
        "valid_receipts": (
            candidate["valid_receipt_count"]
            >= gate["valid_receipts_min"]
        ),
        "failures": total_failures <= gate["failures_max"],
        "label_accuracy": (
            candidate["label_accuracy"]
            >= gate["label_accuracy_min"]
        ),
        "evidence_f1": (
            candidate["evidence_f1"] >= baseline["evidence_f1"]
        ),
        "effective_cbit": (
            candidate["effective_cbit"] > baseline["effective_cbit"]
        ),
        "no_harms": len(harmed) <= gate["harms_max"],
        "required_labels": all(
            labels.get(case_id) == expected
            for case_id, expected in gate["required_labels"].items()
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
    score = {
        "score_version": "prospective_surface_score_v0_73",
        "baseline": baseline,
        "candidate": candidate,
        "corrected_case_ids": corrected,
        "harmed_case_ids": harmed,
        "total_failure_count": total_failures,
    }
    score = {**score, "artifact_hash": hash_payload(score)}
    decision = {
        "decision_version": "prospective_surface_decision_v0_73",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_score_hash": score["artifact_hash"],
        "conditions": conditions,
        "decision": (
            "PASS_PROSPECTIVE_SURFACE_CALIBRATION"
            if passed
            else "REJECT_PROSPECTIVE_SURFACE_CALIBRATION"
        ),
        "fresh_holdout_authorized": passed,
        "fresh_holdout_executed": False,
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
        "baseline": {
            key: baseline[key]
            for key in ("label_accuracy", "evidence_f1", "effective_cbit")
        },
        "candidate": {
            key: candidate[key]
            for key in (
                "valid_receipt_count",
                "label_accuracy",
                "evidence_f1",
                "effective_cbit",
                "provider_task_count",
                "physical_attempt_count",
                "physical_total_tokens",
            )
        },
        "corrected": corrected,
        "harmed": harmed,
        "conditions": conditions,
        "decision": decision["decision"],
        "fresh_holdout_authorized": passed,
        "fresh_holdout_executed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
