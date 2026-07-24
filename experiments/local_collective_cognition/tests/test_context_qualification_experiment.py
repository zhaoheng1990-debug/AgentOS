from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "agentos_core_slim_v0"),
    str(PACK),
    str(Path(__file__).resolve().parent),
]

from local_collective_cognition.context_qualification_experiment import (  # noqa: E402
    analyze_context_qualification_experiment,
    build_context_qualification_preregistration,
    run_context_qualification_experiment,
)
from local_collective_cognition.context_qualification_holdout import (  # noqa: E402
    build_context_qualification_holdout,
)
from local_collective_cognition.context_qualification_policy import (  # noqa: E402
    POLICY_VERSION,
    derive_context_qualification,
)
from local_collective_cognition.context_qualification_posthoc import (  # noqa: E402
    analyze_context_qualification_posthoc,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.runtime_escalation_policy import (  # noqa: E402
    derive_escalation_receipt,
)
from local_collective_cognition.selective_rejection_experiment import (  # noqa: E402
    build_selective_rejection_preregistration,
)
from local_collective_cognition.selective_rejection_holdout import (  # noqa: E402
    build_selective_rejection_holdout,
)
from test_reference_complete_portfolio_experiment import (  # noqa: E402
    _reference_audit,
)
from test_selective_rejection_experiment import (  # noqa: E402
    SelectiveFixture,
    _v051_sources,
)


def _artifact(value):
    return {**value, "artifact_hash": hash_payload(value)}


def _v052_sources():
    prior_prereg, prior_analysis51, prior_closure51, prior_posthoc51 = (
        _v051_sources()
    )
    corpus52 = build_selective_rejection_holdout()
    prereg52 = build_selective_rejection_preregistration(
        corpus=corpus52,
        reference_audit=_reference_audit(corpus52),
        prior_preregistration=prior_prereg,
        prior_analysis=prior_analysis51,
        prior_closure=prior_closure51,
        prior_posthoc=prior_posthoc51,
    )
    analysis = _artifact({
        "decision": "REJECT_SELECTIVE_REJECTION_REPLICATION",
        "candidate_state": "SELECTIVE_REJECTION_REJECTED_STOP",
        "physical_total_tokens": 148846,
        "replacement_gate_metrics": {"accepted_count": 3},
        "selective_rejection_metrics": {
            "coordinated_activation_count": 1,
        },
        "composition_metrics": {
            "triggered_composition_gross_uplift": {"mean": 2.0},
        },
    })
    closure = _artifact({
        "candidate_state": "SELECTIVE_REJECTION_REJECTED_STOP",
    })
    posthoc = _artifact({
        "classification_distribution": {"BENEFICIAL_ACCEPTED": 3},
        "coordinated_recovery_beneficial_count": 1,
        "coordinated_recovery_harmful_count": 0,
    })
    return prereg52, analysis, closure, posthoc


def _calibration():
    commitment = {
        "calibration_version": (
            "context_qualification_unlabeled_calibration_v0_53"
        ),
        "source_policy_version": POLICY_VERSION,
        "source_metrics": {
            "V0_51": {"new_qualified_count": 19},
            "V0_52": {"new_qualified_count": 17},
        },
        "source_count": 2,
        "total_receipt_count": 48,
        "old_qualified_count": 12,
        "new_qualified_count": 36,
        "qualification_basis_distribution": {
            "BOTH": 12,
            "LEGACY_ASYMMETRY": 4,
            "NONE": 8,
            "STRUCTURAL_OPPORTUNITY_GAP": 24,
        },
        "cross_source_rate_range": 0.083334,
        "private_outcomes_accessed": False,
        "posthoc_labels_accessed": False,
        "provider_calls_added": 0,
        "absolute_threshold_retuned_from_v0_41": False,
        "calibration_authority": "PREREGISTRATION_INPUT_ONLY",
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return _artifact(commitment)


def test_context_policy_qualifies_structural_gap_without_retuning():
    corpus = build_context_qualification_holdout()
    item = corpus["public_surface"]["items"][0]
    fixture = SelectiveFixture(corpus)
    raw = fixture._standard(item, "R1", corpus["evidence_refs"])
    escalation = derive_escalation_receipt(raw_receipt=raw, item=item)
    if not escalation["triggered"]:
        commitment = {
            key: value for key, value in escalation.items()
            if key != "artifact_hash"
        }
        commitment["triggered"] = True
        commitment["route_id"] = "ADVERSARIAL"
        commitment["diagnostic_flags"] = ["THIN_EVIDENCE_BINDING"]
        escalation = {
            **commitment, "artifact_hash": hash_payload(commitment)
        }
    receipt = derive_context_qualification(
        raw_receipt=raw, item=item, escalation_receipt=escalation
    )
    assert receipt["qualified"] is True
    assert receipt["structural_opportunity_gap_satisfied"] is True
    assert receipt["additional_provider_call_used"] is False
    assert receipt["absolute_threshold_retuned_from_v0_41"] is False


def test_context_qualification_fixture_closes_end_to_end():
    corpus = build_context_qualification_holdout()
    prereg52, analysis52, closure52, posthoc52 = _v052_sources()
    prereg = build_context_qualification_preregistration(
        corpus=corpus,
        reference_audit=_reference_audit(corpus),
        calibration=_calibration(),
        prior_preregistration=prereg52,
        prior_analysis=analysis52,
        prior_closure=closure52,
        prior_posthoc=posthoc52,
    )
    run = run_context_qualification_experiment(
        corpus=corpus,
        preregistration=prereg,
        adapter=SelectiveFixture(corpus),
    )
    analysis = analyze_context_qualification_experiment(
        corpus=corpus, preregistration=prereg, run=run
    )
    metrics = analysis["context_qualification_metrics"]
    assert metrics["context_policy_coverage"] == 1
    assert metrics["additional_provider_call_count"] == 0
    assert metrics["private_truth_use_count"] == 0
    assert metrics["structural_gap_qualified_count"] > 0
    posthoc = analyze_context_qualification_posthoc(
        corpus=corpus, run=run, analysis=analysis
    )
    assert posthoc["source_unlabeled_calibration_hash"] == (
        prereg["source_unlabeled_calibration_hash"]
    )
    assert analysis["core_integration_authorized"] is False
