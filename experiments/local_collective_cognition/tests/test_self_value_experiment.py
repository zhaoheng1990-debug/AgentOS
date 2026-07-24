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
from local_collective_cognition.self_value_experiment import (  # noqa: E402
    analyze_self_value_experiment,
    build_self_value_preregistration,
    run_self_value_experiment,
)
from local_collective_cognition.self_value_holdout import (  # noqa: E402
    build_self_value_holdout,
    validate_self_value_holdout,
)
from local_collective_cognition.self_valued_candidate_composition import (  # noqa: E402
    compose_self_valued_pool,
    validate_self_valued_receipt,
)


class SelfValueFixture:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-self-value",
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
            task.inputs["stage"] == "INDEPENDENT_COUNTER_SELF_VALUE"
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
                    "relation_evidence": (
                        "SUPPORTED_EFFECT" if target in supported
                        else "SUPPORTED_NULL" if target == null_pair
                        else "WEAK"
                    ),
                    "counterevidence_handling": (
                        "EXPLICIT" if valuable else "ABSENT"
                    ),
                    "constraint_binding": (
                        "ADEQUATE" if valuable else "ABSENT"
                    ),
                    "falsifiability": "SPECIFIC",
                    "expected_cbit": "HIGH" if valuable else "LOW",
                    "verdict": "ADMIT" if valuable else "REJECT",
                    "evidence_span_ids": [spans[0]],
                    "rationale": "Fixture self-value.",
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
    analysis_value = {
        "decision": "REJECT_CANDIDATE_VALUE_COMPOSITION",
        "candidate_state": "CANDIDATE_VALUE_REJECTED_STOP",
        "physical_total_tokens": 215884,
        "composition_metrics": {
            "triggered_composition_gross_uplift": {
                "mean": 0.708333,
                "loss_count": 0,
            }
        },
    }
    closure_value = {
        "candidate_state": "CANDIDATE_VALUE_REJECTED_STOP"
    }
    posthoc_value = {
        "formal_decision_unchanged": True,
        "mean_fraction_of_positive_oracle_uplift_captured": 0.636364,
    }
    return tuple({
        **value,
        "artifact_hash": hash_payload(value),
    } for value in (
        analysis_value, closure_value, posthoc_value
    ))


def test_self_value_contract_and_source_calibrated_composition():
    corpus = build_self_value_holdout()
    item = corpus["public_surface"]["items"][0]
    fixture = SelfValueFixture(corpus)
    standard_task = type("TaskLike", (), {
        "inputs": {
            "public_case": item,
            "stage": "STANDARD_SELF_VALUE",
        },
        "allowed_evidence": corpus["evidence_refs"],
    })()
    counter_task = type("TaskLike", (), {
        "inputs": {
            "public_case": item,
            "stage": "INDEPENDENT_COUNTER_SELF_VALUE",
        },
        "allowed_evidence": corpus["evidence_refs"],
    })()
    base = fixture.invoke(standard_task)["result"]
    counter = fixture.invoke(counter_task)["result"]
    assert validate_self_valued_receipt(
        raw_receipt=base, item=item, refs=corpus["evidence_refs"]
    ) == []
    pool = build_candidate_pool(
        provisional_receipt=base,
        counter_receipt=counter,
        item=item,
        replication_id="R1",
    )
    raw, receipt = compose_self_valued_pool(
        pool=pool, provisional_receipt=base,
        item=item, refs=corpus["evidence_refs"],
    )
    assert len({
        (value["source_object_id"], value["target_object_id"])
        for value in raw["problem_candidates"]
    }) == 3
    assert receipt["provider_selected_final_candidates"] is False


def test_self_value_experiment_can_pass_fixture():
    corpus = build_self_value_holdout()
    validate_self_value_holdout(corpus)
    prior_analysis, prior_closure, prior_posthoc = _prior()
    preregistration = build_self_value_preregistration(
        corpus=corpus,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
        prior_posthoc=prior_posthoc,
    )
    run = run_self_value_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=SelfValueFixture(corpus),
    )
    analysis = analyze_self_value_experiment(
        corpus=corpus, preregistration=preregistration, run=run
    )
    assert len(run["composition_receipts"]) == 24
    assert analysis["runtime_metrics"][
        "standard_self_value_contract_coverage"
    ] == 1
    assert analysis["runtime_metrics"][
        "counter_self_value_contract_coverage"
    ] == 1
    assert analysis["conditions"]["no_third_provider_call"] is True
    assert analysis["self_value_gate"] == "PASS"
    assert analysis["core_integration_authorized"] is False
