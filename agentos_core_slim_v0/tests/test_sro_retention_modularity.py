import ast
import sys
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
    DelayedRetrievalLedger,
    GradedSROCompatibilityGate,
    SROMatcherReceiptValidator,
    SerialSelectionWitness,
)
from agentos_kernel.delayed_retrieval import DelayedRetrievalLedger as FocusedDelayedLedger  # noqa: E402
from agentos_kernel.sro_retention_models import SerialSelectionWitness as FocusedWitness  # noqa: E402
from agentos_kernel.sro_retention_policy import GradedSROCompatibilityGate as FocusedGate  # noqa: E402
from agentos_kernel.sro_retention_receipt import SROMatcherReceiptValidator as FocusedValidator  # noqa: E402
from agentos_runtime import (  # noqa: E402
    JsonlDelayedRetrievalEventStore,
    LegacyRetentionMigrator,
    ProviderBackedSROMatcher,
    SRORetentionRepository,
)


KERNEL_SRO_MODULES = (
    "sro_retention_models.py",
    "sro_retention_receipt.py",
    "sro_retention_policy.py",
    "delayed_retrieval.py",
)


def test_kernel_sro_modules_are_pure_and_runtime_independent():
    kernel_root = CORE_ROOT / "agentos_kernel"
    forbidden_roots = {"agentos_runtime", "os", "pathlib"}

    for filename in KERNEL_SRO_MODULES:
        tree = ast.parse((kernel_root / filename).read_text(encoding="utf-8"))
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        assert imported_roots.isdisjoint(forbidden_roots), (filename, imported_roots)


def test_compatibility_exports_are_the_focused_module_types():
    assert DelayedRetrievalLedger is FocusedDelayedLedger
    assert SerialSelectionWitness is FocusedWitness
    assert GradedSROCompatibilityGate is FocusedGate
    assert SROMatcherReceiptValidator is FocusedValidator


def test_runtime_exposes_independent_sro_services():
    assert LegacyRetentionMigrator.__module__.endswith("sro_retention_migration")
    assert ProviderBackedSROMatcher.__module__.endswith("sro_retention_provider")
    assert SRORetentionRepository.__module__.endswith("sro_retention_repository")
    assert JsonlDelayedRetrievalEventStore.__module__.endswith("sro_retention_persistence")
