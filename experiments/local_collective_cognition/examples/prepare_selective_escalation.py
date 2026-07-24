"""Freeze the v0.18 preregistration and fresh holdout."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_selective_holdout import build_selective_holdout  # noqa: E402
from local_collective_cognition.cognitive_action_selective_runtime import build_selective_preregistration  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "outputs" / "selective_escalation_v0_18"))
    parser.add_argument("--source-dir", default=str(REPO_ROOT / "outputs" / "axis_credibility_routing_v0_17" / "external_panel"))
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    source = read(Path(args.source_dir) / "axis_routing_external_evaluation.json")
    preregistration = build_selective_preregistration(source_evaluation=source)
    corpus = build_selective_holdout()
    write(output / "selective_preregistration.json", preregistration)
    write(output / "selective_fresh_corpus_frozen.json", corpus)
    print(json.dumps({
        "preregistration_hash": preregistration["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "case_count": corpus["case_count"],
        "design_stratum_counts": corpus["design_stratum_counts"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
