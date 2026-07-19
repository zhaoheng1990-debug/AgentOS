from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[1]


def nonblank(path):
    return sum(bool(line.strip()) for line in path.read_text(encoding="utf-8").splitlines())


def test_selector_calibration_runtime_stays_modular():
    kernel = CORE_ROOT / "agentos_kernel"
    runtime = CORE_ROOT / "agentos_runtime"
    limits = {
        kernel / "selector_calibration_base.py": 60,
        kernel / "selector_calibration_observation.py": 210,
        kernel / "selector_calibration_models.py": 280,
        kernel / "selector_calibration_eval.py": 120,
        kernel / "selector_calibration_gate.py": 110,
        runtime / "selector_calibration_adapter.py": 150,
        runtime / "selector_calibration_provider.py": 210,
        runtime / "selector_calibration_repository.py": 230,
        runtime / "selector_calibration_runtime.py": 160,
    }
    counts = {path.name: nonblank(path) for path in limits}
    assert all(counts[path.name] <= limit for path, limit in limits.items()), counts
