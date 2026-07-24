import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (  # noqa: E402
    DelayedRetrievalLedger,
    DelayedRetrievalPrediction,
    GradedSROCompatibilityGate,
    SerialSelectionWitness,
)
from agentos_kernel.provider_cognition_layer import (  # noqa: E402
    BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING,
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    ProviderBackedRuntimeCognitionLayer,
)


HASH_A = "a" * 64
HASH_B = "b" * 64


def precommitted_witness() -> SerialSelectionWitness:
    return SerialSelectionWitness(
        witness_id="PW-0002",
        status="PRECOMMITTED",
        selection_context_ref="selection://SCR-0006",
        sro_address_ref="sro://retention-routing",
        validity_boundary_ref="boundary://v1",
        reconstruction_ref="reconstruction://witness-protocol",
        authority_ref="authority://user-plus-kernel",
        privacy_boundary="reference_only_no_raw_chat",
        precommit_hash=HASH_A,
        sealed_at="2026-07-19T02:50:05+00:00",
        evidence_refs=("evidence://selection",),
    )


def matcher_receipt(**overrides):
    receipt = {
        "matcher_id": "matcher://graded-sro-v1",
        "matcher_version": "1.0",
        "task_id": "task://later-1",
        "witness_id": "PW-0002",
        "scope": "project_scoped",
        "evidence_refs": ["evidence://heldout"],
        "calibration_ref": "calibration://frozen-heldout",
        "provider_support_receipt_ref": "provider://sro-support",
        "replayable_evidence": True,
        "evidence_scope": "INTERNAL_PROJECT",
        "calibration_status": "FROZEN_PROJECT_SCOPED",
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
    }
    receipt.update(overrides)
    return receipt


def test_serial_witness_lifecycle_preserves_precommit_and_reference_only_roles():
    precommit = precommitted_witness()
    immediate = precommit.with_immediate_delta("delta://PW-0002", "evidence://delta")
    delayed = immediate.with_delayed_value("delayed://DR-0002", "evidence://delayed")

    assert precommit.status == "PRECOMMITTED"
    assert precommit.delta_ref == ""
    assert immediate.status == "IMMEDIATE_DELTA_OBSERVED"
    assert immediate.precommit_hash == precommit.precommit_hash
    assert delayed.status == "DELAYED_VALUE_OBSERVED"
    assert delayed.delayed_value_ref == "delayed://DR-0002"
    assert "raw_chat" not in delayed.as_dict()
    assert delayed.as_dict()["record_hash"]


def test_precommit_rejects_outcome_leakage():
    with pytest.raises(ValueError, match="precommitted_witness_cannot_contain_outcome_refs"):
        SerialSelectionWitness(
            **{**precommitted_witness().__dict__, "delta_ref": "delta://future"}
        )


def test_calibrated_internal_receipt_can_directly_reuse():
    decision = GradedSROCompatibilityGate().evaluate(matcher_receipt())

    assert decision.route == "DIRECT_REUSE"
    assert decision.candidate_admitted is True
    assert decision.reuse_allowed is True
    assert decision.hard_gate_failures == ()


def test_synthetic_formal_receipt_cannot_authorize_direct_reuse():
    decision = GradedSROCompatibilityGate().evaluate(
        matcher_receipt(
            evidence_scope="SYNTHETIC_FORMAL",
            calibration_status="FROZEN_HELD_OUT",
        )
    )

    assert decision.route == "LOCAL_RECONSTRUCTION"
    assert decision.reuse_allowed is False
    assert decision.reconstruction_required is True
    assert decision.reason == "synthetic_formal_evidence_cannot_authorize_direct_reuse"


def test_trace_insufficiency_routes_to_observe_not_model_abstention():
    decision = GradedSROCompatibilityGate().evaluate(
        matcher_receipt(trace_sufficiency=0.2, uncertainty=0.9)
    )

    assert decision.route == "OBSERVE"
    assert decision.observation_required is True
    assert decision.reason == "task_trace_or_validity_state_insufficient"


def test_model_uncertainty_routes_to_abstain():
    decision = GradedSROCompatibilityGate().evaluate(
        matcher_receipt(uncertainty=0.45)
    )

    assert decision.route == "ABSTAIN"
    assert "high_uncertainty" in decision.decision_factors
    assert decision.observation_required is False


def test_role_collision_rejects_despite_high_structural_match():
    decision = GradedSROCompatibilityGate().evaluate(
        matcher_receipt(structural_compatibility=0.96, role_compatibility=0.15)
    )

    assert decision.route == "REJECT"
    assert "role_incompatibility" in decision.decision_factors


def test_validity_drift_routes_to_revise_before_reuse():
    decision = GradedSROCompatibilityGate().evaluate(
        matcher_receipt(drift_risk=0.82, validity_state="DRIFTED")
    )

    assert decision.route == "REVISE"
    assert decision.revision_required is True
    assert decision.reuse_allowed is False


