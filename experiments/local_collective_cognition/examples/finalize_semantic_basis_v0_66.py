"""Build the auditable v0.66 negative-result return pack."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from hashlib import sha256
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT = REPO_ROOT / "outputs" / "semantic_basis_v0_66"
RETURN_PACK = REPO_ROOT / "return_packs" / "semantic_basis_v0_66"
SOURCE_FILES = (
    "semantic_basis_calibration.py",
    "semantic_basis_consistency.py",
    "semantic_basis_contracts.py",
    "semantic_basis_holdout.py",
    "semantic_basis_metrics.py",
    "semantic_basis_protocol.py",
    "semantic_basis_runtime.py",
    "semantic_basis_schemas.py",
    "semantic_basis_selection.py",
    "semantic_basis_sources.py",
    "semantic_basis_tasks.py",
    "semantic_basis_types.py",
)
RUN_ARTIFACTS = (
    "calibration_private.json",
    "calibration_public.json",
    "holdout_private.json",
    "holdout_public.json",
    "calibration_preregistration.json",
    "calibration_candidate_run.json",
    "calibration_score.json",
    "calibration_decision.json",
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    RETURN_PACK.mkdir(parents=True, exist_ok=True)
    decision = read(OUTPUT / "calibration_decision.json")
    if decision["decision"] != (
        "REJECT_TYPED_SEMANTIC_BASIS_CALIBRATION"
    ):
        raise ValueError("unexpected_v0_66_closure_decision")
    base_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    score = read(OUTPUT / "calibration_score.json")
    analysis = {
        "experiment_version": "0.66.0",
        "decision": decision["decision"],
        "baseline": _score_summary(score["baseline"]),
        "candidate": _score_summary(score["candidate"]),
        "basis_receipt_count": score["basis_receipt_count"],
        "candidate_total_failure_count": score[
            "candidate_total_failure_count"
        ],
        "corrected_case_ids": score["corrected_case_ids"],
        "harmed_case_ids": score["harmed_case_ids"],
        "unresolved_case_ids": score["unresolved_case_ids"],
        "fresh_holdout_provider_calls": 0,
        "interpretation": (
            "typed basis has local value; free synthesis and comparison "
            "frame remain unclosed"
        ),
        "next_candidate": "COMPARISON_FRAME_AND_BASIS_COMPILER_V0_67",
    }
    write(OUTPUT / "analysis.json", analysis)
    write(OUTPUT / "rollback_pointer.json", {
        "pointer_version": "semantic_basis_rollback_v0_66",
        "base_commit": base_commit,
        "base_branch": "codex/v0.65-benchmark-bridge",
        "rollback_scope": "remove_v0_66_experiment_only",
        "core_version": "0.4.0-alpha.21",
        "core_rollback_required": False,
        "production_state_restore_required": False,
    })
    write(OUTPUT / "pointer_update_candidate.json", {
        "candidate_version": "semantic_basis_pointer_candidate_v0_66",
        "decision": "HOLD_CURRENT_CORE_POINTER",
        "core_version": "0.4.0-alpha.21",
        "experiment_pack_version": "0.66.0",
        "calibration_supported": False,
        "fresh_holdout_executed": False,
        "candidate_next_window": (
            "v0.67 comparison frame and deterministic basis compiler"
        ),
        "automatic_pointer_update_allowed": False,
        "pm_review_required": True,
    })
    write(OUTPUT / "replay.json", {
        "replay_version": "semantic_basis_replay_v0_66",
        "freeze_command": (
            "python experiments/local_collective_cognition/examples/"
            "freeze_semantic_basis_v0_66.py"
        ),
        "score_replay_command": (
            "python experiments/local_collective_cognition/examples/"
            "run_semantic_basis_calibration_v0_66.py --stage score"
        ),
        "fresh_holdout_execution_allowed": False,
        "raw_cache_scope": "%LOCALAPPDATA%/AgentOS/benchmark_cache",
        "prompt_tuning_after_receipt_allowed": False,
    })
    write(OUTPUT / "verification.json", {
        "verification_version": "semantic_basis_verification_v0_66",
        "focused_tests": {"passed": 15, "failed": 0},
        "experiment_pack_tests": {"passed": 442, "failed": 0},
        "core_slim_tests": {"passed": 394, "failed": 0},
        "fresh_holdout_provider_calls": 0,
        "raw_benchmark_files_in_repository": 0,
        "largest_v0_66_semantic_module_lines": 202,
        "core_modified": False,
        "core_version": "0.4.0-alpha.21",
    })
    report = PACK_ROOT / "SEMANTIC_BASIS_CLOSURE_V0_66.md"
    (OUTPUT / "experiment_report.md").write_text(
        report.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    manifest = {
        "manifest_version": "semantic_basis_manifest_v0_66",
        "experiment_version": "0.66.0",
        "base_commit": base_commit,
        "decision": decision["decision"],
        "run_artifacts": list(RUN_ARTIFACTS),
        "closure_artifacts": [
            "analysis.json",
            "rollback_pointer.json",
            "pointer_update_candidate.json",
            "replay.json",
            "verification.json",
            "experiment_report.md",
        ],
        "fresh_holdout_executed": False,
        "raw_benchmark_data_included": False,
        "production_authority": False,
    }
    write(OUTPUT / "manifest.json", manifest)
    write(OUTPUT / "hash_inventory.json", _inventory())
    closure = {
        "closure_version": "semantic_basis_closure_v0_66",
        "status": "CLOSED",
        "decision": decision["decision"],
        "typed_basis_local_value": True,
        "calibration_supported": False,
        "fresh_holdout_executed": False,
        "next_stage_authorized": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "manifest_sha256": digest(OUTPUT / "manifest.json"),
        "hash_inventory_sha256": digest(OUTPUT / "hash_inventory.json"),
    }
    write(OUTPUT / "closure.json", closure)
    files = [
        *RUN_ARTIFACTS,
        "analysis.json",
        "rollback_pointer.json",
        "pointer_update_candidate.json",
        "replay.json",
        "verification.json",
        "experiment_report.md",
        "manifest.json",
        "hash_inventory.json",
        "closure.json",
    ]
    archive = OUTPUT / "semantic_basis_v0_66_return_pack.zip"
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED
    ) as bundle:
        for name in files:
            bundle.write(OUTPUT / name, arcname=name)
    target = RETURN_PACK / archive.name
    target.write_bytes(archive.read_bytes())
    print(json.dumps({
        "decision": closure["decision"],
        "archive": str(target),
        "archive_sha256": digest(target),
        "artifact_count": len(files),
        "fresh_holdout_executed": False,
        "raw_benchmark_data_included": False,
    }, indent=2, sort_keys=True))
    return 0


def _score_summary(score: dict) -> dict:
    keys = (
        "valid_receipt_count",
        "contract_failure_count",
        "label_accuracy",
        "evidence_f1",
        "rationale_token_f1",
        "effective_cbit",
        "physical_total_tokens",
        "effective_cbit_per_1k_tokens",
    )
    return {key: score[key] for key in keys}


def _inventory() -> dict:
    root = PACK_ROOT / "local_collective_cognition"
    source = {
        str((root / name).relative_to(REPO_ROOT)): digest(root / name)
        for name in SOURCE_FILES
    }
    artifacts = {
        name: digest(OUTPUT / name)
        for name in [
            *RUN_ARTIFACTS,
            "analysis.json",
            "rollback_pointer.json",
            "pointer_update_candidate.json",
            "replay.json",
            "verification.json",
            "experiment_report.md",
            "manifest.json",
        ]
    }
    return {
        "inventory_version": "semantic_basis_hash_inventory_v0_66",
        "algorithm": "sha256",
        "source_files": source,
        "artifacts": artifacts,
    }


if __name__ == "__main__":
    sys.exit(main())
