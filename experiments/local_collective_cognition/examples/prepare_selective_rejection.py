"""Freeze the v0.52 corpus and v0.51 source artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.selective_rejection_holdout import (  # noqa: E402
    build_selective_rejection_holdout,
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
    source = REPO_ROOT / "outputs" / "reference_complete_portfolio_v0_51"
    preregistration = read(
        source / "reference_complete_portfolio_preregistration.json"
    )
    analysis = read(source / "reference_complete_portfolio_analysis.json")
    closure = read(source / "closure.json")
    posthoc = read(source / "posthoc_reference_complete_portfolio.json")
    for value in (preregistration, analysis, closure, posthoc):
        verify(value)
    corpus = build_selective_rejection_holdout()
    output = REPO_ROOT / "outputs" / "selective_rejection_v0_52"
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("source_v0_51_preregistration.json", preregistration),
        ("source_v0_51_analysis.json", analysis),
        ("source_v0_51_closure.json", closure),
        ("source_v0_51_posthoc.json", posthoc),
        ("selective_rejection_corpus_frozen.json", corpus),
    ):
        write(output / name, value)
    print(json.dumps({
        "corpus_hash": corpus["artifact_hash"],
        "case_count": corpus["case_count"],
        "relation_state_positions_rotated": corpus[
            "relation_state_positions_rotated_across_cases"
        ],
        "required_audit_calls": 16,
        "formal_run_authorized": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
