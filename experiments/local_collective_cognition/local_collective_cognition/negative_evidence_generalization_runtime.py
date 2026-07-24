"""Provider orchestration for the four-arm negative-evidence holdout."""

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
from .negative_evidence_generalization_fusion import (
    BASELINE,
    FUSION_VERSION,
    HETEROGENEOUS_LIVE,
    LANES,
    MONOLITHIC_REPEAT_2,
    MONOLITHIC_REPEAT_3,
    SAME_MODEL_LIVE,
    SHARED_FABRICATION,
    build_four_arm_fusion,
)
from .negative_evidence_generalization_holdout import (
    EVIDENCE_REFS,
    validate_generalization_corpus_artifact,
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


RUNTIME_VERSION = "negative_evidence_generalization_runtime_v0_2"
MONOLITHIC_LANES = (BASELINE, MONOLITHIC_REPEAT_2, MONOLITHIC_REPEAT_3)
LIVE_LANES = (SAME_MODEL_LIVE, HETEROGENEOUS_LIVE)


class NegativeEvidenceGeneralizationRuntime:
    def __init__(self, *, corpus_artifact):
        validate_generalization_corpus_artifact(corpus_artifact)
        self.corpus_artifact = corpus_artifact
        self.surface = corpus_artifact["blind_surface"]
        self.evidence_refs = (
            *EVIDENCE_REFS,
            f"artifact://{corpus_artifact['artifact_hash']}",
        )

    def evaluate(self, *, experiment_id, adapters):
        if set(adapters) != set(LANES):
            raise ValueError("negative_generalization_adapter_surface_invalid")
        if len({adapter.profile.provider_id for adapter in adapters.values()}) != len(LANES):
            raise ValueError("negative_generalization_context_identity_not_isolated")
        lanes = {
            lane: {
                "judgments": [], "failures": [], "provider_calls": 0,
                "input_tokens": 0, "output_tokens": 0,
            }
            for lane in LANES
        }
        for batch in self.surface["batches"]:
            for lane in LANES:
                adapter = adapters[lane]
                task = self._task(experiment_id, lane, adapter, batch)
                result, accounting = self._route(
                    lane=lane, adapter=adapter, task=task, batch=batch,
                )
                for key in ("provider_calls", "input_tokens", "output_tokens"):
                    lanes[lane][key] += accounting[key]
                lanes[lane]["judgments" if result["ok"] else "failures"].append(
                    result["record"]
                )
        fusion = build_four_arm_fusion(
            corpus_artifact=self.corpus_artifact, lanes=lanes,
        )
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
            "total_unique_provider_calls": sum(
                item["provider_calls"] for item in lanes.values()
            ),
            "total_unique_input_tokens": sum(
                item["input_tokens"] for item in lanes.values()
            ),
            "total_unique_output_tokens": sum(
                item["output_tokens"] for item in lanes.values()
            ),
            "panel_labels_available_at_prediction_time": False,
            "predecessor_labels_used_for_tuning": False,
            "post_reference_adaptation_allowed": False,
            "specialists_can_promote_baseline": False,
            "selection_authority": False,
            "retention_authority": False,
            "production_authority": False,
        }
        return {**commitment, "candidate_run_hash": hash_payload(commitment)}

    def _route(self, *, lane, adapter, task, batch):
        envelope = ProviderTaskRouter([adapter]).route(task)
        invocation = envelope.invocation_receipt.as_dict()
        usage = invocation.get("token_usage") or {}
        attempted = invocation.get("fallback_decision", {}).get(
            "attempted_providers", []
        )
        accounting = {
            "provider_calls": max(1, int(
                usage.get("provider_calls") or len(attempted) or 1
            )),
            "input_tokens": int(
                usage.get("prompt_tokens") or usage.get("input_tokens") or 0
            ),
            "output_tokens": int(
                usage.get("completion_tokens") or usage.get("output_tokens") or 0
            ),
        }
        if envelope.status != "COMPLETED":
            return ({
                "ok": False,
                "record": {
                    "batch_id": batch["batch_id"],
                    "status": envelope.status,
                    "validation_errors": list(envelope.validation_errors),
                    "invocation_receipt": invocation,
                },
            }, accounting)
        candidate_ids = tuple(
            item["blind_candidate_id"] for item in batch["public_candidates"]
        )
        try:
            _validate_payload(
                lane, envelope.normalized_result, batch["batch_id"],
                candidate_ids, self.evidence_refs,
            )
        except ValueError as exc:
            return ({
                "ok": False,
                "record": {
                    "batch_id": batch["batch_id"],
                    "status": "SEMANTIC_VALIDATION_FAILED",
                    "validation_errors": [str(exc)],
                    "invocation_receipt": invocation,
                    "payload_hash": hash_payload(envelope.normalized_result),
                },
            }, accounting)
        receipt = self._receipt(
            lane=lane, adapter=adapter, task=task,
            payload=envelope.normalized_result, invocation=invocation,
        )
        return ({
            "ok": True,
            "record": {
                "batch_id": batch["batch_id"],
                "payload": envelope.normalized_result,
                "invocation_receipt": invocation,
                "receipt": receipt,
            },
        }, accounting)

    def _receipt(self, *, lane, adapter, task, payload, invocation):
        commitment = {
            "receipt_version": (
                "structure_packet_semantic_judge_v0_1"
                if lane in MONOLITHIC_LANES else AUDIT_VERSION
            ),
            "lane": lane,
            "judge_provider_id": adapter.profile.provider_id,
            "judge_model_id": adapter.profile.model_id,
            "task_contract_hash": task.contract_hash(),
            "invocation_receipt_hash": invocation["receipt_hash"],
            "blind_surface_hash": self.surface["surface_hash"],
            "source_artifact_hash": self.surface["source_artifact_hash"],
            "candidate_ids": [
                item["blind_candidate_id"] for item in payload["assessments"]
            ],
            "payload_hash": hash_payload(payload),
            "evidence_refs": list(task.allowed_evidence),
            "provider_backed": True,
            "provider_authority": False,
            "context_scope": f"ISOLATED::{lane}",
        }
        return {**commitment, "receipt_hash": hash_payload(commitment)}

    def _task(self, experiment_id, lane, adapter, batch):
        candidate_ids = tuple(
            item["blind_candidate_id"] for item in batch["public_candidates"]
        )
        if lane in MONOLITHIC_LANES:
            objective = (
                "Independently assess each anonymous receipt against its own public_prompt. "
                "Evaluate all six criteria. PRESENT requires public support, ABSENT means "
                "contradicted or failed, and UNCERTAIN must be preserved. Treat alternative "
                "packet formats as semantically equivalent. Do not infer source identity, use "
                "predecessor labels, compare candidates, or emit text outside JSON."
            )
            inputs = {
                "source_identity": "WITHHELD",
                "predecessor_labels": "WITHHELD_AND_FORBIDDEN",
                "panel_reference_labels": "NOT_YET_AVAILABLE",
                "blind_candidates": batch["public_candidates"],
                "rubric": RUBRIC,
                "allowed_states": list(JUDGE_STATES),
                "required_criteria": list(JUDGE_CRITERIA),
            }
            schema = semantic_judge_schema(batch["batch_id"], candidate_ids)
        else:
            audit_kind = (
                LIVE_AMBIGUITY_AUDIT if lane in LIVE_LANES
                else FABRICATION_AUDIT
            )
            objective = _specialist_objective(audit_kind)
            inputs = {
                "audit_kind": audit_kind,
                "source_identity": "WITHHELD",
                "predecessor_labels": "WITHHELD_AND_FORBIDDEN",
                "panel_reference_labels": "NOT_YET_AVAILABLE",
                "blind_candidates": batch["public_candidates"],
                "allowed_states": ["PASS", "VETO", "UNCERTAIN"],
            }
            schema = specialist_audit_schema(
                batch["batch_id"], audit_kind, candidate_ids,
            )
        return ProviderCognitiveTask(
            task_id=f"{experiment_id}-{adapter.profile.provider_id}-{batch['batch_id']}",
            task_kind=_task_kind(lane),
            objective=objective,
            inputs=inputs,
            allowed_evidence=list(self.evidence_refs),
            expected_schema=schema,
            timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
            failure_semantics="record_failed_lane_without_cross_lane_substitution",
        )


