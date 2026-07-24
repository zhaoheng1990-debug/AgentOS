"""Freeze v0.32 receipt-native lazy metacognition experiment."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.lazy_metacognition_experiment import (  # noqa: E402
    build_lazy_metacognition_preregistration,
)
from local_collective_cognition.lazy_metacognition_holdout import (  # noqa: E402
    build_lazy_metacognition_holdout,
)
from local_collective_cognition.provider_telemetry import (  # noqa: E402
    hash_payload,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def verify(value):
    commitment = {
        key: item
        for key, item in value.items()
        if key != "artifact_hash"
    }
    if value["artifact_hash"] != hash_payload(commitment):
        raise ValueError("source_hash_invalid")


def main():
    source = REPO_ROOT / "outputs" / "comparative_plan_intent_v0_31"
    analysis = read(source / "comparative_plan_intent_analysis.json")
    ledger = read(source / "ledger.json")
    closure = read(source / "closure.json")
    for value in (analysis, ledger, closure):
        verify(value)
    if (
        ledger["source_analysis_hash"] != analysis["artifact_hash"]
        or closure["source_ledger_hash"] != ledger["artifact_hash"]
    ):
        raise ValueError("source_chain_invalid")
    corpus = build_lazy_metacognition_holdout()
    preregistration = build_lazy_metacognition_preregistration(
        corpus=corpus,
        prior_analysis=analysis,
        prior_closure=closure,
    )
    output = REPO_ROOT / "outputs" / "lazy_metacognition_v0_32"
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("source_v0_31_analysis.json", analysis),
        ("source_v0_31_closure.json", closure),
        ("lazy_metacognition_corpus_frozen.json", corpus),
        ("lazy_metacognition_preregistration.json", preregistration),
    ):
        write(output / name, value)
    print(json.dumps({
        "corpus_hash": corpus["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "case_count": corpus["case_count"],
        "fixed_base_call_count": corpus["case_count"] * 3 * 2,
        "maximum_specialized_call_count": corpus["case_count"] * 3,
        "soft_tokens": preregistration[
            "cost_policy"
        ]["soft_expected_total_tokens"],
        "hard_tokens": preregistration[
            "cost_policy"
        ]["hard_runaway_total_tokens"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
