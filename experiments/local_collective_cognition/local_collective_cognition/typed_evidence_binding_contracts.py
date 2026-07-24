"""Typed relation-evidence contracts for the v0.63 mechanism calibration."""

from __future__ import annotations

from typing import Any

from .portfolio_critic_fresh_holdout import (
    validate_portfolio_critic_fresh_holdout_v0_61_1,
)
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "typed_evidence_binding_calibration_v0_63"
BINDING_ROLES = ("EVIDENCE_BINDER", "BINDING_SKEPTIC")
STATE_ROLES = ("STATE_ASSESSOR", "STATE_SKEPTIC")
REFERENCE_STATES = (
    "SUPPORTED_EFFECT",
    "SUPPORTED_NULL",
    "UNRESOLVED",
)
EVIDENCE_DESIGNS = (
    "INTERVENTION_OR_ROLLBACK",
    "MATCHED_NULL_COMPARISON",
    "UNTESTED_DIFFERENCE",
    "OTHER",
)
EVIDENCE_SPAN_FIELDS = (
    "primary_evidence_span_ids",
    "corroborating_evidence_span_ids",
    "counterevidence_span_ids",
    "gap_evidence_span_ids",
)
AUXILIARY_SPAN_FIELDS = EVIDENCE_SPAN_FIELDS[1:]


def build_typed_preregistration(
    *,
    corpus: dict[str, Any],
    source_closure: dict[str, Any],
) -> dict[str, Any]:
    validate_portfolio_critic_fresh_holdout_v0_61_1(corpus)
    _validate_artifact(source_closure)
    if (
        source_closure.get("decision")
        != "REJECT_RELATION_EVIDENCE_BINDING_CONSENSUS_GATE"
        or source_closure.get("typed_evidence_set_calibration_required")
        is not True
        or source_closure.get("state_assessment_executed") is not False
    ):
        raise ValueError("typed_binding_source_closure_invalid")
    relation_count = corpus["case_count"] * 5
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_closure_hash": source_closure["artifact_hash"],
        "binding_roles": list(BINDING_ROLES),
        "state_roles": list(STATE_ROLES),
        "required_binding_receipt_count": (
            corpus["case_count"] * len(BINDING_ROLES)
        ),
        "required_binding_relation_consensus_count": relation_count,
        "maximum_binding_conflict_count": 0,
        "maximum_binding_contract_failure_count": 0,
        "required_state_receipt_count": (
            corpus["case_count"] * len(STATE_ROLES)
        ),
        "maximum_state_contract_failure_count": 0,
        "maximum_state_reference_mismatch_count": 0,
        "maximum_state_cross_role_disagreement_count": 0,
        "required_recovered_coordinate": {
            "case_id": "PC-TRAFFIC",
            "relation_id": "REL-O3-O1",
            "required_state": "SUPPORTED_EFFECT",
        },
        "primary_evidence_consensus": "STRICT_SET_EQUALITY",
        "nonconflicting_auxiliary_evidence_policy": "TYPED_UNION",
        "cross_type_span_conflict_policy": "BLOCK",
        "corroboration_without_primary_promotion_allowed": False,
        "provider_binding_state_authority": False,
        "binding_roles_forbidden_from_truth_state": True,
        "state_roles_require_complete_binding_consensus": True,
        "maximum_provider_calls": (
            corpus["case_count"]
            * (len(BINDING_ROLES) + len(STATE_ROLES))
        ),
        "hard_token_ceiling": 220000,
        "formal_scope": "REVEALED_MECHANISM_CALIBRATION_ONLY",
        "fresh_generalization_claim_allowed": False,
        "core_contract_sync_requires_full_pass": True,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def typed_binding_schema(
    *,
    item: dict[str, Any],
    role: str,
    refs: tuple[str, ...],
) -> dict[str, Any]:
    relation_ids = relation_ids_for(item)
    object_ids = [value["object_id"] for value in item["object_registry"]]
    span_ids = [value["span_id"] for value in item["evidence_spans"]]
    span_array = {
        "type": "array",
        "uniqueItems": True,
        "items": {"type": "string", "enum": span_ids},
    }
    relation = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "relation_id",
            "source_object_id",
            "target_object_id",
            "source_object_binding",
            "target_outcome_binding",
            "evidence_design",
            *EVIDENCE_SPAN_FIELDS,
            "rationale",
        ],
        "properties": {
            "relation_id": {"type": "string", "enum": relation_ids},
            "source_object_id": {"type": "string", "enum": object_ids},
            "target_object_id": {
                "type": "string",
                "enum": [item["focal_object_id"]],
            },
            "source_object_binding": {
                "type": "string",
                "enum": ["EXACT_EXPLICIT", "COREFERENCE", "UNBOUND"],
            },
            "target_outcome_binding": {
                "type": "string",
                "enum": ["EXACT_EXPLICIT", "COREFERENCE", "UNBOUND"],
            },
            "evidence_design": {
                "type": "string",
                "enum": list(EVIDENCE_DESIGNS),
            },
            "primary_evidence_span_ids": {
                **span_array,
                "minItems": 1,
            },
            "corroborating_evidence_span_ids": span_array,
            "counterevidence_span_ids": span_array,
            "gap_evidence_span_ids": span_array,
            "rationale": {"type": "string"},
        },
    }
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "binding_role": {"type": "string", "enum": [role]},
        "source_item_hash": {
            "type": "string",
            "enum": [hash_payload(item)],
        },
        "all_relations_assessed": {"type": "boolean", "enum": [True]},
        "relation_bindings": {
            "type": "array",
            "minItems": len(relation_ids),
            "maxItems": len(relation_ids),
            "items": relation,
        },
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


