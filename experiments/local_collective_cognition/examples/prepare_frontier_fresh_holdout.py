"""Freeze the v0.27 fresh holdout after a passed neutral preflight."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.frontier_experiment import (  # noqa: E402
    build_frontier_preregistration,
)
from local_collective_cognition.frontier_fresh_holdout import (  # noqa: E402
    build_frontier_fresh_holdout,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    preflight = (
        REPO_ROOT / "outputs" / "frontier_preflight_v0_27"
    )
    analysis = read(preflight / "preflight_analysis.json")
    closure = read(preflight / "closure.json")
    if (
        closure.get("source_analysis_hash") != analysis["artifact_hash"]
        or closure.get("fresh_holdout_authorized") is not True
    ):
        raise ValueError("frontier_preflight_closure_invalid")
    corpus = build_frontier_fresh_holdout()
    preregistration = build_frontier_preregistration(
        corpus=corpus, preflight_analysis=analysis
    )
    output = REPO_ROOT / "outputs" / "frontier_fresh_v0_27"
    output.mkdir(parents=True, exist_ok=True)
    write(output / "source_preflight_analysis.json", analysis)
    write(output / "frontier_corpus_frozen.json", corpus)
    write(output / "frontier_preregistration.json", preregistration)
    print(json.dumps({
        "preflight_analysis_hash": analysis["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "case_count": corpus["case_count"],
        "domain_count": corpus["domain_count"],
        "maximum_total_tokens": preregistration[
            "success_gate"
        ]["maximum_total_tokens"],
        "reference_state": corpus["reference_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
