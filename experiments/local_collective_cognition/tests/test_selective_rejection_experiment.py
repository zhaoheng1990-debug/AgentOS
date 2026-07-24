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

from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.reference_complete_portfolio_experiment import (  # noqa: E402
    build_reference_complete_portfolio_preregistration,
)
from local_collective_cognition.reference_complete_portfolio_holdout import (  # noqa: E402
    build_reference_complete_portfolio_holdout,
)
from local_collective_cognition.selective_rejection_contract import (  # noqa: E402
    validate_rejection_challenge,
    validate_rejection_coordination,
)
from local_collective_cognition.selective_rejection_experiment import (  # noqa: E402
    analyze_selective_rejection_experiment,
    build_selective_rejection_preregistration,
    run_selective_rejection_experiment,
)
from local_collective_cognition.selective_rejection_holdout import (  # noqa: E402
    build_selective_rejection_holdout,
    validate_selective_rejection_holdout,
)
from local_collective_cognition.selective_rejection_posthoc import (  # noqa: E402
    analyze_selective_rejection_posthoc,
)
from test_reference_complete_portfolio_experiment import (  # noqa: E402
    PortfolioFixture,
    _prior,
    _reference_audit,
)


class SelectiveFixture(PortfolioFixture):
    def invoke(self, task):
        if "challenge_case" in task.inputs:
            raw = self._challenge(
                task.inputs["challenge_case"], task.allowed_evidence
            )
        elif "coordination_case" in task.inputs:
            raw = self._coordination(
                task.inputs["coordination_case"],
                task.allowed_evidence,
            )
        elif "pairwise_case" in task.inputs:
            raw = self._pairwise(
                task.inputs["pairwise_case"], task.allowed_evidence
            )
            if task.inputs["replication_id"] != "R1":
                raw.update({
                    "portfolio_decision": "KEEP_BASE_ACTIVE",
                    "marginal_information_preference": "BASE",
                    "delta_has_higher_marginal_cbit": False,
                    "rationale": (
                        "Fixture initial arbiter conservatively keeps base."
                    ),
                })
        elif "delta_case" in task.inputs:
            raw = self._delta(
                task.inputs["delta_case"], task.allowed_evidence
            )
        else:
            raw = self._standard(
                task.inputs["public_case"],
                task.inputs.get("replication_id", "R1"),
                task.allowed_evidence,
            )
        return {
            "result": raw,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 50,
                "output_tokens": 40,
            },
            "provenance_refs": list(task.allowed_evidence),
        }

    @staticmethod
    def _challenge(item, refs):
        return {
            "case_id": item["case_id"],
            "source_challenge_view_hash": item["artifact_hash"],
            "source_portfolio_view_hash": item[
                "source_portfolio_view_hash"
            ],
            "source_initial_receipt_hash": item[
                "source_initial_receipt_hash"
            ],
            "dropped_base_pool_id": item["dropped_base_pool_id"],
            "delta_pool_id": item["delta_pool_id"],
            "initial_portfolio_decision": item[
                "initial_portfolio_decision"
            ],
            "initial_marginal_preference": item[
                "initial_marginal_preference"
            ],
            "base_evidence_resolution": "WEAK",
            "delta_evidence_resolution": "DIRECT",
            "base_hypothesis_space_reduction": "LOW",
            "delta_hypothesis_space_reduction": "HIGH",
            "base_portfolio_redundancy": "MEDIUM",
            "delta_portfolio_redundancy": "LOW",
            "novelty_without_evidence_detected": True,
            "relation_state_category_bias_detected": False,
            "challenge_decision": "REOPEN_DELTA",
            "delta_has_higher_evidence_bound_marginal_cbit": True,
            "evidence_span_ids": [
                item["evidence_spans"][0]["span_id"]
            ],
            "rationale": "Fixture evidence supports reopening.",
            "evidence_refs": list(refs),
        }

    @staticmethod
    def _coordination(item, refs):
        return {
            "case_id": item["case_id"],
            "source_coordination_view_hash": item["artifact_hash"],
            "source_portfolio_view_hash": item[
                "source_portfolio_view_hash"
            ],
            "source_initial_receipt_hash": item[
                "source_initial_receipt_hash"
            ],
            "source_challenge_receipt_hash": item[
                "source_challenge_receipt_hash"
            ],
            "dropped_base_pool_id": item["dropped_base_pool_id"],
            "delta_pool_id": item["delta_pool_id"],
            "initial_portfolio_decision": item[
                "initial_portfolio_decision"
            ],
            "challenge_decision": "REOPEN_DELTA",
            "coordination_decision": "ACTIVATE_DELTA",
            "marginal_information_preference": "DELTA",
            "evidence_conflict_resolved": True,
            "novelty_not_used_as_standalone_value": True,
            "relation_state_category_priority_forbidden": True,
            "delta_has_higher_marginal_cbit": True,
            "evidence_span_ids": [
                item["evidence_spans"][0]["span_id"]
            ],
            "rationale": "Fixture coordinator confirms delta.",
            "evidence_refs": list(refs),
        }


