import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.cognitive_team_execution_project_source_smoke import (
    load_life_case,
    load_math_cbit1_case,
    load_ocs1r2_case,
    run_case,
)
from examples.project_source_group_cognition_smoke import default_paths


def test_default_project_source_fixtures_are_committed_and_repo_local():
    core_root = Path(__file__).resolve().parents[1]
    source_fixture, gate_fixture = default_paths()

    assert source_fixture.is_file()
    assert gate_fixture.is_file()
    assert core_root in source_fixture.resolve().parents
    assert core_root in gate_fixture.resolve().parents


@pytest.mark.parametrize("loader", (load_life_case, load_math_cbit1_case, load_ocs1r2_case))
def test_project_source_case_keeps_hidden_truth_out_of_public_evidence(loader):
    case = loader()

    assert len(case.finding_catalog) == 3
    assert {item.expected_state for item in case.hidden_truths} == {
        "SUPPORTED",
        "REJECTED",
        "UNRESOLVED",
    }
    public = json.dumps(case.evidence_payload, sort_keys=True).lower()
    assert "expected_state" not in public
    assert "ground_truth" not in public


@pytest.mark.parametrize("loader", (load_life_case, load_math_cbit1_case, load_ocs1r2_case))
def test_scripted_three_arm_project_source_smoke_closes_runtime_and_artifacts(tmp_path, loader):
    case = loader()
    output_dir = tmp_path / case.case_id

    result = run_case(case, output_dir, provider_mode="scripted", coordinated=True)

    assert result["status"] == "PASS"
    assert all(result["gates"].values())
    assert result["counterfactual_evaluation"]["verdict_vs_best_member"] == "OUTPERFORMS"
    assert result["counterfactual_evaluation"]["verdict_vs_fixed_team"] == "OUTPERFORMS"
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "PASS"
    pack = output_dir / "AgentOS_CognitiveTeamExecution_ProjectSource_ReturnPack_v0_1.zip"
    with zipfile.ZipFile(pack) as archive:
        assert "manifest.json" in archive.namelist()
        assert "smoke_result.json" in archive.namelist()
