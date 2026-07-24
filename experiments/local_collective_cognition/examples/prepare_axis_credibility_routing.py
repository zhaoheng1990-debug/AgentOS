"""Freeze the v0.17 preregistration, fresh holdout, and local-role plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_axis_holdout import build_axis_routing_holdout  # noqa: E402
from local_collective_cognition.cognitive_action_axis_routing import build_axis_role_plan, build_axis_routing_preregistration  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "outputs" / "axis_credibility_routing_v0_17"))
    parser.add_argument("--source-dir", default=str(REPO_ROOT / "outputs" / "cognitive_action_overnight_v0_16"))
    args = parser.parse_args()
    output = Path(args.output_dir)
    source = Path(args.source_dir)
    output.mkdir(parents=True, exist_ok=True)
    source_evaluation = read(source / "external_panel" / "cognitive_action_external_evaluation.json")
    calibration = read(source / "staged_semantic_analysis.json")
    preregistration = build_axis_routing_preregistration(source_evaluation=source_evaluation)
    corpus = build_axis_routing_holdout()
    plan = build_axis_role_plan(corpus=corpus, preregistration=preregistration, calibration_analysis=calibration)
    write(output / "axis_routing_preregistration.json", preregistration)
    write(output / "axis_fresh_corpus_frozen.json", corpus)
    write(output / "axis_role_plan.json", plan)
    print(json.dumps({
        "preregistration_hash": preregistration["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "plan_hash": plan["plan_hash"],
        "case_count": corpus["case_count"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())

