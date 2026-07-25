"""Run the zero-Provider v0.70 discourse replay."""

import json
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.benchmark_bridge_metrics import score_arm  # noqa: E402
from local_collective_cognition.discourse_witness_replay import build_discourse_replay  # noqa: E402


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    source = ROOT / "outputs" / "relation_witness_v0_69"
    output = ROOT / "outputs" / "discourse_witness_v0_70"
    output.mkdir(parents=True, exist_ok=True)
    panel = read(source / "calibration_private.json")
    prereg = read(source / "calibration_preregistration.json")
    run = build_discourse_replay(
        panel=panel,
        source_run=read(source / "calibration_candidate_run.json"),
    )
    score = score_arm(panel=panel, preregistration=prereg, run=run)
    write(output / "replay_run.json", run)
    write(output / "replay_score.json", score)
    summary = {
        "valid_receipts": score["valid_receipt_count"],
        "failures": len(run["contract_failures"]),
        "label_accuracy": score["label_accuracy"],
        "evidence_f1": score["evidence_f1"],
        "effective_cbit": score["effective_cbit"],
        "provider_calls_added": run["provider_calls_added"],
        "failed_case_ids": [
            value["case_id"] for value in run["contract_failures"]
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
