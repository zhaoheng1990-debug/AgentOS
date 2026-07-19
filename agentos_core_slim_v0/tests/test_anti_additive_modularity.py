import ast
from pathlib import Path


CORE = Path(__file__).resolve().parents[1]


def nonblank(path):
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def imports_runtime_from_kernel(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.startswith("agentos_runtime") for alias in node.names):
                return True
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("agentos_runtime"):
            return True
    return False


def test_anti_additive_runtime_stays_a_thin_orchestrator():
    assert nonblank(CORE / "agentos_runtime" / "anti_additive_runtime.py") <= 90
    assert nonblank(CORE / "agentos_runtime" / "anti_additive_repository.py") <= 160
    assert nonblank(CORE / "agentos_runtime" / "anti_additive_codec.py") <= 70
    assert nonblank(CORE / "agentos_runtime" / "anti_additive_provider.py") <= 220
    assert nonblank(CORE / "agentos_kernel" / "anti_additive_gate.py") <= 120
    assert nonblank(CORE / "agentos_kernel" / "anti_additive_base.py") <= 170
    assert nonblank(CORE / "agentos_kernel" / "anti_additive_judgment.py") <= 120
    assert nonblank(CORE / "agentos_kernel" / "anti_additive_decision.py") <= 150
    assert nonblank(CORE / "agentos_kernel" / "anti_additive_models.py") <= 50
    assert nonblank(CORE / "agentos_kernel" / "anti_additive_control.py") <= 130
    assert nonblank(CORE / "agentos_kernel" / "anti_additive_calibration_observation.py") <= 120
    assert nonblank(CORE / "agentos_kernel" / "anti_additive_calibration_models.py") <= 190
    assert nonblank(CORE / "agentos_kernel" / "anti_additive_calibration_eval.py") <= 100
    assert nonblank(CORE / "agentos_runtime" / "anti_additive_calibration_repository.py") <= 170
    assert nonblank(CORE / "agentos_runtime" / "anti_additive_calibration_source.py") <= 80
    assert nonblank(CORE / "agentos_runtime" / "anti_additive_calibration_runtime.py") <= 130
    assert nonblank(CORE / "agentos_runtime" / "anti_additive_source.py") <= 60
    assert nonblank(CORE / "agentos_runtime" / "anti_additive_baseline_evolution.py") <= 50
    assert nonblank(CORE / "agentos_runtime" / "anti_additive_problem_structure.py") <= 45


def test_anti_additive_kernel_modules_do_not_import_runtime():
    for name in (
        "anti_additive_base.py",
        "anti_additive_judgment.py",
        "anti_additive_decision.py",
        "anti_additive_models.py",
        "anti_additive_gate.py",
        "anti_additive_control.py",
        "anti_additive_calibration_observation.py",
        "anti_additive_calibration_models.py",
        "anti_additive_calibration_eval.py",
    ):
        assert imports_runtime_from_kernel(CORE / "agentos_kernel" / name) is False
