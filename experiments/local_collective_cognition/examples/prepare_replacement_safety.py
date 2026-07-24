"""Freeze v0.43 replacement-safety validation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.replacement_safety_experiment import (  # noqa: E402
    build_replacement_safety_preregistration,
)
from local_collective_cognition.replacement_safety_holdout import (  # noqa: E402
    build_replacement_safety_holdout,
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
    source = REPO_ROOT / "outputs" / "compact_delta_v0_42"
    analysis = read(source / "compact_delta_analysis.json")
    closure = read(source / "closure.json")
    posthoc = read(source / "posthoc_compact_delta_calibration.json")
    for value in (analysis, closure, posthoc):
        verify(value)
    corpus = build_replacement_safety_holdout()
    preregistration = build_replacement_safety_preregistration(
        corpus=corpus,
        prior_analysis=analysis,
        prior_closure=closure,
        prior_posthoc=posthoc,
    )
    output = REPO_ROOT / "outputs" / "replacement_safety_v0_43"
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("source_v0_42_analysis.json", analysis),
        ("source_v0_42_closure.json", closure),
        ("source_v0_42_posthoc.json", posthoc),
        ("replacement_safety_corpus_frozen.json", corpus),
        ("replacement_safety_preregistration.json", preregistration),
    ):
        write(output / name, value)
    print(json.dumps({
        "corpus_hash": corpus["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "case_count": corpus["case_count"],
        "fixed_standard_calls": 48,
        "maximum_single_delta_calls": 24,
        "replacement_gate_provider_calls": 0,
        "soft_tokens": preregistration[
            "cost_policy"
        ]["soft_expected_total_tokens"],
        "hard_tokens": preregistration[
            "cost_policy"
        ]["hard_runaway_total_tokens"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
