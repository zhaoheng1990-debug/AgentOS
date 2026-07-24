"""Freeze v0.7 calibration-history and fresh-validation bindings."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
PACK_ROOT=Path(__file__).resolve().parents[1];REPO_ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(REPO_ROOT/'agentos_core_slim_v0'),str(PACK_ROOT)]
from local_collective_cognition.clarification_action_credit_calibration import FROZEN_GATES
from local_collective_cognition.clarification_action_credit_holdout import build_action_credit_validation_artifact,validate_action_credit_validation_artifact
from local_collective_cognition.clarification_regret_holdout import validate_clarification_regret_artifact
from local_collective_cognition.provider_telemetry import hash_payload
def resolve(p):p=Path(p);return p if p.is_absolute() else REPO_ROOT/p
def main():
 p=argparse.ArgumentParser();p.add_argument('--calibration-corpus',default='outputs/clarification_regret_v0_6/private_clarification_regret_corpus.json');p.add_argument('--output-dir',default='outputs/clarification_action_credit_v0_7');a=p.parse_args();out=resolve(a.output_dir);out.mkdir(parents=True,exist_ok=True)
 calibration=json.loads(resolve(a.calibration_corpus).read_text(encoding='utf-8'));validate_clarification_regret_artifact(calibration);validation=build_action_credit_validation_artifact();validate_action_credit_validation_artifact(validation)
 commitment={'protocol_version':'clarification_action_credit_protocol_v0_7','methodology_kernel':'v1.1','theory_baseline':'AgentOS local collective cognition v0.34.0','calibration_corpus_hash':calibration['artifact_hash'],'validation_corpus_hash':validation['artifact_hash'],'validation_oracle_hash':validation['private_oracle']['oracle_hash'],'frozen_gates':FROZEN_GATES,'validation_outcomes_available_to_ledger':False,'selection_authority':False,'retention_authority':False,'production_authority':False};contract={**commitment,'contract_hash':hash_payload(commitment)}
 (out/'private_validation_corpus.json').write_text(json.dumps(validation,indent=2,sort_keys=True),encoding='utf-8');(out/'action_credit_contract.json').write_text(json.dumps(contract,indent=2,sort_keys=True),encoding='utf-8');print(json.dumps({'calibration_corpus_hash':calibration['artifact_hash'],'validation_corpus_hash':validation['artifact_hash'],'oracle_hash':validation['private_oracle']['oracle_hash'],'contract_hash':contract['contract_hash']},indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
