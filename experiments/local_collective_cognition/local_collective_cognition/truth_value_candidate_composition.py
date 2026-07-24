"""Truth-state and research-value separated candidate composition v0.39."""

from __future__ import annotations

import copy
from collections import defaultdict

from .collaborative_stability_experiment import exact_three_schema
from .provider_telemetry import hash_payload


CONTRACT_VERSION = "truth_value_candidate_composition_v0_39"
SOURCE_RANK_BONUS = (2, 1, 0)
SCORE_MAP = {
    "relation_truth_state": {
        "SUPPORTED_EFFECT": 6,
        "SUPPORTED_NULL": 5,
        "INDIRECT": 3,
        "WEAK": 0,
        "CONFLICTED": -2,
    },
    "null_discrimination": {
        "RULES_OUT_PLAUSIBLE_CAUSE": 4,
        "CONSTRAINS_BOUNDARY": 3,
        "REDUNDANT_NULL": 0,
        "NOT_APPLICABLE": 0,
    },
    "counterevidence_handling": {
        "EXPLICIT": 2,
        "PARTIAL": 1,
        "ABSENT": 0,
    },
    "constraint_binding": {
        "ADEQUATE": 2,
        "PARTIAL": 1,
        "ABSENT": 0,
    },
    "falsifiability": {
        "SPECIFIC": 2,
        "GENERIC": 1,
        "ABSENT": 0,
    },
    "expected_cbit": {
        "HIGH": 4,
        "MEDIUM": 2,
        "LOW": 0,
        "NEGATIVE": -4,
    },
    "research_value_disposition": {
        "PRIORITIZE": 3,
        "RETAIN": 2,
        "DEFER": 0,
        "DISCARD": -5,
    },
}
DISCRIMINATING_NULL_STATES = {
    "RULES_OUT_PLAUSIBLE_CAUSE",
    "CONSTRAINS_BOUNDARY",
}


def truth_valued_exact_three_schema(*, item, arm_id, refs):
    schema = copy.deepcopy(
        exact_three_schema(item=item, arm_id=arm_id, refs=refs)
    )
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    value_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            *SCORE_MAP.keys(), "evidence_span_ids", "rationale",
        ],
        "properties": {
            **{
                axis: {
                    "type": "string", "enum": list(mapping)
                }
                for axis, mapping in SCORE_MAP.items()
            },
            "evidence_span_ids": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {"type": "string", "enum": span_ids},
            },
            "rationale": {"type": "string"},
        },
    }
    candidate_schema = schema["properties"][
        "problem_candidates"
    ]["items"]
    candidate_schema["required"].append("candidate_value")
    candidate_schema["properties"]["candidate_value"] = value_schema
    return schema


def validate_truth_valued_receipt(*, raw_receipt, item, refs):
    failures = []
    if not isinstance(raw_receipt, dict):
        return ["TRUTH_VALUE_RECEIPT_NOT_OBJECT"]
    if raw_receipt.get("case_id") != item["case_id"]:
        failures.append("CASE_BINDING_MISMATCH")
    if raw_receipt.get("evidence_refs") != list(refs):
        failures.append("EVIDENCE_SCOPE_MISMATCH")
    candidates = raw_receipt.get("problem_candidates")
    if not isinstance(candidates, list) or len(candidates) != 3:
        failures.append("CANDIDATE_COUNT_INVALID")
        return failures
    ids = [value.get("candidate_id") for value in candidates]
    if len(set(ids)) != 3:
        failures.append("CANDIDATE_IDS_INVALID")
    allowed_spans = {
        value["span_id"] for value in item["evidence_spans"]
    }
    for candidate in candidates:
        candidate_id = candidate.get("candidate_id", "UNKNOWN")
        value = candidate.get("candidate_value")
        if not isinstance(value, dict):
            failures.append(f"CANDIDATE_VALUE_MISSING:{candidate_id}")
            continue
        for axis, mapping in SCORE_MAP.items():
            if value.get(axis) not in mapping:
                failures.append(
                    f"VALUE_AXIS_INVALID:{candidate_id}:{axis}"
                )
        spans = value.get("evidence_span_ids")
        if (
            not isinstance(spans, list)
            or not spans
            or len(set(spans)) != len(spans)
            or not set(spans).issubset(allowed_spans)
        ):
            failures.append(
                f"VALUE_EVIDENCE_BINDING_INVALID:{candidate_id}"
            )
        truth_state = value.get("relation_truth_state")
        null_state = value.get("null_discrimination")
        disposition = value.get("research_value_disposition")
        expected_cbit = value.get("expected_cbit")
        if (
            truth_state == "SUPPORTED_NULL"
            and null_state == "NOT_APPLICABLE"
        ):
            failures.append(
                f"SUPPORTED_NULL_DISCRIMINATION_MISSING:{candidate_id}"
            )
        if (
            truth_state != "SUPPORTED_NULL"
            and null_state != "NOT_APPLICABLE"
        ):
            failures.append(
                f"NON_NULL_DISCRIMINATION_INVALID:{candidate_id}"
            )
        if (
            truth_state == "SUPPORTED_NULL"
            and null_state in DISCRIMINATING_NULL_STATES
            and disposition == "DISCARD"
        ):
            failures.append(
                f"DISCRIMINATING_NULL_DISCARDED:{candidate_id}"
            )
        if (
            truth_state == "SUPPORTED_NULL"
            and null_state in DISCRIMINATING_NULL_STATES
            and expected_cbit == "NEGATIVE"
        ):
            failures.append(
                f"DISCRIMINATING_NULL_NEGATIVE_CBIT:{candidate_id}"
            )
    return failures


