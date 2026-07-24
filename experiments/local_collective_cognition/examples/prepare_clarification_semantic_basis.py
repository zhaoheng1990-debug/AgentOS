"""Freeze the v0.11 semantic-basis corpus and diagnostic contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_semantic_basis_calibration import FROZEN_DIAGNOSTIC_THRESHOLDS
from local_collective_cognition.clarification_semantic_basis_holdout import build_semantic_basis_holdout_artifact, validate_semantic_basis_holdout_artifact
from local_collective_cognition.provider_telemetry import hash_payload


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/clarification_semantic_basis_v0_11")
    args = parser.parse_args()
    output = resolve(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    corpus = build_semantic_basis_holdout_artifact()
    validate_semantic_basis_holdout_artifact(corpus)
    commitment = {
        "protocol_version": "clarification_semantic_basis_protocol_v0_11",
        "theory_baseline": "AgentOS local collective cognition v0.39.0",
        "corpus_hash": corpus["artifact_hash"],
        "oracle_hash": corpus["private_oracle"]["oracle_hash"],
        "surface_hash": corpus["public_surface"]["surface_hash"],
        "frozen_diagnostic_thresholds": FROZEN_DIAGNOSTIC_THRESHOLDS,
        "construction_labels_are_pre_panel_diagnostics_only": True,
        "required_final_reference": "GPT-5.6_GEMINI-3.1_KIMI-K3_MODEL_PANEL",
        "action_policy_evaluated": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    contract = {**commitment, "contract_hash": hash_payload(commitment)}
    (output / "private_semantic_basis_corpus.json").write_text(json.dumps(corpus, indent=2, sort_keys=True), encoding="utf-8")
    (output / "semantic_basis_contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"corpus_hash": corpus["artifact_hash"], "oracle_hash": corpus["private_oracle"]["oracle_hash"], "contract_hash": contract["contract_hash"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
