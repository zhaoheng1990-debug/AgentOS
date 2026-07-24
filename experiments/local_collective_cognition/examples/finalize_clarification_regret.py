"""Reveal the committed formal oracle and score v0.6 actions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_regret_calibration import build_clarification_regret_calibration, validate_clarification_regret_calibration


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/clarification_regret_v0_6"
    parser.add_argument("--corpus", default=f"{base}/private_clarification_regret_corpus.json")
    parser.add_argument("--candidate-run", default=f"{base}/candidate_run.json")
    parser.add_argument("--output", default=f"{base}/calibration.json")
    args = parser.parse_args()
    corpus = json.loads(resolve(args.corpus).read_text(encoding="utf-8"))
    run = json.loads(resolve(args.candidate_run).read_text(encoding="utf-8"))
    calibration = build_clarification_regret_calibration(corpus_artifact=corpus, candidate_run=run)
    validate_clarification_regret_calibration(calibration, corpus_artifact=corpus, candidate_run=run)
    resolve(args.output).write_text(json.dumps(calibration, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"artifact_hash": calibration["artifact_hash"], "candidate_state": calibration["candidate_state"], "arm_metrics": calibration["arm_metrics"], "single_regret_gate_results": calibration["single_regret_gate_results"], "three_pass_regret_gate_results": calibration["three_pass_regret_gate_results"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
