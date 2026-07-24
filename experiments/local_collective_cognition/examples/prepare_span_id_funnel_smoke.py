"""Freeze the v0.25 immutable span-ID funnel structural smoke."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_span_id_funnel import (  # noqa: E402
    build_span_id_funnel_preregistration,
)
from local_collective_cognition.cognitive_action_span_id_funnel_holdout import (  # noqa: E402
    build_span_id_funnel_holdout,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    output = REPO_ROOT / "outputs" / "span_id_funnel_v0_25"
    output.mkdir(parents=True, exist_ok=True)
    source = read(
        REPO_ROOT
        / "outputs"
        / "candidate_blind_funnel_v0_24"
        / "closure.json"
    )
    preregistration = build_span_id_funnel_preregistration(
        source_closure=source
    )
    corpus = build_span_id_funnel_holdout()
    write(output / "span_id_funnel_preregistration.json", preregistration)
    write(output / "span_id_funnel_corpus_frozen.json", corpus)
    print(json.dumps({
        "preregistration_hash": preregistration["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "case_count": corpus["case_count"],
        "family_counts": corpus["family_counts"],
        "source_status_counts": corpus["source_status_counts"],
        "reference_state": corpus["reference_state"],
        "claim_ceiling": preregistration["claim_ceiling"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
