from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.collaborative_stability_experiment import (  # noqa: E402
    ROLE_IDS,
    analyze_collaborative_experiment,
    build_collaborative_preregistration,
    run_collaborative_experiment,
)
from local_collective_cognition.collaborative_stability_holdout import (  # noqa: E402
    build_collaborative_stability_holdout,
    validate_collaborative_stability_holdout,
)
from local_collective_cognition.collaborative_stability_posthoc import (  # noqa: E402
    analyze_collaborative_posthoc,
)
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


class CollaborativeFixtureProvider:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-collaborative-stability",
            model_id="fixture-model",
            task_kinds=(TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        stage = task.inputs["stage"]
        if stage == "EVIDENCE_ONLY_POOL_SELECTION":
            result = self._selector(task)
        else:
            result = self._proposal(task)
        return {
            "result": result,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 80,
                "output_tokens": 40,
                "latency_ms": 1,
            },
            "provenance_refs": list(task.allowed_evidence),
        }

    def _proposal(self, task):
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
        wrong = _wrong_relations(item, {*supported, null_pair})
        if task.inputs["stage"] == "EQUAL_COUNT_BASELINE":
            arm_id = task.inputs["arm_id"]
            targets = (
                [supported[0], wrong[0], wrong[1]]
                if arm_id == "A0_DIRECT"
                else [supported[0], supported[1], wrong[0]]
            )
        else:
            arm_id = "A1_ONTOLOGY"
            role_id = task.inputs["role_id"]
            targets = {
                "MECHANISM": [supported[0], supported[1], wrong[0]],
                "ADVERSARIAL": [supported[0], null_pair, wrong[1]],
                "COORDINATE_SHIFT": [
                    supported[1], null_pair, wrong[2]
                ],
            }[role_id]
        raw = {
            "case_id": item["case_id"],
            "arm_id": arm_id,
            "problem_candidates": [
                _candidate(
                    item, truth, target, index,
                    frontier=(target == null_pair),
                )
                for index, target in enumerate(targets, 1)
            ],
            "selected_problem_id": "C1",
            "rationale": "Fixture candidates.",
            "evidence_refs": list(task.allowed_evidence),
        }
        if arm_id == "A1_ONTOLOGY":
            spans = [
                value["span_id"] for value in item["evidence_spans"]
            ]
            raw["object_census"] = [
                {
                    "object_id": value["object_id"],
                    "object_type": "OBSERVABLE",
                    "anchor_span_ids": [spans[index % len(spans)]],
                }
                for index, value in enumerate(item["object_registry"])
            ]
        return raw

    def _selector(self, task):
        item = task.inputs["public_case"]
        truth = self.corpus["private_provenance"]["bindings"][
            item["case_id"]
        ]
        desired = {
            (
                value["source_object_id"],
                value["target_object_id"],
            )
            for value in [
                *truth["supported_targets"],
                *truth["informative_null_targets"],
            ]
        }
        selected = []
        for value in task.inputs["candidate_pool"]:
            candidate = value["candidate"]
            relation = (
                candidate["source_object_id"],
                candidate["target_object_id"],
            )
            if (
                relation in desired
                and relation not in {
                    (
                        prior["candidate"]["source_object_id"],
                        prior["candidate"]["target_object_id"],
                    )
                    for prior in selected
                }
            ):
                selected.append(value)
        ids = [value["pool_candidate_id"] for value in selected[:3]]
        return {
            "case_id": item["case_id"],
            "arm_id": "A2_COLLAB",
            "selected_candidate_ids": ids,
            "selected_problem_id": ids[0],
            "rationale": "Select the evidence-bound supported and null set.",
            "evidence_refs": list(task.allowed_evidence),
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


def _candidate(item, truth, target, index, *, frontier):
    spans = [value["span_id"] for value in item["evidence_spans"]]
    return {
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
        "falsifier": "A matched contrast shows no relation.",
        "required_observation": "Run a matched contrast.",
        "evidence_span_ids": [] if frontier else [spans[0], spans[-1]],
        "estimated_test_cost": "LOW",
    }


def _prior():
    analysis_commitment = {
        "decision": "REJECT_NO_STABLE_CBIT_GAIN",
        "total_tokens": 112000,
        "conditions": {
            "minimum_cross_replication_positive_consistency": False,
            "minimum_pooled_case_win_rate": False,
            "coverage": True,
            "cost": True,
        },
    }
    analysis = {
        **analysis_commitment,
        "artifact_hash": hash_payload(analysis_commitment),
    }
    closure_commitment = {
        "candidate_state": "FRONTIER_STABILITY_REJECTED_STOP",
        "stability_gate": "REJECT",
        "core_integration_authorized": False,
    }
    closure = {
        **closure_commitment,
        "artifact_hash": hash_payload(closure_commitment),
    }
    return analysis, closure


def test_collaborative_holdout_is_fresh_and_hash_bound():
    corpus = build_collaborative_stability_holdout()
    validate_collaborative_stability_holdout(corpus)
    assert corpus["case_count"] == corpus["domain_count"] == 10
    assert corpus["replication_ids"] == ["R1", "R2", "R3"]
    assert corpus["prior_holdout_labels_reused"] is False


def test_collaboration_passes_only_with_full_cost_and_pool_selection():
    corpus = build_collaborative_stability_holdout()
    prior_analysis, prior_closure = _prior()
    preregistration = build_collaborative_preregistration(
        corpus=corpus,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
    )
    run = run_collaborative_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=CollaborativeFixtureProvider(corpus),
    )
    analysis = analyze_collaborative_experiment(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    assert len(run["task_calls"]) == 180
    assert len(run["raw_receipts"]) == 180
    assert len(run["candidate_pools"]) == 30
    assert all(
        len(value["candidates"]) == len(ROLE_IDS) * 3
        for value in run["candidate_pools"].values()
    )
    assert analysis["collaborative_stability_gate"] == "PASS"
    assert analysis["decision"] == "PASS_COLLABORATIVE_STABILIZATION"
    assert analysis["conditions"]["all_a2_tokens_charged"] is True
    assert analysis["conditions"][
        "selector_did_not_generate_candidates"
    ] is True
    assert analysis["pooled_contrast_metrics"][
        "A2_MINUS_A1"
    ]["median"] > 0
    assert analysis["runtime_metrics"][
        "exact_three_coverage_per_arm"
    ] == {
        "A0_DIRECT": 1.0,
        "A1_ONTOLOGY": 1.0,
        "A2_COLLAB": 1.0,
    }
    assert analysis["external_semantic_panel_authorized"] is True
    assert analysis["core_integration_authorized"] is False
    posthoc = analyze_collaborative_posthoc(
        corpus=corpus, run=run, analysis=analysis
    )
    assert posthoc["status"] == "POSTHOC_CEILING_NOT_FROZEN_GATE"
    assert posthoc["changes_frozen_decision"] is False
    assert posthoc["pre_execution_role_router_oracle"][
        "mean"
    ] >= 0
