import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (
    FrozenFindingTrialHarness,
    TrialFindingCatalogEntry,
    TrialFindingTruth,
)


EVIDENCE = ("evidence://fixture-a", "evidence://fixture-b")
CATALOG = (
    TrialFindingCatalogEntry("F1", "The primary local result survived its frozen check."),
    TrialFindingCatalogEntry("F2", "The broad causal interpretation is supported."),
    TrialFindingCatalogEntry("F3", "The unresolved alternative remains open."),
)
TRUTHS = (
    TrialFindingTruth("F1", "SUPPORTED"),
    TrialFindingTruth("F2", "REJECTED"),
    TrialFindingTruth("F3", "UNRESOLVED"),
)


def candidate(*, supported=("F1",), rejected=("F2",), unresolved=("F3",)):
    return {
        "answer": "Only the local result is supported; causality is rejected and one rival remains open.",
        "supported_finding_ids": list(supported),
        "rejected_finding_ids": list(rejected),
        "unresolved_finding_ids": list(unresolved),
        "rival_explanations": ["The unresolved alternative may explain the observation."],
        "falsifier": "A held-out intervention reverses the local result.",
        "evidence_refs": list(EVIDENCE),
        "uncertainties": ["External validity is unknown."],
    }


def test_hidden_finding_harness_measures_observed_cbit_without_provider_judgment():
    harness = FrozenFindingTrialHarness("frozen-finding-harness", TRUTHS)

    receipt = harness.evaluate(
        trial_id="trial-fixture",
        arm="DYNAMIC_TEAM",
        candidate_output=candidate(),
        finding_catalog=CATALOG,
        evidence_refs=EVIDENCE,
        provider_call_count=5,
        max_provider_calls=10,
        convergence_steps=5,
        execution_receipt_refs=("execution://1",),
    )

    assert receipt.observed_cbit_gain == 1.0
    assert receipt.errors_exposed == 1
    assert receipt.errors_corrected == 1
    assert receipt.negative_transfer_opportunities == 2
    assert receipt.negative_transfer_intercepts == 2
    assert receipt.normalized_cost == 0.5
    assert receipt.harness_owned
    assert not receipt.semantic_provider_used
    assert "expected_state" not in str(receipt.as_dict())


def test_finding_harness_penalizes_wrong_promotion_and_preserves_mechanical_counts():
    harness = FrozenFindingTrialHarness("frozen-finding-harness", TRUTHS)

    receipt = harness.evaluate(
        trial_id="trial-fixture",
        arm="FIXED_TEAM",
        candidate_output=candidate(supported=("F1", "F2", "F3"), rejected=(), unresolved=()),
        finding_catalog=CATALOG,
        evidence_refs=EVIDENCE,
        provider_call_count=4,
        max_provider_calls=10,
        convergence_steps=4,
        execution_receipt_refs=("execution://1",),
    )

    assert receipt.observed_cbit_gain < 0.5
    assert receipt.errors_corrected == 0
    assert receipt.negative_transfer_intercepts == 0
    assert receipt.finding_accuracy == pytest.approx(1 / 3)


@pytest.mark.parametrize(
    "payload,error",
    [
        (candidate(supported=("F1",), rejected=("F2",), unresolved=()), "candidate_finding_coverage_mismatch"),
        (
            candidate(supported=("F1", "F2"), rejected=("F2",), unresolved=("F3",)),
            "candidate_finding_classifications_overlap",
        ),
        (
            {**candidate(), "evidence_refs": ["evidence://outside"]},
            "candidate_evidence_surface_mismatch",
        ),
    ],
)
def test_finding_harness_fails_closed_on_noncomparable_candidate(payload, error):
    harness = FrozenFindingTrialHarness("frozen-finding-harness", TRUTHS)

    with pytest.raises(ValueError, match=error):
        harness.evaluate(
            trial_id="trial-fixture",
            arm="BEST_MEMBER",
            candidate_output=payload,
            finding_catalog=CATALOG,
            evidence_refs=EVIDENCE,
            provider_call_count=1,
            max_provider_calls=10,
            convergence_steps=1,
            execution_receipt_refs=("execution://1",),
        )


def test_harness_truth_must_exactly_match_public_catalog():
    harness = FrozenFindingTrialHarness("frozen-finding-harness", TRUTHS[:-1])

    with pytest.raises(ValueError, match="trial_truth_catalog_mismatch"):
        harness.evaluate(
            trial_id="trial-fixture",
            arm="BEST_MEMBER",
            candidate_output=candidate(),
            finding_catalog=CATALOG,
            evidence_refs=EVIDENCE,
            provider_call_count=1,
            max_provider_calls=10,
            convergence_steps=1,
            execution_receipt_refs=("execution://1",),
        )
