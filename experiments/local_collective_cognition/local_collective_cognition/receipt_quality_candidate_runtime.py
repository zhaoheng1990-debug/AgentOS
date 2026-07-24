"""Freeze candidate Provider receipt-quality judgments before panel labels exist."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .provider_telemetry import hash_payload
from .receipt_quality_calibration_corpus import (
    EVIDENCE_REFS,
    validate_receipt_quality_corpus_artifact,
)
from .structure_semantic_judge_contracts import (
    JUDGE_CRITERIA,
    JUDGE_STATES,
    JUDGE_TASK_KIND,
    RUBRIC,
    semantic_judge_schema,
    validate_semantic_judgment,
)
from .structure_semantic_judge_receipts import (
    build_judgment_receipt,
    validate_judge_run,
)


RUNTIME_VERSION = "receipt_quality_candidate_runtime_v0_1"


class ReceiptQualityCandidateRuntime:
    def __init__(self, *, corpus_artifact):
        validate_receipt_quality_corpus_artifact(corpus_artifact)
        self.corpus_artifact = corpus_artifact
        self.surface = corpus_artifact["blind_surface"]
        self.evidence_refs = (
            *EVIDENCE_REFS,
            f"artifact://{corpus_artifact['artifact_hash']}",
        )

    def evaluate(self, *, experiment_id, adapter):
        judgments, failures, calls = [], [], 0
        input_tokens = output_tokens = 0
        for batch in self.surface["batches"]:
            task = self._task(experiment_id, adapter, batch)
            envelope = ProviderTaskRouter([adapter]).route(task)
            invocation = envelope.invocation_receipt.as_dict()
            usage = invocation.get("token_usage") or {}
            attempted = invocation.get("fallback_decision", {}).get(
                "attempted_providers", []
            )
            calls += max(1, len(attempted))
            input_tokens += int(
                usage.get("prompt_tokens") or usage.get("input_tokens") or 0
            )
            output_tokens += int(
                usage.get("completion_tokens") or usage.get("output_tokens") or 0
            )
            candidate_ids = tuple(
                item["blind_candidate_id"] for item in batch["public_candidates"]
            )
            if envelope.status != "COMPLETED":
                failures.append({
                    "batch_id": batch["batch_id"],
                    "status": envelope.status,
                    "validation_errors": list(envelope.validation_errors),
                    "invocation_receipt": invocation,
                })
                continue
            try:
                validate_semantic_judgment(
                    envelope.normalized_result,
                    batch_id=batch["batch_id"],
                    candidate_ids=candidate_ids,
                    evidence_refs=self.evidence_refs,
                )
            except ValueError as exc:
                failures.append({
                    "batch_id": batch["batch_id"],
                    "status": "SEMANTIC_VALIDATION_FAILED",
                    "validation_errors": [str(exc)],
                    "invocation_receipt": invocation,
                    "payload_hash": hash_payload(envelope.normalized_result),
                })
                continue
            receipt = build_judgment_receipt(
                task=task,
                payload=envelope.normalized_result,
                invocation_receipt=invocation,
                surface=self.surface,
                adapter=adapter,
            )
            judgments.append({
                "batch_id": batch["batch_id"],
                "provider_input": task.inputs,
                "payload": envelope.normalized_result,
                "invocation_receipt": invocation,
                "receipt": receipt,
            })
        commitment = {
            "runtime_version": RUNTIME_VERSION,
            "experiment_id": experiment_id,
            "judge_provider_id": adapter.profile.provider_id,
            "judge_model_id": adapter.profile.model_id,
            "blind_surface_hash": self.surface["surface_hash"],
            "source_artifact_hash": self.corpus_artifact["artifact_hash"],
            "successful_batches": len(judgments),
            "failed_batches": len(failures),
            "judgments": judgments,
            "failures": failures,
            "total_provider_calls": calls,
            "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
            "panel_labels_available_at_prediction_time": False,
            "predecessor_labels_used_for_tuning": False,
            "selection_authority": False,
            "retention_authority": False,
        }
        return {**commitment, "judge_run_hash": hash_payload(commitment)}

    def _task(self, experiment_id, adapter, batch):
        candidate_ids = tuple(
            item["blind_candidate_id"] for item in batch["public_candidates"]
        )
        return ProviderCognitiveTask(
            task_id=f"{experiment_id}-{adapter.profile.provider_id}-{batch['batch_id']}",
            task_kind=JUDGE_TASK_KIND,
            objective=(
                "Assess the anonymous ambiguity-discovery receipt against the public prompt. "
                "Evaluate all six frozen receipt-quality criteria independently. PRESENT means "
                "the displayed prompt and packet support the criterion; ABSENT means they contradict "
                "or fail it; preserve UNCERTAIN when the packet is insufficient. Do not decide the "
                "task's final ambiguity label, compare candidates, infer source identity, solve the "
                "numeric task, or use confidence and verbosity as quality evidence. Keep audit_note "
                "under 40 words and emit no text outside the JSON contract."
            ),
            inputs={
                "source_identity": "WITHHELD",
                "predecessor_labels": "WITHHELD_AND_FORBIDDEN",
                "panel_reference_labels": "NOT_YET_AVAILABLE",
                "public_prompt": batch["public_prompt"],
                "blind_candidates": batch["public_candidates"],
                "rubric": RUBRIC,
                "allowed_states": list(JUDGE_STATES),
                "required_criteria": list(JUDGE_CRITERIA),
            },
            allowed_evidence=list(self.evidence_refs),
            expected_schema=semantic_judge_schema(batch["batch_id"], candidate_ids),
            timeout_seconds=min(180, adapter.profile.max_timeout_seconds),
            failure_semantics=(
                "record_unresolved_receipt_quality_batch_without_retry_or_local_substitution"
            ),
        )


def validate_receipt_quality_candidate_run(run, *, corpus_artifact):
    validate_receipt_quality_corpus_artifact(corpus_artifact)
    commitment = {key: value for key, value in run.items() if key != "judge_run_hash"}
    if (
        run.get("judge_run_hash") != hash_payload(commitment)
        or run.get("runtime_version") != RUNTIME_VERSION
        or run.get("source_artifact_hash") != corpus_artifact["artifact_hash"]
        or run.get("panel_labels_available_at_prediction_time") is not False
        or run.get("predecessor_labels_used_for_tuning") is not False
    ):
        raise ValueError("receipt_quality_candidate_run_binding_invalid")
    validate_judge_run(run, surface=corpus_artifact["blind_surface"])
    expected_batches = {
        batch["batch_id"] for batch in corpus_artifact["blind_surface"]["batches"]
    }
    observed = {
        item["batch_id"] for item in (*run["judgments"], *run["failures"])
    }
    if observed != expected_batches:
        raise ValueError("receipt_quality_candidate_run_surface_incomplete")