def validate_typed_binding_receipt(
    *,
    receipt: dict[str, Any],
    item: dict[str, Any],
    role: str,
    refs: tuple[str, ...],
) -> list[str]:
    failures: list[str] = []
    if receipt.get("case_id") != item["case_id"]:
        failures.append("BINDING_CASE_MISMATCH")
    if receipt.get("binding_role") != role:
        failures.append("BINDING_ROLE_MISMATCH")
    if receipt.get("source_item_hash") != hash_payload(item):
        failures.append("BINDING_ITEM_HASH_MISMATCH")
    if receipt.get("all_relations_assessed") is not True:
        failures.append("BINDING_COVERAGE_NOT_CONFIRMED")
    if receipt.get("evidence_refs") != list(refs):
        failures.append("BINDING_EVIDENCE_SCOPE_MISMATCH")
    if any(
        forbidden in str(receipt)
        for forbidden in ("relation_truth_state", "binding_state")
    ):
        failures.append("BINDING_FORBIDDEN_STATE_AUTHORITY")
    values = receipt.get("relation_bindings")
    if not isinstance(values, list):
        return [*failures, "BINDINGS_NOT_ARRAY"]
    expected = set(relation_ids_for(item))
    observed = {
        value.get("relation_id")
        for value in values
        if isinstance(value, dict)
    }
    if len(values) != len(expected) or observed != expected:
        failures.append("BINDING_RELATION_COVERAGE_INVALID")
    allowed_spans = {
        value["span_id"] for value in item["evidence_spans"]
    }
    for value in values:
        if not isinstance(value, dict):
            failures.append("BINDING_RELATION_NOT_OBJECT")
            continue
        relation_id = value.get("relation_id", "")
        expected_source = (
            relation_id.split("-")[1]
            if relation_id.startswith("REL-")
            else None
        )
        if value.get("source_object_id") != expected_source:
            failures.append("BINDING_SOURCE_RELATION_MISMATCH")
        if value.get("target_object_id") != item["focal_object_id"]:
            failures.append("BINDING_TARGET_RELATION_MISMATCH")
        if value.get("evidence_design") not in EVIDENCE_DESIGNS:
            failures.append("BINDING_EVIDENCE_DESIGN_INVALID")
        seen: set[str] = set()
        for field in EVIDENCE_SPAN_FIELDS:
            spans = value.get(field)
            if (
                not isinstance(spans, list)
                or len(spans) != len(set(spans))
                or not set(spans).issubset(allowed_spans)
            ):
                failures.append(f"BINDING_{field.upper()}_INVALID")
                continue
            if field == "primary_evidence_span_ids" and not spans:
                failures.append("BINDING_PRIMARY_EVIDENCE_REQUIRED")
            overlap = seen.intersection(spans)
            if overlap:
                failures.append("BINDING_EVIDENCE_TYPE_OVERLAP")
            seen.update(spans)
    return sorted(set(failures))


