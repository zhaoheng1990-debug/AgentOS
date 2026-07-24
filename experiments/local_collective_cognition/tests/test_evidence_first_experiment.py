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
    build_context_qualification_preregistration,
)
from local_collective_cognition.context_qualification_holdout import (  # noqa: E402
    build_context_qualification_holdout,
)
from local_collective_cognition.evidence_first_contract import (  # noqa: E402
    AUDIT_ROLES,
    apply_evidence_first_gate,
)
from local_collective_cognition.evidence_first_experiment import (  # noqa: E402
    analyze_evidence_first_experiment,
    build_evidence_first_preregistration,
    run_evidence_first_experiment,
)
from local_collective_cognition.evidence_first_holdout import (  # noqa: E402
    build_evidence_first_holdout,
)
from local_collective_cognition.evidence_first_posthoc import (  # noqa: E402
    analyze_evidence_first_posthoc,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from test_context_qualification_experiment import (  # noqa: E402
    _calibration,
    _v052_sources,
)
from test_reference_complete_portfolio_experiment import (  # noqa: E402
    _reference_audit,
)
from test_selective_rejection_experiment import SelectiveFixture  # noqa: E402


def _artifact(value):
    return {**value, "artifact_hash": hash_payload(value)}


def _v053_sources():
    corpus = build_context_qualification_holdout()
    prior_prereg, prior_analysis, prior_closure, prior_posthoc = (
        _v052_sources()
    )
    prereg = build_context_qualification_preregistration(
        corpus=corpus,
        reference_audit=_reference_audit(corpus),
        calibration=_calibration(),
        prior_preregistration=prior_prereg,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
        prior_posthoc=prior_posthoc,
    )
    analysis = _artifact({
        "decision": "REJECT_CONTEXT_QUALIFICATION_REPLICATION",
        "candidate_state": "CONTEXT_QUALIFICATION_REJECTED_STOP",
        "physical_total_tokens": 346894,
        "context_qualification_metrics": {"qualified_count": 19},
        "replacement_gate_metrics": {"accepted_count": 7},
        "composition_metrics": {
            "triggered_composition_gross_uplift": {"mean": 2.0},
        },
    })
    closure = _artifact({
        "candidate_state": "CONTEXT_QUALIFICATION_REJECTED_STOP",
    })
    posthoc = _artifact({
        "classification_distribution": {
            "BENEFICIAL_ACCEPTED": 7,
            "BENEFICIAL_REJECTED": 7,
            "TIE_REJECTED": 3,
        },
        "coordinated_recovery_beneficial_count": 4,
        "coordinated_recovery_harmful_count": 0,
    })
    return prereg, analysis, closure, posthoc


class EvidenceFirstFixture(SelectiveFixture):
    def invoke(self, task):
        if "blind_case" not in task.inputs:
            return super().invoke(task)
        item = task.inputs["blind_case"]
        role = task.inputs["audit_role"]
        raw = {
            "case_id": item["case_id"],
            "audit_role": role,
            "source_blind_view_hash": item["artifact_hash"],
            "source_portfolio_view_hash": item[
                "source_portfolio_view_hash"
            ],
            "dropped_base_pool_id": item["dropped_base_pool_id"],
            "delta_pool_id": item["delta_pool_id"],
            "base_evidence_state": "PARTIALLY_RESOLVED",
            "delta_evidence_state": "RESOLVED_NULL",
            "base_realized_information_gain": "LOW",
            "delta_realized_information_gain": "HIGH",
            "base_future_test_option_value": "MEDIUM",
            "delta_future_test_option_value": "LOW",
            "base_relation_redundancy": "HIGH",
            "delta_relation_redundancy": "LOW",
            "resolved_evidence_counts_as_realized_cbit": True,
            "same_truth_state_is_not_relation_redundancy": True,
            "marginal_information_preference": "DELTA",
            "delta_has_higher_evidence_bound_marginal_cbit": True,
            "evidence_span_ids": [
                item["evidence_spans"][0]["span_id"]
            ],
            "rationale": "Fixture evidence-first review prefers delta.",
            "evidence_refs": list(task.allowed_evidence),
        }
        return {
            "result": raw,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 50,
                "output_tokens": 40,
            },
            "provenance_refs": list(task.allowed_evidence),
        }


