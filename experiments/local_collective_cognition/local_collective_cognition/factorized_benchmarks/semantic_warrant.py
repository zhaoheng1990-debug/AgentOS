"""Provider contract and strict validation for v0.87 semantic warrants."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderCognitiveTask

from ..provider_telemetry import hash_payload

TASK_KIND = "SCIFACT_SEMANTIC_WARRANT_V0_87"
RECEIPT_KIND = "SEMANTIC_WARRANT"
CLAIM_STATES = (
    "SUPPORTED",
    "REFUTED",
    "NOT_ENOUGH_INFO",
    "UNCERTAIN",
)
UNCERTAINTY_STATES = ("RESOLVED", "MATERIAL_UNCERTAINTY")
REQUIRED_FIELDS = (
    "case_id",
    "receipt_kind",
    "source_public_case_hash",
    "claim_state",
    "selected_unit_ids",
    "all_units_assessed",
    "uncertainty_state",
    "rationale",
)
FORBIDDEN_POLICY_FIELDS = {
    "admission",
    "disposition",
    "promotion",
    "retention",
    "utility",
    "write",
    "candidate_state",
}


def warrant_schema(public_case: dict[str, Any]) -> dict[str, Any]:
    unit_ids = [unit["unit_id"] for unit in public_case["evidence_units"]]
    properties = {
        "case_id": {"type": "string", "enum": [public_case["case_id"]]},
        "receipt_kind": {"type": "string", "enum": [RECEIPT_KIND]},
        "source_public_case_hash": {
            "type": "string",
            "enum": [hash_payload(public_case)],
        },
        "claim_state": {"type": "string", "enum": list(CLAIM_STATES)},
        "selected_unit_ids": {
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


def build_warrant_task(
    *,
    public_case: dict[str, Any],
    adapter: Any,
) -> ProviderCognitiveTask:
    unit_ids = [unit["unit_id"] for unit in public_case["evidence_units"]]
    return ProviderCognitiveTask(
        task_id=f"scifact-v0-87-{public_case['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Assess whether the supplied scientific evidence supports, refutes, "
            "or is insufficient for the exact claim. Select only the minimal "
            "complete sentence set needed for the judgment. A sentence that "
            "merely discusses the same topic is not a rationale. Use "
            "NOT_ENOUGH_INFO when no supplied sentence establishes either "
            "support or refutation. Use UNCERTAIN only for a material semantic "
            "conflict that cannot be resolved from the supplied text. Assess "
            "every unit. Return semantic judgment only. Do not recommend "
            "admission, promotion, retention, utility, candidate state, or any "
            "write action."
        ),
        inputs={
            "benchmark_id": public_case["benchmark_id"],
            "case_id": public_case["case_id"],
            "cognitive_object": public_case["cognitive_object"],
            "evidence_units": public_case["evidence_units"],
            "source_public_case_hash": hash_payload(public_case),
            "private_reference_available": False,
            "policy_action_requested": False,
        },
        allowed_evidence=unit_ids,
        expected_schema=warrant_schema(public_case),
        timeout_seconds=min(300, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure_and_abstain",
    )


def validate_warrant(
    receipt: dict[str, Any],
    *,
    public_case: dict[str, Any],
) -> list[str]:
    failures = []
    if set(receipt) != set(REQUIRED_FIELDS):
        failures.append("SEMANTIC_WARRANT_SHAPE_INVALID")
    if receipt.get("case_id") != public_case["case_id"]:
        failures.append("SEMANTIC_WARRANT_CASE_MISMATCH")
    if receipt.get("receipt_kind") != RECEIPT_KIND:
        failures.append("SEMANTIC_WARRANT_KIND_INVALID")
    if receipt.get("source_public_case_hash") != hash_payload(public_case):
        failures.append("SEMANTIC_WARRANT_SOURCE_HASH_INVALID")
    if receipt.get("claim_state") not in CLAIM_STATES:
        failures.append("SEMANTIC_WARRANT_CLAIM_STATE_INVALID")
    if receipt.get("uncertainty_state") not in UNCERTAINTY_STATES:
        failures.append("SEMANTIC_WARRANT_UNCERTAINTY_INVALID")
    if receipt.get("all_units_assessed") is not True:
        failures.append("SEMANTIC_WARRANT_ASSESSMENT_INCOMPLETE")
    selected = receipt.get("selected_unit_ids")
    allowed = {unit["unit_id"] for unit in public_case["evidence_units"]}
    if (
        not isinstance(selected, list)
        or len(selected) != len(set(selected))
        or not set(selected).issubset(allowed)
    ):
        failures.append("SEMANTIC_WARRANT_UNIT_SELECTION_INVALID")
        selected = []
    state = receipt.get("claim_state")
    uncertainty = receipt.get("uncertainty_state")
    if state in {"SUPPORTED", "REFUTED"} and not selected:
        failures.append("SEMANTIC_WARRANT_STRONG_STATE_UNGROUNDED")
    if state == "NOT_ENOUGH_INFO" and selected:
        failures.append("SEMANTIC_WARRANT_NEI_HAS_RATIONALE")
    if (state == "UNCERTAIN") != (uncertainty == "MATERIAL_UNCERTAINTY"):
        failures.append("SEMANTIC_WARRANT_UNCERTAINTY_INCONSISTENT")
    rationale = receipt.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        failures.append("SEMANTIC_WARRANT_RATIONALE_MISSING")
    lowered = {key.casefold() for key in receipt}
    if lowered.intersection(FORBIDDEN_POLICY_FIELDS):
        failures.append("SEMANTIC_WARRANT_POLICY_AUTHORITY_PRESENT")
    return sorted(set(failures))
