"""Build a frozen action-credit ledger from v0.6 calibration outcomes."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
PACK_ROOT=Path(__file__).resolve().parents[1];REPO_ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(REPO_ROOT/'agentos_core_slim_v0'),str(PACK_ROOT)]
from local_collective_cognition.clarification_action_credit_ledger import build_action_credit_ledger,validate_action_credit_ledger
def resolve(p):p=Path(p);return p if p.is_absolute() else REPO_ROOT/p
def main():
 p=argparse.ArgumentParser();base='outputs/clarification_action_credit_v0_7';p.add_argument('--corpus',default='outputs/clarification_regret_v0_6/private_clarification_regret_corpus.json');p.add_argument('--run',default=f'{base}/calibration_fingerprint_run.json');p.add_argument('--output',default=f'{base}/action_credit_ledger.json');a=p.parse_args();corpus=json.loads(resolve(a.corpus).read_text(encoding='utf-8'));run=json.loads(resolve(a.run).read_text(encoding='utf-8'));ledger=build_action_credit_ledger(calibration_corpus=corpus,calibration_run=run);validate_action_credit_ledger(ledger,calibration_corpus=corpus,calibration_run=run);resolve(a.output).write_text(json.dumps(ledger,indent=2,sort_keys=True),encoding='utf-8');print(json.dumps({'ledger_hash':ledger['ledger_hash'],'records':ledger['records']},indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
