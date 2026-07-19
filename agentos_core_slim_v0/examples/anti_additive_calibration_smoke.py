"""Deterministic smoke for calibrated Anti-Additive receipt authority."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from hashlib import sha256
from pathlib import Path
from typing import Any


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
    ANTI_ADDITIVE_TRIGGER_IDS,
    AntiAdditiveChangeCandidate,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    methodology_candidate_commitment,
)
from agentos_runtime import (  # noqa: E402
    AntiAdditiveBaselineEvolutionRuntime,
    AntiAdditiveCalibrationRuntime,
    AntiAdditiveMethodologyRuntime,
    LegacyRetentionMigrator,
)


RETURN_PACK_NAME = "AgentOS_AntiAdditiveCalibration_ReturnPack_v0_1.zip"
SCOPE = "project://anti-additive-calibration-smoke"
EVIDENCE = ("evidence://prediction", "evidence://harness-outcome")


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _hash_payload(payload: Any) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


class SmokeProvider:
    profile = ProviderCapabilityProfile(
        provider_id="anti-additive-calibration-smoke-provider",
        model_id="deterministic-calibration-smoke-model",
        task_kinds=("anti_additive_methodology_assessment",),
        max_timeout_seconds=120,
    )

    def invoke(self, task):
        return {
            "result": {
                "current_object_adequacy": "UNDERPOWERED",
                "trigger_assessments": [
                    {
                        "trigger_id": trigger_id,
                        "triggered": trigger_id == "PATCH_PRESERVES_OBJECT_WITHOUT_CBIT_GAIN",
                        "rationale": f"deterministic assessment for {trigger_id}",
                        "evidence_refs": list(EVIDENCE),
                    }
                    for trigger_id in ANTI_ADDITIVE_TRIGGER_IDS
                ],
                "expected_effective_cbit_gain": 0.80,
                "complexity_cost": 0.20,
                "object_upgrade_gain": 0.70,
                "abstraction_cost": 0.20,
                "uncertainty": 0.15,
                "recommended_action": "UPGRADE_OBJECT",
                "rationale": "one governed object replaces repeated local patches",
                "evidence_refs": list(EVIDENCE),
            },
            "usage": {},
            "provenance_refs": list(EVIDENCE),
        }


def _methodology_runtime(root: Path, runtime_id: str, calibration_source=None):
    return AntiAdditiveMethodologyRuntime(
        runtime_id=runtime_id,
        project_scope=SCOPE,
        provider_router=ProviderTaskRouter([SmokeProvider()]),
        workspace_root=root,
        calibration_source=calibration_source,
    )


def _change_candidate(*, audit_id: str, payload: dict, target_type: str, change_kind: str):
    return AntiAdditiveChangeCandidate.create(
        audit_id=audit_id,
        candidate_id=payload["candidate_id"],
        project_scope=SCOPE,
        change_kind=change_kind,
        target_type=target_type,
        current_object_ref="object://local-patch",
        proposed_object_ref="object://governed-runtime-object",
        current_object_level="PROXY",
        proposed_object_level="ONTOLOGY_OBJECT",
        prior_failure_count=2,
        prior_patch_count=3,
        candidate_payload_hash=methodology_candidate_commitment(payload),
        evidence_refs=EVIDENCE,
    )


def _retention_candidate(index: int) -> dict[str, Any]:
    return {
        "candidate_id": f"retention-{index}",
        "project_scope_ref": SCOPE,
        "scope": "project_scoped",
        "decision_status": "SUPPORTED_BOUNDED",
        "evidence_refs": list(EVIDENCE),
        "support_path": f"claim://retention-{index} -> evidence://harness-outcome",
        "accept_decision_ref": f"decision://retention-{index}",
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


def _baseline_candidate() -> dict[str, Any]:
    return {
        "candidate_id": "baseline-proposal",
        "project_scope_ref": SCOPE,
        "source_project": "AgentOS_CoreSlim",
        "accept_decision_ref": "decision://accepted-project-learning",
        "project_scoped_write_ref": "project://memory/accepted-learning",
        "evidence_refs": list(EVIDENCE),
        "empirical_validation_refs": ["replay://retention-calibration-pass"],
        "replayable_evidence": True,
        "cross_project_reuse_value": 0.8,
        "negative_transfer_risk": "bounded",
        "conflict_scan": "complete_no_unresolved_blocker",
    }


def _manifest(output: Path) -> dict[str, Any]:
    excluded = {output / "manifest.json", output / RETURN_PACK_NAME}
    files = [
        {
            "path": path.relative_to(output).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(output.rglob("*"))
        if path.is_file() and path not in excluded
    ]
    payload = {"status": "PASS", "files": files}
    payload["manifest_hash"] = _hash_payload(payload)
    (output / "manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return payload


def run_smoke(output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    predictions = _methodology_runtime(output / "predictions", "aa-predictions")
    calibration = AntiAdditiveCalibrationRuntime(
        runtime_id="aa-calibration",
        project_scope=SCOPE,
        workspace_root=output / "calibration",
    )
    calibration_receipts = []
    for index in (1, 2):
        payload = _retention_candidate(index)
        prediction = predictions.review_change(
            candidate=_change_candidate(
                audit_id=f"audit-calibration-{index}",
                payload=payload,
                target_type="RetentionCandidate",
                change_kind="MEMORY",
            ),
            kernel_authorization_ref="kernel://anti-additive-prediction",
        )
        calibration_receipts.append(
            calibration.record_outcome(
                calibration_id=f"calibration-{index}",
                observation_id=f"observation-{index}",
                methodology_receipt=prediction,
                outcome_source_hash=_digest(f"outcome-source-{index}"),
                harness_receipt_hash=_digest(f"harness-receipt-{index}"),
                observed_effective_cbit_gain=0.78,
                observed_complexity_cost=0.22,
                observed_object_upgrade_gain=0.68,
                observed_abstraction_cost=0.22,
                evidence_refs=EVIDENCE,
                kernel_authorization_ref="kernel://anti-additive-calibration",
            )
        )

    source = _methodology_runtime(output / "controlled", "aa-controlled", calibration)
    retention = _retention_candidate(3)
    retention_receipt = source.review_change(
        candidate=_change_candidate(
            audit_id="audit-retention-3",
            payload=retention,
            target_type="RetentionCandidate",
            change_kind="MEMORY",
        ),
        kernel_authorization_ref="kernel://anti-additive-retention",
    )
    migration = LegacyRetentionMigrator(SCOPE, anti_additive_source=source).create(
        retention,
        migration_authority_ref="kernel://retention-migration",
        methodology_audit_id="audit-retention-3",
    )

    baseline = _baseline_candidate()
    baseline_receipt = source.review_change(
        candidate=_change_candidate(
            audit_id="audit-baseline-proposal",
            payload=baseline,
            target_type="BaselineEvolutionProposal",
            change_kind="POLICY",
        ),
        kernel_authorization_ref="kernel://anti-additive-baseline",
    )
    baseline_runtime = AntiAdditiveBaselineEvolutionRuntime(
        project_scope=SCOPE,
        methodology_source=source,
    )
    review = baseline_runtime.review_eligibility(
        baseline,
        methodology_audit_id="audit-baseline-proposal",
    )
    proposal = baseline_runtime.build_proposal(baseline, review)

    gates = {
        "calibration_reached_trusted_state": calibration_receipts[-1].decision.state
        == "CALIBRATED",
        "future_retention_receipt_is_trusted": (
            retention_receipt.decision.state == "ALLOW_BOUNDED_CHANGE"
            and retention_receipt.decision.calibration_control.control_mode == "TRUSTED"
        ),
        "retention_durable_authority_is_bound": (
            migration.legacy_eligible_for_retention is True
            and migration.anti_additive_methodology_receipt_hash == retention_receipt.receipt_hash
        ),
        "baseline_remains_candidate_only": (
            baseline_receipt.decision.state == "REQUIRE_CALIBRATED_VALIDATION"
            and proposal["anti_additive_methodology_receipt_hash"]
            == baseline_receipt.receipt_hash
            and proposal["official_baseline_written"] is False
        ),
        "all_ledgers_replay": (
            predictions.verify_replay()["valid"]
            and calibration.verify_replay()["valid"]
            and source.verify_replay()["valid"]
        ),
    }
    if not all(gates.values()):
        raise RuntimeError("anti_additive_calibration_smoke_failed")
    result = {
        "status": "PASS",
        "gates": gates,
        "calibration_receipt": calibration_receipts[-1].as_dict(),
        "retention_methodology_receipt": retention_receipt.as_dict(),
        "retention_migration": migration.as_dict(),
        "baseline_methodology_receipt": baseline_receipt.as_dict(),
        "baseline_proposal": proposal,
        "prediction_replay": predictions.verify_replay(),
        "calibration_replay": calibration.verify_replay(),
        "source_replay": source.verify_replay(),
    }
    (output / "anti_additive_calibration_smoke_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = _manifest(output)
    pack = output / RETURN_PACK_NAME
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output.rglob("*")):
            if path.is_file() and path != pack:
                archive.write(path, path.relative_to(output).as_posix())
    return {
        "status": "PASS",
        "output_dir": str(output),
        "manifest_file_count": len(manifest["files"]),
        "return_pack": str(pack),
        "return_pack_sha256": sha256(pack.read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    print(json.dumps(run_smoke(args.output_dir), indent=2, sort_keys=True))
