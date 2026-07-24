"""Live smoke for the local Transformers pool and Ollama structured adapter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
CORE_ROOT = REPO_ROOT / "agentos_core_slim_v0"
sys.path.insert(0, str(CORE_ROOT))
sys.path.insert(0, str(PACK_ROOT))

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter  # noqa: E402
from local_collective_cognition import (  # noqa: E402
    LocalTransformersJsonAdapter,
    LocalTransformersModelSpec,
    LocalTransformersResidentPool,
    OllamaJsonAdapter,
    ProviderTelemetryLedger,
)


EVIDENCE = ["evidence://local-provider-prerequisites-smoke"]
SCHEMA = {
    "type": "object",
    "required": ["status", "evidence_refs"],
    "properties": {
        "status": {"type": "string", "enum": ["OK"]},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
    },
}


def smoke_task(task_id: str, task_kind: str) -> ProviderCognitiveTask:
    return ProviderCognitiveTask(
        task_id=task_id,
        task_kind=task_kind,
        objective="Return status exactly OK and evidence_refs exactly as supplied.",
        inputs={"requested_status": "OK", "required_evidence_refs": EVIDENCE},
        allowed_evidence=EVIDENCE,
        expected_schema=SCHEMA,
        timeout_seconds=300,
    )


def run_small_models(args: argparse.Namespace) -> dict:
    specs = (
        LocalTransformersModelSpec("llama-3.2-1b-instruct", args.llama_path),
        LocalTransformersModelSpec("qwen2.5-1.5b-instruct", args.qwen_path),
        LocalTransformersModelSpec("gemma-2-2b-it", args.gemma_path),
    )
    pool = LocalTransformersResidentPool(specs)
    resident = pool.load_all()
    ledger = ProviderTelemetryLedger()
    results = {}
    try:
        for spec in specs:
            adapter = LocalTransformersJsonAdapter(
                provider_id="local-transformers",
                model_id=spec.model_id,
                task_kinds=("local_transformers_json_smoke",),
                pool=pool,
                telemetry_ledger=ledger,
                max_new_tokens=96,
                max_attempts=2,
            )
            envelope = ProviderTaskRouter([adapter]).route(smoke_task(
                f"smoke-{spec.model_id}", "local_transformers_json_smoke"
            ))
            if envelope.status != "COMPLETED" or envelope.normalized_result.get("evidence_refs") != EVIDENCE:
                raise RuntimeError(f"local_model_smoke_failed:{spec.model_id}:{envelope.status}")
            results[spec.model_id] = envelope.normalized_result
        return {
            "all_resident_before_execution": set(resident) == {item.model_id for item in specs},
            "resident_model_ids": list(resident),
            "results": results,
            "telemetry": [item.as_dict() for item in ledger.items()],
        }
    finally:
        pool.unload_all()


def run_ollama(args: argparse.Namespace) -> dict:
    ledger = ProviderTelemetryLedger()
    adapter = OllamaJsonAdapter(
        provider_id="ollama-local",
        model_id=args.ollama_model,
        task_kinds=("ollama_json_smoke",),
        telemetry_ledger=ledger,
        base_url=args.ollama_url,
        timeout_seconds=args.ollama_timeout,
        max_new_tokens=256,
        thinking_enabled=args.ollama_thinking,
        keep_alive=0,
    )
    task = smoke_task("smoke-deepseek-r1-32b", "ollama_json_smoke")
    envelope = ProviderTaskRouter([adapter]).route(task)
    if envelope.status != "COMPLETED" or envelope.normalized_result.get("evidence_refs") != EVIDENCE:
        raise RuntimeError(f"ollama_smoke_failed:{envelope.status}")
    telemetry = ledger.items()
    return {
        "model_id": args.ollama_model,
        "result": envelope.normalized_result,
        "thinking_separated": "thinking" not in envelope.normalized_result,
        "thinking_char_count": telemetry[-1].thinking_char_count,
        "thinking_text_retained_in_memory": bool(adapter.thinking_text(task.task_id)),
        "telemetry": [item.as_dict() for item in telemetry],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llama-path", default=r"D:\model\Llama-3.2-1B-Instruct")
    parser.add_argument("--qwen-path", default=r"D:\model\models--Qwen--Qwen2.5-1.5B-Instruct\main")
    parser.add_argument("--gemma-path", default=r"D:\model\gemma-2-2b-it")
    parser.add_argument("--ollama-model", default="deepseek-r1:32b")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--ollama-timeout", type=int, default=600)
    parser.add_argument("--ollama-thinking", action="store_true")
    parser.add_argument("--small-only", action="store_true")
    parser.add_argument("--ollama-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.small_only and args.ollama_only:
        parser.error("--small-only and --ollama-only are mutually exclusive")
    return args


def main() -> None:
    args = parse_args()
    result = {
        "smoke_id": "local-provider-prerequisites-v0-1",
        "small_models": None if args.ollama_only else run_small_models(args),
        "ollama": None if args.small_only else run_ollama(args),
    }
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
