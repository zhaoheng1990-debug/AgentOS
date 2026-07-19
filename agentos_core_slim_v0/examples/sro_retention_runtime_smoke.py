"""Deterministic end-to-end smoke for the provider-backed SRO retention runtime."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import ProviderCapabilityProfile, ProviderTaskRouter  # noqa: E402
from agentos_runtime import (  # noqa: E402
    SROCalibrationContract,
    SRORetentionRuntime,
    SRORetentionTask,
)


RETURN_PACK_NAME = "AgentOS_SRORetentionRuntime_ReturnPack_v0_2.zip"
HASH_B = "b" * 64


def _utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _hash_payload(payload: Any) -> str:
    return _hash_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


class StaticSROMatcher:
    def __init__(self) -> None:
        self.profile = ProviderCapabilityProfile(
            provider_id="scripted-sro-provider",
            model_id="scripted-sro-model",
            task_kinds=("graded_sro_retention_candidate_routing",),
            max_timeout_seconds=120,
        )
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        return {
            "result": {
                "route_probabilities": {
                    "DIRECT_REUSE": 0.82,
                    "LOCAL_RECONSTRUCTION": 0.08,
                    "OBSERVE": 0.03,
                    "REJECT": 0.03,
                    "REVISE": 0.04,
                },
                "uncertainty": 0.12,
                "drift_risk": 0.10,
                "negative_transfer_risk": 0.08,
                "structural_compatibility": 0.91,
                "role_compatibility": 0.90,
                "boundary_compatibility": 0.92,
                "interface_compatibility": 0.88,
                "trace_sufficiency": 0.94,
                "calibration_error": 0.03,
                "validity_state": "CURRENT",
                "confidence": 0.82,
                "evidence_refs": [task.allowed_evidence[0]],
            },
            "usage": {"total_tokens": 1},
            "provenance_refs": list(task.allowed_evidence),
        }


def _legacy_candidate() -> dict[str, Any]:
    return {
        "candidate_id": "legacy-sro-smoke",
        "scope": "project_scoped",
        "status": "ACCEPT_READY_WITH_EVIDENCE",
        "evidence_refs": ["evidence://legacy-sro-smoke"],
        "accept_decision_ref": "decision://legacy-sro-smoke",
        "replayable_evidence": True,
        "future_cbit_gain": "positive",
        "negative_transfer_risk": "low",
    }


def _revalidated_candidate(migration_hash: str) -> dict[str, Any]:
    return {
        "candidate_id": "legacy-sro-smoke",
        "legacy_source_hash": migration_hash,
        "scope": "project_scoped",
        "decision_status": "SUPPORTED_BOUNDED",
        "evidence_refs": ["evidence://legacy-sro-smoke", "evidence://provider-revalidation"],
        "support_path": "claim://legacy-sro-smoke -> evidence://provider-revalidation",
        "accept_decision_ref": "decision://provider-revalidation",
        "replayable_evidence": True,
        "future_cbit_gain_score": 0.9,
        "transferability": 0.8,
        "search_efficiency": 0.8,
        "residual_reduction": 0.9,
        "complexity": 0.2,
        "negative_transfer_score": 0.1,
        "scope_ambiguity": 0.1,
        "constraint_alignment": 0.9,
    }


def _manifest(output_dir: Path, status: str) -> dict[str, Any]:
    files = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in {"manifest.json", RETURN_PACK_NAME}:
            files.append(
                {
                    "path": path.relative_to(output_dir).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _hash_bytes(path.read_bytes()),
                }
            )
    payload = {"status": status, "created_at": _utc_now(), "files": files}
    payload["manifest_hash"] = _hash_payload(payload)
    _write_json(output_dir / "manifest.json", payload)
    return payload


def _return_pack(output_dir: Path) -> Path:
    path = output_dir / RETURN_PACK_NAME
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(output_dir.rglob("*")):
            if item.is_file() and item != path:
                archive.write(item, item.relative_to(output_dir).as_posix())
    return path


def run_smoke(output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    provider = StaticSROMatcher()
    router = ProviderTaskRouter([provider])
    runtime = SRORetentionRuntime(
        runtime_id="sro-retention-smoke",
        project_scope="project://sro-retention-smoke",
        matcher_router=router,
        workspace_root=output_dir / "runtime",
    )
    initial_migration = runtime.migrate_legacy_candidate(
        _legacy_candidate(),
        migration_authority_ref="kernel://sro-retention-smoke/migrate",
    )
    revalidated = runtime.revalidate_legacy_migration(
        initial_migration.migration_id,
        _revalidated_candidate(initial_migration.legacy_candidate_hash),
        kernel_authorization_ref="kernel://sro-retention-smoke/revalidate",
    )
    witness = runtime.reconstruct_migrated_witness(
        revalidated.migration_id,
        witness_id="PW-SRO-SMOKE-1",
        sro_address_ref="sro://smoke/bounded-role-structure",
        validity_boundary_ref="boundary://sro-smoke/current",
        reconstruction_ref="reconstruction://sro-smoke/local",
        authority_ref="authority://sro-smoke/kernel",
        privacy_boundary="reference_only_no_raw_chat",
        sealed_at="2026-07-19T13:00:00+00:00",
        evidence_refs=(
            "evidence://legacy-sro-smoke",
            "evidence://provider-revalidation",
            "evidence://witness-reconstruction",
        ),
        kernel_authorization_ref="kernel://sro-retention-smoke/reconstruct",
    )
    task = SRORetentionTask(
        task_id="task-sro-smoke-later-1",
        project_scope="project://sro-retention-smoke",
        objective="Route one reconstructed witness for a bounded later task.",
        context_ref="context://sro-smoke/later-1",
        constraint_field_ref="constraint://sro-smoke/later-1",
        evidence_refs=("evidence://later-task",),
    )
    calibration = SROCalibrationContract(
        matcher_id="matcher://sro-smoke-v1",
        matcher_version="1.0",
        calibration_ref="calibration://sro-smoke/frozen",
        calibration_status="FROZEN_PROJECT_SCOPED",
        evidence_scope="INTERNAL_PROJECT",
        evidence_refs=("evidence://sro-smoke-calibration",),
    )
    route = runtime.route_witness(witness.witness_id, task, calibration)
    prediction = runtime.seal_delayed_prediction(
        route.route_receipt_id,
        prediction_id="DR-SRO-SMOKE-1",
        sealed_at="2026-07-19T13:10:00+00:00",
        evidence_refs=(*route.evidence_refs, "evidence://sro-smoke-prediction"),
    )
    score = runtime.score_delayed_outcome(
        prediction.prediction_id,
        observed_route="DIRECT_REUSE",
        role_reconstruction_fidelity=0.9,
        negative_transfer_penalty=0.1,
        outcome_ref="outcome://sro-smoke-later-1",
        outcome_hash=HASH_B,
        revealed_at="2026-07-19T13:11:00+00:00",
        scoring_authority_ref="authority://sro-smoke/frozen-harness",
    )
    restarted = SRORetentionRuntime(
        runtime_id="sro-retention-smoke",
        project_scope="project://sro-retention-smoke",
        matcher_router=router,
        workspace_root=output_dir / "runtime",
    )
    replay = restarted.verify_replay()
    gates = {
        "legacy_record_waited_for_provider_revalidation": (
            initial_migration.candidate_state == "PENDING_PROVIDER_REVALIDATION"
        ),
        "revalidation_preceded_witness_registration": (
            revalidated.candidate_state == "PENDING_WITNESS_RECONSTRUCTION"
        ),
        "witness_bound_to_project": witness.project_scope_ref == task.project_scope,
        "provider_invocation_strongly_bound": (
            route.matcher_receipt["provider_invocation_receipt_hash"]
            == route.provider_invocation_receipt["receipt_hash"]
        ),
        "kernel_route_is_bounded": route.decision["route"] == "DIRECT_REUSE",
        "delayed_prediction_preceded_outcome": score.prediction_id == prediction.prediction_id,
        "restart_replay_valid": replay["valid"],
        "restart_state_complete": (
            len(restarted.snapshot().migrations) == 1
            and len(restarted.snapshot().witnesses) == 1
            and len(restarted.snapshot().route_receipts) == 1
            and restarted.snapshot().delayed_retrieval_replay["score_count"] == 1
        ),
        "no_global_or_production_authority": (
            route.as_dict()["global_memory_write_authority"] is False
            and route.as_dict()["production_activation"] is False
        ),
    }
    status = "PASS" if all(gates.values()) else "FAIL"
    result = {
        "smoke_id": "provider-backed-sro-retention-runtime-v0-2",
        "status": status,
        "created_at": _utc_now(),
        "gates": gates,
        "initial_migration": initial_migration.as_dict(),
        "revalidated_migration": revalidated.as_dict(),
        "witness": witness.as_dict(),
        "route_receipt": route.as_dict(),
        "delayed_prediction": prediction.as_dict(),
        "delayed_score": score.as_dict(),
        "restart_replay": replay,
        "provider_task_count": len(provider.tasks),
        "manifest_path": str(output_dir / "manifest.json"),
        "return_pack": str(output_dir / RETURN_PACK_NAME),
    }
    _write_json(output_dir / "sro_retention_smoke_result.json", result)
    _manifest(output_dir, status)
    _return_pack(output_dir)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_smoke(args.output_dir)
        print(json.dumps({"status": result["status"], "output_dir": str(args.output_dir)}, indent=2))
        return 0 if result["status"] == "PASS" else 1
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        failure = {"status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)}
        _write_json(args.output_dir / "sro_retention_smoke_failure.json", failure)
        print(json.dumps(failure, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
