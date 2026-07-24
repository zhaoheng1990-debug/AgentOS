"""Calibration and fresh-validation runtime for clarification action credit."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .clarification_action_credit_contracts import FINGERPRINT_TASK_KIND, FINGERPRINT_VERSION, fingerprint_schema, validate_fingerprint
from .clarification_action_credit_holdout import validate_action_credit_validation_artifact
from .clarification_action_credit_ledger import select_ledger_action
from .clarification_regret_contracts import DIRECT_TASK_KIND, DIRECT_VERSION, direct_schema, validate_direct
from .clarification_regret_holdout import CLARIFICATION_COST, CORRECT_UTILITY, WRONG_UTILITY, validate_clarification_regret_artifact
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "clarification_action_credit_runtime_v0_7"
FINGERPRINT_LANE = "STRUCTURAL_FINGERPRINT"
DIRECT_LANE = "HOLISTIC_DIRECT"
MODES = ("CALIBRATION", "VALIDATION")


class ClarificationActionCreditRuntime:
    def __init__(self, *, corpus_artifact):
        _validate_corpus(corpus_artifact)
        self.corpus = corpus_artifact
        self.surface = corpus_artifact["public_surface"]
        self.evidence_refs = (*tuple(corpus_artifact["evidence_refs"]), f"artifact://{corpus_artifact['artifact_hash']}")

    def evaluate(self, *, experiment_id, mode, adapters, ledger=None):
        if mode not in MODES:
            raise ValueError("clarification_action_credit_mode_invalid")
        expected_lanes = {FINGERPRINT_LANE} if mode == "CALIBRATION" else {FINGERPRINT_LANE, DIRECT_LANE}
        if set(adapters) != expected_lanes or len({adapter.profile.provider_id for adapter in adapters.values()}) != len(adapters):
            raise ValueError("clarification_action_credit_adapter_surface_invalid")
        if mode == "VALIDATION" and (not ledger or ledger.get("source_corpus_hash") == self.corpus["artifact_hash"]):
            raise ValueError("clarification_action_credit_ledger_source_invalid")
        lanes = {lane: {"judgments": [], "failures": [], "provider_calls": 0, "input_tokens": 0, "output_tokens": 0} for lane in expected_lanes}
        for batch in self.surface["batches"]:
            for lane in sorted(expected_lanes):
                adapter = adapters[lane]
                result, accounting = self._route(lane, adapter, self._task(experiment_id, lane, adapter, batch), batch)
                for key in ("provider_calls", "input_tokens", "output_tokens"):
                    lanes[lane][key] += accounting[key]
                lanes[lane]["judgments" if result["ok"] else "failures"].append(result["record"])
        proposals = _index(lanes[FINGERPRINT_LANE]["judgments"])
        proposal_rows = [{"blind_case_id": blind_id, **proposals.get(blind_id, {"fingerprint": "UNCERTAIN", "preferred_direct_answer": "UNCERTAIN"})} for blind_id in sorted(self.corpus["private_oracle"]["bindings"])]
        commitment = {
            "runtime_version": RUNTIME_VERSION,
            "experiment_id": experiment_id,
            "mode": mode,
            "source_artifact_hash": self.corpus["artifact_hash"],
            "public_surface_hash": self.surface["surface_hash"],
            "role_bindings": {lane: {"provider_id": adapter.profile.provider_id, "model_id": adapter.profile.model_id, "task_kind": FINGERPRINT_TASK_KIND if lane == FINGERPRINT_LANE else DIRECT_TASK_KIND, "context_scope": f"ISOLATED::{lane}"} for lane, adapter in adapters.items()},
            "lanes": lanes,
            "proposals": proposal_rows,
            "total_unique_provider_calls": sum(item["provider_calls"] for item in lanes.values()),
            "total_unique_input_tokens": sum(item["input_tokens"] for item in lanes.values()),
            "total_unique_output_tokens": sum(item["output_tokens"] for item in lanes.values()),
            "private_oracle_available_at_prediction_time": False,
            "validation_outcomes_used_for_current_action": False,
            "runtime_owns_final_action": True,
            "selection_authority": False, "retention_authority": False, "production_authority": False,
        }
        if mode == "VALIDATION":
            direct = _index_direct(lanes[DIRECT_LANE]["judgments"])
            records = []
            for proposal in proposal_rows:
                blind_id = proposal["blind_case_id"]
                direct_item = direct.get(blind_id)
                records.append({
                    "blind_case_id": blind_id,
                    "always_ask_action": "ASK",
                    "always_answer_a_action": "ANSWER_A",
                    "direct_policy_action": "ASK" if not direct_item or direct_item["action"] == "UNCERTAIN" else direct_item["action"],
                    "fingerprint": proposal["fingerprint"],
                    "preferred_direct_answer": proposal["preferred_direct_answer"],
                    "ledger_policy_action": select_ledger_action(ledger=ledger, fingerprint=proposal["fingerprint"], preferred_direct_answer=proposal["preferred_direct_answer"]),
                })
            commitment["ledger_hash"] = ledger["ledger_hash"]
            commitment["records"] = records
            commitment["arm_accounting"] = {
                "ALWAYS_ASK": {"attributed_provider_calls": 0, "attributed_input_tokens": 0, "attributed_output_tokens": 0},
                "ALWAYS_ANSWER_A": {"attributed_provider_calls": 0, "attributed_input_tokens": 0, "attributed_output_tokens": 0},
                "DIRECT_POLICY": _account(lanes, (DIRECT_LANE,)),
                "LEDGER_POLICY": _account(lanes, (FINGERPRINT_LANE,)),
            }
        return {**commitment, "candidate_run_hash": hash_payload(commitment)}

    def _task(self, experiment_id, lane, adapter, batch):
        case_ids = tuple(item["blind_case_id"] for item in batch["public_cases"])
        inputs = {"source_identity": "WITHHELD", "private_intent_oracle": "WITHHELD_AND_INACCESSIBLE", "construction_category": "WITHHELD", "public_cases": batch["public_cases"], "utility_contract": {"correct_answer_utility": CORRECT_UTILITY, "wrong_answer_utility": WRONG_UTILITY, "clarification_cost": CLARIFICATION_COST, "clarification_reveals_intended_object": True, "genuinely_open_intent_prior": {"ANSWER_A": 0.5, "ANSWER_B": 0.5}}}
        if lane == FINGERPRINT_LANE:
            objective = (
                "Classify the structural relation between the request and the two proposed objects as OPEN_RIVALS, PROMPT_FIXED, EQUIVALENT_RIVALS, UNSUPPORTED_RIVAL, or UNCERTAIN. "
                "Also identify the best direct answer if one must answer without asking. Do not estimate a probability and do not choose ASK. "
                "A common convention is not PROMPT_FIXED; an assumption absent from the prompt supports UNSUPPORTED_RIVAL. Return JSON only."
            )
            schema, task_kind = fingerprint_schema(batch["batch_id"], case_ids), FINGERPRINT_TASK_KIND
        else:
            objective = "Choose ASK, ANSWER_A, or ANSWER_B for each case to maximize expected utility under the supplied contract. Use only the public prompt and packet. Return JSON only."
            schema, task_kind = direct_schema(batch["batch_id"], case_ids), DIRECT_TASK_KIND
        return ProviderCognitiveTask(task_id=f"{experiment_id}-{adapter.profile.provider_id}-{batch['batch_id']}", task_kind=task_kind, objective=objective, inputs=inputs, allowed_evidence=list(self.evidence_refs), expected_schema=schema, timeout_seconds=min(600, adapter.profile.max_timeout_seconds), failure_semantics="record_failure_and_runtime_asks")

    def _route(self, lane, adapter, task, batch):
        envelope = ProviderTaskRouter([adapter]).route(task)
        invocation = envelope.invocation_receipt.as_dict()
        usage = invocation.get("token_usage") or {}
        accounting = {"provider_calls": max(1, int(usage.get("provider_calls") or 1)), "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0), "output_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)}
        case_ids = tuple(item["blind_case_id"] for item in batch["public_cases"])
        if envelope.status != "COMPLETED":
            return ({"ok": False, "record": {"batch_id": batch["batch_id"], "case_ids": list(case_ids), "status": envelope.status, "validation_errors": list(envelope.validation_errors), "invocation_receipt": invocation}}, accounting)
        try:
            _validate_payload(lane, envelope.normalized_result, batch["batch_id"], case_ids, self.evidence_refs)
        except ValueError as exc:
            return ({"ok": False, "record": {"batch_id": batch["batch_id"], "case_ids": list(case_ids), "status": "SEMANTIC_VALIDATION_FAILED", "validation_errors": [str(exc)], "invocation_receipt": invocation}}, accounting)
        receipt_commitment = {"receipt_version": FINGERPRINT_VERSION if lane == FINGERPRINT_LANE else DIRECT_VERSION, "lane": lane, "provider_id": adapter.profile.provider_id, "model_id": adapter.profile.model_id, "task_contract_hash": task.contract_hash(), "invocation_receipt_hash": invocation["receipt_hash"], "public_surface_hash": self.surface["surface_hash"], "case_ids": list(case_ids), "payload_hash": hash_payload(envelope.normalized_result), "evidence_refs": list(task.allowed_evidence), "provider_backed": True, "provider_authority": False}
        receipt = {**receipt_commitment, "receipt_hash": hash_payload(receipt_commitment)}
        return ({"ok": True, "record": {"batch_id": batch["batch_id"], "payload": envelope.normalized_result, "invocation_receipt": invocation, "receipt": receipt}}, accounting)


def validate_action_credit_run(run, *, corpus_artifact, expected_mode, ledger=None):
    _validate_corpus(corpus_artifact)
    commitment = {key: value for key, value in run.items() if key != "candidate_run_hash"}
    if run.get("candidate_run_hash") != hash_payload(commitment) or run.get("runtime_version") != RUNTIME_VERSION or run.get("mode") != expected_mode or run.get("source_artifact_hash") != corpus_artifact["artifact_hash"] or run.get("private_oracle_available_at_prediction_time") is not False or run.get("validation_outcomes_used_for_current_action") is not False or any(run.get(key) is not False for key in ("selection_authority", "retention_authority", "production_authority")):
        raise ValueError("clarification_action_credit_run_invalid")
    expected_lanes = {FINGERPRINT_LANE} if expected_mode == "CALIBRATION" else {FINGERPRINT_LANE, DIRECT_LANE}
    if set(run.get("lanes", {})) != expected_lanes or set(run.get("role_bindings", {})) != expected_lanes:
        raise ValueError("clarification_action_credit_lane_invalid")
    if len(run.get("proposals", [])) != len(corpus_artifact["private_oracle"]["bindings"]):
        raise ValueError("clarification_action_credit_proposal_coverage_invalid")
    proposals = _index(run["lanes"][FINGERPRINT_LANE]["judgments"])
    expected_proposals = [{"blind_case_id": blind_id, **proposals.get(blind_id, {"fingerprint": "UNCERTAIN", "preferred_direct_answer": "UNCERTAIN"})} for blind_id in sorted(corpus_artifact["private_oracle"]["bindings"])]
    if run["proposals"] != expected_proposals:
        raise ValueError("clarification_action_credit_proposal_invalid")
    if expected_mode == "VALIDATION":
        if not ledger or run.get("ledger_hash") != ledger.get("ledger_hash"):
            raise ValueError("clarification_action_credit_ledger_binding_invalid")
        direct = _index_direct(run["lanes"][DIRECT_LANE]["judgments"])
        expected_records = []
        for proposal in expected_proposals:
            blind_id = proposal["blind_case_id"]; direct_item = direct.get(blind_id)
            expected_records.append({"blind_case_id": blind_id, "always_ask_action": "ASK", "always_answer_a_action": "ANSWER_A", "direct_policy_action": "ASK" if not direct_item or direct_item["action"] == "UNCERTAIN" else direct_item["action"], "fingerprint": proposal["fingerprint"], "preferred_direct_answer": proposal["preferred_direct_answer"], "ledger_policy_action": select_ledger_action(ledger=ledger, fingerprint=proposal["fingerprint"], preferred_direct_answer=proposal["preferred_direct_answer"])})
        if run.get("records") != expected_records:
            raise ValueError("clarification_action_credit_records_invalid")


def _validate_corpus(corpus):
    if corpus.get("artifact_version") == "clarification_regret_source_v0_6":
        validate_clarification_regret_artifact(corpus)
    elif corpus.get("artifact_version") == "clarification_action_credit_source_v0_7":
        validate_action_credit_validation_artifact(corpus)
    else:
        raise ValueError("clarification_action_credit_corpus_invalid")


def _validate_payload(lane, payload, batch_id, case_ids, evidence_refs):
    if lane == FINGERPRINT_LANE:
        validate_fingerprint(payload, batch_id=batch_id, case_ids=case_ids, evidence_refs=evidence_refs)
    else:
        validate_direct(payload, batch_id=batch_id, case_ids=case_ids, evidence_refs=evidence_refs)


def _index(judgments):
    return {item["blind_case_id"]: {key: value for key, value in item.items() if key != "blind_case_id"} for judgment in judgments for item in judgment["payload"]["assessments"]}


def _index_direct(judgments):
    return {item["blind_case_id"]: item for judgment in judgments for item in judgment["payload"]["assessments"]}


def _account(lanes, selected):
    return {"attributed_provider_calls": sum(lanes[lane]["provider_calls"] for lane in selected), "attributed_input_tokens": sum(lanes[lane]["input_tokens"] for lane in selected), "attributed_output_tokens": sum(lanes[lane]["output_tokens"] for lane in selected)}
