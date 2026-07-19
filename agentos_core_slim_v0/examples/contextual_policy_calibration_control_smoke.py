"""End-to-end smoke for calibration-controlled contextual policy selection."""

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

from agentos_kernel import ProviderTaskRouter, SelectorCalibrationThresholds  # noqa: E402
from agentos_runtime import (  # noqa: E402
    ContextualOrganizationPolicyRuntime,
    ContextualPolicyRepository,
    SelectionExecutionFeedbackBridge,
    SelectorCalibrationRuntime,
)
from examples.cognitive_team_execution_project_source_smoke import (  # noqa: E402
    _build_runtime,
    load_life_case,
)
from examples.selection_execution_feedback_bridge_smoke import (  # noqa: E402
    DynamicPolicyProvider,
    _budget,
    _problem,
    _risk,
    _selection_registry,
    run_smoke as run_feedback_smoke,
)
from examples.selector_calibration_drift_smoke import CalibrationSmokeProvider  # noqa: E402


RETURN_PACK_NAME = "AgentOS_ContextualPolicyCalibrationControl_ReturnPack_v0_1.zip"


def _utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _manifest(output_dir: Path, status: str) -> dict[str, Any]:
    excluded = {output_dir / "manifest.json", output_dir / RETURN_PACK_NAME}
    files = []
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


def _thresholds(mode: str):
    if mode == "WATCH":
        return None
    if mode == "CALIBRATED":
        return SelectorCalibrationThresholds(
            threshold_ref="threshold://selector-control/calibrated",
            cbit_mae_watch=0.20,
            cbit_mae_drift=0.30,
            cost_mae_watch=0.20,
            cost_mae_drift=0.30,
            absolute_bias_watch=0.20,
            absolute_bias_drift=0.30,
        )
    return SelectorCalibrationThresholds(
        threshold_ref="threshold://selector-control/drifted",
        cbit_mae_watch=0.01,
        cbit_mae_drift=0.03,
        cost_mae_watch=0.01,
        cost_mae_drift=0.03,
        absolute_bias_watch=0.01,
        absolute_bias_drift=0.03,
    )


def _calibration_source(
    *,
    mode: str,
    project_scope: str,
    selection,
    feedback_bridge,
    output_dir: Path,
):
    runtime = SelectorCalibrationRuntime(
        runtime_id=f"life-selector-control-{mode.lower()}",
        project_scope=project_scope,
        provider_router=ProviderTaskRouter([CalibrationSmokeProvider()]),
        workspace_root=output_dir / f"calibration-{mode.lower()}",
        thresholds=_thresholds(mode),
    )
    first = runtime.observe(
        calibration_id=f"control-{mode.lower()}-1",
        selection=selection,
        feedback=feedback_bridge.receipt("life-feedback-run-1"),
        kernel_authorization_ref=f"kernel://selector-control/{mode.lower()}/1",
    )
    second = runtime.observe(
        calibration_id=f"control-{mode.lower()}-2",
        selection=selection,
        feedback=feedback_bridge.receipt("life-feedback-run-2"),
        kernel_authorization_ref=f"kernel://selector-control/{mode.lower()}/2",
    )
    return runtime, first, second


def _controlled_selection(
    *,
    label: str,
    case,
    registry,
    record_source,
    calibration_source,
    output_dir: Path,
):
    runtime = ContextualOrganizationPolicyRuntime(
        runtime_id=f"life-calibration-controlled-selector-{label}",
        project_scope=case.scope,
        registry=registry,
        provider_router=ProviderTaskRouter([DynamicPolicyProvider()]),
        workspace_root=output_dir / f"selector-{label}",
        record_source=record_source,
        calibration_source=calibration_source,
    )
    receipt = runtime.select_policy(
        selection_id=f"life-calibration-controlled-{label}",
        problem=_problem(case),
        evidence_tier="SCRIPTED_FIXTURE",
        budget=_budget(),
        risk=_risk(),
        kernel_authorization_ref=f"kernel://selector-control/{label}/select",
    )
    return runtime, receipt


