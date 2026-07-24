from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.runtime_candidate_diff import (  # noqa: E402
    derive_candidate_diff,
    validate_candidate_diff,
)
from local_collective_cognition.runtime_diff_experiment import (  # noqa: E402
    analyze_runtime_diff_experiment,
    build_runtime_diff_preregistration,
    run_runtime_diff_experiment,
)
from local_collective_cognition.runtime_diff_holdout import (  # noqa: E402
    build_runtime_diff_holdout,
    validate_runtime_diff_holdout,
)
from local_collective_cognition.runtime_escalation_policy import (  # noqa: E402
    derive_escalation_receipt,
)


class DiffFixture:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-runtime-diff", model_id="fixture",
            task_kinds=(TASK_KIND,), max_timeout_seconds=180,
        )

    def invoke(self, task):
        item = task.inputs["public_case"]
        truth = self.corpus["private_provenance"]["bindings"][item["case_id"]]
        supported = [
            (v["source_object_id"], v["target_object_id"])
            for v in truth["supported_targets"]
        ]
        null = truth["informative_null_targets"][0]
        null_pair = (null["source_object_id"], null["target_object_id"])
        objects = [v["object_id"] for v in item["object_registry"]]
        wrong = [
            (s, t) for s in objects for t in objects
            if s != t and (s, t) not in {*supported, null_pair}
        ]
        revision = task.inputs["stage"] == "RUNTIME_DIFF_REVISION"
        provisional = task.inputs.get("provisional_receipt")
        targets = (
            [supported[0], supported[1], null_pair]
            if revision else [supported[0], wrong[0], wrong[1]]
        )
        spans = [v["span_id"] for v in item["evidence_spans"]]
        candidates = []
        for index, target in enumerate(targets, 1):
            if revision and index == 1:
                candidates.append(copy.deepcopy(
                    provisional["problem_candidates"][0]
                ))
                continue
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
                "epistemic_basis": "SPECULATIVE" if frontier else "INFERRED",
                "structural_origin": (
                    "COUNTERFACTUAL" if frontier else "EVIDENCE"
                ),
                "falsifier": "A matched intervention shows no relation.",
                "required_observation": "Run one matched test.",
                "evidence_span_ids": [] if frontier else [spans[0], spans[1]],
                "estimated_test_cost": "LOW",
            })
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
        if revision:
            raw["revision_summary"] = "Preserve one and replace two."
        return {
            "result": raw,
            "usage": {"provider_calls": 1, "input_tokens": 50,
                      "output_tokens": 35},
            "provenance_refs": list(task.allowed_evidence),
        }


def _prior():
    analysis_c = {
        "decision": "REJECT_LINEAGE_REVISION",
        "candidate_state": "LINEAGE_REVISION_REJECTED_STOP",
        "physical_total_tokens": 178000,
    }
    closure_c = {"candidate_state": "LINEAGE_REVISION_REJECTED_STOP"}
    posthoc_c = {
        "status": "POSTHOC_DECOMPOSITION_NOT_FROZEN_GATE",
        "contract_failure_reason_counts": {
            "REVISE_RELATION_OR_NOOP_INVALID": 10,
            "WORKER_ROUTE_MISMATCH": 2,
        },
    }
    return tuple({
        **value, "artifact_hash": hash_payload(value)
    } for value in (analysis_c, closure_c, posthoc_c))


def test_runtime_diff_derives_actions_without_provider_labels():
    corpus = build_runtime_diff_holdout()
    validate_runtime_diff_holdout(corpus)
    item = corpus["public_surface"]["items"][0]
    fixture = DiffFixture(corpus)
    task0 = type("TaskLike", (), {
        "inputs": {"public_case": item, "stage": "STANDARD_ONTOLOGY"},
        "allowed_evidence": corpus["evidence_refs"],
    })()
    provisional = fixture.invoke(task0)["result"]
    trigger = derive_escalation_receipt(
        raw_receipt=provisional, item=item
    )
    task1 = type("TaskLike", (), {
        "inputs": {
            "public_case": item, "stage": "RUNTIME_DIFF_REVISION",
            "provisional_receipt": provisional,
        },
        "allowed_evidence": corpus["evidence_refs"],
    })()
    final = fixture.invoke(task1)["result"]
    receipt = derive_candidate_diff(
        provisional_receipt=provisional, final_receipt=final,
        trigger=trigger, item=item,
    )
    validate_candidate_diff(
        receipt=receipt, provisional_receipt=provisional,
        final_receipt=final, trigger=trigger, item=item,
    )
    assert [v["action"] for v in receipt["revision_actions"]] == [
        "KEEP", "REPLACE", "REPLACE"
    ]
    assert receipt["provider_declared_action_used"] is False
    assert receipt["provider_declared_route_used"] is False


def test_runtime_diff_can_pass_fixture():
    corpus = build_runtime_diff_holdout()
    analysis0, closure0, posthoc0 = _prior()
    prereg = build_runtime_diff_preregistration(
        corpus=corpus, prior_analysis=analysis0,
        prior_closure=closure0, prior_posthoc=posthoc0,
    )
    run = run_runtime_diff_experiment(
        corpus=corpus, preregistration=prereg, adapter=DiffFixture(corpus),
    )
    analysis = analyze_runtime_diff_experiment(
        corpus=corpus, preregistration=prereg, run=run,
    )
    assert len(run["revision_receipts"]) == 24
    assert analysis["runtime_metrics"]["lineage_contract_coverage"] == 1
    assert analysis["revision_metrics"]["revision_action_distribution"] == {
        "KEEP": 24, "REPLACE": 48
    }
    assert analysis["runtime_diff_gate"] == "PASS"
    assert analysis["external_semantic_panel_authorized"] is True
    assert analysis["core_integration_authorized"] is False


def test_runtime_diff_analysis_accounts_for_missing_trigger():
    corpus = build_runtime_diff_holdout()
    analysis0, closure0, posthoc0 = _prior()
    prereg = build_runtime_diff_preregistration(
        corpus=corpus, prior_analysis=analysis0,
        prior_closure=closure0, prior_posthoc=posthoc0,
    )
    run = run_runtime_diff_experiment(
        corpus=corpus, preregistration=prereg, adapter=DiffFixture(corpus),
    )
    key = sorted(run["trigger_receipts"])[0]
    replication_id, arm_id, case_id = key.split(":", 2)
    del run["trigger_receipts"][key]
    del run["revision_receipts"][key]
    del run["provisional_projections"][key]
    del run["final_projections"][key]
    raw_key = (
        f"{replication_id}:{arm_id}:STANDARD_ONTOLOGY:{case_id}"
    )
    del run["raw_receipts"][raw_key]
    run["task_calls"] = [
        value for value in run["task_calls"]
        if not (
            value["replication_id"] == replication_id
            and value["arm_id"] == arm_id
            and value["case_id"] == case_id
            and value["stage"] == "LINEAGE_REVISION_WORKER"
        )
    ]
    commitment = {
        name: value for name, value in run.items() if name != "run_hash"
    }
    run["run_hash"] = hash_payload(commitment)
    analysis = analyze_runtime_diff_experiment(
        corpus=corpus, preregistration=prereg, run=run,
    )
    assert analysis["runtime_diff_gate"] in {"PASS", "REJECT"}
    assert (
        analysis["runtime_metrics"]["trigger_receipt_coverage"] < 1
    )
