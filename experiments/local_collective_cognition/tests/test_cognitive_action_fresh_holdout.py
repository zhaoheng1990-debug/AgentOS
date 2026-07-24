from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_fresh_holdout import build_fresh_action_holdout, validate_fresh_action_holdout  # noqa: E402


def test_fresh_holdout_is_balanced_unlabeled_and_candidate_blind():
    artifact = build_fresh_action_holdout()
    validate_fresh_action_holdout(artifact)
    assert artifact["case_count"] == 24
    assert set(artifact["family_counts"].values()) == {4}
    assert artifact["reference_state"] == "UNLABELED_FROZEN_BEFORE_CANDIDATE_RUN"
    assert artifact["private_provenance"]["semantic_labels_present"] is False
    assert artifact["public_surface"]["candidate_outputs_exposed"] is False

