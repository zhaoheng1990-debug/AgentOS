"""Freeze v0.56 corpus and prior artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.effect_witness_holdout import (  # noqa: E402
    build_effect_witness_holdout,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    v54 = REPO_ROOT / "outputs" / "evidence_first_v0_54"
    v55 = REPO_ROOT / "outputs" / "relation_stability_audit_v0_55"
    output = REPO_ROOT / "outputs" / "effect_witness_v0_56"
    output.mkdir(parents=True, exist_ok=True)
    sources = (
        ("source_v0_54_preregistration.json", v54 / "evidence_first_preregistration.json"),
        ("source_v0_54_analysis.json", v54 / "evidence_first_analysis.json"),
        ("source_v0_54_closure.json", v54 / "closure.json"),
        ("source_v0_54_posthoc.json", v54 / "posthoc_evidence_first.json"),
        ("source_v0_55_closure.json", v55 / "closure.json"),
        ("source_dual_axis_gate_candidate.json", v55 / "dual_axis_gate_candidate.json"),
    )
    for name, path in sources:
        write(output / name, read(path))
    corpus = build_effect_witness_holdout()
    write(output / "effect_witness_corpus_frozen.json", corpus)
    print(json.dumps({
        "corpus_hash": corpus["artifact_hash"],
        "case_count": corpus["case_count"],
        "formal_run_authorized": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
