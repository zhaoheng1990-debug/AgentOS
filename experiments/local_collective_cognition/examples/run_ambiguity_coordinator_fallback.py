"""Run the calibrated secondary coordinator after bounded primary failures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.ambiguity_coordinator_contracts import TASK_KIND  # noqa: E402
from local_collective_cognition.ambiguity_coordinator_eval import (  # noqa: E402
    build_coordinator_artifact, validate_coordinator_artifact,
)
from local_collective_cognition.ambiguity_coordinator_fallback import (  # noqa: E402
    build_fallback_role_candidate, validate_fallback_role_candidate,
)
from local_collective_cognition.ambiguity_coordinator_holdout import HOLDOUT_SPEC  # noqa: E402
from local_collective_cognition.ambiguity_coordinator_runtime import AmbiguityCoordinatorRuntime  # noqa: E402
from local_collective_cognition.ambiguity_coordinator_surface import (  # noqa: E402
    build_coordinator_surface, validate_coordinator_surface,
)
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter, OpenAICompatibleProviderSpec,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load(path):
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary-role", default="outputs/ambiguity_role_complementarity_v0_1.json")
    parser.add_argument("--judge-calibration", default="outputs/structure_reference_judge_calibration_v0_1.json")
    parser.add_argument("--primary-failure-v1", default="outputs/ambiguity_coordinator_fresh_holdout_v0_1.json")
    parser.add_argument("--primary-failure-v2", default="outputs/ambiguity_coordinator_fresh_holdout_v0_2.json")
    parser.add_argument("--checkpoint", default="outputs/ambiguity_coordinator_fresh_holdout_v0_1_checkpoint.json")
    parser.add_argument("--fallback-role-output", default="outputs/ambiguity_coordinator_fallback_role_v0_1.json")
    parser.add_argument("--output", default="outputs/ambiguity_coordinator_fresh_holdout_v0_3.json")
    args = parser.parse_args()
    primary_role, judge = _load(args.primary_role), _load(args.judge_calibration)
    failures = (_load(args.primary_failure_v1), _load(args.primary_failure_v2))
    checkpoint = _load(args.checkpoint)
    checkpoint_commitment = {key: value for key, value in checkpoint.items() if key != "checkpoint_hash"}
    if (checkpoint.get("checkpoint_hash") != hash_payload(checkpoint_commitment)
            or checkpoint.get("role_artifact_hash") != primary_role["artifact_hash"]
            or checkpoint.get("holdout_spec_hash") != HOLDOUT_SPEC["spec_hash"]):
        raise ValueError("ambiguity_coordinator_fallback_checkpoint_invalid")
    fallback_role = build_fallback_role_candidate(
        primary_role_artifact=primary_role, judge_calibration_artifact=judge,
        primary_failure_artifacts=failures,
    )
    validate_fallback_role_candidate(
        fallback_role, primary_role_artifact=primary_role,
        judge_calibration_artifact=judge, primary_failure_artifacts=failures,
    )
    role_output = _resolve(args.fallback_role_output)
    role_output.parent.mkdir(parents=True, exist_ok=True)
    role_output.write_text(json.dumps(fallback_role, indent=2, sort_keys=True), encoding="utf-8")
    model_runs = tuple(checkpoint["model_runs"])
    original_surface = checkpoint["blind_surface"]
    validate_coordinator_surface(
        original_surface, role_artifact=primary_role, model_runs=model_runs,
    )
    surface = build_coordinator_surface(
        role_artifact=fallback_role, model_runs=model_runs, batch_size=3,
    )
    coordinator = fallback_role["role_candidates"]["semantic_coordinator"]
    adapter = OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
        coordinator["provider_id"], coordinator["model_id"],
        "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", (TASK_KIND,),
        max_tokens=4000, timeout_seconds=180,
        extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
    ))
    run = AmbiguityCoordinatorRuntime(surface=surface, max_attempts_per_batch=1).evaluate(
        experiment_id=checkpoint["experiment_id"] + "-fallback", adapter=adapter,
    )
    intervention = {
        "primary_failure_artifact_hashes": [artifact["artifact_hash"] for artifact in failures],
        "primary_total_semantic_decisions": 0,
        "truth_tasks_local_role_receipts_semantic_contract_and_gates_unchanged": True,
        "coordinator_route_changed_to_calibrated_secondary": True,
        "batch_size": 3, "max_attempts_per_batch": 1, "max_tokens": 4000,
    }
    artifact = build_coordinator_artifact(
        experiment_id=checkpoint["experiment_id"] + "-fallback",
        role_artifact=fallback_role, judge_calibration_artifact=judge,
        model_runs=model_runs, surface=surface, coordinator_run=run,
        construction_intervention=intervention,
    )
    validate_coordinator_artifact(
        artifact, role_artifact=fallback_role, judge_calibration_artifact=judge,
    )
    output = _resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "artifact_hash": artifact["artifact_hash"], "fallback_role_hash": fallback_role["artifact_hash"],
        "candidate_state": artifact["report"]["candidate_state"],
        "coordinator_profile": artifact["report"]["coordinator_profile"],
        "balanced_gain": artifact["report"]["balanced_gain_vs_frozen_comparator"],
        "cost_profile": artifact["report"]["cost_profile"],
        "gate_results": artifact["report"]["gate_results"], "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
