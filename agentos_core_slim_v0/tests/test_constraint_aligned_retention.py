import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import ConstraintAlignedRetentionGate


def valid_candidate():
    return {
        "candidate_id": "valid",
        "scope": "project_scoped",
        "decision_status": "SUPPORTED_BOUNDED",
        "evidence_refs": ["fixture://valid"],
        "support_path": "claim://valid -> fixture://valid",
        "accept_decision_ref": "decision://valid",
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


def test_valid_candidate_is_eligible_for_project_scoped_retention():
    decision = ConstraintAlignedRetentionGate().evaluate(valid_candidate())

    assert decision.decision == "RETAIN_PROJECT_SCOPED"
    assert decision.eligible_for_retention is True
    assert decision.retention_score == 3.0


def test_low_alignment_is_a_hard_failure_despite_high_score():
    candidate = valid_candidate()
    candidate["constraint_alignment"] = 0.2

    decision = ConstraintAlignedRetentionGate().evaluate(candidate)

    assert decision.decision == "BLOCK_CONSTRAINT_MISALIGNMENT"
    assert decision.eligible_for_retention is False
    assert decision.retention_score == 3.0


def test_exact_threshold_does_not_retain():
    candidate = valid_candidate()
    candidate.update(
        {
            "future_cbit_gain_score": 0.5,
            "transferability": 0.5,
            "search_efficiency": 0.5,
            "residual_reduction": 0.5,
            "complexity": 0.5,
            "negative_transfer_score": 0.25,
            "scope_ambiguity": 0.25,
            "constraint_alignment": 0.7,
        }
    )

    decision = ConstraintAlignedRetentionGate().evaluate(candidate)

    assert decision.retention_score == 1.0
    assert decision.decision == "OBSERVE_LOW_RETENTION_SCORE"


def test_negative_transfer_routes_to_quarantine_without_retention_eligibility():
    candidate = valid_candidate()
    candidate["negative_transfer_detected"] = True

    decision = ConstraintAlignedRetentionGate().evaluate(candidate)

    assert decision.decision == "QUARANTINE_NEGATIVE_TRANSFER"
    assert decision.eligible_for_retention is False


def test_accept_string_cannot_replace_bounded_decision_status():
    candidate = valid_candidate()
    candidate["status"] = "ACCEPT_READY_WITH_EVIDENCE"
    candidate["decision_status"] = "PENDING"

    decision = ConstraintAlignedRetentionGate().evaluate(candidate)

    assert decision.decision == "BLOCK_UNSUPPORTED_DECISION"


def test_missing_metric_blocks_closed():
    candidate = valid_candidate()
    del candidate["transferability"]

    decision = ConstraintAlignedRetentionGate().evaluate(candidate)

    assert decision.decision == "BLOCK_INCOMPLETE_RETENTION_METRICS"
    assert "invalid_metric:transferability" in decision.hard_gate_failures
