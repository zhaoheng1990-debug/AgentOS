"""Equal-call warrant baseline and semantic-basis candidate runtime v0.11."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .clarification_semantic_basis_contracts import (
    SEMANTIC_BASIS_TASK_KIND,
    SEMANTIC_BASIS_VERSION,
    derive_semantic_basis_decision,
    semantic_basis_schema,
    validate_semantic_basis,
)
from .clarification_semantic_basis_holdout import validate_semantic_basis_holdout_artifact
from .clarification_warrant_contracts import (
    WARRANT_TASK_KIND,
    WARRANT_VERSION,
    derive_warrant_decision,
    validate_warrant,
    warrant_schema,
)
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "clarification_semantic_basis_runtime_v0_11"
BASELINE_LANE = "BASELINE_V0_10_WARRANT"
SEMANTIC_BASIS_LANE = "SEMANTIC_BASIS_V0_11"
LANES = (BASELINE_LANE, SEMANTIC_BASIS_LANE)


class ClarificationSemanticBasisRuntime:
    def __init__(self, *, corpus_artifact):
        validate_semantic_basis_holdout_artifact(corpus_artifact)
        self.corpus = corpus_artifact
        self.surface = corpus_artifact["public_surface"]
        self.evidence_refs = (*tuple(corpus_artifact["evidence_refs"]), f"artifact://{corpus_artifact['artifact_hash']}")

    def evaluate(self, *, experiment_id, adapters):
        if set(adapters) != set(LANES) or len({adapter.profile.provider_id for adapter in adapters.values()}) != len(adapters):
            raise ValueError("clarification_semantic_basis_adapter_surface_invalid")
        lanes = {lane: {"judgments": [], "failures": [], "provider_calls": 0, "input_tokens": 0, "output_tokens": 0} for lane in LANES}
        for batch in self.surface["batches"]:
            for lane in LANES:
                adapter = adapters[lane]
                task = self._task(experiment_id, lane, adapter, batch)
                result, accounting = self._route(lane, adapter, task, batch)
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
                    "task_kind": WARRANT_TASK_KIND if lane == BASELINE_LANE else SEMANTIC_BASIS_TASK_KIND,
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
            "construction_labels_are_pre_panel_diagnostics_only": True,
            "runtime_executes_semantic_basis_policy": True,
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
                "Apply the frozen v0.10 warrant rubric. explicit_selection is what the prompt itself fixes; "
                "pragmatic_preference is the natural default if forced; assessment_status reports whether the "
                "distinction can be assessed. Classify warrant_type as EXACT_OBJECT_MENTION, EXPLICIT_DEFINITION, "
                "EXPLICIT_OPERATION, DEFAULT_COMPATIBILITY, or NO_EXPLICIT_WARRANT. Semantic fit without an exact, "
                "defined, or operational phrase is soft. Hard warrant_quote must be an exact prompt substring; "
                "soft warrant_quote must be NONE. Return JSON only."
            )
            schema, task_kind = warrant_schema(batch["batch_id"], case_ids), WARRANT_TASK_KIND
        else:
            objective = (
                "Assess four independent coordinates. selected_object is A or B only when the request semantically "
                "entails that object; otherwise NONE. selection_basis is LEXICAL_EXACT when the requested measure "
                "directly names the candidate, COMPOSITIONAL_ENTAILMENT when ordinary composition, synonymy, or "
                "reference fixes it without exact candidate wording, PRAGMATIC_DEFAULT when one candidate is only a "
                "contextual default, or NO_PREFERENCE when neither has a meaningful advantage. pragmatic_preference "
                "records the best soft default and may be NONE. axis_assessment_complete asks whether these judgments "
                "can be completed, not whether the task is open; a justified NONE is complete. For lexical or "
                "compositional entailment, entailment_evidence_quote must be an exact prompt substring. For soft "
                "bases it must be NONE. Return JSON only."
            )
            schema, task_kind = semantic_basis_schema(batch["batch_id"], case_ids), SEMANTIC_BASIS_TASK_KIND
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
            "receipt_version": WARRANT_VERSION if lane == BASELINE_LANE else SEMANTIC_BASIS_VERSION,
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


def validate_semantic_basis_run(run, *, corpus_artifact):
    validate_semantic_basis_holdout_artifact(corpus_artifact)
    commitment = {key: value for key, value in run.items() if key != "candidate_run_hash"}
    if run.get("candidate_run_hash") != hash_payload(commitment) or run.get("runtime_version") != RUNTIME_VERSION or run.get("source_artifact_hash") != corpus_artifact["artifact_hash"]:
        raise ValueError("clarification_semantic_basis_run_invalid")
    if set(run.get("lanes", {})) != set(LANES) or set(run.get("role_bindings", {})) != set(LANES):
        raise ValueError("clarification_semantic_basis_run_lanes_invalid")
    if run.get("private_oracle_available_at_prediction_time") is not False or run.get("construction_labels_are_pre_panel_diagnostics_only") is not True:
        raise ValueError("clarification_semantic_basis_prediction_boundary_invalid")
    if any(run.get(key) is not False for key in ("action_credit_authority", "selection_authority", "retention_authority", "production_authority")):
        raise ValueError("clarification_semantic_basis_authority_invalid")
    batches = {batch["batch_id"]: batch for batch in corpus_artifact["public_surface"]["batches"]}
    evidence_refs = (*tuple(corpus_artifact["evidence_refs"]), f"artifact://{corpus_artifact['artifact_hash']}")
    for lane in LANES:
        lane_result = run["lanes"][lane]
        if len(lane_result.get("judgments", [])) + len(lane_result.get("failures", [])) != len(batches):
            raise ValueError("clarification_semantic_basis_batch_coverage_invalid")
        for judgment in lane_result.get("judgments", []):
            batch = batches.get(judgment.get("batch_id"))
            if not batch:
                raise ValueError("clarification_semantic_basis_batch_binding_invalid")
            _validate_payload(lane, judgment.get("payload"), batch, evidence_refs)
    if run.get("predictions") != _build_predictions(corpus_artifact, run["lanes"]):
        raise ValueError("clarification_semantic_basis_predictions_invalid")


def _validate_payload(lane, payload, batch, evidence_refs):
    case_ids = tuple(case["blind_case_id"] for case in batch["public_cases"])
    if lane == BASELINE_LANE:
        validate_warrant(payload, batch_id=batch["batch_id"], public_cases=batch["public_cases"], evidence_refs=evidence_refs)
    else:
        validate_semantic_basis(payload, batch_id=batch["batch_id"], public_cases=batch["public_cases"], evidence_refs=evidence_refs)


def _build_predictions(corpus, lanes):
    baseline = _index(lanes[BASELINE_LANE]["judgments"])
    semantic = _index(lanes[SEMANTIC_BASIS_LANE]["judgments"])
    rows = []
    for blind_id in sorted(corpus["private_oracle"]["bindings"]):
        base = baseline.get(blind_id, {})
        base_selection = base.get("explicit_selection", "NONE")
        base_status = base.get("assessment_status", "UNRESOLVED")
        base_warrant = base.get("warrant_type", "NO_EXPLICIT_WARRANT")
        base_category, base_hard_selection, _ = derive_warrant_decision(base_selection, base_status, base_warrant)
        item = semantic.get(blind_id, {})
        selected = item.get("selected_object", "NONE")
        basis = item.get("selection_basis", "NO_PREFERENCE")
        complete = item.get("axis_assessment_complete", False)
        category, hard_selection, downgraded = derive_semantic_basis_decision(selected, basis, complete)
        rows.append({
            "blind_case_id": blind_id,
            "baseline_explicit_selection": base_selection,
            "baseline_assessment_status": base_status,
            "baseline_warrant_type": base_warrant,
            "baseline_derived_category": base_category,
            "baseline_hard_selection": base_hard_selection,
            "semantic_selected_object": selected,
            "semantic_selection_basis": basis,
            "semantic_pragmatic_preference": item.get("pragmatic_preference", "NONE"),
            "semantic_axis_assessment_complete": complete,
            "semantic_derived_category": category,
            "semantic_hard_selection": hard_selection,
            "soft_selection_downgraded": downgraded,
            "semantic_receipt_available": bool(item),
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
