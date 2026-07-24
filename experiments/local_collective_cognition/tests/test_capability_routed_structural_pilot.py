from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(Path(__file__).resolve().parents[1])]

from local_collective_cognition.capability_routed_structural_holdout import (  # noqa: E402
    QUESTIONS, build_capability_routed_structural_harness, mechanical_truth_checks,
)
from local_collective_cognition.capability_routed_structural_runtime import DEFAULT_ASSIGNMENTS  # noqa: E402
from local_collective_cognition.structure_capability_routing import (  # noqa: E402
    packet_placeholder_pre_gate, route_structure_elicitor,
)


def test_capability_route_prefers_positive_transfer_candidate_without_authority():
    receipt = route_structure_elicitor(
        eligible_model_ids=("llama-3.2-1b-instruct", "gemma-2-2b-it"),
        source_report_hash="a" * 64,
    )
    assert receipt["selected_model_id"] == "gemma-2-2b-it"
    assert receipt["support_mode"] == "TRANSFER_CANDIDATE_EXPLORATORY"
    assert receipt["same_context_support"] is False
    assert receipt["retention_authority"] is False


def test_mechanical_pre_gate_blocks_identifier_and_allows_structural_content():
    blocked = packet_placeholder_pre_gate(
        packet={"item_id": "modular-28", "contrastive_packet": "modular-28"},
        public_prompt="What is the remainder?",
    )
    allowed = packet_placeholder_pre_gate(
        packet={"item_id": "modular-28", "contrastive_packet": (
            "Rival 1 treats this as quotient selection; rival 2 treats it as a remainder. "
            "The decisive question is which output the public task requests."
        )},
        public_prompt="What is the remainder?",
    )
    assert blocked["status"] == "BLOCK"
    assert "PACKET_IDENTIFIER_OR_PROMPT_ONLY" in blocked["reasons"]
    assert allowed["status"] == "ALLOW"


def test_fresh_holdout_is_truth_blind_mechanically_valid_and_keeps_gemma_independent():
    harness = build_capability_routed_structural_harness()
    assert len(QUESTIONS) == 6 and all(mechanical_truth_checks())
    assert "truth" not in str(harness.provider_inputs()).lower()
    assert {model for _, model in DEFAULT_ASSIGNMENTS} == {
        "qwen2.5-1.5b-instruct", "llama-3.2-1b-instruct"
    }
