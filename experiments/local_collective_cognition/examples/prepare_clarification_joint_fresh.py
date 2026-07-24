"""Freeze the v0.13 fresh joint coordinator corpus."""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path
PACK_ROOT=Path(__file__).resolve().parents[1]; REPO_ROOT=Path(__file__).resolve().parents[3]; sys.path[:0]=[str(REPO_ROOT/'agentos_core_slim_v0'),str(PACK_ROOT)]
from local_collective_cognition.clarification_joint_fresh_eval import FROZEN_THRESHOLDS
from local_collective_cognition.clarification_joint_holdout import build_joint_holdout_artifact, validate_joint_holdout_artifact
from local_collective_cognition.provider_telemetry import hash_payload
def resolve(path):
    path=Path(path); return path if path.is_absolute() else REPO_ROOT/path
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output-dir',default='outputs/clarification_joint_fresh_v0_13'); args=parser.parse_args(); output=resolve(args.output_dir); output.mkdir(parents=True,exist_ok=True)
    corpus=build_joint_holdout_artifact(); validate_joint_holdout_artifact(corpus)
    commitment={"protocol_version":"clarification_joint_fresh_protocol_v0_13","theory_baseline":"AgentOS local collective cognition v0.41.0","corpus_hash":corpus["artifact_hash"],"surface_hash":corpus["public_surface"]["surface_hash"],"oracle_hash":corpus["private_oracle"]["oracle_hash"],"frozen_thresholds":FROZEN_THRESHOLDS,"construction_labels_are_pre_panel_diagnostics_only":True,"action_credit_authority":False,"selection_authority":False,"retention_authority":False,"production_authority":False}
    contract={**commitment,"contract_hash":hash_payload(commitment)}
    (output/'private_joint_corpus.json').write_text(json.dumps(corpus,indent=2,sort_keys=True),encoding='utf-8'); (output/'joint_contract.json').write_text(json.dumps(contract,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps({"corpus_hash":corpus["artifact_hash"],"contract_hash":contract["contract_hash"]},indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
