import copy
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_runtime import OrganizationExperimentPlan, organization_records_from_ablation_smoke_result
from examples.cognitive_organization_ablation_project_source_smoke import run_case
from examples.cognitive_team_execution_project_source_smoke import load_life_case
from examples.organization_ablation_learning_feedback_smoke import run_feedback


def authorized_ablation_plan():
    return OrganizationExperimentPlan(
        plan_id="experiment-project-source-ablation",
        context_key="context://life-cog3r/finding-classification",
        evidence_tier="SCRIPTED_FIXTURE",
        selected_variants=(
            "DYNAMIC_NO_COORDINATOR",
            "DYNAMIC_NO_REVIEWER",
            "DYNAMIC_NO_REPLICATOR",
        ),
        rationale_refs=("organization-policy://fixture", "organization-diagnosis://fixture"),
        policy_ref="organization-policy://fixture",
        budget={"max_trial_runs": 4, "max_provider_calls_per_run": 20},
        budget_hash="a" * 64,
        kernel_authorization_ref="kernel://organization-ablation/project-source",
        created_at="2026-07-19T00:00:00+00:00",
        plan_hash="b" * 64,
        candidate_state="AUTHORIZED_FOR_EXPERIMENT",
        execution_authorized=True,
    )


def authorized_full_ablation_plan():
    plan = authorized_ablation_plan()
    return OrganizationExperimentPlan(
        plan_id=plan.plan_id,
        context_key=plan.context_key,
        evidence_tier=plan.evidence_tier,
        selected_variants=(
            *plan.selected_variants,
            "DYNAMIC_NO_SYNTHESIZER",
        ),
        rationale_refs=plan.rationale_refs,
        policy_ref=plan.policy_ref,
        budget={"max_trial_runs": 5, "max_provider_calls_per_run": 20},
        budget_hash="c" * 64,
        kernel_authorization_ref=plan.kernel_authorization_ref,
        created_at=plan.created_at,
        plan_hash="d" * 64,
        candidate_state=plan.candidate_state,
        execution_authorized=plan.execution_authorized,
    )


def authorized_synthesizer_only_plan():
    plan = authorized_ablation_plan()
    return OrganizationExperimentPlan(
        plan_id="experiment-project-source-no-synth",
        context_key=plan.context_key,
        evidence_tier=plan.evidence_tier,
        selected_variants=("DYNAMIC_NO_SYNTHESIZER",),
        rationale_refs=plan.rationale_refs,
        policy_ref=plan.policy_ref,
        budget={"max_trial_runs": 2, "max_provider_calls_per_run": 20},
        budget_hash="e" * 64,
        kernel_authorization_ref=plan.kernel_authorization_ref,
        created_at=plan.created_at,
        plan_hash="f" * 64,
        candidate_state=plan.candidate_state,
        execution_authorized=plan.execution_authorized,
    )


def test_project_source_ablation_smoke_packages_replay_valid_learning_records(tmp_path):
    result = run_case(
        load_life_case(),
        tmp_path / "ablation-smoke",
        authorized_ablation_plan(),
        provider_mode="scripted",
        bundle_id="fixture-bundle",
    )

    records = organization_records_from_ablation_smoke_result(
        result,
        context_key=result["context_key"],
        evidence_tier=result["evidence_tier"],
        trial_group_id="fixture-trial",
    )

    assert result["status"] == "PASS"
    assert all(result["gates"].values())
    assert len(records) == 4
    assert len({item.source_result_hash for item in records}) == 1
    assert (tmp_path / "ablation-smoke" / "manifest.json").is_file()
    assert (
        tmp_path
        / "ablation-smoke"
        / "AgentOS_CognitiveOrganizationAblation_ReturnPack_v0_1.zip"
    ).is_file()


