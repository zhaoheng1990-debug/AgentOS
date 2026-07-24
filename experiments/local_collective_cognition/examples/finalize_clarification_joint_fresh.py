"""Rebuild v0.13 diagnostics from the frozen run without Provider calls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_joint_fresh_eval import build_joint_fresh_analysis, build_joint_fresh_report, render_joint_fresh_analysis, validate_joint_fresh_report


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output-dir", default="outputs/clarification_joint_fresh_v0_13"); args = parser.parse_args()
    output = resolve(args.output_dir)
    corpus = json.loads((output / "private_joint_corpus.json").read_text(encoding="utf-8"))
    run = json.loads((output / "candidate_run.json").read_text(encoding="utf-8"))
    report = build_joint_fresh_report(corpus_artifact=corpus, run=run); validate_joint_fresh_report(report, corpus_artifact=corpus, run=run)
    analysis = build_joint_fresh_analysis(report)
    (output / "construction_pre_panel_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (output / "pre_panel_analysis.json").write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    (output / "PRE_PANEL_ANALYSIS.md").write_text(render_joint_fresh_analysis(analysis), encoding="utf-8")
    print(json.dumps({"report_hash": report["artifact_hash"], "analysis_hash": analysis["artifact_hash"], "candidate_metrics": report["candidate_metrics"], "diagnostics_passed": report["construction_diagnostic_all_passed"]}, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
