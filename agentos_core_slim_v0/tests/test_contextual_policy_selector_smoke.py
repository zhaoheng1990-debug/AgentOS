import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.audit_release_artifacts import audit_artifact_dir
from examples.contextual_organization_policy_selector_smoke import run_smoke


def test_contextual_policy_selector_smoke_closes_selection_restart_and_packaging(tmp_path):
    output_dir = tmp_path / "contextual-policy-selector-smoke"

    result = run_smoke(output_dir)
    audit = audit_artifact_dir(output_dir)

    assert result["status"] == "PASS"
    assert all(result["gates"].values())
    assert result["provider_task_count"] == 1
    assert result["selection_receipt"]["provider_advice"]["recommended_policy_id"] == "DYNAMIC_TEAM"
    assert result["selection_receipt"]["kernel_decision"]["selected_policy_id"] == (
        "DYNAMIC_NO_SYNTHESIZER"
    )
    assert result["restart_replay"]["valid"]
    assert audit["status"] == "PASS"
