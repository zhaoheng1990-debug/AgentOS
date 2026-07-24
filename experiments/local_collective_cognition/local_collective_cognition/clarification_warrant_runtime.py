"""Equal-call baseline and explicit-warrant runtime for v0.10."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .clarification_two_axis_contracts import TWO_AXIS_TASK_KIND, TWO_AXIS_VERSION, derive_category, two_axis_schema, validate_two_axis
from .clarification_warrant_contracts import WARRANT_TASK_KIND, WARRANT_VERSION, derive_warrant_decision, validate_warrant, warrant_schema
from .clarification_warrant_holdout import validate_warrant_holdout_artifact
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "clarification_warrant_runtime_v0_10"
BASELINE_LANE = "BASELINE_TWO_AXIS"
WARRANT_LANE = "EXPLICIT_WARRANT"
LANES = (BASELINE_LANE, WARRANT_LANE)


class ClarificationWarrantRuntime:
    def __init__(self, *, corpus_artifact):
        validate_warrant_holdout_artifact(corpus_artifact)
        self.corpus = corpus_artifact
        self.surface = corpus_artifact["public_surface"]
        self.evidence_refs = (*tuple(corpus_artifact["evidence_refs"]), f"artifact://{corpus_artifact['artifact_hash']}")

    def evaluate(self, *, experiment_id, adapters):
        if set(adapters) != set(LANES) or len({adapter.profile.provider_id for adapter in adapters.values()}) != len(adapters):
            raise ValueError("clarification_warrant_adapter_surface_invalid")
        lanes = {lane: {"judgments": [], "failures": [], "provider_calls": 0, "input_tokens": 0, "output_tokens": 0} for lane in LANES}
        for batch in self.surface["batches"]:
            for lane in LANES:
                adapter = adapters[lane]
                result, accounting = self._route(lane, adapter, self._task(experiment_id, lane, adapter, batch), batch)
                for key in ("provider_calls", "input_tokens", "output_tokens"):
                    lanes[lane][key] += accounting[key]
                lanes[lane]["judgments" if result["ok"] else "failures"].append(result["record"])
        commitment = {
            "runtime_version": RUNTIME_VERSION,
            "experiment_id": experiment_id,
            "source_artifact_hash": self.corpus["artifact_hash"],
            "public_surface_hash": self.surface["surface_hash"],
            "role_bindings": {
                lane: {
                    "provider_id": adapters[lane].profile.provider_id,
                    "model_id": adapters[lane].profile.model_id,
                    "task_kind": TWO_AXIS_TASK_KIND if lane == BASELINE_LANE else WARRANT_TASK_KIND,
                    "context_scope": f"ISOLATED::{lane}",
                }
                for lane in LANES
            },
            "lanes": lanes,
            "predictions": _build_predictions(self.corpus, lanes),
            "arm_accounting": {lane: _account(lanes[lane]) for lane in LANES},
            "total_unique_provider_calls": sum(lanes[lane]["provider_calls"] for lane in LANES),
            "total_unique_input_tokens": sum(lanes[lane]["input_tokens"] for lane in LANES),
            "total_unique_output_tokens": sum(lanes[lane]["output_tokens"] for lane in LANES),
            "private_oracle_available_at_prediction_time": False,
            "runtime_executes_hard_warrant_policy": True,
            "pragmatic_preference_has_hard_constraint_authority": False,
            "action_policy_evaluated": False,
            "action_credit_authority": False,
            "selection_authority": False,
            "retention_authority": False,
            "production_authority": False,
        }
        return {**commitment, "candidate_run_hash": hash_payload(commitment)}

    def _task(self, experiment_id, lane, adapter, batch):
        case_ids = tuple(case["blind_case_id"] for case in batch["public_cases"])
        inputs = {
            "source_identity": "WITHHELD",
            "private_oracle": "WITHHELD_AND_INACCESSIBLE",
            "public_cases": batch["public_cases"],
            "matched_counterpart_visible": False,
        }
        if lane == BASELINE_LANE:
            objective = (
                "Assess object_selection as CANDIDATE_A, CANDIDATE_B, or NONE independently from assessment_status "
                "RESOLVED or UNRESOLVED. NONE + RESOLVED means the prompt does not explicitly select either object. "
                "Bind quotes exactly and return JSON only."
            )
            schema, task_kind = two_axis_schema(batch["batch_id"], case_ids), TWO_AXIS_TASK_KIND
        else:
            objective = (
                "Separate three coordinates. explicit_selection is what the prompt itself fixes: CANDIDATE_A, "
                "CANDIDATE_B, or NONE. pragmatic_preference is the most natural default if forced, and may be A or B "
                "even when explicit_selection is NONE. assessment_status says whether this distinction is resolvable. "
                "Classify the explicit warrant as EXACT_OBJECT_MENTION, EXPLICIT_DEFINITION, EXPLICIT_OPERATION, "
                "DEFAULT_COMPATIBILITY, or NO_EXPLICIT_WARRANT. Natural fit, convention, or a generic output label "
                "is DEFAULT_COMPATIBILITY rather than explicit selection, regardless of which candidate it favors. "
                "Only exact/defined/operational prompt evidence gets a warrant quote; soft warrant_quote must be NONE. "
                "Return JSON only."
            )
            schema, task_kind = warrant_schema(batch["batch_id"], case_ids), WARRANT_TASK_KIND
        return ProviderCognitiveTask(
            task_id=f"{experiment_id}-{adapter.profile.provider_id}-{batch['batch_id']}",
            task_kind=task_kind,
            objective=objective,
            inputs=inputs,
            allowed_evidence=list(self.evidence_refs),
            expected_schema=schema,
            timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
            failure_semantics="record_failure_and_runtime_marks_uncertain",
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
        case_ids = [case["blind_case_id"] for case in batch["public_cases"]]
        if envelope.status != "COMPLETED":
            return {"ok": False, "record": _failure(batch, envelope.status, envelope.validation_errors, invocation)}, accounting
        try:
            _validate_payload(lane, envelope.normalized_result, batch, self.evidence_refs)
        except ValueError as exc:
            return {"ok": False, "record": _failure(batch, "SEMANTIC_VALIDATION_FAILED", [str(exc)], invocation)}, accounting
        receipt_commitment = {
            "receipt_version": TWO_AXIS_VERSION if lane == BASELINE_LANE else WARRANT_VERSION,
            "lane": lane,
            "provider_id": adapter.profile.provider_id,
            "model_id": adapter.profile.model_id,
            "task_contract_hash": task.contract_hash(),
            "invocation_receipt_hash": invocation["receipt_hash"],
            "public_surface_hash": self.surface["surface_hash"],
            "case_ids": case_ids,
            "payload_hash": hash_payload(envelope.normalized_result),
            "evidence_refs": list(task.allowed_evidence),
            "provider_backed": True,
            "provider_authority": False,
        }
        receipt = {**receipt_commitment, "receipt_hash": hash_payload(receipt_commitment)}
        return {"ok": True, "record": {"batch_id": batch["batch_id"], "payload": envelope.normalized_result, "invocation_receipt": invocation, "receipt": receipt}}, accounting


def validate_warrant_run(run, *, corpus_artifact):
    validate_warrant_holdout_artifact(corpus_artifact)
    commitment = {key: value for key, value in run.items() if key != "candidate_run_hash"}
    if run.get("candidate_run_hash") != hash_payload(commitment) or run.get("runtime_version") != RUNTIME_VERSION or run.get("source_artifact_hash") != corpus_artifact["artifact_hash"]:
        raise ValueError("clarification_warrant_run_invalid")
    if set(run.get("lanes", {})) != set(LANES) or set(run.get("role_bindings", {})) != set(LANES):
        raise ValueError("clarification_warrant_run_lanes_invalid")
    if run.get("private_oracle_available_at_prediction_time") is not False or run.get("action_policy_evaluated") is not False or run.get("pragmatic_preference_has_hard_constraint_authority") is not False:
        raise ValueError("clarification_warrant_prediction_boundary_invalid")
    if any(run.get(key) is not False for key in ("action_credit_authority", "selection_authority", "retention_authority", "production_authority")):
        raise ValueError("clarification_warrant_authority_invalid")
    batches = {batch["batch_id"]: batch for batch in corpus_artifact["public_surface"]["batches"]}
    evidence_refs = (*tuple(corpus_artifact["evidence_refs"]), f"artifact://{corpus_artifact['artifact_hash']}")
    for lane in LANES:
        lane_result = run["lanes"][lane]
        if len(lane_result.get("judgments", [])) + len(lane_result.get("failures", [])) != len(batches):
            raise ValueError("clarification_warrant_batch_coverage_invalid")
        for judgment in lane_result.get("judgments", []):
            batch = batches.get(judgment.get("batch_id"))
            if not batch:
                raise ValueError("clarification_warrant_batch_binding_invalid")
            _validate_payload(lane, judgment.get("payload"), batch, evidence_refs)
    if run.get("predictions") != _build_predictions(corpus_artifact, run["lanes"]):
        raise ValueError("clarification_warrant_predictions_invalid")


def _validate_payload(lane, payload, batch, evidence_refs):
    case_ids = tuple(case["blind_case_id"] for case in batch["public_cases"])
    if lane == BASELINE_LANE:
        validate_two_axis(payload, batch_id=batch["batch_id"], public_cases=batch["public_cases"], evidence_refs=evidence_refs)
    else:
        validate_warrant(payload, batch_id=batch["batch_id"], public_cases=batch["public_cases"], evidence_refs=evidence_refs)


def _build_predictions(corpus, lanes):
    baseline = _index(lanes[BASELINE_LANE]["judgments"])
    warranted = _index(lanes[WARRANT_LANE]["judgments"])
    rows = []
    for blind_id in sorted(corpus["private_oracle"]["bindings"]):
        base = baseline.get(blind_id, {})
        base_selection = base.get("object_selection", "NONE")
        base_status = base.get("assessment_status", "UNRESOLVED")
        item = warranted.get(blind_id, {})
        explicit = item.get("explicit_selection", "NONE")
        status = item.get("assessment_status", "UNRESOLVED")
        warrant_type = item.get("warrant_type", "NO_EXPLICIT_WARRANT")
        category, hard_selection, downgraded = derive_warrant_decision(explicit, status, warrant_type)
        rows.append({
            "blind_case_id": blind_id,
            "baseline_object_selection": base_selection,
            "baseline_assessment_status": base_status,
            "baseline_derived_category": derive_category(base_selection, base_status),
            "warrant_explicit_selection": explicit,
            "warrant_pragmatic_preference": item.get("pragmatic_preference", "NONE"),
            "warrant_assessment_status": status,
            "warrant_type": warrant_type,
            "warrant_derived_category": category,
            "warrant_hard_selection": hard_selection,
            "soft_selection_downgraded": downgraded,
            "warrant_quote_bound": bool(item),
        })
    return rows


def _index(judgments):
    return {item["blind_case_id"]: item for judgment in judgments for item in judgment["payload"]["assessments"]}


def _account(lane):
    return {
        "attributed_provider_calls": lane["provider_calls"],
        "attributed_input_tokens": lane["input_tokens"],
        "attributed_output_tokens": lane["output_tokens"],
    }


def _failure(batch, status, errors, invocation):
    return {"batch_id": batch["batch_id"], "case_ids": [case["blind_case_id"] for case in batch["public_cases"]], "status": status, "validation_errors": list(errors), "invocation_receipt": invocation}
