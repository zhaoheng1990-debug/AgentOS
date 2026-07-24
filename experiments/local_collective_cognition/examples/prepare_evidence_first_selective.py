"""Freeze the v0.22 evidence-first preregistration and holdout."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_evidence_first import (  # noqa: E402
    build_evidence_first_preregistration,
)
from local_collective_cognition.cognitive_action_evidence_first_holdout import (  # noqa: E402
    build_evidence_first_holdout,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    output = REPO_ROOT / "outputs" / "evidence_first_selective_v0_22"
    output.mkdir(parents=True, exist_ok=True)
    source = read(
        REPO_ROOT
        / "outputs"
        / "source_ontology_ablation_v0_21"
        / "external_panel"
        / "source_ontology_external_evaluation.json"
    )
    preregistration = build_evidence_first_preregistration(
        source_evaluation=source
    )
    corpus = build_evidence_first_holdout()
    write(output / "evidence_first_preregistration.json", preregistration)
    write(output / "evidence_first_corpus_frozen.json", corpus)
    print(json.dumps({
        "preregistration_hash": preregistration["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "case_count": corpus["case_count"],
        "family_counts": corpus["family_counts"],
        "design_stratum_counts": corpus["design_stratum_counts"],
        "reference_state": corpus["reference_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
