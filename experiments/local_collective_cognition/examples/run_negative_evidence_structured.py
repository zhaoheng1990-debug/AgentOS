"""Run frozen pre-reference v0.4 arms."""
from __future__ import annotations
import argparse,json,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
PACK_ROOT=Path(__file__).resolve().parents[1]; REPO_ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(REPO_ROOT/'agentos_core_slim_v0'),str(PACK_ROOT)]
from local_collective_cognition.bounded_retry_provider import BoundedRetryProviderAdapter
from local_collective_cognition.negative_evidence_audit_contracts import FABRICATION_AUDIT,LIVE_AMBIGUITY_AUDIT,TASK_KINDS
from local_collective_cognition.negative_evidence_structured_contracts import STRUCTURED_LIVE_TASK_KIND
from local_collective_cognition.negative_evidence_structured_fusion import BASELINE,FABRICATION,LEGACY_LIVE,MONOLITHIC_REPEAT_2,MONOLITHIC_REPEAT_3,STRUCTURED_LIVE
from local_collective_cognition.negative_evidence_structured_holdout import validate_structured_corpus_artifact
from local_collective_cognition.negative_evidence_structured_runtime import NegativeEvidenceStructuredRuntime,validate_structured_candidate_run
from local_collective_cognition.openai_compatible_provider import OpenAICompatibleJsonAdapter,OpenAICompatibleProviderSpec
from local_collective_cognition.structure_semantic_judge_contracts import JUDGE_TASK_KIND
def resolve(p): p=Path(p); return p if p.is_absolute() else REPO_ROOT/p
def ds(pid,kind,tokens): return BoundedRetryProviderAdapter(OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(pid,'deepseek-v4-flash','https://api.deepseek.com/chat/completions','DEEPSEEK_API_KEY',(kind,),max_tokens=tokens,timeout_seconds=240,extra_body={'thinking':{'type':'disabled'},'temperature':0})),max_attempts=2)
def main():
 p=argparse.ArgumentParser(); base='outputs/negative_evidence_structured_v0_4'; p.add_argument('--corpus',default=f'{base}/private_negative_structured_corpus.json'); p.add_argument('--output',default=f'{base}/candidate_run.json'); a=p.parse_args(); corpus=json.loads(resolve(a.corpus).read_text()); validate_structured_corpus_artifact(corpus)
 adapters={BASELINE:ds('deepseek-structured-baseline',JUDGE_TASK_KIND,2600),MONOLITHIC_REPEAT_2:ds('deepseek-structured-mono-r2',JUDGE_TASK_KIND,2600),MONOLITHIC_REPEAT_3:ds('deepseek-structured-mono-r3',JUDGE_TASK_KIND,2600),LEGACY_LIVE:ds('deepseek-structured-legacy-live',TASK_KINDS[LIVE_AMBIGUITY_AUDIT],1800),STRUCTURED_LIVE:ds('deepseek-structured-semantic-live',STRUCTURED_LIVE_TASK_KIND,2000),FABRICATION:ds('deepseek-structured-fabrication',TASK_KINDS[FABRICATION_AUDIT],1800)}
 run=NegativeEvidenceStructuredRuntime(corpus_artifact=corpus).evaluate(experiment_id='negative-structured-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),adapters=adapters); validate_structured_candidate_run(run,corpus_artifact=corpus); out=resolve(a.output); out.write_text(json.dumps(run,indent=2,sort_keys=True),encoding='utf-8'); records=run['fusion']['records']; keys={'SINGLE':'single_monolithic_state','BUDGET':'budget_matched_monolithic_state','NAIVE':'naive_replication_state','STRUCTURED':'structured_defer_state'}
 print(json.dumps({'candidate_run_hash':run['candidate_run_hash'],'calls':run['total_unique_provider_calls'],'tokens':run['total_unique_input_tokens']+run['total_unique_output_tokens'],'successes':{k:len(v['judgments']) for k,v in run['lanes'].items()},'failures':{k:len(v['failures']) for k,v in run['lanes'].items()},'states':{k:dict(Counter(x[v] for x in records)) for k,v in keys.items()},'accounting':run['fusion']['arm_accounting']},indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
