"""Recover v0.36 run metadata from its last immutable checkpoint."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.candidate_pool_arbitration import (  # noqa: E402
    CONTRACT_VERSION,
)
from local_collective_cognition.independent_arbitration_experiment import (  # noqa: E402
    RUNTIME_VERSION,
    analyze_independent_arbitration_experiment,
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
    output = REPO_ROOT / "outputs" / "independent_arbitration_v0_36"
    corpus = read(output / "independent_arbitration_corpus_frozen.json")
    preregistration = read(
        output / "independent_arbitration_preregistration.json"
    )
    progress = read(output / "independent_arbitration_progress.json")
    commitment = {
        key: value for key, value in progress.items()
        if key != "artifact_hash"
    }
    if progress["artifact_hash"] != hash_payload(commitment):
        raise ValueError("progress_hash_invalid")
    run_commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_trigger_policy_version": POLICY_VERSION,
        "source_arbitration_contract_version": CONTRACT_VERSION,
        "provider_id": "deepseek-independent-arbitration-v0-36",
        "model_id": "deepseek-v4-flash",
        "task_calls": progress["task_calls"],
        "raw_receipts": progress["raw_receipts"],
        "provisional_projections": progress["provisional_projections"],
        "final_projections": progress["final_projections"],
        "trigger_receipts": progress["trigger_receipts"],
        "candidate_pools": progress["candidate_pools"],
        "selection_receipts": progress["selection_receipts"],
        "arbitration_receipts": progress["arbitration_receipts"],
        "failures": progress["failures"],
        "raw_receipts_preserved_before_projection": True,
        "private_truth_exposed": False,
        "counterproposal_sees_provisional_candidates": False,
        "counterproposal_sees_trigger_diagnostics": False,
        "arbiter_candidate_generation_allowed": False,
        "trigger_policy_retuned_from_v0_33": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    run = {
        **run_commitment,
        "run_hash": hash_payload(run_commitment),
    }
    analysis = analyze_independent_arbitration_experiment(
        corpus=corpus, preregistration=preregistration, run=run
    )
    write(output / "independent_arbitration_run.json", run)
    write(output / "independent_arbitration_analysis.json", analysis)
    recovery_commitment = {
        "recovery_version": (
            "independent_arbitration_checkpoint_recovery_v0_36"
        ),
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
        "run_hash": run["run_hash"],
        "decision": analysis["decision"],
        "state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
