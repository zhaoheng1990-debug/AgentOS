import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (
    ANTI_ADDITIVE_TRIGGER_IDS,
    AntiAdditiveChangeCandidate,
    AutonomousICMEvolutionPolicy,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    methodology_candidate_commitment,
)
from agentos_runtime import AntiAdditiveMethodologyRuntime


EVIDENCE = ("evidence://failure-history", "evidence://object-audit")


def evolution_candidate():
    return {
        "candidate_id": "operator-memory-upgrade",
        "research_line": "UtilityPolicySelector",
        "status": "ACCEPT_READY_WITH_EVIDENCE",
        "evidence_refs": list(EVIDENCE),
        "accept_decision_ref": "decision://accept-upgrade",
        "scope": "project_scoped",
        "project_scope_ref": "project://anti-additive-test",
        "target_type": "OperatorMemory",
        "negative_transfer_risk": "bounded",
        "future_cbit_gain": "positive",
        "replayable_evidence": True,
    }


def change_candidate(**overrides):
    evolution = evolution_candidate()
    values = {
        "audit_id": "audit-operator-memory-upgrade",
        "candidate_id": evolution["candidate_id"],
        "project_scope": evolution["project_scope_ref"],
        "change_kind": "MEMORY",
        "target_type": evolution["target_type"],
        "current_object_ref": "object://policy-score-proxy",
        "proposed_object_ref": "object://contextual-policy-control",
        "current_object_level": "PROXY",
        "proposed_object_level": "ONTOLOGY_OBJECT",
        "prior_failure_count": 3,
        "prior_patch_count": 4,
        "candidate_payload_hash": methodology_candidate_commitment(evolution),
        "evidence_refs": EVIDENCE,
    }
    values.update(overrides)
    return AntiAdditiveChangeCandidate.create(**values)


def provider_result(**overrides):
    active = set(overrides.pop("active_triggers", ()))
    values = {
        "current_object_adequacy": "UNDERPOWERED",
        "trigger_assessments": [
            {
                "trigger_id": trigger_id,
                "triggered": trigger_id in active,
                "rationale": f"bounded assessment for {trigger_id}",
                "evidence_refs": list(EVIDENCE),
            }
            for trigger_id in ANTI_ADDITIVE_TRIGGER_IDS
        ],
        "expected_effective_cbit_gain": 0.8,
        "complexity_cost": 0.25,
        "object_upgrade_gain": 0.7,
        "abstraction_cost": 0.2,
        "uncertainty": 0.2,
        "recommended_action": "UPGRADE_OBJECT",
        "rationale": "the higher-level object compresses repeated patch failures",
        "evidence_refs": list(EVIDENCE),
    }
    values.update(overrides)
    return values


class MethodologyProvider:
    def __init__(self, result=None, *, fail=False):
        self.profile = ProviderCapabilityProfile(
            provider_id="provider-methodology",
            model_id="fixture-methodology-model",
            task_kinds=("anti_additive_methodology_assessment",),
            max_timeout_seconds=120,
        )
        self.result = result or provider_result()
        self.fail = fail

    def invoke(self, task):
        if self.fail:
            raise RuntimeError("provider unavailable")
        return {
            "result": self.result,
            "usage": {"input_tokens": 10, "output_tokens": 10},
            "provenance_refs": list(EVIDENCE),
        }


def runtime(tmp_path, result=None, *, fail=False):
    return AntiAdditiveMethodologyRuntime(
        runtime_id="anti-additive-test",
        project_scope="project://anti-additive-test",
        provider_router=ProviderTaskRouter([MethodologyProvider(result, fail=fail)]),
        workspace_root=tmp_path,
    )


