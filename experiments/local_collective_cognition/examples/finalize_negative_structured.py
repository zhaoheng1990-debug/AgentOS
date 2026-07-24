"""Finalize the v0.4 panel and score frozen replication/defer arms."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from zipfile import ZipFile
PACK_ROOT=Path(__file__).resolve().parents[1];REPO_ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(REPO_ROOT/'agentos_core_slim_v0'),str(PACK_ROOT)]
from local_collective_cognition.negative_evidence_structured_calibration import build_structured_calibration,validate_structured_calibration
from local_collective_cognition.negative_evidence_structured_holdout import validate_structured_corpus_artifact
from local_collective_cognition.negative_evidence_structured_runtime import validate_structured_candidate_run
from local_collective_cognition.structure_reference_panel_final import build_reference_candidate,validate_reference_candidate
def resolve(p):p=Path(p);return p if p.is_absolute() else REPO_ROOT/p
def load(p):return json.loads(resolve(p).read_text(encoding='utf-8'))
def bundle(path,panel,pack_hash):
 matches=[]
 with ZipFile(path) as z:
  for i in z.infolist():
   if i.is_dir() or not i.filename.lower().endswith('.json'):continue
   x=json.loads(z.read(i).decode('utf-8-sig'))
   if x.get('panel_id')==panel and x.get('adjudication_pack_hash')==pack_hash and {'blinding_attestation','decisions'}.issubset(x):matches.append(x)
 if len(matches)!=1:raise ValueError('negative_structured_k3_bundle_invalid')
 return matches[0]
def main():
 p=argparse.ArgumentParser();base='outputs/negative_evidence_structured_v0_4';p.add_argument('--corpus',default=f'{base}/private_negative_structured_corpus.json');p.add_argument('--candidate-run',default=f'{base}/candidate_run.json');p.add_argument('--gpt-pack',default=f'{base}/gpt_5_6_negative_structured_pack.json');p.add_argument('--gemini-pack',default=f'{base}/gemini_3_1_negative_structured_pack.json');p.add_argument('--panel-manifest',default=f'{base}/private_panel_manifest.json');p.add_argument('--gpt-response',default=f'{base}/gpt_5_6_negative_structured_response.json');p.add_argument('--gemini-response',default=f'{base}/gemini_3_1_negative_structured_response.json');p.add_argument('--adjudication-pack',default=f'{base}/kimi_k3_negative_structured_adjudication_pack.json');p.add_argument('--adjudication-manifest',default=f'{base}/private_adjudication_manifest.json');g=p.add_mutually_exclusive_group(required=True);g.add_argument('--k3-response');g.add_argument('--k3-bundle');p.add_argument('--k3-output',default=f'{base}/kimi_k3_negative_structured_response.json');p.add_argument('--reference-output',default=f'{base}/model_panel_reference_candidate.json');p.add_argument('--calibration-output',default=f'{base}/structured_calibration.json');a=p.parse_args()
 corpus=load(a.corpus);run=load(a.candidate_run);validate_structured_corpus_artifact(corpus);validate_structured_candidate_run(run,corpus_artifact=corpus);packs=(load(a.gpt_pack),load(a.gemini_pack));pm=load(a.panel_manifest);responses=(load(a.gpt_response),load(a.gemini_response));ap=load(a.adjudication_pack);am=load(a.adjudication_manifest);k3=bundle(resolve(a.k3_bundle),ap['panel_id'],ap['pack_hash']) if a.k3_bundle else load(a.k3_response)
 ref=build_reference_candidate(adjudication_pack=ap,adjudication_manifest=am,panel_packs=packs,panel_manifest=pm,annotation_responses=responses,response=k3);validate_reference_candidate(ref,adjudication_pack=ap,adjudication_manifest=am,panel_packs=packs,panel_manifest=pm,annotation_responses=responses,response=k3);cal=build_structured_calibration(corpus_artifact=corpus,candidate_run=run,reference_artifact=ref);validate_structured_calibration(cal,corpus_artifact=corpus,candidate_run=run,reference_artifact=ref)
 resolve(a.k3_output).write_text(json.dumps(k3,indent=2,sort_keys=True),encoding='utf-8');resolve(a.reference_output).write_text(json.dumps(ref,indent=2,sort_keys=True),encoding='utf-8');resolve(a.calibration_output).write_text(json.dumps(cal,indent=2,sort_keys=True),encoding='utf-8');print(json.dumps({'reference_artifact_hash':ref['artifact_hash'],'calibration_artifact_hash':cal['artifact_hash'],'candidate_state':cal['candidate_state'],'arm_metrics':cal['arm_metrics'],'naive_gate_results':cal['naive_gate_results'],'structured_gate_results':cal['structured_gate_results']},indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
