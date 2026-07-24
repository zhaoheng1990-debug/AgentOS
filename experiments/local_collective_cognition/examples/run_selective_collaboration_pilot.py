"""Run calibration-backed selective collaboration on the frozen holdout."""

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
CORE_ROOT = REPO_ROOT / "agentos_core_slim_v0"
sys.path.insert(0, str(CORE_ROOT))
sys.path.insert(0, str(PACK_ROOT))

from local_collective_cognition.collective_protocol import (  # noqa: E402
    PILOT_TASK_KINDS,
    LocalCollectiveCognitionProtocol,
    role_run_as_dict,
    role_run_from_dict,
)
from local_collective_cognition.holdout_benchmark import build_holdout_harness  # noqa: E402
from local_collective_cognition.local_transformers_provider import (  # noqa: E402
    LocalTransformersJsonAdapter,
    LocalTransformersModelSpec,
    LocalTransformersResidentPool,
)
from local_collective_cognition.ollama_provider import OllamaJsonAdapter  # noqa: E402
from local_collective_cognition.pilot_benchmark import build_pilot_harness  # noqa: E402
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger  # noqa: E402
from local_collective_cognition.selective_calibration import build_reliability_profiles  # noqa: E402
from local_collective_cognition.selective_protocol import SelectiveCollaborationProtocol  # noqa: E402


def wait_for_ollama_release(base_url: str, model_id: str, timeout_seconds: int = 180) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/ps", timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        loaded = {str(item.get("name") or item.get("model") or "") for item in payload.get("models", [])}
        if model_id not in loaded:
            return
        time.sleep(2)
    raise TimeoutError("ollama_model_release_timeout")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration-report", default="outputs/local_collective_cognition_pilot_v0_2.json")
    parser.add_argument("--llama-path", default=r"D:\model\Llama-3.2-1B-Instruct")
    parser.add_argument("--qwen-path", default=r"D:\model\models--Qwen--Qwen2.5-1.5B-Instruct\main")
    parser.add_argument("--gemma-path", default=r"D:\model\gemma-2-2b-it")
    parser.add_argument("--ollama-model", default="deepseek-r1:32b")
    parser.add_argument("--baseline-cache", default="outputs/selective_collaboration_32b_holdout_cache_v0_3.json")
    parser.add_argument("--output", default="outputs/selective_collaboration_pilot_v0_3.json")
    args = parser.parse_args()

    calibration_path = Path(args.calibration_report)
    if not calibration_path.is_absolute():
        calibration_path = REPO_ROOT / calibration_path
    calibration_report = json.loads(calibration_path.read_text(encoding="utf-8"))
    receipts, profiles = build_reliability_profiles(calibration_report, build_pilot_harness())

    specs = (
        LocalTransformersModelSpec("llama-3.2-1b-instruct", args.llama_path),
        LocalTransformersModelSpec("qwen2.5-1.5b-instruct", args.qwen_path),
        LocalTransformersModelSpec("gemma-2-2b-it", args.gemma_path),
    )
    ledger = ProviderTelemetryLedger()
    pool = LocalTransformersResidentPool(specs)
    small_adapters = {
        spec.model_id: LocalTransformersJsonAdapter(
            provider_id=f"local-transformers-{spec.model_id}",
            model_id=spec.model_id,
            task_kinds=PILOT_TASK_KINDS,
            pool=pool,
            telemetry_ledger=ledger,
            max_new_tokens=256,
            max_attempts=2,
        )
        for spec in specs
    }
    baseline = OllamaJsonAdapter(
        provider_id="ollama-local",
        model_id=args.ollama_model,
        task_kinds=PILOT_TASK_KINDS,
        telemetry_ledger=ledger,
        timeout_seconds=900,
        max_new_tokens=256,
        max_attempts=2,
        thinking_enabled=False,
        keep_alive=0,
    )
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_harness(),
        small_adapters=small_adapters,
        baseline_adapter=baseline,
        telemetry_ledger=ledger,
        reviewer_model_id="qwen2.5-1.5b-instruct",
        synthesizer_model_id="gemma-2-2b-it",
    )
    protocol = SelectiveCollaborationProtocol(
        base=base,
        reliability_receipts=receipts,
        reliability_profiles=profiles,
    )

    cache_path = Path(args.baseline_cache)
    if not cache_path.is_absolute():
        cache_path = REPO_ROOT / cache_path
    cached_baseline = role_run_from_dict(json.loads(cache_path.read_text(encoding="utf-8"))) if cache_path.is_file() else None

    def save_baseline(run):
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(role_run_as_dict(run), indent=2, sort_keys=True), encoding="utf-8")

    def prepare_small_models():
        if cached_baseline is None:
            wait_for_ollama_release(baseline.base_url, args.ollama_model)
        return pool.load_all()

    experiment_id = "selective-collaboration-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        report = protocol.run(
            experiment_id,
            baseline_run=cached_baseline,
            baseline_observer=save_baseline,
            prepare_small_models=prepare_small_models,
        )
    finally:
        pool.unload_all()
    report["protocol"]["baseline_reused_from_cache"] = cached_baseline is not None

    output = Path(args.output)
    if not output.is_absolute():
        output = REPO_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
