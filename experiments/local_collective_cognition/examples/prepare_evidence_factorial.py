"""Freeze the v0.20 factorial preregistration and fresh holdout."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_evidence_factorial import (  # noqa: E402
    build_factorial_preregistration,
)
from local_collective_cognition.cognitive_action_evidence_factorial_holdout import (  # noqa: E402
    build_factorial_holdout,
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
            REPO_ROOT / "outputs" / "evidence_factorial_calibration_v0_20"
        ),
    )
    parser.add_argument(
        "--source",
        default=str(
            REPO_ROOT
            / "outputs"
            / "evidence_state_calibration_v0_19"
            / "external_panel"
            / "evidence_external_evaluation.json"
        ),
    )
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    preregistration = build_factorial_preregistration(
        source_evaluation=read(args.source)
    )
    corpus = build_factorial_holdout()
    write(output / "evidence_factorial_preregistration.json", preregistration)
    write(output / "evidence_factorial_corpus_frozen.json", corpus)
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
