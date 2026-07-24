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
from local_collective_cognition.provider_telemetry import (  # noqa: E402
    hash_payload,
)
from local_collective_cognition.runtime_escalation_experiment import (  # noqa: E402
    analyze_runtime_escalation_experiment,
    build_runtime_escalation_preregistration,
    run_runtime_escalation_experiment,
)
from local_collective_cognition.runtime_escalation_holdout import (  # noqa: E402
    build_runtime_escalation_holdout,
    validate_runtime_escalation_holdout,
)
from local_collective_cognition.runtime_escalation_policy import (  # noqa: E402
    derive_escalation_receipt,
    validate_escalation_receipt,
)
from local_collective_cognition.runtime_escalation_posthoc import (  # noqa: E402
    analyze_worker_uplift,
)


class RuntimeEscalationFixture:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-runtime-escalation",
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
        wrong = [
            (source, target)
            for source in objects
            for target in objects
            if source != target
            and (source, target) not in {*supported, null_pair}
        ]
        worker = task.inputs["stage"] == "RUNTIME_TRIGGERED_WORKER"
        targets = (
            [supported[0], supported[1], null_pair]
            if worker
            else [supported[0], wrong[0], wrong[1]]
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
                    [] if frontier else [spans[0], spans[1]]
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
        return {
            "result": raw,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 50,
                "output_tokens": 35,
            },
            "provenance_refs": list(task.allowed_evidence),
        }


def _prior():
    analysis_commitment = {
        "decision": "REJECT_LAZY_METACOGNITION",
        "candidate_state": "LAZY_METACOGNITION_REJECTED_STOP",
        "physical_total_tokens": 140000,
        "trigger_metrics": {"trigger_count": 0},
    }
    analysis = {
        **analysis_commitment,
        "artifact_hash": hash_payload(analysis_commitment),
    }
    closure_commitment = {
        "candidate_state": "LAZY_METACOGNITION_REJECTED_STOP",
    }
    closure = {
        **closure_commitment,
        "artifact_hash": hash_payload(closure_commitment),
    }
    posthoc_commitment = {
        "status": "POSTHOC_DECOMPOSITION_NOT_FROZEN_GATE",
        "gross_candidate_delta": {"median": 0},
        "incremental_token_penalty": {"mean_cbit_per_cell": 0.16},
    }
    posthoc = {
        **posthoc_commitment,
        "artifact_hash": hash_payload(posthoc_commitment),
    }
    return analysis, closure, posthoc


def test_runtime_escalation_holdout_and_policy_are_replayable():
    corpus = build_runtime_escalation_holdout()
    validate_runtime_escalation_holdout(corpus)
    item = corpus["public_surface"]["items"][0]
    fixture = RuntimeEscalationFixture(corpus)
    task_like = type("TaskLike", (), {
        "inputs": {
            "public_case": item,
            "stage": "STANDARD_ONTOLOGY",
        },
        "allowed_evidence": corpus["evidence_refs"],
    })()
    raw = fixture.invoke(task_like)["result"]
    receipt = derive_escalation_receipt(raw_receipt=raw, item=item)
    validate_escalation_receipt(
        receipt=receipt,
        raw_receipt=raw,
        item=item,
    )
    assert corpus["case_count"] == corpus["domain_count"] == 8
    assert corpus["prior_holdout_labels_reused"] is False
    assert receipt["triggered"] is True
    assert receipt["private_truth_used"] is False
    assert receipt["provider_generated_trigger_text_used"] is False


def test_runtime_escalation_dynamic_path_can_pass_fixture():
    corpus = build_runtime_escalation_holdout()
    prior_analysis, prior_closure, prior_posthoc = _prior()
    preregistration = build_runtime_escalation_preregistration(
        corpus=corpus,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
        prior_posthoc=prior_posthoc,
    )
    run = run_runtime_escalation_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=RuntimeEscalationFixture(corpus),
    )
    analysis = analyze_runtime_escalation_experiment(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    assert len(run["trigger_receipts"]) == 24
    assert len([
        value for value in run["task_calls"]
        if value["stage"] == "RUNTIME_TRIGGERED_WORKER"
    ]) == 24
    assert analysis["runtime_metrics"]["prompt_identity_coverage"] == 1
    assert analysis["trigger_metrics"]["trigger_rate"] == 1
    assert analysis["runtime_escalation_gate"] == "PASS"
    assert analysis["decision"] == "PASS_RUNTIME_ESCALATION"
    assert analysis["external_semantic_panel_authorized"] is True
    assert analysis["core_integration_authorized"] is False
    posthoc = analyze_worker_uplift(
        corpus=corpus,
        run=run,
        formal_analysis=analysis,
    )
    assert posthoc["triggered_worker_net_uplift"]["mean"] > 0
    assert posthoc["frozen_decision_changed"] is False
