"""Recover failed specialist receipts with flat one-object local tasks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_reference_first_role_analysis import build_specialist_role_analysis, render_specialist_role_analysis, validate_specialist_role_analysis  # noqa: E402
from local_collective_cognition.clarification_reference_first_role_recovery import (  # noqa: E402
    ReferenceFirstSpecialistRecoveryRuntime,
    build_recovered_specialist_role_run,
    build_specialist_recovery_plan,
    validate_specialist_recovery_plan,
    validate_specialist_recovery_run,
)
from local_collective_cognition.clarification_reference_first_role_runtime import validate_specialist_role_run  # noqa: E402
from local_collective_cognition.clarification_reference_first_roles import MODEL_IDS, ROLE_TASK_KIND  # noqa: E402
from local_collective_cognition.local_transformers_provider import LocalTransformersJsonAdapter, LocalTransformersModelSpec, LocalTransformersResidentPool  # noqa: E402
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
    parser.add_argument("--max-new-tokens", type=int, default=480)
    args = parser.parse_args()
    output = resolve(args.output_dir)
    corpus = read(output / "private_reference_first_corpus.json")
    reference = read(output / "reference_first_model_panel_reference_candidate.json")
    role_plan = read(output / "local_specialist_role_plan.json")
    initial_run = read(output / "local_specialist_role_run.json")
    recovery_plan = build_specialist_recovery_plan(role_plan=role_plan, failed_run=initial_run)
    validate_specialist_recovery_plan(recovery_plan, role_plan=role_plan, failed_run=initial_run)
    write(output / "local_specialist_role_recovery_plan.json", recovery_plan)
    evidence_refs = [*corpus["evidence_refs"], f"artifact://{corpus['artifact_hash']}", f"surface://{corpus['public_surface']['surface_hash']}"]
    experiment_id = "reference-first-role-recovery-" + hash_payload([role_plan["plan_hash"], initial_run["run_hash"], recovery_plan["plan_hash"]])[:16]
    paths = dict(zip(MODEL_IDS, (args.qwen_path, args.gemma_path, args.llama_path)))
    specs = tuple(LocalTransformersModelSpec(model_id, paths[model_id]) for model_id in MODEL_IDS)
    ledger = ProviderTelemetryLedger()
    pool = LocalTransformersResidentPool(specs)
    adapters = tuple(LocalTransformersJsonAdapter(provider_id="local-transformers-recovery-" + spec.model_id, model_id=spec.model_id, task_kinds=(ROLE_TASK_KIND,), pool=pool, telemetry_ledger=ledger, max_new_tokens=args.max_new_tokens, max_attempts=2, max_timeout_seconds=600) for spec in specs)
    try:
        pool.load_all()
        recovery_run = ReferenceFirstSpecialistRecoveryRuntime(role_plan=role_plan, failed_run=initial_run, recovery_plan=recovery_plan, evidence_refs=evidence_refs).evaluate(experiment_id=experiment_id, adapters=adapters)
    finally:
        pool.unload_all()
    validate_specialist_recovery_run(recovery_run, recovery_plan=recovery_plan)
    recovered_run = build_recovered_specialist_role_run(role_plan=role_plan, initial_run=initial_run, recovery_plan=recovery_plan, recovery_run=recovery_run)
    validate_specialist_role_run(recovered_run, corpus_artifact=corpus, role_plan=role_plan)
    analysis = build_specialist_role_analysis(corpus_artifact=corpus, frozen_reference=reference, role_plan=role_plan, role_run=recovered_run)
    validate_specialist_role_analysis(analysis, corpus_artifact=corpus, frozen_reference=reference, role_plan=role_plan, role_run=recovered_run)
    telemetry_commitment = {"telemetry_version": "clarification_reference_first_role_recovery_telemetry_v0_15", "experiment_id": experiment_id, "items": [item.as_dict() for item in ledger.items()]}
    telemetry = {**telemetry_commitment, "artifact_hash": hash_payload(telemetry_commitment)}
    progress_commitment = {"progress_version": "clarification_reference_first_roles_recovered_progress_v0_15", "source_corpus_hash": corpus["artifact_hash"], "frozen_reference_hash": reference["artifact_hash"], "initial_failed_run_hash": initial_run["run_hash"], "recovery_plan_hash": recovery_plan["plan_hash"], "recovery_run_hash": recovery_run["run_hash"], "recovered_role_run_hash": recovered_run["run_hash"], "role_analysis_hash": analysis["artifact_hash"], "telemetry_hash": telemetry["artifact_hash"], "current_phase": analysis["candidate_state"], "local_role_receipts_frozen": analysis["local_role_receipts_frozen"], "coordinator_run_allowed": analysis["coordinator_run_allowed"], "reference_revision_allowed": False, "ground_truth_claim": False, "action_credit_authority": False, "selection_authority": False, "retention_authority": False, "production_authority": False}
    progress = {**progress_commitment, "artifact_hash": hash_payload(progress_commitment)}
    write(output / "local_specialist_role_recovery_run_raw.json", recovery_run)
    write(output / "local_specialist_role_run_recovered.json", recovered_run)
    write(output / "local_specialist_role_analysis_recovered.json", analysis)
    (output / "LOCAL_SPECIALIST_ROLE_ANALYSIS_RECOVERED.md").write_text(render_specialist_role_analysis(analysis), encoding="utf-8")
    write(output / "local_specialist_role_recovery_telemetry.json", telemetry)
    write(output / "local_specialist_role_recovery_progress.json", progress)
    print(json.dumps({"experiment_id": experiment_id, "recovery_task_count": recovery_plan["task_count"], "recovered_output_count": len(recovery_run["outputs"]), "recovery_failure_count": len(recovery_run["failures"]), "receipt_coverage": analysis["receipt_coverage"], "role_metrics": analysis["role_metrics"], "model_role_metrics": analysis["model_role_metrics"], "accounting": analysis["accounting"], "current_phase": progress["current_phase"], "coordinator_run_allowed": progress["coordinator_run_allowed"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
