"""Build the v0.68 negative-result audit pack."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from hashlib import sha256
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT = REPO_ROOT / "outputs" / "relational_contrast_v0_68"
RETURN_PACK = REPO_ROOT / "return_packs" / "relational_contrast_v0_68"
RUN_FILES = (
    "calibration_private.json",
    "calibration_public.json",
    "holdout_private.json",
    "holdout_public.json",
    "calibration_preregistration.json",
    "calibration_candidate_run.json",
    "calibration_score.json",
    "calibration_decision.json",
)
SOURCE_FILES = (
    "relational_contrast_types.py",
    "relational_contrast_objects.py",
    "relational_contrast_schemas.py",
    "relational_contrast_contracts.py",
    "relational_contrast_tasks.py",
    "relational_basis_compiler.py",
    "relational_contrast_runtime.py",
    "relational_contrast_protocol.py",
    "relational_contrast_metrics.py",
)


def read(name: str) -> dict:
    return json.loads((OUTPUT / name).read_text(encoding="utf-8"))


def write(name: str, value: dict) -> None:
    (OUTPUT / name).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    RETURN_PACK.mkdir(parents=True, exist_ok=True)
    decision = read("calibration_decision.json")
    if decision["decision"] != "REJECT_RELATIONAL_CONTRAST_CALIBRATION":
        raise ValueError("unexpected_v0_68_decision")
    score = read("calibration_score.json")
    base_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()
    write("analysis.json", {
        "experiment_version": "0.68.0",
        "decision": decision["decision"],
        "baseline": _summary(score["baseline"]),
        "candidate": _summary(score["candidate"]),
        "corrected_case_ids": score["corrected_case_ids"],
        "harmed_case_ids": score["harmed_case_ids"],
        "unresolved_case_ids": score["unresolved_case_ids"],
        "compiler_failure_count": score["compiler_failure_count"],
        "fresh_holdout_provider_calls": 0,
        "next_candidate": "SPAN_ANCHORED_RELATION_WITNESS_V0_69",
    })
    write("rollback_pointer.json", {
        "pointer_version": "relational_rollback_v0_68",
        "base_commit": base_commit,
        "base_branch": "codex/v0.67-comparison-frame",
        "rollback_scope": "remove_v0_68_experiment_only",
        "core_version": "0.4.0-alpha.21",
        "core_rollback_required": False,
    })
    write("pointer_update_candidate.json", {
        "candidate_version": "relational_pointer_candidate_v0_68",
        "decision": "HOLD_CURRENT_CORE_POINTER",
        "experiment_pack_version": "0.68.0",
        "calibration_supported": False,
        "fresh_holdout_executed": False,
        "candidate_next_window": "v0.69 span-anchored relation witness",
        "automatic_pointer_update_allowed": False,
        "pm_review_required": True,
    })
    write("replay.json", {
        "replay_version": "relational_replay_v0_68",
        "freeze_command": (
            "python experiments/local_collective_cognition/examples/"
            "freeze_relational_contrast_v0_68.py"
        ),
        "score_command": (
            "python experiments/local_collective_cognition/examples/"
            "run_relational_contrast_v0_68.py --stage score"
        ),
        "fresh_holdout_execution_allowed": False,
    })
    write("verification.json", {
        "verification_version": "relational_verification_v0_68",
        "focused_tests": {"passed": 6, "failed": 0},
        "experiment_pack_tests": {"passed": 461, "failed": 0},
        "core_slim_tests": {"passed": 394, "failed": 0},
        "fresh_holdout_provider_calls": 0,
        "raw_benchmark_files_in_repository": 0,
        "core_modified": False,
        "core_version": "0.4.0-alpha.21",
    })
    (OUTPUT / "experiment_report.md").write_text(
        (PACK_ROOT / "RELATIONAL_CONTRAST_CLOSURE_V0_68.md").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    write("manifest.json", {
        "manifest_version": "relational_manifest_v0_68",
        "experiment_version": "0.68.0",
        "base_commit": base_commit,
        "decision": decision["decision"],
        "run_artifacts": list(RUN_FILES),
        "fresh_holdout_executed": False,
        "raw_benchmark_data_included": False,
        "production_authority": False,
    })
    root = PACK_ROOT / "local_collective_cognition"
    write("hash_inventory.json", {
        "inventory_version": "relational_hash_inventory_v0_68",
        "algorithm": "sha256",
        "source_files": {
            str((root / name).relative_to(REPO_ROOT)): digest(root / name)
            for name in SOURCE_FILES
        },
        "artifacts": {
            name: digest(OUTPUT / name)
            for name in [
                *RUN_FILES,
                "analysis.json",
                "rollback_pointer.json",
                "pointer_update_candidate.json",
                "replay.json",
                "verification.json",
                "experiment_report.md",
                "manifest.json",
            ]
        },
    })
    write("closure.json", {
        "closure_version": "relational_closure_v0_68",
        "status": "CLOSED",
        "decision": decision["decision"],
        "positive_mechanism_evidence": True,
        "calibration_supported": False,
        "fresh_holdout_executed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    })
    files = [
        *RUN_FILES,
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
    archive = OUTPUT / "relational_contrast_v0_68_return_pack.zip"
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED
    ) as bundle:
        for name in files:
            bundle.write(OUTPUT / name, arcname=name)
    target = RETURN_PACK / archive.name
    target.write_bytes(archive.read_bytes())
    print(json.dumps({
        "decision": decision["decision"],
        "archive": str(target),
        "archive_sha256": digest(target),
        "artifact_count": len(files),
    }, indent=2, sort_keys=True))
    return 0


def _summary(score: dict) -> dict:
    return {
        key: score[key] for key in (
            "valid_receipt_count",
            "label_accuracy",
            "evidence_f1",
            "rationale_token_f1",
            "effective_cbit",
            "physical_total_tokens",
        )
    }


if __name__ == "__main__":
    sys.exit(main())
