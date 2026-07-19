import json
from hashlib import sha256
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (
    CreditProfile,
    OrganizationLearningEvaluator,
    OrganizationTrialRecord,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
)
from agentos_runtime import (
    CognitiveOrganizationLearningRuntime,
    OrganizationLearningSeed,
    organization_records_from_execution_smoke_result,
)


EVIDENCE = ("evidence://organization-learning",)
CONTEXT = "context://life-cog3r/finding-classification"
TIER = "LIVE_PROJECT"


class StaticDiagnosisProvider:
    def __init__(self, result_factory):
        self.profile = ProviderCapabilityProfile(
            provider_id="diagnosis-provider",
            model_id="diagnosis-model",
            task_kinds=("cognitive_organization_failure_diagnosis",),
            max_timeout_seconds=120,
        )
        self.result_factory = result_factory
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        return {
            "result": self.result_factory(task),
            "usage": {"total_tokens": 20},
            "provenance_refs": list(task.allowed_evidence),
        }


def record(
    group,
    protocol,
    score,
    *,
    context=CONTEXT,
    tier=TIER,
    cbit=None,
    cost=0.2,
    source_hash=None,
):
    execution_hash = sha256(f"{group}:{protocol}:execution".encode()).hexdigest()
    source_result_hash = source_hash or sha256(f"{group}:source".encode()).hexdigest()
    return OrganizationTrialRecord.create(
        record_id=f"record-{group}-{protocol.lower()}",
        trial_group_id=group,
        context_key=context,
        evidence_tier=tier,
        protocol_id=protocol,
        effectiveness_score=score,
        observed_cbit_gain=score if cbit is None else cbit,
        normalized_cost=cost,
        convergence_steps=1 if protocol == "SOLO" else 8,
        errors_exposed=2,
        errors_corrected=round(score * 2),
        negative_transfer_opportunities=2,
        negative_transfer_intercepts=round(score * 2),
        evidence_refs=EVIDENCE,
        harness_receipt_ref=f"harness://{group}/{protocol.lower()}",
        execution_result_hash=execution_hash,
        source_result_hash=source_result_hash,
        replay_valid=True,
    )


def complete_group(group, *, solo=0.7, fixed=0.6, dynamic=0.9):
    return (
        record(group, "SOLO", solo, cost=0.05),
        record(group, "FIXED_TEAM", fixed, cost=0.5),
        record(group, "DYNAMIC_TEAM", dynamic, cost=0.5),
    )


def diagnosis_result(task, *, causal_status="HYPOTHESIS_ONLY", variants=None):
    return {
        "failure_modes": ["Coordination may add cost without improving finding accuracy."],
        "component_hypotheses": [
            {
                "component_id": "COORDINATOR",
                "direction": "UNCERTAIN",
                "causal_status": causal_status,
                "rationale": "A matched ablation is required before a causal claim.",
                "evidence_refs": list(EVIDENCE),
            }
        ],
        "coordination_cost_assessment": "The team used more calls than the solo arm.",
        "next_experiment_variants": variants or ["DYNAMIC_NO_COORDINATOR"],
        "confidence": 0.5,
        "evidence_refs": list(EVIDENCE),
    }


def make_runtime(tmp_path, provider, *, min_trials=2, credits=None):
    return CognitiveOrganizationLearningRuntime(
        runtime_id="organization-learning",
        seed=OrganizationLearningSeed(
            context_key=CONTEXT,
            evidence_tier=TIER,
            evidence_refs=EVIDENCE,
            allowed_experiment_variants=(
                "SOLO",
                "FIXED_TEAM",
                "DYNAMIC_TEAM",
                "DYNAMIC_NO_COORDINATOR",
                "DYNAMIC_NO_REVIEWER",
                "DYNAMIC_NO_REPLICATOR",
                "DYNAMIC_NO_SYNTHESIZER",
            ),
            minimum_repeated_trials=min_trials,
            improvement_threshold=0.02,
        ),
        diagnosis_router=ProviderTaskRouter([provider]),
        workspace_root=tmp_path,
        advisory_credit_profiles=credits or {},
    )


def test_single_live_trial_stays_exploratory_and_role_causality_not_identifiable(tmp_path):
    provider = StaticDiagnosisProvider(lambda task: diagnosis_result(task))
    runtime = make_runtime(tmp_path, provider)
    runtime.admit_records(complete_group("trial-1", solo=0.9925, fixed=0.585, dynamic=0.455))

    diagnosis = runtime.diagnose()
    policy = runtime.synthesize_policy()

    assert all(item.identifiability == "NOT_IDENTIFIABLE" for item in diagnosis.attribution.components)
    assert policy.recommendation == "REQUIRE_EXPLORATION"
    assert policy.incumbent_protocol == "SOLO"
    assert policy.execution_authorized is False
    assert policy.route_selection_authority is False
    assert "protocol_id" not in provider.tasks[0].inputs.get("advisory_credit_profiles", {})


