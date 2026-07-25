"""Evidence-first Provider contract for minimal complete warrant groups."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderCognitiveTask

from ..provider_telemetry import hash_payload

TASK_KIND = "SCIFACT_EVIDENCE_SET_V0_88"
RECEIPT_KIND = "EVIDENCE_SET"
GROUP_RELATIONS = ("SUPPORTS", "REFUTES")
GROUP_FIELDS = ("group_id", "relation", "unit_ids", "rationale")
REQUIRED_FIELDS = (
    "case_id",
    "receipt_kind",
    "source_public_case_hash",
    "evidence_groups",
    "context_unit_ids",
    "irrelevant_unit_ids",
    "all_units_assessed",
    "uncertainty_state",
    "rationale",
)
UNCERTAINTY_STATES = ("RESOLVED", "MATERIAL_UNCERTAINTY")


def evidence_set_schema(public_case: dict[str, Any]) -> dict[str, Any]:
    unit_ids = [unit["unit_id"] for unit in public_case["evidence_units"]]
    group = {
        "type": "object",
        "additionalProperties": False,
        "required": list(GROUP_FIELDS),
        "properties": {
            "group_id": {"type": "string"},
            "relation": {"type": "string", "enum": list(GROUP_RELATIONS)},
            "unit_ids": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {"type": "string", "enum": unit_ids},
            },
            "rationale": {"type": "string"},
        },
    }
    properties = {
        "case_id": {"type": "string", "enum": [public_case["case_id"]]},
        "receipt_kind": {"type": "string", "enum": [RECEIPT_KIND]},
        "source_public_case_hash": {
            "type": "string",
            "enum": [hash_payload(public_case)],
        },
        "evidence_groups": {
            "type": "array",
            "uniqueItems": True,
            "items": group,
        },
        "context_unit_ids": {
            "type": "array",
            "uniqueItems": True,
            "items": {"type": "string", "enum": unit_ids},
        },
        "irrelevant_unit_ids": {
            "type": "array",
            "uniqueItems": True,
            "items": {"type": "string", "enum": unit_ids},
        },
        "all_units_assessed": {"type": "boolean", "enum": [True]},
        "uncertainty_state": {
            "type": "string",
            "enum": list(UNCERTAINTY_STATES),
        },
        "rationale": {"type": "string"},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(REQUIRED_FIELDS),
        "properties": properties,
    }


def build_evidence_set_task(
    *,
    public_case: dict[str, Any],
    adapter: Any,
) -> ProviderCognitiveTask:
    unit_ids = [unit["unit_id"] for unit in public_case["evidence_units"]]
    return ProviderCognitiveTask(
        task_id=f"scifact-v0-88-evidence-{public_case['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Construct minimal complete evidence groups before deciding the "
            "claim's global state. Each evidence group must contain exactly "
            "the sentence or sentence combination needed to support or refute "
            "the claim. Do not add explanatory context to a complete group. "
            "Put relevant but non-decisive sentences in context_unit_ids and "
            "unrelated sentences in irrelevant_unit_ids. A fragment of a "
            "multi-sentence warrant is not a complete evidence group. "
            "Alternative complete groups may be returned separately. Assess "
            "every supplied unit exactly once across evidence, context, and "
            "irrelevant partitions. Do not return a global claim label, "
            "candidate action, admission, promotion, retention, or utility."
        ),
        inputs={
            "benchmark_id": public_case["benchmark_id"],
            "case_id": public_case["case_id"],
            "cognitive_object": public_case["cognitive_object"],
            "evidence_units": public_case["evidence_units"],
            "source_public_case_hash": hash_payload(public_case),
            "private_reference_available": False,
            "global_claim_label_requested": False,
            "policy_action_requested": False,
        },
        allowed_evidence=unit_ids,
        expected_schema=evidence_set_schema(public_case),
        timeout_seconds=min(300, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure_and_abstain",
    )


def validate_evidence_set(
    receipt: dict[str, Any],
    *,
    public_case: dict[str, Any],
) -> list[str]:
    failures = []
    if set(receipt) != set(REQUIRED_FIELDS):
        failures.append("EVIDENCE_SET_SHAPE_INVALID")
    if receipt.get("case_id") != public_case["case_id"]:
        failures.append("EVIDENCE_SET_CASE_MISMATCH")
    if receipt.get("receipt_kind") != RECEIPT_KIND:
        failures.append("EVIDENCE_SET_KIND_INVALID")
    if receipt.get("source_public_case_hash") != hash_payload(public_case):
        failures.append("EVIDENCE_SET_SOURCE_HASH_INVALID")
    if receipt.get("all_units_assessed") is not True:
        failures.append("EVIDENCE_SET_ASSESSMENT_INCOMPLETE")
    if receipt.get("uncertainty_state") not in UNCERTAINTY_STATES:
        failures.append("EVIDENCE_SET_UNCERTAINTY_INVALID")
    allowed = {unit["unit_id"] for unit in public_case["evidence_units"]}
    groups = receipt.get("evidence_groups")
    group_ids = []
    group_units = []
    if not isinstance(groups, list):
        failures.append("EVIDENCE_SET_GROUPS_INVALID")
        groups = []
    for group in groups:
        if not isinstance(group, dict) or set(group) != set(GROUP_FIELDS):
            failures.append("EVIDENCE_SET_GROUP_SHAPE_INVALID")
            continue
        group_ids.append(group.get("group_id"))
        units = group.get("unit_ids")
        if (
            not isinstance(group.get("group_id"), str)
            or not group["group_id"].strip()
            or group.get("relation") not in GROUP_RELATIONS
            or not isinstance(units, list)
            or not units
            or len(units) != len(set(units))
            or not set(units).issubset(allowed)
            or not isinstance(group.get("rationale"), str)
            or not group["rationale"].strip()
        ):
            failures.append("EVIDENCE_SET_GROUP_VALUE_INVALID")
            continue
        group_units.extend(units)
    if len(group_ids) != len(set(group_ids)):
        failures.append("EVIDENCE_SET_GROUP_ID_DUPLICATE")
    if len(group_units) != len(set(group_units)):
        failures.append("EVIDENCE_SET_UNIT_IN_MULTIPLE_GROUPS")
    context = receipt.get("context_unit_ids")
    irrelevant = receipt.get("irrelevant_unit_ids")
    if not _valid_unit_list(context, allowed):
        failures.append("EVIDENCE_SET_CONTEXT_INVALID")
        context = []
    if not _valid_unit_list(irrelevant, allowed):
        failures.append("EVIDENCE_SET_IRRELEVANT_INVALID")
        irrelevant = []
    partitions = [set(group_units), set(context), set(irrelevant)]
    if any(
        partitions[left].intersection(partitions[right])
        for left in range(3)
        for right in range(left + 1, 3)
    ):
        failures.append("EVIDENCE_SET_PARTITION_OVERLAP")
    if set().union(*partitions) != allowed:
        failures.append("EVIDENCE_SET_PARTITION_INCOMPLETE")
    rationale = receipt.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        failures.append("EVIDENCE_SET_RATIONALE_MISSING")
    forbidden = {
        "claim_state", "admission", "promotion", "retention", "utility",
        "candidate_state", "runtime_action",
    }
    if forbidden.intersection({key.casefold() for key in receipt}):
        failures.append("EVIDENCE_SET_POLICY_OR_LABEL_AUTHORITY_PRESENT")
    return sorted(set(failures))


def _valid_unit_list(value: Any, allowed: set[str]) -> bool:
    return (
        isinstance(value, list)
        and len(value) == len(set(value))
        and set(value).issubset(allowed)
    )
