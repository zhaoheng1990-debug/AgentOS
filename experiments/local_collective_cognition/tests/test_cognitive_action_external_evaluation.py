from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_external_evaluation import (  # noqa: E402
    validate_external_evaluation,
    validate_external_reference,
)


SOURCE = ROOT / "outputs" / "cognitive_action_overnight_v0_16"
PANEL = SOURCE / "external_panel"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_frozen_reference_is_complete_coherent_and_candidate_blind():
    reference = read(PANEL / "cognitive_action_external_reference_candidate.json")
    validate_external_reference(reference)
    assert reference["object_count"] == 24
    assert reference["label_count"] == 96
    assert reference["candidate_outputs_exposed_to_panel"] is False
    assert reference["reference_revision_allowed"] is False


def test_external_evaluation_replays_and_preserves_zero_net_cell_gain():
    reference = read(PANEL / "cognitive_action_external_reference_candidate.json")
    evaluation = read(PANEL / "cognitive_action_external_evaluation.json")
    inputs = {
        "reference": reference,
        "role_run": read(SOURCE / "fresh_action_role_run.json"),
        "role_analysis": read(SOURCE / "fresh_action_role_analysis.json"),
        "coordinator_run": read(SOURCE / "blind_coordinator_arms_run.json"),
        "coordinator_analysis": read(SOURCE / "blind_coordinator_arms_analysis.json"),
    }
    validate_external_evaluation(evaluation, **inputs)
    assert evaluation["net_correct_cell_delta"] == 0
    assert evaluation["correction_counts"]["corrections"] == 14
    assert evaluation["correction_counts"]["harms"] == 14
    assert evaluation["anti_additive_gate"] == "REJECT"
    assert evaluation["arm_metrics"]["ROLE_INFORMED_COORDINATOR"]["full_tuple_correct"] == 3
    assert evaluation["arm_metrics"]["SINGLE_MODEL_BASELINE"]["full_tuple_correct"] == 1


def test_reference_hash_detects_post_freeze_mutation():
    reference = read(PANEL / "cognitive_action_external_reference_candidate.json")
    broken = deepcopy(reference)
    broken["labels"][0]["criteria"]["SELECTED_OBJECT"] = "UNCERTAIN"
    with pytest.raises(ValueError, match="reference_invalid"):
        validate_external_reference(broken)

