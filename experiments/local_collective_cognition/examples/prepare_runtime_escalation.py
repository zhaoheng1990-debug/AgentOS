"""Freeze v0.33 zero-token Runtime escalation experiment."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.provider_telemetry import (  # noqa: E402
    hash_payload,
)
from local_collective_cognition.runtime_escalation_experiment import (  # noqa: E402
    build_runtime_escalation_preregistration,
)
from local_collective_cognition.runtime_escalation_holdout import (  # noqa: E402
    build_runtime_escalation_holdout,
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
        key: item for key, item in value.items()
        if key != "artifact_hash"
    }
    if value["artifact_hash"] != hash_payload(commitment):
        raise ValueError("source_hash_invalid")


def main():
    source = REPO_ROOT / "outputs" / "lazy_metacognition_v0_32"
    analysis = read(source / "lazy_metacognition_analysis.json")
    posthoc = read(source / "posthoc_cost_quality_decomposition.json")
    ledger = read(source / "ledger.json")
    closure = read(source / "closure.json")
    for value in (analysis, posthoc, ledger, closure):
        verify(value)
    if (
        posthoc["source_analysis_hash"] != analysis["artifact_hash"]
        or ledger["source_analysis_hash"] != analysis["artifact_hash"]
        or closure["source_ledger_hash"] != ledger["artifact_hash"]
    ):
        raise ValueError("source_chain_invalid")
    corpus = build_runtime_escalation_holdout()
    preregistration = build_runtime_escalation_preregistration(
        corpus=corpus,
        prior_analysis=analysis,
        prior_closure=closure,
        prior_posthoc=posthoc,
    )
    output = REPO_ROOT / "outputs" / "runtime_escalation_v0_33"
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("source_v0_32_analysis.json", analysis),
        ("source_v0_32_posthoc.json", posthoc),
        ("source_v0_32_closure.json", closure),
        ("runtime_escalation_corpus_frozen.json", corpus),
        ("runtime_escalation_preregistration.json", preregistration),
    ):
        write(output / name, value)
    print(json.dumps({
        "corpus_hash": corpus["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "case_count": corpus["case_count"],
        "fixed_standard_call_count": corpus["case_count"] * 3 * 2,
        "maximum_worker_call_count": corpus["case_count"] * 3,
        "soft_tokens": preregistration[
            "cost_policy"
        ]["soft_expected_total_tokens"],
        "hard_tokens": preregistration[
            "cost_policy"
        ]["hard_runaway_total_tokens"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
