"""Provider-backed split-auditor candidate runtime for fresh receipt evidence."""

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
from .negative_evidence_holdout import (
    EVIDENCE_REFS,
    validate_negative_evidence_corpus_artifact,
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


RUNTIME_VERSION = "negative_evidence_candidate_runtime_v0_1"
FUSION_VERSION = "negative_evidence_mechanical_veto_fusion_v0_1"


class NegativeEvidenceCandidateRuntime:
    def __init__(self, *, corpus_artifact):
        validate_negative_evidence_corpus_artifact(corpus_artifact)
        self.corpus_artifact = corpus_artifact
        self.surface = corpus_artifact["blind_surface"]
        self.evidence_refs = (
            *EVIDENCE_REFS,
            f"artifact://{corpus_artifact['artifact_hash']}",
        )

    def evaluate(self, *, experiment_id, baseline_adapter, live_adapter,
                 fabrication_adapter):
        adapters = {
            "BASELINE": baseline_adapter,
            LIVE_AMBIGUITY_AUDIT: live_adapter,
            FABRICATION_AUDIT: fabrication_adapter,
        }
        if len({adapter.profile.provider_id for adapter in adapters.values()}) != 3:
            raise ValueError("negative_evidence_role_context_identity_not_isolated")
        lanes = {
            name: {
                "judgments": [], "failures": [], "provider_calls": 0,
                "input_tokens": 0, "output_tokens": 0,
            }
            for name in adapters
        }
        calls = input_tokens = output_tokens = 0
        for batch in self.surface["batches"]:
            for lane, adapter in adapters.items():
                task = (
                    self._baseline_task(experiment_id, adapter, batch)
                    if lane == "BASELINE"
                    else self._specialist_task(experiment_id, adapter, batch, lane)
                )
                result, usage = self._route(
                    lane=lane, adapter=adapter, task=task, batch=batch,
                )
                calls += usage["calls"]
                input_tokens += usage["input_tokens"]
                output_tokens += usage["output_tokens"]
                lanes[lane]["provider_calls"] += usage["calls"]
                lanes[lane]["input_tokens"] += usage["input_tokens"]
                lanes[lane]["output_tokens"] += usage["output_tokens"]
                lanes[lane]["judgments" if result["ok"] else "failures"].append(
                    result["record"]
                )
        fusion = self._build_fusion(lanes)
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
                    "task_kind": (
                        JUDGE_TASK_KIND if lane == "BASELINE" else TASK_KINDS[lane]
                    ),
                    "context_scope": f"ISOLATED::{lane}",
                }
                for lane, adapter in adapters.items()
            },
            "lanes": lanes,
            "fusion": fusion,
            "total_provider_calls": calls,
            "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
            "panel_labels_available_at_prediction_time": False,
            "predecessor_labels_used_for_tuning": False,
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
            "calls": max(1, len(attempted)),
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
            if lane == "BASELINE":
                validate_semantic_judgment(
                    envelope.normalized_result,
                    batch_id=batch["batch_id"],
                    candidate_ids=candidate_ids,
                    evidence_refs=self.evidence_refs,
                )
            else:
                validate_specialist_audit(
                    envelope.normalized_result,
                    batch_id=batch["batch_id"],
                    audit_kind=lane,
                    candidate_ids=candidate_ids,
                    evidence_refs=self.evidence_refs,
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
                if lane == "BASELINE" else AUDIT_VERSION
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

    def _build_fusion(self, lanes):
        baseline = _baseline_states(lanes["BASELINE"]["judgments"])
        live = _specialist_states(lanes[LIVE_AMBIGUITY_AUDIT]["judgments"])
        fabrication = _specialist_states(
            lanes[FABRICATION_AUDIT]["judgments"]
        )
        records = []
        for blind_id in sorted(self.surface["bindings"]):
            baseline_state = baseline.get(blind_id, "MISSING")
            live_state = live.get(blind_id, "MISSING")
            fabrication_state = fabrication.get(blind_id, "MISSING")
            fused_state = _fuse_packet_state(
                baseline_state, live_state, fabrication_state,
            )
            records.append({
                "blind_candidate_id": blind_id,
                "baseline_packet_state": baseline_state,
                "live_ambiguity_audit_state": live_state,
                "fabrication_audit_state": fabrication_state,
                "fused_packet_state": fused_state,
                "mechanical_rule": (
                    "BASELINE_CAN_ONLY_BE_DOWNGRADED_BY_SPECIALIST_VETO"
                ),
            })
        commitment = {
            "fusion_version": FUSION_VERSION,
            "records": records,
            "specialists_can_promote_baseline": False,
            "provider_semantic_input": True,
            "kernel_mechanical_fusion": True,
        }
        return {**commitment, "fusion_hash": hash_payload(commitment)}

    def _baseline_task(self, experiment_id, adapter, batch):
        candidate_ids = tuple(
            item["blind_candidate_id"] for item in batch["public_candidates"]
        )
        return ProviderCognitiveTask(
            task_id=(
                f"{experiment_id}-{adapter.profile.provider_id}-{batch['batch_id']}"
            ),
            task_kind=JUDGE_TASK_KIND,
            objective=(
                "Assess each anonymous receipt against its own public_prompt. Evaluate all "
                "six criteria independently. PRESENT requires public support; ABSENT means "
                "contradicted or failed; preserve UNCERTAIN. Do not infer source identity, "
                "use predecessor labels, or emit text outside JSON."
            ),
            inputs={
                "source_identity": "WITHHELD",
                "predecessor_labels": "WITHHELD_AND_FORBIDDEN",
                "panel_reference_labels": "NOT_YET_AVAILABLE",
                "blind_candidates": batch["public_candidates"],
                "rubric": RUBRIC,
                "allowed_states": list(JUDGE_STATES),
                "required_criteria": list(JUDGE_CRITERIA),
            },
            allowed_evidence=list(self.evidence_refs),
            expected_schema=semantic_judge_schema(batch["batch_id"], candidate_ids),
            timeout_seconds=min(180, adapter.profile.max_timeout_seconds),
            failure_semantics="record_failed_baseline_without_retry_or_substitution",
        )

    def _specialist_task(self, experiment_id, adapter, batch, audit_kind):
        candidate_ids = tuple(
            item["blind_candidate_id"] for item in batch["public_candidates"]
        )
        if audit_kind == LIVE_AMBIGUITY_AUDIT:
            objective = (
                "Audit only whether the public prompt leaves a live requested-object "
                "underdetermination between the displayed rivals and whether the question "
                "would resolve that live split. PASS only when both rival meanings remain "
                "plausible under the prompt. VETO when wording, units, or boundaries already "
                "determine the object, a rival is irrelevant or equivalent, or the question "
                "manufactures a false choice. Do not audit general factual fabrication."
            )
        else:
            objective = (
                "Audit only whether the packet avoids invented facts and avoids depending on "
                "solving the task. PASS when every rival, contrast, and question can be grounded "
                "in the public prompt without an unstated adjustment, entity, event, coefficient, "
                "or boundary. VETO when any such premise is introduced. Do not decide whether "
                "the requested object is ambiguous."
            )
        return ProviderCognitiveTask(
            task_id=(
                f"{experiment_id}-{adapter.profile.provider_id}-{batch['batch_id']}"
            ),
            task_kind=TASK_KINDS[audit_kind],
            objective=(
                objective
                + " Preserve UNCERTAIN. evidence_basis must cite only supplied text; "
                  "counterfactual must name the minimal fact or wording that would flip the "
                  "decision. Return JSON only."
            ),
            inputs={
                "audit_kind": audit_kind,
                "source_identity": "WITHHELD",
                "predecessor_labels": "WITHHELD_AND_FORBIDDEN",
                "panel_reference_labels": "NOT_YET_AVAILABLE",
                "blind_candidates": batch["public_candidates"],
                "allowed_states": ["PASS", "VETO", "UNCERTAIN"],
            },
            allowed_evidence=list(self.evidence_refs),
            expected_schema=specialist_audit_schema(
                batch["batch_id"], audit_kind, candidate_ids,
            ),
            timeout_seconds=min(180, adapter.profile.max_timeout_seconds),
            failure_semantics=(
                "record_failed_specialist_without_retry_or_local_substitution"
            ),
        )


def validate_negative_evidence_candidate_run(run, *, corpus_artifact):
    validate_negative_evidence_corpus_artifact(corpus_artifact)
    commitment = {key: value for key, value in run.items() if key != "candidate_run_hash"}
    if (
        run.get("candidate_run_hash") != hash_payload(commitment)
        or run.get("runtime_version") != RUNTIME_VERSION
        or run.get("fusion_version") != FUSION_VERSION
        or run.get("blind_surface_hash")
        != corpus_artifact["blind_surface"]["surface_hash"]
        or run.get("source_artifact_hash") != corpus_artifact["artifact_hash"]
        or run.get("panel_labels_available_at_prediction_time") is not False
        or run.get("predecessor_labels_used_for_tuning") is not False
        or run.get("specialists_can_promote_baseline") is not False
        or run.get("selection_authority") is not False
        or run.get("retention_authority") is not False
        or run.get("production_authority") is not False
    ):
        raise ValueError("negative_evidence_candidate_run_binding_invalid")
    role_bindings = run.get("role_bindings", {})
    if (
        set(role_bindings) != {"BASELINE", LIVE_AMBIGUITY_AUDIT, FABRICATION_AUDIT}
        or set(run.get("lanes", {})) != set(role_bindings)
        or len({item.get("provider_id") for item in role_bindings.values()}) != 3
        or any(
            item.get("context_scope") != f"ISOLATED::{lane}"
            for lane, item in role_bindings.items()
        )
    ):
        raise ValueError("negative_evidence_role_bindings_invalid")
    expected_batches = {
        batch["batch_id"] for batch in corpus_artifact["blind_surface"]["batches"]
    }
    batch_index = {
        batch["batch_id"]: batch
        for batch in corpus_artifact["blind_surface"]["batches"]
    }
    for lane, lane_record in run["lanes"].items():
        lane_items = (*lane_record["judgments"], *lane_record["failures"])
        observed = {
            item["batch_id"]
            for item in lane_items
        }
        if observed != expected_batches or len(lane_items) != len(expected_batches):
            raise ValueError("negative_evidence_lane_surface_incomplete")
        for item in lane_record["judgments"]:
            batch = batch_index[item["batch_id"]]
            candidate_ids = tuple(
                candidate["blind_candidate_id"]
                for candidate in batch["public_candidates"]
            )
            if lane == "BASELINE":
                validate_semantic_judgment(
                    item["payload"], batch_id=batch["batch_id"],
                    candidate_ids=candidate_ids,
                    evidence_refs=(*EVIDENCE_REFS, f"artifact://{corpus_artifact['artifact_hash']}"),
                )
            else:
                validate_specialist_audit(
                    item["payload"], batch_id=batch["batch_id"], audit_kind=lane,
                    candidate_ids=candidate_ids,
                    evidence_refs=(*EVIDENCE_REFS, f"artifact://{corpus_artifact['artifact_hash']}"),
                )
            receipt = item["receipt"]
            receipt_commitment = {
                key: value for key, value in receipt.items() if key != "receipt_hash"
            }
            binding = role_bindings[lane]
            if (
                receipt.get("receipt_hash") != hash_payload(receipt_commitment)
                or receipt.get("lane") != lane
                or receipt.get("payload_hash") != hash_payload(item["payload"])
                or receipt.get("invocation_receipt_hash")
                != item["invocation_receipt"].get("receipt_hash")
                or receipt.get("blind_surface_hash")
                != corpus_artifact["blind_surface"]["surface_hash"]
                or receipt.get("source_artifact_hash")
                != corpus_artifact["blind_surface"]["source_artifact_hash"]
                or receipt.get("candidate_ids") != list(candidate_ids)
                or receipt.get("judge_provider_id") != binding["provider_id"]
                or receipt.get("judge_model_id") != binding["model_id"]
                or receipt.get("provider_authority") is not False
                or receipt.get("context_scope") != f"ISOLATED::{lane}"
            ):
                raise ValueError("negative_evidence_lane_receipt_invalid")
    if (
        run.get("total_provider_calls")
        != sum(lane["provider_calls"] for lane in run["lanes"].values())
        or run.get("total_input_tokens")
        != sum(lane["input_tokens"] for lane in run["lanes"].values())
        or run.get("total_output_tokens")
        != sum(lane["output_tokens"] for lane in run["lanes"].values())
    ):
        raise ValueError("negative_evidence_accounting_invalid")
    expected_fusion = _rebuild_fusion(run, corpus_artifact)
    if run.get("fusion") != expected_fusion:
        raise ValueError("negative_evidence_fusion_semantics_invalid")


def _rebuild_fusion(run, corpus_artifact):
    baseline = _baseline_states(run["lanes"]["BASELINE"]["judgments"])
    live = _specialist_states(
        run["lanes"][LIVE_AMBIGUITY_AUDIT]["judgments"]
    )
    fabrication = _specialist_states(
        run["lanes"][FABRICATION_AUDIT]["judgments"]
    )
    records = []
    for blind_id in sorted(corpus_artifact["blind_surface"]["bindings"]):
        baseline_state = baseline.get(blind_id, "MISSING")
        live_state = live.get(blind_id, "MISSING")
        fabrication_state = fabrication.get(blind_id, "MISSING")
        records.append({
            "blind_candidate_id": blind_id,
            "baseline_packet_state": baseline_state,
            "live_ambiguity_audit_state": live_state,
            "fabrication_audit_state": fabrication_state,
            "fused_packet_state": _fuse_packet_state(
                baseline_state, live_state, fabrication_state,
            ),
            "mechanical_rule": "BASELINE_CAN_ONLY_BE_DOWNGRADED_BY_SPECIALIST_VETO",
        })
    commitment = {
        "fusion_version": FUSION_VERSION,
        "records": records,
        "specialists_can_promote_baseline": False,
        "provider_semantic_input": True,
        "kernel_mechanical_fusion": True,
    }
    return {**commitment, "fusion_hash": hash_payload(commitment)}


def _baseline_states(judgments):
    states = {}
    for judgment in judgments:
        for assessment in judgment["payload"]["assessments"]:
            states[assessment["blind_candidate_id"]] = _packet_state(
                assessment["criteria"]
            )
    return states


def _specialist_states(judgments):
    states = {}
    for judgment in judgments:
        for assessment in judgment["payload"]["assessments"]:
            states[assessment["blind_candidate_id"]] = assessment["state"]
    return states


def _packet_state(criteria):
    if set(criteria) != set(JUDGE_CRITERIA):
        return "MISSING"
    states = set(criteria.values())
    if not states.issubset(set(JUDGE_STATES)):
        return "MISSING"
    if states == {"PRESENT"}:
        return "USABLE"
    if "ABSENT" in states:
        return "UNUSABLE"
    return "UNRESOLVED"


def _fuse_packet_state(baseline_state, live_state, fabrication_state):
    if baseline_state == "UNUSABLE":
        return "UNUSABLE"
    if "VETO" in {live_state, fabrication_state}:
        return "UNUSABLE"
    if baseline_state == "USABLE" and {live_state, fabrication_state} == {"PASS"}:
        return "USABLE"
    return "UNRESOLVED"
