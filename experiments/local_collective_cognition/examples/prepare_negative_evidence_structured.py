"""Freeze v0.4 structured-defer protocol and blind annotation packs."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
PACK_ROOT=Path(__file__).resolve().parents[1]; REPO_ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(REPO_ROOT/'agentos_core_slim_v0'),str(PACK_ROOT)]
from local_collective_cognition.negative_evidence_structured_calibration import CALIBRATION_VERSION,FROZEN_GATES
from local_collective_cognition.negative_evidence_structured_fusion import ARM_LANES
from local_collective_cognition.negative_evidence_structured_holdout import build_structured_corpus_artifact,validate_structured_corpus_artifact
from local_collective_cognition.negative_evidence_structured_runtime import RUNTIME_VERSION
from local_collective_cognition.provider_telemetry import hash_payload
from local_collective_cognition.structure_reference_panel_pack import build_reference_panel,validate_reference_panel
def resolve(p): p=Path(p); return p if p.is_absolute() else REPO_ROOT/p
def write(p,x): p.write_text(json.dumps(x,indent=2,sort_keys=True),encoding='utf-8')
def main():
 p=argparse.ArgumentParser(); p.add_argument('--output-dir',default='outputs/negative_evidence_structured_v0_4'); a=p.parse_args(); out=resolve(a.output_dir); out.mkdir(parents=True,exist_ok=True)
 corpus=build_structured_corpus_artifact(); validate_structured_corpus_artifact(corpus); packs,manifest=build_reference_panel(semantic_artifact=corpus); validate_reference_panel(packs=packs,manifest=manifest,semantic_artifact=corpus)
 commitment={'calibration_version':CALIBRATION_VERSION,'runtime_version':RUNTIME_VERSION,'corpus_artifact_hash':corpus['artifact_hash'],'corpus_spec_hash':corpus['corpus_spec']['spec_hash'],'panel_id':manifest['panel_id'],'lane_pack_hashes':manifest['lane_pack_hashes'],'frozen_gates':FROZEN_GATES,'arm_lanes':{k:list(v) for k,v in ARM_LANES.items()},'current_reference_labels_available':False,'post_current_reference_adaptation_allowed':False,'construction_categories_are_ground_truth':False,'selection_authority':False,'retention_authority':False,'production_authority':False}; contract={**commitment,'contract_hash':hash_payload(commitment)}
 write(out/'private_negative_structured_corpus.json',corpus); names={'annotation-lane-a':'gpt_5_6_negative_structured_pack.json','annotation-lane-b':'gemini_3_1_negative_structured_pack.json'}
 for pack in packs:
  path=out/names[pack['lane_id']]; write(path,pack)
  with ZipFile(path.with_suffix('.zip'),'w',compression=ZIP_DEFLATED) as z:z.write(path,arcname=path.name)
 write(out/'private_panel_manifest.json',manifest); write(out/'structured_calibration_contract.json',contract)
 print(json.dumps({'corpus_artifact_hash':corpus['artifact_hash'],'panel_id':manifest['panel_id'],'pack_hashes':manifest['lane_pack_hashes'],'contract_hash':contract['contract_hash']},indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
