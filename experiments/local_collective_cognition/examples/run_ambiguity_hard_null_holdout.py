"""Freeze and run the independent hard-null ambiguity coordinator holdout."""

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

from local_collective_cognition.ambiguity_discovery_adapters import (  # noqa: E402
    LocalAmbiguityDiscoveryAdapter,
    OllamaAmbiguityDiscoveryAdapter,
)
from local_collective_cognition.ambiguity_discovery_contracts import (  # noqa: E402
    TASK_KIND as DISCOVERY_TASK_KIND,
)
from local_collective_cognition.ambiguity_discovery_runtime import (  # noqa: E402
    AmbiguityDiscoveryRuntime,
)
from local_collective_cognition.ambiguity_hard_null_contracts import (  # noqa: E402
    TASK_KIND as HARD_NULL_TASK_KIND,
)
from local_collective_cognition.ambiguity_hard_null_eval import (  # noqa: E402
    build_hard_null_artifact,
    validate_hard_null_artifact,
)
from local_collective_cognition.ambiguity_hard_null_holdout import (  # noqa: E402
    CASES,
    EVIDENCE_REFS,
    HOLDOUT_SPEC,
    validate_hard_null_holdout_spec,
)
from local_collective_cognition.ambiguity_hard_null_runtime import (  # noqa: E402
    HardNullAmbiguityCoordinatorRuntime,
)
from local_collective_cognition.ambiguity_hard_null_surface import (  # noqa: E402
    build_hard_null_surface,
    validate_hard_null_surface,
)
from local_collective_cognition.local_transformers_provider import (  # noqa: E402
    LocalTransformersModelSpec,
    LocalTransformersResidentPool,
)
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from local_collective_cognition.provider_telemetry import (  # noqa: E402
    ProviderTelemetryLedger,
    hash_payload,
)


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load(path):
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def _validate_artifact_hash(artifact, name):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError(f"hard_null_{name}_artifact_hash_invalid")


