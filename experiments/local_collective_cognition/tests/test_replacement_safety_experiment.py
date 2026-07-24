from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.candidate_pool_arbitration import (  # noqa: E402
    build_candidate_pool,
)
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.frontier_partial_admission import (  # noqa: E402
    project_frontier_receipt,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.replacement_safety_experiment import (  # noqa: E402
    analyze_replacement_safety_experiment,
    build_replacement_safety_preregistration,
    run_replacement_safety_experiment,
)
from local_collective_cognition.replacement_safety_holdout import (  # noqa: E402
    build_replacement_safety_holdout,
    validate_replacement_safety_holdout,
)
from local_collective_cognition.replacement_safety_posthoc import (  # noqa: E402
    analyze_replacement_safety_posthoc,
)
from local_collective_cognition.null_role_candidate_composition import (  # noqa: E402
    compose_null_role_valued_pool,
    validate_null_role_valued_receipt,
)
from local_collective_cognition.runtime_escalation_policy import (  # noqa: E402
    derive_escalation_receipt,
)
from local_collective_cognition.replacement_safety_gate import (  # noqa: E402
    apply_replacement_safety_gate,
)
from local_collective_cognition.selective_delta_policy import (  # noqa: E402
    derive_selective_qualification,
)
from local_collective_cognition.compact_delta_contract import (  # noqa: E402
    build_compact_delta_view,
    compact_delta_schema,
    materialize_compact_delta,
    validate_compact_delta,
)


class CompactDeltaFixture:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-compact-delta",
            model_id="fixture",
            task_kinds=(TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        counter = "delta_case" in task.inputs
        item = (
            task.inputs["delta_case"]
            if counter else task.inputs["public_case"]
        )
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
        targets = [supported[0], wrong[0], wrong[1]]
        spans = [
            value["span_id"] for value in item["evidence_spans"]
        ]
        candidates = []
        for index, target in enumerate(targets, 1):
            valuable = target in supported
            frontier = not valuable and index == 3
            if index == 1:
                truth_state = "SUPPORTED_EFFECT"
                null_role = "RULES_OUT_PLAUSIBLE_CAUSE"
                expected_cbit = "HIGH"
                disposition = "PRIORITIZE"
                counterevidence = "PARTIAL"
                constraint = "ADEQUATE"
            elif index == 2:
                truth_state = "INDIRECT"
                null_role = "CONSTRAINS_BOUNDARY"
                expected_cbit = "MEDIUM"
                disposition = "RETAIN"
                counterevidence = "PARTIAL"
                constraint = "PARTIAL"
            else:
                truth_state = "WEAK"
                null_role = "RULES_OUT_PLAUSIBLE_CAUSE"
                expected_cbit = "HIGH"
                disposition = "DEFER"
                counterevidence = "ABSENT"
                constraint = "ABSENT"
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
                "evidence_span_ids": spans[:2] if counter else spans[:1],
                "estimated_test_cost": "LOW",
                "candidate_value": {
                    "relation_truth_state": truth_state,
                    "null_information_role": null_role,
                    "counterevidence_handling": counterevidence,
                    "constraint_binding": constraint,
                    "falsifiability": "SPECIFIC",
                    "expected_cbit": expected_cbit,
                    "research_value_disposition": disposition,
                    "evidence_span_ids": [spans[0]],
                    "rationale": "Fixture independent truth/null role.",
                },
            })
        if counter:
            target = supported[1]
            raw = {
                "case_id": item["case_id"],
                "source_object_id": target[0],
                "target_object_id": target[1],
                "question": f"Does {target[0]} alter {target[1]}?",
                "constraint_object_ids": list(
                    truth["hidden_constraint_object_ids"]
                ),
                "falsifier": "A matched intervention shows no relation.",
                "required_observation": "Run one matched test.",
                "evidence_span_ids": spans[:2],
                "estimated_test_cost": "LOW",
                "relation_truth_state": "SUPPORTED_EFFECT",
                "null_information_role": "RULES_OUT_PLAUSIBLE_CAUSE",
                "counterevidence_handling": "EXPLICIT",
                "constraint_binding": "ADEQUATE",
                "falsifiability": "SPECIFIC",
                "expected_cbit": "HIGH",
                "research_value_disposition": "PRIORITIZE",
                "rationale": "Fixture compact semantic delta.",
                "evidence_refs": list(task.allowed_evidence),
            }
        else:
            raw = {
                "case_id": item["case_id"],
                "arm_id": "A1_ONTOLOGY",
                "problem_candidates": candidates,
                "selected_problem_id": "C1",
                "rationale": "Fixture.",
                "evidence_refs": list(task.allowed_evidence),
            }
            raw["object_census"] = [
                {
                    "object_id": value["object_id"],
                    "object_type": "OBSERVABLE",
                    "anchor_span_ids": [spans[index % len(spans)]],
                }
                for index, value in enumerate(item["object_registry"])
            ]
        return {
            "result": raw,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 50,
                "output_tokens": 40,
            },
            "provenance_refs": list(task.allowed_evidence),
        }


