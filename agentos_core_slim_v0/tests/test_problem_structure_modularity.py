import ast
import sys
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
    ProblemStructureAdmissionGate,
    ProblemStructureCandidate,
)
from agentos_kernel.problem_structure_admission_gate import (  # noqa: E402
    ProblemStructureAdmissionGate as FocusedAdmissionGate,
)
from agentos_kernel.problem_structure_admission_models import (  # noqa: E402
    ProblemStructureCandidate as FocusedCandidate,
)
from agentos_runtime import (  # noqa: E402
    ProblemDefinitionStructureAdapter,
    ProblemStructureAdmissionRuntime,
    ProblemStructureProviderAdvisor,
    ProblemStructureRepository,
)


def nonblank(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def test_problem_structure_kernel_is_runtime_and_filesystem_independent():
    kernel_root = CORE_ROOT / "agentos_kernel"
    forbidden_roots = {"agentos_runtime", "os", "pathlib"}
    for filename in (
        "problem_structure_admission_models.py",
        "problem_structure_admission_gate.py",
    ):
        tree = ast.parse((kernel_root / filename).read_text(encoding="utf-8"))
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        assert imported_roots.isdisjoint(forbidden_roots), (filename, imported_roots)

    assert ProblemStructureCandidate is FocusedCandidate
    assert ProblemStructureAdmissionGate is FocusedAdmissionGate
    assert nonblank(kernel_root / "problem_structure_admission_models.py") <= 390
    assert nonblank(kernel_root / "problem_structure_admission_gate.py") <= 120


def test_problem_structure_runtime_services_remain_focused():
    runtime_root = CORE_ROOT / "agentos_runtime"
    assert nonblank(runtime_root / "problem_structure_admission.py") <= 165
    assert nonblank(runtime_root / "problem_structure_repository.py") <= 205
    assert nonblank(runtime_root / "problem_structure_provider.py") <= 200
    assert nonblank(runtime_root / "problem_structure_source_adapter.py") <= 185
    assert ProblemStructureAdmissionRuntime.__module__.endswith("problem_structure_admission")
    assert ProblemStructureRepository.__module__.endswith("problem_structure_repository")
    assert ProblemStructureProviderAdvisor.__module__.endswith("problem_structure_provider")
    assert ProblemDefinitionStructureAdapter.__module__.endswith(
        "problem_structure_source_adapter"
    )
