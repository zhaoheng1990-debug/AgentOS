"""Freeze the v0.21 source-ontology preregistration and fresh holdout."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_source_ontology import (  # noqa: E402
    build_source_ontology_preregistration,
)
from local_collective_cognition.cognitive_action_source_ontology_holdout import (  # noqa: E402
    build_source_ontology_holdout,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default=str(
            REPO_ROOT / "outputs" / "source_ontology_ablation_v0_21"
        ),
    )
    parser.add_argument(
        "--source",
        default=str(
            REPO_ROOT
            / "outputs"
            / "evidence_factorial_calibration_v0_20"
            / "external_panel"
            / "evidence_factorial_external_evaluation.json"
        ),
    )
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    preregistration = build_source_ontology_preregistration(
        source_evaluation=read(args.source)
    )
    corpus = build_source_ontology_holdout()
    write(
        output / "source_ontology_preregistration.json",
        preregistration,
    )
    write(output / "source_ontology_corpus_frozen.json", corpus)
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
