from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.staged_semantic_role_adapter import _margin, _primary_prompt  # noqa: E402


ITEM = {"public_prompt": "request", "candidate_a": "alpha", "candidate_b": "beta"}


def test_swapped_prompt_exchanges_candidate_contents_without_changing_request():
    original = _primary_prompt(ITEM, "OBJECT_GROUNDING", swapped=False, null=False)
    swapped = _primary_prompt(ITEM, "OBJECT_GROUNDING", swapped=True, null=False)
    assert "Candidate A: alpha" in original[1]["content"]
    assert "Candidate A: beta" in swapped[1]["content"]
    assert "Request: request" in original[1]["content"] and "Request: request" in swapped[1]["content"]


def test_margin_is_top_two_difference():
    assert _margin({"A": 0.9, "B": 0.4, "NONE": 0.1}) == 0.5

