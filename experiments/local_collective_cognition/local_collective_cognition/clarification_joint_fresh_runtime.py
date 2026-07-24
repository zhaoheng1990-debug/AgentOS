"""Provider-backed fresh joint coordinator runtime v0.13."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .clarification_joint_fresh_contracts import FRESH_COORDINATOR_TASK_KIND, FRESH_COORDINATOR_VERSION, assess_fresh_decision, fresh_coordinator_schema, validate_fresh_coordinator_payload
from .clarification_joint_holdout import validate_joint_holdout_artifact
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "clarification_joint_fresh_runtime_v0_13"


class ClarificationJointFreshRuntime:
    def __init__(self, *, corpus_artifact):
        validate_joint_holdout_artifact(corpus_artifact)
        self.corpus = corpus_artifact
        self.surface = corpus_artifact["public_surface"]
        self.evidence_refs = (*tuple(corpus_artifact["evidence_refs"]), f"artifact://{corpus_artifact['artifact_hash']}")

    def evaluate(self, *, experiment_id, adapter):
        judgments, failures = [], []
        calls = input_tokens = output_tokens = 0
        for batch in self.surface["batches"]:
            task = self._task(experiment_id, adapter, batch)
            envelope = ProviderTaskRouter([adapter]).route(task)
            invocation = envelope.invocation_receipt.as_dict()
            usage = invocation.get("token_usage") or {}
            calls += max(1, int(usage.get("provider_calls") or 1))
            input_tokens += int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
            output_tokens += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
            if envelope.status != "COMPLETED":
                failures.append({"batch_id": batch["batch_id"], "status": envelope.status, "validation_errors": list(envelope.validation_errors), "invocation_receipt": invocation})
                continue
            try:
                validate_fresh_coordinator_payload(envelope.normalized_result, batch=batch, evidence_refs=self.evidence_refs)
            except ValueError as exc:
                failures.append({"batch_id": batch["batch_id"], "status": "SEMANTIC_VALIDATION_FAILED", "validation_errors": [str(exc)], "invocation_receipt": invocation, "payload_hash": hash_payload(envelope.normalized_result)})
                continue
            by_id = {item["conflict_id"]: item for item in batch["conflicts"]}
            decisions = [{"decision": decision, "runtime_assessment": assess_fresh_decision(decision, conflict=by_id[decision["conflict_id"]])} for decision in envelope.normalized_result["decisions"]]
            commitment = {"batch_id": batch["batch_id"], "payload": envelope.normalized_result, "decisions": decisions, "invocation_receipt": invocation, "task_contract_hash": task.contract_hash()}
            judgments.append({**commitment, "judgment_hash": hash_payload(commitment)})
        commitment = {
            "runtime_version": RUNTIME_VERSION, "receipt_version": FRESH_COORDINATOR_VERSION,
            "experiment_id": experiment_id, "source_artifact_hash": self.corpus["artifact_hash"], "surface_hash": self.surface["surface_hash"],
            "provider_id": adapter.profile.provider_id, "model_id": adapter.profile.model_id,
            "judgments": judgments, "failures": failures,
            "accounting": {"provider_calls": calls, "input_tokens": input_tokens, "output_tokens": output_tokens},
            "private_oracle_available_at_prediction_time": False, "construction_labels_are_pre_panel_diagnostics_only": True,
            "action_credit_authority": False, "selection_authority": False, "retention_authority": False, "production_authority": False,
        }
        return {**commitment, "run_hash": hash_payload(commitment)}

    def _task(self, experiment_id, adapter, batch):
        conflict_ids = tuple(item["conflict_id"] for item in batch["conflicts"])
        return ProviderCognitiveTask(
            task_id=f"{experiment_id}-{adapter.profile.provider_id}-{batch['batch_id']}", task_kind=FRESH_COORDINATOR_TASK_KIND,
            objective=(
                "Coordinate each complete semantic tuple. For each unanimous consensus axis, output PRESERVE when "
                "the final value is unchanged and REOPEN when evidence requires a different final value. For the "
                "single-position local basis, output PRESERVE or REVISE. Runtime derives governance state from these "
                "per-axis actions; there is no overall disposition. Apply the tuple invariants: hard basis requires "
                "selected A/B; PRAGMATIC_DEFAULT requires selected NONE and preference A/B; NO_PREFERENCE requires "
                "selected NONE and preference NONE; a complete assessment may be open. Consensus is strong evidence "
                "but can be reopened when contradicted by clear prompt semantics. Return JSON only."
            ),
            inputs={"source_identity": "WITHHELD", "construction_labels": "WITHHELD", "prior_scores": "WITHHELD", "batch": batch},
            allowed_evidence=list(self.evidence_refs), expected_schema=fresh_coordinator_schema(batch["batch_id"], conflict_ids),
            timeout_seconds=min(240, adapter.profile.max_timeout_seconds), failure_semantics="retain_batch_without_local_semantic_substitution",
        )


def validate_joint_fresh_run(run, *, corpus_artifact):
    validate_joint_holdout_artifact(corpus_artifact)
    commitment = {key: value for key, value in run.items() if key != "run_hash"}
    if run.get("run_hash") != hash_payload(commitment) or run.get("runtime_version") != RUNTIME_VERSION or run.get("source_artifact_hash") != corpus_artifact["artifact_hash"]:
        raise ValueError("joint_fresh_run_invalid")
    if run.get("private_oracle_available_at_prediction_time") is not False or any(run.get(key) is not False for key in ("action_credit_authority", "selection_authority", "retention_authority", "production_authority")):
        raise ValueError("joint_fresh_run_boundary_invalid")
    batches = {batch["batch_id"]: batch for batch in corpus_artifact["public_surface"]["batches"]}
    if len(run["judgments"]) + len(run["failures"]) != len(batches):
        raise ValueError("joint_fresh_run_batch_coverage_invalid")
    for judgment in run["judgments"]:
        batch = batches[judgment["batch_id"]]
        commitment = {key: value for key, value in judgment.items() if key != "judgment_hash"}
        if judgment.get("judgment_hash") != hash_payload(commitment):
            raise ValueError("joint_fresh_judgment_hash_invalid")
        by_id = {item["conflict_id"]: item for item in batch["conflicts"]}
        for item in judgment["decisions"]:
            if item["runtime_assessment"] != assess_fresh_decision(item["decision"], conflict=by_id[item["decision"]["conflict_id"]]):
                raise ValueError("joint_fresh_runtime_assessment_invalid")
