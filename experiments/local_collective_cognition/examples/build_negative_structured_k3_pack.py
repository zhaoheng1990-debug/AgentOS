"""Build the identity-blind v0.4 K3 dispute pack."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from zipfile import ZIP_DEFLATED,ZipFile
PACK_ROOT=Path(__file__).resolve().parents[1];REPO_ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(REPO_ROOT/'agentos_core_slim_v0'),str(PACK_ROOT)]
from local_collective_cognition.negative_evidence_structured_holdout import validate_structured_corpus_artifact
from local_collective_cognition.structure_reference_panel_disagreement import build_adjudication_bundle,validate_adjudication_bundle
from local_collective_cognition.structure_reference_panel_pack import validate_reference_panel
def resolve(p):p=Path(p);return p if p.is_absolute() else REPO_ROOT/p
def load(p):return json.loads(resolve(p).read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True),encoding='utf-8')
def main():
 p=argparse.ArgumentParser();base='outputs/negative_evidence_structured_v0_4';p.add_argument('--corpus',default=f'{base}/private_negative_structured_corpus.json');p.add_argument('--gpt-pack',default=f'{base}/gpt_5_6_negative_structured_pack.json');p.add_argument('--gemini-pack',default=f'{base}/gemini_3_1_negative_structured_pack.json');p.add_argument('--panel-manifest',default=f'{base}/private_panel_manifest.json');p.add_argument('--gpt-response',required=True);p.add_argument('--gemini-response',required=True);p.add_argument('--output-dir',default=base);a=p.parse_args()
 corpus=load(a.corpus);validate_structured_corpus_artifact(corpus);packs=(load(a.gpt_pack),load(a.gemini_pack));manifest=load(a.panel_manifest);validate_reference_panel(packs=packs,manifest=manifest,semantic_artifact=corpus);responses=(load(a.gpt_response),load(a.gemini_response));pack,private=build_adjudication_bundle(packs=packs,panel_manifest=manifest,responses=responses);validate_adjudication_bundle(pack=pack,manifest=private,panel_packs=packs,panel_manifest=manifest,responses=responses);out=resolve(a.output_dir)
 write(out/'gpt_5_6_negative_structured_response.json',responses[0]);write(out/'gemini_3_1_negative_structured_response.json',responses[1]);path=out/'kimi_k3_negative_structured_adjudication_pack.json';write(path,pack)
 with ZipFile(path.with_suffix('.zip'),'w',compression=ZIP_DEFLATED) as z:z.write(path,arcname=path.name)
 write(out/'private_adjudication_manifest.json',private);print(json.dumps({'agreement_count':private['agreement_count'],'disagreement_count':private['disagreement_count'],'reference_state':private['reference_state'],'pack_hash':pack['pack_hash']},indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
