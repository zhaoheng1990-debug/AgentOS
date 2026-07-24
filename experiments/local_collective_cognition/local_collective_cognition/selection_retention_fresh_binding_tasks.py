"""Typed binding and truth-state Provider tasks for v0.64."""

from __future__ import annotations

from typing import Any, Callable

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .frontier_experiment import TASK_KIND
from .selection_retention_fresh_contracts import (
    BINDING_ROLES,
    RUNTIME_VERSION,
    STATE_ROLES,
)
from .selection_retention_fresh_provider_helpers import (
    call_record,
    failed_call,
)
from .typed_evidence_binding_contracts import (
    typed_binding_schema,
    typed_state_schema,
)


def run_role_tasks(
    *,
    roles: tuple[str, ...],
    items: list[dict[str, Any]],
    task_factory: Callable[[str, dict[str, Any]], ProviderCognitiveTask],
    validator: Callable[[str, dict[str, Any], dict[str, Any]], list[str]],
    adapter: Any,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    calls: list[dict[str, Any]] = []
    receipts: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for role in roles:
        for item in items:
            task = task_factory(role, item)
            envelope = ProviderTaskRouter([adapter]).route(task)
            call = call_record(role, item["case_id"], task, envelope)
            calls.append(call)
            if envelope.status != "COMPLETED":
                failures.append(failed_call(call, envelope))
                continue
            receipt = envelope.normalized_result
            contract_failures = validator(role, item, receipt)
            if contract_failures:
                failures.append({
                    **call,
                    "contract_failures": contract_failures,
                    "invalid_receipt": receipt,
                })
                continue
            receipts[f"{role}:{item['case_id']}"] = receipt
    return calls, receipts, failures


def binding_task(
    *,
    item: dict[str, Any],
    role: str,
    refs: tuple[str, ...],
    adapter: Any,
) -> ProviderCognitiveTask:
    role_prompt = {
        BINDING_ROLES[0]: "Bind each relation to typed evidence.",
        BINDING_ROLES[1]: "Independently challenge every typed binding.",
    }[role]
    return ProviderCognitiveTask(
        task_id=f"{RUNTIME_VERSION}-{role}-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            f"{role_prompt} Assess all five relations exactly once without "
            "judging truth state. Primary evidence is the minimal direct span "
            "that binds source to focal outcome and fixes the design. An "
            "explicit untested statement is primary gap evidence for that "
            "relation. Keep primary, corroborating, counter, and gap sets "
            "disjoint. A replication summary is corroborating when a direct "
            "intervention already establishes the relation. Never emit a "
            "truth state or final decision."
        ),
        inputs={
            "binding_role": role,
            "public_item": item,
            "private_truth_available": False,
            "truth_state_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=typed_binding_schema(
            item=item, role=role, refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def state_task(
    *,
    item: dict[str, Any],
    role: str,
    binding_receipt: dict[str, Any],
    refs: tuple[str, ...],
    adapter: Any,
) -> ProviderCognitiveTask:
    role_prompt = {
        STATE_ROLES[0]: "Classify each relation from the typed binding.",
        STATE_ROLES[1]: "Challenge overclaim and underclaim, then classify.",
    }[role]
    return ProviderCognitiveTask(
        task_id=f"{RUNTIME_VERSION}-{role}-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            f"{role_prompt} Preserve every admitted primary citation. Use "
            "SUPPORTED_EFFECT only for a bound intervention or rollback that "
            "changed the focal outcome; use SUPPORTED_NULL only for a bound "
            "matched comparison with no outcome difference; otherwise use "
            "UNRESOLVED. Auxiliary evidence may qualify but never replace "
            "the primary design."
        ),
        inputs={
            "state_role": role,
            "public_item": item,
            "binding_consensus_receipt": binding_receipt,
            "private_truth_available": False,
        },
        allowed_evidence=list(refs),
        expected_schema=typed_state_schema(
            item=item,
            role=role,
            binding_receipt=binding_receipt,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
