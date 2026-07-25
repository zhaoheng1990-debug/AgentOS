"""Freeze, run, or score v0.69."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.benchmark_bridge_provider import build_deepseek_adapter  # noqa: E402
from local_collective_cognition.relation_witness_metrics import calibration_decision, score_witness  # noqa: E402
from local_collective_cognition.relation_witness_protocol import build_preregistration, validate_preregistration  # noqa: E402
from local_collective_cognition.relation_witness_runtime import run_relation_witness_panel  # noqa: E402


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("freeze", "candidate", "score"))
    stage = parser.parse_args().stage
    source = ROOT / "outputs" / "relational_contrast_v0_68"
    output = ROOT / "outputs" / "relation_witness_v0_69"
    output.mkdir(parents=True, exist_ok=True)
    if stage == "freeze":
        for name in ("calibration_private.json", "calibration_public.json", "holdout_private.json", "holdout_public.json"):
            write(output / name, read(source / name))
        panel, holdout = read(source / "calibration_private.json"), read(source / "holdout_private.json")
        prereg = build_preregistration(panel=panel, holdout=holdout)
        write(output / "calibration_preregistration.json", prereg)
        print(json.dumps({"preregistration_hash": prereg["artifact_hash"], "holdout_hash": holdout["artifact_hash"], "provider_calls": 0}, indent=2))
        return
    panel = read(output / "calibration_private.json")
    prereg = read(output / "calibration_preregistration.json")
    validate_preregistration(prereg)
    if stage == "candidate":
        run = run_relation_witness_panel(
            panel=panel,
            preregistration=prereg,
            admission_receipts=panel["source_admission_receipts"],
            adapter=build_deepseek_adapter(),
        )
        write(output / "calibration_candidate_run.json", run)
        print(json.dumps({"frames": len(run["frame_receipts"]), "bases": len(run["basis_receipts"]), "receipts": len(run["receipts"]), "failures": len(run["contract_failures"]) + len(run["compiler_failures"]), "tasks": len(run["task_calls"])}, indent=2))
        return
    run = read(output / "calibration_candidate_run.json")
    score = score_witness(panel=panel, preregistration=prereg, baseline_run=panel["baseline_projection"], candidate_run=run)
    decision = calibration_decision(preregistration=prereg, score=score)
    write(output / "calibration_score.json", score)
    write(output / "calibration_decision.json", decision)
    print(json.dumps({"baseline": {k: score["baseline"][k] for k in ("label_accuracy", "effective_cbit")}, "candidate": {k: score["candidate"][k] for k in ("valid_receipt_count", "label_accuracy", "evidence_f1", "effective_cbit", "physical_total_tokens")}, "corrected": score["corrected_case_ids"], "harmed": score["harmed_case_ids"], "unresolved": score["unresolved_case_ids"], "conditions": decision["conditions"], "decision": decision["decision"]}, indent=2))


if __name__ == "__main__":
    main()
