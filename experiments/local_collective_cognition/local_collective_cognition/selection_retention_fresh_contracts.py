"""Frozen contracts for fresh selection-retention validation v0.64."""

from __future__ import annotations

from typing import Any

from .provider_telemetry import hash_payload
from .selection_retention_fresh_holdout import (
    audit_selection_retention_fresh_holdout,
    validate_selection_retention_fresh_holdout,
)


RUNTIME_VERSION = "selection_retention_fresh_runtime_v0_64"
BINDING_ROLES = ("EVIDENCE_BINDER", "BINDING_SKEPTIC")
STATE_ROLES = ("STATE_ASSESSOR", "STATE_SKEPTIC")
SELECTION_ROLES = ("SELECTION_PLANNER", "SELECTION_SKEPTIC")
RETENTION_ROLES = ("RETENTION_ASSESSOR", "RETENTION_SKEPTIC")
REFERENCE_STATES = (
    "SUPPORTED_EFFECT",
    "SUPPORTED_NULL",
    "UNRESOLVED",
)
RETENTION_STATES = (
    "PENDING_RETENTION_REVIEW",
    "QUARANTINED_SELECTION_EVIDENCE",
    "PENDING_SELECTION_EVIDENCE",
)


def build_fresh_preregistration(
    *,
    corpus: dict[str, Any],
    construction_audit: dict[str, Any],
    source_closure: dict[str, Any],
) -> dict[str, Any]:
    validate_selection_retention_fresh_holdout(corpus)
    _validate_hash_bound(construction_audit)
    _validate_hash_bound(source_closure)
    expected_audit = audit_selection_retention_fresh_holdout(corpus)
    if construction_audit != expected_audit:
        raise ValueError("v064_construction_audit_invalid")
    if construction_audit["formal_execution_authorized"] is not True:
        raise ValueError("v064_construction_not_authorized")
    if (
        source_closure.get("decision")
        != "PASS_TYPED_EVIDENCE_BINDING_CALIBRATION"
        or source_closure.get("core_contract_sync_eligible") is not True
        or source_closure.get("fresh_generalization_claim") is not False
    ):
        raise ValueError("v064_source_closure_invalid")
    case_count = corpus["case_count"]
    relation_count = corpus["relation_count"]
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_construction_audit_hash": construction_audit[
            "artifact_hash"
        ],
        "source_v0_63_closure_hash": source_closure["artifact_hash"],
        "binding_roles": list(BINDING_ROLES),
        "state_roles": list(STATE_ROLES),
        "selection_roles": list(SELECTION_ROLES),
        "retention_roles": list(RETENTION_ROLES),
        "required_binding_receipt_count": case_count * 2,
        "required_binding_relation_consensus_count": relation_count,
        "maximum_binding_conflict_count": 0,
        "maximum_binding_contract_failure_count": 0,
        "required_state_receipt_count": case_count * 2,
        "maximum_state_contract_failure_count": 0,
        "maximum_state_reference_mismatch_count": 0,
        "maximum_state_cross_role_disagreement_count": 0,
        "required_selection_receipt_count": case_count * 2,
        "required_selection_consensus_count": case_count,
        "maximum_selection_contract_failure_count": 0,
        "maximum_selection_cross_role_disagreement_count": 0,
        "maximum_selection_reference_mismatch_count": 0,
        "required_retention_receipt_count": case_count * 2,
        "required_retention_consensus_count": case_count,
        "maximum_retention_contract_failure_count": 0,
        "maximum_retention_cross_role_disagreement_count": 0,
        "maximum_retention_reference_mismatch_count": 0,
        "primary_evidence_consensus": "STRICT_SET_EQUALITY",
        "auxiliary_evidence_policy": "NONCONFLICTING_TYPED_UNION",
        "consequence_assignment_default": "UNASSIGNED",
        "validity_is_noncompensable": True,
        "semantic_prompt_changes_after_first_receipt_allowed": False,
        "maximum_attempts_per_task": 2,
        "maximum_provider_tasks": case_count * 8,
        "maximum_physical_attempts": 80,
        "hard_token_ceiling": 300000,
        "fresh_generalization_required": True,
        "alpha_22_requires_all_gates": True,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def relation_ids_for(item: dict[str, Any]) -> list[str]:
    return [
        f"REL-{value['object_id']}-{item['focal_object_id']}"
        for value in item["object_registry"]
        if value["object_id"] != item["focal_object_id"]
    ]


def expected_states(
    corpus: dict[str, Any],
) -> dict[str, dict[str, str]]:
    return {
        case_id: {
            relation_id: reference["relation_truth_state"]
            for relation_id, reference in private[
                "typed_relation_reference"
            ].items()
        }
        for case_id, private in corpus["private_provenance"][
            "bindings"
        ].items()
    }


