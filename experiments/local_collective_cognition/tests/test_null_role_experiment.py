from __future__ import annotations

import copy
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
from local_collective_cognition.null_role_experiment import (  # noqa: E402
    analyze_null_role_experiment,
    build_null_role_preregistration,
    run_null_role_experiment,
)
from local_collective_cognition.null_role_holdout import (  # noqa: E402
    build_null_role_holdout,
    validate_null_role_holdout,
)
from local_collective_cognition.null_role_candidate_composition import (  # noqa: E402
    compose_null_role_valued_pool,
    validate_null_role_valued_receipt,
)


class NullRoleFixture:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-null-role",
            model_id="fixture",
            task_kinds=(TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        item = task.inputs["public_case"]
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
        counter = (
            task.inputs["stage"] == "INDEPENDENT_COUNTER_NULL_ROLE"
        )
        targets = (
            [supported[0], supported[1], null_pair]
            if counter else [supported[0], wrong[0], wrong[1]]
        )
        spans = [
            value["span_id"] for value in item["evidence_spans"]
        ]
        candidates = []
        for index, target in enumerate(targets, 1):
            valuable = target in supported or target == null_pair
            frontier = target == null_pair
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
                    "relation_truth_state": (
                        "SUPPORTED_EFFECT" if target in supported
                        else "SUPPORTED_NULL" if target == null_pair
                        else "WEAK"
                    ),
                    "null_information_role": (
                        "RULES_OUT_PLAUSIBLE_CAUSE"
                        if target == null_pair
                        else "CONSTRAINS_BOUNDARY"
                        if not valuable and index == 2
                        else "NOT_APPLICABLE"
                    ),
                    "counterevidence_handling": (
                        "EXPLICIT" if valuable else "ABSENT"
                    ),
                    "constraint_binding": (
                        "ADEQUATE" if valuable else "ABSENT"
                    ),
                    "falsifiability": "SPECIFIC",
                    "expected_cbit": "HIGH" if valuable else "LOW",
                    "research_value_disposition": (
                        "PRIORITIZE" if target in supported
                        else "RETAIN" if target == null_pair
                        else "DISCARD"
                    ),
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
            "object_census": [
                {
                    "object_id": value["object_id"],
                    "object_type": "OBSERVABLE",
                    "anchor_span_ids": [spans[index % len(spans)]],
                }
                for index, value in enumerate(item["object_registry"])
            ],
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


def _prior():
    stop_value = {
        "decision": "STOP_CONTRACT_INFEASIBLE",
        "candidate_state": "TRUTH_VALUE_CONTRACT_STOP",
        "formal_benchmark_completed": False,
        "private_synthetic_outcomes_used": False,
        "maximum_possible_standard_contract_coverage": 0.9375,
        "frozen_minimum_standard_contract_coverage": 0.95,
        "contract_failure_reason_counts": {
            "NON_NULL_DISCRIMINATION_INVALID": 5
        },
    }
    closure_value = {
        "candidate_state": "TRUTH_VALUE_CONTRACT_STOP"
    }
    cost_value = {
        "analysis_version": "self_value_experiment_v0_38",
        "physical_total_tokens": 205471,
    }
    return tuple({
        **value,
        "artifact_hash": hash_payload(value),
    } for value in (
        stop_value, closure_value, cost_value
    ))


def test_null_role_contract_and_source_calibrated_composition():
    corpus = build_null_role_holdout()
    item = corpus["public_surface"]["items"][0]
    fixture = NullRoleFixture(corpus)
    standard_task = type("TaskLike", (), {
        "inputs": {
            "public_case": item,
            "stage": "STANDARD_NULL_ROLE",
        },
        "allowed_evidence": corpus["evidence_refs"],
    })()
    counter_task = type("TaskLike", (), {
        "inputs": {
            "public_case": item,
            "stage": "INDEPENDENT_COUNTER_NULL_ROLE",
        },
        "allowed_evidence": corpus["evidence_refs"],
    })()
    base = fixture.invoke(standard_task)["result"]
    counter = fixture.invoke(counter_task)["result"]
    assert validate_null_role_valued_receipt(
        raw_receipt=base, item=item, refs=corpus["evidence_refs"]
    ) == []
    prospective = base["problem_candidates"][1]["candidate_value"]
    assert prospective["relation_truth_state"] == "WEAK"
    assert prospective["null_information_role"] == "CONSTRAINS_BOUNDARY"
    invalid = copy.deepcopy(counter)
    invalid["problem_candidates"][2]["candidate_value"][
        "research_value_disposition"
    ] = "DISCARD"
    assert any(
        value.startswith("DISCRIMINATING_NULL_DISCARDED:")
        for value in validate_null_role_valued_receipt(
            raw_receipt=invalid, item=item,
            refs=corpus["evidence_refs"],
        )
    )
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


def test_null_role_experiment_can_pass_fixture():
    corpus = build_null_role_holdout()
    validate_null_role_holdout(corpus)
    prior_stop, prior_closure, cost_analysis = _prior()
    preregistration = build_null_role_preregistration(
        corpus=corpus,
        prior_stop=prior_stop,
        prior_closure=prior_closure,
        cost_analysis=cost_analysis,
    )
    run = run_null_role_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=NullRoleFixture(corpus),
    )
    analysis = analyze_null_role_experiment(
        corpus=corpus, preregistration=preregistration, run=run
    )
    assert len(run["composition_receipts"]) == 24
    assert analysis["runtime_metrics"][
        "standard_null_role_contract_coverage"
    ] == 1
    assert analysis["runtime_metrics"][
        "counter_null_role_contract_coverage"
    ] == 1
    assert analysis["conditions"]["no_third_provider_call"] is True
    assert analysis["null_role_gate"] == "PASS"
    assert analysis["core_integration_authorized"] is False

