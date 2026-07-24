"""Freeze v0.34 lineage-aware revision experiment."""
from __future__ import annotations
import json, sys
from pathlib import Path
PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]
from local_collective_cognition.lineage_revision_experiment import build_lineage_revision_preregistration  # noqa: E402
from local_collective_cognition.lineage_revision_holdout import build_lineage_revision_holdout  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write(p,v): Path(p).write_text(json.dumps(v,indent=2,sort_keys=True),encoding="utf-8")
def verify(v):
    if v["artifact_hash"] != hash_payload({k:x for k,x in v.items() if k!="artifact_hash"}): raise ValueError("source_hash_invalid")
def main():
    src=REPO_ROOT/"outputs"/"runtime_escalation_v0_33"
    a=read(src/"runtime_escalation_analysis.json")
    p=read(src/"posthoc_worker_uplift.json")
    l=read(src/"ledger.json"); c=read(src/"closure.json")
    for value in (a,p,l,c): verify(value)
    if p["source_analysis_hash"]!=a["artifact_hash"] or l["source_analysis_hash"]!=a["artifact_hash"] or c["source_ledger_hash"]!=l["artifact_hash"]: raise ValueError("source_chain_invalid")
    corpus=build_lineage_revision_holdout()
    prereg=build_lineage_revision_preregistration(corpus=corpus,prior_analysis=a,prior_closure=c,prior_posthoc=p)
    out=REPO_ROOT/"outputs"/"lineage_revision_v0_34";out.mkdir(parents=True,exist_ok=True)
    for name,value in (("source_v0_33_analysis.json",a),("source_v0_33_posthoc.json",p),("source_v0_33_closure.json",c),("lineage_revision_corpus_frozen.json",corpus),("lineage_revision_preregistration.json",prereg)): write(out/name,value)
    print(json.dumps({"corpus_hash":corpus["artifact_hash"],"preregistration_hash":prereg["artifact_hash"],"case_count":corpus["case_count"],"fixed_standard_calls":48,"maximum_revision_calls":24,"soft_tokens":prereg["cost_policy"]["soft_expected_total_tokens"],"hard_tokens":prereg["cost_policy"]["hard_runaway_total_tokens"]},indent=2,sort_keys=True))
if __name__=="__main__": raise SystemExit(main())
