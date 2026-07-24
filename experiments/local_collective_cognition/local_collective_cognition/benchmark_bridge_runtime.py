"""Modular orchestration for the v0.65 benchmark bridge."""

from __future__ import annotations

from typing import Any, Callable

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .benchmark_bridge_contracts import (
    validate_admission,
    validate_one_pass,
    validate_staged_binding,
)
from .benchmark_bridge_protocol import validate_preregistration
from .benchmark_bridge_tasks import (
    admission_task,
    evidence_refs,
    one_pass_task,
    staged_binding_task,
)
from .evidence_inference_bridge import validate_panel
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import call_record, failed_call


Validator = Callable[[dict[str, Any], dict[str, Any]], list[str]]


def run_one_pass_panel(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    _validate_inputs(panel, preregistration)
    calls, receipts, failures = _run_items(
        items=panel["public_surface"]["items"],
        role="A0_ONE_PASS",
        adapter=adapter,
        task_factory=lambda item: one_pass_task(item, adapter),
        validator=lambda item, receipt: validate_one_pass(
            receipt, item, evidence_refs(item)
        ),
    )
    return _artifact(
        arm_id="A0_ONE_PASS",
        panel=panel,
        preregistration=preregistration,
        adapter=adapter,
        task_calls=calls,
        receipts=receipts,
        contract_failures=failures,
    )


def run_staged_panel(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    _validate_inputs(panel, preregistration)
    items = panel["public_surface"]["items"]
    admission_calls, admissions, failures = _run_items(
        items=items,
        role="A1_SPAN_ADMISSION",
        adapter=adapter,
        task_factory=lambda item: admission_task(item, adapter),
        validator=lambda item, receipt: validate_admission(
            receipt, item, evidence_refs(item)
        ),
    )
    binding_calls: list[dict[str, Any]] = []
    bindings: dict[str, dict[str, Any]] = {}
    for item in items:
        admission = admissions.get(item["case_id"])
        if admission is None:
            continue
        task = staged_binding_task(item, admission, adapter)
        call, receipt, failure = _invoke(
            role="A1_STAGED_BINDING",
            item=item,
            task=task,
            adapter=adapter,
            validator=lambda value: validate_staged_binding(
                receipt=value,
                item=item,
                admission=admission,
                refs=evidence_refs(item),
            ),
        )
        binding_calls.append(call)
        if failure:
            failures.append(failure)
        else:
            bindings[item["case_id"]] = receipt
    return _artifact(
        arm_id="A1_STAGED_ADMISSION_BINDING",
        panel=panel,
        preregistration=preregistration,
        adapter=adapter,
        task_calls=[*admission_calls, *binding_calls],
        admission_receipts=admissions,
        receipts=bindings,
        contract_failures=failures,
    )


def _run_items(
    *,
    items: list[dict[str, Any]],
    role: str,
    adapter: Any,
    task_factory: Callable[[dict[str, Any]], ProviderCognitiveTask],
    validator: Validator,
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
]:
    calls: list[dict[str, Any]] = []
    receipts: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for item in items:
        task = task_factory(item)
        call, receipt, failure = _invoke(
            role=role,
            item=item,
            task=task,
            adapter=adapter,
            validator=lambda value, current=item: validator(current, value),
        )
        calls.append(call)
        if failure:
            failures.append(failure)
        else:
            receipts[item["case_id"]] = receipt
    return calls, receipts, failures


def _invoke(
    *,
    role: str,
    item: dict[str, Any],
    task: ProviderCognitiveTask,
    adapter: Any,
    validator: Callable[[dict[str, Any]], list[str]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    envelope = ProviderTaskRouter([adapter]).route(task)
    call = call_record(role, item["case_id"], task, envelope)
    if envelope.status != "COMPLETED":
        return call, {}, failed_call(call, envelope)
    receipt = envelope.normalized_result
    failures = validator(receipt)
    if failures:
        return call, receipt, {
            **call,
            "contract_failures": failures,
            "invalid_receipt": receipt,
        }
    return call, receipt, None


def _validate_inputs(
    panel: dict[str, Any], preregistration: dict[str, Any]
) -> None:
    validate_panel(panel)
    validate_preregistration(preregistration)
    if preregistration["source_panel_hash"] != panel["artifact_hash"]:
        raise ValueError("benchmark_bridge_source_panel_mismatch")


def _artifact(
    *,
    arm_id: str,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    adapter: Any,
    **values: Any,
) -> dict[str, Any]:
    commitment = {
        "runtime_version": "benchmark_bridge_runtime_v0_65",
        "arm_id": arm_id,
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "private_gold_exposed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        **values,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}
