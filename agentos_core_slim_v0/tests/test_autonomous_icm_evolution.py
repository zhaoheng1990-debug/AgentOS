import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (
    ANTI_ADDITIVE_TRIGGER_IDS,
    AntiAdditiveChangeCandidate,
    AntiAdditiveMethodologyGate,
    AntiAdditiveMethodologyPolicy,
    AntiAdditiveProviderJudgment,
    AntiAdditiveTriggerAssessment,
    AutonomousICMEvolutionPolicy,
    ProjectScopedDurableStore,
    methodology_candidate_commitment,
)


def ups_candidate():
    return {
        "candidate_id": "ups_accept_operator_memory",
        "research_line": "UtilityPolicySelector",
        "status": "ACCEPT_READY_WITH_EVIDENCE",
        "evidence_refs": [
            "SR_series",
            "UPS_validation",
            "reuse_gain_records",
            "negative_transfer_audit",
        ],
        "accept_decision_ref": "UPS_ACCEPTDecisionRecord",
        "scope": "AgentOS project runtime policy selection",
        "project_scope_ref": "project://agentos-core-slim",
        "target_type": "OperatorMemory",
        "negative_transfer_risk": "bounded",
        "future_cbit_gain": "positive",
        "replayable_evidence": True,
    }


def methodology_receipt(candidate):
    evidence_refs = tuple(candidate["evidence_refs"])
    change = AntiAdditiveChangeCandidate.create(
        audit_id=f"audit-{candidate['candidate_id']}",
        candidate_id=candidate["candidate_id"],
        project_scope=candidate["project_scope_ref"],
        change_kind="MEMORY",
        target_type=candidate.get("target_type", "MemoryUnit"),
        current_object_ref="object://current",
        proposed_object_ref="object://proposed",
        current_object_level="PROXY",
        proposed_object_level="PROXY",
        prior_failure_count=0,
        prior_patch_count=0,
        candidate_payload_hash=methodology_candidate_commitment(candidate),
        evidence_refs=evidence_refs,
    )
    triggers = tuple(
        AntiAdditiveTriggerAssessment.create(
            trigger_id=trigger_id,
            triggered=False,
            rationale="bounded fixture audit",
            evidence_refs=evidence_refs,
        )
        for trigger_id in ANTI_ADDITIVE_TRIGGER_IDS
    )
    judgment = AntiAdditiveProviderJudgment.create(
        candidate_hash=change.candidate_hash,
        current_object_adequacy="ADEQUATE",
        trigger_assessments=triggers,
        expected_effective_cbit_gain=0.8,
        complexity_cost=0.2,
        object_upgrade_gain=0.0,
        abstraction_cost=0.0,
        uncertainty=0.1,
        recommended_action="KEEP_OBJECT",
        rationale="fixture supports bounded change",
        evidence_refs=evidence_refs,
        provider_invocation_receipt={"receipt_hash": "fixture"},
        provider_audit={"status": "PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT"},
    )
    return AntiAdditiveMethodologyGate().review(
        candidate=change,
        judgment=judgment,
        policy=AntiAdditiveMethodologyPolicy(),
        kernel_authorization_ref="kernel://anti-additive-test",
    )


def test_ups_accept_triggers_project_scoped_operator_memory_write(tmp_path):
    policy = AutonomousICMEvolutionPolicy()
    store = ProjectScopedDurableStore(tmp_path / "project_scoped_icm_store")
    candidate = ups_candidate()
    review = policy.review(candidate, methodology_receipt(candidate))

    envelope = policy.build_envelope(candidate, review, store)
    receipt = store.write(envelope)

    assert review.decision == "AUTONOMOUS_PROJECT_OPERATORMEMORY_WRITE"
    assert receipt["status"] == "PASS"
    assert "operator_memory" in receipt["target_path"]
    payload = json.loads(Path(receipt["target_path"]).read_text(encoding="utf-8"))
    assert payload["operator_id"] == "UtilityPolicySelectorOperator"
    assert receipt["authorized_by"] == "AgentOSKernel.ICMEvolutionPolicy"
    assert receipt["production_activation"] is False
    assert envelope["anti_additive_methodology_decision_hash"]


