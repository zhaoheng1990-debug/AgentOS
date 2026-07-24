from examples.organization_evolution_smoke import run_smoke


def test_organization_evolution_smoke_closes_optimization_and_replay(tmp_path):
    result = run_smoke(tmp_path / "organization-evolution-smoke")
    assert result["status"] == "PASS"
    assert result["retained_operator"] == "ADD_ROLE"
    assert result["baseline_genome_hash"] != result["retained_genome_hash"]
    assert result["generation_count"] == 1
    assert result["spent_provider_calls"] == 1
    assert result["replay"]["valid"] is True
