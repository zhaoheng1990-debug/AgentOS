"""Run the fresh proposer-skeptic-coordinator ambiguity calibration."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
import time
import urllib.request
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.ambiguity_coordinator_contracts import TASK_KIND as COORDINATOR_TASK_KIND  # noqa: E402
from local_collective_cognition.ambiguity_coordinator_eval import (  # noqa: E402
    build_coordinator_artifact, validate_coordinator_artifact,
)
from local_collective_cognition.ambiguity_coordinator_holdout import (  # noqa: E402
    CASES, EVIDENCE_REFS, HOLDOUT_SPEC, validate_coordinator_holdout_spec,
)
from local_collective_cognition.ambiguity_coordinator_runtime import AmbiguityCoordinatorRuntime  # noqa: E402
from local_collective_cognition.ambiguity_coordinator_surface import (  # noqa: E402
    build_coordinator_surface, validate_coordinator_surface,
)
from local_collective_cognition.ambiguity_discovery_adapters import (  # noqa: E402
    LocalAmbiguityDiscoveryAdapter, OllamaAmbiguityDiscoveryAdapter,
)
from local_collective_cognition.ambiguity_discovery_contracts import TASK_KIND as DISCOVERY_TASK_KIND  # noqa: E402
from local_collective_cognition.ambiguity_discovery_runtime import AmbiguityDiscoveryRuntime  # noqa: E402
from local_collective_cognition.ambiguity_role_complementarity import (  # noqa: E402
    validate_role_complementarity_candidate,
)
from local_collective_cognition.local_transformers_provider import (  # noqa: E402
    LocalTransformersModelSpec, LocalTransformersResidentPool,
)
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter, OpenAICompatibleProviderSpec,
)
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger, hash_payload  # noqa: E402


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load(path):
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def _wait_for_release(base_url, model_id, timeout=240):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/ps", timeout=10) as response:
            loaded = json.loads(response.read().decode("utf-8")).get("models", [])
        if model_id not in {str(item.get("name") or item.get("model") or "") for item in loaded}:
            return
        time.sleep(2)
    raise TimeoutError("ambiguity_coordinator_ollama_release_timeout")


def _unload_ollama(base_url, model_id):
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/generate",
        data=json.dumps({"model": model_id, "keep_alive": 0}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        json.loads(response.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role-source", default="outputs/ambiguity_role_complementarity_v0_1.json")
    parser.add_argument("--predecessor-holdout", default="outputs/unstated_ambiguity_holdout_v0_4.json")
    parser.add_argument("--judge-calibration", default="outputs/structure_reference_judge_calibration_v0_1.json")
    parser.add_argument("--gemma-path", default=r"D:\model\gemma-2-2b-it")
    parser.add_argument("--checkpoint", default="outputs/ambiguity_coordinator_fresh_holdout_v0_1_checkpoint.json")
    parser.add_argument("--resume-checkpoint", default="")
    parser.add_argument("--batch-size", type=int, choices=(3, 6), default=6)
    parser.add_argument("--coordinator-attempts", type=int, choices=(1, 2), default=2)
    parser.add_argument("--coordinator-max-tokens", type=int, default=6000)
    parser.add_argument("--construction-predecessor", default="")
    parser.add_argument("--output", default="outputs/ambiguity_coordinator_fresh_holdout_v0_1.json")
    args = parser.parse_args()
    role, predecessor, judge = _load(args.role_source), _load(args.predecessor_holdout), _load(args.judge_calibration)
    validate_role_complementarity_candidate(
        role, holdout_artifact=predecessor, judge_calibration_artifact=judge,
    )
    validate_coordinator_holdout_spec()
    roles = role["role_candidates"]
    proposer, skeptic, coordinator = (
        roles["ambiguity_proposer"], roles["null_skeptic"], roles["semantic_coordinator"],
    )
    if args.resume_checkpoint:
        checkpoint = _load(args.resume_checkpoint)
        checkpoint_commitment = {
            key: value for key, value in checkpoint.items() if key != "checkpoint_hash"
        }
        if (checkpoint.get("checkpoint_hash") != hash_payload(checkpoint_commitment)
                or checkpoint.get("role_artifact_hash") != role["artifact_hash"]
                or checkpoint.get("holdout_spec_hash") != HOLDOUT_SPEC["spec_hash"]):
            raise ValueError("ambiguity_coordinator_checkpoint_binding_invalid")
        experiment_id = checkpoint["experiment_id"]
        model_runs = tuple(checkpoint["model_runs"])
        surface = checkpoint["blind_surface"]
        validate_coordinator_surface(surface, role_artifact=role, model_runs=model_runs)
        if args.batch_size != surface.get("batch_size", 6):
            surface = build_coordinator_surface(
                role_artifact=role, model_runs=model_runs, batch_size=args.batch_size,
            )
    else:
        experiment_id = "ambiguity-coordinator-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        discovery = AmbiguityDiscoveryRuntime(
            cases=CASES, holdout_spec=HOLDOUT_SPEC,
            spec_validator=validate_coordinator_holdout_spec, evidence_refs=EVIDENCE_REFS,
        )
        ledger = ProviderTelemetryLedger()
        skeptic_adapter = OllamaAmbiguityDiscoveryAdapter(
            provider_id=skeptic["provider_id"], model_id=skeptic["model_id"],
            task_kinds=(DISCOVERY_TASK_KIND,), telemetry_ledger=ledger,
            timeout_seconds=900, max_new_tokens=768, max_attempts=2,
            thinking_enabled=False, keep_alive="15m",
        )
        skeptic_run = discovery.evaluate_model(experiment_id=experiment_id, adapter=skeptic_adapter)
        _unload_ollama(skeptic_adapter.base_url, skeptic["model_id"])
        _wait_for_release(skeptic_adapter.base_url, skeptic["model_id"])

        spec = LocalTransformersModelSpec(proposer["model_id"], args.gemma_path)
        pool = LocalTransformersResidentPool((spec,))
        proposer_adapter = LocalAmbiguityDiscoveryAdapter(
            provider_id=proposer["provider_id"], model_id=proposer["model_id"],
            task_kinds=(DISCOVERY_TASK_KIND,), pool=pool, telemetry_ledger=ledger,
            max_new_tokens=768, max_attempts=2,
        )
        try:
            pool.load_all()
            proposer_run = discovery.evaluate_model(experiment_id=experiment_id, adapter=proposer_adapter)
        finally:
            pool.unload_all()
        model_runs = (proposer_run, skeptic_run)
        surface = build_coordinator_surface(role_artifact=role, model_runs=model_runs)
        checkpoint_commitment = {
            "experiment_id": experiment_id, "role_artifact_hash": role["artifact_hash"],
            "holdout_spec_hash": HOLDOUT_SPEC["spec_hash"], "model_runs": list(model_runs),
            "blind_surface": surface,
        }
        checkpoint = {**checkpoint_commitment, "checkpoint_hash": hash_payload(checkpoint_commitment)}
        checkpoint_path = _resolve(args.checkpoint)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True), encoding="utf-8")
        if args.batch_size != 6:
            surface = build_coordinator_surface(
                role_artifact=role, model_runs=model_runs, batch_size=args.batch_size,
            )
    coordinator_adapter = OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
        coordinator["provider_id"], coordinator["model_id"],
        "https://api.moonshot.cn/v1/chat/completions", "MOONSHOT_API_KEY",
        (COORDINATOR_TASK_KIND,), max_tokens=args.coordinator_max_tokens, timeout_seconds=240,
    ))
    coordinator_run = AmbiguityCoordinatorRuntime(
        surface=surface, max_attempts_per_batch=args.coordinator_attempts,
    ).evaluate(
        experiment_id=experiment_id, adapter=coordinator_adapter,
    )
    construction_intervention = None
    if args.construction_predecessor:
        predecessor_artifact = _load(args.construction_predecessor)
        validate_coordinator_artifact(
            predecessor_artifact, role_artifact=role, judge_calibration_artifact=judge,
        )
        if predecessor_artifact["coordinator_run"]["profile"]["decision_count"] != 0:
            raise ValueError("ambiguity_coordinator_construction_predecessor_has_semantic_output")
        construction_intervention = {
            "predecessor_artifact_hash": predecessor_artifact["artifact_hash"],
            "truth_tasks_roles_receipts_and_gates_unchanged": True,
            "semantic_objective_and_decision_contract_unchanged": True,
            "predecessor_decision_count": 0,
            "batch_size": args.batch_size,
            "max_attempts_per_batch": args.coordinator_attempts,
            "max_tokens": args.coordinator_max_tokens,
        }
    artifact = build_coordinator_artifact(
        experiment_id=experiment_id, role_artifact=role, judge_calibration_artifact=judge,
        model_runs=model_runs, surface=surface, coordinator_run=coordinator_run,
        construction_intervention=construction_intervention,
    )
    validate_coordinator_artifact(
        artifact, role_artifact=role, judge_calibration_artifact=judge,
    )
    output = _resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "artifact_hash": artifact["artifact_hash"], "output": str(output),
        "candidate_state": artifact["report"]["candidate_state"],
        "fixed_strategy_profiles": artifact["report"]["fixed_strategy_profiles"],
        "coordinator_profile": artifact["report"]["coordinator_profile"],
        "balanced_gain": artifact["report"]["balanced_gain_vs_frozen_comparator"],
        "cost_profile": artifact["report"]["cost_profile"],
        "gate_results": artifact["report"]["gate_results"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
