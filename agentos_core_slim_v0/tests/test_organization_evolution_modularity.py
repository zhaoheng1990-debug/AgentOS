from pathlib import Path

from agentos_kernel import (
    ORGANIZATION_EVOLUTION_OPERATOR_FAMILIES,
    ORGANIZATION_EVOLUTION_OPERATOR_IDS,
    ProviderBackedRuntimeCognitionLayer,
)
from agentos_kernel.provider_cognition_layer import PROVIDER_REQUIRED
from agentos_runtime import OrganizationEvolutionRuntime, OrganizationEvolutionStrategy


ROOT = Path(__file__).resolve().parents[1]


def test_provider_cognition_contract_registers_organization_evolution():
    contract = ProviderBackedRuntimeCognitionLayer().operation_contract("organization_evolution_proposal")
    assert contract["provider_requirement"] == PROVIDER_REQUIRED
    assert contract["runtime_role"]
    assert set(contract["required_provider_outputs"]) == {
        "proposals",
        "global_rationale",
        "uncertainty",
        "evidence_refs",
    }


def test_operator_registry_preserves_exploration_and_exploitation_families():
    assert set(ORGANIZATION_EVOLUTION_OPERATOR_IDS) == set(ORGANIZATION_EVOLUTION_OPERATOR_FAMILIES)
    assert set(ORGANIZATION_EVOLUTION_OPERATOR_FAMILIES.values()) == {"EXPLORATION", "EXPLOITATION"}


def test_runtime_facade_stays_thin_and_strategy_is_separate():
    runtime_source = ROOT / "agentos_runtime" / "organization_evolution.py"
    strategy_source = ROOT / "agentos_runtime" / "organization_evolution_strategy.py"
    assert len(runtime_source.read_text(encoding="utf-8").splitlines()) <= 320
    assert len(strategy_source.read_text(encoding="utf-8").splitlines()) <= 100
    assert OrganizationEvolutionRuntime.__module__.endswith("organization_evolution")
    assert OrganizationEvolutionStrategy.__module__.endswith("organization_evolution_strategy")


def test_kernel_organization_modules_do_not_import_runtime_or_filesystem():
    for name in ("organization_evolution_models.py", "organization_evolution_eval.py"):
        source = (ROOT / "agentos_kernel" / name).read_text(encoding="utf-8")
        assert "agentos_runtime" not in source
        assert "pathlib" not in source
