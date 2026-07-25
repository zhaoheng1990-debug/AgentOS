"""Freeze, replay, and score v0.72 coordinate projection."""

import argparse
import json
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.benchmark_bridge_metrics import score_arm  # noqa: E402
from local_collective_cognition.coordinate_projection_protocol import build_preregistration, validate_preregistration  # noqa: E402
from local_collective_cognition.coordinate_projection_replay import build_projection_replay  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("freeze", "replay", "score"))
    stage = parser.parse_args().stage
    source = ROOT / "outputs" / "surface_binding_v0_71"
    output = ROOT / "outputs" / "coordinate_projection_v0_72"
    output.mkdir(parents=True, exist_ok=True)
    panel = read(source / "calibration_private.json")
    if stage == "freeze":
        holdout = read(source / "holdout_private.json")
        prereg = build_preregistration(
            panel=panel,
            holdout=holdout,
            source_run=read(source / "calibration_candidate_run.json"),
        )
        write(output / "calibration_preregistration.json", prereg)
        print(json.dumps({"preregistration_hash": prereg["artifact_hash"], "holdout_hash": holdout["artifact_hash"], "provider_calls": 0}, indent=2))
        return
    prereg = read(output / "calibration_preregistration.json")
    validate_preregistration(prereg)
    if stage == "replay":
        run = build_projection_replay(
            panel=panel,
            preregistration=prereg,
            source_run=read(source / "calibration_candidate_run.json"),
        )
        write(output / "calibration_replay_run.json", run)
        print(json.dumps({"receipts": len(run["receipts"]), "projection_changes": sum(len(v["changes"]) for v in run["projection_receipts"].values()), "provider_calls_added": run["provider_calls_added"]}, indent=2))
        return
    run = read(output / "calibration_replay_run.json")
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
        "label_accuracy": candidate["label_accuracy"] >= gate["label_accuracy_min"],
        "effective_cbit": candidate["effective_cbit"] > baseline["effective_cbit"],
        "no_harms": len(harmed) <= gate["harms_max"],
        "required_labels": all(labels.get(k) == v for k, v in gate["required_labels"].items()),
        "zero_added_provider_calls": run["provider_calls_added"] <= prereg["provider_calls_added_max"],
    }
    passed = all(conditions.values())
    value = {"score_version": "coordinate_projection_score_v0_72", "baseline": baseline, "candidate": candidate, "corrected_case_ids": corrected, "harmed_case_ids": harmed, "conditions": conditions, "decision": "PASS_COORDINATE_PROJECTION_CALIBRATION" if passed else "REJECT_COORDINATE_PROJECTION_CALIBRATION", "prospective_holdout_reexecution_required": passed, "fresh_holdout_authorized": False}
    write(output / "calibration_score.json", {**value, "artifact_hash": hash_payload(value)})
    print(json.dumps({"baseline": {k: baseline[k] for k in ("label_accuracy", "effective_cbit")}, "candidate": {k: candidate[k] for k in ("valid_receipt_count", "label_accuracy", "evidence_f1", "effective_cbit")}, "corrected": corrected, "harmed": harmed, "conditions": conditions, "decision": value["decision"], "fresh_holdout_authorized": False}, indent=2))


if __name__ == "__main__":
    main()
