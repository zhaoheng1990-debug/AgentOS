"""Build v0.11 construction-only diagnostics and analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_semantic_basis_calibration import build_semantic_basis_analysis, build_semantic_basis_calibration, render_semantic_basis_analysis, validate_semantic_basis_calibration


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/clarification_semantic_basis_v0_11"
    parser.add_argument("--corpus", default=f"{base}/private_semantic_basis_corpus.json")
    parser.add_argument("--run", default=f"{base}/candidate_run.json")
    parser.add_argument("--output-dir", default=base)
    args = parser.parse_args()
    corpus = json.loads(resolve(args.corpus).read_text(encoding="utf-8"))
    run = json.loads(resolve(args.run).read_text(encoding="utf-8"))
    calibration = build_semantic_basis_calibration(corpus_artifact=corpus, candidate_run=run)
    validate_semantic_basis_calibration(calibration, corpus_artifact=corpus, candidate_run=run)
    analysis = build_semantic_basis_analysis(calibration, candidate_run=run)
    output = resolve(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "construction_pre_panel_calibration.json").write_text(json.dumps(calibration, indent=2, sort_keys=True), encoding="utf-8")
    (output / "pre_panel_analysis.json").write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    (output / "PRE_PANEL_ANALYSIS.md").write_text(render_semantic_basis_analysis(analysis), encoding="utf-8")
    print(json.dumps({
        "calibration_hash": calibration["artifact_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "candidate_state": calibration["candidate_state"],
        "construction_diagnostics_passed": calibration["construction_diagnostic_all_passed"],
        "category_gain": calibration["category_accuracy_gain_over_baseline"],
        "candidate_metrics": calibration["arm_metrics"]["SEMANTIC_BASIS_V0_11"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