def validate_generalization_candidate_run(run, *, corpus_artifact):
    validate_generalization_corpus_artifact(corpus_artifact)
    commitment = {key: value for key, value in run.items() if key != "candidate_run_hash"}
    if (
        run.get("candidate_run_hash") != hash_payload(commitment)
        or run.get("runtime_version") != RUNTIME_VERSION
        or run.get("fusion_version") != FUSION_VERSION
        or run.get("source_artifact_hash") != corpus_artifact["artifact_hash"]
        or run.get("blind_surface_hash")
        != corpus_artifact["blind_surface"]["surface_hash"]
        or run.get("panel_labels_available_at_prediction_time") is not False
        or run.get("predecessor_labels_used_for_tuning") is not False
        or run.get("post_reference_adaptation_allowed") is not False
        or run.get("specialists_can_promote_baseline") is not False
        or any(run.get(key) is not False for key in (
            "selection_authority", "retention_authority", "production_authority",
        ))
    ):
        raise ValueError("negative_generalization_candidate_binding_invalid")
    if set(run.get("lanes", {})) != set(LANES) or set(run.get("role_bindings", {})) != set(LANES):
        raise ValueError("negative_generalization_lane_surface_invalid")
    expected_batches = {
        batch["batch_id"] for batch in corpus_artifact["blind_surface"]["batches"]
    }
    batch_index = {
        batch["batch_id"]: batch
        for batch in corpus_artifact["blind_surface"]["batches"]
    }
    evidence_refs = (*EVIDENCE_REFS, f"artifact://{corpus_artifact['artifact_hash']}")
    for lane in LANES:
        lane_record = run["lanes"][lane]
        items = (*lane_record["judgments"], *lane_record["failures"])
        if (
            len(items) != len(expected_batches)
            or {item["batch_id"] for item in items} != expected_batches
        ):
            raise ValueError("negative_generalization_lane_incomplete")
        binding = run["role_bindings"][lane]
        if (
            binding.get("task_kind") != _task_kind(lane)
            or binding.get("context_scope") != f"ISOLATED::{lane}"
        ):
            raise ValueError("negative_generalization_role_binding_invalid")
        for item in lane_record["judgments"]:
            batch = batch_index[item["batch_id"]]
            candidate_ids = tuple(
                candidate["blind_candidate_id"]
                for candidate in batch["public_candidates"]
            )
            _validate_payload(
                lane, item["payload"], batch["batch_id"], candidate_ids,
                evidence_refs,
            )
            receipt = item["receipt"]
            receipt_commitment = {
                key: value for key, value in receipt.items() if key != "receipt_hash"
            }
            if (
                receipt.get("receipt_hash") != hash_payload(receipt_commitment)
                or receipt.get("lane") != lane
                or receipt.get("payload_hash") != hash_payload(item["payload"])
                or receipt.get("invocation_receipt_hash")
                != item["invocation_receipt"].get("receipt_hash")
                or receipt.get("candidate_ids") != list(candidate_ids)
                or receipt.get("judge_provider_id") != binding["provider_id"]
                or receipt.get("judge_model_id") != binding["model_id"]
                or receipt.get("provider_authority") is not False
                or receipt.get("context_scope") != f"ISOLATED::{lane}"
            ):
                raise ValueError("negative_generalization_receipt_invalid")
    expected_fusion = build_four_arm_fusion(
        corpus_artifact=corpus_artifact, lanes=run["lanes"],
    )
    if run.get("fusion") != expected_fusion:
        raise ValueError("negative_generalization_fusion_invalid")
    if (
        run.get("total_unique_provider_calls")
        != sum(item["provider_calls"] for item in run["lanes"].values())
        or run.get("total_unique_input_tokens")
        != sum(item["input_tokens"] for item in run["lanes"].values())
        or run.get("total_unique_output_tokens")
        != sum(item["output_tokens"] for item in run["lanes"].values())
    ):
        raise ValueError("negative_generalization_accounting_invalid")


