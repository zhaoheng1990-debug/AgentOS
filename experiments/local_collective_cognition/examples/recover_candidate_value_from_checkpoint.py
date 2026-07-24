"""Recover v0.37 run metadata from its last immutable checkpoint."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.candidate_value_composition import (  # noqa: E402
    CONTRACT_VERSION,
    SCORE_MAP,
)
from local_collective_cognition.candidate_value_experiment import (  # noqa: E402
    RUNTIME_VERSION,
    analyze_candidate_value_experiment,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.runtime_escalation_policy import (  # noqa: E402
    POLICY_VERSION,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    output = REPO_ROOT / "outputs" / "candidate_value_v0_37"
    corpus = read(output / "candidate_value_corpus_frozen.json")
    preregistration = read(
        output / "candidate_value_preregistration.json"
    )
    progress = read(output / "candidate_value_progress.json")
    progress_commitment = {
        key: value for key, value in progress.items()
        if key != "artifact_hash"
    }
    if progress["artifact_hash"] != hash_payload(progress_commitment):
        raise ValueError("progress_hash_invalid")
    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_trigger_policy_version": POLICY_VERSION,
        "source_value_contract_version": CONTRACT_VERSION,
        "source_score_map_hash": hash_payload(SCORE_MAP),
        "provider_id": "deepseek-candidate-value-v0-37",
        "model_id": "deepseek-v4-flash",
        "task_calls": progress["task_calls"],
        "raw_receipts": progress["raw_receipts"],
        "provisional_projections": progress["provisional_projections"],
        "final_projections": progress["final_projections"],
        "trigger_receipts": progress["trigger_receipts"],
        "candidate_pools": progress["candidate_pools"],
        "blinded_candidate_views": progress[
            "blinded_candidate_views"
        ],
        "value_receipts": progress["value_receipts"],
        "composition_receipts": progress["composition_receipts"],
        "failures": progress["failures"],
        "raw_receipts_preserved_before_projection": True,
        "private_truth_exposed": False,
        "candidate_sources_visible_to_value_provider": False,
        "pool_candidate_ids_visible_to_value_provider": False,
        "value_provider_selects_final_candidates": False,
        "trigger_policy_retuned_from_v0_33": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    run = {**commitment, "run_hash": hash_payload(commitment)}
    analysis = analyze_candidate_value_experiment(
        corpus=corpus, preregistration=preregistration, run=run
    )
    write(output / "candidate_value_run.json", run)
    write(output / "candidate_value_analysis.json", analysis)
    recovery_commitment = {
        "recovery_version": "candidate_value_checkpoint_recovery_v0_37",
        "source_progress_hash": progress["artifact_hash"],
        "recovered_run_hash": run["run_hash"],
        "recovered_analysis_hash": analysis["artifact_hash"],
        "completed_task_count": progress["completed_task_count"],
        "provider_calls_replayed": False,
        "provider_evidence_changed": False,
    }
    write(output / "checkpoint_recovery.json", {
        **recovery_commitment,
        "artifact_hash": hash_payload(recovery_commitment),
    })
    print(json.dumps({
        "recovered_from_checkpoint": True,
        "completed_task_count": progress["completed_task_count"],
        "decision": analysis["decision"],
        "state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
