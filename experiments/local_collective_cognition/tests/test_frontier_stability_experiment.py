from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.frontier_stability_experiment import (  # noqa: E402
    analyze_stability_experiment,
    build_stability_preregistration,
    run_stability_experiment,
)
from local_collective_cognition.frontier_stability_holdout import (  # noqa: E402
    build_frontier_stability_holdout,
    validate_frontier_stability_holdout,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


class StabilityFixtureProvider:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-frontier-stability",
            model_id="fixture-model",
            task_kinds=(TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        item = task.inputs["public_case"]
        arm_id = task.inputs["arm_id"]
        truth = self.corpus["private_provenance"]["bindings"][
            item["case_id"]
        ]
        raw = _receipt(item, arm_id, truth, task.allowed_evidence)
        return {
            "result": raw,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 50,
                "output_tokens": 30 if arm_id == "A1_ONTOLOGY" else 20,
                "latency_ms": 1,
            },
            "provenance_refs": list(task.allowed_evidence),
        }


def _receipt(item, arm_id, truth, refs):
    objects = [value["object_id"] for value in item["object_registry"]]
    spans = [value["span_id"] for value in item["evidence_spans"]]
    supported = [
        (value["source_object_id"], value["target_object_id"])
        for value in truth["supported_targets"]
    ]
    null_target = truth["informative_null_targets"][0]
    null_pair = (
        null_target["source_object_id"], null_target["target_object_id"]
    )
    if arm_id == "A0_DIRECT":
        known = {*supported, null_pair}
        wrong = next(
            (source, target)
            for source in objects for target in objects
            if source != target and (source, target) not in known
        )
        targets = [
            (supported[0], "CORE", "INFERRED", "EVIDENCE"),
            (wrong, "FRONTIER", "SPECULATIVE", "COUNTERFACTUAL"),
        ]
    else:
        targets = [
            (supported[0], "CORE", "INFERRED", "EVIDENCE"),
            (supported[1], "CORE", "INFERRED", "EVIDENCE"),
            (null_pair, "FRONTIER", "SPECULATIVE", "COUNTERFACTUAL"),
        ]
    candidates = []
    for index, (target, lane, basis, origin) in enumerate(targets, 1):
        candidates.append({
            "candidate_id": f"C{index}",
            "lane": lane,
            "question": f"Does {target[0]} change {target[1]}?",
            "source_object_id": target[0],
            "target_object_id": target[1],
            "constraint_object_ids": list(
                truth["hidden_constraint_object_ids"]
            ),
            "epistemic_basis": basis,
            "structural_origin": origin,
            "falsifier": "A matched contrast shows no difference.",
            "required_observation": "Run one matched contrast.",
            "evidence_span_ids": [] if basis == "SPECULATIVE" else [spans[0]],
            "estimated_test_cost": "LOW",
        })
    raw = {
        "case_id": item["case_id"],
        "arm_id": arm_id,
        "problem_candidates": candidates,
        "selected_problem_id": "C1",
        "rationale": "Fixture stability candidates.",
        "evidence_refs": list(refs),
    }
    if arm_id == "A1_ONTOLOGY":
        raw["object_census"] = [
            {
                "object_id": object_id,
                "object_type": "OBSERVABLE",
                "anchor_span_ids": [spans[index % len(spans)]],
            }
            for index, object_id in enumerate(objects)
        ]
    return raw


def _prior():
    analysis_commitment = {
        "source_run_hash": "a" * 64,
        "a1_cbit_gain_per_case": 1.2,
        "total_tokens": 57000,
        "conditions": {
            "maximum_total_tokens": False,
            "coverage": True,
            "cbit_gain": True,
        },
    }
    analysis = {
        **analysis_commitment,
        "artifact_hash": hash_payload(analysis_commitment),
    }
    closure_commitment = {
        "candidate_state": "FRONTIER_GRAY_HOLDOUT_REJECTED_STOP",
        "frontier_holdout_gate": "REJECT",
        "core_integration_authorized": False,
    }
    closure = {
        **closure_commitment,
        "artifact_hash": hash_payload(closure_commitment),
    }
    return analysis, closure


def test_stability_holdout_is_fresh_and_hash_bound():
    corpus = build_frontier_stability_holdout()
    validate_frontier_stability_holdout(corpus)
    assert corpus["case_count"] == corpus["domain_count"] == 12
    assert corpus["v0_27_labels_reused"] is False
    assert corpus["replication_ids"] == ["R1", "R2"]


def test_stability_can_pass_higher_cbit_at_higher_cost():
    corpus = build_frontier_stability_holdout()
    prior_analysis, prior_closure = _prior()
    preregistration = build_stability_preregistration(
        corpus=corpus,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
    )
    run = run_stability_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=StabilityFixtureProvider(corpus),
    )
    analysis = analyze_stability_experiment(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    assert len(run["task_calls"]) == 48
    assert len(run["raw_receipts"]) == 48
    assert analysis["stability_gate"] == "PASS"
    assert analysis["decision"] == "PASS_HIGHER_CBIT_HIGHER_COST"
    assert analysis["pooled_case_win_rate"] == 1.0
    assert analysis["cross_replication_positive_consistency"] == 1.0
    assert analysis["external_semantic_panel_authorized"] is True
    assert analysis["core_integration_authorized"] is False
    assert preregistration["cost_policy"][
        "cbit_per_token_is_diagnostic_not_acceptance_gate"
    ] is True
