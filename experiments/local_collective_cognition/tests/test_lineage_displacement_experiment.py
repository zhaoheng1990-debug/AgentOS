from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.lineage_displacement_contract import (  # noqa: E402
    build_lineage_bound_delta_view,
    lineage_bound_delta_schema,
    validate_lineage_bound_delta,
)
from local_collective_cognition.lineage_displacement_experiment import (  # noqa: E402
    analyze_lineage_displacement_experiment,
    build_lineage_displacement_preregistration,
    run_lineage_displacement_experiment,
)
from local_collective_cognition.lineage_displacement_holdout import (  # noqa: E402
    build_lineage_displacement_holdout,
    validate_lineage_displacement_holdout,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


class LineageFixture:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-lineage-displacement",
            model_id="fixture",
            task_kinds=(TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        if "pairwise_case" in task.inputs:
            raw = self._pairwise(
                task.inputs["pairwise_case"], task.allowed_evidence
            )
        elif "delta_case" in task.inputs:
            raw = self._delta(
                task.inputs["delta_case"], task.allowed_evidence
            )
        else:
            raw = self._standard(
                task.inputs["public_case"],
                task.inputs.get("replication_id", "R1"),
                task.allowed_evidence,
            )
        return {
            "result": raw,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 50,
                "output_tokens": 40,
            },
            "provenance_refs": list(task.allowed_evidence),
        }

    def _standard(self, item, replication_id, refs):
        truth = self._truth(item)
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
        targets = (
            [supported[0], wrong[0], wrong[1]]
            if replication_id == "R1"
            else [supported[0], supported[1], wrong[0]]
        )
        spans = [
            value["span_id"] for value in item["evidence_spans"]
        ]
        candidates = []
        for index, target in enumerate(targets, 1):
            if index == 1:
                axes = (
                    "SUPPORTED_EFFECT",
                    "RULES_OUT_PLAUSIBLE_CAUSE",
                    "PARTIAL", "ADEQUATE", "HIGH", "PRIORITIZE",
                )
            elif index == 2:
                axes = (
                    "INDIRECT", "CONSTRAINS_BOUNDARY",
                    "PARTIAL", "PARTIAL", "MEDIUM", "RETAIN",
                )
            else:
                axes = (
                    "WEAK", "RULES_OUT_PLAUSIBLE_CAUSE",
                    "ABSENT", "ABSENT", "HIGH", "DEFER",
                )
            candidates.append(
                self._candidate(
                    index=index, target=target, spans=spans,
                    truth=truth, axes=axes,
                )
            )
        opportunities = []
        if replication_id == "R1":
            opportunities.append(
                self._opportunity(
                    supported[1], "EFFECT", spans,
                    "SUPPORTED_EFFECT", "NOT_APPLICABLE",
                    "ADEQUATE", "HIGH", "PRIORITIZE",
                )
            )
        elif replication_id == "R2":
            opportunities.append(
                self._opportunity(
                    null_pair, "INFORMATIVE_NULL", spans,
                    "SUPPORTED_NULL", "RULES_OUT_PLAUSIBLE_CAUSE",
                    "ADEQUATE", "HIGH", "PRIORITIZE",
                )
            )
        return {
            "case_id": item["case_id"],
            "arm_id": "A1_ONTOLOGY",
            "problem_candidates": candidates,
            "selected_problem_id": "C1",
            "rationale": "Fixture standard receipt.",
            "evidence_refs": list(refs),
            "admission_opportunities": opportunities,
            "object_census": [{
                "object_id": value["object_id"],
                "object_type": "OBSERVABLE",
                "anchor_span_ids": [spans[index % len(spans)]],
            } for index, value in enumerate(item["object_registry"])],
        }

    def _delta(self, item, refs):
        binding = item["opportunity_bindings"][0]
        lane = binding["required_admission_lane"]
        if lane == "EFFECT":
            truth_state, null_role = (
                "SUPPORTED_EFFECT", "NOT_APPLICABLE"
            )
            disposition = "PRIORITIZE"
        elif lane == "INFORMATIVE_NULL":
            truth_state, null_role = (
                "SUPPORTED_NULL", "RULES_OUT_PLAUSIBLE_CAUSE"
            )
            disposition = "PRIORITIZE"
        else:
            truth_state, null_role = "INDIRECT", "NOT_APPLICABLE"
            disposition = "RETAIN"
        spans = list(binding["evidence_span_ids"])
        return {
            "case_id": item["case_id"],
            "source_object_id": binding["source_object_id"],
            "target_object_id": binding["target_object_id"],
            "question": "Does the bound relation improve the explanation?",
            "constraint_object_ids": [],
            "falsifier": "A matched intervention shows no relation.",
            "required_observation": "Run one matched test.",
            "evidence_span_ids": spans,
            "estimated_test_cost": "LOW",
            "relation_truth_state": truth_state,
            "null_information_role": null_role,
            "counterevidence_handling": "EXPLICIT",
            "constraint_binding": "ADEQUATE",
            "falsifiability": "SPECIFIC",
            "expected_cbit": "HIGH",
            "research_value_disposition": disposition,
            "rationale": "Fixture lineage-bound delta.",
            "evidence_refs": list(refs),
            "source_opportunity_hash": binding["opportunity_hash"],
            "source_opportunity_type": binding["opportunity_type"],
            "source_opportunity_evidence_span_ids": spans,
            "proposed_admission_lane": lane,
        }

    def _pairwise(self, item, refs):
        delta = item["delta_candidate"]
        return {
            "case_id": item["case_id"],
            "source_opportunity_hash": item[
                "source_opportunity_hash"
            ],
            "dropped_base_candidate_id": item[
                "base_candidate"
            ]["candidate_id"],
            "counter_relation_id": (
                f"REL-{delta['source_object_id']}-"
                f"{delta['target_object_id']}"
            ),
            "decision": "REPLACE",
            "pairwise_information_preference": "DELTA",
            "opportunity_lineage_consistent": True,
            "delta_materially_stronger": True,
            "evidence_span_ids": [
                item["evidence_spans"][0]["span_id"]
            ],
            "rationale": "Fixture delta is materially stronger.",
            "evidence_refs": list(refs),
        }

    def _truth(self, item):
        return self.corpus["private_provenance"]["bindings"][
            item["case_id"]
        ]

    @staticmethod
    def _opportunity(
        target, opportunity_type, spans, truth_state, null_role,
        constraint, expected_cbit, disposition,
    ):
        return {
            "source_object_id": target[0],
            "target_object_id": target[1],
            "opportunity_type": opportunity_type,
            "relation_truth_state": truth_state,
            "null_information_role": null_role,
            "constraint_binding": constraint,
            "expected_cbit": expected_cbit,
            "research_value_disposition": disposition,
            "evidence_span_ids": spans[:2],
            "rationale": "Fixture admission opportunity.",
        }

    @staticmethod
    def _candidate(*, index, target, spans, truth, axes):
        (
            truth_state, null_role, counterevidence, constraint,
            expected_cbit, disposition,
        ) = axes
        return {
            "candidate_id": f"C{index}",
            "lane": "CORE" if index < 3 else "FRONTIER",
            "question": f"Does {target[0]} alter {target[1]}?",
            "source_object_id": target[0],
            "target_object_id": target[1],
            "constraint_object_ids": list(
                truth["hidden_constraint_object_ids"]
            ),
            "epistemic_basis": "INFERRED" if index < 3 else "SPECULATIVE",
            "structural_origin": "EVIDENCE" if index < 3 else "COUNTERFACTUAL",
            "falsifier": "A matched intervention shows no relation.",
            "required_observation": "Run one matched test.",
            "evidence_span_ids": spans[:1],
            "estimated_test_cost": "LOW",
            "candidate_value": {
                "relation_truth_state": truth_state,
                "null_information_role": null_role,
                "counterevidence_handling": counterevidence,
                "constraint_binding": constraint,
                "falsifiability": "SPECIFIC",
                "expected_cbit": expected_cbit,
                "research_value_disposition": disposition,
                "evidence_span_ids": spans[:1],
                "rationale": "Fixture semantic value.",
            },
        }


def _prior():
    values = (
        {
            "decision": "REJECT_ADMISSION_OPPORTUNITY_ROUTING",
            "candidate_state": "OPPORTUNITY_ROUTING_REJECTED_STOP",
            "physical_total_tokens": 119114,
            "runtime_metrics": {
                "standard_compact_delta_contract_coverage": 1.0,
                "counter_compact_delta_contract_coverage": 1.0,
            },
            "composition_metrics": {
                "triggered_composition_gross_uplift": {
                    "mean": -2.0,
                },
            },
            "replacement_gate_metrics": {"accepted_count": 1},
        },
        {"candidate_state": "OPPORTUNITY_ROUTING_REJECTED_STOP"},
        {
            "formal_decision_unchanged": True,
            "mean_fraction_of_positive_oracle_uplift_captured": -4.0,
            "positive_oracle_cell_count": 1,
            "classification_distribution": {"HARMFUL_ACCEPTED": 1},
        },
    )
    return tuple({
        **value, "artifact_hash": hash_payload(value)
    } for value in values)


def test_lineage_contract_rejects_hash_and_lane_drift():
    corpus = build_lineage_displacement_holdout()
    item = corpus["public_surface"]["items"][0]
    fixture = LineageFixture(corpus)
    base = fixture._standard(item, "R1", corpus["evidence_refs"])
    opportunity = base["admission_opportunities"][0]
    routing = {
        "allowed_opportunities": [{
            **opportunity,
            "relation_id": (
                f"{opportunity['source_object_id']}->"
                f"{opportunity['target_object_id']}"
            ),
        }],
        "allowed_relations": [{
            "source_object_id": opportunity["source_object_id"],
            "target_object_id": opportunity["target_object_id"],
        }],
        "artifact_hash": "routing",
    }
    qualification = {"artifact_hash": "qualification"}
    view = build_lineage_bound_delta_view(
        raw_receipt=base,
        item=item,
        qualification_receipt=qualification,
        routing_receipt=routing,
    )
    delta = fixture._delta(view, corpus["evidence_refs"])
    assert validate_lineage_bound_delta(
        delta=delta, item=view, refs=corpus["evidence_refs"]
    ) == []
    assert len(lineage_bound_delta_schema(
        item=view, refs=corpus["evidence_refs"]
    )["anyOf"]) == 1
    bad_hash = {**delta, "source_opportunity_hash": "rewritten"}
    assert "LINEAGE_SOURCE_OPPORTUNITY_HASH_MISMATCH" in (
        validate_lineage_bound_delta(
            delta=bad_hash, item=view, refs=corpus["evidence_refs"]
        )
    )
    quarantine_view = copy.deepcopy(view)
    binding = quarantine_view["opportunity_bindings"][0]
    binding["opportunity_type"] = "QUARANTINE_ALTERNATIVE"
    binding["required_admission_lane"] = "QUARANTINE"
    strengthened = {
        **delta,
        "source_opportunity_type": "QUARANTINE_ALTERNATIVE",
        "proposed_admission_lane": "QUARANTINE",
        "relation_truth_state": "SUPPORTED_NULL",
        "research_value_disposition": "PRIORITIZE",
    }
    assert "QUARANTINE_LINEAGE_STRENGTHENING_FORBIDDEN" in (
        validate_lineage_bound_delta(
            delta=strengthened,
            item=quarantine_view,
            refs=corpus["evidence_refs"],
        )
    )


def test_lineage_displacement_fixture_closes_end_to_end():
    corpus = build_lineage_displacement_holdout()
    validate_lineage_displacement_holdout(corpus)
    analysis0, closure0, posthoc0 = _prior()
    preregistration = build_lineage_displacement_preregistration(
        corpus=corpus,
        prior_analysis=analysis0,
        prior_closure=closure0,
        prior_posthoc=posthoc0,
    )
    run = run_lineage_displacement_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=LineageFixture(corpus),
    )
    analysis = analyze_lineage_displacement_experiment(
        corpus=corpus, preregistration=preregistration, run=run
    )
    assert run["physical_shared_standard_call_count"] == 24
    assert len(run["lineage_valid_keys"]) == 16
    assert len(run["pairwise_displacement_valid_keys"]) == 16
    assert analysis["runtime_metrics"]["pre_call_skip_count"] == 8
    assert analysis["runtime_metrics"][
        "lineage_contract_coverage"
    ] == 1
    assert analysis["runtime_metrics"][
        "pairwise_review_coverage"
    ] == 1
    assert analysis["lineage_displacement_gate"] == "PASS"
    assert analysis["core_integration_authorized"] is False
