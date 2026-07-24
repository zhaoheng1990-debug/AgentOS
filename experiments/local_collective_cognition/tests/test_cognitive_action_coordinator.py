from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_coordinator import tuple_violations, validate_coordinator_payload  # noqa: E402


def payload():
    return {"conflict_id": "c1", "selected_object": "NONE", "selection_basis": "PRAGMATIC_DEFAULT", "pragmatic_preference": "CANDIDATE_A", "assessment_completeness": "COMPLETE", "action": "CLARIFY", "rationale": "The prompt leaves the semantic object open.", "confidence": 0.7, "evidence_refs": ["corpus://fresh"]}


def test_coherent_open_tuple_is_valid():
    value = payload()
    assert tuple_violations(value) == []
    validate_coordinator_payload(value, conflict_id="c1", evidence_refs=("corpus://fresh",))


def test_hard_basis_without_selected_object_is_rejected():
    value = payload()
    value["selection_basis"] = "COMPOSITIONAL_ENTAILMENT"
    assert "HARD_BASIS_WITHOUT_OBJECT" in tuple_violations(value)
    with pytest.raises(ValueError, match="tuple_incoherent"):
        validate_coordinator_payload(value, conflict_id="c1", evidence_refs=("corpus://fresh",))