def test_valid_object_upgrade_is_replayable_and_authorizes_bounded_icm_write(tmp_path):
    engine = runtime(
        tmp_path,
        provider_result(active_triggers=("PATCH_PRESERVES_OBJECT_WITHOUT_CBIT_GAIN",)),
    )
    receipt = engine.review_change(
        candidate=change_candidate(),
        kernel_authorization_ref="kernel://anti-additive-review",
    )

    review = AutonomousICMEvolutionPolicy().review(evolution_candidate(), receipt)

    assert receipt.decision.state == "ALLOW_BOUNDED_CHANGE"
    assert receipt.decision.effective_cbit_margin == 0.55
    assert receipt.decision.object_upgrade_margin == 0.5
    assert receipt.as_dict()["baseline_write_authority"] is False
    assert review.decision == "AUTONOMOUS_PROJECT_OPERATORMEMORY_WRITE"
    assert review.methodology_receipt_hash == receipt.receipt_hash
    assert engine.verify_replay()["valid"] is True


def test_underpowered_object_with_same_level_patch_requires_object_upgrade(tmp_path):
    result = provider_result(active_triggers=("EDGE_CONTROL_WITH_CENTRAL_FAILURE",))
    receipt = runtime(tmp_path, result).review_change(
        candidate=change_candidate(proposed_object_level="PROXY"),
        kernel_authorization_ref="kernel://anti-additive-review",
    )

    review = AutonomousICMEvolutionPolicy().review(evolution_candidate(), receipt)

    assert receipt.decision.state == "REQUIRE_OBJECT_UPGRADE"
    assert receipt.decision.allowed is False
    assert review.reason == "anti_additive_methodology_not_allowed:REQUIRE_OBJECT_UPGRADE"


def test_nonpositive_effective_cbit_margin_blocks_patch_accumulation(tmp_path):
    result = provider_result(expected_effective_cbit_gain=0.3, complexity_cost=0.3)

    receipt = runtime(tmp_path, result).review_change(
        candidate=change_candidate(),
        kernel_authorization_ref="kernel://anti-additive-review",
    )

    assert receipt.decision.state == "BLOCK_PATCH_ACCUMULATION"
    assert receipt.decision.effective_cbit_margin == 0.0


def test_low_value_object_lift_is_blocked_as_abstraction_fog(tmp_path):
    result = provider_result(object_upgrade_gain=0.2, abstraction_cost=0.4)

    receipt = runtime(tmp_path, result).review_change(
        candidate=change_candidate(),
        kernel_authorization_ref="kernel://anti-additive-review",
    )

    assert receipt.decision.state == "BLOCK_ABSTRACTION_FOG"
    assert receipt.decision.object_upgrade_margin == -0.2


def test_provider_unavailable_fails_closed_without_methodology_receipt(tmp_path):
    engine = runtime(tmp_path, fail=True)

    with pytest.raises(RuntimeError, match="anti_additive_provider_blocked:PROVIDER_UNAVAILABLE"):
        engine.review_change(
            candidate=change_candidate(),
            kernel_authorization_ref="kernel://anti-additive-review",
        )

    assert engine.verify_replay()["valid"] is True
    assert engine.verify_replay()["receipt_hashes"] == []


def test_incomplete_trigger_surface_is_rejected_before_kernel_decision(tmp_path):
    result = provider_result()
    result["trigger_assessments"] = result["trigger_assessments"][:-1]

    with pytest.raises(ValueError, match="anti_additive_provider_trigger_count_invalid"):
        runtime(tmp_path, result).review_change(
            candidate=change_candidate(),
            kernel_authorization_ref="kernel://anti-additive-review",
        )


def test_ledger_tamper_is_detected(tmp_path):
    engine = runtime(tmp_path)
    engine.review_change(
        candidate=change_candidate(),
        kernel_authorization_ref="kernel://anti-additive-review",
    )
    events_path = engine.public_store_path / "events.jsonl"
    event = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])
    event["payload"]["receipt"]["decision"]["state"] = "BLOCK_PATCH_ACCUMULATION"
    events_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    replay = engine.verify_replay()

    assert replay["valid"] is False
    assert "event_hash_invalid:1" in replay["failures"]
    assert "receipt_hash_invalid:1" in replay["failures"]


def test_cross_scope_candidate_is_rejected_before_provider_call(tmp_path):
    with pytest.raises(ValueError, match="anti_additive_runtime_cross_scope_candidate"):
        runtime(tmp_path).review_change(
            candidate=change_candidate(project_scope="project://other"),
            kernel_authorization_ref="kernel://anti-additive-review",
        )