def compose_truth_valued_pool(
    *, pool, provisional_receipt, item, refs
):
    scored = []
    by_source = defaultdict(list)
    for entry in pool["candidates"]:
        candidate_value = entry["candidate"].get("candidate_value", {})
        components = {
            axis: SCORE_MAP[axis][candidate_value[axis]]
            for axis in SCORE_MAP
        }
        value = {
            "pool_candidate_id": entry["pool_candidate_id"],
            "relation_id": entry["relation_id"],
            "source_id": entry["source_id"],
            "source_candidate_id": entry["source_candidate_id"],
            "source_receipt_hash": entry["source_receipt_hash"],
            "raw_semantic_score": sum(components.values()),
            "score_components": components,
            "provider_candidate_value": copy.deepcopy(candidate_value),
        }
        scored.append(value)
        by_source[value["source_id"]].append(value)
    for source_id, values in by_source.items():
        ordered_scores = sorted(
            {value["raw_semantic_score"] for value in values},
            reverse=True,
        )
        bonus_by_score = {
            score: SOURCE_RANK_BONUS[
                min(index, len(SOURCE_RANK_BONUS) - 1)
            ]
            for index, score in enumerate(ordered_scores)
        }
        for value in values:
            value["source_rank_bonus"] = bonus_by_score[
                value["raw_semantic_score"]
            ]
            value["calibrated_score"] = (
                value["raw_semantic_score"]
                + value["source_rank_bonus"]
            )
            value["tie_break_hash"] = hash_payload([
                CONTRACT_VERSION, pool["artifact_hash"],
                source_id, value["pool_candidate_id"],
            ])
    best_by_relation = {}
    for value in scored:
        incumbent = best_by_relation.get(value["relation_id"])
        if incumbent is None or (
            value["calibrated_score"], value["tie_break_hash"]
        ) > (
            incumbent["calibrated_score"],
            incumbent["tie_break_hash"],
        ):
            best_by_relation[value["relation_id"]] = value
    selected = sorted(
        best_by_relation.values(),
        key=lambda value: (
            value["calibrated_score"], value["tie_break_hash"]
        ),
        reverse=True,
    )[:3]
    if len(selected) != 3:
        raise ValueError("INSUFFICIENT_DISTINCT_RELATIONS")
    pool_by_id = {
        value["pool_candidate_id"]: value
        for value in pool["candidates"]
    }
    final_candidates, lineage = [], []
    for index, value in enumerate(selected, 1):
        final_id = f"C{index}"
        candidate = copy.deepcopy(
            pool_by_id[value["pool_candidate_id"]]["candidate"]
        )
        candidate["candidate_id"] = final_id
        final_candidates.append(candidate)
        lineage.append({
            "final_candidate_id": final_id,
            **{
                key: item_value
                for key, item_value in value.items()
                if key != "provider_candidate_value"
            },
        })
    raw = {
        "case_id": item["case_id"],
        "arm_id": "A1_ONTOLOGY",
        "problem_candidates": final_candidates,
        "selected_problem_id": "C1",
        "rationale": (
            "Runtime composition from separated truth and research value."
        ),
        "evidence_refs": list(refs),
        "object_census": copy.deepcopy(
            provisional_receipt["object_census"]
        ),
    }
    commitment = {
        "contract_version": CONTRACT_VERSION,
        "case_id": item["case_id"],
        "source_pool_hash": pool["artifact_hash"],
        "source_score_map_hash": hash_payload(SCORE_MAP),
        "source_rank_bonus": list(SOURCE_RANK_BONUS),
        "scored_candidates": scored,
        "lineage": lineage,
        "final_raw_receipt_hash": hash_payload(raw),
        "truth_state_research_value_separated": True,
        "discriminating_null_discard_forbidden": True,
        "provider_sees_numeric_score_map": False,
        "provider_selected_final_candidates": False,
        "runtime_deterministic_composition": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return raw, {**commitment, "artifact_hash": hash_payload(commitment)}
