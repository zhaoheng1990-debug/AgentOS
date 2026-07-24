"""Field-level gray admission for core and frontier cognitive candidates."""

from __future__ import annotations

from .provider_telemetry import hash_payload


ADMISSION_VERSION = "frontier_partial_admission_v0_27"
LANES = ("CORE", "FRONTIER")
DISPOSITIONS = ("ADMITTED_COMPONENT", "SPECULATIVE_COMPONENT", "QUARANTINED_COMPONENT")
EPISTEMIC_BASES = ("OBSERVED", "INFERRED", "SPECULATIVE")
STRUCTURAL_ORIGINS = (
    "EVIDENCE", "ANALOGY", "COORDINATE_SHIFT", "COUNTERFACTUAL",
)
TEST_COSTS = ("LOW", "MEDIUM", "HIGH")
OBJECT_TYPES = (
    "ACTOR", "PROCESS", "STATE", "RESOURCE", "CONSTRAINT",
    "OBSERVABLE", "EVIDENCE_SOURCE", "POLICY",
)


def project_frontier_receipt(*, raw_receipt, item, arm_id, evidence_refs):
    object_ids = {
        value["object_id"] for value in item["object_registry"]
    }
    span_ids = {value["span_id"] for value in item["evidence_spans"]}
    hard_failures = _hard_failures(
        raw_receipt, item=item, arm_id=arm_id, evidence_refs=evidence_refs
    )
    candidate_components = []
    census_components = []
    if not hard_failures:
        candidate_components = [
            _candidate_component(
                candidate,
                index=index,
                object_ids=object_ids,
                span_ids=span_ids,
            )
            for index, candidate in enumerate(
                raw_receipt.get("problem_candidates", ()), 1
            )
        ]
        if arm_id == "A1_ONTOLOGY":
            census_components = [
                _census_component(
                    value,
                    index=index,
                    object_ids=object_ids,
                    span_ids=span_ids,
                )
                for index, value in enumerate(
                    raw_receipt.get("object_census", ()), 1
                )
            ]
    eligible = [
        value for value in candidate_components
        if value["disposition"] != "QUARANTINED_COMPONENT"
    ]
    quarantined = [
        value for value in candidate_components
        if value["disposition"] == "QUARANTINED_COMPONENT"
    ]
    selected_id = (
        raw_receipt.get("selected_problem_id")
        if isinstance(raw_receipt, dict) else None
    )
    selected_eligible = selected_id in {
        value["candidate_id"] for value in eligible
    }
    if hard_failures or not eligible:
        state = "BLOCK"
    elif (
        quarantined
        or any(
            value["disposition"] == "QUARANTINED_COMPONENT"
            for value in census_components
        )
        or not selected_eligible
    ):
        state = "PARTIAL_CANDIDATE"
    else:
        state = "ADMITTED"
    commitment = {
        "admission_version": ADMISSION_VERSION,
        "case_id": item["case_id"],
        "arm_id": arm_id,
        "raw_receipt_hash": hash_payload(raw_receipt),
        "hard_failures": hard_failures,
        "candidate_components": candidate_components,
        "census_components": census_components,
        "eligible_candidate_ids": [
            value["candidate_id"] for value in eligible
        ],
        "selected_problem_id": selected_id,
        "selected_problem_is_eligible": selected_eligible,
        "receipt_state": state,
        "whole_receipt_block_reserved_for_boundary_failure": True,
        "component_level_gray_admission": True,
        "provider_has_promotion_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_frontier_projection(projection, *, raw_receipt, item, arm_id, evidence_refs):
    expected = project_frontier_receipt(
        raw_receipt=raw_receipt,
        item=item,
        arm_id=arm_id,
        evidence_refs=evidence_refs,
    )
    if projection != expected:
        raise ValueError("frontier_partial_projection_invalid")


def _hard_failures(raw, *, item, arm_id, evidence_refs):
    if not isinstance(raw, dict):
        return ["RAW_RECEIPT_NOT_OBJECT"]
    failures = []
    if raw.get("case_id") != item["case_id"]:
        failures.append("CASE_BINDING_MISMATCH")
    if raw.get("arm_id") != arm_id:
        failures.append("ARM_BINDING_MISMATCH")
    if raw.get("evidence_refs") != list(evidence_refs):
        failures.append("EVIDENCE_SCOPE_MISMATCH")
    if not isinstance(raw.get("problem_candidates"), list):
        failures.append("PROBLEM_CANDIDATES_NOT_LIST")
    if arm_id == "A1_ONTOLOGY" and not isinstance(
        raw.get("object_census"), list
    ):
        failures.append("OBJECT_CENSUS_NOT_LIST")
    return failures


def _candidate_component(candidate, *, index, object_ids, span_ids):
    reasons = []
    required = {
        "candidate_id", "lane", "question", "source_object_id",
        "target_object_id", "constraint_object_ids", "epistemic_basis",
        "structural_origin", "falsifier", "required_observation",
        "evidence_span_ids", "estimated_test_cost",
    }
    if not isinstance(candidate, dict):
        reasons.append("CANDIDATE_NOT_OBJECT")
        candidate = {}
    missing = sorted(required - set(candidate))
    if missing:
        reasons.append("MISSING_FIELDS:" + ",".join(missing))
    candidate_id = candidate.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        reasons.append("CANDIDATE_ID_INVALID")
        candidate_id = f"INVALID-{index}"
    if candidate.get("lane") not in LANES:
        reasons.append("LANE_INVALID")
    if not str(candidate.get("question", "")).strip():
        reasons.append("QUESTION_EMPTY")
    source = candidate.get("source_object_id")
    target = candidate.get("target_object_id")
    self_coordinate_hypothesis = (
        source == target
        and candidate.get("lane") == "FRONTIER"
        and candidate.get("structural_origin")
        in {"COORDINATE_SHIFT", "COUNTERFACTUAL"}
    )
    if (
        source not in object_ids
        or target not in object_ids
        or source == target and not self_coordinate_hypothesis
    ):
        reasons.append("OBJECT_BINDING_INVALID")
    constraints = candidate.get("constraint_object_ids")
    if not _valid_id_list(constraints, object_ids, allow_empty=True):
        reasons.append("CONSTRAINT_BINDING_INVALID")
    basis = candidate.get("epistemic_basis")
    if basis not in EPISTEMIC_BASES:
        reasons.append("EPISTEMIC_BASIS_INVALID")
    origin = candidate.get("structural_origin")
    if origin not in STRUCTURAL_ORIGINS:
        reasons.append("STRUCTURAL_ORIGIN_INVALID")
    evidence = candidate.get("evidence_span_ids")
    allow_empty = (
        basis == "SPECULATIVE"
        and origin in {"ANALOGY", "COORDINATE_SHIFT", "COUNTERFACTUAL"}
    )
    if not _valid_id_list(evidence, span_ids, allow_empty=allow_empty):
        reasons.append("EVIDENCE_BINDING_INVALID")
    if not str(candidate.get("falsifier", "")).strip():
        reasons.append("FALSIFIER_EMPTY")
    if not str(candidate.get("required_observation", "")).strip():
        reasons.append("REQUIRED_OBSERVATION_EMPTY")
    if candidate.get("estimated_test_cost") not in TEST_COSTS:
        reasons.append("TEST_COST_INVALID")
    if reasons:
        disposition = "QUARANTINED_COMPONENT"
        normalized = None
    else:
        disposition = (
            "SPECULATIVE_COMPONENT"
            if candidate["lane"] == "FRONTIER"
            or candidate["epistemic_basis"] == "SPECULATIVE"
            else "ADMITTED_COMPONENT"
        )
        normalized = {
            key: candidate[key] for key in sorted(required)
        }
    commitment = {
        "candidate_id": candidate_id,
        "disposition": disposition,
        "reasons": reasons,
        "normalized_candidate": normalized,
        "additional_fields_preserved_in_raw_only": sorted(
            set(candidate) - required
        ),
    }
    return {**commitment, "component_hash": hash_payload(commitment)}


def _census_component(value, *, index, object_ids, span_ids):
    reasons = []
    required = {"object_id", "object_type", "anchor_span_ids"}
    if not isinstance(value, dict):
        reasons.append("CENSUS_ITEM_NOT_OBJECT")
        value = {}
    object_id = value.get("object_id")
    if object_id not in object_ids:
        reasons.append("CENSUS_OBJECT_ID_INVALID")
        object_id = f"INVALID-{index}"
    if value.get("object_type") not in OBJECT_TYPES:
        reasons.append("CENSUS_OBJECT_TYPE_INVALID")
    if not _valid_id_list(
        value.get("anchor_span_ids"), span_ids, allow_empty=False
    ):
        reasons.append("CENSUS_ANCHOR_INVALID")
    if reasons:
        disposition = "QUARANTINED_COMPONENT"
        normalized = None
    else:
        disposition = "ADMITTED_COMPONENT"
        normalized = {key: value[key] for key in sorted(required)}
    commitment = {
        "object_id": object_id,
        "disposition": disposition,
        "reasons": reasons,
        "normalized_object": normalized,
        "additional_fields_preserved_in_raw_only": sorted(
            set(value) - required
        ),
    }
    return {**commitment, "component_hash": hash_payload(commitment)}


def _valid_id_list(values, allowed, *, allow_empty):
    return (
        isinstance(values, list)
        and (allow_empty or bool(values))
        and len(values) == len(set(values))
        and set(values).issubset(allowed)
    )
