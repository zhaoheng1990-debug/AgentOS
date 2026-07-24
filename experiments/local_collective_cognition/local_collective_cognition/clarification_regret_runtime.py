"""Provider orchestration for the v0.6 clarification-regret pilot."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .clarification_regret_contracts import DIRECT_TASK_KIND, DIRECT_VERSION, REGRET_TASK_KIND, REGRET_VERSION, direct_schema, regret_schema, validate_direct, validate_regret
from .clarification_regret_fusion import DIRECT, FUSION_VERSION, LANES, REGRET_LANES, build_clarification_regret_fusion
from .clarification_regret_holdout import CLARIFICATION_COST, CORRECT_UTILITY, EVIDENCE_REFS, WRONG_UTILITY, validate_clarification_regret_artifact
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "clarification_regret_runtime_v0_6"


class ClarificationRegretRuntime:
    def __init__(self, *, corpus_artifact):
        validate_clarification_regret_artifact(corpus_artifact)
        self.corpus_artifact = corpus_artifact
        self.surface = corpus_artifact["public_surface"]
        self.evidence_refs = (*EVIDENCE_REFS, f"artifact://{corpus_artifact['artifact_hash']}")

    def evaluate(self, *, experiment_id, adapters):
        if set(adapters) != set(LANES):
            raise ValueError("clarification_regret_adapter_surface_invalid")
        if len({adapter.profile.provider_id for adapter in adapters.values()}) != len(LANES):
            raise ValueError("clarification_regret_context_identity_not_isolated")
        lanes = {lane: {"judgments": [], "failures": [], "provider_calls": 0, "input_tokens": 0, "output_tokens": 0} for lane in LANES}
        for batch in self.surface["batches"]:
            for lane in LANES:
                adapter = adapters[lane]
                result, accounting = self._route(lane, adapter, self._task(experiment_id, lane, adapter, batch), batch)
                for key in ("provider_calls", "input_tokens", "output_tokens"):
                    lanes[lane][key] += accounting[key]
                lanes[lane]["judgments" if result["ok"] else "failures"].append(result["record"])
        fusion = build_clarification_regret_fusion(corpus_artifact=self.corpus_artifact, lanes=lanes)
        commitment = {
            "runtime_version": RUNTIME_VERSION,
            "fusion_version": FUSION_VERSION,
            "experiment_id": experiment_id,
            "source_artifact_hash": self.corpus_artifact["artifact_hash"],
            "public_surface_hash": self.surface["surface_hash"],
            "role_bindings": {
                lane: {"provider_id": adapter.profile.provider_id, "model_id": adapter.profile.model_id, "task_kind": DIRECT_TASK_KIND if lane == DIRECT else REGRET_TASK_KIND, "context_scope": f"ISOLATED::{lane}"}
                for lane, adapter in adapters.items()
            },
            "lanes": lanes,
            "fusion": fusion,
            "total_unique_provider_calls": sum(item["provider_calls"] for item in lanes.values()),
            "total_unique_input_tokens": sum(item["input_tokens"] for item in lanes.values()),
            "total_unique_output_tokens": sum(item["output_tokens"] for item in lanes.values()),
            "private_oracle_available_at_prediction_time": False,
            "provider_emits_final_runtime_action_for_regret_lanes": False,
            "runtime_owns_utility_policy_and_final_action": True,
            "post_outcome_adaptation_allowed": False,
            "selection_authority": False,
            "retention_authority": False,
            "production_authority": False,
        }
        return {**commitment, "candidate_run_hash": hash_payload(commitment)}

    def _task(self, experiment_id, lane, adapter, batch):
        case_ids = tuple(item["blind_case_id"] for item in batch["public_cases"])
        common = {
            "source_identity": "WITHHELD",
            "private_intent_oracle": "WITHHELD_AND_INACCESSIBLE",
            "construction_category": "WITHHELD",
            "public_cases": batch["public_cases"],
            "utility_contract": {
                "correct_answer_utility": CORRECT_UTILITY,
                "wrong_answer_utility": WRONG_UTILITY,
                "clarification_cost": CLARIFICATION_COST,
                "clarification_reveals_intended_object": True,
                "genuinely_open_intent_prior": {"ANSWER_A": 0.5, "ANSWER_B": 0.5},
            },
        }
        if lane == DIRECT:
            objective = (
                "Choose ASK, ANSWER_A, or ANSWER_B for each case to maximize expected utility under the supplied contract. "
                "Use only the public prompt and packet. ASK pays the clarification cost and then reveals the intended object. "
                "Return UNCERTAIN only when no action can be supported. Return JSON only."
            )
            schema = direct_schema(batch["batch_id"], case_ids)
            task_kind = DIRECT_TASK_KIND
        else:
            objective = (
                "Do not choose whether to ask. Identify the best direct answer from the public prompt and packet, then estimate the probability that this preferred direct answer targets the wrong object. "
                "For genuinely open alternatives use the supplied balanced intent prior; explicit wording, equivalent rivals, and unsupported assumptions should change the estimate. "
                "State the minimal counterfactual that would change the estimate. Runtime alone compares expected wrong-answer loss with clarification cost. Return JSON only."
            )
            schema = regret_schema(batch["batch_id"], case_ids)
            task_kind = REGRET_TASK_KIND
        return ProviderCognitiveTask(
            task_id=f"{experiment_id}-{adapter.profile.provider_id}-{batch['batch_id']}",
            task_kind=task_kind,
            objective=objective,
            inputs=common,
            allowed_evidence=list(self.evidence_refs),
            expected_schema=schema,
            timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
            failure_semantics="record_failed_lane_and_runtime_asks",
        )

    def _route(self, lane, adapter, task, batch):
        envelope = ProviderTaskRouter([adapter]).route(task)
        invocation = envelope.invocation_receipt.as_dict()
        usage = invocation.get("token_usage") or {}
        accounting = {
            "provider_calls": max(1, int(usage.get("provider_calls") or 1)),
            "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        }
        case_ids = tuple(item["blind_case_id"] for item in batch["public_cases"])
        if envelope.status != "COMPLETED":
            return ({"ok": False, "record": {"batch_id": batch["batch_id"], "case_ids": list(case_ids), "status": envelope.status, "validation_errors": list(envelope.validation_errors), "invocation_receipt": invocation}}, accounting)
        try:
            _validate_payload(lane, envelope.normalized_result, batch["batch_id"], case_ids, self.evidence_refs)
        except ValueError as exc:
            return ({"ok": False, "record": {"batch_id": batch["batch_id"], "case_ids": list(case_ids), "status": "SEMANTIC_VALIDATION_FAILED", "validation_errors": [str(exc)], "invocation_receipt": invocation, "payload_hash": hash_payload(envelope.normalized_result)}}, accounting)
        commitment = {
            "receipt_version": DIRECT_VERSION if lane == DIRECT else REGRET_VERSION,
            "lane": lane,
            "provider_id": adapter.profile.provider_id,
            "model_id": adapter.profile.model_id,
            "task_contract_hash": task.contract_hash(),
            "invocation_receipt_hash": invocation["receipt_hash"],
            "public_surface_hash": self.surface["surface_hash"],
            "case_ids": list(case_ids),
            "payload_hash": hash_payload(envelope.normalized_result),
            "evidence_refs": list(task.allowed_evidence),
            "provider_backed": True,
            "provider_authority": False,
            "context_scope": f"ISOLATED::{lane}",
        }
        receipt = {**commitment, "receipt_hash": hash_payload(commitment)}
        return ({"ok": True, "record": {"batch_id": batch["batch_id"], "payload": envelope.normalized_result, "invocation_receipt": invocation, "receipt": receipt}}, accounting)


def validate_clarification_regret_run(run, *, corpus_artifact):
    validate_clarification_regret_artifact(corpus_artifact)
    commitment = {key: value for key, value in run.items() if key != "candidate_run_hash"}
    if (
        run.get("candidate_run_hash") != hash_payload(commitment)
        or run.get("runtime_version") != RUNTIME_VERSION
        or run.get("fusion_version") != FUSION_VERSION
        or run.get("source_artifact_hash") != corpus_artifact["artifact_hash"]
        or run.get("public_surface_hash") != corpus_artifact["public_surface"]["surface_hash"]
        or run.get("private_oracle_available_at_prediction_time") is not False
        or run.get("provider_emits_final_runtime_action_for_regret_lanes") is not False
        or run.get("runtime_owns_utility_policy_and_final_action") is not True
        or any(run.get(key) is not False for key in ("selection_authority", "retention_authority", "production_authority"))
    ):
        raise ValueError("clarification_regret_run_binding_invalid")
    if set(run.get("lanes", {})) != set(LANES) or set(run.get("role_bindings", {})) != set(LANES):
        raise ValueError("clarification_regret_lane_surface_invalid")
    batches = {batch["batch_id"]: batch for batch in corpus_artifact["public_surface"]["batches"]}
    refs = (*EVIDENCE_REFS, f"artifact://{corpus_artifact['artifact_hash']}")
    for lane, lane_record in run["lanes"].items():
        items = (*lane_record["judgments"], *lane_record["failures"])
        if len(items) != len(batches) or {item["batch_id"] for item in items} != set(batches):
            raise ValueError("clarification_regret_lane_incomplete")
        for item in lane_record["judgments"]:
            case_ids = tuple(case["blind_case_id"] for case in batches[item["batch_id"]]["public_cases"])
            _validate_payload(lane, item["payload"], item["batch_id"], case_ids, refs)
            receipt = item["receipt"]
            receipt_commitment = {key: value for key, value in receipt.items() if key != "receipt_hash"}
            if receipt.get("receipt_hash") != hash_payload(receipt_commitment) or receipt.get("payload_hash") != hash_payload(item["payload"]) or receipt.get("case_ids") != list(case_ids):
                raise ValueError("clarification_regret_receipt_invalid")
    if run.get("fusion") != build_clarification_regret_fusion(corpus_artifact=corpus_artifact, lanes=run["lanes"]):
        raise ValueError("clarification_regret_fusion_invalid")


def _validate_payload(lane, payload, batch_id, case_ids, evidence_refs):
    if lane == DIRECT:
        validate_direct(payload, batch_id=batch_id, case_ids=case_ids, evidence_refs=evidence_refs)
    else:
        validate_regret(payload, batch_id=batch_id, case_ids=case_ids, evidence_refs=evidence_refs)