def run_smoke(output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    feedback_dir = output_dir / "feedback-source"
    feedback_result = run_feedback_smoke(feedback_dir)
    project_scope = feedback_result["initial_selection"]["project_scope"]
    selection_repo = ContextualPolicyRepository(
        runtime_id="life-feedback-selector-selector-initial",
        project_scope=project_scope,
        workspace_root=feedback_dir / "selector-initial",
    )
    selection = selection_repo.selection("life-feedback-initial")
    feedback_bridge = SelectionExecutionFeedbackBridge(
        runtime_id="life-selection-feedback-bridge",
        project_scope=project_scope,
        workspace_root=feedback_dir / "feedback-runtime",
    )
    assert selection is not None
    sources = {}
    calibration_receipts = {}
    for mode in ("CALIBRATED", "WATCH", "DRIFTED"):
        source, first, second = _calibration_source(
            mode=mode,
            project_scope=project_scope,
            selection=selection,
            feedback_bridge=feedback_bridge,
            output_dir=output_dir,
        )
        sources[mode] = source
        calibration_receipts[mode] = (first, second)
    case = load_life_case()
    execution_runtime, _ = _build_runtime(
        case,
        output_dir / "selector-registry-source",
        "scripted",
        True,
    )
    registry, _ = _selection_registry(case, execution_runtime)
    selections = {}
    selector_replays = {}
    for mode, source in sources.items():
        selector, receipt = _controlled_selection(
            label=mode.lower(),
            case=case,
            registry=registry,
            record_source=feedback_bridge,
            calibration_source=source,
            output_dir=output_dir,
        )
        selections[mode] = receipt
        selector_replays[mode] = selector.verify_replay()
    calibrated = selections["CALIBRATED"]
    watch = selections["WATCH"]
    drifted = selections["DRIFTED"]
    drifted_eval = next(
        item for item in drifted.kernel_decision.candidate_evaluations if item.policy_id == "DYNAMIC_TEAM"
    )
    calibrated_control = next(
        item for item in calibrated.kernel_decision.calibration_controls if item.policy_id == "DYNAMIC_TEAM"
    )
    gates = {
        "feedback_source_passed": feedback_result["status"] == "PASS",
        "all_calibration_ledgers_replay": all(source.verify_replay()["valid"] for source in sources.values()),
        "first_observations_withhold_trust": all(
            pair[0].kernel_decision.final_state == "INSUFFICIENT_HISTORY"
            for pair in calibration_receipts.values()
        ),
        "calibrated_state_authorizes_matched_policy": (
            calibrated.kernel_decision.selected_policy_id == "DYNAMIC_TEAM"
            and calibrated.kernel_decision.activation_mode == "AUTHORIZED_PROJECT_SCOPED"
            and calibrated_control.prediction_trusted
        ),
        "watch_state_downgrades_to_exploration": (
            watch.kernel_decision.selected_policy_id == "DYNAMIC_TEAM"
            and watch.kernel_decision.activation_mode == "EXPLORATORY_TRIAL_ONLY"
            and not watch.kernel_decision.execution_authorized
        ),
        "drifted_state_hard_blocks_policy": (
            drifted_eval.eligibility == "BLOCKED"
            and "selector_calibration_drifted" in drifted_eval.hard_gate_failures
            and drifted.kernel_decision.selected_policy_id != "DYNAMIC_TEAM"
        ),
        "selection_receipt_binds_calibration_evidence": (
            calibrated_control.calibration_receipt_ref in calibrated.kernel_decision.evidence_refs
        ),
        "selector_replay_valid": all(item["valid"] for item in selector_replays.values()),
        "no_global_or_production_authority": all(
            not receipt.as_dict()["global_policy_authority"]
            and not receipt.as_dict()["production_activation"]
            for receipt in selections.values()
        ),
    }
    status = "PASS" if all(gates.values()) else "FAIL"
    result = {
        "smoke_id": "contextual-policy-calibration-control-v0-1",
        "status": status,
        "created_at": _utc_now(),
        "gates": gates,
        "calibration_states": {
            mode: pair[1].kernel_decision.final_state for mode, pair in calibration_receipts.items()
        },
        "controlled_selections": {mode: receipt.as_dict() for mode, receipt in selections.items()},
        "selector_replays": selector_replays,
        "manifest_path": str(output_dir / "manifest.json"),
        "return_pack": str(output_dir / RETURN_PACK_NAME),
    }
    _write_json(output_dir / "contextual_policy_calibration_control_smoke_result.json", result)
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
        _write_json(args.output_dir / "contextual_policy_calibration_control_smoke_failure.json", failure)
        print(json.dumps(failure, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
