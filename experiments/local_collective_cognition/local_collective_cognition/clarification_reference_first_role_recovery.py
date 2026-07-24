"""Flat one-object recovery for failed local specialist batches v0.15."""

from __future__ import annotations

from collections import defaultdict

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .clarification_reference_first_role_runtime import RECOVERED_RUNTIME_VERSION, validate_specialist_role_run
from .clarification_reference_first_roles import (
    MODEL_IDS,
    ROLE_DEFINITIONS,
    ROLE_TASK_KIND,
    ROLE_VERSION,
    role_decision_contract,
    validate_specialist_role_payload,
    validate_specialist_role_plan,
)
from .provider_telemetry import hash_payload


RECOVERY_VERSION = "clarification_reference_first_role_recovery_v0_15"
RECOVERY_RUNTIME_VERSION = "clarification_reference_first_role_recovery_runtime_v0_15"


def build_specialist_recovery_plan(*, role_plan, failed_run):
    validate_specialist_role_plan(role_plan)
    accepted = {
        (decision["conflict_id"], receipt["role_id"])
        for receipt in failed_run.get("receipts", [])
        for decision in receipt["payload"]["decisions"]
    }
    assignments = {(item["conflict_id"], item["role_id"]): item for item in role_plan["assignments"]}
    missing = [assignments[key] for key in sorted(set(assignments) - accepted)]
    public = {item["conflict_id"]: item for batch in role_plan["batches"] for item in batch["items"]}
    original_batch = {
        (item["conflict_id"], batch["role_id"]): batch["batch_id"]
        for batch in role_plan["batches"]
        for item in batch["items"]
    }
    tasks = []
    for assignment in missing:
        key = (assignment["conflict_id"], assignment["role_id"])
        task_id = "specialist-recovery-" + hash_payload([RECOVERY_VERSION, role_plan["plan_hash"], *key])[:18]
        tasks.append({
            "recovery_task_id": task_id,
            "original_batch_id": original_batch[key],
            "model_id": assignment["model_id"],
            "role_id": assignment["role_id"],
            "item": public[assignment["conflict_id"]],
            "item_hash": hash_payload(public[assignment["conflict_id"]]),
        })
    tasks.sort(key=lambda item: hash_payload([RECOVERY_VERSION, item["recovery_task_id"]]))
    commitment = {
        "recovery_version": RECOVERY_VERSION,
        "source_role_plan_hash": role_plan["plan_hash"],
        "source_failed_run_hash": failed_run["run_hash"],
        "frozen_reference_hash": role_plan["frozen_reference_hash"],
        "tasks": tasks,
        "task_count": len(tasks),
        "accepted_decision_count_before_recovery": len(accepted),
        "semantic_payload_reuse_from_failed_batches": False,
        "recovery_operator": "ONE_OBJECT_ONE_ROLE_FLAT_JSON",
        "reference_content_exposed_to_roles": False,
        "reference_hash_exposed_to_roles": False,
        "coordinator_run_allowed": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "plan_hash": hash_payload(commitment)}


def validate_specialist_recovery_plan(plan, *, role_plan=None, failed_run=None):
    commitment = {key: value for key, value in plan.items() if key != "plan_hash"}
    task_keys = {(item["item"]["conflict_id"], item["role_id"]) for item in plan.get("tasks", [])}
    if (
        plan.get("plan_hash") != hash_payload(commitment)
        or plan.get("recovery_version") != RECOVERY_VERSION
        or plan.get("task_count") != len(plan.get("tasks", []))
        or len(task_keys) != len(plan.get("tasks", []))
        or plan.get("semantic_payload_reuse_from_failed_batches") is not False
        or plan.get("reference_content_exposed_to_roles") is not False
        or plan.get("reference_hash_exposed_to_roles") is not False
        or plan.get("coordinator_run_allowed") is not False
    ):
        raise ValueError("specialist_recovery_plan_invalid")
    if role_plan is not None or failed_run is not None:
        if role_plan is None or failed_run is None or plan != build_specialist_recovery_plan(role_plan=role_plan, failed_run=failed_run):
            raise ValueError("specialist_recovery_plan_semantics_invalid")


