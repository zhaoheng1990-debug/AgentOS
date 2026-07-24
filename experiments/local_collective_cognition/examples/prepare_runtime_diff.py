"""Freeze v0.35 Runtime-derived candidate diff experiment."""
from __future__ import annotations
import json,sys
from pathlib import Path
PACK_ROOT=Path(__file__).resolve().parents[1];REPO_ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(REPO_ROOT/"agentos_core_slim_v0"),str(PACK_ROOT)]
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.runtime_diff_experiment import build_runtime_diff_preregistration  # noqa: E402
from local_collective_cognition.runtime_diff_holdout import build_runtime_diff_holdout  # noqa: E402
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write(p,v): Path(p).write_text(json.dumps(v,indent=2,sort_keys=True),encoding="utf-8")
def verify(v):
    if v["artifact_hash"]!=hash_payload({k:x for k,x in v.items() if k!="artifact_hash"}): raise ValueError("source_hash_invalid")
def main():
    src=REPO_ROOT/"outputs"/"lineage_revision_v0_34"
    a=read(src/"lineage_revision_analysis.json");p=read(src/"posthoc_contract_failure_decomposition.json");l=read(src/"ledger.json");c=read(src/"closure.json")
    for v in (a,p,l,c): verify(v)
    if p["source_analysis_hash"]!=a["artifact_hash"] or l["source_analysis_hash"]!=a["artifact_hash"] or c["source_ledger_hash"]!=l["artifact_hash"]: raise ValueError("source_chain_invalid")
    corpus=build_runtime_diff_holdout();prereg=build_runtime_diff_preregistration(corpus=corpus,prior_analysis=a,prior_closure=c,prior_posthoc=p)
    out=REPO_ROOT/"outputs"/"runtime_diff_v0_35";out.mkdir(parents=True,exist_ok=True)
    for name,value in (("source_v0_34_analysis.json",a),("source_v0_34_posthoc.json",p),("source_v0_34_closure.json",c),("runtime_diff_corpus_frozen.json",corpus),("runtime_diff_preregistration.json",prereg)): write(out/name,value)
    print(json.dumps({"corpus_hash":corpus["artifact_hash"],"preregistration_hash":prereg["artifact_hash"],"case_count":corpus["case_count"],"fixed_standard_calls":48,"maximum_revision_calls":24,"soft_tokens":prereg["cost_policy"]["soft_expected_total_tokens"],"hard_tokens":prereg["cost_policy"]["hard_runaway_total_tokens"]},indent=2,sort_keys=True))
if __name__=="__main__": raise SystemExit(main())
