import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
OUTPUT = ROOT / "outputs" / "admission_v10_external_panel_v0_85"


def test_v085_external_lanes_reject_all_a19_mutations():
    analysis = json.loads(
        (OUTPUT / "lane_analysis.json").read_text(encoding="utf-8")
    )

    assert analysis["agreement_count"] == 3
    assert analysis["disagreement_count"] == 1
    assert analysis["mutation_outcome_counts"] == {
        "CORRECTED": 0,
        "HARMED": 2,
        "UNRESOLVED": 0,
    }
    assert analysis["all_mutations_resolved_by_lane_agreement"] is True
    assert analysis[
        "control_adjudication_required_for_mechanism_decision"
    ] is False
    assert analysis["mechanism_decision"] == (
        "REJECT_A19_ALL_MUTATIONS_EXTERNALLY_HARMFUL"
    )
    assert analysis["candidate_acceptance_authorized"] is False
