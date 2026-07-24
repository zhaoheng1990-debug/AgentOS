"""Collect reference-blind Qwen/Gemma/Llama specialist receipts on CUDA."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_reference_first_role_analysis import (  # noqa: E402
    build_specialist_role_analysis,
    render_specialist_role_analysis,
    validate_specialist_role_analysis,
)
from local_collective_cognition.clarification_reference_first_role_runtime import (  # noqa: E402
    ReferenceFirstSpecialistRuntime,
    validate_specialist_role_run,
)
from local_collective_cognition.clarification_reference_first_roles import (  # noqa: E402
    MODEL_IDS,
    ROLE_TASK_KIND,
    build_specialist_role_plan,
    validate_specialist_role_plan,
)
from local_collective_cognition.local_transformers_provider import (  # noqa: E402
    LocalTransformersJsonAdapter,
    LocalTransformersModelSpec,
    LocalTransformersResidentPool,
)
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger, hash_payload  # noqa: E402


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def read(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/clarification_reference_first_v0_15")
    parser.add_argument("--qwen-path", default=r"D:\model\models--Qwen--Qwen2.5-1.5B-Instruct\main")
    parser.add_argument("--gemma-path", default=r"D:\model\gemma-2-2b-it")
    parser.add_argument("--llama-path", default=r"D:\model\Llama-3.2-1B-Instruct")
    parser.add_argument("--max-new-tokens", type=int, default=1400)
    args = parser.parse_args()
    output = resolve(args.output_dir)
    corpus = read(output / "private_reference_first_corpus.json")
    reference = read(output / "reference_first_model_panel_reference_candidate.json")
    frozen_progress = read(output / "reference_frozen_progress.json")
    plan = build_specialist_role_plan(corpus_artifact=corpus, frozen_reference=reference, frozen_progress=frozen_progress)
    validate_specialist_role_plan(plan, corpus_artifact=corpus, frozen_reference=reference, frozen_progress=frozen_progress)
    write(output / "local_specialist_role_plan.json", plan)
    experiment_id = "reference-first-specialists-" + hash_payload([corpus["artifact_hash"], reference["artifact_hash"], plan["plan_hash"]])[:16]
    paths = dict(zip(MODEL_IDS, (args.qwen_path, args.gemma_path, args.llama_path)))
    specs = tuple(LocalTransformersModelSpec(model_id, paths[model_id]) for model_id in MODEL_IDS)
    ledger = ProviderTelemetryLedger()
    pool = LocalTransformersResidentPool(specs)
    adapters = tuple(LocalTransformersJsonAdapter(
        provider_id="local-transformers-" + spec.model_id,
        model_id=spec.model_id,
        task_kinds=(ROLE_TASK_KIND,),
        pool=pool,
        telemetry_ledger=ledger,
        max_new_tokens=args.max_new_tokens,
        max_attempts=2,
        max_timeout_seconds=600,
    ) for spec in specs)
    try:
        pool.load_all()
        run = ReferenceFirstSpecialistRuntime(corpus_artifact=corpus, role_plan=plan).evaluate(
            experiment_id=experiment_id,
            adapters=adapters,
        )
    finally:
        pool.unload_all()
    validate_specialist_role_run(run, corpus_artifact=corpus, role_plan=plan)
    analysis = build_specialist_role_analysis(
        corpus_artifact=corpus,
        frozen_reference=reference,
        role_plan=plan,
        role_run=run,
    )
    validate_specialist_role_analysis(
        analysis,
        corpus_artifact=corpus,
        frozen_reference=reference,
        role_plan=plan,
        role_run=run,
    )
    telemetry_commitment = {
        "telemetry_version": "clarification_reference_first_role_telemetry_v0_15",
        "experiment_id": experiment_id,
        "items": [item.as_dict() for item in ledger.items()],
    }
    telemetry = {**telemetry_commitment, "artifact_hash": hash_payload(telemetry_commitment)}
    progress_commitment = {
        "progress_version": "clarification_reference_first_roles_progress_v0_15",
        "source_corpus_hash": corpus["artifact_hash"],
        "frozen_reference_hash": reference["artifact_hash"],
        "role_plan_hash": plan["plan_hash"],
        "role_run_hash": run["run_hash"],
        "role_analysis_hash": analysis["artifact_hash"],
        "telemetry_hash": telemetry["artifact_hash"],
        "current_phase": analysis["candidate_state"],
        "local_role_receipts_frozen": analysis["local_role_receipts_frozen"],
        "coordinator_run_allowed": analysis["coordinator_run_allowed"],
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    progress = {**progress_commitment, "artifact_hash": hash_payload(progress_commitment)}
    write(output / "local_specialist_role_run.json", run)
    write(output / "local_specialist_role_analysis.json", analysis)
    (output / "LOCAL_SPECIALIST_ROLE_ANALYSIS.md").write_text(render_specialist_role_analysis(analysis), encoding="utf-8")
    write(output / "local_specialist_role_telemetry.json", telemetry)
    write(output / "local_specialist_role_progress.json", progress)
    print(json.dumps({
        "experiment_id": experiment_id,
        "plan_hash": plan["plan_hash"],
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "completed_batch_count": len(run["receipts"]),
        "failed_batch_count": len(run["failures"]),
        "observed_decision_count": analysis["observed_decision_count"],
        "receipt_coverage": analysis["receipt_coverage"],
        "role_metrics": analysis["role_metrics"],
        "accounting": analysis["accounting"],
        "current_phase": progress["current_phase"],
        "coordinator_run_allowed": progress["coordinator_run_allowed"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