def test_evidence_weak_user_positive_remains_no_write(tmp_path):
    policy = AutonomousICMEvolutionPolicy()
    store = ProjectScopedDurableStore(tmp_path / "project_scoped_icm_store")
    candidate = {
        "candidate_id": "user_positive_weak",
        "research_line": "UserPraisedHeuristic",
        "status": "USER_POSITIVE_CANDIDATE",
        "user_value_signal": "positive",
        "evidence_refs": [],
        "scope": "project_scoped",
        "negative_transfer_risk": "low",
        "future_cbit_gain": "positive",
    }

    review = policy.review(candidate)

    assert review.decision == "BLOCK_WRITE_INSUFFICIENT_EVIDENCE"
    assert not any((store.root / "memory_units").iterdir())
    assert not any((store.root / "operator_memory").iterdir())


def test_negative_transfer_candidate_is_quarantined(tmp_path):
    policy = AutonomousICMEvolutionPolicy()
    store = ProjectScopedDurableStore(tmp_path / "project_scoped_icm_store")
    candidate = {
        "candidate_id": "negative_transfer_case",
        "research_line": "RiskyReusePattern",
        "status": "ACCEPT_READY_WITH_EVIDENCE",
        "evidence_refs": ["replay_case"],
        "scope": "project_scoped",
        "negative_transfer_detected": True,
        "future_cbit_gain": "positive",
    }
    review = policy.review(candidate)
    receipt = store.quarantine(candidate, policy)

    assert review.decision == "AUTONOMOUS_QUARANTINE"
    assert receipt["status"] == "PASS"
    assert "negative_transfer_quarantine" in receipt["target_path"]


def test_replay_and_rollback_for_project_scoped_write(tmp_path):
    policy = AutonomousICMEvolutionPolicy()
    store = ProjectScopedDurableStore(tmp_path / "project_scoped_icm_store")
    candidate = ups_candidate()
    review = policy.review(candidate, methodology_receipt(candidate))
    receipt = store.write(policy.build_envelope(candidate, review, store))

    replay = store.replay(receipt)
    rollback = store.rollback(receipt["rollback_pointer"])

    assert replay["replay_status"] == "PASS"
    assert rollback["status"] == "ROLLED_BACK"
    assert rollback["matches_before_hash"] is True
    assert not Path(receipt["target_path"]).exists()


def test_repeated_candidate_write_preserves_append_only_replay_and_rollback_history(tmp_path):
    policy = AutonomousICMEvolutionPolicy()
    store = ProjectScopedDurableStore(tmp_path / "project_scoped_icm_store")
    candidate = ups_candidate()
    review = policy.review(candidate, methodology_receipt(candidate))

    first = store.write(policy.build_envelope(candidate, review, store))
    second = store.write(policy.build_envelope(candidate, review, store))

    assert first["operation_id"] != second["operation_id"]
    assert first["rollback_pointer"] != second["rollback_pointer"]
    assert first["replay_manifest_ref"] != second["replay_manifest_ref"]
    assert Path(first["rollback_pointer"]).is_file()
    assert Path(second["rollback_pointer"]).is_file()
    assert Path(first["replay_manifest_ref"]).is_file()
    assert Path(second["replay_manifest_ref"]).is_file()


def test_durable_write_without_anti_additive_receipt_remains_candidate(tmp_path):
    policy = AutonomousICMEvolutionPolicy()
    candidate = ups_candidate()

    review = policy.review(candidate)

    assert review.decision == "NO_WRITE_KEEP_CANDIDATE"
    assert review.reason == "anti_additive_methodology_receipt_required"
    assert review.eligible is False


def test_global_or_production_write_is_blocked(tmp_path):
    store = ProjectScopedDurableStore(tmp_path / "project_scoped_icm_store")
    target = tmp_path / "global_icm" / "bad.json"
    envelope = {
        "write_id": "bad",
        "decision_id": "bad",
        "authorized_by": "AgentOSKernel.ICMEvolutionPolicy",
        "target_scope": "global_production",
        "target_type": "OperatorMemory",
        "target_path": str(target),
        "payload": {},
        "rollback_required": True,
        "production_activation": True,
    }

    try:
        store.write(envelope)
    except Exception as exc:
        assert "target_scope_not_project_scoped" in str(exc)
    else:
        raise AssertionError("global production write should be blocked")