def _validate_payload(lane, payload, batch_id, candidate_ids, evidence_refs):
    if lane in MONOLITHIC_LANES:
        validate_semantic_judgment(
            payload, batch_id=batch_id, candidate_ids=candidate_ids,
            evidence_refs=evidence_refs,
        )
        return
    audit_kind = LIVE_AMBIGUITY_AUDIT if lane in LIVE_LANES else FABRICATION_AUDIT
    validate_specialist_audit(
        payload, batch_id=batch_id, audit_kind=audit_kind,
        candidate_ids=candidate_ids, evidence_refs=evidence_refs,
    )


def _task_kind(lane):
    if lane in MONOLITHIC_LANES:
        return JUDGE_TASK_KIND
    if lane in LIVE_LANES:
        return TASK_KINDS[LIVE_AMBIGUITY_AUDIT]
    return TASK_KINDS[FABRICATION_AUDIT]


def _specialist_objective(audit_kind):
    if audit_kind == LIVE_AMBIGUITY_AUDIT:
        focus = (
            "Audit only whether the prompt leaves a live requested-object split between "
            "the two readings and whether the proposed clarifier would resolve that split. "
            "VETO false choices, equivalent readings, irrelevant readings, or objects already "
            "fixed by explicit wording, units, or boundaries. Do not audit fabrication itself."
        )
    else:
        focus = (
            "Audit only whether every reading, distinction, and clarifier is grounded in the "
            "public prompt without an unstated adjustment, entity, event, coefficient, or "
            "boundary. Disclosed deductions and disclosed alternatives are allowed. Do not "
            "decide whether the requested object is ambiguous."
        )
    return (
        focus
        + " PASS only when this audit is satisfied, VETO when it fails, and preserve "
          "UNCERTAIN. evidence_basis must cite supplied text; counterfactual must name the "
          "minimal fact or wording that would flip the decision. Return JSON only."
    )
