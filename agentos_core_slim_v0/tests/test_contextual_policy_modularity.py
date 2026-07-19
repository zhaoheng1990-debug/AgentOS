import ast
import sys
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
    ContextualMatchedEvidenceEvaluator,
    ContextualOrganizationPolicySelector,
    ContextualProblemStructure,
)
from agentos_kernel.contextual_policy_evidence import (  # noqa: E402
    ContextualMatchedEvidenceEvaluator as FocusedEvidenceEvaluator,
)
from agentos_kernel.contextual_policy_models import (  # noqa: E402
    ContextualProblemStructure as FocusedProblemStructure,
)
from agentos_kernel.contextual_policy_selector import (  # noqa: E402
    ContextualOrganizationPolicySelector as FocusedKernelSelector,
)
from agentos_runtime import (  # noqa: E402
    ContextualOrganizationPolicyRuntime,
    ContextualOrganizationProviderAdvisor,
    ContextualPolicyRepository,
    SelectionExecutionFeedbackBridge,
    SelectionFeedbackRepository,
    TeamExecutionPolicyAdapter,
)


KERNEL_POLICY_MODULES = (
    "contextual_policy_models.py",
    "contextual_policy_evidence.py",
    "contextual_policy_selector.py",
)


def test_contextual_policy_kernel_modules_are_runtime_and_filesystem_independent():
    kernel_root = CORE_ROOT / "agentos_kernel"
    forbidden_roots = {"agentos_runtime", "os", "pathlib"}

    for filename in KERNEL_POLICY_MODULES:
        tree = ast.parse((kernel_root / filename).read_text(encoding="utf-8"))
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        assert imported_roots.isdisjoint(forbidden_roots), (filename, imported_roots)


def test_public_exports_resolve_to_focused_kernel_modules():
    assert ContextualProblemStructure is FocusedProblemStructure
    assert ContextualMatchedEvidenceEvaluator is FocusedEvidenceEvaluator
    assert ContextualOrganizationPolicySelector is FocusedKernelSelector


def test_runtime_facade_remains_thin_and_services_are_independent():
    runtime_path = CORE_ROOT / "agentos_runtime" / "contextual_policy_runtime.py"
    nonblank_lines = [line for line in runtime_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert len(nonblank_lines) <= 200
    assert ContextualOrganizationPolicyRuntime.__module__.endswith("contextual_policy_runtime")
    assert ContextualOrganizationProviderAdvisor.__module__.endswith("contextual_policy_provider")
    assert ContextualPolicyRepository.__module__.endswith("contextual_policy_repository")


def test_feedback_bridge_remains_a_thin_composition_root():
    bridge_path = CORE_ROOT / "agentos_runtime" / "selection_feedback_bridge.py"
    repository_path = CORE_ROOT / "agentos_runtime" / "selection_feedback_repository.py"
    adapters_path = CORE_ROOT / "agentos_runtime" / "selection_execution_adapters.py"
    nonblank_lines = [line for line in bridge_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    repository_lines = [
        line for line in repository_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    adapter_lines = [
        line for line in adapters_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]

    assert len(nonblank_lines) <= 180
    assert len(repository_lines) <= 180
    assert len(adapter_lines) <= 320
    assert SelectionExecutionFeedbackBridge.__module__.endswith("selection_feedback_bridge")
    assert SelectionFeedbackRepository.__module__.endswith("selection_feedback_repository")
    assert TeamExecutionPolicyAdapter.__module__.endswith("selection_execution_adapters")


def test_feedback_kernel_contracts_are_runtime_and_filesystem_independent():
    kernel_root = CORE_ROOT / "agentos_kernel"
    forbidden_roots = {"agentos_runtime", "os", "pathlib"}
    for filename in (
        "selection_execution_models.py",
        "selection_execution_outcomes.py",
        "selection_feedback_gate.py",
    ):
        tree = ast.parse((kernel_root / filename).read_text(encoding="utf-8"))
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        assert imported_roots.isdisjoint(forbidden_roots), (filename, imported_roots)

    request_lines = [
        line
        for line in (kernel_root / "selection_execution_models.py")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    outcome_lines = [
        line
        for line in (kernel_root / "selection_execution_outcomes.py")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert len(request_lines) <= 210
    assert len(outcome_lines) <= 270
