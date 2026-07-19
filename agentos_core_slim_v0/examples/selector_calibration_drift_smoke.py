"""End-to-end smoke from Selector prediction through execution-backed calibration."""

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

from agentos_kernel import (  # noqa: E402
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    SelectorCalibrationThresholds,
)
from agentos_runtime import (  # noqa: E402
    ContextualPolicyRepository,
    SelectionFeedbackRepository,
    SelectorCalibrationRuntime,
)
from examples.selection_execution_feedback_bridge_smoke import run_smoke as run_feedback_smoke  # noqa: E402


RETURN_PACK_NAME = "AgentOS_SelectorCalibrationDrift_ReturnPack_v0_1.zip"


def _utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


class CalibrationSmokeProvider:
    def __init__(self) -> None:
        self.profile = ProviderCapabilityProfile(
            provider_id="scripted-selector-calibration-provider",
            model_id="scripted-selector-calibration-model",
            task_kinds=("selector_calibration_drift_assessment",),
            max_timeout_seconds=120,
        )
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        insufficient = task.inputs["calibration_profile"]["mechanical_state"] == "INSUFFICIENT_HISTORY"
        result = {
            "diagnostic_state": "INSUFFICIENT_HISTORY" if insufficient else "NO_SEMANTIC_DRIFT",
            "drift_drivers": [],
            "recommended_action": "COLLECT_MORE" if insufficient else "KEEP_CURRENT_CALIBRATION",
            "uncertainty": 0.20,
            "rationale": "exact-profile diagnosis over two independently sourced Harness outcomes",
            "evidence_refs": [task.allowed_evidence[0]],
        }
        return {
            "result": result,
            "usage": {"total_tokens": 12},
            "provenance_refs": list(task.allowed_evidence),
        }


def _manifest(output_dir: Path, status: str) -> dict[str, Any]:
    files = []
    excluded = {output_dir / "manifest.json", output_dir / RETURN_PACK_NAME}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path not in excluded:
            files.append(
                {
                    "path": path.relative_to(output_dir).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path.read_bytes()).hexdigest(),
                }
            )
    payload = {"status": status, "created_at": _utc_now(), "files": files}
    payload["manifest_hash"] = _hash_payload(payload)
    _write_json(output_dir / "manifest.json", payload)
    return payload


def _return_pack(output_dir: Path) -> Path:
    target = output_dir / RETURN_PACK_NAME
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path != target:
                archive.write(path, path.relative_to(output_dir).as_posix())
    return target


def run_smoke(output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source_dir = output_dir / "feedback-source"
    source = run_feedback_smoke(source_dir)
    project_scope = source["initial_selection"]["project_scope"]
    selection_repo = ContextualPolicyRepository(
        runtime_id="life-feedback-selector-selector-initial",
        project_scope=project_scope,
        workspace_root=source_dir / "selector-initial",
    )
    feedback_repo = SelectionFeedbackRepository(
        runtime_id="life-selection-feedback-bridge",
        project_scope=project_scope,
        workspace_root=source_dir / "feedback-runtime",
    )
    selection = selection_repo.selection("life-feedback-initial")
    first_feedback = feedback_repo.receipt("life-feedback-run-1")
    second_feedback = feedback_repo.receipt("life-feedback-run-2")
    assert selection is not None and first_feedback is not None and second_feedback is not None
    provider = CalibrationSmokeProvider()
    thresholds = SelectorCalibrationThresholds(
        threshold_ref="threshold://selector-calibration/life-smoke-v0-1",
        cbit_mae_watch=0.20,
        cbit_mae_drift=0.30,
        cost_mae_watch=0.20,
        cost_mae_drift=0.30,
        absolute_bias_watch=0.20,
        absolute_bias_drift=0.30,
    )
    runtime = SelectorCalibrationRuntime(
        runtime_id="life-selector-calibration",
        project_scope=project_scope,
        provider_router=ProviderTaskRouter([provider]),
        workspace_root=output_dir / "calibration-runtime",
        thresholds=thresholds,
    )
    first = runtime.observe(
        calibration_id="life-calibration-1",
        selection=selection,
        feedback=first_feedback,
        kernel_authorization_ref="kernel://life-selector-calibration/1",
    )
    second = runtime.observe(
        calibration_id="life-calibration-2",
        selection=selection,
        feedback=second_feedback,
        kernel_authorization_ref="kernel://life-selector-calibration/2",
    )
    restarted = SelectorCalibrationRuntime(
        runtime_id="life-selector-calibration",
        project_scope=project_scope,
        provider_router=ProviderTaskRouter([CalibrationSmokeProvider()]),
        workspace_root=output_dir / "calibration-runtime",
        thresholds=thresholds,
    )
    gates = {
        "source_feedback_smoke_passed": source["status"] == "PASS",
        "prediction_and_feedback_hashes_bound": all(
            receipt.observation.selection_receipt_hash == selection.receipt_hash
            and receipt.observation.feedback_receipt_hash == feedback.receipt_hash
            for receipt, feedback in ((first, first_feedback), (second, second_feedback))
        ),
        "first_observation_withholds_trust": first.kernel_decision.final_state == "INSUFFICIENT_HISTORY",
        "two_independent_sources_close_profile": (
            second.profile.observation_count == 2
            and second.profile.independent_source_count == 2
            and second.kernel_decision.final_state == "CALIBRATED"
        ),
        "revision_lineage_is_exact": second.supersedes_receipt_hash == first.receipt_hash,
        "provider_support_is_profile_bound": (
            len(provider.tasks) == 2
            and second.profile.evidence_ref in second.provider_judgment.evidence_refs
        ),
        "restart_replay_valid": restarted.verify_replay()["valid"],
        "no_global_or_production_authority": all(
            not item.as_dict()["global_policy_authority"]
            and not item.as_dict()["production_activation"]
            for item in (first, second)
        ),
    }
    status = "PASS" if all(gates.values()) else "FAIL"
    result = {
        "smoke_id": "selector-calibration-drift-v0-1",
        "status": status,
        "created_at": _utc_now(),
        "gates": gates,
        "first_calibration": first.as_dict(),
        "second_calibration": second.as_dict(),
        "restart_replay": restarted.verify_replay(),
        "thresholds": thresholds.as_dict(),
        "provider_call_count": len(provider.tasks),
        "manifest_path": str(output_dir / "manifest.json"),
        "return_pack": str(output_dir / RETURN_PACK_NAME),
    }
    _write_json(output_dir / "selector_calibration_smoke_result.json", result)
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
        _write_json(args.output_dir / "selector_calibration_smoke_failure.json", failure)
        print(json.dumps(failure, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