def selection_schema(
    *,
    item: dict[str, Any],
    role: str,
    refs: tuple[str, ...],
) -> dict[str, Any]:
    alternatives = [
        value["alternative_ref"]
        for value in item["selection_alternatives"]
    ]
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "selection_role": {"type": "string", "enum": [role]},
        "source_item_hash": {
            "type": "string",
            "enum": [hash_payload(item)],
        },
        "ranked_alternative_refs": {
            "type": "array",
            "minItems": len(alternatives),
            "maxItems": len(alternatives),
            "uniqueItems": True,
            "items": {"type": "string", "enum": alternatives},
        },
        "selected_ref": {"type": "string", "enum": alternatives},
        "rejected_refs": {
            "type": "array",
            "uniqueItems": True,
            "items": {"type": "string", "enum": alternatives},
        },
        "deferred_refs": {
            "type": "array",
            "uniqueItems": True,
            "items": {"type": "string", "enum": alternatives},
        },
        "path_change_hypothesis": {"type": "string"},
        "expected_cbit_gain": {"type": "number"},
        "residual_risk": {"type": "number"},
        "uncertainty": {"type": "number"},
        "rationale": {"type": "string"},
        "evidence_refs": {
            "type": "array",
            "items": {"type": "string", "enum": list(refs)},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def validate_selection_receipt(
    *,
    receipt: dict[str, Any],
    item: dict[str, Any],
    role: str,
    refs: tuple[str, ...],
) -> list[str]:
    failures = []
    if receipt.get("case_id") != item["case_id"]:
        failures.append("SELECTION_CASE_MISMATCH")
    if receipt.get("selection_role") != role:
        failures.append("SELECTION_ROLE_MISMATCH")
    if receipt.get("source_item_hash") != hash_payload(item):
        failures.append("SELECTION_ITEM_HASH_MISMATCH")
    if receipt.get("evidence_refs") != list(refs):
        failures.append("SELECTION_EVIDENCE_SCOPE_MISMATCH")
    alternatives = {
        value["alternative_ref"]
        for value in item["selection_alternatives"]
    }
    ranked = receipt.get("ranked_alternative_refs")
    rejected = receipt.get("rejected_refs")
    deferred = receipt.get("deferred_refs")
    selected = receipt.get("selected_ref")
    if (
        not isinstance(ranked, list)
        or len(ranked) != len(set(ranked))
        or set(ranked) != alternatives
    ):
        failures.append("SELECTION_RANKING_COVERAGE_INVALID")
    if selected not in alternatives:
        failures.append("SELECTION_SELECTED_REF_INVALID")
    if (
        not isinstance(rejected, list)
        or not isinstance(deferred, list)
        or len(rejected) != len(set(rejected))
        or len(deferred) != len(set(deferred))
        or set(rejected).intersection(deferred)
        or {selected, *rejected, *deferred} != alternatives
        or len({selected, *rejected, *deferred}) != 3
    ):
        failures.append("SELECTION_PARTITION_INVALID")
    for field in ("residual_risk", "uncertainty"):
        value = receipt.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 0 <= value <= 1
        ):
            failures.append(f"SELECTION_{field.upper()}_INVALID")
    if isinstance(receipt.get("expected_cbit_gain"), bool) or not isinstance(
        receipt.get("expected_cbit_gain"), (int, float)
    ):
        failures.append("SELECTION_EXPECTED_CBIT_INVALID")
    if any(
        forbidden in receipt
        for forbidden in (
            "observed_cbit_gain",
            "consequence_ref",
            "validity_state",
            "retention_candidate_state",
        )
    ):
        failures.append("SELECTION_CONSEQUENCE_LEAK")
    return sorted(set(failures))


