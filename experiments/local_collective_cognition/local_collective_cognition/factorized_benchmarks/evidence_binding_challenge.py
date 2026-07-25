"""Context-isolated veto-only challenge contract for evidence groups."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderCognitiveTask

from ..provider_telemetry import hash_payload

TASK_KIND = "SCIFACT_EVIDENCE_BINDING_CHALLENGE_V0_89"
RECEIPT_KIND = "EVIDENCE_BINDING_CHALLENGE"
VERDICTS = (
    "PASS_DIRECT",
    "VETO_UNSUPPORTED_BRIDGE",
    "VETO_SCOPE_MISMATCH",
    "VETO_DIRECTION_OR_POLARITY",
    "VETO_CAUSAL_OR_QUANTIFIER_UPGRADE",
    "VETO_INSUFFICIENT_BINDING",
)
ISSUE_CODES = (
    "NONE",
    "ENTITY_OR_POPULATION_MISMATCH",
    "OUTCOME_OR_RELATION_MISMATCH",
    "DIRECTION_OR_POLARITY_MISSING",
    "QUANTIFIER_OR_SCOPE_MISMATCH",
    "CAUSAL_OR_MODALITY_UPGRADE",
    "CONDITION_OR_TIME_MISMATCH",
    "UNSTATED_SCIENTIFIC_BRIDGE",
    "GROUP_NOT_MINIMAL",
)
CHALLENGE_FIELDS = (
    "group_id",
    "verdict",
    "issue_codes",
    "unit_ids",
    "rationale",
)
REQUIRED_FIELDS = (
    "case_id",
    "receipt_kind",
    "source_public_case_hash",
    "source_evidence_set_hash",
    "group_challenges",
    "all_groups_assessed",
    "rationale",
)


def build_binding_challenge_task(
    *,
    public_case: dict[str, Any],
    evidence_receipt: dict[str, Any],
    adapter: Any,
) -> ProviderCognitiveTask:
    group_ids = [
        group["group_id"] for group in evidence_receipt["evidence_groups"]
    ]
    unit_ids = [unit["unit_id"] for unit in public_case["evidence_units"]]
    return ProviderCognitiveTask(
        task_id=f"scifact-v0-89-challenge-{public_case['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Independently challenge each proposed evidence group. You do "
            "not have access to another binding judgment, a claim-scope "
            "judgment, a candidate decision, or a private reference. Pass a "
            "group only when its supplied sentences directly bind the "
            "claim's entities, outcome, direction, quantifier, causality, "
            "and conditions without importing an unstated scientific bridge. "
            "Otherwise select the most specific veto and issue codes. This "
            "role may veto but must never propose a claim state, candidate "
            "action, admission, promotion, retention, or utility."
        ),
        inputs={
            "benchmark_id": public_case["benchmark_id"],
            "case_id": public_case["case_id"],
            "claim": public_case["cognitive_object"]["claim"],
            "evidence_units": public_case["evidence_units"],
            "evidence_groups": evidence_receipt["evidence_groups"],
            "source_public_case_hash": hash_payload(public_case),
            "source_evidence_set_hash": hash_payload(evidence_receipt),
            "private_reference_available": False,
            "primary_binding_receipt_available": False,
            "scope_receipt_available": False,
            "candidate_decision_available": False,
            "promotion_requested": False,
        },
        allowed_evidence=unit_ids,
        expected_schema=_schema(public_case, evidence_receipt),
        timeout_seconds=min(300, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure_and_abstain",
    )


def validate_binding_challenge(
    receipt: dict[str, Any],
    *,
    public_case: dict[str, Any],
    evidence_receipt: dict[str, Any],
) -> list[str]:
    failures = []
    if set(receipt) != set(REQUIRED_FIELDS):
        failures.append("BINDING_CHALLENGE_SHAPE_INVALID")
    if receipt.get("case_id") != public_case["case_id"]:
        failures.append("BINDING_CHALLENGE_CASE_MISMATCH")
    if receipt.get("receipt_kind") != RECEIPT_KIND:
        failures.append("BINDING_CHALLENGE_KIND_INVALID")
    if receipt.get("source_public_case_hash") != hash_payload(public_case):
        failures.append("BINDING_CHALLENGE_PUBLIC_HASH_INVALID")
    if receipt.get("source_evidence_set_hash") != hash_payload(
        evidence_receipt
    ):
        failures.append("BINDING_CHALLENGE_EVIDENCE_HASH_INVALID")
    if receipt.get("all_groups_assessed") is not True:
        failures.append("BINDING_CHALLENGE_ASSESSMENT_INCOMPLETE")
    group_map = {
        group["group_id"]: group
        for group in evidence_receipt["evidence_groups"]
    }
    challenges = receipt.get("group_challenges")
    seen = []
    if not isinstance(challenges, list):
        failures.append("BINDING_CHALLENGE_GROUPS_INVALID")
        challenges = []
    for challenge in challenges:
        if (
            not isinstance(challenge, dict)
            or set(challenge) != set(CHALLENGE_FIELDS)
        ):
            failures.append("BINDING_CHALLENGE_GROUP_SHAPE_INVALID")
            continue
        group_id = challenge.get("group_id")
        seen.append(group_id)
        group = group_map.get(group_id)
        issues = challenge.get("issue_codes")
        units = challenge.get("unit_ids")
        if (
            group is None
            or challenge.get("verdict") not in VERDICTS
            or not isinstance(issues, list)
            or not issues
            or len(issues) != len(set(issues))
            or not set(issues).issubset(ISSUE_CODES)
            or not isinstance(units, list)
            or len(units) != len(set(units))
            or not set(units).issubset(set(group["unit_ids"]))
            or not _nonempty(challenge.get("rationale"))
        ):
            failures.append("BINDING_CHALLENGE_GROUP_VALUE_INVALID")
            continue
        if (
            challenge["verdict"] == "PASS_DIRECT"
            and issues != ["NONE"]
        ):
            failures.append("BINDING_CHALLENGE_PASS_ISSUES_INCONSISTENT")
        if challenge["verdict"] == "PASS_DIRECT" and not units:
            failures.append("BINDING_CHALLENGE_PASS_EVIDENCE_MISSING")
        if (
            challenge["verdict"] != "PASS_DIRECT"
            and (not issues or "NONE" in issues)
        ):
            failures.append("BINDING_CHALLENGE_VETO_ISSUES_INCONSISTENT")
    if set(seen) != set(group_map) or len(seen) != len(set(seen)):
        failures.append("BINDING_CHALLENGE_GROUP_COVERAGE_INVALID")
    if not _nonempty(receipt.get("rationale")):
        failures.append("BINDING_CHALLENGE_RATIONALE_MISSING")
    forbidden = {
        "claim_state",
        "runtime_action",
        "candidate_state",
        "admission",
        "promotion",
        "retention",
        "utility",
    }
    if forbidden.intersection({key.casefold() for key in receipt}):
        failures.append("BINDING_CHALLENGE_POLICY_AUTHORITY_PRESENT")
    return sorted(set(failures))


def _schema(
    public_case: dict[str, Any],
    evidence_receipt: dict[str, Any],
) -> dict[str, Any]:
    group_ids = [
        group["group_id"] for group in evidence_receipt["evidence_groups"]
    ]
    unit_ids = [unit["unit_id"] for unit in public_case["evidence_units"]]
    challenge = {
        "type": "object",
        "additionalProperties": False,
        "required": list(CHALLENGE_FIELDS),
        "properties": {
            "group_id": {"type": "string", "enum": group_ids},
            "verdict": {"type": "string", "enum": list(VERDICTS)},
            "issue_codes": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {"type": "string", "enum": list(ISSUE_CODES)},
            },
            "unit_ids": {
                "type": "array",
                "uniqueItems": True,
                "items": {"type": "string", "enum": unit_ids},
            },
            "rationale": {"type": "string"},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(REQUIRED_FIELDS),
        "properties": {
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
            "group_challenges": {
                "type": "array",
                "minItems": len(group_ids),
                "maxItems": len(group_ids),
                "uniqueItems": True,
                "items": challenge,
            },
            "all_groups_assessed": {"type": "boolean", "enum": [True]},
            "rationale": {"type": "string"},
        },
    }


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
