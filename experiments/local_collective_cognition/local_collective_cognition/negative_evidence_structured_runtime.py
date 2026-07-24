"""Provider orchestration for v0.4 structured semantic defer."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .negative_evidence_audit_contracts import AUDIT_VERSION, FABRICATION_AUDIT, LIVE_AMBIGUITY_AUDIT, TASK_KINDS, specialist_audit_schema, validate_specialist_audit
from .negative_evidence_structured_contracts import STRUCTURED_LIVE_TASK_KIND, STRUCTURED_LIVE_VERSION, structured_live_schema, validate_structured_live
from .negative_evidence_structured_fusion import FABRICATION, FUSION_VERSION, LANES, LEGACY_LIVE, MONOLITHIC_LANES, STRUCTURED_LIVE, build_structured_fusion
from .negative_evidence_structured_holdout import EVIDENCE_REFS, validate_structured_corpus_artifact
from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_STATES, JUDGE_TASK_KIND, RUBRIC, semantic_judge_schema, validate_semantic_judgment


RUNTIME_VERSION = "negative_evidence_structured_runtime_v0_4"


class NegativeEvidenceStructuredRuntime:
    def __init__(self, *, corpus_artifact):
        validate_structured_corpus_artifact(corpus_artifact)
        self.corpus_artifact = corpus_artifact
        self.surface = corpus_artifact["blind_surface"]
        self.evidence_refs = (*EVIDENCE_REFS, f"artifact://{corpus_artifact['artifact_hash']}")

    def evaluate(self, *, experiment_id, adapters):
        if set(adapters) != set(LANES):
            raise ValueError("negative_structured_adapter_surface_invalid")
        if len({adapter.profile.provider_id for adapter in adapters.values()}) != len(LANES):
            raise ValueError("negative_structured_context_identity_not_isolated")
        lanes = {lane: {"judgments": [], "failures": [], "provider_calls": 0, "input_tokens": 0, "output_tokens": 0} for lane in LANES}
        for batch in self.surface["batches"]:
            for lane in LANES:
                adapter = adapters[lane]
                task = self._task(experiment_id, lane, adapter, batch)
                result, accounting = self._route(lane, adapter, task, batch)
                for key in ("provider_calls", "input_tokens", "output_tokens"):
                    lanes[lane][key] += accounting[key]
                lanes[lane]["judgments" if result["ok"] else "failures"].append(result["record"])
        fusion = build_structured_fusion(corpus_artifact=self.corpus_artifact, lanes=lanes)
        commitment = {
            "runtime_version": RUNTIME_VERSION, "fusion_version": FUSION_VERSION,
            "experiment_id": experiment_id, "blind_surface_hash": self.surface["surface_hash"],
            "source_artifact_hash": self.corpus_artifact["artifact_hash"],
            "role_bindings": {
                lane: {"provider_id": adapter.profile.provider_id, "model_id": adapter.profile.model_id, "task_kind": _task_kind(lane), "context_scope": f"ISOLATED::{lane}"}
                for lane, adapter in adapters.items()
            },
            "lanes": lanes, "fusion": fusion,
            "total_unique_provider_calls": sum(x["provider_calls"] for x in lanes.values()),
            "total_unique_input_tokens": sum(x["input_tokens"] for x in lanes.values()),
            "total_unique_output_tokens": sum(x["output_tokens"] for x in lanes.values()),
            "current_reference_labels_available_at_prediction_time": False,
            "predecessor_diagnostics_used_for_architecture": True,
            "predecessor_examples_exposed_to_providers": False,
            "post_current_reference_adaptation_allowed": False,
            "provider_emits_final_structured_state": False,
            "specialists_can_promote_baseline": False,
            "selection_authority": False, "retention_authority": False, "production_authority": False,
        }
        return {**commitment, "candidate_run_hash": hash_payload(commitment)}

    def _route(self, lane, adapter, task, batch):
        envelope = ProviderTaskRouter([adapter]).route(task)
        invocation = envelope.invocation_receipt.as_dict()
        usage = invocation.get("token_usage") or {}
        accounting = {
            "provider_calls": max(1, int(usage.get("provider_calls") or 1)),
            "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        }
        candidate_ids = tuple(x["blind_candidate_id"] for x in batch["public_candidates"])
        if envelope.status != "COMPLETED":
            return ({"ok": False, "record": {"batch_id": batch["batch_id"], "candidate_ids": list(candidate_ids), "status": envelope.status, "validation_errors": list(envelope.validation_errors), "invocation_receipt": invocation}}, accounting)
        try:
            _validate_payload(lane, envelope.normalized_result, batch["batch_id"], candidate_ids, self.evidence_refs)
        except ValueError as exc:
            return ({"ok": False, "record": {"batch_id": batch["batch_id"], "candidate_ids": list(candidate_ids), "status": "SEMANTIC_VALIDATION_FAILED", "validation_errors": [str(exc)], "invocation_receipt": invocation, "payload_hash": hash_payload(envelope.normalized_result)}}, accounting)
        commitment = {
            "receipt_version": "structure_packet_semantic_judge_v0_1" if lane in MONOLITHIC_LANES else STRUCTURED_LIVE_VERSION if lane == STRUCTURED_LIVE else AUDIT_VERSION,
            "lane": lane, "judge_provider_id": adapter.profile.provider_id, "judge_model_id": adapter.profile.model_id,
            "task_contract_hash": task.contract_hash(), "invocation_receipt_hash": invocation["receipt_hash"],
            "blind_surface_hash": self.surface["surface_hash"], "source_artifact_hash": self.surface["source_artifact_hash"],
            "candidate_ids": list(candidate_ids), "payload_hash": hash_payload(envelope.normalized_result),
            "evidence_refs": list(task.allowed_evidence), "provider_backed": True,
            "provider_authority": False, "context_scope": f"ISOLATED::{lane}",
        }
        receipt = {**commitment, "receipt_hash": hash_payload(commitment)}
        return ({"ok": True, "record": {"batch_id": batch["batch_id"], "payload": envelope.normalized_result, "invocation_receipt": invocation, "receipt": receipt}}, accounting)

    def _task(self, experiment_id, lane, adapter, batch):
        ids = tuple(x["blind_candidate_id"] for x in batch["public_candidates"])
        common = {"source_identity": "WITHHELD", "predecessor_labels": "WITHHELD_AND_FORBIDDEN", "current_reference_labels": "NOT_YET_AVAILABLE", "blind_candidates": batch["public_candidates"]}
        if lane in MONOLITHIC_LANES:
            objective = "Assess each anonymous receipt against all six criteria. Preserve uncertainty and return JSON only."
            inputs = {**common, "rubric": RUBRIC, "allowed_states": list(JUDGE_STATES), "required_criteria": list(JUDGE_CRITERIA)}
            schema = semantic_judge_schema(batch["batch_id"], ids)
        elif lane in {LEGACY_LIVE, FABRICATION}:
            kind = LIVE_AMBIGUITY_AUDIT if lane == LEGACY_LIVE else FABRICATION_AUDIT
            objective = _legacy_objective(kind)
            inputs = {**common, "audit_kind": kind, "allowed_states": ["PASS", "VETO", "UNCERTAIN"]}
            schema = specialist_audit_schema(batch["batch_id"], kind, ids)
        else:
            objective = (
                "Independently provide semantic subjudgments only; do not emit PASS or VETO. "
                "Decide whether explicit wording, requested units, statistic type, or time window fixes the requested object; "
                "whether both rivals are valid and structurally distinct; and whether an answer to the proposed question would select between them. "
                "A common default is not explicit fixation. A requested percentage, count, currency, unit, named statistic, or activity window is explicit when it excludes a rival. "
                "Quote the exact fixing phrase for EXPLICITLY_FIXED. Preserve UNCERTAIN. Return JSON only."
            )
            inputs = {**common, "runtime_state_rule": "WITHHELD_FROM_PROVIDER;_RUNTIME_DERIVES_STATE"}
            schema = structured_live_schema(batch["batch_id"], ids)
        return ProviderCognitiveTask(
            task_id=f"{experiment_id}-{adapter.profile.provider_id}-{batch['batch_id']}", task_kind=_task_kind(lane),
            objective=objective, inputs=inputs, allowed_evidence=list(self.evidence_refs), expected_schema=schema,
            timeout_seconds=min(600, adapter.profile.max_timeout_seconds), failure_semantics="record_failed_lane_without_substitution",
        )


def validate_structured_candidate_run(run, *, corpus_artifact):
    validate_structured_corpus_artifact(corpus_artifact)
    commitment = {key: value for key, value in run.items() if key != "candidate_run_hash"}
    if (
        run.get("candidate_run_hash") != hash_payload(commitment) or run.get("runtime_version") != RUNTIME_VERSION
        or run.get("fusion_version") != FUSION_VERSION or run.get("source_artifact_hash") != corpus_artifact["artifact_hash"]
        or run.get("blind_surface_hash") != corpus_artifact["blind_surface"]["surface_hash"]
        or run.get("current_reference_labels_available_at_prediction_time") is not False
        or run.get("provider_emits_final_structured_state") is not False
        or run.get("specialists_can_promote_baseline") is not False
        or any(run.get(key) is not False for key in ("selection_authority", "retention_authority", "production_authority"))
    ):
        raise ValueError("negative_structured_candidate_binding_invalid")
    if set(run.get("lanes", {})) != set(LANES) or set(run.get("role_bindings", {})) != set(LANES):
        raise ValueError("negative_structured_lane_surface_invalid")
    batches = {x["batch_id"]: x for x in corpus_artifact["blind_surface"]["batches"]}
    evidence_refs = (*EVIDENCE_REFS, f"artifact://{corpus_artifact['artifact_hash']}")
    for lane, lane_record in run["lanes"].items():
        items = (*lane_record["judgments"], *lane_record["failures"])
        if len(items) != len(batches) or {x["batch_id"] for x in items} != set(batches):
            raise ValueError("negative_structured_lane_incomplete")
        for item in lane_record["judgments"]:
            ids = tuple(x["blind_candidate_id"] for x in batches[item["batch_id"]]["public_candidates"])
            _validate_payload(lane, item["payload"], item["batch_id"], ids, evidence_refs)
            receipt = item["receipt"]
            rc = {key: value for key, value in receipt.items() if key != "receipt_hash"}
            binding = run["role_bindings"][lane]
            if receipt.get("receipt_hash") != hash_payload(rc) or receipt.get("payload_hash") != hash_payload(item["payload"]) or receipt.get("candidate_ids") != list(ids) or receipt.get("judge_provider_id") != binding["provider_id"]:
                raise ValueError("negative_structured_receipt_invalid")
    if run.get("fusion") != build_structured_fusion(corpus_artifact=corpus_artifact, lanes=run["lanes"]):
        raise ValueError("negative_structured_fusion_invalid")


def _validate_payload(lane, payload, batch_id, ids, refs):
    if lane in MONOLITHIC_LANES:
        validate_semantic_judgment(payload, batch_id=batch_id, candidate_ids=ids, evidence_refs=refs)
    elif lane == STRUCTURED_LIVE:
        validate_structured_live(payload, batch_id=batch_id, candidate_ids=ids, evidence_refs=refs)
    else:
        kind = LIVE_AMBIGUITY_AUDIT if lane == LEGACY_LIVE else FABRICATION_AUDIT
        validate_specialist_audit(payload, batch_id=batch_id, audit_kind=kind, candidate_ids=ids, evidence_refs=refs)


def _task_kind(lane):
    if lane in MONOLITHIC_LANES: return JUDGE_TASK_KIND
    if lane == STRUCTURED_LIVE: return STRUCTURED_LIVE_TASK_KIND
    return TASK_KINDS[LIVE_AMBIGUITY_AUDIT if lane == LEGACY_LIVE else FABRICATION_AUDIT]


def _legacy_objective(kind):
    if kind == LIVE_AMBIGUITY_AUDIT:
        return "Audit whether both rival requested objects remain live and whether an answer to the clarifying question would distinguish them. VETO explicit wording, units, statistic types, time windows, invalid/equivalent rivals, or ineffective questions. A common default alone is not explicit. Return JSON only."
    return "Audit only whether every reading and question is grounded without an unstated adjustment, entity, event, coefficient, or boundary. Return JSON only."
