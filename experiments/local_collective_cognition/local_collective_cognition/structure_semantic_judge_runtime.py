"""Run blinded semantic structure assessment through independent Providers."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .provider_telemetry import hash_payload
from .structure_elicitor_fresh_eval import validate_fresh_artifact
from .structure_semantic_judge_blinding import build_blind_surface, validate_blind_surface
from .structure_semantic_judge_contracts import (
    JUDGE_CRITERIA, JUDGE_STATES, JUDGE_TASK_KIND, RUBRIC,
    semantic_judge_schema, validate_semantic_judgment,
)
from .structure_semantic_judge_receipts import build_judgment_receipt


class StructureSemanticJudgeRuntime:
    def __init__(self, *, calibration_artifact, fresh_artifact):
        validate_fresh_artifact(fresh_artifact, calibration_artifact=calibration_artifact)
        self.fresh_artifact = fresh_artifact
        self.surface = build_blind_surface(fresh_artifact)
        validate_blind_surface(self.surface)
        self.evidence_refs = (f"artifact://{fresh_artifact['artifact_hash']}",)

    def evaluate_judge(self, *, experiment_id, adapter, batch_ids=()):
        judgments, failures = [], []
        total_calls = total_input = total_output = 0
        selected = set(batch_ids)
        known = {item["batch_id"] for item in self.surface["batches"]}
        if selected and not selected.issubset(known):
            raise ValueError("semantic_judge_recovery_batch_unknown")
        batches = [
            item for item in self.surface["batches"]
            if not selected or item["batch_id"] in selected
        ]
        for batch in batches:
            task = self._task(experiment_id, adapter, batch)
            envelope = ProviderTaskRouter([adapter]).route(task)
            invocation = envelope.invocation_receipt.as_dict()
            calls, input_tokens, output_tokens = _usage(invocation)
            total_calls += calls
            total_input += input_tokens
            total_output += output_tokens
            candidate_ids = tuple(
                item["blind_candidate_id"] for item in batch["public_candidates"]
            )
            if envelope.status != "COMPLETED":
                failures.append({
                    "batch_id": batch["batch_id"], "status": envelope.status,
                    "validation_errors": list(envelope.validation_errors),
                    "invocation_receipt": invocation,
                })
                continue
            try:
                validate_semantic_judgment(
                    envelope.normalized_result, batch_id=batch["batch_id"],
                    candidate_ids=candidate_ids, evidence_refs=self.evidence_refs,
                )
            except ValueError as exc:
                failures.append({
                    "batch_id": batch["batch_id"], "status": "SEMANTIC_VALIDATION_FAILED",
                    "validation_errors": [str(exc)], "invocation_receipt": invocation,
                    "payload_hash": hash_payload(envelope.normalized_result),
                })
                continue
            receipt = build_judgment_receipt(
                task=task, payload=envelope.normalized_result,
                invocation_receipt=invocation, surface=self.surface, adapter=adapter,
            )
            judgments.append({
                "batch_id": batch["batch_id"],
                "provider_input": task.inputs,
                "payload": envelope.normalized_result,
                "invocation_receipt": invocation,
                "receipt": receipt,
            })
        commitment = {
            "experiment_id": experiment_id,
            "judge_provider_id": adapter.profile.provider_id,
            "judge_model_id": adapter.profile.model_id,
            "blind_surface_hash": self.surface["surface_hash"],
            "source_artifact_hash": self.fresh_artifact["artifact_hash"],
            "successful_batches": len(judgments),
            "failed_batches": len(failures),
            "judgments": judgments,
            "failures": failures,
            "total_provider_calls": total_calls,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "requested_batch_ids": [item["batch_id"] for item in batches],
        }
        return {**commitment, "judge_run_hash": hash_payload(commitment)}

    def _task(self, experiment_id, adapter, batch):
        candidate_ids = tuple(item["blind_candidate_id"] for item in batch["public_candidates"])
        return ProviderCognitiveTask(
            task_id=f"{experiment_id}-{adapter.profile.provider_id}-{batch['batch_id']}",
            task_kind=JUDGE_TASK_KIND,
            objective=(
                "Assess every anonymous contrastive structure packet independently against the public prompt. "
                "Do not rank candidates, infer their source, solve the numeric task, or claim final authority. "
                "Keep each audit_note under 40 words and emit no reasoning outside the required JSON fields."
            ),
            inputs={
                "source_identity": "WITHHELD",
                "candidate_order": "HASH_RANDOMIZED",
                "public_prompt": batch["public_prompt"],
                "blind_candidates": batch["public_candidates"],
                "rubric": RUBRIC,
                "allowed_states": list(JUDGE_STATES),
                "required_criteria": list(JUDGE_CRITERIA),
            },
            allowed_evidence=list(self.evidence_refs),
            expected_schema=semantic_judge_schema(batch["batch_id"], candidate_ids),
            timeout_seconds=min(120, adapter.profile.max_timeout_seconds),
            failure_semantics="record_unresolved_semantic_batch_without_local_substitution",
        )


def _usage(invocation):
    usage = invocation.get("token_usage") or {}
    attempted = invocation.get("fallback_decision", {}).get("attempted_providers", [])
    calls = max(1, len(attempted)) if attempted else 0
    input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    return calls, input_tokens, output_tokens
