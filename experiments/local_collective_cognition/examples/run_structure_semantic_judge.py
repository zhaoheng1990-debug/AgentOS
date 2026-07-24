"""Calibrate structure-packet quality with two independent blind semantic judges."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter, OpenAICompatibleProviderSpec,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.structure_semantic_judge_consensus import (  # noqa: E402
    build_semantic_report, validate_semantic_report,
)
from local_collective_cognition.structure_semantic_judge_artifact import validate_semantic_artifact  # noqa: E402
from local_collective_cognition.structure_semantic_judge_contracts import JUDGE_TASK_KIND  # noqa: E402
from local_collective_cognition.structure_semantic_judge_recovery import merge_recovered_judge_run  # noqa: E402
from local_collective_cognition.structure_semantic_judge_runtime import StructureSemanticJudgeRuntime  # noqa: E402


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _adapters():
    specs = (
        OpenAICompatibleProviderSpec(
            "deepseek", "deepseek-v4-flash", "https://api.deepseek.com/chat/completions",
            "DEEPSEEK_API_KEY", (JUDGE_TASK_KIND,), max_tokens=5000,
            extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
        ),
        OpenAICompatibleProviderSpec(
            "moonshot", "kimi-k2.5", "https://api.moonshot.cn/v1/chat/completions",
            "MOONSHOT_API_KEY", (JUDGE_TASK_KIND,), max_tokens=5000,
        ),
    )
    return tuple(OpenAICompatibleJsonAdapter(spec) for spec in specs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration-source", default="outputs/structure_elicitor_calibration_v0_2.json")
    parser.add_argument("--fresh-source", default="outputs/structure_elicitor_fresh_holdout_v0_1.json")
    parser.add_argument("--output", default="outputs/structure_semantic_judge_v0_1.json")
    args = parser.parse_args()
    calibration = json.loads(_resolve(args.calibration_source).read_text(encoding="utf-8"))
    fresh = json.loads(_resolve(args.fresh_source).read_text(encoding="utf-8"))
    experiment_id = "structure-semantic-judge-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runtime = StructureSemanticJudgeRuntime(
        calibration_artifact=calibration, fresh_artifact=fresh,
    )
    judge_runs = []
    for adapter in _adapters():
        run = runtime.evaluate_judge(experiment_id=experiment_id, adapter=adapter)
        if run["failures"]:
            recovery = runtime.evaluate_judge(
                experiment_id=experiment_id, adapter=adapter,
                batch_ids=tuple(item["batch_id"] for item in run["failures"]),
            )
            run = merge_recovered_judge_run(run, recovery, surface=runtime.surface)
        judge_runs.append(run)
    judge_runs = tuple(judge_runs)
    report = build_semantic_report(
        experiment_id=experiment_id, fresh_artifact=fresh,
        surface=runtime.surface, judge_runs=judge_runs,
    )
    validate_semantic_report(
        report, fresh_artifact=fresh, surface=runtime.surface, judge_runs=judge_runs,
    )
    commitment = {
        "experiment_id": experiment_id,
        "calibration_source_hash": calibration["artifact_hash"],
        "fresh_source_hash": fresh["artifact_hash"],
        "blind_surface": runtime.surface,
        "judge_runs": list(judge_runs),
        "report": report,
        "claim_boundary": (
            "dual-Provider semantic-scale calibration candidate only; no human gold labels, "
            "selection authority, retention authority, or endogenous ambiguity claim"
        ),
    }
    artifact = {**commitment, "artifact_hash": hash_payload(commitment)}
    validate_semantic_artifact(
        artifact, calibration_artifact=calibration, fresh_artifact=fresh,
    )
    output = _resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "artifact_hash": artifact["artifact_hash"], "output": str(output), "report": report,
    }, indent=2, sort_keys=True))
    return 0 if report["candidate_state"] == "SEMANTIC_SCALE_CALIBRATION_CANDIDATE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
