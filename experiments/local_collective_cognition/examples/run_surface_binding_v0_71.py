"""Freeze, run, and score v0.71."""

import argparse
import json
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.benchmark_bridge_metrics import score_arm  # noqa: E402
from local_collective_cognition.benchmark_bridge_provider import build_deepseek_adapter  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.surface_binding_protocol import build_preregistration, validate_preregistration  # noqa: E402
from local_collective_cognition.surface_binding_runtime import run_surface_binding_panel  # noqa: E402


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("freeze", "candidate", "score"))
    stage = parser.parse_args().stage
    source = ROOT / "outputs" / "relation_witness_v0_69"
    output = ROOT / "outputs" / "surface_binding_v0_71"
    output.mkdir(parents=True, exist_ok=True)
    if stage == "freeze":
        panel = read(source / "calibration_private.json")
        holdout = read(source / "holdout_private.json")
        frame_run = read(source / "calibration_candidate_run.json")
        prereg = build_preregistration(panel=panel, holdout=holdout, frame_run=frame_run)
        for name in ("calibration_private.json", "calibration_public.json", "holdout_private.json", "holdout_public.json"):
            write(output / name, read(source / name))
        write(output / "calibration_preregistration.json", prereg)
        print(json.dumps({"preregistration_hash": prereg["artifact_hash"], "holdout_hash": holdout["artifact_hash"], "provider_calls": 0}, indent=2))
        return
    panel = read(output / "calibration_private.json")
    prereg = read(output / "calibration_preregistration.json")
    validate_preregistration(prereg)
    if stage == "candidate":
        run = run_surface_binding_panel(
            panel=panel,
            preregistration=prereg,
            admission_receipts=panel["source_admission_receipts"],
            source_frame_run=read(source / "calibration_candidate_run.json"),
            adapter=build_deepseek_adapter(),
        )
        write(output / "calibration_candidate_run.json", run)
        print(json.dumps({"receipts": len(run["receipts"]), "failures": len(run["contract_failures"]), "tasks": len(run["task_calls"]), "catalog_mean": sum(len(v["candidates"]) for v in run["surface_catalogs"].values()) / 12}, indent=2))
        return
    run = read(output / "calibration_candidate_run.json")
    baseline = score_arm(panel=panel, preregistration=prereg, run=panel["baseline_projection"])
    candidate = score_arm(panel=panel, preregistration=prereg, run=run)
    old = {v["case_id"]: v for v in baseline["cases"]}
    new = {v["case_id"]: v for v in candidate["cases"]}
    corrected = sorted(k for k in new if not old[k]["label_correct"] and new[k]["label_correct"])
    harmed = sorted(k for k in new if old[k]["label_correct"] and not new[k]["label_correct"])
    gate = prereg["calibration_gate"]
    labels = {v["case_id"]: v["predicted_label"] for v in candidate["cases"]}
    conditions = {
        "valid_receipts": candidate["valid_receipt_count"] >= gate["valid_receipts_min"],
        "failures": len(run["contract_failures"]) <= gate["failures_max"],
        "label_accuracy": candidate["label_accuracy"] >= gate["label_accuracy_min"],
        "evidence_f1": candidate["evidence_f1"] >= baseline["evidence_f1"],
        "effective_cbit": candidate["effective_cbit"] > baseline["effective_cbit"],
        "no_harms": len(harmed) <= gate["harms_max"],
        "required_labels": all(labels.get(k) == v for k, v in gate["required_labels"].items()),
        "task_budget": candidate["provider_task_count"] <= prereg["maximum_provider_tasks"],
        "attempt_budget": candidate["physical_attempt_count"] <= prereg["maximum_physical_attempts"],
        "token_budget": candidate["physical_total_tokens"] <= prereg["hard_token_ceiling"],
    }
    value = {"score_version": "surface_binding_score_v0_71", "baseline": baseline, "candidate": candidate, "corrected_case_ids": corrected, "harmed_case_ids": harmed, "conditions": conditions, "decision": "PASS_SURFACE_BINDING_CALIBRATION" if all(conditions.values()) else "REJECT_SURFACE_BINDING_CALIBRATION", "fresh_holdout_authorized": all(conditions.values())}
    write(output / "calibration_score.json", {**value, "artifact_hash": hash_payload(value)})
    print(json.dumps({"baseline": {k: baseline[k] for k in ("label_accuracy", "effective_cbit")}, "candidate": {k: candidate[k] for k in ("valid_receipt_count", "label_accuracy", "evidence_f1", "effective_cbit", "physical_total_tokens")}, "corrected": corrected, "harmed": harmed, "conditions": conditions, "decision": value["decision"]}, indent=2))


if __name__ == "__main__":
    main()
