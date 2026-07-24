"""Close and package v0.34 lineage-aware revision."""
from __future__ import annotations
import hashlib,json,sys,zipfile
from collections import Counter
from pathlib import Path
PACK_ROOT=Path(__file__).resolve().parents[1]
REPO_ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(REPO_ROOT/"agentos_core_slim_v0"),str(PACK_ROOT)]
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write(p,v): Path(p).write_text(json.dumps(v,indent=2,sort_keys=True),encoding="utf-8")
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest()
def zpack(path,files):
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        for source in sorted(files,key=lambda x:x.name):
            i=zipfile.ZipInfo(source.name);i.date_time=(1980,1,1,0,0,0);i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,source.read_bytes())
def main():
    out=REPO_ROOT/"outputs"/"lineage_revision_v0_34"
    prior=read(out/"source_v0_33_analysis.json");post0=read(out/"source_v0_33_posthoc.json");close0=read(out/"source_v0_33_closure.json")
    corpus=read(out/"lineage_revision_corpus_frozen.json");prereg=read(out/"lineage_revision_preregistration.json");run=read(out/"lineage_revision_run.json");a=read(out/"lineage_revision_analysis.json")
    failed=sorted(k for k,v in a["conditions"].items() if not v)
    d_c={"diagnostic_version":"lineage_revision_diagnostics_v0_34","source_run_hash":run["run_hash"],"source_analysis_hash":a["artifact_hash"],"raw_receipt_count":len(run["raw_receipts"]),"trigger_receipt_count":len(run["trigger_receipts"]),"revision_receipt_count":len(run["revision_receipts"]),"failures":run["failures"],"runtime_metrics":a["runtime_metrics"],"revision_metrics":a["revision_metrics"],"pooled_metrics":a["pooled_contrast_metrics"],"failed_conditions":failed,"external_panel_present":False,"core_integration_authorized":False}
    d={**d_c,"artifact_hash":hash_payload(d_c)};write(out/"lineage_revision_diagnostics.json",d)
    declared=Counter()
    for key,raw in run["raw_receipts"].items():
        if ":LINEAGE_REVISION_WORKER:" not in key: continue
        for action in raw.get("revision_actions",[]): declared[action.get("action","MISSING")]+=1
    reasons=Counter()
    for failure in run["failures"]:
        if failure.get("stage")!="LINEAGE_CONTRACT": continue
        for reason in failure.get("failures",[]): reasons[reason.split(":",1)[0]]+=1
    post_c={"posthoc_version":"lineage_revision_contract_failure_posthoc_v0_34","source_run_hash":run["run_hash"],"source_analysis_hash":a["artifact_hash"],"status":"POSTHOC_DECOMPOSITION_NOT_FROZEN_GATE","provider_completed_revision_count":sum(v["stage"]=="LINEAGE_REVISION_WORKER" and v["status"]=="COMPLETED" for v in run["task_calls"]),"lineage_valid_revision_count":len(run["revision_receipts"]),"lineage_invalid_revision_count":sum(v.get("stage")=="LINEAGE_CONTRACT" for v in run["failures"]),"declared_action_distribution":dict(declared),"contract_failure_reason_counts":dict(reasons),"frozen_decision_changed":False,"selection_authority":False,"retention_authority":False,"production_authority":False}
    post={**post_c,"artifact_hash":hash_payload(post_c)};write(out/"posthoc_contract_failure_decomposition.json",post)
    m=a["pooled_contrast_metrics"];r=a["revision_metrics"];g=r["triggered_gross_candidate_uplift"];n=r["triggered_net_uplift"]
    report="\n".join(["# Lineage-aware revision v0.34","","## Observed facts",f"- Revision-minus-A1 mean/median: {m['mean']:.3f}/{m['median']:.3f}; wins {m['win_count']}/{m['count']}.",f"- Majority-positive case rate: {a['majority_positive_case_rate']:.3f}.",f"- Trigger rate: {r['trigger_rate']:.3f} ({r['trigger_count']} cells).",f"- Valid/invalid lineage revisions: {post['lineage_valid_revision_count']}/{post['lineage_invalid_revision_count']}.",f"- Declared actions across all worker receipts: {json.dumps(post['declared_action_distribution'],sort_keys=True)}.",f"- Contract failures: {json.dumps(post['contract_failure_reason_counts'],sort_keys=True)}.",f"- Admitted revision actions: {json.dumps(r['revision_action_distribution'],sort_keys=True)}; KEEP rate {r['keep_action_rate']:.3f}.",("- Gross revision mean/median: "+(f"{g['mean']:.3f}/{g['median']:.3f}." if g else "not observed.")),("- Net revision mean/median: "+(f"{n['mean']:.3f}/{n['median']:.3f}." if n else "not observed.")),f"- Mean worker token penalty: {r['mean_worker_token_penalty']:.3f} Cbit.",f"- Prompt/lineage coverage: {a['runtime_metrics']['prompt_identity_coverage']:.3f}/{a['runtime_metrics']['lineage_contract_coverage']:.3f}.",f"- Total tokens: {a['physical_total_tokens']}.","- Failed frozen conditions: "+(", ".join(failed) if failed else "none")+".","","## Interpretation","- Trigger policy is unchanged from v0.33; only the worker interaction contract changed.","- KEEP, REVISE, and REPLACE are mechanically checked against the original candidate slot and relation.","- Provider completion is not counted as collaboration success when action semantics or route binding fail.","- All outcomes remain synthetic, external, candidate-only, and unable to write CoreSlim, retention, baseline, selection, or production state.","",f"Decision: `{a['decision']}`.",f"Candidate state: `{a['candidate_state']}`."])
    (out/"experiment_report.md").write_text(report,encoding="utf-8")
    l_c={"ledger_version":"lineage_revision_ledger_v0_34","source_prior_analysis_hash":prior["artifact_hash"],"source_prior_posthoc_hash":post0["artifact_hash"],"source_prior_closure_hash":close0["artifact_hash"],"source_corpus_hash":corpus["artifact_hash"],"source_preregistration_hash":prereg["artifact_hash"],"source_run_hash":run["run_hash"],"source_analysis_hash":a["artifact_hash"],"decision":a["decision"],"candidate_state":a["candidate_state"],"external_semantic_panel_authorized":a["external_semantic_panel_authorized"],"core_integration_authorized":False,"retention_authority":False,"production_authority":False}
    ledger={**l_c,"artifact_hash":hash_payload(l_c)};write(out/"ledger.json",ledger)
    rp_c={"replay_version":"lineage_revision_replay_v0_34","working_directory":str(PACK_ROOT),"commands":["python examples/prepare_lineage_revision.py","python examples/run_lineage_revision.py","python examples/finalize_lineage_revision.py"],"provider_model":run["model_id"],"frozen_corpus_hash":corpus["artifact_hash"],"warning":"Replay creates new Provider evidence."}
    replay={**rp_c,"artifact_hash":hash_payload(rp_c)};write(out/"replay.json",replay)
    rb_c={"rollback_version":"lineage_revision_rollback_v0_34","isolated_output_directory":str(out),"rollback_action":"Remove only this isolated output directory.","agentos_core_files_touched":False,"retention_or_baseline_mutation_performed":False}
    rollback={**rb_c,"artifact_hash":hash_payload(rb_c)};write(out/"rollback_pointer.json",rollback)
    c_c={"closure_version":"lineage_revision_closure_v0_34","source_ledger_hash":ledger["artifact_hash"],"candidate_state":a["candidate_state"],"decision":a["decision"],"lineage_revision_gate":a["lineage_revision_gate"],"external_semantic_panel_authorized":a["external_semantic_panel_authorized"],"core_integration_authorized":False,"promotion_allowed":False}
    closure={**c_c,"artifact_hash":hash_payload(c_c)};write(out/"closure.json",closure)
    names=["source_v0_33_analysis.json","source_v0_33_posthoc.json","source_v0_33_closure.json","lineage_revision_corpus_frozen.json","lineage_revision_preregistration.json","lineage_revision_progress.json","lineage_revision_run.json","lineage_revision_analysis.json","lineage_revision_diagnostics.json","posthoc_contract_failure_decomposition.json","experiment_report.md","ledger.json","replay.json","rollback_pointer.json","closure.json"]
    i_c={"inventory_version":"lineage_revision_inventory_v0_34","files":[{"path":name,"bytes":(out/name).stat().st_size,"sha256":sha(out/name)} for name in names]}
    inv={**i_c,"artifact_hash":hash_payload(i_c)};write(out/"hash_inventory.json",inv)
    pack=out/"lineage_revision_v0_34_return_pack.zip";zpack(pack,[out/name for name in names+["hash_inventory.json"]])
    m_c={"manifest_version":"lineage_revision_manifest_v0_34","return_pack":pack.name,"return_pack_sha256":sha(pack),"return_pack_bytes":pack.stat().st_size,"inventory_hash":inv["artifact_hash"],"closure_hash":closure["artifact_hash"]}
    manifest={**m_c,"artifact_hash":hash_payload(m_c)};write(out/"manifest.json",manifest)
    print(json.dumps({"decision":a["decision"],"state":a["candidate_state"],"return_pack":str(pack),"sha256":manifest["return_pack_sha256"]},indent=2,sort_keys=True))
if __name__=="__main__": raise SystemExit(main())
