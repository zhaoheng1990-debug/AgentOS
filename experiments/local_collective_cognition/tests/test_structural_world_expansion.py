from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.structural_world_constraints import (  # noqa: E402
    build_science_institutional_constraints,
    validate_science_institutional_constraints,
)
from local_collective_cognition.structural_world_expansion import (  # noqa: E402
    ARM_IDS,
    TASK_KIND,
    analyze_structural_world_smoke,
    build_structural_world_preregistration,
    run_structural_world_smoke,
    validate_structural_world_receipt,
)
from local_collective_cognition.structural_world_holdout import (  # noqa: E402
    build_structural_world_holdout,
    validate_structural_world_holdout,
)


class StructuralWorldFixtureProvider:
    def __init__(self, corpus):
        self.corpus = corpus
        self.bindings = corpus["private_provenance"]["bindings"]
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-structural-world",
            model_id="fixture-model",
            task_kinds=(TASK_KIND,),
            max_timeout_seconds=180,
        )
        self.input_keys = []

    def invoke(self, task):
        self.input_keys.append(set(task.inputs))
        item = task.inputs["public_case"]
        arm_id = task.inputs["arm_id"]
        truth = self.bindings[item["case_id"]]
        result = _fixture_receipt(item, arm_id, truth, task.allowed_evidence)
        return {
            "result": result,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 40,
                "output_tokens": 20,
                "latency_ms": 1,
            },
            "provenance_refs": list(task.allowed_evidence),
        }


def _fixture_receipt(item, arm_id, truth, refs):
    object_ids = [value["object_id"] for value in item["object_registry"]]
    span_ids = [value["span_id"] for value in item["evidence_spans"]]
    targets = [
        (value["source_object_id"], value["target_object_id"])
        for value in truth["unresolved_targets"]
    ]
    if arm_id == "A0_DIRECT":
        wrong = next(
            (source, target)
            for source in object_ids
            for target in object_ids
            if source != target and (source, target) not in set(targets)
        )
        selected_targets = [targets[0], wrong]
    else:
        selected_targets = targets[:2]
    problems = []
    for index, (source, target) in enumerate(selected_targets, 1):
        problems.append({
            "problem_id": f"P{index}",
            "question": f"Does {source} account for variation in {target}?",
            "focal_object_ids": list(dict.fromkeys([
                source, target, *truth["primary_object_ids"]
            ])),
            "constraint_object_ids": list(
                truth["hidden_constraint_object_ids"]
            ),
            "target_relation": {
                "source_object_id": source,
                "target_object_id": target,
            },
            "question_type": (
                "CAUSAL" if index == 1 else "DISCRIMINATIVE"
            ),
            "coordinate": "CAUSAL" if index == 1 else "EVIDENCE",
            "falsifier": "A controlled contrast removes the association.",
            "required_observation": "Observe a matched contrast.",
            "evidence_span_ids": span_ids[:2],
        })
    census = []
    if arm_id != "A0_DIRECT":
        census = [
            {
                "object_id": object_id,
                "object_type": "OBSERVABLE",
                "anchor_span_ids": [span_ids[index % len(span_ids)]],
            }
            for index, object_id in enumerate(object_ids)
        ]
    graph = []
    if arm_id in {"A2_GRAPH", "A3_INTERVENTION"}:
        graph = [
            {
                "relation_id": f"R{index}",
                "source_object_id": value["source_object_id"],
                "relation_type": value["relation_type"],
                "target_object_id": value["target_object_id"],
                "epistemic_status": "OBSERVED",
                "evidence_span_ids": [span_ids[(index - 1) % len(span_ids)]],
            }
            for index, value in enumerate(truth["critical_relations"], 1)
        ]
    perspectives = []
    if arm_id in {"A2_GRAPH", "A3_INTERVENTION"}:
        perspectives = [
            {
                "perspective_id": "PV1",
                "bound_object_id": object_ids[0],
                "coordinate": "OBJECT",
                "observation": "Object-position view.",
            },
            {
                "perspective_id": "PV2",
                "bound_object_id": object_ids[1],
                "coordinate": "EVIDENCE",
                "observation": "Evidence-position view.",
            },
        ]
    interventions = []
    if arm_id == "A3_INTERVENTION":
        interventions = [{
            "intervention_id": "I1",
            "intervention_type": "REVERSE_RELATION",
            "target_object_ids": object_ids[:2],
            "target_relation_ids": [graph[0]["relation_id"]],
            "predicted_discrepancy": "The competing direction changes the test.",
        }]
    return {
        "case_id": item["case_id"],
        "arm_id": arm_id,
        "object_census": census,
        "relation_graph": graph,
        "situated_perspectives": perspectives,
        "interventions": interventions,
        "identified_constraint_object_ids": list(
            truth["hidden_constraint_object_ids"]
        ),
        "invariant_object_ids": list(truth["invariant_object_ids"]),
        "counterevidence_span_ids": list(
            truth["counterevidence_span_ids"]
        ),
        "problem_candidates": problems,
        "selected_problem_id": "P1",
        "synthesis": "Fixture candidate-only synthesis.",
        "evidence_refs": list(refs),
    }


def test_science_constraints_and_fresh_holdout_are_hash_bound():
    constraints = build_science_institutional_constraints()
    corpus = build_structural_world_holdout()
    validate_science_institutional_constraints(constraints)
    validate_structural_world_holdout(corpus)
    assert corpus["case_count"] == corpus["domain_count"] == 12
    assert corpus["prior_v0_25_labels_reused"] is False
    assert corpus["public_surface"]["private_labels_exposed"] is False
    for item in corpus["public_surface"]["items"]:
        assert not {
            "primary_object_ids", "hidden_constraint_object_ids",
            "critical_relations", "unresolved_targets",
        } & set(item)


def test_receipt_validator_rejects_unknown_object_reference():
    corpus = build_structural_world_holdout()
    item = corpus["public_surface"]["items"][0]
    truth = corpus["private_provenance"]["bindings"][item["case_id"]]
    receipt = _fixture_receipt(
        item, "A3_INTERVENTION", truth, corpus["evidence_refs"]
    )
    receipt["problem_candidates"][0]["focal_object_ids"] = ["O99"]
    with pytest.raises(ValueError, match="id_list_invalid"):
        validate_structural_world_receipt(
            receipt,
            item=item,
            arm_id="A3_INTERVENTION",
            evidence_refs=tuple(corpus["evidence_refs"]),
        )


def test_four_arm_runtime_is_blind_and_structural_gain_gate_is_replayable():
    constraints = build_science_institutional_constraints()
    corpus = build_structural_world_holdout()
    preregistration = build_structural_world_preregistration(
        constraints=constraints, corpus=corpus
    )
    adapter = StructuralWorldFixtureProvider(corpus)
    run = run_structural_world_smoke(
        constraints=constraints,
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
    )
    analysis = analyze_structural_world_smoke(
        constraints=constraints,
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    assert len(run["task_calls"]) == len(ARM_IDS) * corpus["case_count"]
    assert len(run["receipts"]) == 48
    assert not run["failures"]
    assert all(keys == {
        "stage", "arm_id", "method_name", "method_instructions",
        "public_case", "authority_boundary",
    } for keys in adapter.input_keys)
    assert analysis["structure_first_smoke_gate"] == "PASS"
    assert analysis["problem_target_f1_gain_over_direct"] >= 0.08
    assert analysis["fresh_replication_authorized"] is True
    assert analysis["recursive_society_authorized"] is False
    assert all(
        value["receipt_coverage"] == 1.0
        for value in analysis["arm_metrics"].values()
    )
