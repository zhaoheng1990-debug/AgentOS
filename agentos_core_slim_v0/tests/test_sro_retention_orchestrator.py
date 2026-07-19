import json
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (  # noqa: E402
    DelayedRetrievalLedger,
    DelayedRetrievalPrediction,
    GradedSROCompatibilityGate,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    SerialSelectionWitness,
)
from agentos_runtime import (  # noqa: E402
    SROCalibrationContract,
    SRORetentionRuntime,
    SRORetentionTask,
)


HASH_A = "a" * 64
HASH_B = "b" * 64


class RecordingMatcher:
    def __init__(self, result_factory=None):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-provider",
            model_id="fixture-sro-model",
            task_kinds=("graded_sro_retention_candidate_routing",),
            max_timeout_seconds=120,
        )
        self.result_factory = result_factory or matcher_result
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        return {
            "result": self.result_factory(task),
            "usage": {"total_tokens": 12},
            "provenance_refs": list(task.allowed_evidence),
        }


def matcher_result(task):
    return {
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
    }


def witness(witness_id="PW-RUNTIME-1"):
    return SerialSelectionWitness(
        witness_id=witness_id,
        status="PRECOMMITTED",
        project_scope_ref="project://runtime-fixture",
        selection_context_ref="selection://runtime-fixture",
        sro_address_ref="sro://bounded-role-structure",
        validity_boundary_ref="boundary://runtime-fixture",
        reconstruction_ref="reconstruction://runtime-fixture",
        authority_ref="authority://kernel-fixture",
        privacy_boundary="reference_only_no_raw_chat",
        precommit_hash=HASH_A,
        sealed_at="2026-07-19T12:00:00+00:00",
        evidence_refs=("evidence://witness",),
    )


def task():
    return SRORetentionTask(
        task_id="task-runtime-1",
        project_scope="project://runtime-fixture",
        objective="Determine whether the retained witness applies to this bounded task.",
        context_ref="context://runtime-fixture/later-task",
        constraint_field_ref="constraint://runtime-fixture",
        evidence_refs=("evidence://task",),
    )


def calibration():
    return SROCalibrationContract(
        matcher_id="matcher://fixture-v1",
        matcher_version="1.0",
        calibration_ref="calibration://fixture-heldout",
        calibration_status="FROZEN_PROJECT_SCOPED",
        evidence_scope="INTERNAL_PROJECT",
        evidence_refs=("evidence://calibration",),
    )


def runtime(tmp_path, matcher=None):
    matcher = matcher or RecordingMatcher()
    return (
        SRORetentionRuntime(
            runtime_id="sro-runtime-fixture",
            project_scope="project://runtime-fixture",
            matcher_router=ProviderTaskRouter([matcher]),
            workspace_root=tmp_path,
        ),
        matcher,
    )


