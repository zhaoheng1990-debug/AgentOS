"""Freeze the v0.19 preregistration and fresh holdout."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_evidence_calibrator import build_evidence_preregistration  # noqa: E402
from local_collective_cognition.cognitive_action_evidence_holdout import build_evidence_holdout  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "outputs" / "evidence_state_calibration_v0_19"))
    parser.add_argument("--source", default=str(REPO_ROOT / "outputs" / "selective_escalation_v0_18" / "external_panel" / "selective_external_evaluation.json"))
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    prereg = build_evidence_preregistration(source_evaluation=read(args.source))
    corpus = build_evidence_holdout()
    write(output / "evidence_preregistration.json", prereg)
    write(output / "evidence_fresh_corpus_frozen.json", corpus)
    print(json.dumps({
        "preregistration_hash": prereg["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "case_count": corpus["case_count"],
        "design_stratum_counts": corpus["design_stratum_counts"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
