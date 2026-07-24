"""Run the capability-routed structural quality pilot on a fresh holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.capability_routed_structural_holdout import build_capability_routed_structural_harness  # noqa: E402
from local_collective_cognition.capability_routed_structural_runtime import CapabilityRoutedStructuralRuntime  # noqa: E402
from local_collective_cognition.collective_protocol import PILOT_TASK_KINDS, LocalCollectiveCognitionProtocol  # noqa: E402
from local_collective_cognition.disagreement_case_failure import DisagreementCaseProviderFailure  # noqa: E402
from local_collective_cognition.local_plan_intent_provider import PlanIntentTransformersResidentPool  # noqa: E402
from local_collective_cognition.local_structure_packet_provider import LocalQualityGatedStructureAdapter  # noqa: E402
from local_collective_cognition.local_transformers_provider import LocalTransformersModelSpec  # noqa: E402
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llama-path", default=r"D:\model\Llama-3.2-1B-Instruct")
    parser.add_argument("--qwen-path", default=r"D:\model\models--Qwen--Qwen2.5-1.5B-Instruct\main")
    parser.add_argument("--gemma-path", default=r"D:\model\gemma-2-2b-it")
    parser.add_argument("--capability-source", default="outputs/structural_prior_mini_pilot_v0_1.json")
    parser.add_argument("--output", default="outputs/capability_routed_structural_pilot_v0_4.json")
    args = parser.parse_args()
    source = REPO_ROOT / args.capability_source
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    specs = (
        LocalTransformersModelSpec("llama-3.2-1b-instruct", args.llama_path),
        LocalTransformersModelSpec("qwen2.5-1.5b-instruct", args.qwen_path),
        LocalTransformersModelSpec("gemma-2-2b-it", args.gemma_path),
    )
    ledger = ProviderTelemetryLedger()
    pool = PlanIntentTransformersResidentPool(specs)
    adapters = {spec.model_id: LocalQualityGatedStructureAdapter(
        provider_id="local-transformers-" + spec.model_id, model_id=spec.model_id,
        task_kinds=PILOT_TASK_KINDS, pool=pool, telemetry_ledger=ledger,
        max_new_tokens=1024, max_attempts=2,
    ) for spec in specs}
    base = LocalCollectiveCognitionProtocol(
        harness=build_capability_routed_structural_harness(), small_adapters=adapters,
        baseline_adapter=None, telemetry_ledger=ledger,
        reviewer_model_id="qwen2.5-1.5b-instruct", synthesizer_model_id="gemma-2-2b-it",
    )
    experiment_id = "capability-routed-structure-" + datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    failure = None
    try:
        pool.load_all()
        report = CapabilityRoutedStructuralRuntime(
            base, capability_source_report_hash=source_hash,
        ).run(experiment_id=experiment_id)
    except DisagreementCaseProviderFailure as exc:
        failure = {"experiment_id": experiment_id, "status": "FAILED_CLOSED",
                   "provider_failure": exc.as_dict()}
        report = failure
    finally:
        pool.unload_all()
    output = Path(args.output)
    if not output.is_absolute():
        output = REPO_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2 if failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
