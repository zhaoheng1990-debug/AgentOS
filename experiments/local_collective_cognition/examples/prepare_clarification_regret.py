"""Freeze the v0.6 formal clarification-regret pilot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_regret_calibration import CALIBRATION_VERSION, FROZEN_GATES
from local_collective_cognition.clarification_regret_fusion import ARM_LANES
from local_collective_cognition.clarification_regret_holdout import build_clarification_regret_artifact, validate_clarification_regret_artifact
from local_collective_cognition.clarification_regret_runtime import RUNTIME_VERSION
from local_collective_cognition.provider_telemetry import hash_payload


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/clarification_regret_v0_6")
    args = parser.parse_args()
    output_dir = resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    corpus = build_clarification_regret_artifact()
    validate_clarification_regret_artifact(corpus)
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "methodology_kernel": "v1.1",
        "theory_baseline": "AgentOS local collective cognition v0.33.0",
        "object_before_proxy": corpus["corpus_spec"]["ontology_object"],
        "corpus_artifact_hash": corpus["artifact_hash"],
        "corpus_spec_hash": corpus["corpus_spec"]["spec_hash"],
        "private_oracle_hash": corpus["private_oracle"]["oracle_hash"],
        "frozen_gates": FROZEN_GATES,
        "arm_lanes": {key: list(value) for key, value in ARM_LANES.items()},
        "oracle_available_at_prediction_time": False,
        "post_outcome_adaptation_allowed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    contract = {**commitment, "contract_hash": hash_payload(commitment)}
    (output_dir / "private_clarification_regret_corpus.json").write_text(json.dumps(corpus, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "clarification_regret_contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"corpus_artifact_hash": corpus["artifact_hash"], "oracle_hash": corpus["private_oracle"]["oracle_hash"], "contract_hash": contract["contract_hash"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