def _prior():
    analysis_value = {
        "decision": "REJECT_COMPACT_DELTA_COMPOSITION",
        "candidate_state": "COMPACT_DELTA_REJECTED_STOP",
        "physical_total_tokens": 206003,
        "runtime_metrics": {
            "standard_compact_delta_contract_coverage": 1.0,
            "counter_compact_delta_contract_coverage": 1.0,
        },
        "composition_metrics": {
            "triggered_composition_gross_uplift": {
                "mean": 0.166667,
                "loss_count": 2,
            },
            "mean_delta_token_penalty_cbit": 0.637833,
        },
    }
    closure_value = {
        "candidate_state": "COMPACT_DELTA_REJECTED_STOP"
    }
    posthoc_value = {
        "formal_decision_unchanged": True,
        "mean_fraction_of_positive_oracle_uplift_captured": 1.0,
        "positive_oracle_cell_count": 2,
        "invalid_delta_contract_count": 0,
    }
    return tuple({
        **value,
        "artifact_hash": hash_payload(value),
    } for value in (
        analysis_value, closure_value, posthoc_value
    ))


def test_compact_delta_contract_and_source_calibrated_composition():
    corpus = build_replacement_safety_holdout()
    item = corpus["public_surface"]["items"][0]
    fixture = CompactDeltaFixture(corpus)
    standard_task = type("TaskLike", (), {
        "inputs": {
            "public_case": item,
            "stage": "STANDARD_COMPACT_DELTA",
        },
        "allowed_evidence": corpus["evidence_refs"],
    })()
    base = fixture.invoke(standard_task)["result"]
    assert validate_null_role_valued_receipt(
        raw_receipt=base, item=item, refs=corpus["evidence_refs"]
    ) == []
    escalation = derive_escalation_receipt(
        raw_receipt=base, item=item
    )
    qualification = derive_selective_qualification(
        raw_receipt=base, item=item,
        escalation_receipt=escalation,
    )
    assert qualification["qualified"] is True
    assert qualification["private_truth_used"] is False
    delta_view = build_compact_delta_view(
        raw_receipt=base, item=item,
        qualification_receipt=qualification,
    )
    counter_task = type("TaskLike", (), {
        "inputs": {
            "delta_case": delta_view,
            "stage": "INDEPENDENT_COUNTER_COMPACT_DELTA",
        },
        "allowed_evidence": corpus["evidence_refs"],
    })()
    delta = fixture.invoke(counter_task)["result"]
    assert validate_compact_delta(
        delta=delta, item=delta_view, refs=corpus["evidence_refs"]
    ) == []
    duplicate = {
        **delta, **delta_view["excluded_relations"][0]
    }
    assert "DELTA_RELATION_NOT_DISTINCT" in validate_compact_delta(
        delta=duplicate, item=delta_view,
        refs=corpus["evidence_refs"],
    )
    assert len(compact_delta_schema(
        item=delta_view, refs=corpus["evidence_refs"]
    )["allOf"]) == 3
    counter, materialization = materialize_compact_delta(
        delta=delta, item=delta_view, refs=corpus["evidence_refs"],
        route_id=qualification["route_id"],
    )
    assert len(counter["problem_candidates"]) == 1
    assert materialization[
        "semantic_fields_copied_without_rewrite"
    ] is True
    pool = build_candidate_pool(
        provisional_receipt=base,
        counter_receipt=counter,
        item=item,
        replication_id="R1",
    )
    raw, receipt = compose_null_role_valued_pool(
        pool=pool, provisional_receipt=base,
        item=item, refs=corpus["evidence_refs"],
    )
    assert len({
        (value["source_object_id"], value["target_object_id"])
        for value in raw["problem_candidates"]
    }) == 3
    assert receipt["provider_selected_final_candidates"] is False
    projection = project_frontier_receipt(
        raw_receipt=base, item=item, arm_id="A1_ONTOLOGY",
        evidence_refs=corpus["evidence_refs"],
    )
    _, accepted, gate = apply_replacement_safety_gate(
        provisional_receipt=base,
        provisional_projection=projection,
        proposed_receipt=raw,
        composition_receipt=receipt,
        item=item,
    )
    assert accepted is receipt
    assert gate["reason"] == "STRONG_FOCAL_RELATION"
    selected = {
        value["pool_candidate_id"] for value in receipt["lineage"]
    }
    dropped = next(
        value for value in receipt["scored_candidates"]
        if value["source_id"] == "BASE"
        and value["pool_candidate_id"] not in selected
    )
    protected_receipt = copy.deepcopy(receipt)
    protected = next(
        value for value in protected_receipt["scored_candidates"]
        if value["pool_candidate_id"] == dropped["pool_candidate_id"]
    )
    protected["provider_candidate_value"][
        "relation_truth_state"
    ] = "SUPPORTED_NULL"
    _, accepted, gate = apply_replacement_safety_gate(
        provisional_receipt=base,
        provisional_projection=projection,
        proposed_receipt=raw,
        composition_receipt=protected_receipt,
        item=item,
    )
    assert accepted is None
    assert gate["reason"] == "SUPPORTED_NULL_PROTECTED"
    quarantine_projection = copy.deepcopy(projection)
    dropped_component = next(
        value for value in quarantine_projection["candidate_components"]
        if value["candidate_id"] == dropped["source_candidate_id"]
    )
    dropped_component["disposition"] = "QUARANTINED_COMPONENT"
    _, accepted, gate = apply_replacement_safety_gate(
        provisional_receipt=base,
        provisional_projection=quarantine_projection,
        proposed_receipt=raw,
        composition_receipt=protected_receipt,
        item=item,
    )
    assert accepted is protected_receipt
    assert gate["reason"] == "QUARANTINED_BASE_REPLACEMENT"


