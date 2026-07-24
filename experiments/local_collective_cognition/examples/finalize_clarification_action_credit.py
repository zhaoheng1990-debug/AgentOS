"""Score fresh v0.7 validation without writing outcomes into the current ledger."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
PACK_ROOT=Path(__file__).resolve().parents[1];REPO_ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(REPO_ROOT/'agentos_core_slim_v0'),str(PACK_ROOT)]
from local_collective_cognition.clarification_action_credit_calibration import build_action_credit_calibration,validate_action_credit_calibration
def resolve(p):p=Path(p);return p if p.is_absolute() else REPO_ROOT/p
def load(p):return json.loads(resolve(p).read_text(encoding='utf-8'))
def main():
 p=argparse.ArgumentParser();base='outputs/clarification_action_credit_v0_7';p.add_argument('--calibration-corpus',default='outputs/clarification_regret_v0_6/private_clarification_regret_corpus.json');p.add_argument('--calibration-run',default=f'{base}/calibration_fingerprint_run.json');p.add_argument('--ledger',default=f'{base}/action_credit_ledger.json');p.add_argument('--validation-corpus',default=f'{base}/private_validation_corpus.json');p.add_argument('--validation-run',default=f'{base}/validation_run.json');p.add_argument('--output',default=f'{base}/calibration.json');a=p.parse_args();sources={'calibration_corpus':load(a.calibration_corpus),'calibration_run':load(a.calibration_run),'ledger':load(a.ledger),'validation_corpus':load(a.validation_corpus),'validation_run':load(a.validation_run)};artifact=build_action_credit_calibration(**sources);validate_action_credit_calibration(artifact,**sources);resolve(a.output).write_text(json.dumps(artifact,indent=2,sort_keys=True),encoding='utf-8');print(json.dumps({'artifact_hash':artifact['artifact_hash'],'candidate_state':artifact['candidate_state'],'arm_metrics':artifact['arm_metrics'],'gate_results':artifact['gate_results']},indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
