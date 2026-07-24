from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.candidate_pool_arbitration import (  # noqa: E402
    build_candidate_pool,
    materialize_arbitrated_receipt,
    validate_arbitration,
)
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.independent_arbitration_experiment import (  # noqa: E402
    analyze_independent_arbitration_experiment,
    build_independent_arbitration_preregistration,
    run_independent_arbitration_experiment,
)
from local_collective_cognition.independent_arbitration_holdout import (  # noqa: E402
    build_independent_arbitration_holdout,
    validate_independent_arbitration_holdout,
)
from local_collective_cognition.independent_arbitration_posthoc import (  # noqa: E402
    analyze_independent_arbitration_posthoc,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


class ArbitrationFixture:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-independent-arbitration",
            model_id="fixture",
            task_kinds=(TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        item = task.inputs["public_case"]
        stage = task.inputs["stage"]
        if stage == "CANDIDATE_WISE_ARBITRATION":
            return self._selection(task)
        return self._candidate_receipt(task, item, stage)

    def _candidate_receipt(self, task, item, stage):
        truth = self.corpus["private_provenance"]["bindings"][
            item["case_id"]
        ]
        supported = [
            (value["source_object_id"], value["target_object_id"])
            for value in truth["supported_targets"]
        ]
        null = truth["informative_null_targets"][0]
        null_pair = (
            null["source_object_id"], null["target_object_id"]
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
        targets = (
            [supported[0], supported[1], null_pair]
            if stage == "INDEPENDENT_COUNTERPROPOSAL"
            else [supported[0], wrong[0], wrong[1]]
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
                    span_ids[:2]
                    if stage == "INDEPENDENT_COUNTERPROPOSAL"
                    else span_ids[:1]
                ),
                "estimated_test_cost": "LOW",
            })
        raw = {
            "case_id": item["case_id"],
            "arm_id": "A1_ONTOLOGY",
            "problem_candidates": candidates,
            "selected_problem_id": "C1",
            "rationale": "Fixture candidate receipt.",
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

    def _selection(self, task):
        pool = task.inputs["candidate_pool"]
        selected = []
        relations = set()
        for entry in sorted(
            pool,
            key=lambda value: (
                value["source_id"] != "COUNTER",
                value["pool_candidate_id"],
            ),
        ):
            if entry["relation_id"] in relations:
                continue
            selected.append(entry)
            relations.add(entry["relation_id"])
            if len(selected) == 3:
                break
        result = {
            "case_id": task.inputs["public_case"]["case_id"],
            "arm_id": "A2_ARBITRATED",
            "selected_relation_ids": [
                value["relation_id"] for value in selected
            ],
            "selected_pool_candidate_ids": [
                value["pool_candidate_id"] for value in selected
            ],
            "selected_problem_pool_id": selected[0][
                "pool_candidate_id"
            ],
            "rationale": "Select the three strongest distinct relations.",
            "evidence_refs": list(task.allowed_evidence),
        }
        return {
            "result": result,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 45,
                "output_tokens": 20,
            },
            "provenance_refs": list(task.allowed_evidence),
        }


def _prior():
    analysis_c = {
        "decision": "REJECT_RUNTIME_DIFF",
        "candidate_state": "RUNTIME_DIFF_REJECTED_STOP",
        "physical_total_tokens": 184429,
        "runtime_metrics": {"lineage_contract_coverage": 1.0},
    }
    closure_c = {"candidate_state": "RUNTIME_DIFF_REJECTED_STOP"}
    recovery_c = {"provider_calls_replayed": False}
    return tuple({
        **value,
        "artifact_hash": hash_payload(value),
    } for value in (analysis_c, closure_c, recovery_c))


def test_candidate_pool_requires_relation_binding_and_materializes_lineage():
    corpus = build_independent_arbitration_holdout()
    item = corpus["public_surface"]["items"][0]
    fixture = ArbitrationFixture(corpus)
    base_task = type("TaskLike", (), {
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
    base = fixture.invoke(base_task)["result"]
    counter = fixture.invoke(counter_task)["result"]
    pool = build_candidate_pool(
        provisional_receipt=base,
        counter_receipt=counter,
        item=item,
        replication_id="R1",
    )
    selected = [
        value for value in pool["candidates"]
        if value["source_id"] == "COUNTER"
    ]
    selection = {
        "case_id": item["case_id"],
        "arm_id": "A2_ARBITRATED",
        "selected_relation_ids": [
            value["relation_id"] for value in selected
        ],
        "selected_pool_candidate_ids": [
            value["pool_candidate_id"] for value in selected
        ],
        "selected_problem_pool_id": selected[0]["pool_candidate_id"],
        "rationale": "Fixture.",
        "evidence_refs": corpus["evidence_refs"],
    }
    assert validate_arbitration(
        selection=selection, pool=pool, item=item,
        refs=corpus["evidence_refs"],
    ) == []
    raw, receipt = materialize_arbitrated_receipt(
        selection=selection, pool=pool, provisional_receipt=base,
        item=item, refs=corpus["evidence_refs"],
    )
    assert [value["candidate_id"] for value in raw[
        "problem_candidates"
    ]] == ["C1", "C2", "C3"]
    assert {value["source_id"] for value in receipt["lineage"]} == {
        "COUNTER"
    }

    invalid = dict(selection)
    invalid["selected_relation_ids"] = [
        selection["selected_relation_ids"][0],
        selection["selected_relation_ids"][0],
        selection["selected_relation_ids"][2],
    ]
    assert "SELECTED_RELATION_IDS_INVALID" in validate_arbitration(
        selection=invalid, pool=pool, item=item,
        refs=corpus["evidence_refs"],
    )


def test_independent_arbitration_can_pass_fixture():
    corpus = build_independent_arbitration_holdout()
    validate_independent_arbitration_holdout(corpus)
    prior_analysis, prior_closure, prior_recovery = _prior()
    preregistration = build_independent_arbitration_preregistration(
        corpus=corpus,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
        prior_recovery=prior_recovery,
    )
    run = run_independent_arbitration_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=ArbitrationFixture(corpus),
    )
    analysis = analyze_independent_arbitration_experiment(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    assert len(run["arbitration_receipts"]) == 24
    assert (
        analysis["runtime_metrics"]["arbitration_contract_coverage"]
        == 1.0
    )
    assert analysis["arbitration_metrics"][
        "counterproposal_adoption_rate"
    ] == 1.0
    assert analysis["independent_arbitration_gate"] == "PASS"
    assert analysis["external_semantic_panel_authorized"] is True
    assert analysis["core_integration_authorized"] is False
    posthoc = analyze_independent_arbitration_posthoc(
        corpus=corpus, run=run, analysis=analysis
    )
    assert posthoc["pool_oracle_gross_uplift"]["loss_count"] == 0
    assert posthoc["formal_decision_unchanged"] is True
