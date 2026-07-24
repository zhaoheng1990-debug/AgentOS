"""Close and package v0.31 comparative plan-intent experiment."""
from __future__ import annotations
import hashlib, json, sys, zipfile
from pathlib import Path
PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write(p, v): Path(p).write_text(json.dumps(v, indent=2, sort_keys=True), encoding="utf-8")
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest()
def zpack(path, files):
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        for source in sorted(files,key=lambda x:x.name):
            i=zipfile.ZipInfo(source.name);i.date_time=(1980,1,1,0,0,0);i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16
            z.writestr(i,source.read_bytes())
def main():
    out=REPO_ROOT/"outputs"/"comparative_plan_intent_v0_31"
    prior=read(out/"source_v0_30_analysis.json"); posthoc=read(out/"source_v0_30_posthoc.json"); closure0=read(out/"source_v0_30_closure.json")
    corpus=read(out/"comparative_plan_intent_corpus_frozen.json"); prereg=read(out/"comparative_plan_intent_preregistration.json")
    run=read(out/"comparative_plan_intent_run.json"); a=read(out/"comparative_plan_intent_analysis.json")
    failed=sorted(k for k,v in a["conditions"].items() if not v)
    diag_c={"diagnostic_version":"comparative_plan_intent_diagnostics_v0_31","source_run_hash":run["run_hash"],"source_analysis_hash":a["artifact_hash"],"raw_receipt_count":len(run["raw_receipts"]),"plan_receipt_count":len(run["plan_receipts"]),"failures":run["failures"],"runtime_metrics":a["runtime_metrics"],"plan_metrics":a["plan_metrics"],"pooled_metrics":a["pooled_contrast_metrics"],"failed_conditions":failed,"external_panel_present":False,"core_integration_authorized":False}
    diag={**diag_c,"artifact_hash":hash_payload(diag_c)};write(out/"comparative_plan_intent_diagnostics.json",diag)
    m=a["pooled_contrast_metrics"]; p=a["plan_metrics"]
    report="\n".join([
        "# Comparative plan intent v0.31","",
        "## Observed facts",
        f"- Plan-minus-A1 mean/median: {m['mean']:.3f}/{m['median']:.3f}; wins {m['win_count']}/{m['count']}.",
        f"- Majority-positive case rate: {a['majority_positive_case_rate']:.3f}.",
        f"- Plan consistency coverage: {a['runtime_metrics']['plan_consistency_coverage']:.3f}.",
        f"- Selected routes: {json.dumps(p['selected_route_distribution'], sort_keys=True)}.",
        f"- Execution modes: {json.dumps(p['execution_mode_distribution'], sort_keys=True)}.",
        f"- Total tokens: {a['total_tokens']}.",
        "- Failed frozen conditions: "+(", ".join(failed) if failed else "none")+".","",
        "## Interpretation",
        "- The plan-intent and candidates were generated in one Provider call; no separate router cost was hidden.",
        "- Four route utilities, anti-additive risks, no-escalation mode, and candidate-plan consistency were mechanically checked.",
        "- Synthetic outcomes remain candidate-only and do not authorize CoreSlim, retention, baseline, or production writes.","",
        f"Decision: `{a['decision']}`.",f"Candidate state: `{a['candidate_state']}`.",
    ])
    (out/"experiment_report.md").write_text(report,encoding="utf-8")
    led_c={"ledger_version":"comparative_plan_intent_ledger_v0_31","source_prior_analysis_hash":prior["artifact_hash"],"source_prior_posthoc_hash":posthoc["artifact_hash"],"source_prior_closure_hash":closure0["artifact_hash"],"source_corpus_hash":corpus["artifact_hash"],"source_preregistration_hash":prereg["artifact_hash"],"source_run_hash":run["run_hash"],"source_analysis_hash":a["artifact_hash"],"decision":a["decision"],"candidate_state":a["candidate_state"],"external_semantic_panel_authorized":a["external_semantic_panel_authorized"],"core_integration_authorized":False,"retention_authority":False,"production_authority":False}
    ledger={**led_c,"artifact_hash":hash_payload(led_c)};write(out/"ledger.json",ledger)
    replay_c={"replay_version":"comparative_plan_intent_replay_v0_31","working_directory":str(PACK_ROOT),"commands":["python examples/prepare_comparative_plan_intent.py","python examples/run_comparative_plan_intent.py","python examples/finalize_comparative_plan_intent.py"],"provider_model":run["model_id"],"frozen_corpus_hash":corpus["artifact_hash"],"warning":"Replay creates new Provider evidence."}
    replay={**replay_c,"artifact_hash":hash_payload(replay_c)};write(out/"replay.json",replay)
    roll_c={"rollback_version":"comparative_plan_intent_rollback_v0_31","isolated_output_directory":str(out),"rollback_action":"Remove only this isolated output directory.","agentos_core_files_touched":False,"retention_or_baseline_mutation_performed":False}
    roll={**roll_c,"artifact_hash":hash_payload(roll_c)};write(out/"rollback_pointer.json",roll)
    close_c={"closure_version":"comparative_plan_intent_closure_v0_31","source_ledger_hash":ledger["artifact_hash"],"candidate_state":a["candidate_state"],"decision":a["decision"],"plan_intent_gate":a["plan_intent_gate"],"external_semantic_panel_authorized":a["external_semantic_panel_authorized"],"core_integration_authorized":False,"promotion_allowed":False}
    closure={**close_c,"artifact_hash":hash_payload(close_c)};write(out/"closure.json",closure)
    names=["source_v0_30_analysis.json","source_v0_30_posthoc.json","source_v0_30_closure.json","comparative_plan_intent_corpus_frozen.json","comparative_plan_intent_preregistration.json","comparative_plan_intent_progress.json","comparative_plan_intent_run.json","comparative_plan_intent_analysis.json","comparative_plan_intent_diagnostics.json","experiment_report.md","ledger.json","replay.json","rollback_pointer.json","closure.json"]
    inv_c={"inventory_version":"comparative_plan_intent_inventory_v0_31","files":[{"path":n,"bytes":(out/n).stat().st_size,"sha256":sha(out/n)} for n in names]}
    inv={**inv_c,"artifact_hash":hash_payload(inv_c)};write(out/"hash_inventory.json",inv)
    pack=out/"comparative_plan_intent_v0_31_return_pack.zip";zpack(pack,[out/n for n in names+["hash_inventory.json"]])
    man_c={"manifest_version":"comparative_plan_intent_manifest_v0_31","return_pack":pack.name,"return_pack_sha256":sha(pack),"return_pack_bytes":pack.stat().st_size,"inventory_hash":inv["artifact_hash"],"closure_hash":closure["artifact_hash"]}
    man={**man_c,"artifact_hash":hash_payload(man_c)};write(out/"manifest.json",man)
    print(json.dumps({"decision":a["decision"],"state":a["candidate_state"],"return_pack":str(pack),"sha256":man["return_pack_sha256"]},indent=2))
if __name__=="__main__": raise SystemExit(main())