def test_only_matched_same_context_and_tier_ablations_identify_component_effects():
    evaluator = OrganizationLearningEvaluator(minimum_repeated_trials=2)
    records = []
    for group in ("trial-a", "trial-b"):
        records.extend(
            (
                record(group, "DYNAMIC_TEAM", 0.8),
                record(group, "DYNAMIC_NO_COORDINATOR", 0.6),
                record(group, "DYNAMIC_NO_REVIEWER", 0.9),
            )
        )
    records.append(record("trial-a", "DYNAMIC_NO_REPLICATOR", 0.1, context="context://other"))
    records.append(record("trial-b", "DYNAMIC_NO_REPLICATOR", 0.1, tier="SCRIPTED_FIXTURE"))

    report = evaluator.attribute(tuple(records), context_key=CONTEXT, evidence_tier=TIER)
    by_component = {item.component_id: item for item in report.components}

    assert by_component["COORDINATOR"].identifiability == "IDENTIFIED_MATCHED_ABLATION"
    assert by_component["COORDINATOR"].mean_effectiveness_contribution == pytest.approx(0.2)
    assert by_component["ADVERSARIAL_REVIEWER"].mean_effectiveness_contribution == pytest.approx(-0.1)
    assert by_component["REPLICATOR"].identifiability == "NOT_IDENTIFIABLE"


def test_repeated_protocol_evidence_rejects_duplicate_source_results():
    evaluator = OrganizationLearningEvaluator(minimum_repeated_trials=2)
    duplicate_source = "d" * 64
    records = tuple(
        record(group, protocol, score, source_hash=duplicate_source)
        for group in ("trial-a", "trial-b")
        for protocol, score in (("SOLO", 0.7), ("FIXED_TEAM", 0.6), ("DYNAMIC_TEAM", 0.9))
    )

    with pytest.raises(ValueError, match="organization_learning_duplicate_complete_source"):
        evaluator.evaluate_protocols(records, context_key=CONTEXT, evidence_tier=TIER)


def test_matched_ablation_requires_one_source_result_surface():
    evaluator = OrganizationLearningEvaluator(minimum_repeated_trials=2)
    records = (
        record("trial-a", "DYNAMIC_TEAM", 0.8, source_hash="e" * 64),
        record("trial-a", "DYNAMIC_NO_COORDINATOR", 0.6, source_hash="f" * 64),
    )

    with pytest.raises(ValueError, match="organization_learning_ablation_pair_surface_mismatch"):
        evaluator.attribute(records, context_key=CONTEXT, evidence_tier=TIER)


def test_trial_hash_fields_require_sha256_hex():
    with pytest.raises(ValueError, match="organization_trial_source_result_hash_invalid"):
        record("trial-a", "SOLO", 0.7, source_hash="not-a-hash")


def test_repeated_trials_select_observed_best_even_when_advisory_credit_favors_loser(tmp_path):
    provider = StaticDiagnosisProvider(lambda task: diagnosis_result(task))
    credits = {
        "SOLO": CreditProfile("solo", "operator", 10, 10.0, 0.0, 1.0, 0.9),
        "FIXED_TEAM": CreditProfile("fixed", "operator", 10, 6.0, 4.0, 0.6, 0.9),
        "DYNAMIC_TEAM": CreditProfile("dynamic", "operator", 10, 0.0, 10.0, 0.0, 0.9),
    }
    runtime = make_runtime(tmp_path, provider, credits=credits)
    runtime.admit_records(tuple(item for group in ("trial-1", "trial-2", "trial-3") for item in complete_group(group)))
    runtime.diagnose()

    policy = runtime.synthesize_policy()

    assert policy.recommendation == "DYNAMIC_TEAM"
    assert policy.incumbent_protocol == "DYNAMIC_TEAM"
    assert policy.protocol_statistics["DYNAMIC_TEAM"]["mean_effectiveness"] == pytest.approx(0.9)
    assert policy.credit_is_advisory is True
    assert policy.advisory_exploration_priorities[0] == "DYNAMIC_TEAM"
    assert policy.execution_authorized is False


def test_advisory_credit_profile_values_are_bounded(tmp_path):
    provider = StaticDiagnosisProvider(lambda task: diagnosis_result(task))
    invalid_credit = {
        "subject_id": "solo",
        "subject_kind": "operator",
        "event_count": 1,
        "positive_weight": 1.0,
        "negative_weight": 0.0,
        "trust_score": 2.0,
        "confidence": 0.5,
        "advisory_only": True,
        "selection_authority": False,
    }

    with pytest.raises(ValueError, match="organization_credit_profile_invalid"):
        make_runtime(tmp_path, provider, credits={"SOLO": invalid_credit})


