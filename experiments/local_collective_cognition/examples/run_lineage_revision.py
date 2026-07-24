"""Run v0.34 lineage-aware revision experiment."""
from __future__ import annotations
import json, sys
from pathlib import Path
PACK_ROOT=Path(__file__).resolve().parents[1]
REPO_ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(REPO_ROOT/"agentos_core_slim_v0"),str(PACK_ROOT)]
from local_collective_cognition.bounded_retry_provider import BoundedRetryProviderAdapter  # noqa: E402
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.lineage_revision_experiment import analyze_lineage_revision_experiment,run_lineage_revision_experiment  # noqa: E402
from local_collective_cognition.openai_compatible_provider import OpenAICompatibleJsonAdapter,OpenAICompatibleProviderSpec  # noqa: E402
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write(p,v): Path(p).write_text(json.dumps(v,indent=2,sort_keys=True),encoding="utf-8")
def main():
    out=REPO_ROOT/"outputs"/"lineage_revision_v0_34"
    corpus=read(out/"lineage_revision_corpus_frozen.json");prereg=read(out/"lineage_revision_preregistration.json")
    adapter=BoundedRetryProviderAdapter(OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(provider_id="deepseek-lineage-revision-v0-34",model_id="deepseek-v4-flash",endpoint="https://api.deepseek.com/chat/completions",api_key_env="DEEPSEEK_API_KEY",task_kinds=(TASK_KIND,),max_tokens=3600,timeout_seconds=300,extra_body={"thinking":{"type":"disabled"},"temperature":0})),max_attempts=2,delay_seconds=1.0)
    run=run_lineage_revision_experiment(corpus=corpus,preregistration=prereg,adapter=adapter,checkpoint_callback=lambda value:write(out/"lineage_revision_progress.json",value))
    a=analyze_lineage_revision_experiment(corpus=corpus,preregistration=prereg,run=run)
    write(out/"lineage_revision_run.json",run);write(out/"lineage_revision_analysis.json",a)
    print(json.dumps({"decision":a["decision"],"state":a["candidate_state"],"metrics":a["pooled_contrast_metrics"],"revision":a["revision_metrics"],"runtime":a["runtime_metrics"],"conditions":a["conditions"],"tokens":a["physical_total_tokens"]},indent=2,sort_keys=True))
if __name__=="__main__": raise SystemExit(main())
