import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.audit_release_artifacts import audit_artifact_dir
from examples.sro_retention_runtime_smoke import run_smoke


def test_sro_retention_smoke_closes_migration_route_restart_and_packaging(tmp_path):
    output_dir = tmp_path / "sro-retention-smoke"

    result = run_smoke(output_dir)
    audit = audit_artifact_dir(output_dir)

    assert result["status"] == "PASS"
    assert all(result["gates"].values())
    assert result["provider_task_count"] == 1
    assert result["initial_migration"]["candidate_state"] == "PENDING_PROVIDER_REVALIDATION"
    assert result["revalidated_migration"]["candidate_state"] == "PENDING_WITNESS_RECONSTRUCTION"
    assert result["route_receipt"]["decision"]["route"] == "DIRECT_REUSE"
    assert result["restart_replay"]["valid"]
    assert audit["status"] == "PASS"
