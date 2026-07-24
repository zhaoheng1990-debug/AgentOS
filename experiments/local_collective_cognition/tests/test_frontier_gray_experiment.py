from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.frontier_cbit_ledger import (  # noqa: E402
    build_realized_cbit_ledger,
)
from local_collective_cognition.frontier_experiment import (  # noqa: E402
    TASK_KIND,
    analyze_frontier_holdout,
    analyze_frontier_preflight,
    build_frontier_preregistration,
    run_frontier_batch,
)
from local_collective_cognition.frontier_fresh_holdout import (  # noqa: E402
    build_frontier_fresh_holdout,
    build_frontier_preflight,
)
from local_collective_cognition.frontier_partial_admission import (  # noqa: E402
    project_frontier_receipt,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


class FrontierFixtureProvider:
    def __init__(self, corpus=None):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-frontier",
            model_id="fixture-model",
            task_kinds=(TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        item = task.inputs["public_case"]
        arm_id = task.inputs["arm_id"]
        truth = (
            self.corpus["private_provenance"]["bindings"][item["case_id"]]
            if self.corpus else None
        )
        raw = _raw_receipt(
            item, arm_id, task.allowed_evidence, truth=truth
        )
        return {
            "result": raw,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 50,
                "output_tokens": 20,
                "latency_ms": 1,
            },
            "provenance_refs": list(task.allowed_evidence),
        }


def _candidate(
    candidate_id, source, target, *, lane="CORE", basis="INFERRED",
    origin="EVIDENCE", constraints=(), evidence=("S1",),
):
    return {
        "candidate_id": candidate_id,
        "lane": lane,
        "question": f"Does {source} change {target}?",
        "source_object_id": source,
        "target_object_id": target,
        "constraint_object_ids": list(constraints),
        "epistemic_basis": basis,
        "structural_origin": origin,
        "falsifier": "A matched contrast shows no difference.",
        "required_observation": "Run one matched contrast.",
        "evidence_span_ids": list(evidence),
        "estimated_test_cost": "LOW",
    }


def _raw_receipt(item, arm_id, refs, *, truth=None):
    object_ids = [value["object_id"] for value in item["object_registry"]]
    span_ids = [value["span_id"] for value in item["evidence_spans"]]
    if truth is None:
        targets = [
            (object_ids[1], object_ids[0]),
            (object_ids[2], object_ids[0]),
        ]
    else:
        supported = [
            (value["source_object_id"], value["target_object_id"])
            for value in truth["supported_targets"]
        ]
        nulls = [
            (value["source_object_id"], value["target_object_id"])
            for value in truth["informative_null_targets"]
        ]
        if arm_id == "A0_DIRECT":
            wrong = next(
                (source, target)
                for source in object_ids for target in object_ids
                if source != target
                and (source, target) not in set([*supported, *nulls])
            )
            targets = [supported[0], wrong]
        else:
            targets = [*supported[:2], nulls[0]]
    candidates = []
    for index, (source, target) in enumerate(targets, 1):
        frontier = index == len(targets) and len(targets) == 3
        candidates.append(_candidate(
            f"P{index}", source, target,
            lane="FRONTIER" if frontier else "CORE",
            basis="SPECULATIVE" if frontier else "INFERRED",
            origin="COUNTERFACTUAL" if frontier else "EVIDENCE",
            constraints=(
                truth["hidden_constraint_object_ids"] if truth else ()
            ),
            evidence=() if frontier else (span_ids[0],),
        ))
    raw = {
        "case_id": item["case_id"],
        "arm_id": arm_id,
        "problem_candidates": candidates,
        "selected_problem_id": "P1",
        "rationale": "Fixture candidate set.",
        "evidence_refs": list(refs),
    }
    if arm_id == "A1_ONTOLOGY":
        raw["object_census"] = [
            {
                "object_id": object_id,
                "object_type": "OBSERVABLE",
                "anchor_span_ids": [span_ids[index % len(span_ids)]],
            }
            for index, object_id in enumerate(object_ids)
        ]
    return raw


def test_partial_admission_salvages_valid_and_speculative_components():
    artifact = build_frontier_preflight()
    item = artifact["public_surface"]["items"][0]
    raw = _raw_receipt(
        item, "A1_ONTOLOGY", artifact["evidence_refs"]
    )
    raw["problem_candidates"].append({
        **raw["problem_candidates"][0],
        "candidate_id": "BROKEN",
        "source_object_id": "O99",
    })
    raw["object_census"].append({
        "object_id": "O99",
        "object_type": "OBSERVABLE",
        "anchor_span_ids": ["S99"],
    })
    projection = project_frontier_receipt(
        raw_receipt=raw,
        item=item,
        arm_id="A1_ONTOLOGY",
        evidence_refs=tuple(artifact["evidence_refs"]),
    )
    assert projection["receipt_state"] == "PARTIAL_CANDIDATE"
    assert len(projection["eligible_candidate_ids"]) == 2
    assert sum(
        value["disposition"] == "QUARANTINED_COMPONENT"
        for value in [
            *projection["candidate_components"],
            *projection["census_components"],
        ]
    ) == 2


def test_boundary_mismatch_still_blocks_whole_receipt():
    artifact = build_frontier_preflight()
    item = artifact["public_surface"]["items"][0]
    raw = _raw_receipt(item, "A0_DIRECT", ["outside://scope"])
    projection = project_frontier_receipt(
        raw_receipt=raw,
        item=item,
        arm_id="A0_DIRECT",
        evidence_refs=tuple(artifact["evidence_refs"]),
    )
    assert projection["receipt_state"] == "BLOCK"
    assert projection["hard_failures"] == ["EVIDENCE_SCOPE_MISMATCH"]


def test_frontier_coordinate_shift_may_compare_one_object_across_states():
    artifact = build_frontier_preflight()
    item = artifact["public_surface"]["items"][0]
    raw = _raw_receipt(
        item, "A0_DIRECT", artifact["evidence_refs"]
    )
    raw["problem_candidates"][1].update({
        "lane": "FRONTIER",
        "epistemic_basis": "SPECULATIVE",
        "structural_origin": "COORDINATE_SHIFT",
        "source_object_id": "O1",
        "target_object_id": "O1",
    })
    projection = project_frontier_receipt(
        raw_receipt=raw,
        item=item,
        arm_id="A0_DIRECT",
        evidence_refs=tuple(artifact["evidence_refs"]),
    )
    assert len(projection["eligible_candidate_ids"]) == 2
    assert projection["candidate_components"][1][
        "disposition"
    ] == "SPECULATIVE_COMPONENT"


def test_core_and_frontier_use_identical_realized_cbit_weights():
    corpus = build_frontier_fresh_holdout()
    item = corpus["public_surface"]["items"][0]
    truth = corpus["private_provenance"]["bindings"][item["case_id"]]
    target = truth["supported_targets"][0]
    raw_core = _raw_receipt(
        item, "A0_DIRECT", corpus["evidence_refs"], truth=truth
    )
    raw_frontier = _raw_receipt(
        item, "A1_ONTOLOGY", corpus["evidence_refs"], truth=truth
    )
    for raw, lane in ((raw_core, "CORE"), (raw_frontier, "FRONTIER")):
        raw["problem_candidates"] = [_candidate(
            "PX", target["source_object_id"], target["target_object_id"],
            lane=lane, basis="INFERRED", evidence=("S1",),
        )]
        raw["selected_problem_id"] = "PX"
    refs = tuple(corpus["evidence_refs"])
    projections = {
        "A0_DIRECT:" + item["case_id"]: project_frontier_receipt(
            raw_receipt=raw_core, item=item, arm_id="A0_DIRECT",
            evidence_refs=refs,
        ),
        "A1_ONTOLOGY:" + item["case_id"]: project_frontier_receipt(
            raw_receipt=raw_frontier, item=item, arm_id="A1_ONTOLOGY",
            evidence_refs=refs,
        ),
    }
    calls = [
        _call(arm, item["case_id"]) for arm in ("A0_DIRECT", "A1_ONTOLOGY")
    ]
    commitment = {
        "task_calls": calls, "projections": projections,
    }
    run = {**commitment, "run_hash": hash_payload(commitment)}
    ledger = build_realized_cbit_ledger(corpus=corpus, run=run)
    assert ledger["lane_specific_score_weights_present"] is False
    assert (
        ledger["entries"][0]["realized_effective_cbit"]
        == ledger["entries"][1]["realized_effective_cbit"]
    )


def test_preflight_then_fresh_holdout_closes_with_fixture():
    preflight = build_frontier_preflight()
    preflight_run = run_frontier_batch(
        artifact=preflight,
        adapter=FrontierFixtureProvider(),
        mode="PREFLIGHT",
    )
    preflight_analysis = analyze_frontier_preflight(
        artifact=preflight, run=preflight_run
    )
    assert preflight_analysis["preflight_gate"] == "PASS"
    corpus = build_frontier_fresh_holdout()
    preregistration = build_frontier_preregistration(
        corpus=corpus, preflight_analysis=preflight_analysis
    )
    run = run_frontier_batch(
        artifact=corpus,
        adapter=FrontierFixtureProvider(corpus),
        mode="FRESH_HOLDOUT",
    )
    analysis = analyze_frontier_holdout(
        corpus=corpus, preregistration=preregistration, run=run
    )
    assert analysis["comparison_valid"] is True
    assert analysis["a1_cbit_gain_per_case"] > 0
    assert analysis["frontier_holdout_gate"] == "PASS"
    assert analysis["core_integration_authorized"] is False


def _call(arm_id, case_id):
    commitment = {
        "arm_id": arm_id,
        "case_id": case_id,
        "invocation_receipt": {
            "token_usage": {"input_tokens": 100, "output_tokens": 100}
        },
    }
    return {**commitment, "call_hash": hash_payload(commitment)}
