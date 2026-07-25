import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
OUTPUT = ROOT / "outputs" / "admission_v9_external_panel_v0_84"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_v084_typed_reference_rejects_a18_and_preserves_a16():
    reference = read(
        OUTPUT / "typed_admission_reference_candidate_v0_84.json"
    )
    score = read(OUTPUT / "typed_reference_score_v0_84.json")

    assert reference["label_count"] == 48
    assert score["staged_to_candidate"]["corrected_count"] == 0
    assert score["staged_to_candidate"]["harmed_count"] == 4
    assert score["candidate_accuracy_delta_vs_staged"] < 0
    assert score["candidate_macro_f1_delta_vs_staged"] < 0
    assert score["experimental_decision"] == (
        "REJECT_A18_TYPED_REFERENCE_HARM"
    )
    assert score["candidate_acceptance_authorized"] is False
