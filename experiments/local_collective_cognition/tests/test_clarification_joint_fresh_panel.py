from copy import deepcopy
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[3]; PACK=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'agentos_core_slim_v0'),str(PACK)]
from local_collective_cognition.clarification_joint_fresh_panel import build_joint_fresh_adjudication, build_joint_fresh_panel, build_joint_fresh_reference, validate_joint_fresh_adjudication, validate_joint_fresh_panel, validate_joint_fresh_reference  # noqa: E402
from local_collective_cognition.clarification_joint_holdout import build_joint_holdout_artifact  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
def test_joint_fresh_panel_is_deterministic_and_withholds_coordination_priors():
    corpus=build_joint_holdout_artifact(); packs,manifest=build_joint_fresh_panel(corpus_artifact=corpus); validate_joint_fresh_panel(packs=packs,manifest=manifest,corpus_artifact=corpus)
    assert manifest['candidate_count']==24 and manifest['criterion_count']==4
    for pack in packs:
        assert pack['locked_consensus_axes']=='WITHHELD' and pack['local_basis_outcome']=='WITHHELD' and pack['deepseek_outputs']=='WITHHELD'
        assert all(set(item)=={'annotation_id','public_prompt','candidate_a','candidate_b'} for item in pack['items'])
def test_joint_fresh_panel_rejects_pack_tamper():
    packs,manifest=build_joint_fresh_panel(corpus_artifact=build_joint_holdout_artifact()); tampered=deepcopy(packs[0]); tampered['items'][0]['candidate_a']='tampered'; tampered['pack_hash']=hash_payload({key:value for key,value in tampered.items() if key!='pack_hash'})
    with pytest.raises(ValueError,match='pack_binding_invalid'): validate_joint_fresh_panel(packs=(tampered,packs[1]),manifest=manifest)


def test_joint_fresh_panel_reduces_only_disagreement_cells_for_k3():
    packs,manifest=build_joint_fresh_panel(corpus_artifact=build_joint_holdout_artifact()); responses=[]
    for pack in packs:
        labels=[]
        for item in pack['items']:
            criteria={'SELECTED_OBJECT':'NONE','SELECTION_BASIS':'NO_PREFERENCE','PRAGMATIC_PREFERENCE':'NONE','AXIS_ASSESSMENT_COMPLETE':'COMPLETE'}
            labels.append({'annotation_id':item['annotation_id'],'criteria':criteria,'criterion_notes':{key:'Fixture note.' for key in criteria},'criterion_confidence':{key:0.8 for key in criteria}})
        if pack['lane_id']=='annotation-lane-b': labels[0]['criteria']['SELECTION_BASIS']='PRAGMATIC_DEFAULT'
        responses.append({'panel_version':pack['panel_version'],'panel_id':pack['panel_id'],'lane_id':pack['lane_id'],'pack_hash':pack['pack_hash'],'annotator_provider':pack['expected_annotator']['provider'],'annotator_model':pack['expected_annotator']['model'],'annotation_session_ref':'fixture-'+pack['lane_id'],'labels':labels})
    k3_pack,k3_manifest=build_joint_fresh_adjudication(packs=packs,panel_manifest=manifest,responses=responses); validate_joint_fresh_adjudication(pack=k3_pack,manifest=k3_manifest,panel_packs=packs,panel_manifest=manifest,responses=responses)
    assert k3_manifest['agreement_count']==95 and k3_manifest['disagreement_count']==1
    assert k3_pack['locked_consensus_axes']=='WITHHELD' and k3_pack['local_basis_outcome']=='WITHHELD'
    item=k3_pack['items'][0];position=item['positions'][0]
    response={'panel_version':k3_pack['panel_version'],'panel_id':k3_pack['panel_id'],'adjudication_pack_hash':k3_pack['pack_hash'],'adjudicator_provider':'Moonshot','adjudicator_model':'Kimi-K3','adjudication_session_ref':'fixture','blinding_attestation':{'pack_only_context':True,'annotator_identity_unavailable':True,'source_identity_unavailable':True,'construction_labels_unavailable':True,'locked_consensus_axes_unavailable':True,'local_basis_outcome_unavailable':True,'deepseek_outputs_unavailable':True,'prior_scores_unavailable':True,'external_pairing_not_used':True},'decisions':[{'adjudication_id':item['adjudication_id'],'selected_state':position['state'],'decision_basis':position['position_id'],'confidence':0.8,'rationale':'Fixture.'}]}
    reference=build_joint_fresh_reference(adjudication_pack=k3_pack,adjudication_manifest=k3_manifest,response=response);validate_joint_fresh_reference(reference,adjudication_pack=k3_pack,adjudication_manifest=k3_manifest,response=response)
    assert reference['label_count']==96
