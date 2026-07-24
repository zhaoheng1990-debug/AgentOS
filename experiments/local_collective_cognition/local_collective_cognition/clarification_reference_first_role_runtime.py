"""Reference-blind local specialist execution runtime for v0.15."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .clarification_reference_first_holdout import validate_reference_first_holdout
from .clarification_reference_first_roles import (
    MODEL_IDS,
    ROLE_TASK_KIND,
    ROLE_VERSION,
    specialist_role_schema,
    validate_specialist_role_payload,
    validate_specialist_role_plan,
)
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "clarification_reference_first_role_runtime_v0_15"
RECOVERED_RUNTIME_VERSION = "clarification_reference_first_role_runtime_recovered_v0_15"


class ReferenceFirstSpecialistRuntime:
    def __init__(self, *, corpus_artifact, role_plan):
        validate_reference_first_holdout(corpus_artifact)
        validate_specialist_role_plan(role_plan)
        if role_plan["source_corpus_hash"] != corpus_artifact["artifact_hash"]:
            raise ValueError("specialist_runtime_source_mismatch")
        self.corpus = corpus_artifact
        self.plan = role_plan
        self.evidence_refs = (
            *tuple(corpus_artifact["evidence_refs"]),
            f"artifact://{corpus_artifact['artifact_hash']}",
            f"surface://{corpus_artifact['public_surface']['surface_hash']}",
        )

    def evaluate(self, *, experiment_id, adapters):
        adapters = tuple(adapters)
        adapter_index = {adapter.profile.model_id: adapter for adapter in adapters}
        if len(adapter_index) != len(adapters) or set(adapter_index) != set(MODEL_IDS):
            raise ValueError("specialist_runtime_adapters_invalid")
        receipts, failures = [], []
        calls = input_tokens = output_tokens = 0
        for batch in self.plan["batches"]:
            adapter = adapter_index[batch["model_id"]]
            task = self._task(experiment_id=experiment_id, adapter=adapter, batch=batch)
            envelope = ProviderTaskRouter([adapter]).route(task)
            invocation = envelope.invocation_receipt.as_dict()
            usage = invocation.get("token_usage") or {}
            calls += max(1, int(usage.get("provider_calls") or 1))
            input_tokens += int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
            output_tokens += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
            if envelope.status != "COMPLETED":
                failures.append({
                    "batch_id": batch["batch_id"],
                    "model_id": batch["model_id"],
                    "role_id": batch["role_id"],
                    "status": envelope.status,
                    "validation_errors": list(envelope.validation_errors),
                    "invocation_receipt": invocation,
                })
                continue
            try:
                validate_specialist_role_payload(envelope.normalized_result, batch=batch, evidence_refs=self.evidence_refs)
            except ValueError as exc:
                failures.append({
                    "batch_id": batch["batch_id"],
                    "model_id": batch["model_id"],
                    "role_id": batch["role_id"],
                    "status": "SEMANTIC_VALIDATION_FAILED",
                    "validation_errors": [str(exc)],
                    "payload_hash": hash_payload(envelope.normalized_result),
                    "payload": envelope.normalized_result,
                    "invocation_receipt": invocation,
                })
                continue
            commitment = {
                "batch_id": batch["batch_id"],
                "model_id": batch["model_id"],
                "role_id": batch["role_id"],
                "payload": envelope.normalized_result,
                "invocation_receipt": invocation,
                "task_contract_hash": task.contract_hash(),
            }
            receipts.append({**commitment, "receipt_hash": hash_payload(commitment)})
        commitment = {
            "runtime_version": RUNTIME_VERSION,
            "role_version": ROLE_VERSION,
            "experiment_id": experiment_id,
            "source_corpus_hash": self.corpus["artifact_hash"],
            "source_surface_hash": self.corpus["public_surface"]["surface_hash"],
            "role_plan_hash": self.plan["plan_hash"],
            "frozen_reference_hash": self.plan["frozen_reference_hash"],
            "receipts": receipts,
            "failures": failures,
            "accounting": {"provider_calls": calls, "input_tokens": input_tokens, "output_tokens": output_tokens},
            "reference_available_to_roles": False,
            "reference_hash_available_to_roles": False,
            "candidate_coordinator_output_available": False,
            "coordinator_run_allowed_during_collection": False,
            "action_credit_authority": False,
            "selection_authority": False,
            "retention_authority": False,
            "production_authority": False,
        }
        return {**commitment, "run_hash": hash_payload(commitment)}

    def _task(self, *, experiment_id, adapter, batch):
        conflict_ids = tuple(item["conflict_id"] for item in batch["items"])
        return ProviderCognitiveTask(
            task_id=f"{experiment_id}-{adapter.profile.model_id}-{batch['batch_id']}",
            task_kind=ROLE_TASK_KIND,
            objective=(
                f"Act only as role {batch['role_id']}. {batch['role_definition']} Return one decision for every "
                "conflict_id. Keep support and counterevidence distinct. Confidence is epistemic confidence in this "
                "bounded role judgment, not authority. Return JSON only and copy evidence_refs exactly."
            ),
            inputs={
                "source_identity": "WITHHELD",
                "object_family": "WITHHELD",
                "peer_role_outputs": "NOT_YET_CREATED",
                "coordinator_output": "NOT_YET_CREATED",
                "role_id": batch["role_id"],
                "role_definition": batch["role_definition"],
                "batch_id": batch["batch_id"],
                "items": batch["items"],
            },
            allowed_evidence=list(self.evidence_refs),
            expected_schema=specialist_role_schema(role_id=batch["role_id"], batch_id=batch["batch_id"], conflict_ids=conflict_ids),
            timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
            failure_semantics="retain_failed_role_batch_without_semantic_substitution",
        )


def validate_specialist_role_run(run, *, corpus_artifact, role_plan):
    validate_reference_first_holdout(corpus_artifact)
    validate_specialist_role_plan(role_plan)
    commitment = {key: value for key, value in run.items() if key != "run_hash"}
    if (
        run.get("run_hash") != hash_payload(commitment)
        or run.get("runtime_version") not in (RUNTIME_VERSION, RECOVERED_RUNTIME_VERSION)
        or run.get("source_corpus_hash") != corpus_artifact.get("artifact_hash")
        or run.get("role_plan_hash") != role_plan.get("plan_hash")
        or run.get("frozen_reference_hash") != role_plan.get("frozen_reference_hash")
        or run.get("reference_available_to_roles") is not False
        or run.get("reference_hash_available_to_roles") is not False
        or run.get("candidate_coordinator_output_available") is not False
        or run.get("coordinator_run_allowed_during_collection") is not False
    ):
        raise ValueError("specialist_role_run_invalid")
    batches = {batch["batch_id"]: batch for batch in role_plan["batches"]}
    if len(run.get("receipts", [])) + len(run.get("failures", [])) != len(batches):
        raise ValueError("specialist_role_run_batch_coverage_invalid")
    observed_batches = []
    for receipt in run["receipts"]:
        rc = {key: value for key, value in receipt.items() if key != "receipt_hash"}
        batch = batches.get(receipt.get("batch_id"))
        if receipt.get("receipt_hash") != hash_payload(rc) or batch is None:
            raise ValueError("specialist_role_receipt_invalid")
        validate_specialist_role_payload(receipt["payload"], batch=batch, evidence_refs=(
            *tuple(corpus_artifact["evidence_refs"]),
            f"artifact://{corpus_artifact['artifact_hash']}",
            f"surface://{corpus_artifact['public_surface']['surface_hash']}",
        ))
        observed_batches.append(receipt["batch_id"])
    observed_batches.extend(item["batch_id"] for item in run["failures"])
    if len(observed_batches) != len(set(observed_batches)) or set(observed_batches) != set(batches):
        raise ValueError("specialist_role_run_batch_ids_invalid")
