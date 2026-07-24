import pytest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_protocol import (
    ACTION_TYPES,
    ActionCost,
    allowed_actions,
    build_action_receipt,
    validate_action_receipt,
)


def test_canonical_action_receipt_round_trips_with_runtime_authority():
    receipt = build_action_receipt(
        action_id="act-1",
        action_type="DEFINE_OBJECT",
        object_ref="object://case-1",
        actor_role="OBJECT_GROUNDING",
        actor_instance="qwen-role-1",
        method="grammar-backed finite semantic choice",
        result_state="CANDIDATE",
        result={"selected_object": "CANDIDATE_A"},
        evidence_refs=("corpus://fresh",),
        uncertainty=0.25,
        recommended_next_actions=("FALSIFY", "SYNTHESIZE"),
        cost=ActionCost(provider_calls=1, input_tokens=100, output_tokens=3, latency_ms=20),
    )
    validate_action_receipt(receipt)
    assert receipt["provider_semantic_choice"] is True
    assert receipt["runtime_final_state_authority"] is True
    assert receipt["provider_selection_authority"] is False


def test_role_cannot_emit_action_outside_capability_envelope():
    with pytest.raises(ValueError, match="outside_role_capability"):
        build_action_receipt(
            action_id="act-2",
            action_type="ADJUDICATE",
            object_ref="object://case-2",
            actor_role="OBJECT_GROUNDING",
            actor_instance="model-role-2",
            method="invalid escalation",
            result_state="CANDIDATE",
            result={},
        )


def test_protocol_exposes_standard_actions_and_deduplicated_role_actions():
    assert {"VERIFY", "VALIDATE", "FALSIFY", "REPLICATE", "GENERATE_QUESTION"}.issubset(ACTION_TYPES)
    actions = allowed_actions("COORDINATOR")
    assert len(actions) == len(set(actions))
    assert "SYNTHESIZE" in actions