def build_selection_consensus(
    *,
    item: dict[str, Any],
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, Any]:
    disagreements = []
    for field in ("selected_ref", "rejected_refs", "deferred_refs"):
        left_value = (
            set(left[field]) if isinstance(left[field], list) else left[field]
        )
        right_value = (
            set(right[field])
            if isinstance(right[field], list)
            else right[field]
        )
        if left_value != right_value:
            disagreements.append(f"{field.upper()}_DISAGREEMENT")
    commitment = {
        "consensus_version": RUNTIME_VERSION,
        "case_id": item["case_id"],
        "source_item_hash": hash_payload(item),
        "source_role_receipt_hashes": {
            SELECTION_ROLES[0]: hash_payload(left),
            SELECTION_ROLES[1]: hash_payload(right),
        },
        "selected_ref": (
            left["selected_ref"] if not disagreements else None
        ),
        "rejected_refs": (
            sorted(left["rejected_refs"]) if not disagreements else []
        ),
        "deferred_refs": (
            sorted(left["deferred_refs"]) if not disagreements else []
        ),
        "path_change_hypotheses": [
            left["path_change_hypothesis"],
            right["path_change_hypothesis"],
        ],
        "expected_cbit_estimates": [
            left["expected_cbit_gain"],
            right["expected_cbit_gain"],
        ],
        "disagreements": disagreements,
        "selection_ready": not disagreements,
        "consequence_known": False,
        "provider_selection_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def retention_schema(
    *,
    case_id: str,
    role: str,
    selection_hash: str,
    consequence_hash: str,
    refs: tuple[str, ...],
) -> dict[str, Any]:
    properties = {
        "case_id": {"type": "string", "enum": [case_id]},
        "retention_role": {"type": "string", "enum": [role]},
        "source_selection_hash": {
            "type": "string",
            "enum": [selection_hash],
        },
        "source_consequence_hash": {
            "type": "string",
            "enum": [consequence_hash],
        },
        "applicability_delta": {"type": "number"},
        "validity_state": {
            "type": "string",
            "enum": ["CURRENT", "UNKNOWN", "DRIFTED", "STALE"],
        },
        "consequence_supported": {"type": "boolean"},
        "observed_cbit_interpretation": {
            "type": "string",
            "enum": ["POSITIVE", "NEGATIVE", "NEUTRAL"],
        },
        "recommended_candidate_state": {
            "type": "string",
            "enum": list(RETENTION_STATES),
        },
        "residual_risk": {"type": "number"},
        "uncertainty": {"type": "number"},
        "rationale": {"type": "string"},
        "evidence_refs": {
            "type": "array",
            "items": {"type": "string", "enum": list(refs)},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def validate_retention_receipt(
    *,
    receipt: dict[str, Any],
    case_id: str,
    role: str,
    selection_hash: str,
    consequence_hash: str,
    refs: tuple[str, ...],
) -> list[str]:
    failures = []
    expected = {
        "case_id": case_id,
        "retention_role": role,
        "source_selection_hash": selection_hash,
        "source_consequence_hash": consequence_hash,
        "evidence_refs": list(refs),
    }
    for field, value in expected.items():
        if receipt.get(field) != value:
            failures.append(f"RETENTION_{field.upper()}_MISMATCH")
    if receipt.get("validity_state") not in {
        "CURRENT",
        "UNKNOWN",
        "DRIFTED",
        "STALE",
    }:
        failures.append("RETENTION_VALIDITY_INVALID")
    if receipt.get("recommended_candidate_state") not in RETENTION_STATES:
        failures.append("RETENTION_STATE_INVALID")
    for field in ("residual_risk", "uncertainty"):
        value = receipt.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 0 <= value <= 1
        ):
            failures.append(f"RETENTION_{field.upper()}_INVALID")
    delta = receipt.get("applicability_delta")
    if (
        isinstance(delta, bool)
        or not isinstance(delta, (int, float))
        or not -1 <= delta <= 1
    ):
        failures.append("RETENTION_APPLICABILITY_DELTA_INVALID")
    if receipt.get("consequence_supported") is not True:
        failures.append("RETENTION_CONSEQUENCE_UNSUPPORTED")
    if any(
        receipt.get(field) is True
        for field in (
            "retention_write_allowed",
            "baseline_write_allowed",
            "production_authority",
        )
    ):
        failures.append("RETENTION_FORBIDDEN_AUTHORITY")
    return sorted(set(failures))


def build_retention_consensus(
    *,
    case_id: str,
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, Any]:
    fields = (
        "validity_state",
        "observed_cbit_interpretation",
        "recommended_candidate_state",
    )
    disagreements = [
        f"{field.upper()}_DISAGREEMENT"
        for field in fields
        if left[field] != right[field]
    ]
    commitment = {
        "consensus_version": RUNTIME_VERSION,
        "case_id": case_id,
        "source_role_receipt_hashes": {
            RETENTION_ROLES[0]: hash_payload(left),
            RETENTION_ROLES[1]: hash_payload(right),
        },
        "validity_state": (
            left["validity_state"] if not disagreements else None
        ),
        "observed_cbit_interpretation": (
            left["observed_cbit_interpretation"]
            if not disagreements
            else None
        ),
        "recommended_candidate_state": (
            left["recommended_candidate_state"]
            if not disagreements
            else None
        ),
        "applicability_delta_estimates": [
            left["applicability_delta"],
            right["applicability_delta"],
        ],
        "disagreements": disagreements,
        "retention_ready": not disagreements,
        "consequence_assignment_state": "UNASSIGNED",
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_hash_bound(value: dict[str, Any]) -> None:
    _validate_hash_bound(value)


def _validate_hash_bound(value: dict[str, Any]) -> None:
    field = "run_hash" if "run_hash" in value else "artifact_hash"
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError("v064_hash_binding_invalid")