def test_replacement_safety_experiment_can_pass_fixture():
    corpus = build_replacement_safety_holdout()
    validate_replacement_safety_holdout(corpus)
    prior_analysis, prior_closure, prior_posthoc = _prior()
    preregistration = build_replacement_safety_preregistration(
        corpus=corpus,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
        prior_posthoc=prior_posthoc,
    )
    run = run_replacement_safety_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=CompactDeltaFixture(corpus),
    )
    analysis = analyze_replacement_safety_experiment(
        corpus=corpus, preregistration=preregistration, run=run
    )
    assert len(run["composition_receipts"]) == 24
    assert len(run["replacement_gate_receipts"]) == 24
    assert all(
        value["reason"] == "STRONG_FOCAL_RELATION"
        for value in run["replacement_gate_receipts"].values()
    )
    assert analysis["runtime_metrics"][
        "standard_compact_delta_contract_coverage"
    ] == 1
    assert analysis["runtime_metrics"][
        "counter_compact_delta_contract_coverage"
    ] == 1
    assert analysis["conditions"]["no_third_provider_call"] is True
    assert analysis["replacement_safety_gate"] == "PASS"
    assert analysis["core_integration_authorized"] is False
    posthoc = analyze_replacement_safety_posthoc(
        corpus=corpus, run=run, analysis=analysis
    )
    assert len(posthoc["cells"]) == 24
    assert 0 <= posthoc[
        "mean_fraction_of_positive_oracle_uplift_captured"
    ] <= 1

