"""Calibrate three small structure elicitors against a DeepSeek-R1 32B ceiling."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.collective_protocol import PILOT_TASK_KINDS  # noqa: E402
from local_collective_cognition.local_structure_packet_provider import LocalQualityGatedStructureAdapter  # noqa: E402
from local_collective_cognition.local_transformers_provider import (  # noqa: E402
    LocalTransformersModelSpec, LocalTransformersResidentPool,
)
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger, hash_payload  # noqa: E402
from local_collective_cognition.structure_elicitor_calibration_eval import (  # noqa: E402
    build_calibration_report, validate_report,
)
from local_collective_cognition.structure_elicitor_calibration_holdout import TRUTH_COMMITMENT  # noqa: E402
from local_collective_cognition.structure_elicitor_calibration_runtime import (  # noqa: E402
    OllamaStructurePacketAdapter, StructureElicitorCalibrationRuntime,
)


def wait_for_ollama_release(base_url, model_id, timeout_seconds=240):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/ps", timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        loaded = {str(item.get("name") or item.get("model") or "") for item in payload.get("models", [])}
        if model_id not in loaded:
            return
        time.sleep(2)
    raise TimeoutError("ollama_model_release_timeout")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llama-path", default=r"D:\model\Llama-3.2-1B-Instruct")
    parser.add_argument("--qwen-path", default=r"D:\model\models--Qwen--Qwen2.5-1.5B-Instruct\main")
    parser.add_argument("--gemma-path", default=r"D:\model\gemma-2-2b-it")
    parser.add_argument("--ollama-model", default="deepseek-r1:32b")
    parser.add_argument("--output", default="outputs/structure_elicitor_calibration_v0_2.json")
    args = parser.parse_args()
    experiment_id = "structure-elicitor-calibration-" + datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    runtime = StructureElicitorCalibrationRuntime()
    ledger = ProviderTelemetryLedger()
    strong_adapter = OllamaStructurePacketAdapter(
        provider_id="ollama-local", model_id=args.ollama_model,
        task_kinds=PILOT_TASK_KINDS, telemetry_ledger=ledger,
        timeout_seconds=900, max_new_tokens=1024, max_attempts=2,
        thinking_enabled=False, keep_alive=0,
    )
    strong_run = runtime.evaluate_model(experiment_id=experiment_id, adapter=strong_adapter)
    wait_for_ollama_release(strong_adapter.base_url, args.ollama_model)

    specs = (
        LocalTransformersModelSpec("llama-3.2-1b-instruct", args.llama_path),
        LocalTransformersModelSpec("qwen2.5-1.5b-instruct", args.qwen_path),
        LocalTransformersModelSpec("gemma-2-2b-it", args.gemma_path),
    )
    pool = LocalTransformersResidentPool(specs)
    adapters = tuple(LocalQualityGatedStructureAdapter(
        provider_id="local-transformers-" + spec.model_id,
        model_id=spec.model_id, task_kinds=PILOT_TASK_KINDS,
        pool=pool, telemetry_ledger=ledger, max_new_tokens=1024, max_attempts=2,
    ) for spec in specs)
    try:
        pool.load_all()
        small_runs = tuple(
            runtime.evaluate_model(experiment_id=experiment_id, adapter=adapter)
            for adapter in adapters
        )
    finally:
        pool.unload_all()
    model_runs = (strong_run, *small_runs)
    report = build_calibration_report(
        experiment_id=experiment_id,
        profiles=tuple(item["profile"] for item in model_runs),
        strong_model_id=args.ollama_model,
        truth_commitment=TRUTH_COMMITMENT,
    )
    validate_report(report)
    commitment = {
        "experiment_id": experiment_id,
        "report": report,
        "model_runs": list(model_runs),
        "claim_boundary": (
            "calibration-only transfer candidate; independent fresh holdout required before "
            "AgentOS capability evidence or retention"
        ),
    }
    artifact = {**commitment, "artifact_hash": hash_payload(commitment)}
    output = Path(args.output)
    if not output.is_absolute():
        output = REPO_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(artifact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
