"""Rebuild v0.12 diagnostics from the frozen coordinator run without a new call."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_joint_coordinator_eval import build_joint_coordinator_analysis, build_joint_coordinator_report, render_joint_coordinator_analysis, validate_joint_coordinator_report


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/clarification_joint_coordinator_v0_12")
    args = parser.parse_args()
    output = resolve(args.output_dir)
    surface = json.loads((output / "joint_conflict_surface.json").read_text(encoding="utf-8"))
    run = json.loads((output / "coordinator_run.json").read_text(encoding="utf-8"))
    report = build_joint_coordinator_report(surface=surface, run=run)
    validate_joint_coordinator_report(report, surface=surface, run=run)
    analysis = build_joint_coordinator_analysis(report, run=run)
    (output / "coordinator_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (output / "post_experiment_analysis.json").write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    (output / "POST_EXPERIMENT_ANALYSIS.md").write_text(render_joint_coordinator_analysis(analysis), encoding="utf-8")
    print(json.dumps({"report_hash": report["artifact_hash"], "analysis_hash": analysis["artifact_hash"], "accepted_repair_count": report["accepted_repair_count"], "coherent_but_governance_invalid_count": report["coherent_but_governance_invalid_count"], "semantic_incoherence_count": report["semantic_incoherence_count"], "local_adjudication_basis_follow_count": report["local_adjudication_basis_follow_count"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