def test_provider_cannot_claim_identified_component_without_matched_ablation(tmp_path):
    provider = StaticDiagnosisProvider(
        lambda task: diagnosis_result(task, causal_status="IDENTIFIED_MATCHED_ABLATION")
    )
    runtime = make_runtime(tmp_path, provider)
    runtime.admit_records(complete_group("trial-1"))

    with pytest.raises(ValueError, match="organization_diagnosis_unsupported_causal_claim"):
        runtime.diagnose()


def test_provider_identified_direction_must_match_frozen_ablation_effect(tmp_path):
    provider = StaticDiagnosisProvider(
        lambda task: {
            **diagnosis_result(task, causal_status="IDENTIFIED_MATCHED_ABLATION"),
            "component_hypotheses": [
                {
                    **diagnosis_result(task, causal_status="IDENTIFIED_MATCHED_ABLATION")[
                        "component_hypotheses"
                    ][0],
                    "direction": "HARMFUL",
                }
            ],
        }
    )
    runtime = make_runtime(tmp_path, provider)
    records = tuple(
        item
        for group in ("trial-a", "trial-b")
        for item in (
            record(group, "DYNAMIC_TEAM", 0.8),
            record(group, "DYNAMIC_NO_COORDINATOR", 0.6),
        )
    )
    runtime.admit_records(records)

    with pytest.raises(ValueError, match="organization_diagnosis_causal_direction_conflict"):
        runtime.diagnose()


def test_experiment_plan_is_bounded_and_requires_separate_kernel_authorization(tmp_path):
    provider = StaticDiagnosisProvider(
        lambda task: diagnosis_result(
            task,
            variants=["DYNAMIC_NO_COORDINATOR", "DYNAMIC_NO_REVIEWER"],
        )
    )
    runtime = make_runtime(tmp_path, provider)
    runtime.admit_records(complete_group("trial-1"))
    runtime.diagnose()
    runtime.synthesize_policy()

    proposal = runtime.propose_experiment(max_variants=2)
    authorization = runtime.authorize_experiment(
        kernel_authorization_ref="kernel://organization-learning/experiment",
        budget={"max_trial_runs": 3, "max_provider_calls_per_run": 20},
    )

    assert proposal.execution_authorized is False
    assert set(proposal.selected_variants).issubset(set(runtime.seed.allowed_experiment_variants))
    assert authorization.execution_authorized is True
    assert authorization.kernel_authorization_ref.startswith("kernel://")
    assert runtime.verify_replay()["valid"]


def test_unknown_provider_experiment_variant_fails_closed(tmp_path):
    provider = StaticDiagnosisProvider(
        lambda task: diagnosis_result(task, variants=["DYNAMIC_MAGIC_ROLE"])
    )
    runtime = make_runtime(tmp_path, provider)
    runtime.admit_records(complete_group("trial-1"))

    with pytest.raises(ValueError, match="organization_diagnosis_unknown_experiment_variant"):
        runtime.diagnose()


def test_matched_ablation_family_filters_provider_protocol_suggestions(tmp_path):
    provider = StaticDiagnosisProvider(
        lambda task: diagnosis_result(
            task,
            variants=["SOLO", "DYNAMIC_NO_COORDINATOR", "DYNAMIC_NO_REVIEWER"],
        )
    )
    runtime = make_runtime(tmp_path, provider)
    runtime.admit_records(complete_group("trial-1"))
    runtime.diagnose()
    runtime.synthesize_policy()

    proposal = runtime.propose_experiment(max_variants=3, experiment_family="MATCHED_ABLATION")

    assert proposal.selected_variants == (
        "DYNAMIC_NO_COORDINATOR",
        "DYNAMIC_NO_REVIEWER",
        "DYNAMIC_NO_REPLICATOR",
    )


def test_matched_ablation_family_can_authorize_all_four_components(tmp_path):
    provider = StaticDiagnosisProvider(
        lambda task: diagnosis_result(
            task,
            variants=["SOLO", "DYNAMIC_NO_COORDINATOR", "DYNAMIC_NO_REVIEWER"],
        )
    )
    runtime = make_runtime(tmp_path, provider)
    runtime.admit_records(complete_group("trial-1"))
    runtime.diagnose()
    runtime.synthesize_policy()

    proposal = runtime.propose_experiment(max_variants=4, experiment_family="MATCHED_ABLATION")

    assert proposal.selected_variants == (
        "DYNAMIC_NO_COORDINATOR",
        "DYNAMIC_NO_REVIEWER",
        "DYNAMIC_NO_REPLICATOR",
        "DYNAMIC_NO_SYNTHESIZER",
    )