def valid_legacy_candidate(candidate_id="legacy-1"):
    return {
        "candidate_id": candidate_id,
        "scope": "project_scoped",
        "decision_status": "SUPPORTED_BOUNDED",
        "evidence_refs": ["evidence://legacy"],
        "support_path": "claim://legacy -> evidence://legacy",
        "accept_decision_ref": "decision://legacy",
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


def old_autonomous_candidate(candidate_id="legacy-autonomous-1"):
    return {
        "candidate_id": candidate_id,
        "scope": "project_scoped",
        "status": "ACCEPT_READY_WITH_EVIDENCE",
        "evidence_refs": ["evidence://legacy-autonomous"],
        "accept_decision_ref": "decision://legacy-autonomous",
        "replayable_evidence": True,
        "future_cbit_gain": "positive",
        "negative_transfer_risk": "low",
    }


def test_provider_backed_runtime_binds_real_witness_task_and_invocation_receipt(tmp_path):
    engine, matcher = runtime(tmp_path)
    source = witness()
    engine.register_witness(source, kernel_authorization_ref="kernel://register-native")

    route = engine.route_witness(source.witness_id, task(), calibration())

    assert route.decision["route"] == "DIRECT_REUSE"
    assert route.witness_hash == source.as_dict()["record_hash"]
    assert route.task_commitment_hash == task().task_commitment_hash
    assert route.matcher_receipt["provider_invocation_receipt_hash"] == (
        route.provider_invocation_receipt["receipt_hash"]
    )
    assert route.provider_audit["status"].startswith("PASS_")
    assert route.candidate_state == "ROUTE_DECIDED_PROJECT_SCOPED"
    assert route.as_dict()["global_memory_write_authority"] is False
    assert len(matcher.tasks) == 1
    assert engine.verify_replay()["valid"]


def test_gate_rejects_spoofed_bound_witness_or_invocation_hash():
    source = witness()
    receipt = {
        "matcher_id": "matcher://fixture",
        "matcher_version": "1",
        "task_id": "task-runtime-1",
        "task_commitment_hash": HASH_B,
        "witness_id": source.witness_id,
        "witness_hash": HASH_A,
        "project_scope_ref": "project://runtime-fixture",
        "scope": "project_scoped",
        "evidence_refs": ["evidence://fixture"],
        "calibration_ref": "calibration://fixture",
        "provider_support_receipt_ref": "provider-receipt://fixture",
        "provider_invocation_receipt_hash": HASH_A,
        "cognition_audit_hash": HASH_B,
        "replayable_evidence": True,
        "evidence_scope": "INTERNAL_PROJECT",
        "calibration_status": "FROZEN_PROJECT_SCOPED",
        **matcher_result(type("Task", (), {"allowed_evidence": ["evidence://fixture"]})()),
    }
    receipt.pop("evidence_refs")
    receipt["evidence_refs"] = ["evidence://fixture"]

    decision = GradedSROCompatibilityGate().evaluate(
        receipt,
        witness=source,
        task_commitment_hash=HASH_B,
        provider_invocation_receipt_hash=HASH_B,
    )

    assert decision.route == "ABSTAIN"
    assert "witness_hash_mismatch" in decision.hard_gate_failures
    assert "provider_invocation_receipt_hash_mismatch" in decision.hard_gate_failures


def test_provider_missing_contract_field_blocks_before_kernel_route(tmp_path):
    def incomplete(task):
        result = matcher_result(task)
        del result["role_compatibility"]
        return result

    engine, _matcher = runtime(tmp_path, RecordingMatcher(incomplete))
    source = witness()
    engine.register_witness(source, kernel_authorization_ref="kernel://register-native")

    with pytest.raises(RuntimeError, match="sro_retention_provider_blocked:VALIDATION_FAILED"):
        engine.route_witness(source.witness_id, task(), calibration())

    assert engine.verify_replay()["valid"]


def test_provider_out_of_scope_evidence_is_preserved_and_blocked(tmp_path):
    def wrong_evidence(task):
        result = matcher_result(task)
        result["evidence_refs"] = ["evidence://not-admitted"]
        return result

    engine, _matcher = runtime(tmp_path, RecordingMatcher(wrong_evidence))
    source = witness()
    engine.register_witness(source, kernel_authorization_ref="kernel://register-native")

    with pytest.raises(ValueError, match="sro_retention_provider_evidence_invalid"):
        engine.route_witness(source.witness_id, task(), calibration())

    events = engine.public_store_path.joinpath("events.jsonl").read_text(encoding="utf-8")
    assert "SRO_PROVIDER_ROUTE_BLOCKED" in events


def test_provider_cannot_smuggle_binding_or_authority_fields(tmp_path):
    def smuggled_identity(task):
        result = matcher_result(task)
        result["witness_id"] = "PW-SPOOFED"
        return result

    engine, _matcher = runtime(tmp_path, RecordingMatcher(smuggled_identity))
    source = witness()
    engine.register_witness(source, kernel_authorization_ref="kernel://register-native")

    with pytest.raises(ValueError, match="sro_retention_provider_field_set_invalid"):
        engine.route_witness(source.witness_id, task(), calibration())


def test_cross_project_witness_registration_is_blocked(tmp_path):
    engine, _matcher = runtime(tmp_path)
    cross_project = SerialSelectionWitness(
        **{**witness().__dict__, "project_scope_ref": "project://different-project"}
    )

    with pytest.raises(ValueError, match="sro_witness_project_scope_mismatch"):
        engine.register_witness(
            cross_project,
            kernel_authorization_ref="kernel://register-cross-project",
        )


def test_legacy_candidate_migrates_candidate_only_then_requires_explicit_reconstruction(tmp_path):
    engine, _matcher = runtime(tmp_path)
    migration = engine.migrate_legacy_candidate(
        valid_legacy_candidate(),
        migration_authority_ref="kernel://legacy-migration",
    )

    assert migration.candidate_state == "PENDING_WITNESS_RECONSTRUCTION"
    assert migration.registered_witness_id == ""
    with pytest.raises(KeyError, match="unknown_sro_witness"):
        engine.route_witness("legacy-1", task(), calibration())

    reconstructed = engine.reconstruct_migrated_witness(
        migration.migration_id,
        witness_id="PW-MIGRATED-1",
        sro_address_ref="sro://migrated-role",
        validity_boundary_ref="boundary://migrated",
        reconstruction_ref="reconstruction://migrated",
        authority_ref="authority://migrated",
        privacy_boundary="reference_only_no_raw_chat",
        sealed_at="2026-07-19T12:10:00+00:00",
        evidence_refs=("evidence://legacy", "evidence://reconstruction"),
        kernel_authorization_ref="kernel://reconstruct-legacy",
    )

    assert reconstructed.selection_context_ref == f"migration://{migration.migration_id}"
    assert engine.migration(migration.migration_id).candidate_state == (
        "WITNESS_REGISTERED_PROJECT_SCOPED"
    )
    assert engine.route_witness(reconstructed.witness_id, task(), calibration()).decision["route"] == (
        "DIRECT_REUSE"
    )


def test_ineligible_legacy_record_is_quarantined_and_cannot_be_reconstructed(tmp_path):
    engine, _matcher = runtime(tmp_path)
    candidate = valid_legacy_candidate("legacy-quarantine")
    candidate["negative_transfer_detected"] = True

    migration = engine.migrate_legacy_candidate(
        candidate,
        migration_authority_ref="kernel://legacy-migration",
    )

    assert migration.candidate_state == "QUARANTINED_LEGACY_RECORD"
    with pytest.raises(ValueError, match="legacy_migration_not_pending_reconstruction"):
        engine.reconstruct_migrated_witness(
            migration.migration_id,
            witness_id="PW-BLOCKED",
            sro_address_ref="sro://blocked",
            validity_boundary_ref="boundary://blocked",
            reconstruction_ref="reconstruction://blocked",
            authority_ref="authority://blocked",
            privacy_boundary="reference_only",
            sealed_at="2026-07-19T12:10:00+00:00",
            evidence_refs=("evidence://legacy",),
            kernel_authorization_ref="kernel://blocked",
        )


def test_old_autonomous_schema_waits_for_bound_revalidation_before_reconstruction(tmp_path):
    engine, _matcher = runtime(tmp_path)
    migration = engine.migrate_legacy_candidate(
        old_autonomous_candidate(),
        migration_authority_ref="kernel://legacy-migration",
    )

    assert migration.candidate_state == "PENDING_PROVIDER_REVALIDATION"
    revalidated = valid_legacy_candidate(migration.legacy_candidate_id)
    revalidated["legacy_source_hash"] = migration.legacy_candidate_hash
    revalidated["evidence_refs"].append("evidence://legacy-autonomous")
    updated = engine.revalidate_legacy_migration(
        migration.migration_id,
        revalidated,
        kernel_authorization_ref="kernel://legacy-revalidation",
    )

    assert updated.candidate_state == "PENDING_WITNESS_RECONSTRUCTION"
    assert updated.legacy_eligible_for_retention is True


def test_legacy_revalidation_cannot_switch_source_identity_or_drop_evidence(tmp_path):
    engine, _matcher = runtime(tmp_path)
    migration = engine.migrate_legacy_candidate(
        old_autonomous_candidate(),
        migration_authority_ref="kernel://legacy-migration",
    )
    revalidated = valid_legacy_candidate("different-candidate")
    revalidated["legacy_source_hash"] = migration.legacy_candidate_hash

    with pytest.raises(ValueError, match="legacy_revalidation_candidate_id_mismatch"):
        engine.revalidate_legacy_migration(
            migration.migration_id,
            revalidated,
            kernel_authorization_ref="kernel://legacy-revalidation",
        )


def test_persistent_runtime_and_delayed_ledger_reload_after_restart(tmp_path):
    engine, matcher = runtime(tmp_path)
    source = witness()
    engine.register_witness(source, kernel_authorization_ref="kernel://register-native")
    route = engine.route_witness(source.witness_id, task(), calibration())
    engine.seal_delayed_prediction(
        route.route_receipt_id,
        prediction_id="DR-RUNTIME-1",
        sealed_at="2026-07-19T12:20:00+00:00",
        evidence_refs=(*route.evidence_refs, "evidence://prediction"),
    )
    engine.score_delayed_outcome(
        "DR-RUNTIME-1",
        observed_route="DIRECT_REUSE",
        role_reconstruction_fidelity=0.9,
        negative_transfer_penalty=0.1,
        outcome_ref="outcome://runtime-fixture",
        outcome_hash=HASH_B,
        revealed_at="2026-07-19T12:21:00+00:00",
        scoring_authority_ref="authority://frozen-harness",
    )

    restarted, _ = runtime(tmp_path, matcher)

    assert restarted.witness(source.witness_id).as_dict() == source.as_dict()
    assert restarted.route_receipt(route.route_receipt_id).as_dict() == route.as_dict()
    assert restarted.snapshot().delayed_retrieval_replay["prediction_count"] == 1
    assert restarted.snapshot().delayed_retrieval_replay["score_count"] == 1
    assert restarted.verify_replay()["valid"]


def test_persistent_delayed_ledger_rejects_tamper_on_reload(tmp_path):
    path = tmp_path / "delayed.jsonl"
    ledger = DelayedRetrievalLedger(path)
    ledger.register_prediction(
        DelayedRetrievalPrediction(
            prediction_id="DR-TAMPER",
            source_witness_id="PW-TAMPER",
            target_task_id="TASK-TAMPER",
            predicted_route="OBSERVE",
            source_witness_hash=HASH_A,
            target_task_commitment_hash=HASH_B,
            sealed_at="2026-07-19T12:00:00+00:00",
            evidence_refs=("evidence://tamper",),
        )
    )
    event = json.loads(path.read_text(encoding="utf-8"))
    event["payload"]["predicted_route"] = "DIRECT_REUSE"
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="delayed_retrieval_ledger_replay_invalid"):
        DelayedRetrievalLedger(path)


def test_persistent_delayed_ledger_detects_stale_concurrent_writer(tmp_path):
    path = tmp_path / "concurrent.jsonl"
    first = DelayedRetrievalLedger(path)
    stale = DelayedRetrievalLedger(path)
    first.register_prediction(
        DelayedRetrievalPrediction(
            prediction_id="DR-FIRST",
            source_witness_id="PW-FIRST",
            target_task_id="TASK-FIRST",
            predicted_route="OBSERVE",
            source_witness_hash=HASH_A,
            target_task_commitment_hash=HASH_B,
            sealed_at="2026-07-19T12:00:00+00:00",
            evidence_refs=("evidence://first",),
        )
    )

    with pytest.raises(RuntimeError, match="concurrent_modification"):
        stale.register_prediction(
            DelayedRetrievalPrediction(
                prediction_id="DR-STALE",
                source_witness_id="PW-STALE",
                target_task_id="TASK-STALE",
                predicted_route="OBSERVE",
                source_witness_hash=HASH_A,
                target_task_commitment_hash=HASH_B,
                sealed_at="2026-07-19T12:00:01+00:00",
                evidence_refs=("evidence://stale",),
            )
        )
