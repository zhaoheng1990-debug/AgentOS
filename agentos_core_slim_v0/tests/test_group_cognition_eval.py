import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import CognitionRunObservation, GroupCognitionEvalHarness


def observation(subject_id, quality, **overrides):
    values = {
        "subject_id": subject_id,
        "quality_score": quality,
        "hypotheses": (),
        "evidence_refs": (f"fixture://{subject_id}",),
    }
    values.update(overrides)
    return CognitionRunObservation(**values)


def test_group_evaluation_measures_gain_against_best_member_and_bounded_metrics():
    harness = GroupCognitionEvalHarness()
    members = (
        observation("agent-a", 0.62, hypotheses=("h1", "h2")),
        observation("agent-b", 0.74, hypotheses=("h2", "h3")),
    )
    group = observation(
        "ensemble-ab",
        0.86,
        errors_exposed=4,
        errors_corrected=3,
        candidates_admitted=5,
        candidates_survived=4,
        negative_transfer_opportunities=2,
        negative_transfer_intercepts=2,
        convergence_steps=3,
    )

    result = harness.evaluate("trial-1", members, group)

    assert result.best_member_id == "agent-b"
    assert result.group_delta_vs_best_member == 0.12
    assert result.error_correction_rate == 0.75
    assert result.candidate_survival_rate == 0.8
    assert result.hypothesis_diversity == 0.75
    assert result.negative_transfer_intercept_rate == 1.0
    assert result.verdict == "GROUP_OUTPERFORMS_BEST_MEMBER"
    assert result.proxy_boundary == "observable_trial_metrics_do_not_establish_group_cognition_ontology"


def test_threshold_can_treat_small_delta_as_parity():
    result = GroupCognitionEvalHarness(improvement_threshold=0.02).evaluate(
        "trial-parity",
        (observation("agent-a", 0.8),),
        observation("ensemble", 0.81),
    )

    assert result.verdict == "GROUP_AT_PARITY_WITH_BEST_MEMBER"


def test_invalid_observation_counts_fail_closed():
    with pytest.raises(ValueError, match="errors_corrected_exceeds_errors_exposed"):
        observation("agent-a", 0.5, errors_exposed=1, errors_corrected=2)


def test_duplicate_member_identity_is_rejected():
    harness = GroupCognitionEvalHarness()

    with pytest.raises(ValueError, match="duplicate_member_subject_id"):
        harness.evaluate(
            "trial-duplicate",
            (observation("agent-a", 0.5), observation("agent-a", 0.7)),
            observation("ensemble", 0.8),
        )
