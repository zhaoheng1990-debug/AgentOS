from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.comparative_plan_intent_experiment import (  # noqa: E402
    analyze_plan_intent_experiment,
    build_plan_intent_preregistration,
    run_plan_intent_experiment,
)
from local_collective_cognition.comparative_plan_intent_holdout import (  # noqa: E402
    build_comparative_plan_intent_holdout,
    validate_comparative_plan_intent_holdout,
)
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.selective_role_routing_experiment import (  # noqa: E402
    ROUTE_IDS,
)


class PlanFixture:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-plan-intent", model_id="fixture",
            task_kinds=(TASK_KIND,), max_timeout_seconds=180,
        )

    def invoke(self, task):
        item = task.inputs["public_case"]
        truth = self.corpus["private_provenance"]["bindings"][
            item["case_id"]
        ]
        supported = [
            (v["source_object_id"], v["target_object_id"])
            for v in truth["supported_targets"]
        ]
        null = truth["informative_null_targets"][0]
        null_pair = (null["source_object_id"], null["target_object_id"])
        objects = [v["object_id"] for v in item["object_registry"]]
        wrong = next(
            (s, t) for s in objects for t in objects
            if s != t and (s, t) not in {*supported, null_pair}
        )
        plan_arm = task.inputs["arm_id"] == "A2_PLAN_INTENT"
        targets = (
            [supported[0], supported[1], null_pair]
            if plan_arm else [supported[0], wrong, (objects[1], objects[2])]
        )
        spans = [v["span_id"] for v in item["evidence_spans"]]
        candidates = []
        for index, target in enumerate(targets, 1):
            frontier = target == null_pair
            value = {
                "candidate_id": f"C{index}",
                "lane": "FRONTIER" if frontier else "CORE",
                "question": f"Does {target[0]} alter {target[1]}?",
                "source_object_id": target[0],
                "target_object_id": target[1],
                "constraint_object_ids": list(
                    truth["hidden_constraint_object_ids"]
                ),
                "epistemic_basis": "SPECULATIVE" if frontier else "INFERRED",
                "structural_origin": "COUNTERFACTUAL" if frontier else "EVIDENCE",
                "falsifier": "Matched evidence shows no relation.",
                "required_observation": "Run one matched test.",
                "evidence_span_ids": [] if frontier else [spans[0], spans[-1]],
                "estimated_test_cost": "LOW",
            }
            if plan_arm:
                value["plan_route_id"] = "MECHANISM"
            candidates.append(value)
        raw = {
            "case_id": item["case_id"], "arm_id": "A1_ONTOLOGY",
            "problem_candidates": candidates, "selected_problem_id": "C1",
            "rationale": "Fixture.", "evidence_refs": list(task.allowed_evidence),
            "object_census": [
                {"object_id": v["object_id"], "object_type": "OBSERVABLE",
                 "anchor_span_ids": [spans[i % len(spans)]]}
                for i, v in enumerate(item["object_registry"])
            ],
        }
        if plan_arm:
            raw["plan_intent"] = {
                "route_assessments": [
                    {
                        "route_id": route,
                        "expected_net_cbit_band": (
                            "HIGH_POSITIVE" if route == "MECHANISM"
                            else "NEUTRAL"
                        ),
                        "fit_reason": "Fixture comparative utility.",
                        "anti_additive_risks": ["NONE"],
                        "confidence": "HIGH",
                    }
                    for route in ROUTE_IDS
                ],
                "selected_route_id": "MECHANISM",
                "execution_mode": "SPECIALIZED_ROUTE",
                "selection_margin": "CLEAR",
                "global_stop_condition": "Stop after three candidates.",
            }
        return {
            "result": raw,
            "usage": {"provider_calls": 1, "input_tokens": 60,
                      "output_tokens": 50 if plan_arm else 40},
            "provenance_refs": list(task.allowed_evidence),
        }


def _prior():
    analysis_c = {
        "decision": "REJECT_SELECTIVE_ROLE_ROUTING",
        "physical_total_tokens": 280000,
    }
    closure_c = {
        "candidate_state": "SELECTIVE_ROLE_ROUTING_REJECTED_STOP"
    }
    posthoc_c = {
        "status": "POSTHOC_DECOMPOSITION_NOT_FROZEN_GATE",
        "shadow_oracle_mean_gain_vs_baseline": 0.4,
    }
    return tuple({
        **value, "artifact_hash": hash_payload(value)
    } for value in (analysis_c, closure_c, posthoc_c))


def test_plan_holdout_is_fresh():
    corpus = build_comparative_plan_intent_holdout()
    validate_comparative_plan_intent_holdout(corpus)
    assert corpus["case_count"] == corpus["domain_count"] == 8
    assert corpus["prior_holdout_labels_reused"] is False


def test_single_call_plan_intent_can_pass_fixture():
    corpus = build_comparative_plan_intent_holdout()
    analysis0, closure0, posthoc0 = _prior()
    prereg = build_plan_intent_preregistration(
        corpus=corpus, prior_analysis=analysis0,
        prior_closure=closure0, prior_posthoc=posthoc0,
    )
    run = run_plan_intent_experiment(
        corpus=corpus, preregistration=prereg,
        adapter=PlanFixture(corpus),
    )
    analysis = analyze_plan_intent_experiment(
        corpus=corpus, preregistration=prereg, run=run
    )
    assert len(run["task_calls"]) == 48
    assert len(run["plan_receipts"]) == 24
    assert analysis["plan_intent_gate"] == "PASS"
    assert analysis["decision"] == "PASS_COMPARATIVE_PLAN_INTENT"
    assert analysis["pooled_contrast_metrics"]["median"] > 0
    assert analysis["external_semantic_panel_authorized"] is True
    assert analysis["core_integration_authorized"] is False
