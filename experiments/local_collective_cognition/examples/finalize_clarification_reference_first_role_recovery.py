"""Finalize assignment-level analysis after bounded local role recovery."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_reference_first_role_analysis import (  # noqa: E402
    build_specialist_recovery_analysis,
    render_specialist_role_analysis,
    validate_specialist_recovery_analysis,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


OUTPUT = REPO_ROOT / "outputs" / "clarification_reference_first_v0_15"


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding="utf-8"))


def write(name, value):
    (OUTPUT / name).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    values = {
        "corpus_artifact": read("private_reference_first_corpus.json"),
        "frozen_reference": read("reference_first_model_panel_reference_candidate.json"),
        "role_plan": read("local_specialist_role_plan.json"),
        "initial_run": read("local_specialist_role_run.json"),
        "recovery_plan": read("local_specialist_role_recovery_plan.json"),
        "recovery_run": read("local_specialist_role_recovery_run_raw.json"),
    }
    analysis = build_specialist_recovery_analysis(**values)
    validate_specialist_recovery_analysis(analysis, **values)
    progress_commitment = {
        "progress_version": "clarification_reference_first_role_recovery_final_v0_15",
        "source_corpus_hash": values["corpus_artifact"]["artifact_hash"],
        "frozen_reference_hash": values["frozen_reference"]["artifact_hash"],
        "role_recovery_analysis_hash": analysis["artifact_hash"],
        "current_phase": analysis["candidate_state"],
        "strict_receipt_coverage": analysis["strict_receipt_coverage"],
        "local_role_receipts_frozen": False,
        "coordinator_run_allowed": False,
        "further_prompt_only_recovery_allowed": False,
        "reference_revision_allowed": False,
        "next_required_evidence": analysis["next_required_evidence"],
        "ground_truth_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    progress = {**progress_commitment, "artifact_hash": hash_payload(progress_commitment)}
    write("local_specialist_role_recovery_analysis_final.json", analysis)
    (OUTPUT / "LOCAL_SPECIALIST_ROLE_RECOVERY_ANALYSIS_FINAL.md").write_text(render_specialist_role_analysis(analysis), encoding="utf-8")
    write("local_specialist_role_recovery_final_progress.json", progress)
    print(json.dumps({
        "analysis_hash": analysis["artifact_hash"],
        "strict_receipt_coverage": analysis["strict_receipt_coverage"],
        "structural_metrics_by_model_role": analysis["structural_metrics_by_model_role"],
        "semantic_metrics_by_model_role": analysis["semantic_metrics_by_model_role"],
        "role_metrics_on_structurally_valid_receipts": analysis["role_metrics_on_structurally_valid_receipts"],
        "total_accounting": analysis["total_accounting"],
        "tokens_per_accepted_receipt": analysis["tokens_per_accepted_receipt"],
        "current_phase": progress["current_phase"],
        "coordinator_run_allowed": progress["coordinator_run_allowed"],
        "further_prompt_only_recovery_allowed": progress["further_prompt_only_recovery_allowed"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
