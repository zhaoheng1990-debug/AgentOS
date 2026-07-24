"""Freeze the v0.51 preregistration after the reference audit passes."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.reference_complete_portfolio_experiment import (  # noqa: E402
    build_reference_complete_portfolio_preregistration,
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
    output = REPO_ROOT / "outputs" / "reference_complete_portfolio_v0_51"
    corpus = read(output / "reference_complete_portfolio_corpus_frozen.json")
    audit = read(output / "reference_completeness_audit.json")
    analysis = read(output / "source_v0_50_analysis.json")
    closure = read(output / "source_v0_50_closure.json")
    posthoc = read(output / "source_v0_50_posthoc.json")
    for value in (corpus, audit, analysis, closure, posthoc):
        verify(value)
    preregistration = build_reference_complete_portfolio_preregistration(
        corpus=corpus,
        reference_audit=audit,
        prior_analysis=analysis,
        prior_closure=closure,
        prior_posthoc=posthoc,
    )
    write(
        output / "reference_complete_portfolio_preregistration.json",
        preregistration,
    )
    print(json.dumps({
        "corpus_hash": corpus["artifact_hash"],
        "reference_audit_hash": audit["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "case_count": corpus["case_count"],
        "physical_standard_calls": 24,
        "derived_arm_standard_receipts": 48,
        "maximum_single_delta_calls": 24,
        "maximum_physical_tokens": preregistration[
            "success_gate"
        ]["maximum_physical_total_tokens"],
        "hard_tokens": preregistration[
            "cost_policy"
        ]["hard_runaway_total_tokens"],
        "formal_run_authorized": True,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