def flat_recovery_schema(*, recovery_task):
    role_id = recovery_task["role_id"]
    base = {
        "recovery_version": {"type": "string", "enum": [RECOVERY_VERSION]},
        "role_id": {"type": "string", "enum": [role_id]},
        "recovery_task_id": {"type": "string", "enum": [recovery_task["recovery_task_id"]]},
        "conflict_id": {"type": "string", "enum": [recovery_task["item"]["conflict_id"]]},
    }
    if role_id == "OBJECT_GROUNDING":
        fields = {
            "selected_object": {"type": "string", "enum": role_decision_contract(role_id)["selected_object"]},
            "selection_basis": {"type": "string", "enum": role_decision_contract(role_id)["selection_basis"]},
            "support": {"type": "string", "minLength": 1},
            "counterevidence": {"type": "string", "minLength": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        }
    elif role_id == "PRAGMATIC_DEFAULT":
        fields = {
            "pragmatic_preference": {"type": "string", "enum": role_decision_contract(role_id)["pragmatic_preference"]},
            "default_advantage": {"type": "string", "minLength": 1},
            "counterpressure": {"type": "string", "minLength": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        }
    else:
        fields = {
            "assessment_completeness": {"type": "string", "enum": role_decision_contract(role_id)["assessment_completeness"]},
            "missing_information": {"type": "array", "items": {"type": "string"}},
            "rationale": {"type": "string", "minLength": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        }
    properties = {**base, **fields}
    return {"type": "object", "required": list(properties), "additionalProperties": False, "properties": properties}


def validate_flat_recovery_payload(payload, *, recovery_task):
    if not isinstance(payload, dict) or set(payload) != set(flat_recovery_schema(recovery_task=recovery_task)["properties"]):
        raise ValueError("specialist_recovery_payload_shape_invalid")
    if (
        payload["recovery_version"] != RECOVERY_VERSION
        or payload["role_id"] != recovery_task["role_id"]
        or payload["recovery_task_id"] != recovery_task["recovery_task_id"]
        or payload["conflict_id"] != recovery_task["item"]["conflict_id"]
    ):
        raise ValueError("specialist_recovery_payload_binding_invalid")
    decision = _canonical_decision(payload, role_id=recovery_task["role_id"])
    canonical_payload = {"role_version": ROLE_VERSION, "role_id": recovery_task["role_id"], "batch_id": recovery_task["original_batch_id"], "decisions": [decision], "evidence_refs": ["fixture://recovery"]}
    validate_specialist_role_payload(canonical_payload, batch={"role_id": recovery_task["role_id"], "batch_id": recovery_task["original_batch_id"], "items": [recovery_task["item"]]}, evidence_refs=("fixture://recovery",))


class ReferenceFirstSpecialistRecoveryRuntime:
    def __init__(self, *, role_plan, failed_run, recovery_plan, evidence_refs):
        validate_specialist_role_plan(role_plan)
        validate_specialist_recovery_plan(recovery_plan, role_plan=role_plan, failed_run=failed_run)
        self.role_plan = role_plan
        self.failed_run = failed_run
        self.plan = recovery_plan
        self.evidence_refs = tuple(evidence_refs)

    def evaluate(self, *, experiment_id, adapters):
        adapters = tuple(adapters)
        adapter_index = {adapter.profile.model_id: adapter for adapter in adapters}
        if len(adapter_index) != len(adapters) or set(adapter_index) != set(MODEL_IDS):
            raise ValueError("specialist_recovery_adapters_invalid")
        outputs, failures = [], []
        calls = input_tokens = output_tokens = 0
        for recovery_task in self.plan["tasks"]:
            adapter = adapter_index[recovery_task["model_id"]]
            task = self._task(experiment_id=experiment_id, adapter=adapter, recovery_task=recovery_task)
            envelope = ProviderTaskRouter([adapter]).route(task)
            invocation = envelope.invocation_receipt.as_dict()
            usage = invocation.get("token_usage") or {}
            calls += max(1, int(usage.get("provider_calls") or 1))
            input_tokens += int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
            output_tokens += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
            if envelope.status != "COMPLETED":
                failures.append({"recovery_task_id": recovery_task["recovery_task_id"], "model_id": recovery_task["model_id"], "role_id": recovery_task["role_id"], "status": envelope.status, "validation_errors": list(envelope.validation_errors), "invocation_receipt": invocation})
                continue
            try:
                validate_flat_recovery_payload(envelope.normalized_result, recovery_task=recovery_task)
            except ValueError as exc:
                failures.append({"recovery_task_id": recovery_task["recovery_task_id"], "model_id": recovery_task["model_id"], "role_id": recovery_task["role_id"], "status": "SEMANTIC_VALIDATION_FAILED", "validation_errors": [str(exc)], "payload": envelope.normalized_result, "invocation_receipt": invocation})
                continue
            commitment = {"recovery_task_id": recovery_task["recovery_task_id"], "original_batch_id": recovery_task["original_batch_id"], "model_id": recovery_task["model_id"], "role_id": recovery_task["role_id"], "payload": envelope.normalized_result, "provenance_refs": list(envelope.provenance_refs), "invocation_receipt": invocation, "task_contract_hash": task.contract_hash()}
            outputs.append({**commitment, "output_hash": hash_payload(commitment)})
        commitment = {
            "runtime_version": RECOVERY_RUNTIME_VERSION,
            "recovery_version": RECOVERY_VERSION,
            "experiment_id": experiment_id,
            "source_role_plan_hash": self.role_plan["plan_hash"],
            "source_failed_run_hash": self.failed_run["run_hash"],
            "recovery_plan_hash": self.plan["plan_hash"],
            "outputs": outputs,
            "failures": failures,
            "accounting": {"provider_calls": calls, "input_tokens": input_tokens, "output_tokens": output_tokens},
            "reference_available_to_roles": False,
            "reference_hash_available_to_roles": False,
            "candidate_coordinator_output_available": False,
            "coordinator_run_allowed_during_recovery": False,
        }
        return {**commitment, "run_hash": hash_payload(commitment)}

    def _task(self, *, experiment_id, adapter, recovery_task):
        role_id = recovery_task["role_id"]
        return ProviderCognitiveTask(
            task_id=f"{experiment_id}-{adapter.profile.model_id}-{recovery_task['recovery_task_id']}",
            task_kind=ROLE_TASK_KIND,
            objective=(f"Act only as {role_id}. {ROLE_DEFINITIONS[role_id]} Assess the one displayed object. Return exactly the flat JSON keys in the schema. Do not repeat candidate_a, candidate_b, source_identity, role_definition, schema, or instructions. Confidence must be a number from 0 to 1."),
            inputs={"role_id": role_id, "item": recovery_task["item"]},
            allowed_evidence=list(self.evidence_refs),
            expected_schema=flat_recovery_schema(recovery_task=recovery_task),
            timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
            failure_semantics="retain_failed_flat_role_without_semantic_substitution",
        )


def validate_specialist_recovery_run(run, *, recovery_plan):
    validate_specialist_recovery_plan(recovery_plan)
    commitment = {key: value for key, value in run.items() if key != "run_hash"}
    if run.get("run_hash") != hash_payload(commitment) or run.get("runtime_version") != RECOVERY_RUNTIME_VERSION or run.get("recovery_plan_hash") != recovery_plan.get("plan_hash") or run.get("reference_available_to_roles") is not False or run.get("reference_hash_available_to_roles") is not False:
        raise ValueError("specialist_recovery_run_invalid")
    expected = {item["recovery_task_id"]: item for item in recovery_plan["tasks"]}
    observed = [item["recovery_task_id"] for item in run["outputs"]] + [item["recovery_task_id"] for item in run["failures"]]
    if len(observed) != len(set(observed)) or set(observed) != set(expected):
        raise ValueError("specialist_recovery_run_coverage_invalid")
    for output in run["outputs"]:
        commitment = {key: value for key, value in output.items() if key != "output_hash"}
        if output.get("output_hash") != hash_payload(commitment):
            raise ValueError("specialist_recovery_output_hash_invalid")
        validate_flat_recovery_payload(output["payload"], recovery_task=expected[output["recovery_task_id"]])


def build_recovered_specialist_role_run(*, role_plan, initial_run, recovery_plan, recovery_run):
    validate_specialist_role_plan(role_plan)
    validate_specialist_recovery_plan(recovery_plan, role_plan=role_plan, failed_run=initial_run)
    validate_specialist_recovery_run(recovery_run, recovery_plan=recovery_plan)
    decisions = defaultdict(dict)
    invocation_sources = defaultdict(list)
    for receipt in initial_run["receipts"]:
        for decision in receipt["payload"]["decisions"]:
            decisions[receipt["batch_id"]][decision["conflict_id"]] = decision
        invocation_sources[receipt["batch_id"]].append(receipt["invocation_receipt"])
    recovery_tasks = {item["recovery_task_id"]: item for item in recovery_plan["tasks"]}
    for output in recovery_run["outputs"]:
        task = recovery_tasks[output["recovery_task_id"]]
        decision = _canonical_decision(output["payload"], role_id=task["role_id"])
        decisions[task["original_batch_id"]][decision["conflict_id"]] = decision
        invocation_sources[task["original_batch_id"]].append(output["invocation_receipt"])
    evidence_refs = next((receipt["payload"]["evidence_refs"] for receipt in initial_run["receipts"]), None)
    if evidence_refs is None:
        evidence_refs = []
        if recovery_run["outputs"]:
            evidence_refs = list(recovery_run["outputs"][0]["provenance_refs"])
    receipts, failures = [], []
    for batch in role_plan["batches"]:
        ordered = [decisions[batch["batch_id"]].get(item["conflict_id"]) for item in batch["items"]]
        if any(item is None for item in ordered):
            failures.append({"batch_id": batch["batch_id"], "model_id": batch["model_id"], "role_id": batch["role_id"], "status": "RECOVERY_INCOMPLETE", "validation_errors": ["missing_recovered_role_decisions"], "invocation_receipt": {"recovery_sources": invocation_sources[batch["batch_id"]]}})
            continue
        payload = {"role_version": ROLE_VERSION, "role_id": batch["role_id"], "batch_id": batch["batch_id"], "decisions": ordered, "evidence_refs": evidence_refs}
        validate_specialist_role_payload(payload, batch=batch, evidence_refs=tuple(evidence_refs))
        rc = {"batch_id": batch["batch_id"], "model_id": batch["model_id"], "role_id": batch["role_id"], "payload": payload, "invocation_receipt": {"recovery_sources": invocation_sources[batch["batch_id"]]}, "task_contract_hash": "recovery-aggregate://" + hash_payload(invocation_sources[batch["batch_id"]])}
        receipts.append({**rc, "receipt_hash": hash_payload(rc)})
    accounting = {key: initial_run["accounting"][key] + recovery_run["accounting"][key] for key in ("provider_calls", "input_tokens", "output_tokens")}
    commitment = {
        "runtime_version": RECOVERED_RUNTIME_VERSION,
        "role_version": ROLE_VERSION,
        "experiment_id": recovery_run["experiment_id"],
        "source_corpus_hash": initial_run["source_corpus_hash"],
        "source_surface_hash": initial_run["source_surface_hash"],
        "role_plan_hash": role_plan["plan_hash"],
        "frozen_reference_hash": role_plan["frozen_reference_hash"],
        "initial_failed_run_hash": initial_run["run_hash"],
        "recovery_plan_hash": recovery_plan["plan_hash"],
        "recovery_run_hash": recovery_run["run_hash"],
        "receipts": receipts,
        "failures": failures,
        "accounting": accounting,
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


def _canonical_decision(payload, *, role_id):
    metadata = {"recovery_version", "role_id", "recovery_task_id"}
    return {key: value for key, value in payload.items() if key not in metadata}
