from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.cognitive_action_axis_holdout import build_axis_routing_holdout, validate_axis_routing_holdout  # noqa: E402
from local_collective_cognition.cognitive_action_axis_routing import (  # noqa: E402
    AXIS_TASK_KIND,
    SOURCE_EVALUATION_HASH,
    SOURCE_REFERENCE_HASH,
    analyze_axis_routing_run,
    build_axis_external_annotation_pack,
    build_axis_routing_preregistration,
    run_axis_routing_arms,
    validate_axis_routing_run,
)
from local_collective_cognition.cognitive_action_protocol import ActionCost, build_action_receipt  # noqa: E402


def source_evaluation():
    return {
        "artifact_hash": SOURCE_EVALUATION_HASH,
        "reference_hash": SOURCE_REFERENCE_HASH,
        "collective_gain_status": "MIXED_NO_NET_CELL_GAIN",
        "anti_additive_gate": "REJECT",
        "arm_metrics": {
            "SINGLE_MODEL_BASELINE": {"axis_correct": {"SELECTED_OBJECT": 23, "SELECTION_BASIS": 11, "PRAGMATIC_PREFERENCE": 1, "AXIS_ASSESSMENT_COMPLETE": 22}},
            "ROLE_INFORMED_COORDINATOR": {"axis_correct": {"SELECTED_OBJECT": 16, "SELECTION_BASIS": 9, "PRAGMATIC_PREFERENCE": 8, "AXIS_ASSESSMENT_COMPLETE": 24}},
        },
    }


class FixtureAxisAdapter:
    def __init__(self):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-axis",
            model_id="fixture-deepseek",
            task_kinds=(AXIS_TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        evidence = list(task.allowed_evidence)
        conflict_id = task.inputs["public_object"]["conflict_id"]
        if "frozen_selected_object" in task.inputs:
            result = {
                "conflict_id": conflict_id,
                "selected_object": task.inputs["frozen_selected_object"],
                "selection_basis": "COMPOSITIONAL_ENTAILMENT",
                "rationale": "The candidate follows from the combined prompt constraints.",
                "confidence": 0.8,
                "evidence_refs": evidence,
            }
        else:
            preference = "CANDIDATE_B" if task.inputs["arm"] == "ROLE_INFORMED_COORDINATOR" else "NONE"
            result = {
                "conflict_id": conflict_id,
                "selected_object": "CANDIDATE_A",
                "selection_basis": "LEXICAL_EXACT",
                "pragmatic_preference": preference,
                "assessment_completeness": "COMPLETE",
                "action": "ACCEPT",
                "rationale": "The prompt directly supports candidate A.",
                "confidence": 0.8,
                "evidence_refs": evidence,
            }
        return {"result": result, "usage": {"input_tokens": 20, "output_tokens": 10, "latency_ms": 1}, "provenance_refs": evidence}


def role_inputs(corpus):
    outputs = []
    role_specs = (
        ("OBJECT_GROUNDING", "DEFINE_OBJECT", {"selected_object": "CANDIDATE_A", "selection_basis": "COMPOSITIONAL_ENTAILMENT"}),
        ("PRAGMATIC_DEFAULT", "COMPARE", {"pragmatic_preference": "CANDIDATE_B"}),
        ("ASSESSMENT_SKEPTIC", "AUDIT_UNCERTAINTY", {"assessment_completeness": "COMPLETE"}),
    )
    for item in corpus["public_surface"]["items"]:
        for role, action, result in role_specs:
            receipt = build_action_receipt(
                action_id=f"fixture-{item['conflict_id']}-{role}",
                action_type=action,
                object_ref="object://" + item["conflict_id"],
                actor_role=role,
                actor_instance="fixture-small-model",
                method="fixture",
                result_state="CANDIDATE",
                result=result,
                evidence_refs=tuple(corpus["evidence_refs"]),
                recommended_next_actions=("SYNTHESIZE",),
                cost=ActionCost(input_tokens=5, output_tokens=1),
            )
            outputs.append({"object_ref": "object://" + item["conflict_id"], "action_receipt": receipt})
    role_run = {"run_hash": "fixture-role-run", "outputs": outputs}
    role_analysis = {
        "artifact_hash": "fixture-role-analysis",
        "tuple_inference_allowed": True,
        "accounting": {"provider_calls": 72, "input_tokens": 360, "output_tokens": 72, "latency_ms": 0},
    }
    return role_run, role_analysis


def test_axis_holdout_and_preregistration_are_frozen_and_unlabeled():
    corpus = build_axis_routing_holdout()
    validate_axis_routing_holdout(corpus)
    preregistration = build_axis_routing_preregistration(source_evaluation=source_evaluation())
    assert corpus["case_count"] == 24
    assert set(corpus["family_counts"].values()) == {4}
    assert corpus["private_provenance"]["semantic_labels_present"] is False
    assert preregistration["frozen_axis_sources"]["selected_object"] == "SINGLE_MODEL_BASELINE"
    assert preregistration["completeness_in_promotion_gate"] is False


def test_axis_routing_uses_registered_sources_and_freezes_blind_outputs():
    corpus = build_axis_routing_holdout()
    preregistration = build_axis_routing_preregistration(source_evaluation=source_evaluation())
    role_run, role_analysis = role_inputs(corpus)
    run = run_axis_routing_arms(
        corpus=corpus,
        preregistration=preregistration,
        role_run=role_run,
        role_analysis=role_analysis,
        adapter=FixtureAxisAdapter(),
    )
    validate_axis_routing_run(corpus=corpus, run=run)
    analysis = analyze_axis_routing_run(corpus=corpus, role_analysis=role_analysis, run=run)
    assert analysis["coverage"] == {"SINGLE_MODEL_BASELINE": 1.0, "ROLE_INFORMED_COORDINATOR": 1.0, "AXIS_ROUTED": 1.0}
    assert analysis["candidate_state"] == "AXIS_ROUTED_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL"
    assert all(output["payload"]["selected_object"] == "CANDIDATE_A" for output in run["routed_outputs"])
    assert all(output["payload"]["selection_basis"] == "COMPOSITIONAL_ENTAILMENT" for output in run["routed_outputs"])
    assert all(output["payload"]["pragmatic_preference"] == "CANDIDATE_B" for output in run["routed_outputs"])
    assert all(output["fusion_receipt"]["semantic_inference_performed_by_runtime"] is False for output in run["routed_outputs"])
    pack = build_axis_external_annotation_pack(corpus=corpus, run=run)
    assert pack["candidate_outputs_exposed"] is False
    assert pack["frozen_candidate_run_hash_commitment"] == run["run_hash"]

