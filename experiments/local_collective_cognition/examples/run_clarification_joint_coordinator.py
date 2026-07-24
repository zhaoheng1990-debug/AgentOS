"""Run the observed-conflict joint coordinator experiment v0.12."""

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
from local_collective_cognition.clarification_joint_coordinator_contracts import JOINT_COORDINATOR_TASK_KIND
from local_collective_cognition.clarification_joint_coordinator_eval import build_joint_coordinator_analysis, build_joint_coordinator_report, render_joint_coordinator_analysis, validate_joint_coordinator_report
from local_collective_cognition.clarification_joint_coordinator_runtime import ClarificationJointCoordinatorRuntime, validate_joint_coordinator_run
from local_collective_cognition.clarification_joint_coordinator_surface import build_joint_coordinator_surface, validate_joint_coordinator_surface
from local_collective_cognition.openai_compatible_provider import OpenAICompatibleJsonAdapter, OpenAICompatibleProviderSpec


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def read(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    source = "outputs/clarification_semantic_basis_v0_11"
    parser.add_argument("--source-dir", default=source)
    parser.add_argument("--output-dir", default="outputs/clarification_joint_coordinator_v0_12")
    args = parser.parse_args()
    source = args.source_dir
    corpus = read(f"{source}/private_semantic_basis_corpus.json")
    reference = read(f"{source}/semantic_basis_model_panel_reference_candidate.json")
    adjudication_pack = read(f"{source}/kimi_k3_semantic_basis_adjudication_pack.json")
    adjudication_response = read(f"{source}/kimi_k3_semantic_basis_response.json")
    surface = build_joint_coordinator_surface(corpus_artifact=corpus, panel_reference=reference, adjudication_pack=adjudication_pack, adjudication_response=adjudication_response)
    validate_joint_coordinator_surface(surface, corpus_artifact=corpus, panel_reference=reference, adjudication_pack=adjudication_pack, adjudication_response=adjudication_response)
    spec = OpenAICompatibleProviderSpec(
        "deepseek-v012-joint-coordinator", "deepseek-v4-flash",
        "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY",
        (JOINT_COORDINATOR_TASK_KIND,), max_tokens=2600, timeout_seconds=240,
        extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
    )
    adapter = BoundedRetryProviderAdapter(OpenAICompatibleJsonAdapter(spec), max_attempts=2)
    experiment_id = "joint-coordinator-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = ClarificationJointCoordinatorRuntime(surface=surface).evaluate(experiment_id=experiment_id, adapter=adapter)
    validate_joint_coordinator_run(run, surface=surface)
    report = build_joint_coordinator_report(surface=surface, run=run)
    validate_joint_coordinator_report(report, surface=surface, run=run)
    analysis = build_joint_coordinator_analysis(report, run=run)
    output = resolve(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    write(output / "joint_conflict_surface.json", surface)
    write(output / "coordinator_run.json", run)
    write(output / "coordinator_report.json", report)
    write(output / "post_experiment_analysis.json", analysis)
    (output / "POST_EXPERIMENT_ANALYSIS.md").write_text(render_joint_coordinator_analysis(analysis), encoding="utf-8")
    print(json.dumps({
        "surface_hash": surface["surface_hash"], "run_hash": run["run_hash"],
        "report_hash": report["artifact_hash"], "analysis_hash": analysis["artifact_hash"],
        "provider_failure": report["provider_failure"], "decision_count": report["decision_count"],
        "accepted_repair_count": report["accepted_repair_count"], "reopen_required_count": report["reopen_required_count"],
        "mechanical_state_counts": report["mechanical_state_counts"], "accounting": report["accounting"],
        "candidate_state": report["candidate_state"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
