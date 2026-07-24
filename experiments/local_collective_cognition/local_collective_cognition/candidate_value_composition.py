"""Source-blind candidate value receipts and deterministic composition."""

from __future__ import annotations

import copy

from .provider_telemetry import hash_payload


CONTRACT_VERSION = "candidate_value_composition_v0_37"
SCORE_MAP = {
    "relation_evidence": {
        "SUPPORTED_EFFECT": 6,
        "SUPPORTED_NULL": 5,
        "INDIRECT": 3,
        "WEAK": 0,
        "CONFLICTED": -2,
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
    "verdict": {
        "ADMIT": 3,
        "HOLD": 0,
        "REJECT": -5,
    },
}


def build_blinded_candidate_view(
    *, pool, replication_id, corpus_hash
):
    ordered = sorted(
        pool["candidates"],
        key=lambda value: hash_payload([
            CONTRACT_VERSION, corpus_hash, replication_id,
            value["pool_candidate_id"],
        ]),
    )
    entries, bindings = [], {}
    for index, value in enumerate(ordered, 1):
        opaque_id = f"P{index}"
        candidate = copy.deepcopy(value["candidate"])
        candidate["candidate_id"] = opaque_id
        entries.append({
            "opaque_candidate_id": opaque_id,
            "relation_id": value["relation_id"],
            "candidate": candidate,
        })
        bindings[opaque_id] = {
            "pool_candidate_id": value["pool_candidate_id"],
            "relation_id": value["relation_id"],
            "source_id": value["source_id"],
            "source_candidate_id": value["source_candidate_id"],
            "source_receipt_hash": value["source_receipt_hash"],
        }
    commitment = {
        "contract_version": CONTRACT_VERSION,
        "replication_id": replication_id,
        "case_id": pool["case_id"],
        "source_pool_hash": pool["artifact_hash"],
        "entries": entries,
        "bindings": bindings,
        "provider_visible_source_ids": False,
        "provider_visible_pool_candidate_ids": False,
        "private_truth_exposed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def candidate_value_schema(*, item, blinded_view, refs):
    opaque_ids = [
        value["opaque_candidate_id"]
        for value in blinded_view["entries"]
    ]
    relation_ids = sorted({
        value["relation_id"] for value in blinded_view["entries"]
    })
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    evaluation = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "opaque_candidate_id", "relation_id", "relation_evidence",
            "counterevidence_handling", "constraint_binding",
            "falsifiability", "expected_cbit", "verdict",
            "evidence_span_ids", "rationale",
        ],
        "properties": {
            "opaque_candidate_id": {
                "type": "string", "enum": opaque_ids,
            },
            "relation_id": {
                "type": "string", "enum": relation_ids,
            },
            "relation_evidence": {
                "type": "string",
                "enum": list(SCORE_MAP["relation_evidence"]),
            },
            "counterevidence_handling": {
                "type": "string",
                "enum": list(SCORE_MAP["counterevidence_handling"]),
            },
            "constraint_binding": {
                "type": "string",
                "enum": list(SCORE_MAP["constraint_binding"]),
            },
            "falsifiability": {
                "type": "string",
                "enum": list(SCORE_MAP["falsifiability"]),
            },
            "expected_cbit": {
                "type": "string",
                "enum": list(SCORE_MAP["expected_cbit"]),
            },
            "verdict": {
                "type": "string",
                "enum": list(SCORE_MAP["verdict"]),
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
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "case_id", "arm_id", "candidate_evaluations",
            "evidence_refs",
        ],
        "properties": {
            "case_id": {
                "type": "string", "enum": [item["case_id"]],
            },
            "arm_id": {
                "type": "string", "enum": ["A2_VALUE_COMPOSED"],
            },
            "candidate_evaluations": {
                "type": "array",
                "minItems": len(opaque_ids),
                "maxItems": len(opaque_ids),
                "items": evaluation,
            },
            "evidence_refs": {
                "type": "array",
                "items": {
                    "type": "string", "enum": list(refs),
                },
            },
        },
    }


def validate_candidate_value_receipt(
    *, value_receipt, blinded_view, item, refs
):
    failures = []
    if not isinstance(value_receipt, dict):
        return ["VALUE_RECEIPT_NOT_OBJECT"]
    if value_receipt.get("case_id") != item["case_id"]:
        failures.append("CASE_BINDING_MISMATCH")
    if value_receipt.get("arm_id") != "A2_VALUE_COMPOSED":
        failures.append("ARM_BINDING_MISMATCH")
    if value_receipt.get("evidence_refs") != list(refs):
        failures.append("EVIDENCE_SCOPE_MISMATCH")
    evaluations = value_receipt.get("candidate_evaluations")
    expected = {
        value["opaque_candidate_id"]: value
        for value in blinded_view["entries"]
    }
    if not isinstance(evaluations, list):
        failures.append("EVALUATIONS_NOT_ARRAY")
        return failures
    ids = [
        value.get("opaque_candidate_id")
        for value in evaluations if isinstance(value, dict)
    ]
    if (
        len(evaluations) != len(expected)
        or len(ids) != len(expected)
        or len(set(ids)) != len(expected)
        or set(ids) != set(expected)
    ):
        failures.append("CANDIDATE_COVERAGE_INVALID")
        return failures
    allowed_spans = {
        value["span_id"] for value in item["evidence_spans"]
    }
    for evaluation in evaluations:
        opaque_id = evaluation["opaque_candidate_id"]
        if evaluation.get("relation_id") != expected[opaque_id][
            "relation_id"
        ]:
            failures.append(
                f"RELATION_BINDING_MISMATCH:{opaque_id}"
            )
        for axis, mapping in SCORE_MAP.items():
            if evaluation.get(axis) not in mapping:
                failures.append(f"VALUE_AXIS_INVALID:{opaque_id}:{axis}")
        spans = evaluation.get("evidence_span_ids")
        if (
            not isinstance(spans, list)
            or not spans
            or len(set(spans)) != len(spans)
            or not set(spans).issubset(allowed_spans)
        ):
            failures.append(f"EVIDENCE_BINDING_INVALID:{opaque_id}")
    return failures


def compose_candidate_value_receipt(
    *, value_receipt, blinded_view, pool, provisional_receipt,
    item, refs
):
    failures = validate_candidate_value_receipt(
        value_receipt=value_receipt,
        blinded_view=blinded_view,
        item=item,
        refs=refs,
    )
    if failures:
        raise ValueError(",".join(failures))
    pool_by_id = {
        value["pool_candidate_id"]: value
        for value in pool["candidates"]
    }
    scored = []
    for evaluation in value_receipt["candidate_evaluations"]:
        opaque_id = evaluation["opaque_candidate_id"]
        binding = blinded_view["bindings"][opaque_id]
        score_components = {
            axis: SCORE_MAP[axis][evaluation[axis]]
            for axis in SCORE_MAP
        }
        scored.append({
            "opaque_candidate_id": opaque_id,
            **binding,
            "score_components": score_components,
            "total_score": sum(score_components.values()),
            "provider_evaluation": copy.deepcopy(evaluation),
        })
    best_by_relation = {}
    for value in scored:
        incumbent = best_by_relation.get(value["relation_id"])
        tie = hash_payload([
            CONTRACT_VERSION,
            blinded_view["artifact_hash"],
            value["opaque_candidate_id"],
        ])
        value["tie_break_hash"] = tie
        if incumbent is None or (
            value["total_score"], tie
        ) > (
            incumbent["total_score"], incumbent["tie_break_hash"]
        ):
            best_by_relation[value["relation_id"]] = value
    selected = sorted(
        best_by_relation.values(),
        key=lambda value: (
            value["total_score"], value["tie_break_hash"]
        ),
        reverse=True,
    )[:3]
    if len(selected) != 3:
        raise ValueError("INSUFFICIENT_DISTINCT_RELATIONS")
    candidates, lineage = [], []
    for index, value in enumerate(selected, 1):
        final_id = f"C{index}"
        source = pool_by_id[value["pool_candidate_id"]]
        candidate = copy.deepcopy(source["candidate"])
        candidate["candidate_id"] = final_id
        candidates.append(candidate)
        lineage.append({
            "final_candidate_id": final_id,
            "opaque_candidate_id": value["opaque_candidate_id"],
            "pool_candidate_id": value["pool_candidate_id"],
            "relation_id": value["relation_id"],
            "source_id": value["source_id"],
            "source_candidate_id": value["source_candidate_id"],
            "total_score": value["total_score"],
            "score_components": value["score_components"],
            "tie_break_hash": value["tie_break_hash"],
        })
    raw = {
        "case_id": item["case_id"],
        "arm_id": "A1_ONTOLOGY",
        "problem_candidates": candidates,
        "selected_problem_id": "C1",
        "rationale": (
            "Runtime deterministic composition from candidate-value receipt."
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
        "source_blinded_view_hash": blinded_view["artifact_hash"],
        "source_value_receipt_hash": hash_payload(value_receipt),
        "score_map_hash": hash_payload(SCORE_MAP),
        "scored_candidates": scored,
        "lineage": lineage,
        "final_raw_receipt_hash": hash_payload(raw),
        "provider_visible_source_ids": False,
        "provider_selected_final_candidates": False,
        "runtime_deterministic_composition": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return raw, {**commitment, "artifact_hash": hash_payload(commitment)}
