"""Provider-backed joint cross-axis coordinator runtime v0.12."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .clarification_joint_coordinator_contracts import JOINT_COORDINATOR_TASK_KIND, JOINT_COORDINATOR_VERSION, assess_joint_decision, joint_coordinator_schema, validate_joint_coordinator_payload
from .clarification_joint_coordinator_surface import validate_joint_coordinator_surface
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "clarification_joint_coordinator_runtime_v0_12"


class ClarificationJointCoordinatorRuntime:
    def __init__(self, *, surface):
        validate_joint_coordinator_surface(surface)
        self.surface = surface
        self.evidence_refs = (f"surface://{surface['surface_hash']}",)

    def evaluate(self, *, experiment_id, adapter):
        conflicts = self.surface["public_conflicts"]
        batch_id = "joint-coordinator-batch-01"
        conflict_ids = tuple(item["conflict_id"] for item in conflicts)
        task = ProviderCognitiveTask(
            task_id=f"{experiment_id}-{adapter.profile.provider_id}-{batch_id}",
            task_kind=JOINT_COORDINATOR_TASK_KIND,
            objective=(
                "Coordinate each semantic receipt as a complete cross-axis object. The locked axes have unanimous "
                "independent support; preserve them unless the prompt provides a compelling reason to explicitly "
                "REOPEN_CONSENSUS_AXIS. A hard basis (LEXICAL_EXACT or COMPOSITIONAL_ENTAILMENT) requires selected "
                "object A/B. PRAGMATIC_DEFAULT requires selected NONE plus directional preference A/B. NO_PREFERENCE "
                "requires selected NONE plus preference NONE. COMPLETE is compatible with an open task. Choose "
                "PRESERVE_CONSENSUS_REPAIR when a coherent basis repairs the tuple, DECLARE_ONTOLOGY_CONFLICT when "
                "the axes cannot be represented coherently, or UNRESOLVED when evidence is insufficient. Return the "
                "entire proposed tuple and JSON only. Do not infer source identity or grant action authority."
            ),
            inputs={
                "source_identity": "WITHHELD", "construction_labels": "WITHHELD",
                "deepseek_predictions": "WITHHELD", "prior_scores": "WITHHELD",
                "batch": {"batch_id": batch_id, "conflicts": conflicts},
            },
            allowed_evidence=list(self.evidence_refs),
            expected_schema=joint_coordinator_schema(batch_id, conflict_ids),
            timeout_seconds=min(240, adapter.profile.max_timeout_seconds),
            failure_semantics="retain_conflicts_without_local_semantic_substitution",
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        invocation = envelope.invocation_receipt.as_dict()
        usage = invocation.get("token_usage") or {}
        accounting = {
            "provider_calls": max(1, int(usage.get("provider_calls") or 1)),
            "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        }
        failure = None
        decisions = []
        if envelope.status != "COMPLETED":
            failure = {"status": envelope.status, "validation_errors": list(envelope.validation_errors)}
        else:
            try:
                validate_joint_coordinator_payload(envelope.normalized_result, batch_id=batch_id, public_conflicts=conflicts, evidence_refs=self.evidence_refs)
            except ValueError as exc:
                failure = {"status": "SEMANTIC_VALIDATION_FAILED", "validation_errors": [str(exc)], "payload_hash": hash_payload(envelope.normalized_result)}
            else:
                by_id = {item["conflict_id"]: item for item in conflicts}
                for decision in envelope.normalized_result["decisions"]:
                    assessment = assess_joint_decision(decision, locked_consensus_axes=by_id[decision["conflict_id"]]["locked_consensus_axes"])
                    decisions.append({"decision": decision, "runtime_assessment": assessment})
        receipt_commitment = {
            "receipt_version": JOINT_COORDINATOR_VERSION,
            "provider_id": adapter.profile.provider_id,
            "model_id": adapter.profile.model_id,
            "task_contract_hash": task.contract_hash(),
            "invocation_receipt_hash": invocation["receipt_hash"],
            "surface_hash": self.surface["surface_hash"],
            "payload_hash": hash_payload(envelope.normalized_result) if envelope.normalized_result is not None else None,
            "provider_backed": True,
            "provider_authority": False,
        }
        receipt = {**receipt_commitment, "receipt_hash": hash_payload(receipt_commitment)}
        commitment = {
            "runtime_version": RUNTIME_VERSION,
            "experiment_id": experiment_id,
            "surface_hash": self.surface["surface_hash"],
            "provider_id": adapter.profile.provider_id,
            "model_id": adapter.profile.model_id,
            "decisions": decisions,
            "failure": failure,
            "invocation_receipt": invocation,
            "receipt": receipt,
            "accounting": accounting,
            "selection_authority": False,
            "retention_authority": False,
            "production_authority": False,
        }
        return {**commitment, "run_hash": hash_payload(commitment)}


def validate_joint_coordinator_run(run, *, surface):
    validate_joint_coordinator_surface(surface)
    commitment = {key: value for key, value in run.items() if key != "run_hash"}
    if run.get("run_hash") != hash_payload(commitment) or run.get("runtime_version") != RUNTIME_VERSION or run.get("surface_hash") != surface["surface_hash"]:
        raise ValueError("joint_coordinator_run_invalid")
    if any(run.get(key) is not False for key in ("selection_authority", "retention_authority", "production_authority")):
        raise ValueError("joint_coordinator_run_authority_invalid")
    conflicts = {item["conflict_id"]: item for item in surface["public_conflicts"]}
    if run["failure"] is None:
        if len(run["decisions"]) != len(conflicts):
            raise ValueError("joint_coordinator_run_coverage_invalid")
        observed = []
        for item in run["decisions"]:
            decision = item["decision"]
            observed.append(decision["conflict_id"])
            expected = assess_joint_decision(decision, locked_consensus_axes=conflicts[decision["conflict_id"]]["locked_consensus_axes"])
            if item["runtime_assessment"] != expected:
                raise ValueError("joint_coordinator_runtime_assessment_invalid")
        if len(observed) != len(set(observed)) or set(observed) != set(conflicts):
            raise ValueError("joint_coordinator_run_binding_invalid")
    elif run["decisions"]:
        raise ValueError("joint_coordinator_failure_with_decisions_invalid")
