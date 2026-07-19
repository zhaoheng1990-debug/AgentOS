import hashlib
import sys
from pathlib import Path

import pytest


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))
sys.path.insert(0, str(CORE_ROOT / "tests"))

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
    ProblemDefinitionStructureAdapter,
    ProblemStructureAdmissionRuntime,
    SRORetentionRuntime,
)
from agentos_runtime.sro_retention_migration import LegacyRetentionMigrator  # noqa: E402
from test_endogenous_problem_runtime import runtime as build_problem_runtime  # noqa: E402
from test_problem_structure_admission import StructureProvider  # noqa: E402


PROJECT_SCOPE = "project://fixture"
EVIDENCE = ("evidence://anti-additive-prediction", "evidence://consumer-outcome")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class MethodologyProvider:
    profile = ProviderCapabilityProfile(
        provider_id="consumer-methodology-provider",
        model_id="consumer-methodology-model",
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
                        "rationale": f"consumer fixture {trigger_id}",
                        "evidence_refs": list(EVIDENCE),
                    }
                    for trigger_id in ANTI_ADDITIVE_TRIGGER_IDS
                ],
                "expected_effective_cbit_gain": 0.8,
                "complexity_cost": 0.2,
                "object_upgrade_gain": 0.7,
                "abstraction_cost": 0.2,
                "uncertainty": 0.15,
                "recommended_action": "UPGRADE_OBJECT",
                "rationale": "consumer fixture supports an object-level change",
                "evidence_refs": list(EVIDENCE),
            },
            "usage": {},
            "provenance_refs": list(EVIDENCE),
        }


def methodology_runtime(tmp_path, *, calibration_source=None, suffix="source"):
    return AntiAdditiveMethodologyRuntime(
        runtime_id=f"anti-additive-consumer-{suffix}",
        project_scope=PROJECT_SCOPE,
        provider_router=ProviderTaskRouter([MethodologyProvider()]),
        workspace_root=tmp_path,
        calibration_source=calibration_source,
    )


def review(engine, *, audit_id, candidate_id, target_type, payload):
    candidate = AntiAdditiveChangeCandidate.create(
        audit_id=audit_id,
        candidate_id=candidate_id,
        project_scope=PROJECT_SCOPE,
        change_kind="OBJECT",
        target_type=target_type,
        current_object_ref="object://local-patch",
        proposed_object_ref="object://governed-object",
        current_object_level="PROXY",
        proposed_object_level="ONTOLOGY_OBJECT",
        prior_failure_count=2,
        prior_patch_count=2,
        candidate_payload_hash=methodology_candidate_commitment(payload),
        evidence_refs=EVIDENCE,
    )
    return engine.review_change(
        candidate=candidate,
        kernel_authorization_ref="kernel://anti-additive-consumer-review",
    )


def baseline_candidate():
    return {
        "candidate_id": "baseline-candidate",
        "project_scope_ref": PROJECT_SCOPE,
        "source_project": "AgentOS_CoreSlim",
        "accept_decision_ref": "decision://accepted-project-learning",
        "project_scoped_write_ref": "project://memory/accepted-learning",
        "evidence_refs": list(EVIDENCE),
        "empirical_validation_refs": ["replay://pass"],
        "replayable_evidence": True,
        "cross_project_reuse_value": 0.8,
        "negative_transfer_risk": "bounded",
        "conflict_scan": "complete_no_unresolved_blocker",
    }


