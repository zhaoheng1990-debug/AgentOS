"""Claim-scope aggregation contract over frozen evidence groups."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderCognitiveTask

from ..provider_telemetry import hash_payload

TASK_KIND = "SCIFACT_CLAIM_SCOPE_V0_88"
RECEIPT_KIND = "CLAIM_SCOPE"
CLAIM_SCOPES = (
    "AGGREGATE_GENERALIZATION",
    "SUBGROUP_OR_SPECIFIC",
    "CONDITIONAL",
    "ABSOLUTE_UNIVERSAL",
    "UNSPECIFIED",
)
EVIDENCE_SCOPES = (
    "AGGREGATE",
    "SUBGROUP",
    "CONDITIONAL",
    "MECHANISTIC",
    "UNSPECIFIED",
)
CLAIM_RELATIONS = (
    "DIRECTLY_RESOLVES",
    "QUALIFIES",
    "EXCEPTION",
    "OVERTURNS",
    "OUT_OF_SCOPE",
)
CLAIM_STATES = (
    "SUPPORTED",
    "REFUTED",
    "NOT_ENOUGH_INFO",
    "UNCERTAIN",
)
EXCEPTION_EFFECTS = (
    "NO_MATERIAL_EXCEPTION",
    "QUALIFIES_NOT_OVERTURNS",
    "OVERTURNS",
    "MATERIAL_SCOPE_CONFLICT",
    "NOT_APPLICABLE",
)
ASSESSMENT_FIELDS = ("group_id", "scope_level", "claim_relation", "rationale")
REQUIRED_FIELDS = (
    "case_id",
    "receipt_kind",
    "source_public_case_hash",
    "source_evidence_set_hash",
    "claim_scope",
    "group_assessments",
    "claim_state",
    "exception_effect",
    "all_groups_assessed",
    "rationale",
)


def claim_scope_schema(
    public_case: dict[str, Any],
    evidence_receipt: dict[str, Any],
) -> dict[str, Any]:
    group_ids = [
        group["group_id"] for group in evidence_receipt["evidence_groups"]
    ]
    assessment = {
        "type": "object",
        "additionalProperties": False,
        "required": list(ASSESSMENT_FIELDS),
        "properties": {
            "group_id": {"type": "string", "enum": group_ids},
            "scope_level": {
                "type": "string",
                "enum": list(EVIDENCE_SCOPES),
            },
            "claim_relation": {
                "type": "string",
                "enum": list(CLAIM_RELATIONS),
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
        "source_evidence_set_hash": {
            "type": "string",
            "enum": [hash_payload(evidence_receipt)],
        },
        "claim_scope": {"type": "string", "enum": list(CLAIM_SCOPES)},
        "group_assessments": {
            "type": "array",
            "minItems": len(group_ids),
            "maxItems": len(group_ids),
            "uniqueItems": True,
            "items": assessment,
        },
        "claim_state": {"type": "string", "enum": list(CLAIM_STATES)},
        "exception_effect": {
            "type": "string",
            "enum": list(EXCEPTION_EFFECTS),
        },
        "all_groups_assessed": {"type": "boolean", "enum": [True]},
        "rationale": {"type": "string"},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(REQUIRED_FIELDS),
        "properties": properties,
    }


def build_claim_scope_task(
    *,
    public_case: dict[str, Any],
    evidence_receipt: dict[str, Any],
    adapter: Any,
) -> ProviderCognitiveTask:
    group_ids = [
        group["group_id"] for group in evidence_receipt["evidence_groups"]
    ]
    return ProviderCognitiveTask(
        task_id=f"scifact-v0-88-scope-{public_case['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Judge the claim only after respecting the supplied evidence-group "
            "boundaries. Identify whether the claim is aggregate, subgroup, "
            "conditional, absolute, or underspecified. Assess every evidence "
            "group's scope and relation to the claim. A subgroup exception "
            "does not automatically overturn an aggregate conclusion; state "
            "whether it merely qualifies, materially conflicts with, or "
            "overturns the claim. Use MATERIAL_SCOPE_CONFLICT and UNCERTAIN "
            "when the supplied evidence does not resolve that aggregation. "
            "Do not return admission, promotion, retention, utility, "
            "candidate state, or a write action."
        ),
        inputs={
            "benchmark_id": public_case["benchmark_id"],
            "case_id": public_case["case_id"],
            "cognitive_object": public_case["cognitive_object"],
            "evidence_units": public_case["evidence_units"],
            "evidence_set_receipt": evidence_receipt,
            "source_public_case_hash": hash_payload(public_case),
            "source_evidence_set_hash": hash_payload(evidence_receipt),
            "private_reference_available": False,
            "policy_action_requested": False,
        },
        allowed_evidence=group_ids or [
            unit["unit_id"] for unit in public_case["evidence_units"]
        ],
        expected_schema=claim_scope_schema(public_case, evidence_receipt),
        timeout_seconds=min(300, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure_and_abstain",
    )


def validate_claim_scope(
    receipt: dict[str, Any],
    *,
    public_case: dict[str, Any],
    evidence_receipt: dict[str, Any],
) -> list[str]:
    failures = []
    if set(receipt) != set(REQUIRED_FIELDS):
        failures.append("CLAIM_SCOPE_SHAPE_INVALID")
    if receipt.get("case_id") != public_case["case_id"]:
        failures.append("CLAIM_SCOPE_CASE_MISMATCH")
    if receipt.get("receipt_kind") != RECEIPT_KIND:
        failures.append("CLAIM_SCOPE_KIND_INVALID")
    if receipt.get("source_public_case_hash") != hash_payload(public_case):
        failures.append("CLAIM_SCOPE_PUBLIC_HASH_INVALID")
    if receipt.get("source_evidence_set_hash") != hash_payload(evidence_receipt):
        failures.append("CLAIM_SCOPE_EVIDENCE_HASH_INVALID")
    if receipt.get("claim_scope") not in CLAIM_SCOPES:
        failures.append("CLAIM_SCOPE_TYPE_INVALID")
    if receipt.get("claim_state") not in CLAIM_STATES:
        failures.append("CLAIM_SCOPE_STATE_INVALID")
    if receipt.get("exception_effect") not in EXCEPTION_EFFECTS:
        failures.append("CLAIM_SCOPE_EXCEPTION_EFFECT_INVALID")
    if receipt.get("all_groups_assessed") is not True:
        failures.append("CLAIM_SCOPE_ASSESSMENT_INCOMPLETE")
    expected_ids = {
        group["group_id"] for group in evidence_receipt["evidence_groups"]
    }
    assessments = receipt.get("group_assessments")
    seen_ids = []
    if not isinstance(assessments, list):
        failures.append("CLAIM_SCOPE_GROUP_ASSESSMENTS_INVALID")
        assessments = []
    for assessment in assessments:
        if (
            not isinstance(assessment, dict)
            or set(assessment) != set(ASSESSMENT_FIELDS)
        ):
            failures.append("CLAIM_SCOPE_GROUP_ASSESSMENT_SHAPE_INVALID")
            continue
        seen_ids.append(assessment.get("group_id"))
        if (
            assessment.get("group_id") not in expected_ids
            or assessment.get("scope_level") not in EVIDENCE_SCOPES
            or assessment.get("claim_relation") not in CLAIM_RELATIONS
            or not isinstance(assessment.get("rationale"), str)
            or not assessment["rationale"].strip()
        ):
            failures.append("CLAIM_SCOPE_GROUP_ASSESSMENT_VALUE_INVALID")
    if set(seen_ids) != expected_ids or len(seen_ids) != len(set(seen_ids)):
        failures.append("CLAIM_SCOPE_GROUP_COVERAGE_INVALID")
    state = receipt.get("claim_state")
    exception = receipt.get("exception_effect")
    if (state == "UNCERTAIN") != (exception == "MATERIAL_SCOPE_CONFLICT"):
        failures.append("CLAIM_SCOPE_UNCERTAINTY_INCONSISTENT")
    if not expected_ids and state not in {"NOT_ENOUGH_INFO", "UNCERTAIN"}:
        failures.append("CLAIM_SCOPE_STRONG_STATE_WITHOUT_EVIDENCE")
    if not expected_ids and exception not in {
        "NOT_APPLICABLE", "MATERIAL_SCOPE_CONFLICT",
    }:
        failures.append("CLAIM_SCOPE_EMPTY_GROUP_EXCEPTION_INVALID")
    rationale = receipt.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        failures.append("CLAIM_SCOPE_RATIONALE_MISSING")
    forbidden = {
        "admission", "promotion", "retention", "utility", "candidate_state",
        "runtime_action",
    }
    if forbidden.intersection({key.casefold() for key in receipt}):
        failures.append("CLAIM_SCOPE_POLICY_AUTHORITY_PRESENT")
    return sorted(set(failures))
