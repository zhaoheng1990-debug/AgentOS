"""Freeze the v0.9 two-axis corpus and admission contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_two_axis_calibration import FROZEN_GATES
from local_collective_cognition.clarification_two_axis_holdout import build_two_axis_holdout_artifact, validate_two_axis_holdout_artifact
from local_collective_cognition.provider_telemetry import hash_payload


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/clarification_two_axis_v0_9")
    args = parser.parse_args()
    output = resolve(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    corpus = build_two_axis_holdout_artifact()
    validate_two_axis_holdout_artifact(corpus)
    commitment = {
        "protocol_version": "clarification_two_axis_protocol_v0_9",
        "theory_baseline": "AgentOS local collective cognition v0.36.0",
        "corpus_hash": corpus["artifact_hash"],
        "oracle_hash": corpus["private_oracle"]["oracle_hash"],
        "surface_hashes": {key: value["surface_hash"] for key, value in corpus["public_surfaces"].items()},
        "frozen_gates": FROZEN_GATES,
        "admission_arm": "SHUFFLED_TWO_AXIS",
        "action_policy_evaluated": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    contract = {**commitment, "contract_hash": hash_payload(commitment)}
    (output / "private_two_axis_corpus.json").write_text(json.dumps(corpus, indent=2, sort_keys=True), encoding="utf-8")
    (output / "two_axis_contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"corpus_hash": corpus["artifact_hash"], "oracle_hash": corpus["private_oracle"]["oracle_hash"], "contract_hash": contract["contract_hash"], "surface_hashes": contract["surface_hashes"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
