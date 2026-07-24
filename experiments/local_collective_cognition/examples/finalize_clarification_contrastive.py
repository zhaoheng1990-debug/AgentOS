"""Score v0.8 and emit the separate post-experiment analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_contrastive_calibration import build_contrastive_calibration, validate_contrastive_calibration
from local_collective_cognition.post_experiment_analysis import build_contrastive_analysis, render_analysis_markdown


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def load(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/clarification_contrastive_v0_8"
    parser.add_argument("--corpus", default=f"{base}/private_contrastive_corpus.json")
    parser.add_argument("--run", default=f"{base}/candidate_run.json")
    parser.add_argument("--calibration", default=f"{base}/calibration.json")
    parser.add_argument("--analysis-json", default=f"{base}/result_analysis.json")
    parser.add_argument("--analysis-md", default=f"{base}/RESULT_ANALYSIS.md")
    args = parser.parse_args()
    corpus, run = load(args.corpus), load(args.run)
    calibration = build_contrastive_calibration(corpus_artifact=corpus, candidate_run=run)
    validate_contrastive_calibration(calibration, corpus_artifact=corpus, candidate_run=run)
    analysis = build_contrastive_analysis(calibration, candidate_run=run, corpus_artifact=corpus)
    resolve(args.calibration).write_text(json.dumps(calibration, indent=2, sort_keys=True), encoding="utf-8")
    resolve(args.analysis_json).write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    resolve(args.analysis_md).write_text(render_analysis_markdown(analysis), encoding="utf-8")
    print(json.dumps({
        "artifact_hash": calibration["artifact_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "candidate_state": calibration["candidate_state"],
        "arm_metrics": calibration["arm_metrics"],
        "gain": calibration["accuracy_gain_over_category_fingerprint"],
        "gate_results": calibration["gate_results"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
