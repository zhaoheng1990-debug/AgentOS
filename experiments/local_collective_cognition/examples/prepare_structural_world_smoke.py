"""Freeze the v0.26 Science constraints and structure-first holdout."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.structural_world_constraints import (  # noqa: E402
    build_science_institutional_constraints,
)
from local_collective_cognition.structural_world_expansion import (  # noqa: E402
    build_structural_world_preregistration,
)
from local_collective_cognition.structural_world_holdout import (  # noqa: E402
    build_structural_world_holdout,
)


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    output = REPO_ROOT / "outputs" / "structural_world_v0_26"
    output.mkdir(parents=True, exist_ok=True)
    constraints = build_science_institutional_constraints()
    corpus = build_structural_world_holdout()
    preregistration = build_structural_world_preregistration(
        constraints=constraints, corpus=corpus
    )
    write(output / "science_constraints_frozen.json", constraints)
    write(output / "structural_world_corpus_frozen.json", corpus)
    write(output / "structural_world_preregistration.json", preregistration)
    print(json.dumps({
        "science_constraint_hash": constraints["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "case_count": corpus["case_count"],
        "domain_count": corpus["domain_count"],
        "reference_state": corpus["reference_state"],
        "claim_ceiling": preregistration["claim_ceiling"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
