"""Three-lane runtime for two-axis clarification representation v0.9."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .clarification_action_credit_contracts import FINGERPRINT_TASK_KIND, FINGERPRINT_VERSION, fingerprint_schema, validate_fingerprint
from .clarification_two_axis_contracts import TWO_AXIS_TASK_KIND, TWO_AXIS_VERSION, derive_category, two_axis_schema, validate_two_axis
from .clarification_two_axis_holdout import validate_two_axis_holdout_artifact
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "clarification_two_axis_runtime_v0_9"
CATEGORY_LANE = "CATEGORY_FINGERPRINT"
PAIRED_AXIS_LANE = "PAIRED_TWO_AXIS"
SHUFFLED_AXIS_LANE = "SHUFFLED_TWO_AXIS"
LANES = (CATEGORY_LANE, PAIRED_AXIS_LANE, SHUFFLED_AXIS_LANE)
LANE_LAYOUT = {CATEGORY_LANE: "SHUFFLED", PAIRED_AXIS_LANE: "PAIRED", SHUFFLED_AXIS_LANE: "SHUFFLED"}


class ClarificationTwoAxisRuntime:
    def __init__(self, *, corpus_artifact):
        validate_two_axis_holdout_artifact(corpus_artifact)
        self.corpus = corpus_artifact
        self.surfaces = corpus_artifact["public_surfaces"]
        self.evidence_refs = (*tuple(corpus_artifact["evidence_refs"]), f"artifact://{corpus_artifact['artifact_hash']}")

    def evaluate(self, *, experiment_id, adapters):
        if set(adapters) != set(LANES) or len({adapter.profile.provider_id for adapter in adapters.values()}) != len(adapters):
            raise ValueError("clarification_two_axis_adapter_surface_invalid")
        lanes = {lane: {"judgments": [], "failures": [], "provider_calls": 0, "input_tokens": 0, "output_tokens": 0} for lane in LANES}
        for lane in LANES:
            surface = self.surfaces[LANE_LAYOUT[lane]]
            adapter = adapters[lane]
            for batch in surface["batches"]:
                result, accounting = self._route(lane, surface, adapter, self._task(experiment_id, lane, surface, adapter, batch), batch)
                for key in ("provider_calls", "input_tokens", "output_tokens"):
                    lanes[lane][key] += accounting[key]
                lanes[lane]["judgments" if result["ok"] else "failures"].append(result["record"])
        commitment = {
            "runtime_version": RUNTIME_VERSION,
            "experiment_id": experiment_id,
            "source_artifact_hash": self.corpus["artifact_hash"],
            "surface_hashes": {layout: surface["surface_hash"] for layout, surface in self.surfaces.items()},
            "role_bindings": {
                lane: {
                    "provider_id": adapters[lane].profile.provider_id,
                    "model_id": adapters[lane].profile.model_id,
                    "task_kind": FINGERPRINT_TASK_KIND if lane == CATEGORY_LANE else TWO_AXIS_TASK_KIND,
                    "layout": LANE_LAYOUT[lane],
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
            "runtime_derives_category_from_two_axes": True,
            "action_policy_evaluated": False,
            "action_credit_authority": False,
            "selection_authority": False,
            "retention_authority": False,
            "production_authority": False,
        }
        return {**commitment, "candidate_run_hash": hash_payload(commitment)}

    def _task(self, experiment_id, lane, surface, adapter, batch):
        case_ids = tuple(case["blind_case_id"] for case in batch["public_cases"])
        inputs = {
            "source_identity": "WITHHELD",
            "private_category_oracle": "WITHHELD_AND_INACCESSIBLE",
            "public_cases": batch["public_cases"],
            "layout": surface["layout"],
            "matched_counterpart_visible": surface["matched_counterpart_visible"],
        }
        if lane == CATEGORY_LANE:
            objective = (
                "Classify each request/object relation as OPEN_RIVALS, PROMPT_FIXED, EQUIVALENT_RIVALS, "
                "UNSUPPORTED_RIVAL, or UNCERTAIN. Identify the best direct answer if forced. Return JSON only."
            )
            schema, task_kind = fingerprint_schema(batch["batch_id"], case_ids), FINGERPRINT_TASK_KIND
        else:
            objective = (
                "Assess two independent axes. object_selection records what the prompt explicitly selects: "
                "CANDIDATE_A, CANDIDATE_B, or NONE. NONE is a positive, resolved finding that the requested wording "
                "does not select either candidate; it is not uncertainty. assessment_status records whether you have "
                "enough prompt evidence to make that object-state judgment: RESOLVED or UNRESOLVED. Use UNRESOLVED "
                "only when evidence is insufficient to decide whether a selection occurred. Bind request and decisive "
                "quotes exactly; decisive_quote is NONE when object_selection is NONE. Return JSON only."
            )
            schema, task_kind = two_axis_schema(batch["batch_id"], case_ids), TWO_AXIS_TASK_KIND
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

    def _route(self, lane, surface, adapter, task, batch):
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
            "receipt_version": FINGERPRINT_VERSION if lane == CATEGORY_LANE else TWO_AXIS_VERSION,
            "lane": lane,
            "layout": surface["layout"],
            "provider_id": adapter.profile.provider_id,
            "model_id": adapter.profile.model_id,
            "task_contract_hash": task.contract_hash(),
            "invocation_receipt_hash": invocation["receipt_hash"],
            "public_surface_hash": surface["surface_hash"],
            "case_ids": case_ids,
            "payload_hash": hash_payload(envelope.normalized_result),
            "evidence_refs": list(task.allowed_evidence),
            "provider_backed": True,
            "provider_authority": False,
        }
        receipt = {**receipt_commitment, "receipt_hash": hash_payload(receipt_commitment)}
        return {"ok": True, "record": {"batch_id": batch["batch_id"], "payload": envelope.normalized_result, "invocation_receipt": invocation, "receipt": receipt}}, accounting


def validate_two_axis_run(run, *, corpus_artifact):
    validate_two_axis_holdout_artifact(corpus_artifact)
    commitment = {key: value for key, value in run.items() if key != "candidate_run_hash"}
    if run.get("candidate_run_hash") != hash_payload(commitment) or run.get("runtime_version") != RUNTIME_VERSION or run.get("source_artifact_hash") != corpus_artifact["artifact_hash"]:
        raise ValueError("clarification_two_axis_run_invalid")
    if set(run.get("lanes", {})) != set(LANES) or set(run.get("role_bindings", {})) != set(LANES):
        raise ValueError("clarification_two_axis_run_lanes_invalid")
    if run.get("private_oracle_available_at_prediction_time") is not False or run.get("action_policy_evaluated") is not False:
        raise ValueError("clarification_two_axis_prediction_boundary_invalid")
    if any(run.get(key) is not False for key in ("action_credit_authority", "selection_authority", "retention_authority", "production_authority")):
        raise ValueError("clarification_two_axis_authority_invalid")
    evidence_refs = (*tuple(corpus_artifact["evidence_refs"]), f"artifact://{corpus_artifact['artifact_hash']}")
    for lane in LANES:
        surface = corpus_artifact["public_surfaces"][LANE_LAYOUT[lane]]
        batches = {batch["batch_id"]: batch for batch in surface["batches"]}
        lane_result = run["lanes"][lane]
        if len(lane_result.get("judgments", [])) + len(lane_result.get("failures", [])) != len(batches):
            raise ValueError("clarification_two_axis_batch_coverage_invalid")
        for judgment in lane_result.get("judgments", []):
            batch = batches.get(judgment.get("batch_id"))
            if not batch:
                raise ValueError("clarification_two_axis_batch_binding_invalid")
            _validate_payload(lane, judgment.get("payload"), batch, evidence_refs)
    if run.get("predictions") != _build_predictions(corpus_artifact, run["lanes"]):
        raise ValueError("clarification_two_axis_predictions_invalid")


def _validate_payload(lane, payload, batch, evidence_refs):
    case_ids = tuple(case["blind_case_id"] for case in batch["public_cases"])
    if lane == CATEGORY_LANE:
        validate_fingerprint(payload, batch_id=batch["batch_id"], case_ids=case_ids, evidence_refs=evidence_refs)
    else:
        validate_two_axis(payload, batch_id=batch["batch_id"], public_cases=batch["public_cases"], evidence_refs=evidence_refs)


def _build_predictions(corpus, lanes):
    category = _index(lanes[CATEGORY_LANE]["judgments"])
    paired = _index(lanes[PAIRED_AXIS_LANE]["judgments"])
    shuffled = _index(lanes[SHUFFLED_AXIS_LANE]["judgments"])
    rows = []
    for blind_id in sorted(corpus["private_oracle"]["bindings"]):
        baseline = category.get(blind_id, {})
        pair_item = paired.get(blind_id, {})
        shuffle_item = shuffled.get(blind_id, {})
        rows.append({
            "blind_case_id": blind_id,
            "category_fingerprint": baseline.get("fingerprint", "UNCERTAIN"),
            **_axis_prediction("paired", pair_item),
            **_axis_prediction("shuffled", shuffle_item),
        })
    return rows


def _axis_prediction(prefix, item):
    selection = item.get("object_selection", "NONE")
    status = item.get("assessment_status", "UNRESOLVED")
    return {
        f"{prefix}_object_selection": selection,
        f"{prefix}_assessment_status": status,
        f"{prefix}_derived_category": derive_category(selection, status),
        f"{prefix}_quote_bound": bool(item),
    }


def _index(judgments):
    return {item["blind_case_id"]: item for judgment in judgments for item in judgment["payload"]["assessments"]}


def _account(lane):
    return {
        "attributed_provider_calls": lane["provider_calls"],
        "attributed_input_tokens": lane["input_tokens"],
        "attributed_output_tokens": lane["output_tokens"],
    }


def _failure(batch, status, errors, invocation):
    return {
        "batch_id": batch["batch_id"],
        "case_ids": [case["blind_case_id"] for case in batch["public_cases"]],
        "status": status,
        "validation_errors": list(errors),
        "invocation_receipt": invocation,
    }