def test_interface_mismatch_downgrades_direct_prediction_to_local_reconstruction():
    decision = GradedSROCompatibilityGate().evaluate(
        matcher_receipt(interface_compatibility=0.45)
    )

    assert decision.route == "LOCAL_RECONSTRUCTION"
    assert decision.reconstruction_required is True


def test_invalid_probability_contract_fails_closed():
    probabilities = dict(matcher_receipt()["route_probabilities"])
    probabilities["DIRECT_REUSE"] = 0.90
    decision = GradedSROCompatibilityGate().evaluate(
        matcher_receipt(route_probabilities=probabilities)
    )

    assert decision.route == "ABSTAIN"
    assert "invalid:route_probability_sum" in decision.hard_gate_failures


def test_boolean_metric_is_not_treated_as_unit_interval_number():
    decision = GradedSROCompatibilityGate().evaluate(
        matcher_receipt(boundary_compatibility=True)
    )

    assert decision.route == "ABSTAIN"
    assert "invalid:boundary_compatibility" in decision.hard_gate_failures


def test_missing_provider_support_receipt_fails_closed():
    receipt = matcher_receipt()
    del receipt["provider_support_receipt_ref"]
    decision = GradedSROCompatibilityGate().evaluate(receipt)

    assert decision.route == "ABSTAIN"
    assert "missing:provider_support_receipt_ref" in decision.hard_gate_failures


def test_provider_layer_declares_and_fail_closes_graded_sro_operation():
    layer = ProviderBackedRuntimeCognitionLayer()
    operation_id = "graded_sro_retention_candidate_routing"
    contracts = {
        item["operation_id"]: item
        for item in layer.contract()["provider_required_operations"]
    }

    assert operation_id in contracts
    blocked = layer.audit_operation(operation_id, {"operation_id": operation_id})
    assert blocked["status"] == BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING
    complete = matcher_receipt()["route_probabilities"]
    receipt = {
        "route_probabilities": complete,
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
        "evidence_scope": "INTERNAL_PROJECT",
        "confidence": 0.82,
    }
    passed = layer.audit_operation(
        operation_id,
        {"operation_id": operation_id, "provider_support_receipt": receipt},
    )
    assert passed["status"] == PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT


def test_delayed_retrieval_prediction_reveal_and_hash_chain():
    ledger = DelayedRetrievalLedger()
    prediction = DelayedRetrievalPrediction(
        prediction_id="DR-0001",
        source_witness_id="PW-0001",
        target_task_id="PW-0002",
        predicted_route="LOCAL_RECONSTRUCTION",
        source_witness_hash=HASH_A,
        target_task_commitment_hash=HASH_B,
        sealed_at="2026-07-19T02:50:54+00:00",
        evidence_refs=("evidence://preoutcome",),
    )

    first = ledger.register_prediction(prediction)
    score = ledger.score_outcome(
        "DR-0001",
        observed_route="LOCAL_RECONSTRUCTION",
        role_reconstruction_fidelity=1.0,
        negative_transfer_penalty=0.0,
        outcome_ref="outcome://v1.8",
        outcome_hash=HASH_B,
        revealed_at="2026-07-19T02:59:52+00:00",
        scoring_authority_ref="authority://frozen-verifier",
    )
    second = ledger.events()[1]

    assert score.route_supported is True
    assert score.delayed_retrieval_score == 1.0
    assert first["previous_event_hash"] == ""
    assert second["previous_event_hash"] == first["event_hash"]
    assert ledger.score("DR-0001") == score


def test_delayed_outcome_cannot_precede_prediction_or_be_rewritten():
    ledger = DelayedRetrievalLedger()
    prediction = DelayedRetrievalPrediction(
        prediction_id="DR-0002",
        source_witness_id="PW-0002",
        target_task_id="PW-0003",
        predicted_route="OBSERVE",
        source_witness_hash=HASH_A,
        target_task_commitment_hash=HASH_B,
        sealed_at="2026-07-19T03:00:00+00:00",
        evidence_refs=("evidence://preoutcome",),
    )
    ledger.register_prediction(prediction)

    kwargs = {
        "observed_route": "OBSERVE",
        "role_reconstruction_fidelity": 0.8,
        "negative_transfer_penalty": 0.1,
        "outcome_ref": "outcome://future",
        "outcome_hash": HASH_B,
        "scoring_authority_ref": "authority://verifier",
    }
    with pytest.raises(ValueError, match="outcome_must_follow_prediction_seal"):
        ledger.score_outcome(
            "DR-0002",
            revealed_at="2026-07-19T02:59:59+00:00",
            **kwargs,
        )

    ledger.score_outcome(
        "DR-0002",
        revealed_at="2026-07-19T03:00:01+00:00",
        **kwargs,
    )
    with pytest.raises(ValueError, match="duplicate_delayed_retrieval_outcome"):
        ledger.score_outcome(
            "DR-0002",
            revealed_at="2026-07-19T03:00:02+00:00",
            **kwargs,
        )
