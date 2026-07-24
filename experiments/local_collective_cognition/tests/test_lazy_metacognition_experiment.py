from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.frontier_experiment import (  # noqa: E402
    TASK_KIND,
)
from local_collective_cognition.lazy_metacognition_experiment import (  # noqa: E402
    analyze_lazy_metacognition_experiment,
    build_lazy_metacognition_preregistration,
    run_lazy_metacognition_experiment,
)
from local_collective_cognition.lazy_metacognition_holdout import (  # noqa: E402
    build_lazy_metacognition_holdout,
    validate_lazy_metacognition_holdout,
)
from local_collective_cognition.provider_telemetry import (  # noqa: E402
    hash_payload,
)


class LazyFixture:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-lazy-metacognition",
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
        null = truth["informative_null_targets"][0]
        null_pair = (
            null["source_object_id"],
            null["target_object_id"],
        )
        objects = [
            value["object_id"] for value in item["object_registry"]
        ]
        wrong = next(
            (source, target)
            for source in objects
            for target in objects
            if source != target
            and (source, target) not in {*supported, null_pair}
        )
        stage = task.inputs["stage"]
        lazy_base = stage == "ONTOLOGY_WITH_LAZY_TRIGGER"
        worker = stage == "LAZY_SPECIALIZED_WORKER"
        triggered = item["case_id"] in {"LM-LAB", "LM-DRONE"}
        targets = (
            [supported[0], supported[1], null_pair]
            if lazy_base or worker
            else [supported[0], wrong, (objects[1], objects[2])]
        )
        spans = [
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
                    [] if frontier else [spans[0], spans[-1]]
                ),
                "estimated_test_cost": "LOW",
            })
        raw = {
            "case_id": item["case_id"],
            "arm_id": "A1_ONTOLOGY",
            "problem_candidates": candidates,
            "selected_problem_id": "C1",
            "rationale": "Fixture receipt.",
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
        if lazy_base:
            raw["escalation_trigger"] = {
                "triggered": triggered,
                "route_id": (
                    "ADVERSARIAL" if triggered else "A1_ONTOLOGY"
                ),
                "uncertainty_state": "HIGH" if triggered else "LOW",
                "expected_net_gain_band": (
                    "POSITIVE" if triggered else "NEUTRAL"
                ),
                "anti_additive_risks": ["NONE"],
                "evidence_span_ids": [spans[0], spans[-1]],
                "trigger_reason": "Fixture trigger decision.",
                "stop_condition": "Stop after one specialized receipt.",
            }
        return {
            "result": raw,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 60,
                "output_tokens": 45 if lazy_base else 35,
            },
            "provenance_refs": list(task.allowed_evidence),
        }


def _prior():
    analysis_commitment = {
        "decision": "REJECT_COMPARATIVE_PLAN_INTENT",
        "candidate_state": "COMPARATIVE_PLAN_INTENT_REJECTED_STOP",
        "total_tokens": 150000,
        "plan_metrics": {
            "selected_route_distribution": {"A1_ONTOLOGY": 24},
            "execution_mode_distribution": {"NO_ESCALATION": 24},
        },
    }
    analysis = {
        **analysis_commitment,
        "artifact_hash": hash_payload(analysis_commitment),
    }
    closure_commitment = {
        "candidate_state": "COMPARATIVE_PLAN_INTENT_REJECTED_STOP",
    }
    closure = {
        **closure_commitment,
        "artifact_hash": hash_payload(closure_commitment),
    }
    return analysis, closure


def test_lazy_metacognition_holdout_is_fresh():
    corpus = build_lazy_metacognition_holdout()
    validate_lazy_metacognition_holdout(corpus)
    assert corpus["case_count"] == corpus["domain_count"] == 8
    assert corpus["prior_holdout_labels_reused"] is False


def test_lazy_metacognition_dynamic_path_can_pass_fixture():
    corpus = build_lazy_metacognition_holdout()
    prior_analysis, prior_closure = _prior()
    preregistration = build_lazy_metacognition_preregistration(
        corpus=corpus,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
    )
    run = run_lazy_metacognition_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=LazyFixture(corpus),
    )
    analysis = analyze_lazy_metacognition_experiment(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    assert len(run["trigger_receipts"]) == 24
    assert len([
        value for value in run["task_calls"]
        if value["stage"] == "LAZY_SPECIALIZED_WORKER"
    ]) == 6
    assert analysis["trigger_metrics"]["trigger_rate"] == 0.25
    assert analysis["lazy_metacognition_gate"] == "PASS"
    assert analysis["decision"] == "PASS_LAZY_METACOGNITION"
    assert analysis["external_semantic_panel_authorized"] is True
    assert analysis["core_integration_authorized"] is False