def build_typed_consensus(
    *,
    item: dict[str, Any],
    left: dict[str, Any],
    right: dict[str, Any],
    version: str = RUNTIME_VERSION,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    left_map = {
        value["relation_id"]: value for value in left["relation_bindings"]
    }
    right_map = {
        value["relation_id"]: value for value in right["relation_bindings"]
    }
    bindings: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    divergences: list[dict[str, Any]] = []
    for relation_id in relation_ids_for(item):
        first = left_map[relation_id]
        second = right_map[relation_id]
        reasons: list[str] = []
        if _is_bound(first["source_object_binding"]) != _is_bound(
            second["source_object_binding"]
        ):
            reasons.append("SOURCE_BINDING_DISAGREEMENT")
        if _is_bound(first["target_outcome_binding"]) != _is_bound(
            second["target_outcome_binding"]
        ):
            reasons.append("TARGET_BINDING_DISAGREEMENT")
        if first["evidence_design"] != second["evidence_design"]:
            reasons.append("EVIDENCE_DESIGN_DISAGREEMENT")
        if set(first["primary_evidence_span_ids"]) != set(
            second["primary_evidence_span_ids"]
        ):
            reasons.append("PRIMARY_EVIDENCE_DISAGREEMENT")
        type_conflicts = _cross_type_conflicts(first, second)
        if type_conflicts:
            reasons.append("EVIDENCE_TYPE_CONFLICT")
        if reasons:
            conflicts.append({
                "case_id": item["case_id"],
                "relation_id": relation_id,
                "reasons": reasons,
                "cross_type_conflicts": type_conflicts,
                "left": _binding_projection(first),
                "right": _binding_projection(second),
            })
            continue
        source_binding = _coarse_binding(
            first["source_object_binding"],
            second["source_object_binding"],
        )
        target_binding = _coarse_binding(
            first["target_outcome_binding"],
            second["target_outcome_binding"],
        )
        merged = {
            "relation_id": relation_id,
            "source_object_id": first["source_object_id"],
            "target_object_id": first["target_object_id"],
            "source_object_binding": source_binding,
            "target_outcome_binding": target_binding,
            "evidence_design": first["evidence_design"],
            "binding_state": (
                "BOUND"
                if source_binding != "UNBOUND"
                and target_binding != "UNBOUND"
                else "UNBOUND"
            ),
            "primary_evidence_span_ids": sorted(
                set(first["primary_evidence_span_ids"])
            ),
        }
        for field in AUXILIARY_SPAN_FIELDS:
            left_spans = set(first[field])
            right_spans = set(second[field])
            merged[field] = sorted(left_spans | right_spans)
            if left_spans != right_spans:
                divergences.append({
                    "case_id": item["case_id"],
                    "relation_id": relation_id,
                    "field": field,
                    "left": sorted(left_spans),
                    "right": sorted(right_spans),
                    "merged": merged[field],
                })
        merged["all_admitted_evidence_span_ids"] = sorted(
            {
                span
                for field in EVIDENCE_SPAN_FIELDS
                for span in merged[field]
            }
        )
        bindings.append(merged)
    commitment = {
        "consensus_version": version,
        "case_id": item["case_id"],
        "source_item_hash": hash_payload(item),
        "source_role_receipt_hashes": {
            BINDING_ROLES[0]: hash_payload(left),
            BINDING_ROLES[1]: hash_payload(right),
        },
        "relation_bindings": bindings,
        "relation_consensus_count": len(bindings),
        "binding_ready": (
            len(bindings) == len(relation_ids_for(item)) and not conflicts
        ),
        "primary_evidence_consensus": "STRICT_SET_EQUALITY",
        "auxiliary_evidence_policy": "TYPED_UNION",
        "truth_state_authority": False,
    }
    return (
        {**commitment, "artifact_hash": hash_payload(commitment)},
        conflicts,
        divergences,
    )


def typed_state_schema(
    *,
    item: dict[str, Any],
    role: str,
    binding_receipt: dict[str, Any],
    refs: tuple[str, ...],
) -> dict[str, Any]:
    relation_ids = relation_ids_for(item)
    admitted_spans = sorted({
        span_id
        for binding in binding_receipt["relation_bindings"]
        for field in EVIDENCE_SPAN_FIELDS
        for span_id in binding[field]
    })
    assessment_properties = {
        "relation_id": {"type": "string", "enum": relation_ids},
        "relation_truth_state": {
            "type": "string",
            "enum": list(REFERENCE_STATES),
        },
        "cited_primary_span_ids": _citation_schema(
            admitted_spans, require=True
        ),
        "cited_corroborating_span_ids": _citation_schema(admitted_spans),
        "cited_counterevidence_span_ids": _citation_schema(admitted_spans),
        "cited_gap_evidence_span_ids": _citation_schema(admitted_spans),
        "rationale": {"type": "string"},
    }
    assessment = {
        "type": "object",
        "additionalProperties": False,
        "required": list(assessment_properties),
        "properties": assessment_properties,
    }
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "state_role": {"type": "string", "enum": [role]},
        "source_binding_consensus_hash": {
            "type": "string",
            "enum": [binding_receipt["artifact_hash"]],
        },
        "all_relations_assessed": {"type": "boolean", "enum": [True]},
        "relation_assessments": {
            "type": "array",
            "minItems": len(relation_ids),
            "maxItems": len(relation_ids),
            "items": assessment,
        },
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


def validate_typed_state_receipt(
    *,
    receipt: dict[str, Any],
    item: dict[str, Any],
    role: str,
    binding_receipt: dict[str, Any],
    refs: tuple[str, ...],
) -> list[str]:
    failures: list[str] = []
    if receipt.get("case_id") != item["case_id"]:
        failures.append("STATE_CASE_MISMATCH")
    if receipt.get("state_role") != role:
        failures.append("STATE_ROLE_MISMATCH")
    if (
        receipt.get("source_binding_consensus_hash")
        != binding_receipt["artifact_hash"]
    ):
        failures.append("STATE_BINDING_HASH_MISMATCH")
    if receipt.get("all_relations_assessed") is not True:
        failures.append("STATE_COVERAGE_NOT_CONFIRMED")
    if receipt.get("evidence_refs") != list(refs):
        failures.append("STATE_EVIDENCE_SCOPE_MISMATCH")
    values = receipt.get("relation_assessments")
    if not isinstance(values, list):
        return [*failures, "STATE_ASSESSMENTS_NOT_ARRAY"]
    expected = relation_ids_for(item)
    observed = [
        value.get("relation_id")
        for value in values
        if isinstance(value, dict)
    ]
    if len(values) != len(expected) or observed != expected:
        failures.append("STATE_RELATION_ORDER_OR_COVERAGE_INVALID")
    binding_map = {
        value["relation_id"]: value
        for value in binding_receipt["relation_bindings"]
    }
    citation_fields = {
        "cited_primary_span_ids": "primary_evidence_span_ids",
        "cited_corroborating_span_ids": (
            "corroborating_evidence_span_ids"
        ),
        "cited_counterevidence_span_ids": "counterevidence_span_ids",
        "cited_gap_evidence_span_ids": "gap_evidence_span_ids",
    }
    for value in values:
        if not isinstance(value, dict):
            failures.append("STATE_ASSESSMENT_NOT_OBJECT")
            continue
        relation_id = value.get("relation_id")
        binding = binding_map.get(relation_id)
        if binding is None:
            failures.append("STATE_RELATION_NOT_BOUND")
            continue
        for citation_field, binding_field in citation_fields.items():
            spans = value.get(citation_field)
            allowed = set(binding[binding_field])
            if (
                not isinstance(spans, list)
                or len(spans) != len(set(spans))
                or not set(spans).issubset(allowed)
            ):
                failures.append("STATE_TYPED_SPAN_NOT_BOUND")
        if set(value.get("cited_primary_span_ids") or []) != set(
            binding["primary_evidence_span_ids"]
        ):
            failures.append("STATE_PRIMARY_EVIDENCE_NOT_PRESERVED")
        state = value.get("relation_truth_state")
        if state not in REFERENCE_STATES:
            failures.append("STATE_TRUTH_STATE_INVALID")
            continue
        if state == "SUPPORTED_EFFECT" and (
            binding["binding_state"] != "BOUND"
            or binding["evidence_design"] != "INTERVENTION_OR_ROLLBACK"
        ):
            failures.append("STATE_EFFECT_WITHOUT_PRIMARY_EFFECT_DESIGN")
        if state == "SUPPORTED_NULL" and (
            binding["binding_state"] != "BOUND"
            or binding["evidence_design"] != "MATCHED_NULL_COMPARISON"
        ):
            failures.append("STATE_NULL_WITHOUT_PRIMARY_NULL_DESIGN")
        if (
            binding["binding_state"] == "UNBOUND"
            or binding["evidence_design"]
            in {"UNTESTED_DIFFERENCE", "OTHER"}
        ) and state != "UNRESOLVED":
            failures.append("STATE_GAP_OR_UNBOUND_PROMOTED")
    return sorted(set(failures))


def relation_ids_for(item: dict[str, Any]) -> list[str]:
    return [
        f"REL-{value['object_id']}-{item['focal_object_id']}"
        for value in item["object_registry"]
        if value["object_id"] != item["focal_object_id"]
    ]


def expected_states(corpus: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for item in corpus["public_surface"]["items"]:
        case_id = item["case_id"]
        binding = corpus["private_provenance"]["bindings"][case_id]
        supported = {
            value["source_object_id"]
            for value in binding["supported_targets"]
        }
        nulls = {
            value["source_object_id"]
            for value in binding["informative_null_targets"]
        }
        result[case_id] = {}
        for relation_id in relation_ids_for(item):
            source = relation_id.split("-")[1]
            result[case_id][relation_id] = (
                "SUPPORTED_EFFECT"
                if source in supported
                else "SUPPORTED_NULL"
                if source in nulls
                else "UNRESOLVED"
            )
    return result


def validate_hash_bound(value: dict[str, Any]) -> None:
    field = "run_hash" if "run_hash" in value else "artifact_hash"
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError("typed_evidence_binding_source_hash_invalid")


def _validate_artifact(value: dict[str, Any]) -> None:
    if "artifact_hash" not in value:
        raise ValueError("typed_evidence_binding_artifact_hash_missing")
    validate_hash_bound(value)


def _citation_schema(
    allowed: list[str],
    *,
    require: bool = False,
) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "array",
        "uniqueItems": True,
        "items": {"type": "string", "enum": sorted(allowed)},
    }
    if require:
        schema["minItems"] = 1
    return schema


def _is_bound(value: str) -> bool:
    return value != "UNBOUND"


def _coarse_binding(left: str, right: str) -> str:
    if left == "UNBOUND" or right == "UNBOUND":
        return "UNBOUND"
    if left == "COREFERENCE" or right == "COREFERENCE":
        return "COREFERENCE"
    return "EXACT_EXPLICIT"


def _cross_type_conflicts(
    first: dict[str, Any],
    second: dict[str, Any],
) -> list[dict[str, str]]:
    first_types = _span_types(first)
    second_types = _span_types(second)
    return [
        {
            "span_id": span,
            "left_type": first_types[span],
            "right_type": second_types[span],
        }
        for span in sorted(first_types.keys() & second_types.keys())
        if first_types[span] != second_types[span]
    ]


def _span_types(value: dict[str, Any]) -> dict[str, str]:
    return {
        span: field
        for field in EVIDENCE_SPAN_FIELDS
        for span in value[field]
    }


def _binding_projection(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_object_binding": value["source_object_binding"],
        "target_outcome_binding": value["target_outcome_binding"],
        "evidence_design": value["evidence_design"],
        **{field: value[field] for field in EVIDENCE_SPAN_FIELDS},
    }
