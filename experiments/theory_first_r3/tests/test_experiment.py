import hashlib
import json

from theory_first_r3.experiment import run_experiment


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_full_preregistered_gate_set_passes() -> None:
    result = run_experiment()
    assert result["status"] == "PASS"
    assert result["gate_count"] == 12
    assert result["gate_pass_count"] == result["gate_count"]
    assert result["provider_calls"] == 0
    assert result["fresh_holdout_consumed"] is False
    assert result["runtime_imported"] is False


def test_experiment_is_deterministic() -> None:
    assert digest(run_experiment()) == digest(run_experiment())