def _freeze_preexecution_commitment(path, role_artifact):
    commitment = {
        "commitment_version": "ambiguity_hard_null_preexecution_v0_1",
        "holdout_spec": HOLDOUT_SPEC,
        "role_artifact_hash": role_artifact["artifact_hash"],
        "provider_inputs_generated": False,
        "predecessor_labels_used_for_tuning": False,
        "post_reveal_prompt_or_gate_adaptation_allowed": False,
    }
    artifact = {**commitment, "commitment_hash": hash_payload(commitment)}
    output = _resolve(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        existing = json.loads(output.read_text(encoding="utf-8"))
        if existing != artifact:
            raise ValueError("hard_null_preexecution_commitment_conflict")
    else:
        output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    return artifact


def _wait_for_release(base_url, model_id, timeout=240):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/ps", timeout=10) as response:
            loaded = json.loads(response.read().decode("utf-8")).get("models", [])
        if model_id not in {
            str(item.get("name") or item.get("model") or "") for item in loaded
        }:
            return
        time.sleep(2)
    raise TimeoutError("hard_null_ollama_release_timeout")


def _unload_ollama(base_url, model_id):
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/generate",
        data=json.dumps({"model": model_id, "keep_alive": 0}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        json.loads(response.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--role-source", default="outputs/ambiguity_coordinator_fallback_role_v0_1.json",
    )
    parser.add_argument("--gemma-path", default=r"D:\model\gemma-2-2b-it")
    parser.add_argument(
        "--preexecution-commitment",
        default="outputs/ambiguity_hard_null_preexecution_v0_1.json",
    )
    parser.add_argument(
        "--checkpoint", default="outputs/ambiguity_hard_null_holdout_v0_1_checkpoint.json",
    )
    parser.add_argument("--resume-checkpoint", default="")
    parser.add_argument(
        "--output", default="outputs/ambiguity_hard_null_holdout_v0_1.json",
    )
    args = parser.parse_args()

    validate_hard_null_holdout_spec()
    role = _load(args.role_source)
    _validate_artifact_hash(role, "role")
    preexecution = _freeze_preexecution_commitment(args.preexecution_commitment, role)
    roles = role["role_candidates"]
    proposer = roles["ambiguity_proposer"]
    skeptic = roles["null_skeptic"]
    coordinator = roles["semantic_coordinator"]

    if args.resume_checkpoint:
        checkpoint = _load(args.resume_checkpoint)
        checkpoint_commitment = {
            key: value for key, value in checkpoint.items() if key != "checkpoint_hash"
        }
        if (
            checkpoint.get("checkpoint_hash") != hash_payload(checkpoint_commitment)
            or checkpoint.get("holdout_spec_hash") != HOLDOUT_SPEC["spec_hash"]
            or checkpoint.get("role_artifact_hash") != role["artifact_hash"]
            or checkpoint.get("preexecution_commitment_hash")
            != preexecution["commitment_hash"]
        ):
            raise ValueError("hard_null_checkpoint_binding_invalid")
        experiment_id = checkpoint["experiment_id"]
        model_runs = tuple(checkpoint["model_runs"])
        surface = checkpoint["blind_surface"]
        validate_hard_null_surface(
            surface, role_artifact=role, model_runs=model_runs,
        )
    else:
        experiment_id = "ambiguity-hard-null-" + datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        )
        discovery = AmbiguityDiscoveryRuntime(
            cases=CASES,
            holdout_spec=HOLDOUT_SPEC,
            spec_validator=validate_hard_null_holdout_spec,
            evidence_refs=EVIDENCE_REFS,
        )
        ledger = ProviderTelemetryLedger()
        skeptic_adapter = OllamaAmbiguityDiscoveryAdapter(
            provider_id=skeptic["provider_id"],
            model_id=skeptic["model_id"],
            task_kinds=(DISCOVERY_TASK_KIND,),
            telemetry_ledger=ledger,
            timeout_seconds=900,
            max_new_tokens=768,
            max_attempts=2,
            thinking_enabled=False,
            keep_alive="15m",
        )
        skeptic_run = discovery.evaluate_model(
            experiment_id=experiment_id, adapter=skeptic_adapter,
        )
        _unload_ollama(skeptic_adapter.base_url, skeptic["model_id"])
        _wait_for_release(skeptic_adapter.base_url, skeptic["model_id"])

        pool = LocalTransformersResidentPool((
            LocalTransformersModelSpec(proposer["model_id"], args.gemma_path),
        ))
        proposer_adapter = LocalAmbiguityDiscoveryAdapter(
            provider_id=proposer["provider_id"],
            model_id=proposer["model_id"],
            task_kinds=(DISCOVERY_TASK_KIND,),
            pool=pool,
            telemetry_ledger=ledger,
            max_new_tokens=768,
            max_attempts=2,
        )
        try:
            pool.load_all()
            proposer_run = discovery.evaluate_model(
                experiment_id=experiment_id, adapter=proposer_adapter,
            )
        finally:
            pool.unload_all()
        model_runs = (proposer_run, skeptic_run)
        surface = build_hard_null_surface(role_artifact=role, model_runs=model_runs)
        checkpoint_commitment = {
            "experiment_id": experiment_id,
            "role_artifact_hash": role["artifact_hash"],
            "holdout_spec_hash": HOLDOUT_SPEC["spec_hash"],
            "preexecution_commitment_hash": preexecution["commitment_hash"],
            "model_runs": list(model_runs),
            "blind_surface": surface,
        }
        checkpoint = {
            **checkpoint_commitment,
            "checkpoint_hash": hash_payload(checkpoint_commitment),
        }
        checkpoint_path = _resolve(args.checkpoint)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(
            json.dumps(checkpoint, indent=2, sort_keys=True), encoding="utf-8",
        )

    adapter = OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
        coordinator["provider_id"],
        coordinator["model_id"],
        "https://api.deepseek.com/chat/completions",
        "DEEPSEEK_API_KEY",
        (HARD_NULL_TASK_KIND,),
        max_tokens=5000,
        timeout_seconds=240,
        extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
    ))
    coordinator_run = HardNullAmbiguityCoordinatorRuntime(surface=surface).evaluate(
        experiment_id=experiment_id, adapter=adapter,
    )
    artifact = build_hard_null_artifact(
        experiment_id=experiment_id,
        role_artifact=role,
        model_runs=model_runs,
        surface=surface,
        coordinator_run=coordinator_run,
    )
    validate_hard_null_artifact(artifact, role_artifact=role)
    output = _resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "artifact_hash": artifact["artifact_hash"],
        "preexecution_commitment_hash": preexecution["commitment_hash"],
        "holdout_spec_hash": HOLDOUT_SPEC["spec_hash"],
        "candidate_state": artifact["report"]["candidate_state"],
        "fixed_strategy_profiles": artifact["report"]["fixed_strategy_profiles"],
        "coordinator_profile": artifact["report"]["coordinator_profile"],
        "balanced_gain": artifact["report"]["balanced_gain_vs_frozen_comparator"],
        "receipt_control_profile": artifact["report"]["receipt_control_profile"],
        "cost_profile": artifact["report"]["cost_profile"],
        "gate_results": artifact["report"]["gate_results"],
        "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
