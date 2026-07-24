from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.frontier_experiment import (  # noqa: E402
    TASK_KIND,
)
from local_collective_cognition.lineage_revision_contracts import (  # noqa: E402
    lineage_failures,
)
from local_collective_cognition.lineage_revision_experiment import (  # noqa: E402
    analyze_lineage_revision_experiment,
    build_lineage_revision_preregistration,
    run_lineage_revision_experiment,
)
from local_collective_cognition.lineage_revision_holdout import (  # noqa: E402
    build_lineage_revision_holdout,
    validate_lineage_revision_holdout,
)
from local_collective_cognition.provider_telemetry import (  # noqa: E402
    hash_payload,
)
from local_collective_cognition.runtime_escalation_policy import (  # noqa: E402
    derive_escalation_receipt,
)


class LineageFixture:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-lineage-revision",
            model_id="fixture", task_kinds=(TASK_KIND,),
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
            null["source_object_id"], null["target_object_id"]
        )
        objects = [value["object_id"] for value in item["object_registry"]]
        wrong = [
            (source, target) for source in objects for target in objects
            if source != target
            and (source, target) not in {*supported, null_pair}
        ]
        revision = task.inputs["stage"] == "LINEAGE_AWARE_REVISION"
        provisional = task.inputs.get("provisional_receipt")
        targets = (
            [supported[0], supported[1], null_pair]
            if revision else [supported[0], wrong[0], wrong[1]]
        )
        spans = [value["span_id"] for value in item["evidence_spans"]]
        candidates = []
        for index, target in enumerate(targets, 1):
            frontier = target == null_pair
            if revision and index == 1:
                candidates.append(copy.deepcopy(
                    provisional["problem_candidates"][0]
                ))
                continue
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
            "case_id": item["case_id"], "arm_id": "A1_ONTOLOGY",
            "problem_candidates": candidates,
            "selected_problem_id": "C1", "rationale": "Fixture.",
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
        if revision:
            flags = task.inputs["runtime_diagnostic"][
                "diagnostic_flags"
            ]
            raw.update({
                "worker_route_id": task.inputs["worker_route_id"],
                "revision_actions": [
                    {
                        "original_candidate_id": f"C{index}",
                        "final_candidate_id": f"C{index}",
                        "action": "KEEP" if index == 1 else "REPLACE",
                        "addressed_diagnostic_flags": (
                            [] if index == 1 else flags
                        ),
                        "evidence_span_ids": [spans[0], spans[1]],
                        "rationale": "Preserve or repair by fixture.",
                    }
                    for index in range(1, 4)
                ],
                "revision_summary": "One kept and two repaired.",
            })
        return {
            "result": raw,
            "usage": {
                "provider_calls": 1, "input_tokens": 50,
                "output_tokens": 35,
            },
            "provenance_refs": list(task.allowed_evidence),
        }


def _prior():
    analysis_c = {
        "decision": "REJECT_RUNTIME_ESCALATION",
        "candidate_state": "RUNTIME_ESCALATION_REJECTED_STOP",
        "physical_total_tokens": 168000,
        "runtime_metrics": {"prompt_identity_coverage": 1},
    }
    closure_c = {
        "candidate_state": "RUNTIME_ESCALATION_REJECTED_STOP",
    }
    posthoc_c = {
        "status": "POSTHOC_DECOMPOSITION_NOT_FROZEN_GATE",
        "triggered_worker_gross_candidate_uplift": {"mean": 0.6},
        "triggered_worker_net_uplift": {"median": -0.7},
    }
    return tuple({
        **value, "artifact_hash": hash_payload(value)
    } for value in (analysis_c, closure_c, posthoc_c))


def test_lineage_holdout_is_fresh_and_fake_keep_is_rejected():
    corpus = build_lineage_revision_holdout()
    validate_lineage_revision_holdout(corpus)
    item = corpus["public_surface"]["items"][0]
    fixture = LineageFixture(corpus)
    task_like = type("TaskLike", (), {
        "inputs": {"public_case": item, "stage": "STANDARD_ONTOLOGY"},
        "allowed_evidence": corpus["evidence_refs"],
    })()
    provisional = fixture.invoke(task_like)["result"]
    trigger = derive_escalation_receipt(
        raw_receipt=provisional, item=item
    )
    final = copy.deepcopy(provisional)
    final["worker_route_id"] = trigger["route_id"]
    final["revision_summary"] = "Invalid fake keep."
    final["revision_actions"] = [
        {
            "original_candidate_id": f"C{index}",
            "final_candidate_id": f"C{index}", "action": "KEEP",
            "addressed_diagnostic_flags": [],
            "evidence_span_ids": [], "rationale": "Keep.",
        }
        for index in range(1, 4)
    ]
    final["problem_candidates"][0]["question"] = "Mutated question."
    failures = lineage_failures(
        final_receipt=final, provisional_receipt=provisional,
        trigger=trigger, item=item,
    )
    assert corpus["case_count"] == corpus["domain_count"] == 8
    assert corpus["prior_holdout_labels_reused"] is False
    assert "KEEP_MUTATED_CANDIDATE:C1" in failures


def test_lineage_revision_can_pass_fixture():
    corpus = build_lineage_revision_holdout()
    analysis0, closure0, posthoc0 = _prior()
    prereg = build_lineage_revision_preregistration(
        corpus=corpus, prior_analysis=analysis0,
        prior_closure=closure0, prior_posthoc=posthoc0,
    )
    run = run_lineage_revision_experiment(
        corpus=corpus, preregistration=prereg,
        adapter=LineageFixture(corpus),
    )
    analysis = analyze_lineage_revision_experiment(
        corpus=corpus, preregistration=prereg, run=run,
    )
    assert len(run["trigger_receipts"]) == 24
    assert len(run["revision_receipts"]) == 24
    assert analysis["runtime_metrics"]["prompt_identity_coverage"] == 1
    assert analysis["runtime_metrics"]["lineage_contract_coverage"] == 1
    assert analysis["revision_metrics"]["keep_action_rate"] == 0.333333
    assert analysis["lineage_revision_gate"] == "PASS"
    assert analysis["external_semantic_panel_authorized"] is True
    assert analysis["core_integration_authorized"] is False
