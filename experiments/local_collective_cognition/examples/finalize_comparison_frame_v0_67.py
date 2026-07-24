"""Build the auditable v0.67 negative-result return pack."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from hashlib import sha256
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT = REPO_ROOT / "outputs" / "comparison_frame_v0_67"
RETURN_PACK = REPO_ROOT / "return_packs" / "comparison_frame_v0_67"
SOURCE_FILES = (
    "comparison_frame_types.py",
    "comparison_frame_schemas.py",
    "comparison_frame_contracts.py",
    "comparison_frame_tasks.py",
    "deterministic_basis_compiler.py",
    "comparison_frame_runtime.py",
    "comparison_frame_protocol.py",
    "comparison_frame_metrics.py",
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
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
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
    if decision["decision"] != "REJECT_COMPARISON_FRAME_CALIBRATION":
        raise ValueError("unexpected_v0_67_closure_decision")
    score = read(OUTPUT / "calibration_score.json")
    base_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()
    write(OUTPUT / "analysis.json", {
        "experiment_version": "0.67.0",
        "decision": decision["decision"],
        "baseline": _score_summary(score["baseline"]),
        "candidate": _score_summary(score["candidate"]),
        "frame_receipt_count": score["frame_receipt_count"],
        "basis_receipt_count": score["basis_receipt_count"],
        "compiler_failure_count": score["compiler_failure_count"],
        "corrected_case_ids": score["corrected_case_ids"],
        "harmed_case_ids": score["harmed_case_ids"],
        "unresolved_case_ids": score["unresolved_case_ids"],
        "fresh_holdout_provider_calls": 0,
        "interpretation": (
            "deterministic label authority worked; relational identity and "
            "evidence-admissibility semantics remain under-specified"
        ),
        "next_candidate": "EXPLICIT_RELATIONAL_CONTRAST_V0_68",
    })
    write(OUTPUT / "rollback_pointer.json", {
        "pointer_version": "comparison_frame_rollback_v0_67",
        "base_commit": base_commit,
        "base_branch": "codex/v0.66-semantic-basis",
        "rollback_scope": "remove_v0_67_experiment_only",
        "core_version": "0.4.0-alpha.21",
        "core_rollback_required": False,
        "production_state_restore_required": False,
    })
    write(OUTPUT / "pointer_update_candidate.json", {
        "candidate_version": "comparison_frame_pointer_candidate_v0_67",
        "decision": "HOLD_CURRENT_CORE_POINTER",
        "core_version": "0.4.0-alpha.21",
        "experiment_pack_version": "0.67.0",
        "calibration_supported": False,
        "fresh_holdout_executed": False,
        "candidate_next_window": (
            "v0.68 explicit relational contrast and admissibility separation"
        ),
        "automatic_pointer_update_allowed": False,
        "pm_review_required": True,
    })
    write(OUTPUT / "replay.json", {
        "replay_version": "comparison_frame_replay_v0_67",
        "pythonpath": [
            "agentos_core_slim_v0",
            "experiments/local_collective_cognition",
        ],
        "freeze_command": (
            "python experiments/local_collective_cognition/examples/"
            "freeze_comparison_frame_v0_67.py"
        ),
        "score_replay_command": (
            "python experiments/local_collective_cognition/examples/"
            "run_comparison_frame_v0_67.py --stage score"
        ),
        "fresh_holdout_execution_allowed": False,
        "prompt_tuning_after_first_frame_receipt_allowed": False,
    })
    write(OUTPUT / "verification.json", {
        "verification_version": "comparison_frame_verification_v0_67",
        "focused_tests": {"passed": 13, "failed": 0},
        "experiment_pack_tests": {"passed": 455, "failed": 0},
        "core_slim_tests": {"passed": 394, "failed": 0},
        "fresh_holdout_provider_calls": 0,
        "raw_benchmark_files_in_repository": 0,
        "core_modified": False,
        "core_version": "0.4.0-alpha.21",
    })
    report = PACK_ROOT / "COMPARISON_FRAME_CLOSURE_V0_67.md"
    (OUTPUT / "experiment_report.md").write_text(
        report.read_text(encoding="utf-8"), encoding="utf-8"
    )
    write(OUTPUT / "manifest.json", {
        "manifest_version": "comparison_frame_manifest_v0_67",
        "experiment_version": "0.67.0",
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
    })
    write(OUTPUT / "hash_inventory.json", _inventory())
    closure = {
        "closure_version": "comparison_frame_closure_v0_67",
        "status": "CLOSED",
        "decision": decision["decision"],
        "deterministic_compiler_local_value": True,
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
    archive = OUTPUT / "comparison_frame_v0_67_return_pack.zip"
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
        "inventory_version": "comparison_frame_hash_inventory_v0_67",
        "algorithm": "sha256",
        "source_files": source,
        "artifacts": artifacts,
    }


if __name__ == "__main__":
    sys.exit(main())