def retention_candidate():
    return {
        "candidate_id": "retention-candidate",
        "project_scope_ref": PROJECT_SCOPE,
        "scope": "project_scoped",
        "decision_status": "SUPPORTED_BOUNDED",
        "evidence_refs": list(EVIDENCE),
        "support_path": "claim://retention -> evidence://consumer-outcome",
        "accept_decision_ref": "decision://retention",
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


def test_one_replayable_source_supports_problem_admission_and_baseline_candidate(tmp_path):
    calibration = AntiAdditiveCalibrationRuntime(
        runtime_id="consumer-calibration-empty",
        project_scope=PROJECT_SCOPE,
        workspace_root=tmp_path / "calibration",
    )
    source = methodology_runtime(
        tmp_path / "methodology",
        calibration_source=calibration,
        suffix="exploration",
    )

    problem_runtime, _ = build_problem_runtime(tmp_path / "problem")
    assert problem_runtime.run_to_candidate().stage == "CANDIDATE"
    problem_candidate = ProblemDefinitionStructureAdapter(
        problem_runtime,
        context_key="ctx-consumer-problem",
    ).build_candidate(candidate_id="problem-candidate")
    problem_methodology = review(
        source,
        audit_id="audit-problem-admission",
        candidate_id=problem_candidate.candidate_id,
        target_type="ProblemStructure",
        payload=problem_candidate.as_dict(),
    )
    admission = ProblemStructureAdmissionRuntime(
        runtime_id="problem-admission-consumer",
        project_scope=PROJECT_SCOPE,
        provider_router=ProviderTaskRouter([StructureProvider()]),
        workspace_root=tmp_path / "admission",
        anti_additive_source=source,
    ).admit_candidate(
        admission_id="admission-consumer",
        candidate=problem_candidate,
        kernel_authorization_ref="kernel://problem-admission",
        methodology_audit_id="audit-problem-admission",
    )

    baseline = baseline_candidate()
    baseline_methodology = review(
        source,
        audit_id="audit-baseline-proposal",
        candidate_id=baseline["candidate_id"],
        target_type="BaselineEvolutionProposal",
        payload=baseline,
    )
    baseline_runtime = AntiAdditiveBaselineEvolutionRuntime(
        project_scope=PROJECT_SCOPE,
        methodology_source=source,
    )
    baseline_review = baseline_runtime.review_eligibility(
        baseline,
        methodology_audit_id="audit-baseline-proposal",
    )
    proposal = baseline_runtime.build_proposal(baseline, baseline_review)

    assert problem_methodology.decision.state == "REQUIRE_CALIBRATED_VALIDATION"
    assert admission.decision.anti_additive_methodology_receipt_hash == problem_methodology.receipt_hash
    assert baseline_methodology.decision.state == "REQUIRE_CALIBRATED_VALIDATION"
    assert proposal["anti_additive_methodology_receipt_hash"] == baseline_methodology.receipt_hash
    assert source.verify_replay()["valid"] is True


def test_retention_requires_durable_authority_from_same_receipt_contract(tmp_path):
    candidate = retention_candidate()
    trusted_source = methodology_runtime(tmp_path / "trusted", suffix="trusted")
    trusted = review(
        trusted_source,
        audit_id="audit-retention-trusted",
        candidate_id=candidate["candidate_id"],
        target_type="RetentionCandidate",
        payload=candidate,
    )
    migration = LegacyRetentionMigrator(
        PROJECT_SCOPE,
        anti_additive_source=trusted_source,
    ).create(
        candidate,
        migration_authority_ref="kernel://retention-migration",
        methodology_audit_id="audit-retention-trusted",
    )

    calibration = AntiAdditiveCalibrationRuntime(
        runtime_id="retention-calibration-empty",
        project_scope=PROJECT_SCOPE,
        workspace_root=tmp_path / "calibration",
    )
    exploration_source = methodology_runtime(
        tmp_path / "exploration",
        calibration_source=calibration,
        suffix="retention-exploration",
    )
    exploration = review(
        exploration_source,
        audit_id="audit-retention-exploration",
        candidate_id=candidate["candidate_id"],
        target_type="RetentionCandidate",
        payload=candidate,
    )

    assert trusted.decision.allowed is True
    assert migration.anti_additive_methodology_receipt_hash == trusted.receipt_hash
    assert migration.legacy_eligible_for_retention is True
    assert exploration.decision.candidate_only_allowed is True
    with pytest.raises(ValueError, match="durable_authority_required"):
        LegacyRetentionMigrator(
            PROJECT_SCOPE,
            anti_additive_source=exploration_source,
        ).create(
            candidate,
            migration_authority_ref="kernel://retention-migration",
            methodology_audit_id="audit-retention-exploration",
        )


def test_bulk_retention_uses_one_methodology_audit_per_candidate(tmp_path):
    source = methodology_runtime(tmp_path / "methodology", suffix="bulk-retention")
    candidates = (retention_candidate(), {**retention_candidate(), "candidate_id": "retention-2"})
    audit_ids = {}
    for index, candidate in enumerate(candidates, start=1):
        audit_id = f"audit-bulk-retention-{index}"
        audit_ids[candidate["candidate_id"]] = audit_id
        review(
            source,
            audit_id=audit_id,
            candidate_id=candidate["candidate_id"],
            target_type="RetentionCandidate",
            payload=candidate,
        )
    runtime = SRORetentionRuntime(
        runtime_id="bulk-retention-runtime",
        project_scope=PROJECT_SCOPE,
        matcher_router=ProviderTaskRouter([MethodologyProvider()]),
        workspace_root=tmp_path / "retention-runtime",
        anti_additive_source=source,
    )

    migrations = runtime.migrate_legacy_candidates(
        candidates,
        migration_authority_ref="kernel://bulk-retention-migration",
        methodology_audit_ids=audit_ids,
    )

    assert len(migrations) == 2
    assert len({item.anti_additive_methodology_receipt_hash for item in migrations}) == 2
    assert runtime.verify_replay()["valid"] is True


def test_receipt_source_rejects_cross_consumer_object_binding(tmp_path):
    source = methodology_runtime(tmp_path / "methodology", suffix="binding")
    baseline = baseline_candidate()
    review(
        source,
        audit_id="audit-wrong-target",
        candidate_id=baseline["candidate_id"],
        target_type="ProblemStructure",
        payload=baseline,
    )
    runtime = AntiAdditiveBaselineEvolutionRuntime(
        project_scope=PROJECT_SCOPE,
        methodology_source=source,
    )

    with pytest.raises(ValueError, match="binding_invalid"):
        runtime.review_eligibility(baseline, methodology_audit_id="audit-wrong-target")
