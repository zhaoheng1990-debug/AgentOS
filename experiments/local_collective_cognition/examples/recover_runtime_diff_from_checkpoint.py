"""Recover v0.35 run metadata from its final immutable checkpoint."""
from __future__ import annotations
import json,sys
from pathlib import Path
PACK_ROOT=Path(__file__).resolve().parents[1];REPO_ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(REPO_ROOT/"agentos_core_slim_v0"),str(PACK_ROOT)]
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.runtime_candidate_diff import DIFF_VERSION  # noqa: E402
from local_collective_cognition.runtime_diff_experiment import RUNTIME_VERSION,analyze_runtime_diff_experiment  # noqa: E402
from local_collective_cognition.runtime_escalation_policy import POLICY_VERSION  # noqa: E402
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write(p,v): Path(p).write_text(json.dumps(v,indent=2,sort_keys=True),encoding="utf-8")
def main():
    out=REPO_ROOT/"outputs"/"runtime_diff_v0_35";corpus=read(out/"runtime_diff_corpus_frozen.json");prereg=read(out/"runtime_diff_preregistration.json");progress=read(out/"runtime_diff_progress.json")
    if progress["artifact_hash"]!=hash_payload({k:v for k,v in progress.items() if k!="artifact_hash"}): raise ValueError("progress_hash_invalid")
    commitment={"runtime_version":RUNTIME_VERSION,"source_corpus_hash":corpus["artifact_hash"],"source_preregistration_hash":prereg["artifact_hash"],"source_trigger_policy_version":POLICY_VERSION,"source_candidate_diff_version":DIFF_VERSION,"provider_id":"deepseek-runtime-diff-v0-35","model_id":"deepseek-v4-flash","task_calls":progress["task_calls"],"raw_receipts":progress["raw_receipts"],"provisional_projections":progress["provisional_projections"],"final_projections":progress["final_projections"],"trigger_receipts":progress["trigger_receipts"],"revision_receipts":progress["revision_receipts"],"failures":progress["failures"],"raw_receipts_preserved_before_projection":True,"private_truth_exposed":False,"provider_declared_action_used":False,"provider_declared_route_used":False,"trigger_policy_retuned_from_v0_33":False,"selection_authority":False,"retention_authority":False,"production_authority":False}
    run={**commitment,"run_hash":hash_payload(commitment)};a=analyze_runtime_diff_experiment(corpus=corpus,preregistration=prereg,run=run);write(out/"runtime_diff_run.json",run);write(out/"runtime_diff_analysis.json",a)
    recovery_c={"recovery_version":"runtime_diff_checkpoint_recovery_v0_35","source_progress_hash":progress["artifact_hash"],"recovered_run_hash":run["run_hash"],"recovered_analysis_hash":a["artifact_hash"],"completed_task_count":progress["completed_task_count"],"provider_calls_replayed":False,"provider_evidence_changed":False}
    write(out/"checkpoint_recovery.json",{**recovery_c,"artifact_hash":hash_payload(recovery_c)})
    print(json.dumps({"recovered_from_checkpoint":True,"completed_task_count":progress["completed_task_count"],"run_hash":run["run_hash"],"decision":a["decision"],"state":a["candidate_state"]},indent=2,sort_keys=True))
if __name__=="__main__": raise SystemExit(main())
