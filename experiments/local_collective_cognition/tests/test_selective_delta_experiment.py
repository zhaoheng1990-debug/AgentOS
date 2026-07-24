from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.candidate_pool_arbitration import (  # noqa: E402
    build_candidate_pool,
)
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.selective_delta_experiment import (  # noqa: E402
    analyze_selective_delta_experiment,
    build_selective_delta_preregistration,
    run_selective_delta_experiment,
)
from local_collective_cognition.selective_delta_holdout import (  # noqa: E402
    build_selective_delta_holdout,
    validate_selective_delta_holdout,
)
from local_collective_cognition.null_role_candidate_composition import (  # noqa: E402
    compose_null_role_valued_pool,
    validate_null_role_valued_receipt,
)
from local_collective_cognition.runtime_escalation_policy import (  # noqa: E402
    derive_escalation_receipt,
)
from local_collective_cognition.selective_delta_policy import (  # noqa: E402
    build_delta_view,
    derive_selective_qualification,
    validate_single_delta,
)


class SelectiveDeltaFixture:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-selective-delta",
            model_id="fixture",
            task_kinds=(TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        counter = "delta_case" in task.inputs
        item = (
            task.inputs["delta_case"]
            if counter else task.inputs["public_case"]
        )
        truth = self.corpus["private_provenance"]["bindings"][
            item["case_id"]
        ]
        supported = [
            (value["source_object_id"], value["target_object_id"])
            for value in truth["supported_targets"]
        ]
        null_value = truth["informative_null_targets"][0]
        null_pair = (
            null_value["source_object_id"],
            null_value["target_object_id"],
        )
        object_ids = [
            value["object_id"] for value in item["object_registry"]
        ]
        wrong = [
            (source, target)
            for source in object_ids
            for target in object_ids
            if source != target
            and (source, target) not in {*supported, null_pair}
        ]
        targets = (
            [supported[1]]
            if counter else [supported[0], wrong[0], wrong[1]]
        )
        spans = [
            value["span_id"] for value in item["evidence_spans"]
        ]
        candidates = []
        for index, target in enumerate(targets, 1):
            valuable = target in supported
            frontier = not valuable and index == 3
            if counter:
                truth_state = "SUPPORTED_EFFECT"
                null_role = "RULES_OUT_PLAUSIBLE_CAUSE"
                expected_cbit = "HIGH"
                disposition = "PRIORITIZE"
                counterevidence = "EXPLICIT"
                constraint = "ADEQUATE"
            elif index == 1:
                truth_state = "SUPPORTED_EFFECT"
                null_role = "RULES_OUT_PLAUSIBLE_CAUSE"
                expected_cbit = "HIGH"
                disposition = "PRIORITIZE"
                counterevidence = "PARTIAL"
                constraint = "ADEQUATE"
            elif index == 2:
                truth_state = "INDIRECT"
                null_role = "CONSTRAINS_BOUNDARY"
                expected_cbit = "MEDIUM"
                disposition = "RETAIN"
                counterevidence = "PARTIAL"
                constraint = "PARTIAL"
            else:
                truth_state = "WEAK"
                null_role = "RULES_OUT_PLAUSIBLE_CAUSE"
                expected_cbit = "HIGH"
                disposition = "DEFER"
                counterevidence = "ABSENT"
                constraint = "ABSENT"
            candidates.append({
                "candidate_id": f"C{index}",
                "lane": "FRONTIER" if frontier else "CORE",
                "question": f"Does {target[0]} alter {target[1]}?",
                "source_object_id": target[0],
                "target_object_id": target[1],
                "constraint_object_ids": list(
                    truth["hidden_constraint_object_ids"]
                ),
                "epistemic_basis": (
                    "SPECULATIVE" if frontier else "INFERRED"
                ),
                "structural_origin": (
                    "COUNTERFACTUAL" if frontier else "EVIDENCE"
                ),
                "falsifier": "A matched intervention shows no relation.",
                "required_observation": "Run one matched test.",
                "evidence_span_ids": spans[:2] if counter else spans[:1],
                "estimated_test_cost": "LOW",
                "candidate_value": {
                    "relation_truth_state": truth_state,
                    "null_information_role": null_role,
                    "counterevidence_handling": counterevidence,
                    "constraint_binding": constraint,
                    "falsifiability": "SPECIFIC",
                    "expected_cbit": expected_cbit,
                    "research_value_disposition": disposition,
                    "evidence_span_ids": [spans[0]],
                    "rationale": "Fixture independent truth/null role.",
                },
            })
        raw = {
            "case_id": item["case_id"],
            "arm_id": "A1_ONTOLOGY",
            "problem_candidates": candidates,
            "selected_problem_id": "C1",
            "rationale": "Fixture.",
            "evidence_refs": list(task.allowed_evidence),
        }
        if not counter:
            raw["object_census"] = [
                {
                    "object_id": value["object_id"],
                    "object_type": "OBSERVABLE",
                    "anchor_span_ids": [spans[index % len(spans)]],
                }
                for index, value in enumerate(item["object_registry"])
            ]
        return {
            "result": raw,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 50,
                "output_tokens": 40,
            },
            "provenance_refs": list(task.allowed_evidence),
        }


