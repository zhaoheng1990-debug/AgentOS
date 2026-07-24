"""Run paired unstated-ambiguity discovery on two small models and a 32B ceiling."""

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

from local_collective_cognition.ambiguity_discovery_contracts import TASK_KIND  # noqa: E402
from local_collective_cognition.ambiguity_discovery_adapters import (  # noqa: E402
    LocalAmbiguityDiscoveryAdapter, OllamaAmbiguityDiscoveryAdapter,
)
from local_collective_cognition.ambiguity_discovery_eval import (  # noqa: E402
    build_discovery_report, validate_discovery_artifact, validate_discovery_report,
)
from local_collective_cognition.ambiguity_discovery_runtime import AmbiguityDiscoveryRuntime  # noqa: E402
from local_collective_cognition.local_transformers_provider import (  # noqa: E402
    LocalTransformersModelSpec, LocalTransformersResidentPool,
)
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger, hash_payload  # noqa: E402
from local_collective_cognition.structure_elicitor_fresh_eval import calibration_route  # noqa: E402


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
    raise TimeoutError("unstated_ambiguity_ollama_release_timeout")


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
    parser.add_argument("--calibration-source", default="outputs/structure_elicitor_calibration_v0_2.json")
    parser.add_argument("--judge-calibration", default="outputs/structure_reference_judge_calibration_v0_1.json")
    parser.add_argument("--qwen-path", default=r"D:\model\models--Qwen--Qwen2.5-1.5B-Instruct\main")
    parser.add_argument("--gemma-path", default=r"D:\model\gemma-2-2b-it")
    parser.add_argument("--predecessor", default="outputs/unstated_ambiguity_holdout_v0_3.json")
    parser.add_argument("--output", default="outputs/unstated_ambiguity_holdout_v0_4.json")
    args = parser.parse_args()
    calibration, judge_calibration = _load(args.calibration_source), _load(args.judge_calibration)
    selected, comparator, strong, _ = calibration_route(calibration)
    paths = {"qwen2.5-1.5b-instruct": args.qwen_path, "gemma-2-2b-it": args.gemma_path}
    if selected not in paths or comparator not in paths:
        raise ValueError("unstated_ambiguity_local_route_path_unavailable")
    experiment_id = "unstated-ambiguity-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runtime, ledger = AmbiguityDiscoveryRuntime(), ProviderTelemetryLedger()
    strong_adapter = OllamaAmbiguityDiscoveryAdapter(
        provider_id="ollama-local", model_id=strong, task_kinds=(TASK_KIND,),
        telemetry_ledger=ledger, timeout_seconds=900, max_new_tokens=768,
        max_attempts=2, thinking_enabled=False, keep_alive="15m",
    )
    strong_run = runtime.evaluate_model(experiment_id=experiment_id, adapter=strong_adapter)
    _unload_ollama(strong_adapter.base_url, strong)
    _wait_for_release(strong_adapter.base_url, strong)
    specs = tuple(LocalTransformersModelSpec(model_id, paths[model_id]) for model_id in (selected, comparator))
    pool = LocalTransformersResidentPool(specs)
    adapters = tuple(LocalAmbiguityDiscoveryAdapter(
        provider_id="local-transformers-" + spec.model_id, model_id=spec.model_id,
        task_kinds=(TASK_KIND,), pool=pool, telemetry_ledger=ledger,
        max_new_tokens=768, max_attempts=2,
    ) for spec in specs)
    try:
        pool.load_all()
        small_runs = tuple(runtime.evaluate_model(experiment_id=experiment_id, adapter=adapter)
                           for adapter in adapters)
    finally:
        pool.unload_all()
    model_runs = (*small_runs, strong_run)
    report = build_discovery_report(
        experiment_id=experiment_id, calibration_artifact=calibration,
        judge_calibration_artifact=judge_calibration,
        profiles=tuple(run["profile"] for run in model_runs),
    )
    validate_discovery_report(
        report, calibration_artifact=calibration, judge_calibration_artifact=judge_calibration,
    )
    predecessor = _load(args.predecessor)
    commitment = {
        "experiment_id": experiment_id, "report": report, "model_runs": list(model_runs),
        "predecessor_artifact_hash": predecessor["artifact_hash"],
        "construction_intervention": {
            "truth_and_frozen_gates_unchanged": True,
            "compact_discovery_messages": True,
            "nonpositive_structure_fields_mechanically_cleared": True,
            "strong_model_batch_residency": True,
            "discovery_state_decoupled_from_packet_construction": True,
            "concrete_state_and_confidence_template_removed": True,
            "state_menu_order_counterbalanced_by_item": True,
        },
        "claim_boundary": (
            "paired internal synthetic holdout for discovery-state evidence only; semantic packet quality "
            "remains pending calibrated Provider escalation; no baseline or production authority"
        ),
    }
    artifact = {**commitment, "artifact_hash": hash_payload(commitment)}
    validate_discovery_artifact(
        artifact, calibration_artifact=calibration, judge_calibration_artifact=judge_calibration,
    )
    output = _resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "candidate_state": report["candidate_state"], "profiles": report["profiles"],
        "artifact_hash": artifact["artifact_hash"], "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
