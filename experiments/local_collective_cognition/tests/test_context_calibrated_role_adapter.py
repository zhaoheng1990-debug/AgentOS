from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.context_calibrated_role_adapter import _margin_uncertainty, _score_messages  # noqa: E402


ITEM = {
    "conflict_id": "case-1",
    "public_prompt": "Choose the requested monthly event count.",
    "candidate_a": "events during the month",
    "candidate_b": "all registered entities",
}


def test_context_and_null_prompts_separate_object_information():
    context = _score_messages(role_id="OBJECT_GROUNDING", item=ITEM, null_context=False)
    null = _score_messages(role_id="OBJECT_GROUNDING", item=ITEM, null_context=True)
    assert "events during the month" in context[1]["content"]
    assert "events during the month" not in null[1]["content"]
    assert "withheld" in null[1]["content"]


def test_margin_maps_to_bounded_monotonic_uncertainty():
    assert _margin_uncertainty(0.01) > _margin_uncertainty(0.2) > _margin_uncertainty(0.7)

