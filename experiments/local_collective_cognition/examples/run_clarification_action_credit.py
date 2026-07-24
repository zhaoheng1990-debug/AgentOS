"""Run v0.7 calibration fingerprints or fresh validation actions."""
from __future__ import annotations
import argparse,json,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
PACK_ROOT=Path(__file__).resolve().parents[1];REPO_ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(REPO_ROOT/'agentos_core_slim_v0'),str(PACK_ROOT)]
from local_collective_cognition.bounded_retry_provider import BoundedRetryProviderAdapter
from local_collective_cognition.clarification_action_credit_contracts import FINGERPRINT_TASK_KIND
from local_collective_cognition.clarification_action_credit_runtime import ClarificationActionCreditRuntime,DIRECT_LANE,FINGERPRINT_LANE,validate_action_credit_run
from local_collective_cognition.clarification_regret_contracts import DIRECT_TASK_KIND
from local_collective_cognition.openai_compatible_provider import OpenAICompatibleJsonAdapter,OpenAICompatibleProviderSpec
def resolve(p):p=Path(p);return p if p.is_absolute() else REPO_ROOT/p
def ds(pid,kind):return BoundedRetryProviderAdapter(OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(pid,'deepseek-v4-flash','https://api.deepseek.com/chat/completions','DEEPSEEK_API_KEY',(kind,),max_tokens=2200,timeout_seconds=240,extra_body={'thinking':{'type':'disabled'},'temperature':0})),max_attempts=2)
def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=('CALIBRATION','VALIDATION'),required=True);p.add_argument('--corpus');p.add_argument('--ledger');p.add_argument('--output');a=p.parse_args();base='outputs/clarification_action_credit_v0_7';corpus_path=a.corpus or ('outputs/clarification_regret_v0_6/private_clarification_regret_corpus.json' if a.mode=='CALIBRATION' else f'{base}/private_validation_corpus.json');output=a.output or f"{base}/{'calibration_fingerprint_run.json' if a.mode=='CALIBRATION' else 'validation_run.json'}";corpus=json.loads(resolve(corpus_path).read_text(encoding='utf-8'));ledger=json.loads(resolve(a.ledger or f'{base}/action_credit_ledger.json').read_text(encoding='utf-8')) if a.mode=='VALIDATION' else None
 adapters={FINGERPRINT_LANE:ds('deepseek-action-credit-fingerprint-'+a.mode.lower(),FINGERPRINT_TASK_KIND)}
 if a.mode=='VALIDATION':adapters[DIRECT_LANE]=ds('deepseek-action-credit-direct-validation',DIRECT_TASK_KIND)
 run=ClarificationActionCreditRuntime(corpus_artifact=corpus).evaluate(experiment_id='action-credit-'+a.mode.lower()+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),mode=a.mode,adapters=adapters,ledger=ledger);validate_action_credit_run(run,corpus_artifact=corpus,expected_mode=a.mode,ledger=ledger);resolve(output).write_text(json.dumps(run,indent=2,sort_keys=True),encoding='utf-8')
 summary={'candidate_run_hash':run['candidate_run_hash'],'calls':run['total_unique_provider_calls'],'tokens':run['total_unique_input_tokens']+run['total_unique_output_tokens'],'failures':{k:len(v['failures']) for k,v in run['lanes'].items()},'fingerprints':dict(Counter(x['fingerprint'] for x in run['proposals']))}
 if a.mode=='VALIDATION':summary['actions']={'DIRECT':dict(Counter(x['direct_policy_action'] for x in run['records'])),'LEDGER':dict(Counter(x['ledger_policy_action'] for x in run['records']))}
 print(json.dumps(summary,indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
