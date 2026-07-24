"""Build the candidate-only role topology from the clean ambiguity holdout."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.ambiguity_discovery_eval import validate_discovery_artifact  # noqa: E402
from local_collective_cognition.ambiguity_role_complementarity import (  # noqa: E402
    build_role_complementarity_candidate, validate_role_complementarity_candidate,
)


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load(path):
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", default="outputs/unstated_ambiguity_holdout_v0_4.json")
    parser.add_argument("--calibration", default="outputs/structure_elicitor_calibration_v0_2.json")
    parser.add_argument("--judge-calibration", default="outputs/structure_reference_judge_calibration_v0_1.json")
    parser.add_argument("--output", default="outputs/ambiguity_role_complementarity_v0_1.json")
    args = parser.parse_args()
    holdout, calibration, judge = _load(args.holdout), _load(args.calibration), _load(args.judge_calibration)
    validate_discovery_artifact(
        holdout, calibration_artifact=calibration, judge_calibration_artifact=judge,
    )
    artifact = build_role_complementarity_candidate(
        holdout_artifact=holdout, judge_calibration_artifact=judge,
    )
    validate_role_complementarity_candidate(
        artifact, holdout_artifact=holdout, judge_calibration_artifact=judge,
    )
    output = _resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "candidate_state": artifact["candidate_state"],
        "role_candidates": artifact["role_candidates"],
        "naive_ensemble_simulations": artifact["naive_ensemble_simulations"],
        "artifact_hash": artifact["artifact_hash"], "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
