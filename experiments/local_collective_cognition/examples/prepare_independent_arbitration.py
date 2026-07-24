"""Freeze v0.36 independent counterproposal arbitration experiment."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.independent_arbitration_experiment import (  # noqa: E402
    build_independent_arbitration_preregistration,
)
from local_collective_cognition.independent_arbitration_holdout import (  # noqa: E402
    build_independent_arbitration_holdout,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


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
    source = REPO_ROOT / "outputs" / "runtime_diff_v0_35"
    analysis = read(source / "runtime_diff_analysis.json")
    closure = read(source / "closure.json")
    recovery = read(source / "checkpoint_recovery.json")
    for value in (analysis, closure, recovery):
        verify(value)
    corpus = build_independent_arbitration_holdout()
    preregistration = build_independent_arbitration_preregistration(
        corpus=corpus,
        prior_analysis=analysis,
        prior_closure=closure,
        prior_recovery=recovery,
    )
    output = REPO_ROOT / "outputs" / "independent_arbitration_v0_36"
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("source_v0_35_analysis.json", analysis),
        ("source_v0_35_closure.json", closure),
        ("source_v0_35_recovery.json", recovery),
        ("independent_arbitration_corpus_frozen.json", corpus),
        ("independent_arbitration_preregistration.json", preregistration),
    ):
        write(output / name, value)
    print(json.dumps({
        "corpus_hash": corpus["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "case_count": corpus["case_count"],
        "fixed_standard_calls": 48,
        "maximum_counterproposal_calls": 24,
        "maximum_arbiter_calls": 24,
        "soft_tokens": preregistration[
            "cost_policy"
        ]["soft_expected_total_tokens"],
        "hard_tokens": preregistration[
            "cost_policy"
        ]["hard_runaway_total_tokens"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