def _prior():
    analysis_value = {
        "decision": "REJECT_NULL_ROLE_COMPOSITION",
        "candidate_state": "NULL_ROLE_REJECTED_STOP",
        "physical_total_tokens": 227390,
        "runtime_metrics": {
            "standard_null_role_contract_coverage": 1.0,
            "counter_null_role_contract_coverage": 1.0,
        },
        "composition_metrics": {
            "triggered_composition_gross_uplift": {"mean": 0.666667},
            "mean_added_token_penalty_cbit": 1.002167,
        },
    }
    closure_value = {
        "candidate_state": "NULL_ROLE_REJECTED_STOP"
    }
    posthoc_value = {
        "formal_decision_unchanged": True,
        "mean_fraction_of_positive_oracle_uplift_captured": 0.96,
        "positive_oracle_cell_count": 5,
    }
    return tuple({
        **value,
        "artifact_hash": hash_payload(value),
    } for value in (
        analysis_value, closure_value, posthoc_value
    ))


def test_selective_delta_contract_and_source_calibrated_composition():
    corpus = build_selective_delta_holdout()
    item = corpus["public_surface"]["items"][0]
    fixture = SelectiveDeltaFixture(corpus)
    standard_task = type("TaskLike", (), {
        "inputs": {
            "public_case": item,
            "stage": "STANDARD_SELECTIVE_DELTA",
        },
        "allowed_evidence": corpus["evidence_refs"],
    })()
    base = fixture.invoke(standard_task)["result"]
    assert validate_null_role_valued_receipt(
        raw_receipt=base, item=item, refs=corpus["evidence_refs"]
    ) == []
    escalation = derive_escalation_receipt(
        raw_receipt=base, item=item
    )
    qualification = derive_selective_qualification(
        raw_receipt=base, item=item,
        escalation_receipt=escalation,
    )
    assert qualification["qualified"] is True
    assert qualification["private_truth_used"] is False
    delta_view = build_delta_view(
        raw_receipt=base, item=item,
        qualification_receipt=qualification,
    )
    counter_task = type("TaskLike", (), {
        "inputs": {
            "delta_case": delta_view,
            "stage": "INDEPENDENT_COUNTER_SELECTIVE_DELTA",
        },
        "allowed_evidence": corpus["evidence_refs"],
    })()
    counter = fixture.invoke(counter_task)["result"]
    assert validate_single_delta(
        raw_receipt=counter, item=delta_view,
        refs=corpus["evidence_refs"],
        excluded_relation_ids=delta_view["excluded_relation_ids"],
    ) == []
    assert len(counter["problem_candidates"]) == 1
    pool = build_candidate_pool(
        provisional_receipt=base,
        counter_receipt=counter,
        item=item,
        replication_id="R1",
    )
    raw, receipt = compose_null_role_valued_pool(
        pool=pool, provisional_receipt=base,
        item=item, refs=corpus["evidence_refs"],
    )
    assert len({
        (value["source_object_id"], value["target_object_id"])
        for value in raw["problem_candidates"]
    }) == 3
    assert receipt["provider_selected_final_candidates"] is False


def test_selective_delta_experiment_can_pass_fixture():
    corpus = build_selective_delta_holdout()
    validate_selective_delta_holdout(corpus)
    prior_analysis, prior_closure, prior_posthoc = _prior()
    preregistration = build_selective_delta_preregistration(
        corpus=corpus,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
        prior_posthoc=prior_posthoc,
    )
    run = run_selective_delta_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=SelectiveDeltaFixture(corpus),
    )
    analysis = analyze_selective_delta_experiment(
        corpus=corpus, preregistration=preregistration, run=run
    )
    assert len(run["composition_receipts"]) == 24
    assert analysis["runtime_metrics"][
        "standard_selective_delta_contract_coverage"
    ] == 1
    assert analysis["runtime_metrics"][
        "counter_selective_delta_contract_coverage"
    ] == 1
    assert analysis["conditions"]["no_third_provider_call"] is True
    assert analysis["selective_delta_gate"] == "PASS"
    assert analysis["core_integration_authorized"] is False