def test_diagnosis_prompt_freezes_matched_ablation_sign_convention(tmp_path):
    provider = StaticDiagnosisProvider(lambda task: diagnosis_result(task))
    runtime = make_runtime(tmp_path, provider)
    runtime.admit_records(complete_group("trial-1"))

    runtime.diagnose()

    objective = provider.tasks[0].objective
    assert "DYNAMIC_TEAM minus its matched ablation" in objective
    assert "positive effectiveness contribution means BENEFICIAL" in objective
    assert "negative contribution means HARMFUL" in objective
    assert provider.tasks[0].inputs["kernel_causal_constraints"][0] == {
        "component_id": "COORDINATOR",
        "kernel_identifiability": "NOT_IDENTIFIABLE",
        "required_provider_causal_status": "HYPOTHESIS_ONLY",
        "mean_effectiveness_contribution": None,
        "required_direction_if_identified": "UNCERTAIN",
    }


def test_provider_evidence_aliases_resolve_to_admitted_refs_and_unknown_aliases_fail(tmp_path):
    aliased = StaticDiagnosisProvider(
        lambda task: {
            **diagnosis_result(task),
            "evidence_refs": ["E1"],
            "component_hypotheses": [
                {
                    **diagnosis_result(task)["component_hypotheses"][0],
                    "evidence_refs": ["E1"],
                }
            ],
        }
    )
    runtime = make_runtime(tmp_path / "aliased", aliased)
    runtime.admit_records(complete_group("trial-1"))

    receipt = runtime.diagnose()

    assert receipt.evidence_refs == EVIDENCE
    assert receipt.component_hypotheses[0]["evidence_refs"] == list(EVIDENCE)
    unknown = StaticDiagnosisProvider(
        lambda task: {**diagnosis_result(task), "evidence_refs": ["E999"]}
    )
    blocked = make_runtime(tmp_path / "unknown", unknown)
    blocked.admit_records(complete_group("trial-2"))
    with pytest.raises(ValueError, match="organization_diagnosis_evidence_refs_invalid"):
        blocked.diagnose()


def test_tampered_learning_event_chain_is_detected(tmp_path):
    provider = StaticDiagnosisProvider(lambda task: diagnosis_result(task))
    runtime = make_runtime(tmp_path, provider)
    runtime.admit_records(complete_group("trial-1"))
    events_path = runtime.public_store_path / "events.jsonl"
    event = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])
    event["payload"]["context_key"] = "tampered"
    lines = events_path.read_text(encoding="utf-8").splitlines()
    lines[0] = json.dumps(event)
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert runtime.verify_replay()["valid"] is False


def execution_smoke_payload():
    receipts = []
    for arm, cbit, cost, candidate_hash in (
        ("BEST_MEMBER", 1.0, 0.05, "a" * 64),
        ("FIXED_TEAM", 0.6, 0.5, "b" * 64),
        ("DYNAMIC_TEAM", 0.6, 0.5, "c" * 64),
    ):
        receipts.append(
            {
                "arm": arm,
                "observed_cbit_gain": cbit,
                "normalized_cost": cost,
                "convergence_steps": 1 if arm == "BEST_MEMBER" else 10,
                "errors_exposed": 1,
                "errors_corrected": 1 if arm != "DYNAMIC_TEAM" else 0,
                "negative_transfer_opportunities": 2,
                "negative_transfer_intercepts": 2 if arm == "BEST_MEMBER" else 1,
                "evidence_refs": list(EVIDENCE),
                "receipt_hash": (arm[0].lower() * 64),
                "candidate_output_hash": candidate_hash,
                "harness_owned": True,
                "semantic_provider_used": False,
            }
        )
    return {
        "status": "PASS",
        "gates": {
            "three_arms_completed": True,
            "all_arm_replays_valid": True,
            "execution_replay_valid": True,
            "harness_owns_observed_cbit": True,
            "hidden_truth_absent_from_provider_inputs": True,
        },
        "counterfactual_evaluation": {
            "best_member_score": 0.9925,
            "fixed_team_score": 0.585,
            "dynamic_team_score": 0.455,
        },
        "harness_receipts": receipts,
    }


def test_alpha6_execution_smoke_import_requires_gates_and_preserves_three_arm_metrics():
    payload = execution_smoke_payload()

    records = organization_records_from_execution_smoke_result(
        payload,
        context_key=CONTEXT,
        evidence_tier=TIER,
        trial_group_id="live-trial-1",
    )

    assert [item.protocol_id for item in records] == ["SOLO", "FIXED_TEAM", "DYNAMIC_TEAM"]
    assert [item.effectiveness_score for item in records] == [0.9925, 0.585, 0.455]
    assert all(item.replay_valid for item in records)
    payload["gates"]["all_arm_replays_valid"] = False
    with pytest.raises(ValueError, match="organization_import_execution_gates_incomplete"):
        organization_records_from_execution_smoke_result(
            payload,
            context_key=CONTEXT,
            evidence_tier=TIER,
            trial_group_id="live-trial-2",
        )
