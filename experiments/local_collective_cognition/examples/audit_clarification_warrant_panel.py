"""Recalibrate the frozen v0.10 candidate against the model-panel reference."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_warrant_panel_calibration import build_warrant_panel_recalibration, validate_warrant_panel_recalibration
from local_collective_cognition.post_experiment_analysis import build_warrant_panel_recalibration_analysis, render_analysis_markdown


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def load(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/clarification_warrant_v0_10"
    parser.add_argument("--corpus", default=f"{base}/private_warrant_corpus.json")
    parser.add_argument("--run", default=f"{base}/candidate_run.json")
    parser.add_argument("--frozen-calibration", default=f"{base}/calibration.json")
    parser.add_argument("--panel-reference", default=f"{base}/warrant_model_panel_reference_candidate.json")
    parser.add_argument("--output", default=f"{base}/panel_recalibration.json")
    parser.add_argument("--analysis-json", default=f"{base}/panel_recalibration_analysis.json")
    parser.add_argument("--analysis-md", default=f"{base}/PANEL_RECALIBRATION_ANALYSIS.md")
    args = parser.parse_args()
    inputs = {"corpus_artifact": load(args.corpus), "candidate_run": load(args.run), "frozen_calibration": load(args.frozen_calibration), "panel_reference": load(args.panel_reference)}
    audit = build_warrant_panel_recalibration(**inputs)
    validate_warrant_panel_recalibration(audit, **inputs)
    analysis = build_warrant_panel_recalibration_analysis(audit)
    resolve(args.output).write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    resolve(args.analysis_json).write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    resolve(args.analysis_md).write_text(render_analysis_markdown(analysis), encoding="utf-8")
    print(json.dumps({"artifact_hash": audit["artifact_hash"], "analysis_hash": analysis["artifact_hash"], "candidate_state": audit["candidate_state"], "transfer_recommendation": audit["transfer_recommendation"], "metrics": audit["metrics"], "error_counts": {key: len(value) for key, value in audit["error_clusters"].items()}}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
