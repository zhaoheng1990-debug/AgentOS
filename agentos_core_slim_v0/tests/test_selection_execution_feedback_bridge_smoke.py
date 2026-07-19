import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.audit_release_artifacts import audit_artifact_dir
from examples.selection_execution_feedback_bridge_smoke import run_smoke


def test_real_execution_feedback_bridge_closes_learning_loop_and_packaging(tmp_path):
    output_dir = tmp_path / "selection-execution-feedback-smoke"

    result = run_smoke(output_dir)
    audit = audit_artifact_dir(output_dir)

    assert result["status"] == "PASS"
    assert all(result["gates"].values())
    assert result["initial_selection"]["kernel_decision"]["activation_mode"] == (
        "EXPLORATORY_TRIAL_ONLY"
    )
    assert result["second_feedback"]["matched_evidence"][2]["matched_pair_count"] == 2
    assert result["downstream_selection"]["kernel_decision"]["activation_mode"] == (
        "AUTHORIZED_PROJECT_SCOPED"
    )
    assert result["restart_replay"]["valid"]
    assert audit["status"] == "PASS"
