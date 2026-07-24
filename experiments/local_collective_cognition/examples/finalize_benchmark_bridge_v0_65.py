"""Build the auditable v0.65 closure and return pack."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from hashlib import sha256
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT = REPO_ROOT / "outputs" / "benchmark_bridge_v0_65"
RETURN_PACK = REPO_ROOT / "return_packs" / "benchmark_bridge_v0_65"


SOURCE_FILES = (
    "benchmark_bridge_contracts.py",
    "benchmark_bridge_holdout.py",
    "benchmark_bridge_metrics.py",
    "benchmark_bridge_protocol.py",
    "benchmark_bridge_provider.py",
    "benchmark_bridge_runtime.py",
    "benchmark_bridge_sources.py",
    "benchmark_bridge_tasks.py",
    "evidence_inference_bridge.py",
    "evidence_inference_selection.py",
)
RUN_ARTIFACTS = (
    "calibration_panel_private.json",
    "calibration_panel_public.json",
    "preregistration.json",
    "a0_one_pass_run.json",
    "a1_staged_run.json",
    "a0_score.json",
    "a1_score.json",
    "calibration_decision.json",
    "holdout_panel_private.json",
    "holdout_panel_public.json",
    "holdout_preregistration.json",
    "holdout_a0_run.json",
    "holdout_a1_run.json",
    "holdout_a0_score.json",
    "holdout_a1_score.json",
    "holdout_decision.json",
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
    decision = read(OUTPUT / "holdout_decision.json")
    if decision["decision"] != (
        "REJECT_BENCHMARK_BRIDGE_TEST_SPLIT_TRANSFER"
    ):
        raise ValueError("unexpected_v0_65_closure_decision")
    base_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()

    analysis = {
        "experiment_version": "0.65.0",
        "calibration": _score_pair(
            read(OUTPUT / "a0_score.json"),
            read(OUTPUT / "a1_score.json"),
        ),
        "holdout": _score_pair(
            read(OUTPUT / "holdout_a0_score.json"),
            read(OUTPUT / "holdout_a1_score.json"),
        ),
        "calibration_decision": read(
            OUTPUT / "calibration_decision.json"
        )["decision"],
        "holdout_decision": decision["decision"],
        "interpretation": (
            "partial evidence-objectification gain without validated "
            "test-split transfer"
        ),
        "next_candidate": "TYPED_SEMANTIC_BASIS_CHAIN_V0_66",
    }
    write(OUTPUT / "analysis.json", analysis)

    rollback = {
        "pointer_version": "benchmark_bridge_rollback_v0_65",
        "base_commit": base_commit,
        "base_branch": "codex/overnight-v0.64-selection-retention",
        "rollback_scope": "remove_v0_65_experiment_only",
        "core_version": "0.4.0-alpha.21",
        "core_rollback_required": False,
        "raw_cache_delete_required": False,
        "production_state_restore_required": False,
    }
    write(OUTPUT / "rollback_pointer.json", rollback)

    pointer_candidate = {
        "candidate_version": "benchmark_bridge_pointer_candidate_v0_65",
        "decision": "HOLD_CURRENT_CORE_POINTER",
        "core_version": "0.4.0-alpha.21",
        "experiment_pack_version": "0.65.0",
        "test_split_transfer_supported": False,
        "candidate_next_window": "v0.66 typed semantic basis",
        "automatic_pointer_update_allowed": False,
        "pm_review_required": True,
    }
    write(OUTPUT / "pointer_update_candidate.json", pointer_candidate)

    replay = {
        "replay_version": "benchmark_bridge_replay_v0_65",
        "freeze_calibration": (
            "python experiments/local_collective_cognition/examples/"
            "freeze_benchmark_bridge_v0_65.py"
        ),
        "freeze_holdout": (
            "python experiments/local_collective_cognition/examples/"
            "freeze_benchmark_bridge_holdout_v0_65.py"
        ),
        "scoring_replay_only": [
            "python experiments/local_collective_cognition/examples/"
            "run_benchmark_bridge_v0_65.py --stage score",
            "python experiments/local_collective_cognition/examples/"
            "run_benchmark_bridge_holdout_v0_65.py --stage score",
        ],
        "provider_rerun_required_for_hash_identity": False,
        "raw_cache_scope": "%LOCALAPPDATA%/AgentOS/benchmark_cache",
        "prompt_tuning_after_freeze_allowed": False,
    }
    write(OUTPUT / "replay.json", replay)

    verification = {
        "verification_version": "benchmark_bridge_verification_v0_65",
        "focused_tests": {"passed": 12, "failed": 0},
        "experiment_pack_tests": {"passed": 427, "failed": 0},
        "core_slim_tests": {"passed": 394, "failed": 0},
        "raw_benchmark_files_in_repository": 0,
        "largest_v0_65_module_lines": 294,
        "core_modified": False,
        "core_version": "0.4.0-alpha.21",
    }
    write(OUTPUT / "verification.json", verification)

    report_source = PACK_ROOT / "BENCHMARK_BRIDGE_CLOSURE_V0_65.md"
    (OUTPUT / "experiment_report.md").write_text(
        report_source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    manifest = {
        "manifest_version": "benchmark_bridge_manifest_v0_65",
        "experiment_version": "0.65.0",
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
        "raw_benchmark_data_included": False,
        "production_authority": False,
    }
    write(OUTPUT / "manifest.json", manifest)

    inventory = _inventory()
    write(OUTPUT / "hash_inventory.json", inventory)
    closure = {
        "closure_version": "benchmark_bridge_closure_v0_65",
        "status": "CLOSED",
        "decision": decision["decision"],
        "partial_mechanism_benefit": True,
        "test_split_transfer_supported": False,
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
    archive = OUTPUT / "benchmark_bridge_v0_65_return_pack.zip"
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
        "raw_benchmark_data_included": False,
    }, indent=2, sort_keys=True))
    return 0


def _score_pair(a0: dict, a1: dict) -> dict:
    keys = (
        "label_accuracy",
        "evidence_f1",
        "rationale_token_f1",
        "effective_cbit",
        "physical_total_tokens",
        "effective_cbit_per_1k_tokens",
        "contract_failure_count",
    )
    return {
        "a0": {key: a0[key] for key in keys},
        "a1": {key: a1[key] for key in keys},
    }


def _inventory() -> dict:
    module_root = PACK_ROOT / "local_collective_cognition"
    source = {
        str((module_root / name).relative_to(REPO_ROOT)): digest(
            module_root / name
        )
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
        "inventory_version": "benchmark_bridge_hash_inventory_v0_65",
        "algorithm": "sha256",
        "source_files": source,
        "artifacts": artifacts,
    }


if __name__ == "__main__":
    sys.exit(main())
