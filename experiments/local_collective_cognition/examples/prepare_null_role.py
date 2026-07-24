"""Freeze v0.40 independent null-information-role composition."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.null_role_experiment import (  # noqa: E402
    build_null_role_preregistration,
)
from local_collective_cognition.null_role_holdout import (  # noqa: E402
    build_null_role_holdout,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def verify(value):
    commitment = {
        key: item for key, item in value.items()
        if key != "artifact_hash"
    }
    if value["artifact_hash"] != hash_payload(commitment):
        raise ValueError("source_hash_invalid")


def main():
    source = REPO_ROOT / "outputs" / "truth_value_v0_39"
    prior_stop = read(source / "truth_value_early_stop_analysis.json")
    closure = read(source / "closure.json")
    cost_analysis = read(source / "source_v0_38_analysis.json")
    for value in (prior_stop, closure, cost_analysis):
        verify(value)
    corpus = build_null_role_holdout()
    preregistration = build_null_role_preregistration(
        corpus=corpus,
        prior_stop=prior_stop,
        prior_closure=closure,
        cost_analysis=cost_analysis,
    )
    output = REPO_ROOT / "outputs" / "null_role_v0_40"
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("source_v0_39_early_stop.json", prior_stop),
        ("source_v0_39_closure.json", closure),
        ("source_v0_38_cost_analysis.json", cost_analysis),
        ("null_role_corpus_frozen.json", corpus),
        ("null_role_preregistration.json", preregistration),
    ):
        write(output / name, value)
    print(json.dumps({
        "corpus_hash": corpus["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "case_count": corpus["case_count"],
        "fixed_standard_calls": 48,
        "maximum_counterproposal_calls": 24,
        "maximum_separate_value_calls": 0,
        "soft_tokens": preregistration[
            "cost_policy"
        ]["soft_expected_total_tokens"],
        "hard_tokens": preregistration[
            "cost_policy"
        ]["hard_runaway_total_tokens"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())

