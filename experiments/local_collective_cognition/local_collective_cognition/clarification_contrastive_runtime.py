"""Matched-pair runtime for clarification representation v0.8."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .clarification_action_credit_contracts import (
    FINGERPRINT_TASK_KIND,
    FINGERPRINT_VERSION,
    fingerprint_schema,
    validate_fingerprint,
)
from .clarification_contrastive_contracts import (
    SELECTION_TASK_KIND,
    SELECTION_VERSION,
    selection_schema,
    selection_to_category,
    validate_selection,
)
from .clarification_contrastive_holdout import validate_contrastive_holdout_artifact
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "clarification_contrastive_runtime_v0_8"
CATEGORY_LANE = "CATEGORY_FINGERPRINT"
SELECTION_LANE = "REQUEST_SELECTION"
LANES = (CATEGORY_LANE, SELECTION_LANE)


class ClarificationContrastiveRuntime:
    def __init__(self, *, corpus_artifact):
        validate_contrastive_holdout_artifact(corpus_artifact)
        self.corpus = corpus_artifact
        self.surface = corpus_artifact["public_surface"]
        self.evidence_refs = (*tuple(corpus_artifact["evidence_refs"]), f"artifact://{corpus_artifact['artifact_hash']}")

    def evaluate(self, *, experiment_id, adapters):
        if set(adapters) != set(LANES):
            raise ValueError("clarification_contrastive_adapter_surface_invalid")
        if len({adapter.profile.provider_id for adapter in adapters.values()}) != len(adapters):
            raise ValueError("clarification_contrastive_context_isolation_invalid")
        lanes = {
            lane: {"judgments": [], "failures": [], "provider_calls": 0, "input_tokens": 0, "output_tokens": 0}
            for lane in LANES
        }
        for batch in self.surface["batches"]:
            for lane in LANES:
                adapter = adapters[lane]
                result, accounting = self._route(lane, adapter, self._task(experiment_id, lane, adapter, batch), batch)
                for key in ("provider_calls", "input_tokens", "output_tokens"):
                    lanes[lane][key] += accounting[key]
                lanes[lane]["judgments" if result["ok"] else "failures"].append(result["record"])
        predictions = _build_predictions(self.corpus, lanes)
        commitment = {
            "runtime_version": RUNTIME_VERSION,
            "experiment_id": experiment_id,
            "source_artifact_hash": self.corpus["artifact_hash"],
            "public_surface_hash": self.surface["surface_hash"],
            "role_bindings": {
                lane: {
                    "provider_id": adapters[lane].profile.provider_id,
                    "model_id": adapters[lane].profile.model_id,
                    "task_kind": FINGERPRINT_TASK_KIND if lane == CATEGORY_LANE else SELECTION_TASK_KIND,
                    "context_scope": f"ISOLATED::{lane}",
                }
                for lane in LANES
            },
            "lanes": lanes,
            "predictions": predictions,
            "arm_accounting": {lane: _account(lanes[lane]) for lane in LANES},
            "total_unique_provider_calls": sum(lanes[lane]["provider_calls"] for lane in LANES),
            "total_unique_input_tokens": sum(lanes[lane]["input_tokens"] for lane in LANES),
            "total_unique_output_tokens": sum(lanes[lane]["output_tokens"] for lane in LANES),
            "private_oracle_available_at_prediction_time": False,
            "runtime_derives_selection_category": True,
            "action_policy_evaluated": False,
            "ledger_available_at_prediction_time": False,
            "selection_authority": False,
            "retention_authority": False,
            "production_authority": False,
        }
        return {**commitment, "candidate_run_hash": hash_payload(commitment)}

    def _task(self, experiment_id, lane, adapter, batch):
        case_ids = tuple(case["blind_case_id"] for case in batch["public_cases"])
        inputs = {
            "source_identity": "WITHHELD",
            "private_category_oracle": "WITHHELD_AND_INACCESSIBLE",
            "public_cases": batch["public_cases"],
            "matched_pair_note": "The two cases differ only in the requested output wording. Position carries no label information.",
        }
        if lane == CATEGORY_LANE:
            objective = (
                "Classify each request/object relation as OPEN_RIVALS, PROMPT_FIXED, EQUIVALENT_RIVALS, "
                "UNSUPPORTED_RIVAL, or UNCERTAIN. Identify the best direct answer if forced. A metric being "
                "common is not enough to make it prompt-fixed. Return JSON only."
            )
            schema = fingerprint_schema(batch["batch_id"], case_ids)
            task_kind = FINGERPRINT_TASK_KIND
        else:
            objective = (
                "Do not assign an ambiguity category. For each case, quote the requested object phrase exactly "
                "from the public prompt, then determine whether that wording explicitly selects candidate A, "
                "candidate B, neither candidate, or remains uncertain. If one candidate is selected, quote the "
                "decisive prompt text exactly. If neither or uncertain, decisive_quote must be NONE. Compare the "
                "two minimally different requests when explaining the decision. Return JSON only."
            )
            schema = selection_schema(batch["batch_id"], case_ids)
            task_kind = SELECTION_TASK_KIND
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
            "receipt_version": FINGERPRINT_VERSION if lane == CATEGORY_LANE else SELECTION_VERSION,
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
        return {
            "ok": True,
            "record": {
                "batch_id": batch["batch_id"],
                "payload": envelope.normalized_result,
                "invocation_receipt": invocation,
                "receipt": receipt,
            },
        }, accounting


def validate_contrastive_run(run, *, corpus_artifact):
    validate_contrastive_holdout_artifact(corpus_artifact)
    commitment = {key: value for key, value in run.items() if key != "candidate_run_hash"}
    if run.get("candidate_run_hash") != hash_payload(commitment):
        raise ValueError("clarification_contrastive_run_hash_invalid")
    if run.get("runtime_version") != RUNTIME_VERSION or run.get("source_artifact_hash") != corpus_artifact["artifact_hash"]:
        raise ValueError("clarification_contrastive_run_binding_invalid")
    if set(run.get("lanes", {})) != set(LANES) or set(run.get("role_bindings", {})) != set(LANES):
        raise ValueError("clarification_contrastive_run_lanes_invalid")
    if run.get("private_oracle_available_at_prediction_time") is not False or run.get("action_policy_evaluated") is not False or run.get("ledger_available_at_prediction_time") is not False:
        raise ValueError("clarification_contrastive_prediction_boundary_invalid")
    if any(run.get(key) is not False for key in ("selection_authority", "retention_authority", "production_authority")):
        raise ValueError("clarification_contrastive_authority_invalid")
    batches = {batch["batch_id"]: batch for batch in corpus_artifact["public_surface"]["batches"]}
    evidence_refs = (*tuple(corpus_artifact["evidence_refs"]), f"artifact://{corpus_artifact['artifact_hash']}")
    for lane in LANES:
        records = run["lanes"][lane]
        if len(records.get("judgments", [])) + len(records.get("failures", [])) != len(batches):
            raise ValueError("clarification_contrastive_batch_coverage_invalid")
        for judgment in records.get("judgments", []):
            if judgment.get("batch_id") not in batches:
                raise ValueError("clarification_contrastive_batch_binding_invalid")
            _validate_payload(lane, judgment.get("payload"), batches[judgment["batch_id"]], evidence_refs)
    if run.get("predictions") != _build_predictions(corpus_artifact, run["lanes"]):
        raise ValueError("clarification_contrastive_predictions_invalid")


def _validate_payload(lane, payload, batch, evidence_refs):
    case_ids = tuple(case["blind_case_id"] for case in batch["public_cases"])
    if lane == CATEGORY_LANE:
        validate_fingerprint(payload, batch_id=batch["batch_id"], case_ids=case_ids, evidence_refs=evidence_refs)
    else:
        validate_selection(payload, batch_id=batch["batch_id"], public_cases=batch["public_cases"], evidence_refs=evidence_refs)


def _build_predictions(corpus, lanes):
    category_items = _index(lanes[CATEGORY_LANE]["judgments"])
    selection_items = _index(lanes[SELECTION_LANE]["judgments"])
    rows = []
    for blind_id in sorted(corpus["private_oracle"]["bindings"]):
        baseline = category_items.get(blind_id, {})
        selection = selection_items.get(blind_id, {})
        explicit_selection = selection.get("explicit_selection", "UNCERTAIN")
        rows.append({
            "blind_case_id": blind_id,
            "category_fingerprint": baseline.get("fingerprint", "UNCERTAIN"),
            "request_selection": explicit_selection,
            "selection_derived_category": selection_to_category(explicit_selection),
            "selection_quote_bound": bool(selection),
        })
    return rows


def _index(judgments):
    return {
        item["blind_case_id"]: item
        for judgment in judgments
        for item in judgment["payload"]["assessments"]
    }


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