def test_ablation_import_rejects_budget_or_evidence_gate_failure(tmp_path):
    result = run_case(
        load_life_case(),
        tmp_path / "ablation-smoke",
        authorized_ablation_plan(),
        provider_mode="scripted",
        bundle_id="fixture-bundle",
    )

    for gate in ("provider_budget_respected", "evidence_surface_equal"):
        tampered = copy.deepcopy(result)
        tampered["gates"][gate] = False
        with pytest.raises(ValueError, match="organization_ablation_import_gates_incomplete"):
            organization_records_from_ablation_smoke_result(
                tampered,
                context_key=result["context_key"],
                evidence_tier=result["evidence_tier"],
                trial_group_id=f"tampered-{gate}",
            )


def test_project_source_full_ablation_executes_no_synthesizer_and_imports_five_records(tmp_path):
    result = run_case(
        load_life_case(),
        tmp_path / "full-ablation-smoke",
        authorized_full_ablation_plan(),
        provider_mode="scripted",
        bundle_id="full-fixture-bundle",
    )

    records = organization_records_from_ablation_smoke_result(
        result,
        context_key=result["context_key"],
        evidence_tier=result["evidence_tier"],
        trial_group_id="full-fixture-trial",
    )
    by_protocol = {item["protocol_id"]: item for item in result["protocol_results"]}

    assert result["status"] == "PASS"
    assert len(records) == 5
    assert by_protocol["DYNAMIC_NO_SYNTHESIZER"]["omitted_components"] == ["SYNTHESIZER"]
    assert all(
        item["message_type"] != "BOUNDED_SYNTHESIS"
        for item in by_protocol["DYNAMIC_NO_SYNTHESIZER"]["formal_messages"]
    )


def test_two_ablation_bundles_feed_identified_effects_back_into_learning(tmp_path):
    source_paths = []
    for index in (1, 2):
        result = run_case(
            load_life_case(),
            tmp_path / f"ablation-{index}",
            authorized_ablation_plan(),
            provider_mode="scripted",
            bundle_id=f"fixture-bundle-{index}",
        )
        path = tmp_path / f"ablation-{index}" / "ablation_result.json"
        assert result["status"] == "PASS" and path.is_file()
        source_paths.append(path)

    feedback = run_feedback(
        tuple(source_paths),
        tmp_path / "feedback",
        context_key="context://life-cog3r/finding-classification",
        evidence_tier="SCRIPTED_FIXTURE",
        provider_mode="scripted",
    )

    components = {
        item["component_id"]: item for item in feedback["diagnosis"]["attribution"]["components"]
    }
    assert feedback["status"] == "PASS"
    assert all(feedback["gates"].values())
    assert components["COORDINATOR"]["matched_pair_count"] == 2
    assert components["ADVERSARIAL_REVIEWER"]["identifiability"] == "IDENTIFIED_MATCHED_ABLATION"
    assert components["REPLICATOR"]["identifiability"] == "IDENTIFIED_MATCHED_ABLATION"
    assert components["SYNTHESIZER"]["identifiability"] == "NOT_IDENTIFIABLE"
    assert (tmp_path / "feedback" / "manifest.json").is_file()
    assert (tmp_path / "feedback" / "AgentOS_OrganizationAblationLearningFeedback_ReturnPack_v0_1.zip").is_file()


def test_heterogeneous_matched_groups_identify_all_four_components(tmp_path):
    source_paths = []
    for label, plan in (
        ("core-1", authorized_ablation_plan()),
        ("core-2", authorized_ablation_plan()),
        ("synth-1", authorized_synthesizer_only_plan()),
        ("synth-2", authorized_synthesizer_only_plan()),
    ):
        output = tmp_path / label
        result = run_case(
            load_life_case(),
            output,
            plan,
            provider_mode="scripted",
            bundle_id=label,
        )
        assert result["status"] == "PASS"
        source_paths.append(output / "ablation_result.json")

    feedback = run_feedback(
        tuple(source_paths),
        tmp_path / "heterogeneous-feedback",
        context_key="context://life-cog3r/finding-classification",
        evidence_tier="SCRIPTED_FIXTURE",
        provider_mode="scripted",
    )

    components = feedback["diagnosis"]["attribution"]["components"]
    assert feedback["status"] == "PASS"
    assert all(item["matched_pair_count"] == 2 for item in components)
    assert all(item["identifiability"] == "IDENTIFIED_MATCHED_ABLATION" for item in components)
