"""Provider-backed coordinator with frozen materiality and receipt-quality controls."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .ambiguity_hard_null_contracts import (
    TASK_KIND,
    hard_null_coordinator_schema,
    validate_hard_null_coordinator_payload,
)
from .ambiguity_hard_null_holdout import (
    MATERIALITY_CONTROL,
    MATERIALITY_CONTROL_HASH,
    RECEIPT_QUALITY_CONTROL,
    RECEIPT_QUALITY_CONTROL_HASH,
)
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "ambiguity_hard_null_runtime_v0_1"


class HardNullAmbiguityCoordinatorRuntime:
    def __init__(self, *, surface, max_attempts_per_batch=1):
        if max_attempts_per_batch != 1:
            raise ValueError("hard_null_attempt_budget_frozen")
        if (
            surface.get("materiality_control_hash") != MATERIALITY_CONTROL_HASH
            or surface.get("receipt_quality_control_hash") != RECEIPT_QUALITY_CONTROL_HASH
        ):
            raise ValueError("hard_null_surface_control_binding_invalid")
        self.surface = surface
        self.max_attempts_per_batch = max_attempts_per_batch
        self.evidence_refs = (
            f"surface://{surface['surface_hash']}",
            f"control://{MATERIALITY_CONTROL_HASH}",
            f"control://{RECEIPT_QUALITY_CONTROL_HASH}",
        )

    def evaluate(self, *, experiment_id, adapter):
        judgments, failures, all_attempts = [], [], []
        for batch in self.surface["public_batches"]:
            item_ids = tuple(item["coordination_item_id"] for item in batch["items"])
            task = self._task(experiment_id, adapter, batch, item_ids)
            envelope = ProviderTaskRouter([adapter]).route(task)
            invocation = envelope.invocation_receipt.as_dict()
            attempt = {
                "attempt": 1,
                "status": envelope.status,
                "validation_errors": list(envelope.validation_errors),
                "invocation_receipt": invocation,
            }
            all_attempts.append(attempt)
            payload = None
            if envelope.status == "COMPLETED":
                try:
                    validate_hard_null_coordinator_payload(
                        envelope.normalized_result,
                        batch_id=batch["batch_id"],
                        item_ids=item_ids,
                        evidence_refs=self.evidence_refs,
                    )
                except ValueError as exc:
                    attempt["semantic_validation_error"] = str(exc)
                    attempt["payload_hash"] = hash_payload(envelope.normalized_result)
                else:
                    payload = envelope.normalized_result
            if payload is None:
                failures.append({"batch_id": batch["batch_id"], "attempts": [attempt]})
                continue
            commitment = {
                "batch_id": batch["batch_id"],
                "provider_input": task.inputs,
                "payload": payload,
                "attempts": [attempt],
            }
            judgments.append({**commitment, "judgment_hash": hash_payload(commitment)})

        calls, input_tokens, output_tokens = _aggregate_usage(all_attempts)
        profile_commitment = {
            "provider_id": adapter.profile.provider_id,
            "model_id": adapter.profile.model_id,
            "requested_batches": len(self.surface["public_batches"]),
            "successful_batches": len(judgments),
            "failed_batches": len(failures),
            "decision_count": sum(
                len(item["payload"]["decisions"]) for item in judgments
            ),
            "total_provider_calls": calls,
            "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "selection_authority": False,
            "retention_authority": False,
        }
        profile = {**profile_commitment, "profile_hash": hash_payload(profile_commitment)}
        commitment = {
            "runtime_version": RUNTIME_VERSION,
            "experiment_id": experiment_id,
            "surface_hash": self.surface["surface_hash"],
            "materiality_control_hash": MATERIALITY_CONTROL_HASH,
            "receipt_quality_control_hash": RECEIPT_QUALITY_CONTROL_HASH,
            "provider_id": adapter.profile.provider_id,
            "model_id": adapter.profile.model_id,
            "judgments": judgments,
            "failures": failures,
            "profile": profile,
        }
        return {**commitment, "coordinator_run_hash": hash_payload(commitment)}

    def _task(self, experiment_id, adapter, batch, item_ids):
        return ProviderCognitiveTask(
            task_id=(
                f"{experiment_id}-{adapter.profile.provider_id}-{batch['batch_id']}-a1"
            ),
            task_kind=TASK_KIND,
            objective=(
                "Act as an identity-blind semantic coordinator. Apply the frozen materiality and "
                "receipt-quality controls exactly. Material ambiguity exists only when two interpretations "
                "of the requested output object are both compatible with every explicit task constraint, "
                "are not paraphrases, and change the required operation, boundary, unit, or output. A unit, "
                "direction, boundary, operation, or other decisive qualifier makes the case "
                "NO_MATERIAL_AMBIGUITY. Assess each anonymous receipt independently. Mark "
                "USABLE_MATERIAL_SUPPORT only when its rivals are task-grounded, semantically distinct, "
                "and output-sensitive. Confidence, verbosity, position, agreement, and presumed model "
                "strength are not quality evidence. A positive final decision requires at least one usable "
                "material receipt. Return UNCERTAIN when the public task and usable receipts do not support "
                "a controlled decision. Do not solve the task or emit text outside the JSON contract."
            ),
            inputs={
                "source_identity": "WITHHELD",
                "prior_scores": "WITHHELD",
                "predecessor_labels": "WITHHELD_AND_FORBIDDEN",
                "hidden_truth": "WITHHELD",
                "position_order": "COUNTERBALANCED",
                "frozen_controls": {
                    "materiality": MATERIALITY_CONTROL,
                    "materiality_hash": MATERIALITY_CONTROL_HASH,
                    "receipt_quality": RECEIPT_QUALITY_CONTROL,
                    "receipt_quality_hash": RECEIPT_QUALITY_CONTROL_HASH,
                },
                "batch": batch,
            },
            allowed_evidence=list(self.evidence_refs),
            expected_schema=hard_null_coordinator_schema(
                batch["batch_id"], item_ids, self.evidence_refs,
            ),
            timeout_seconds=min(240, adapter.profile.max_timeout_seconds),
            failure_semantics=(
                "preserve_unresolved_batch_without_retry_or_local_semantic_substitution"
            ),
        )


def validate_hard_null_coordinator_run(run, *, surface):
    commitment = {key: value for key, value in run.items() if key != "coordinator_run_hash"}
    if (
        run.get("coordinator_run_hash") != hash_payload(commitment)
        or run.get("surface_hash") != surface["surface_hash"]
        or run.get("materiality_control_hash") != MATERIALITY_CONTROL_HASH
        or run.get("receipt_quality_control_hash") != RECEIPT_QUALITY_CONTROL_HASH
    ):
        raise ValueError("hard_null_run_hash_or_control_binding_invalid")
    profile = run["profile"]
    profile_commitment = {key: value for key, value in profile.items() if key != "profile_hash"}
    if profile.get("profile_hash") != hash_payload(profile_commitment):
        raise ValueError("hard_null_profile_hash_invalid")
    batches = {item["batch_id"]: item for item in surface["public_batches"]}
    evidence_refs = (
        f"surface://{surface['surface_hash']}",
        f"control://{MATERIALITY_CONTROL_HASH}",
        f"control://{RECEIPT_QUALITY_CONTROL_HASH}",
    )
    for judgment in run["judgments"]:
        judgment_commitment = {
            key: value for key, value in judgment.items() if key != "judgment_hash"
        }
        if judgment.get("judgment_hash") != hash_payload(judgment_commitment):
            raise ValueError("hard_null_judgment_hash_invalid")
        batch = batches[judgment["batch_id"]]
        validate_hard_null_coordinator_payload(
            judgment["payload"],
            batch_id=batch["batch_id"],
            item_ids=tuple(item["coordination_item_id"] for item in batch["items"]),
            evidence_refs=evidence_refs,
        )


def _aggregate_usage(attempts):
    calls = input_tokens = output_tokens = 0
    for attempt in attempts:
        receipt = attempt["invocation_receipt"]
        fallback = receipt.get("fallback_decision") or {}
        attempted = fallback.get("attempted_providers", []) if isinstance(fallback, dict) else []
        calls += max(1, len(attempted))
        usage = receipt.get("token_usage") or {}
        input_tokens += int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        output_tokens += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    return calls, input_tokens, output_tokens
