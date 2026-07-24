"""Freeze the v0.51 corpus before reference completeness audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.reference_complete_portfolio_holdout import (  # noqa: E402
    build_reference_complete_portfolio_holdout,
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
    source = REPO_ROOT / "outputs" / "portfolio_displacement_v0_50"
    analysis = read(source / "portfolio_displacement_analysis.json")
    closure = read(source / "closure.json")
    posthoc = read(source / "posthoc_portfolio_displacement.json")
    for value in (analysis, closure, posthoc):
        verify(value)
    corpus = build_reference_complete_portfolio_holdout()
    output = REPO_ROOT / "outputs" / "reference_complete_portfolio_v0_51"
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("source_v0_50_analysis.json", analysis),
        ("source_v0_50_closure.json", closure),
        ("source_v0_50_posthoc.json", posthoc),
        ("reference_complete_portfolio_corpus_frozen.json", corpus),
    ):
        write(output / name, value)
    print(json.dumps({
        "corpus_hash": corpus["artifact_hash"],
        "case_count": corpus["case_count"],
        "reference_relations_per_case": 5,
        "audit_roles": 2,
        "required_audit_calls": 16,
        "formal_run_authorized": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
