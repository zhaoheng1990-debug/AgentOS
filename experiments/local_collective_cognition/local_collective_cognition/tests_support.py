"""Small deterministic fixtures shared by experiment tests."""

from __future__ import annotations

from agentos_kernel import ProviderCapabilityProfile

from .cognitive_action_protocol import ActionCost, build_action_receipt
from .cognitive_action_selective_holdout import build_selective_holdout
from .cognitive_action_selective_runtime import (
    SELECTIVE_TASK_KIND,
    SOURCE_EVALUATION_HASH,
    SOURCE_REFERENCE_HASH,
    build_admission_plan,
    build_selective_preregistration,
    run_local_preference_roles,
    run_selective_adjudication,
    run_selective_baseline,
)
from .provider_telemetry import hash_payload


class _Provider:
    def __init__(self):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-selective-panel",
            model_id="fixture-model",
            task_kinds=(SELECTIVE_TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        conflict_id = task.inputs["public_object"]["conflict_id"]
        evidence = list(task.allowed_evidence)
        if "frozen_selected_object" in task.inputs:
            result = {
                "conflict_id": conflict_id,
                "pragmatic_preference": "CANDIDATE_A",
                "rationale": "Fixture preference.",
                "confidence": 0.8,
                "evidence_refs": evidence,
            }
        else:
            result = {
                "conflict_id": conflict_id,
                "selected_object": "NONE",
                "selection_basis": "NO_PREFERENCE",
                "pragmatic_preference": "NONE",
                "evidence_state": "SOFT_AMBIGUITY",
                "assessment_process_state": "COMPLETE",
                "action": "CLARIFY",
                "rationale": "Fixture open assessment.",
                "confidence": 0.7,
                "evidence_refs": evidence,
            }
        return {
            "result": result,
            "usage": {"provider_calls": 1, "input_tokens": 10, "output_tokens": 2, "latency_ms": 1},
            "provenance_refs": evidence,
        }


class _Local:
    model_id = "fixture-local"

    def invoke(self, *, role_id, item, evidence_refs):
        receipt = build_action_receipt(
            action_id="fixture-" + item["conflict_id"],
            action_type="COMPARE",
            object_ref="object://" + item["conflict_id"],
            actor_role=role_id,
            actor_instance=self.model_id,
            method="fixture",
            result_state="CANDIDATE",
            result={"pragmatic_preference": "CANDIDATE_A"},
            evidence_refs=evidence_refs,
            support=("Fixture.",),
            cost=ActionCost(provider_calls=1, input_tokens=3, output_tokens=1, latency_ms=1),
        )
        commitment = {
            "adapter_version": "staged_semantic_scoring_adapter_v0_16",
            "model_id": self.model_id,
            "role_id": role_id,
            "object_ref": "object://" + item["conflict_id"],
            "registry_hash": hash_payload(["fixture", role_id]),
            "selected_call": "STAGED_SCORE",
            "action_receipt": receipt,
            "score_receipt": {"score_hash": "fixture"},
            "wall_latency_ms": 1,
            "reference_available": False,
        }
        return {**commitment, "output_hash": hash_payload(commitment)}


def build_selective_fixture_bundle():
    corpus = build_selective_holdout()
    source = {
        "artifact_hash": SOURCE_EVALUATION_HASH,
        "reference_hash": SOURCE_REFERENCE_HASH,
        "anti_additive_gate": "REJECT",
        "candidate_state": "AXIS_ROUTING_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION",
    }
    prereg = build_selective_preregistration(source_evaluation=source)
    baseline = run_selective_baseline(corpus=corpus, preregistration=prereg, adapter=_Provider())
    plan = build_admission_plan(corpus=corpus, preregistration=prereg, baseline_run=baseline)
    local = run_local_preference_roles(corpus=corpus, admission_plan=plan, adapter=_Local())
    run = run_selective_adjudication(
        corpus=corpus,
        preregistration=prereg,
        baseline_run=baseline,
        admission_plan=plan,
        local_role_run=local,
        adapter=_Provider(),
    )
    return corpus, baseline, run
