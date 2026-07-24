"""Provider orchestration for conditional precision-confirmed vetoes."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .negative_evidence_audit_contracts import (
    AUDIT_VERSION,
    FABRICATION_AUDIT,
    LIVE_AMBIGUITY_AUDIT,
    TASK_KINDS,
    specialist_audit_schema,
    validate_specialist_audit,
)
from .negative_evidence_precision_contracts import (
    CONFIRMATION_TASK_KIND,
    CONFIRMATION_VERSION,
    confirmation_schema,
    validate_confirmation,
)
from .negative_evidence_precision_fusion import (
    FABRICATION,
    FUSION_VERSION,
    LANES,
    LIVE_AMBIGUITY,
    MONOLITHIC_LANES,
    PRIMARY_LANES,
    VETO_CONFIRMATION,
    build_precision_fusion,
    confirmation_target_ids,
)
from .negative_evidence_precision_holdout import (
    EVIDENCE_REFS,
    validate_precision_corpus_artifact,
)
from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import (
    JUDGE_CRITERIA,
    JUDGE_STATES,
    JUDGE_TASK_KIND,
    RUBRIC,
    semantic_judge_schema,
    validate_semantic_judgment,
)


RUNTIME_VERSION = "negative_evidence_precision_runtime_v0_3_1"


class NegativeEvidencePrecisionRuntime:
    def __init__(self, *, corpus_artifact):
        validate_precision_corpus_artifact(corpus_artifact)
        self.corpus_artifact = corpus_artifact
        self.surface = corpus_artifact["blind_surface"]
        self.evidence_refs = (*EVIDENCE_REFS, f"artifact://{corpus_artifact['artifact_hash']}")

    def evaluate(self, *, experiment_id, adapters):
        if set(adapters) != set(LANES):
            raise ValueError("negative_precision_adapter_surface_invalid")
        if len({adapter.profile.provider_id for adapter in adapters.values()}) != len(LANES):
            raise ValueError("negative_precision_context_identity_not_isolated")
        lanes = {
            lane: {
                "judgments": [], "failures": [], "skipped_batches": [],
                "provider_calls": 0, "input_tokens": 0, "output_tokens": 0,
            }
            for lane in LANES
        }
        for batch in self.surface["batches"]:
            for lane in PRIMARY_LANES:
                self._execute(
                    experiment_id=experiment_id, lane=lane,
                    adapter=adapters[lane], batch=batch, lanes=lanes,
                )
        targets = confirmation_target_ids(lanes)
        for batch in self.surface["batches"]:
            candidates = [
                item for item in batch["public_candidates"]
                if item["blind_candidate_id"] in targets
            ]
            if not candidates:
                lanes[VETO_CONFIRMATION]["skipped_batches"].append({
                    "batch_id": batch["batch_id"],
                    "reason": "NO_ELIGIBLE_LIVE_VETO",
                    "candidate_ids": [],
                })
                continue
            self._execute(
                experiment_id=experiment_id, lane=VETO_CONFIRMATION,
                adapter=adapters[VETO_CONFIRMATION],
                batch={"batch_id": batch["batch_id"], "public_candidates": candidates},
                lanes=lanes,
            )
        fusion = build_precision_fusion(corpus_artifact=self.corpus_artifact, lanes=lanes)
        commitment = {
            "runtime_version": RUNTIME_VERSION,
            "fusion_version": FUSION_VERSION,
            "experiment_id": experiment_id,
            "blind_surface_hash": self.surface["surface_hash"],
            "source_artifact_hash": self.corpus_artifact["artifact_hash"],
            "role_bindings": {
                lane: {
                    "provider_id": adapter.profile.provider_id,
                    "model_id": adapter.profile.model_id,
                    "task_kind": _task_kind(lane),
                    "context_scope": f"ISOLATED::{lane}",
                }
                for lane, adapter in adapters.items()
            },
            "lanes": lanes,
            "fusion": fusion,
            "total_unique_provider_calls": sum(item["provider_calls"] for item in lanes.values()),
            "total_unique_input_tokens": sum(item["input_tokens"] for item in lanes.values()),
            "total_unique_output_tokens": sum(item["output_tokens"] for item in lanes.values()),
            "current_reference_labels_available_at_prediction_time": False,
            "predecessor_v0_2_diagnostics_used_for_architecture": True,
            "predecessor_examples_exposed_to_providers": False,
            "post_current_reference_adaptation_allowed": False,
            "specialists_can_promote_baseline": False,
            "confirmation_can_only_restore_baseline": True,
            "selection_authority": False,
            "retention_authority": False,
            "production_authority": False,
        }
        return {**commitment, "candidate_run_hash": hash_payload(commitment)}

    def _execute(self, *, experiment_id, lane, adapter, batch, lanes):
        task = self._task(experiment_id, lane, adapter, batch)
        result, accounting = self._route(lane=lane, adapter=adapter, task=task, batch=batch)
        for key in ("provider_calls", "input_tokens", "output_tokens"):
            lanes[lane][key] += accounting[key]
        lanes[lane]["judgments" if result["ok"] else "failures"].append(result["record"])

    def _route(self, *, lane, adapter, task, batch):
        envelope = ProviderTaskRouter([adapter]).route(task)
        invocation = envelope.invocation_receipt.as_dict()
        usage = invocation.get("token_usage") or {}
        attempted = invocation.get("fallback_decision", {}).get("attempted_providers", [])
        accounting = {
            "provider_calls": max(1, int(usage.get("provider_calls") or len(attempted) or 1)),
            "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        }
        if envelope.status != "COMPLETED":
            return ({"ok": False, "record": {
                "batch_id": batch["batch_id"], "status": envelope.status,
                "candidate_ids": [
                    item["blind_candidate_id"] for item in batch["public_candidates"]
                ],
                "validation_errors": list(envelope.validation_errors),
                "invocation_receipt": invocation,
            }}, accounting)
        candidate_ids = tuple(item["blind_candidate_id"] for item in batch["public_candidates"])
        try:
            _validate_payload(lane, envelope.normalized_result, batch["batch_id"], candidate_ids, self.evidence_refs)
        except ValueError as exc:
            return ({"ok": False, "record": {
                "batch_id": batch["batch_id"], "status": "SEMANTIC_VALIDATION_FAILED",
                "candidate_ids": list(candidate_ids),
                "validation_errors": [str(exc)], "invocation_receipt": invocation,
                "payload_hash": hash_payload(envelope.normalized_result),
            }}, accounting)
        receipt = self._receipt(lane=lane, adapter=adapter, task=task, payload=envelope.normalized_result, invocation=invocation)
        return ({"ok": True, "record": {
            "batch_id": batch["batch_id"], "payload": envelope.normalized_result,
            "invocation_receipt": invocation, "receipt": receipt,
        }}, accounting)

    def _receipt(self, *, lane, adapter, task, payload, invocation):
        receipt_version = (
            "structure_packet_semantic_judge_v0_1" if lane in MONOLITHIC_LANES
            else CONFIRMATION_VERSION if lane == VETO_CONFIRMATION else AUDIT_VERSION
        )
        commitment = {
            "receipt_version": receipt_version,
            "lane": lane,
            "judge_provider_id": adapter.profile.provider_id,
            "judge_model_id": adapter.profile.model_id,
            "task_contract_hash": task.contract_hash(),
            "invocation_receipt_hash": invocation["receipt_hash"],
            "blind_surface_hash": self.surface["surface_hash"],
            "source_artifact_hash": self.surface["source_artifact_hash"],
            "candidate_ids": [item["blind_candidate_id"] for item in payload["assessments"]],
            "payload_hash": hash_payload(payload),
            "evidence_refs": list(task.allowed_evidence),
            "provider_backed": True,
            "provider_authority": False,
            "context_scope": f"ISOLATED::{lane}",
        }
        return {**commitment, "receipt_hash": hash_payload(commitment)}

    def _task(self, experiment_id, lane, adapter, batch):
        candidate_ids = tuple(item["blind_candidate_id"] for item in batch["public_candidates"])
        if lane in MONOLITHIC_LANES:
            objective = (
                "Independently assess each anonymous receipt against its public_prompt using "
                "all six criteria. PRESENT requires public support, ABSENT means failed, and "
                "UNCERTAIN must be preserved. Do not infer source identity or use prior labels. "
                "Return JSON only."
            )
            inputs = {
                "source_identity": "WITHHELD", "predecessor_labels": "WITHHELD_AND_FORBIDDEN",
                "current_reference_labels": "NOT_YET_AVAILABLE",
                "blind_candidates": batch["public_candidates"], "rubric": RUBRIC,
                "allowed_states": list(JUDGE_STATES), "required_criteria": list(JUDGE_CRITERIA),
            }
            schema = semantic_judge_schema(batch["batch_id"], candidate_ids)
        elif lane in {LIVE_AMBIGUITY, FABRICATION}:
            audit_kind = LIVE_AMBIGUITY_AUDIT if lane == LIVE_AMBIGUITY else FABRICATION_AUDIT
            objective = _specialist_objective(audit_kind)
            inputs = {
                "audit_kind": audit_kind, "source_identity": "WITHHELD",
                "predecessor_labels": "WITHHELD_AND_FORBIDDEN",
                "current_reference_labels": "NOT_YET_AVAILABLE",
                "blind_candidates": batch["public_candidates"],
                "allowed_states": ["PASS", "VETO", "UNCERTAIN"],
            }
            schema = specialist_audit_schema(batch["batch_id"], audit_kind, candidate_ids)
        else:
            objective = (
                "Independently decide whether a live-ambiguity veto is justified, without seeing "
                "the first auditor's state or rationale. Typical usage or a preferred default is "
                "not an explicit disambiguator. A clarifying question WOULD_DISCRIMINATE when an "
                "answer to it would select between valid rival objects; the question need not "
                "contain that answer. CONFIRM_VETO only when the prompt explicitly fixes the "
                "requested object, a rival is invalid/equivalent, or the question would not "
                "distinguish. REJECT_VETO only when both rivals remain genuinely open and the "
                "question would distinguish them. Quote an explicit disambiguator exactly when "
                "claiming EXPLICITLY_FIXED. Preserve UNCERTAIN. Return JSON only."
            )
            inputs = {
                "source_identity": "WITHHELD", "first_auditor_identity": "WITHHELD",
                "first_auditor_state_and_rationale": "WITHHELD_FOR_INDEPENDENCE",
                "predecessor_examples_and_labels": "WITHHELD_AND_FORBIDDEN",
                "current_reference_labels": "NOT_YET_AVAILABLE",
                "blind_candidates": batch["public_candidates"],
            }
            schema = confirmation_schema(batch["batch_id"], candidate_ids)
        return ProviderCognitiveTask(
            task_id=f"{experiment_id}-{adapter.profile.provider_id}-{batch['batch_id']}",
            task_kind=_task_kind(lane), objective=objective, inputs=inputs,
            allowed_evidence=list(self.evidence_refs), expected_schema=schema,
            timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
            failure_semantics="record_failed_lane_without_cross_lane_substitution",
        )


def validate_precision_candidate_run(run, *, corpus_artifact):
    validate_precision_corpus_artifact(corpus_artifact)
    commitment = {key: value for key, value in run.items() if key != "candidate_run_hash"}
    if (
        run.get("candidate_run_hash") != hash_payload(commitment)
        or run.get("runtime_version") != RUNTIME_VERSION
        or run.get("fusion_version") != FUSION_VERSION
        or run.get("source_artifact_hash") != corpus_artifact["artifact_hash"]
        or run.get("blind_surface_hash") != corpus_artifact["blind_surface"]["surface_hash"]
        or run.get("current_reference_labels_available_at_prediction_time") is not False
        or run.get("predecessor_v0_2_diagnostics_used_for_architecture") is not True
        or run.get("predecessor_examples_exposed_to_providers") is not False
        or run.get("post_current_reference_adaptation_allowed") is not False
        or run.get("specialists_can_promote_baseline") is not False
        or run.get("confirmation_can_only_restore_baseline") is not True
        or any(run.get(key) is not False for key in ("selection_authority", "retention_authority", "production_authority"))
    ):
        raise ValueError("negative_precision_candidate_binding_invalid")
    if set(run.get("lanes", {})) != set(LANES) or set(run.get("role_bindings", {})) != set(LANES):
        raise ValueError("negative_precision_lane_surface_invalid")
    batch_index = {batch["batch_id"]: batch for batch in corpus_artifact["blind_surface"]["batches"]}
    expected_batches = set(batch_index)
    evidence_refs = (*EVIDENCE_REFS, f"artifact://{corpus_artifact['artifact_hash']}")
    targets = confirmation_target_ids(run["lanes"])
    observed_confirmations = set()
    failed_confirmations = set()
    for lane in LANES:
        lane_record = run["lanes"][lane]
        binding = run["role_bindings"][lane]
        if binding.get("task_kind") != _task_kind(lane) or binding.get("context_scope") != f"ISOLATED::{lane}":
            raise ValueError("negative_precision_role_binding_invalid")
        items = (*lane_record["judgments"], *lane_record["failures"])
        if lane != VETO_CONFIRMATION and (
            len(items) != len(expected_batches) or {item["batch_id"] for item in items} != expected_batches
        ):
            raise ValueError("negative_precision_primary_lane_incomplete")
        for item in lane_record["judgments"]:
            source_batch = batch_index[item["batch_id"]]
            if lane == VETO_CONFIRMATION:
                candidate_ids = tuple(a["blind_candidate_id"] for a in item["payload"]["assessments"])
                if not set(candidate_ids).issubset(targets):
                    raise ValueError("negative_precision_confirmation_scope_invalid")
                observed_confirmations.update(candidate_ids)
            else:
                candidate_ids = tuple(a["blind_candidate_id"] for a in source_batch["public_candidates"])
            _validate_payload(lane, item["payload"], item["batch_id"], candidate_ids, evidence_refs)
            receipt = item["receipt"]
            receipt_commitment = {key: value for key, value in receipt.items() if key != "receipt_hash"}
            if (
                receipt.get("receipt_hash") != hash_payload(receipt_commitment)
                or receipt.get("lane") != lane
                or receipt.get("payload_hash") != hash_payload(item["payload"])
                or receipt.get("invocation_receipt_hash") != item["invocation_receipt"].get("receipt_hash")
                or receipt.get("candidate_ids") != list(candidate_ids)
                or receipt.get("judge_provider_id") != binding["provider_id"]
                or receipt.get("judge_model_id") != binding["model_id"]
                or receipt.get("provider_authority") is not False
            ):
                raise ValueError("negative_precision_receipt_invalid")
        if lane == VETO_CONFIRMATION:
            for item in lane_record["failures"]:
                candidate_ids = set(item.get("candidate_ids", []))
                if not candidate_ids or not candidate_ids.issubset(targets):
                    raise ValueError("negative_precision_confirmation_failure_scope_invalid")
                failed_confirmations.update(candidate_ids)
    if (
        observed_confirmations & failed_confirmations
        or observed_confirmations | failed_confirmations != targets
    ):
        raise ValueError("negative_precision_confirmation_coverage_invalid")
    expected_fusion = build_precision_fusion(corpus_artifact=corpus_artifact, lanes=run["lanes"])
    if run.get("fusion") != expected_fusion:
        raise ValueError("negative_precision_fusion_invalid")
    if (
        run.get("total_unique_provider_calls") != sum(item["provider_calls"] for item in run["lanes"].values())
        or run.get("total_unique_input_tokens") != sum(item["input_tokens"] for item in run["lanes"].values())
        or run.get("total_unique_output_tokens") != sum(item["output_tokens"] for item in run["lanes"].values())
    ):
        raise ValueError("negative_precision_accounting_invalid")


def _validate_payload(lane, payload, batch_id, candidate_ids, evidence_refs):
    if lane in MONOLITHIC_LANES:
        validate_semantic_judgment(payload, batch_id=batch_id, candidate_ids=candidate_ids, evidence_refs=evidence_refs)
    elif lane == VETO_CONFIRMATION:
        validate_confirmation(payload, batch_id=batch_id, candidate_ids=candidate_ids, evidence_refs=evidence_refs)
    else:
        audit_kind = LIVE_AMBIGUITY_AUDIT if lane == LIVE_AMBIGUITY else FABRICATION_AUDIT
        validate_specialist_audit(payload, batch_id=batch_id, audit_kind=audit_kind, candidate_ids=candidate_ids, evidence_refs=evidence_refs)


def _task_kind(lane):
    if lane in MONOLITHIC_LANES:
        return JUDGE_TASK_KIND
    if lane == LIVE_AMBIGUITY:
        return TASK_KINDS[LIVE_AMBIGUITY_AUDIT]
    if lane == FABRICATION:
        return TASK_KINDS[FABRICATION_AUDIT]
    return CONFIRMATION_TASK_KIND


def _specialist_objective(audit_kind):
    if audit_kind == LIVE_AMBIGUITY_AUDIT:
        focus = (
            "Audit only whether the prompt leaves a live requested-object split between the "
            "readings and whether an answer to the proposed clarifying question would select "
            "between them. VETO false choices, equivalent or irrelevant readings, or an object "
            "already fixed by explicit wording, units, or boundaries. A common default alone "
            "does not explicitly fix the object. Do not audit fabrication."
        )
    else:
        focus = (
            "Audit only whether every reading, distinction, and clarifier is grounded in the "
            "public prompt without an unstated adjustment, entity, event, coefficient, or "
            "boundary. Disclosed alternatives are allowed. Do not decide ambiguity."
        )
    return focus + " PASS when satisfied, VETO when failed, and preserve UNCERTAIN. Return JSON only."