def _v051_sources():
    old_corpus = build_reference_complete_portfolio_holdout()
    analysis0, closure0, posthoc0 = _prior()
    old_prereg = build_reference_complete_portfolio_preregistration(
        corpus=old_corpus,
        reference_audit=_reference_audit(old_corpus),
        prior_analysis=analysis0,
        prior_closure=closure0,
        prior_posthoc=posthoc0,
    )
    values = (
        {
            "decision": "REJECT_REFERENCE_COMPLETE_PORTFOLIO_REPLICATION",
            "candidate_state": "REFERENCE_COMPLETE_PORTFOLIO_REJECTED_STOP",
            "physical_total_tokens": 188231,
            "replacement_gate_metrics": {"accepted_count": 4},
            "composition_metrics": {
                "triggered_composition_gross_uplift": {
                    "mean": 1.5,
                    "win_rate": 1.0,
                },
            },
        },
        {
            "candidate_state": (
                "REFERENCE_COMPLETE_PORTFOLIO_REJECTED_STOP"
            ),
        },
        {
            "formal_decision_unchanged": True,
            "mean_fraction_of_positive_oracle_uplift_captured": 0.5,
            "positive_oracle_cell_count": 8,
            "classification_distribution": {
                "BENEFICIAL_ACCEPTED": 4,
                "BENEFICIAL_REJECTED": 4,
            },
        },
    )
    return (
        old_prereg,
        *({
            **value, "artifact_hash": hash_payload(value)
        } for value in values),
    )


def test_selective_rejection_fixture_closes_end_to_end():
    corpus = build_selective_rejection_holdout()
    validate_selective_rejection_holdout(corpus)
    prior_prereg, prior_analysis, prior_closure, prior_posthoc = (
        _v051_sources()
    )
    preregistration = build_selective_rejection_preregistration(
        corpus=corpus,
        reference_audit=_reference_audit(corpus),
        prior_preregistration=prior_prereg,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
        prior_posthoc=prior_posthoc,
    )
    run = run_selective_rejection_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=SelectiveFixture(corpus),
    )
    analysis = analyze_selective_rejection_experiment(
        corpus=corpus, preregistration=preregistration, run=run
    )
    assert run["rejection_challenge_valid_keys"]
    assert run["rejection_coordination_valid_keys"]
    assert analysis["selective_rejection_metrics"][
        "direct_challenge_activation_count"
    ] == 0
    assert analysis["selective_rejection_metrics"][
        "challenge_contract_coverage"
    ] == 1
    assert analysis["selective_rejection_metrics"][
        "coordination_contract_coverage"
    ] == 1
    assert all(
        receipt["challenge_cannot_activate_directly"] is True
        for receipt in run["replacement_gate_receipts"].values()
    )
    key = run["rejection_challenge_valid_keys"][0]
    challenge = run["rejection_challenge_receipts"][key]
    view = run["rejection_challenge_views"][key]
    assert validate_rejection_challenge(
        receipt=challenge, item=view, refs=corpus["evidence_refs"]
    ) == []
    coordination = run["rejection_coordination_receipts"][key]
    coordination_view = run["rejection_coordination_views"][key]
    assert validate_rejection_coordination(
        receipt=coordination,
        item=coordination_view,
        refs=corpus["evidence_refs"],
    ) == []
    bad = {
        **challenge,
        "challenge_decision": "REOPEN_DELTA",
        "delta_has_higher_evidence_bound_marginal_cbit": False,
    }
    assert "REJECTION_CHALLENGE_REOPEN_UNSUPPORTED" in (
        validate_rejection_challenge(
            receipt=bad, item=view, refs=corpus["evidence_refs"]
        )
    )
    assert analysis["core_integration_authorized"] is False
    posthoc = analyze_selective_rejection_posthoc(
        corpus=corpus, run=run, analysis=analysis
    )
    assert posthoc["coordinated_recovery_count"] > 0
    assert posthoc["coordinated_recovery_harmful_count"] == 0
