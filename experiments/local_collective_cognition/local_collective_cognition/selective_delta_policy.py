"""Zero-token qualification and one-candidate delta contract v0.41."""

from __future__ import annotations

import copy

from .candidate_pool_arbitration import relation_id
from .null_role_candidate_composition import (
    DISCRIMINATING_NULL_ROLES,
    SCORE_MAP,
    null_role_valued_exact_three_schema,
)
from .provider_telemetry import hash_payload


POLICY_VERSION = "selective_delta_policy_v0_41"
DELTA_CONTRACT_VERSION = "single_delta_candidate_v0_41"
MINIMUM_SEMANTIC_SPREAD = 11
MINIMUM_SECOND_SCORE = 12
MINIMUM_COMPOUND_DIAGNOSTICS = 2
MAXIMUM_DELTA_EVIDENCE_SPANS = 4


def derive_selective_qualification(
    *, raw_receipt, item, escalation_receipt
):
    candidates = raw_receipt.get("problem_candidates", [])
    scores = sorted(
        (_semantic_score(value) for value in candidates),
        reverse=True,
    )
    score_spread = (
        scores[0] - scores[-1] if len(scores) == 3 else 0
    )
    second_score = scores[1] if len(scores) == 3 else 0
    diagnostic_count = len(
        escalation_receipt.get("diagnostic_flags", [])
    )
    semantic_asymmetry = (
        len(scores) == 3
        and score_spread >= MINIMUM_SEMANTIC_SPREAD
        and (
            second_score >= MINIMUM_SECOND_SCORE
            or diagnostic_count >= MINIMUM_COMPOUND_DIAGNOSTICS
        )
    )
    qualified = bool(
        escalation_receipt.get("triggered")
        and semantic_asymmetry
    )
    commitment = {
        "policy_version": POLICY_VERSION,
        "case_id": item["case_id"],
        "source_raw_receipt_hash": hash_payload(raw_receipt),
        "source_escalation_receipt_hash": escalation_receipt[
            "artifact_hash"
        ],
        "semantic_scores_descending": scores,
        "semantic_score_spread": score_spread,
        "second_highest_semantic_score": second_score,
        "diagnostic_count": diagnostic_count,
        "thresholds": {
            "minimum_semantic_spread": MINIMUM_SEMANTIC_SPREAD,
            "minimum_second_score": MINIMUM_SECOND_SCORE,
            "minimum_compound_diagnostics": (
                MINIMUM_COMPOUND_DIAGNOSTICS
            ),
        },
        "qualified": qualified,
        "route_id": (
            escalation_receipt["route_id"]
            if qualified else "A1_ONTOLOGY"
        ),
        "private_truth_used": False,
        "provider_generated_qualification_text_used": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def build_delta_view(
    *, raw_receipt, item, qualification_receipt
):
    used_span_ids = {
        span_id
        for candidate in raw_receipt["problem_candidates"]
        for span_id in candidate.get("evidence_span_ids", [])
    }
    ordered_spans = sorted(
        item["evidence_spans"],
        key=lambda value: (
            value["span_id"] in used_span_ids,
            hash_payload([
                POLICY_VERSION,
                qualification_receipt["artifact_hash"],
                value["span_id"],
            ]),
        ),
    )
    selected_spans = ordered_spans[:MAXIMUM_DELTA_EVIDENCE_SPANS]
    excluded_relations = sorted({
        relation_id(candidate)
        for candidate in raw_receipt["problem_candidates"]
    })
    view = {
        "view_version": "selective_delta_view_v0_41",
        "case_id": item["case_id"],
        "domain": item["domain"],
        "research_goal": item["research_goal"],
        "object_registry": copy.deepcopy(item["object_registry"]),
        "evidence_spans": copy.deepcopy(selected_spans),
        "excluded_relation_ids": excluded_relations,
        "source_qualification_hash": qualification_receipt[
            "artifact_hash"
        ],
        "private_truth_used": False,
    }
    return {**view, "artifact_hash": hash_payload(view)}


def single_delta_schema(*, item, refs):
    schema = copy.deepcopy(null_role_valued_exact_three_schema(
        item=item, arm_id="A1_ONTOLOGY", refs=refs
    ))
    schema["properties"]["problem_candidates"]["minItems"] = 1
    schema["properties"]["problem_candidates"]["maxItems"] = 1
    schema["properties"]["problem_candidates"]["items"][
        "properties"
    ]["candidate_id"] = {"type": "string", "enum": ["C1"]}
    schema["properties"]["selected_problem_id"] = {
        "type": "string", "enum": ["C1"]
    }
    schema["required"].remove("object_census")
    del schema["properties"]["object_census"]
    return schema


def validate_single_delta(
    *, raw_receipt, item, refs, excluded_relation_ids
):
    failures = []
    if not isinstance(raw_receipt, dict):
        return ["DELTA_RECEIPT_NOT_OBJECT"]
    if raw_receipt.get("case_id") != item["case_id"]:
        failures.append("CASE_BINDING_MISMATCH")
    if raw_receipt.get("arm_id") != "A1_ONTOLOGY":
        failures.append("ARM_BINDING_MISMATCH")
    if raw_receipt.get("evidence_refs") != list(refs):
        failures.append("EVIDENCE_SCOPE_MISMATCH")
    candidates = raw_receipt.get("problem_candidates")
    if not isinstance(candidates, list) or len(candidates) != 1:
        failures.append("DELTA_CANDIDATE_COUNT_INVALID")
        return failures
    candidate = candidates[0]
    if candidate.get("candidate_id") != "C1":
        failures.append("DELTA_CANDIDATE_ID_INVALID")
    if raw_receipt.get("selected_problem_id") != "C1":
        failures.append("DELTA_SELECTION_INVALID")
    if relation_id(candidate) in set(excluded_relation_ids):
        failures.append("DELTA_RELATION_NOT_DISTINCT")
    allowed_objects = {
        value["object_id"] for value in item["object_registry"]
    }
    if (
        candidate.get("source_object_id") not in allowed_objects
        or candidate.get("target_object_id") not in allowed_objects
    ):
        failures.append("DELTA_OBJECT_BINDING_INVALID")
    allowed_spans = {
        value["span_id"] for value in item["evidence_spans"]
    }
    value = candidate.get("candidate_value")
    if not isinstance(value, dict):
        failures.append("DELTA_VALUE_MISSING")
        return failures
    for axis, mapping in SCORE_MAP.items():
        if value.get(axis) not in mapping:
            failures.append(f"DELTA_VALUE_AXIS_INVALID:{axis}")
    spans = value.get("evidence_span_ids")
    if (
        not isinstance(spans, list)
        or not spans
        or not set(spans).issubset(allowed_spans)
    ):
        failures.append("DELTA_VALUE_EVIDENCE_INVALID")
    truth_state = value.get("relation_truth_state")
    null_role = value.get("null_information_role")
    if (
        truth_state == "SUPPORTED_NULL"
        and null_role == "NOT_APPLICABLE"
    ):
        failures.append("SUPPORTED_NULL_INFORMATION_ROLE_MISSING")
    if (
        truth_state == "SUPPORTED_NULL"
        and null_role in DISCRIMINATING_NULL_ROLES
        and value.get("research_value_disposition") == "DISCARD"
    ):
        failures.append("DISCRIMINATING_NULL_DISCARDED")
    if (
        truth_state == "SUPPORTED_NULL"
        and null_role in DISCRIMINATING_NULL_ROLES
        and value.get("expected_cbit") == "NEGATIVE"
    ):
        failures.append("DISCRIMINATING_NULL_NEGATIVE_CBIT")
    return failures


def _semantic_score(candidate):
    value = candidate.get("candidate_value", {})
    return sum(
        mapping.get(value.get(axis), min(mapping.values()))
        for axis, mapping in SCORE_MAP.items()
    )
