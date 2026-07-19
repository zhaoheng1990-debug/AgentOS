from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[1]


def nonblank(path):
    return sum(bool(line.strip()) for line in path.read_text(encoding="utf-8").splitlines())


def test_calibration_control_slice_stays_modular_and_kernel_pure():
    kernel = CORE_ROOT / "agentos_kernel"
    runtime = CORE_ROOT / "agentos_runtime"
    limits = {
        kernel / "contextual_policy_calibration.py": 200,
        kernel / "contextual_policy_calibration_gate.py": 40,
        kernel / "contextual_policy_selector.py": 350,
        runtime / "contextual_policy_assignment.py": 80,
        runtime / "contextual_policy_calibration_source.py": 130,
        runtime / "contextual_policy_runtime.py": 180,
    }
    counts = {path.name: nonblank(path) for path in limits}
    assert all(counts[path.name] <= limit for path, limit in limits.items()), counts
    for path in (
        kernel / "contextual_policy_calibration.py",
        kernel / "contextual_policy_calibration_gate.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "agentos_runtime" not in text
        assert "pathlib" not in text
