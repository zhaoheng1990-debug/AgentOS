import json
from pathlib import Path

from local_collective_cognition.admission_v7_typed_scoring import (
    score_staged_context_reference,
)


ROOT = Path(__file__).parents[3]
EXTERNAL = ROOT / "outputs" / "admission_v7_external_panel_v0_82"
SOURCE = ROOT / "outputs" / "admission_v7_fresh_holdout_v0_82"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_v082_real_typed_reference_rejects_combined_promotion():
    score = score_staged_context_reference(
        reference=read(
            EXTERNAL / "typed_admission_reference_candidate_v0_82.json"
        ),
        baseline_run=read(SOURCE / "baseline_run.json"),
        atomic_run=read(SOURCE / "atomic_run.json"),
        candidate_run=read(SOURCE / "candidate_run.json"),
    )

    assert len(score["atomic_to_candidate_corrected_spans"]) == 19
    assert score["atomic_to_candidate_harmed_spans"] == []
    assert score["candidate"]["per_class"]["REJECT"]["f1"] > 0.97
    assert score["preregistered_semantic_conditions"][
        "valid_context_recall_floor"
    ] is False
    assert score["experimental_decision"] == (
        "REJECT_STAGED_CONTEXT_TYPED_GATE"
    )
    assert score["candidate_acceptance_authorized"] is False
