"""Provider-backed runtime for identity-blind ambiguity coordination."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .ambiguity_coordinator_contracts import TASK_KIND, coordinator_schema, validate_coordinator_payload
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "ambiguity_coordinator_runtime_v0_1"


class AmbiguityCoordinatorRuntime:
    def __init__(self, *, surface, max_attempts_per_batch=2):
        if max_attempts_per_batch not in {1, 2}:
            raise ValueError("ambiguity_coordinator_attempt_budget_invalid")
        self.surface = surface
        self.max_attempts_per_batch = max_attempts_per_batch
        self.evidence_refs = (f"surface://{surface['surface_hash']}",)

    def evaluate(self, *, experiment_id, adapter):
        judgments, failures, all_attempts = [], [], []
        for batch in self.surface["public_batches"]:
            batch_attempts, payload, provider_input = [], None, None
            item_ids = tuple(item["coordination_item_id"] for item in batch["items"])
            for attempt in range(1, self.max_attempts_per_batch + 1):
                task = self._task(experiment_id, adapter, batch, item_ids, attempt)
                envelope = ProviderTaskRouter([adapter]).route(task)
                invocation = envelope.invocation_receipt.as_dict()
                attempt_record = {
                    "attempt": attempt, "status": envelope.status,
                    "validation_errors": list(envelope.validation_errors),
                    "invocation_receipt": invocation,
                }
                batch_attempts.append(attempt_record)
                all_attempts.append(attempt_record)
                if envelope.status != "COMPLETED":
                    continue
                try:
                    validate_coordinator_payload(
                        envelope.normalized_result, batch_id=batch["batch_id"],
                        item_ids=item_ids, evidence_refs=self.evidence_refs,
                    )
                except ValueError as exc:
                    attempt_record["semantic_validation_error"] = str(exc)
                    attempt_record["payload_hash"] = hash_payload(envelope.normalized_result)
                    continue
                payload, provider_input = envelope.normalized_result, task.inputs
                break
            if payload is None:
                failures.append({"batch_id": batch["batch_id"], "attempts": batch_attempts})
            else:
                commitment = {
                    "batch_id": batch["batch_id"], "provider_input": provider_input,
                    "payload": payload, "attempts": batch_attempts,
                }
                judgments.append({**commitment, "judgment_hash": hash_payload(commitment)})
        calls, input_tokens, output_tokens = _aggregate_usage(all_attempts)
        profile_commitment = {
            "provider_id": adapter.profile.provider_id, "model_id": adapter.profile.model_id,
            "requested_batches": len(self.surface["public_batches"]),
            "successful_batches": len(judgments), "failed_batches": len(failures),
            "decision_count": sum(len(item["payload"]["decisions"]) for item in judgments),
            "total_provider_calls": calls, "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens, "total_tokens": input_tokens + output_tokens,
            "selection_authority": False, "retention_authority": False,
        }
        profile = {**profile_commitment, "profile_hash": hash_payload(profile_commitment)}
        commitment = {
            "runtime_version": RUNTIME_VERSION, "experiment_id": experiment_id,
            "surface_hash": self.surface["surface_hash"],
            "provider_id": adapter.profile.provider_id, "model_id": adapter.profile.model_id,
            "judgments": judgments, "failures": failures, "profile": profile,
        }
        return {**commitment, "coordinator_run_hash": hash_payload(commitment)}

    def _task(self, experiment_id, adapter, batch, item_ids, attempt):
        return ProviderCognitiveTask(
            task_id=f"{experiment_id}-{adapter.profile.provider_id}-{batch['batch_id']}-a{attempt}",
            task_kind=TASK_KIND,
            objective=(
                "Act as an identity-blind semantic coordinator over two independent discovery receipts per "
                "task. Decide whether the requested output object itself has at least two materially plausible, "
                "incompatible interpretations. Judge the public task and receipt content; do not use position, "
                "agreement, confidence, verbosity, or presumed model strength as a substitute for semantics. "
                "Return UNCERTAIN when neither receipt supports a defensible decision. Do not solve the task, "
                "infer source identity, claim authority, or emit reasoning outside the JSON contract."
            ),
            inputs={
                "source_identity": "WITHHELD", "prior_scores": "WITHHELD", "hidden_truth": "WITHHELD",
                "position_order": "COUNTERBALANCED", "batch": batch,
            },
            allowed_evidence=list(self.evidence_refs),
            expected_schema=coordinator_schema(batch["batch_id"], item_ids, self.evidence_refs),
            timeout_seconds=min(240, adapter.profile.max_timeout_seconds),
            failure_semantics="preserve_unresolved_batch_without_local_semantic_substitution",
        )


def validate_coordinator_run(run, *, surface):
    commitment = {key: value for key, value in run.items() if key != "coordinator_run_hash"}
    if run.get("coordinator_run_hash") != hash_payload(commitment) or run.get("surface_hash") != surface["surface_hash"]:
        raise ValueError("ambiguity_coordinator_run_hash_or_surface_invalid")
    profile = run["profile"]
    profile_commitment = {key: value for key, value in profile.items() if key != "profile_hash"}
    if profile.get("profile_hash") != hash_payload(profile_commitment):
        raise ValueError("ambiguity_coordinator_profile_hash_invalid")
    batches = {item["batch_id"]: item for item in surface["public_batches"]}
    for judgment in run["judgments"]:
        judgment_commitment = {key: value for key, value in judgment.items() if key != "judgment_hash"}
        if judgment.get("judgment_hash") != hash_payload(judgment_commitment):
            raise ValueError("ambiguity_coordinator_judgment_hash_invalid")
        batch = batches[judgment["batch_id"]]
        validate_coordinator_payload(
            judgment["payload"], batch_id=batch["batch_id"],
            item_ids=tuple(item["coordination_item_id"] for item in batch["items"]),
            evidence_refs=(f"surface://{surface['surface_hash']}",),
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
