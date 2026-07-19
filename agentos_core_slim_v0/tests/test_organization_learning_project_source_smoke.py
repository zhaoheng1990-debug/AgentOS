import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.organization_learning_project_source_smoke import run_smoke


EVIDENCE = ["evidence://organization-project-source"]


def source_payload(*, dynamic_score=0.9, marker="a"):
    receipts = []
    for arm, cbit, cost, candidate_marker in (
        ("BEST_MEMBER", 0.7, 0.05, "a"),
        ("FIXED_TEAM", 0.6, 0.5, "b"),
        ("DYNAMIC_TEAM", dynamic_score, 0.5, "c"),
    ):
        receipts.append(
            {
                "arm": arm,
                "observed_cbit_gain": cbit,
                "normalized_cost": cost,
                "convergence_steps": 1 if arm == "BEST_MEMBER" else 10,
                "errors_exposed": 1,
                "errors_corrected": 1,
                "negative_transfer_opportunities": 2,
                "negative_transfer_intercepts": 1,
                "evidence_refs": EVIDENCE,
                "receipt_hash": (marker + arm[0].lower()) * 32,
                "candidate_output_hash": candidate_marker * 64,
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
            "best_member_score": 0.7,
            "fixed_team_score": 0.6,
            "dynamic_team_score": dynamic_score,
            "best_member_subject_id": "solo",
            "fixed_team_subject_id": "fixed",
            "dynamic_team_subject_id": "dynamic",
        },
        "harness_receipts": receipts,
        "credit_profiles": [],
        "run_marker": marker,
    }


def test_single_source_trial_remains_exploratory_and_packages_receipts(tmp_path):
    source = tmp_path / "source.json"
    source.write_text(json.dumps(source_payload(dynamic_score=0.4)), encoding="utf-8")
    output = tmp_path / "output"

    result = run_smoke(
        (source,),
        output,
        context_key="context://single",
        evidence_tier="LIVE_PROJECT",
        provider_mode="scripted",
        expected_recommendation="REQUIRE_EXPLORATION",
    )

    assert result["status"] == "PASS"
    assert result["policy_candidate"]["incumbent_protocol"] == "SOLO"
    assert all(
        item["identifiability"] == "NOT_IDENTIFIABLE"
        for item in result["diagnosis"]["attribution"]["components"]
    )
    with zipfile.ZipFile(result["return_pack"]) as archive:
        assert "manifest.json" in archive.namelist()
        assert archive.testzip() is None


def test_three_unique_repeated_sources_can_form_dynamic_policy_candidate(tmp_path):
    sources = []
    for index, marker in enumerate(("d", "e", "f"), start=1):
        path = tmp_path / f"source-{index}.json"
        path.write_text(json.dumps(source_payload(marker=marker)), encoding="utf-8")
        sources.append(path)

    result = run_smoke(
        tuple(sources),
        tmp_path / "repeated-output",
        context_key="context://repeated",
        evidence_tier="SCRIPTED_FIXTURE",
        provider_mode="scripted",
        expected_recommendation="DYNAMIC_TEAM",
    )

    assert result["status"] == "PASS"
    assert result["policy_candidate"]["recommendation"] == "DYNAMIC_TEAM"
    assert result["policy_candidate"]["execution_authorized"] is False
    assert result["experiment_authorization"]["execution_authorized"] is True
