"""Run and score the fresh joint coordinator experiment v0.13."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.bounded_retry_provider import BoundedRetryProviderAdapter
from local_collective_cognition.clarification_joint_fresh_contracts import FRESH_COORDINATOR_TASK_KIND
from local_collective_cognition.clarification_joint_fresh_eval import build_joint_fresh_analysis, build_joint_fresh_report, render_joint_fresh_analysis, validate_joint_fresh_report
from local_collective_cognition.clarification_joint_fresh_runtime import ClarificationJointFreshRuntime, validate_joint_fresh_run
from local_collective_cognition.openai_compatible_provider import OpenAICompatibleJsonAdapter, OpenAICompatibleProviderSpec


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/clarification_joint_fresh_v0_13"
    parser.add_argument("--corpus", default=f"{base}/private_joint_corpus.json")
    parser.add_argument("--output-dir", default=base)
    args = parser.parse_args()
    corpus = json.loads(resolve(args.corpus).read_text(encoding="utf-8"))
    spec = OpenAICompatibleProviderSpec(
        "deepseek-v013-joint-fresh", "deepseek-v4-flash", "https://api.deepseek.com/chat/completions",
        "DEEPSEEK_API_KEY", (FRESH_COORDINATOR_TASK_KIND,), max_tokens=3800, timeout_seconds=240,
        extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
    )
    adapter = BoundedRetryProviderAdapter(OpenAICompatibleJsonAdapter(spec), max_attempts=2)
    experiment_id = "joint-fresh-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = ClarificationJointFreshRuntime(corpus_artifact=corpus).evaluate(experiment_id=experiment_id, adapter=adapter)
    validate_joint_fresh_run(run, corpus_artifact=corpus)
    report = build_joint_fresh_report(corpus_artifact=corpus, run=run)
    validate_joint_fresh_report(report, corpus_artifact=corpus, run=run)
    analysis = build_joint_fresh_analysis(report)
    output = resolve(args.output_dir); output.mkdir(parents=True, exist_ok=True)
    (output / "candidate_run.json").write_text(json.dumps(run, indent=2, sort_keys=True), encoding="utf-8")
    (output / "construction_pre_panel_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (output / "pre_panel_analysis.json").write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    (output / "PRE_PANEL_ANALYSIS.md").write_text(render_joint_fresh_analysis(analysis), encoding="utf-8")
    print(json.dumps({"run_hash": run["run_hash"], "report_hash": report["artifact_hash"], "analysis_hash": analysis["artifact_hash"], "candidate_state": report["candidate_state"], "failed_batches": len(run["failures"]), "construction_diagnostic_all_passed": report["construction_diagnostic_all_passed"], "preserve_all_baseline": report["preserve_all_baseline"], "candidate_metrics": report["candidate_metrics"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
