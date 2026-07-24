from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.selective_role_routing_experiment import (  # noqa: E402
    analyze_selective_routing_experiment,
    build_routing_preregistration,
    run_selective_routing_experiment,
)
from local_collective_cognition.selective_role_routing_holdout import (  # noqa: E402
    build_selective_role_routing_holdout,
    validate_selective_role_routing_holdout,
)
from local_collective_cognition.selective_role_routing_posthoc import (  # noqa: E402
    analyze_routing_posthoc,
)


class RoutingFixtureProvider:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-selective-routing",
            model_id="fixture-model",
            task_kinds=(TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        stage = task.inputs["stage"]
        if stage == "PROVIDER_BACKED_STRUCTURAL_ROUTING":
            result = self._route(task)
            usage = {"input_tokens": 20, "output_tokens": 10}
        else:
            result = self._generate(task)
            usage = {"input_tokens": 60, "output_tokens": 40}
        return {
            "result": result,
            "usage": {
                **usage, "provider_calls": 1, "latency_ms": 1,
            },
            "provenance_refs": list(task.allowed_evidence),
        }

    def _route(self, task):
        item = task.inputs["public_case"]
        spans = [
            value["span_id"] for value in item["evidence_spans"]
        ]
        return {
            "case_id": item["case_id"],
            "route_id": "MECHANISM",
            "focal_object_ids": [
                item["object_registry"][0]["object_id"]
            ],
            "evidence_span_ids": [spans[0]],
            "expected_cbit_source": "MECHANISM_RESOLUTION",
            "uncertainty_risk": "MEDIUM",
            "route_rationale": "Resolve interacting causes.",
            "stop_condition": "Stop after three falsifiable relations.",
            "evidence_refs": list(task.allowed_evidence),
        }

    def _generate(self, task):
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
        known = {*supported, null_pair}
        wrong = _wrong_relations(item, known)
        route_id = task.inputs["route_id"]
        if task.inputs["stage"] == "BASELINE":
            targets = [supported[0], wrong[0], wrong[1]]
        elif route_id == "MECHANISM":
            targets = [supported[0], supported[1], null_pair]
        else:
            targets = [supported[0], wrong[0], wrong[1]]
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
                "falsifier": "A matched contrast shows no relation.",
                "required_observation": "Run a matched contrast.",
                "evidence_span_ids": (
                    [] if frontier else [spans[0], spans[-1]]
                ),
                "estimated_test_cost": "LOW",
            })
        return {
            "case_id": item["case_id"],
            "arm_id": "A1_ONTOLOGY",
            "problem_candidates": candidates,
            "selected_problem_id": "C1",
            "rationale": "Fixture routed candidates.",
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


def _wrong_relations(item, known):
    objects = [
        value["object_id"] for value in item["object_registry"]
    ]
    return [
        (source, target)
        for source in objects
        for target in objects
        if source != target and (source, target) not in known
    ]


def _prior():
    analysis_commitment = {
        "decision": "REJECT_COLLABORATIVE_STABILIZATION",
        "total_tokens": 497000,
    }
    analysis = {
        **analysis_commitment,
        "artifact_hash": hash_payload(analysis_commitment),
    }
    closure_commitment = {
        "candidate_state": "COLLABORATIVE_STABILITY_REJECTED_STOP",
        "collaborative_stability_gate": "REJECT",
        "core_integration_authorized": False,
    }
    closure = {
        **closure_commitment,
        "artifact_hash": hash_payload(closure_commitment),
    }
    posthoc_commitment = {
        "status": "POSTHOC_CEILING_NOT_FROZEN_GATE",
        "pre_execution_role_router_oracle": {
            "mean": 0.9,
            "majority_positive_case_count": 6,
        },
    }
    posthoc = {
        **posthoc_commitment,
        "artifact_hash": hash_payload(posthoc_commitment),
    }
    return analysis, closure, posthoc


def test_selective_routing_holdout_is_fresh_and_hash_bound():
    corpus = build_selective_role_routing_holdout()
    validate_selective_role_routing_holdout(corpus)
    assert corpus["case_count"] == corpus["domain_count"] == 10
    assert corpus["replication_ids"] == ["R1", "R2", "R3"]
    assert corpus["prior_holdout_labels_reused"] is False


def test_selective_routing_charges_router_and_passes_fixture():
    corpus = build_selective_role_routing_holdout()
    prior_analysis, prior_closure, prior_posthoc = _prior()
    preregistration = build_routing_preregistration(
        corpus=corpus,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
        prior_posthoc=prior_posthoc,
    )
    run = run_selective_routing_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=RoutingFixtureProvider(corpus),
    )
    analysis = analyze_selective_routing_experiment(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    assert len(run["task_calls"]) == 120
    assert len(run["raw_receipts"]) == 120
    assert len(run["route_receipts"]) == 30
    assert len(run["formal_projections"]) == 60
    assert len(run["shadow_route_projections"]) == 40
    assert analysis["selective_routing_gate"] == "PASS"
    assert analysis["decision"] == "PASS_SELECTIVE_ROLE_ROUTING"
    assert analysis["pooled_contrast_metrics"]["median"] > 0
    assert analysis["conditions"][
        "formal_path_cost_accounting_complete"
    ] is True
    assert analysis["shadow_regret_audit"][
        "top1_or_tied_accuracy"
    ] == 1.0
    assert analysis["external_semantic_panel_authorized"] is True
    assert analysis["core_integration_authorized"] is False
    posthoc = analyze_routing_posthoc(run=run, analysis=analysis)
    assert posthoc["changes_frozen_decision"] is False
    assert posthoc["router_token_cost_per_case"]["mean"] > 0
