from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[3];PACK=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'agentos_core_slim_v0'),str(PACK)]
from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.clarification_action_credit_calibration import build_action_credit_calibration,validate_action_credit_calibration  # noqa: E402
from local_collective_cognition.clarification_action_credit_contracts import FINGERPRINT_TASK_KIND  # noqa: E402
from local_collective_cognition.clarification_action_credit_holdout import build_action_credit_validation_artifact,validate_action_credit_validation_artifact  # noqa: E402
from local_collective_cognition.clarification_action_credit_ledger import build_action_credit_ledger,validate_action_credit_ledger  # noqa: E402
from local_collective_cognition.clarification_action_credit_runtime import ClarificationActionCreditRuntime,DIRECT_LANE,FINGERPRINT_LANE,validate_action_credit_run  # noqa: E402
from local_collective_cognition.clarification_regret_contracts import DIRECT_TASK_KIND  # noqa: E402
from local_collective_cognition.clarification_regret_holdout import build_clarification_regret_artifact  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


FP={"OPEN":"OPEN_RIVALS","EXPLICIT":"PROMPT_FIXED","EQUIVALENT":"EQUIVALENT_RIVALS","FABRICATED":"UNSUPPORTED_RIVAL"}


class FixtureAdapter:
 def __init__(self,lane,oracle):
  self.lane=lane;self.oracle=oracle;kind=FINGERPRINT_TASK_KIND if lane==FINGERPRINT_LANE else DIRECT_TASK_KIND
  self.profile=ProviderCapabilityProfile(provider_id='fixture-'+lane.lower(),model_id='fixture',task_kinds=(kind,),max_timeout_seconds=180)
 def invoke(self,task):
  assert task.inputs['private_intent_oracle']=='WITHHELD_AND_INACCESSIBLE';items=[]
  for case in task.inputs['public_cases']:
   bid=case['blind_case_id'];binding=self.oracle[bid]
   if self.lane==DIRECT_LANE:items.append({'blind_case_id':bid,'action':'ASK','evidence_basis':'Fixture.','confidence':0.8})
   else:
    preferred='ANSWER_A' if binding['category']=='OPEN' else binding['valid_direct_actions'][0]
    items.append({'blind_case_id':bid,'fingerprint':FP[binding['category']],'preferred_direct_answer':preferred,'evidence_basis':'Fixture fingerprint.','counterfactual':'Changed wording changes the relation.'})
  return {'result':{'batch_id':task.expected_schema['properties']['batch_id']['enum'][0],'assessments':items,'evidence_refs':list(task.allowed_evidence)},'usage':{'input_tokens':30,'output_tokens':20},'provenance_refs':list(task.allowed_evidence)}


def test_credit_ledger_transfers_without_validation_writeback():
 calibration=build_clarification_regret_artifact();cal_adapters={FINGERPRINT_LANE:FixtureAdapter(FINGERPRINT_LANE,calibration['private_oracle']['bindings'])};cal_run=ClarificationActionCreditRuntime(corpus_artifact=calibration).evaluate(experiment_id='fixture-credit-cal',mode='CALIBRATION',adapters=cal_adapters);validate_action_credit_run(cal_run,corpus_artifact=calibration,expected_mode='CALIBRATION')
 ledger=build_action_credit_ledger(calibration_corpus=calibration,calibration_run=cal_run);validate_action_credit_ledger(ledger,calibration_corpus=calibration,calibration_run=cal_run)
 assert next(x for x in ledger['records'] if x['fingerprint']=='OPEN_RIVALS')['direct_success_posterior']==0.5
 validation=build_action_credit_validation_artifact();validate_action_credit_validation_artifact(validation);adapters={FINGERPRINT_LANE:FixtureAdapter(FINGERPRINT_LANE,validation['private_oracle']['bindings']),DIRECT_LANE:FixtureAdapter(DIRECT_LANE,validation['private_oracle']['bindings'])};val_run=ClarificationActionCreditRuntime(corpus_artifact=validation).evaluate(experiment_id='fixture-credit-val',mode='VALIDATION',adapters=adapters,ledger=ledger);validate_action_credit_run(val_run,corpus_artifact=validation,expected_mode='VALIDATION',ledger=ledger)
 artifact=build_action_credit_calibration(calibration_corpus=calibration,calibration_run=cal_run,ledger=ledger,validation_corpus=validation,validation_run=val_run);validate_action_credit_calibration(artifact,calibration_corpus=calibration,calibration_run=cal_run,ledger=ledger,validation_corpus=validation,validation_run=val_run)
 assert artifact['candidate_state']=='ACTION_CREDIT_TRANSFER_CANDIDATE';assert artifact['arm_metrics']['LEDGER_POLICY']['mean_utility']==0.9;assert artifact['validation_outcomes_written_to_current_ledger'] is False


def test_action_credit_validation_rejects_record_tamper():
 calibration=build_clarification_regret_artifact();cal_run=ClarificationActionCreditRuntime(corpus_artifact=calibration).evaluate(experiment_id='fixture-credit-cal2',mode='CALIBRATION',adapters={FINGERPRINT_LANE:FixtureAdapter(FINGERPRINT_LANE,calibration['private_oracle']['bindings'])});ledger=build_action_credit_ledger(calibration_corpus=calibration,calibration_run=cal_run);validation=build_action_credit_validation_artifact();run=ClarificationActionCreditRuntime(corpus_artifact=validation).evaluate(experiment_id='fixture-credit-val2',mode='VALIDATION',adapters={FINGERPRINT_LANE:FixtureAdapter(FINGERPRINT_LANE,validation['private_oracle']['bindings']),DIRECT_LANE:FixtureAdapter(DIRECT_LANE,validation['private_oracle']['bindings'])},ledger=ledger)
 tampered=deepcopy(run);tampered['records'][0]['ledger_policy_action']='ANSWER_B';tampered['candidate_run_hash']=hash_payload({k:v for k,v in tampered.items() if k!='candidate_run_hash'})
 with pytest.raises(ValueError,match='records_invalid'):validate_action_credit_run(tampered,corpus_artifact=validation,expected_mode='VALIDATION',ledger=ledger)