def test_blind_roles_have_no_direct_activation_authority():
    provisional = {
        "problem_candidates": [{"candidate_id": "C1"}],
        "selected_problem_id": "C1",
    }
    proposed = {
        "problem_candidates": [{"candidate_id": "C2"}],
        "selected_problem_id": "C2",
    }
    composition = {
        "artifact_hash": hash_payload({"composition": 1}),
        "lineage": [],
    }
    portfolio = {
        "case_id": "EF-TEST",
        "artifact_hash": hash_payload({"view": 1}),
        "base_candidate": {
            "candidate_value": {
                "relation_truth_state": "UNRESOLVED"
            }
        },
        "base_candidate_disposition": "QUARANTINED_COMPONENT",
    }
    lineage = {
        "proposed_admission_lane": "QUARANTINE",
        "source_opportunity_hash": hash_payload({"opportunity": 1}),
    }
    initial = {
        "portfolio_decision": "KEEP_BASE_ACTIVE",
        "marginal_information_preference": "BASE",
        "opportunity_lineage_consistent": True,
        "delta_has_higher_marginal_cbit": False,
    }
    blind = [{
        "audit_role": role,
        "marginal_information_preference": "DELTA",
        "delta_has_higher_evidence_bound_marginal_cbit": True,
        "resolved_evidence_counts_as_realized_cbit": True,
        "same_truth_state_is_not_relation_redundancy": True,
    } for role in AUDIT_ROLES]
    _, _, gate = apply_evidence_first_gate(
        provisional_receipt=provisional,
        proposed_receipt=proposed,
        composition_receipt=composition,
        portfolio_view=portfolio,
        lineage_delta=lineage,
        cross_replication_witnesses=[],
        initial_receipt=initial,
        blind_receipts=blind,
    )
    assert gate["accepted"] is True
    assert gate["direct_arbiter_approved"] is False
    assert gate["blind_evidence_consensus"] is True
    assert gate["blind_roles_cannot_activate_directly"] is True
    assert gate["reason"] == "BLIND_EVIDENCE_CONSENSUS_ACTIVATION"


def test_evidence_first_fixture_closes_end_to_end():
    corpus = build_evidence_first_holdout()
    prior_prereg, prior_analysis, prior_closure, prior_posthoc = (
        _v053_sources()
    )
    prereg = build_evidence_first_preregistration(
        corpus=corpus,
        reference_audit=_reference_audit(corpus),
        calibration=_calibration(),
        prior_preregistration=prior_prereg,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
        prior_posthoc=prior_posthoc,
    )
    run = run_evidence_first_experiment(
        corpus=corpus,
        preregistration=prereg,
        adapter=EvidenceFirstFixture(corpus),
    )
    analysis = analyze_evidence_first_experiment(
        corpus=corpus, preregistration=prereg, run=run
    )
    assert run["blind_evidence_views"]
    assert all(
        "initial_portfolio_decision" not in value
        and "initial_rationale" not in value
        and value["initial_decision_available"] is False
        for value in run["blind_evidence_views"].values()
    )
    assert analysis["blind_evidence_metrics"][
        "role_contract_coverage"
    ] == 1
    assert analysis["blind_evidence_metrics"][
        "blind_consensus_activation_count"
    ] > 0
    assert analysis["blind_evidence_metrics"][
        "blind_direct_activation_count"
    ] == 0
    posthoc = analyze_evidence_first_posthoc(
        corpus=corpus, run=run, analysis=analysis
    )
    assert posthoc["formal_decision_unchanged"] is True
    assert posthoc["private_synthetic_outcomes_used_only_posthoc"] is True
