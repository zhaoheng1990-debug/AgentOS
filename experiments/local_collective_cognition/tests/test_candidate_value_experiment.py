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
from local_collective_cognition.candidate_value_composition import (  # noqa: E402
    build_blinded_candidate_view,
    compose_candidate_value_receipt,
    validate_candidate_value_receipt,
)
from local_collective_cognition.candidate_value_experiment import (  # noqa: E402
    analyze_candidate_value_experiment,
    build_candidate_value_preregistration,
    run_candidate_value_experiment,
)
from local_collective_cognition.candidate_value_holdout import (  # noqa: E402
    build_candidate_value_holdout,
    validate_candidate_value_holdout,
)
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


class CandidateValueFixture:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-candidate-value",
            model_id="fixture",
            task_kinds=(TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        item = task.inputs["public_case"]
        if task.inputs["stage"] == "SOURCE_BLIND_CANDIDATE_VALUE":
            return self._value_receipt(task, item)
        return self._candidate_receipt(task, item)

    def _candidate_receipt(self, task, item):
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
            task.inputs["stage"] == "INDEPENDENT_COUNTERPROPOSAL"
        )
        targets = (
            [supported[0], supported[1], null_pair]
            if counter else [supported[0], wrong[0], wrong[1]]
        )
        span_ids = [
            value["span_id"] for value in item["evidence_spans"]
        ]
        candidates = []
        for index, target in enumerate(targets, 1):
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
                "evidence_span_ids": (
                    span_ids[:2] if counter else span_ids[:1]
                ),
                "estimated_test_cost": "LOW",
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
                    "anchor_span_ids": [span_ids[index % len(span_ids)]],
                }
                for index, value in enumerate(item["object_registry"])
            ],
        }
        return {
            "result": raw,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 50,
                "output_tokens": 35,
            },
            "provenance_refs": list(task.allowed_evidence),
        }

    def _value_receipt(self, task, item):
        view = task.inputs["blinded_candidate_view"]
        serialized = str(view)
        assert "BASE:" not in serialized
        assert "COUNTER:" not in serialized
        truth = self.corpus["private_provenance"]["bindings"][
            item["case_id"]
        ]
        supported = {
            (value["source_object_id"], value["target_object_id"])
            for value in truth["supported_targets"]
        }
        nulls = {
            (value["source_object_id"], value["target_object_id"])
            for value in truth["informative_null_targets"]
        }
        span_id = item["evidence_spans"][0]["span_id"]
        evaluations = []
        for entry in view["entries"]:
            candidate = entry["candidate"]
            relation = (
                candidate["source_object_id"],
                candidate["target_object_id"],
            )
            valuable = relation in supported or relation in nulls
            evaluations.append({
                "opaque_candidate_id": entry["opaque_candidate_id"],
                "relation_id": entry["relation_id"],
                "relation_evidence": (
                    "SUPPORTED_EFFECT" if relation in supported
                    else "SUPPORTED_NULL" if relation in nulls
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
                "evidence_span_ids": [span_id],
                "rationale": "Fixture value judgment.",
            })
        raw = {
            "case_id": item["case_id"],
            "arm_id": "A2_VALUE_COMPOSED",
            "candidate_evaluations": evaluations,
            "evidence_refs": list(task.allowed_evidence),
        }
        return {
            "result": raw,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 45,
                "output_tokens": 30,
            },
            "provenance_refs": list(task.allowed_evidence),
        }


def _prior():
    analysis_value = {
        "decision": "REJECT_INDEPENDENT_ARBITRATION",
        "candidate_state": "INDEPENDENT_ARBITRATION_REJECTED_STOP",
        "physical_total_tokens": 234780,
    }
    closure_value = {
        "candidate_state": "INDEPENDENT_ARBITRATION_REJECTED_STOP"
    }
    posthoc_value = {
        "formal_decision_unchanged": True,
        "pool_oracle_gross_uplift": {"mean": 0.96875},
        "mean_fraction_of_positive_oracle_uplift_captured": 0.089286,
    }
    return tuple({
        **value,
        "artifact_hash": hash_payload(value),
    } for value in (
        analysis_value, closure_value, posthoc_value
    ))


def test_value_contract_is_source_blind_and_composes_distinct_relations():
    corpus = build_candidate_value_holdout()
    item = corpus["public_surface"]["items"][0]
    fixture = CandidateValueFixture(corpus)
    standard_task = type("TaskLike", (), {
        "inputs": {
            "public_case": item,
            "stage": "STANDARD_ONTOLOGY",
        },
        "allowed_evidence": corpus["evidence_refs"],
    })()
    counter_task = type("TaskLike", (), {
        "inputs": {
            "public_case": item,
            "stage": "INDEPENDENT_COUNTERPROPOSAL",
        },
        "allowed_evidence": corpus["evidence_refs"],
    })()
    base = fixture.invoke(standard_task)["result"]
    counter = fixture.invoke(counter_task)["result"]
    pool = build_candidate_pool(
        provisional_receipt=base,
        counter_receipt=counter,
        item=item,
        replication_id="R1",
    )
    blinded = build_blinded_candidate_view(
        pool=pool, replication_id="R1",
        corpus_hash=corpus["artifact_hash"],
    )
    assert all(
        "source_id" not in value for value in blinded["entries"]
    )
    task = type("TaskLike", (), {
        "inputs": {
            "public_case": item,
            "stage": "SOURCE_BLIND_CANDIDATE_VALUE",
            "blinded_candidate_view": {
                "entries": blinded["entries"],
            },
        },
        "allowed_evidence": corpus["evidence_refs"],
    })()
    value = fixture.invoke(task)["result"]
    assert validate_candidate_value_receipt(
        value_receipt=value, blinded_view=blinded,
        item=item, refs=corpus["evidence_refs"],
    ) == []
    raw, receipt = compose_candidate_value_receipt(
        value_receipt=value,
        blinded_view=blinded,
        pool=pool,
        provisional_receipt=base,
        item=item,
        refs=corpus["evidence_refs"],
    )
    assert len({
        (value["source_object_id"], value["target_object_id"])
        for value in raw["problem_candidates"]
    }) == 3
    assert receipt["provider_selected_final_candidates"] is False


def test_candidate_value_experiment_can_pass_fixture():
    corpus = build_candidate_value_holdout()
    validate_candidate_value_holdout(corpus)
    prior_analysis, prior_closure, prior_posthoc = _prior()
    preregistration = build_candidate_value_preregistration(
        corpus=corpus,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
        prior_posthoc=prior_posthoc,
    )
    run = run_candidate_value_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=CandidateValueFixture(corpus),
    )
    analysis = analyze_candidate_value_experiment(
        corpus=corpus, preregistration=preregistration, run=run
    )
    assert len(run["composition_receipts"]) == 24
    assert analysis["runtime_metrics"]["value_contract_coverage"] == 1
    assert analysis["runtime_metrics"]["source_blindness_coverage"] == 1
    assert analysis["candidate_value_gate"] == "PASS"
    assert analysis["external_semantic_panel_authorized"] is True
    assert analysis["core_integration_authorized"] is False
