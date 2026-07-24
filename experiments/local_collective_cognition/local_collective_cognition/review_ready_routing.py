"""Review-ready opportunity routing for v0.48."""

from __future__ import annotations

import copy
from collections import Counter

from .candidate_pool_arbitration import relation_id
from .provider_telemetry import hash_payload


ROUTING_VERSION = "review_ready_opportunity_routing_v0_48"
MAXIMUM_REVIEW_OPPORTUNITIES = 2


def derive_review_ready_receipt(
    *,
    key,
    raw_receipt,
    item,
    qualification_receipt,
    all_standard_receipts,
):
    rep, _, case_id = key.split(":", 2)
    focal = item["focal_object_id"]
    base_relations = {
        relation_id(value) for value in raw_receipt["problem_candidates"]
    }
    occurrence = Counter()
    candidates = []
    for other_key, other_raw in all_standard_receipts.items():
        parts = other_key.split(":", 3)
        if len(parts) != 4:
            continue
        other_rep, _, stage, other_case = parts
        if stage != "STANDARD_OPPORTUNITY" or other_case != case_id:
            continue
        for value in other_raw.get("admission_opportunities", []):
            current = (
                f"{value['source_object_id']}->"
                f"{value['target_object_id']}"
            )
            occurrence[current] += 1
            candidates.append((other_rep, current, value))
    review_ready = []
    for source_rep, current, value in candidates:
        own = source_rep == rep
        recurrent = occurrence[current] >= 2
        focal_relation = focal in {
            value["source_object_id"],
            value["target_object_id"],
        }
        if (
            current in base_relations
            or not focal_relation
            or not _review_ready(value)
            or not (own or recurrent)
        ):
            continue
        review_ready.append({
            **copy.deepcopy(value),
            "relation_id": current,
            "source_replication_id": source_rep,
            "cross_replication_occurrence_count": occurrence[current],
            "own_receipt_opportunity": own,
            "review_ready_only": True,
            "admission_authority": False,
        })
    best = {}
    for value in review_ready:
        rank = (
            value["own_receipt_opportunity"],
            value["cross_replication_occurrence_count"],
            value["constraint_binding"] == "ADEQUATE",
            value["expected_cbit"] == "HIGH",
            hash_payload([ROUTING_VERSION, key, value["relation_id"]]),
        )
        incumbent = best.get(value["relation_id"])
        if incumbent is None or rank > incumbent[0]:
            best[value["relation_id"]] = (rank, value)
    selected = [
        value for _, value in sorted(
            best.values(), key=lambda pair: pair[0], reverse=True
        )[:MAXIMUM_REVIEW_OPPORTUNITIES]
    ]
    qualified = qualification_receipt["qualified"]
    commitment = {
        "routing_version": ROUTING_VERSION,
        "case_id": case_id,
        "replication_id": rep,
        "source_standard_receipt_hash": hash_payload(raw_receipt),
        "source_qualification_hash": qualification_receipt["artifact_hash"],
        "qualified": qualified,
        "review_ready_opportunities": selected,
        "allowed_opportunities": selected,
        "allowed_relations": [{
            "source_object_id": value["source_object_id"],
            "target_object_id": value["target_object_id"],
        } for value in selected],
        "delta_review_call_authorized": bool(qualified and selected),
        "delta_call_authorized": bool(qualified and selected),
        "reason": (
            "QUALIFIED_REVIEW_READY_OPPORTUNITY"
            if qualified and selected else (
                "QUALIFICATION_FAILED"
                if not qualified else "NO_REVIEW_READY_OPPORTUNITY"
            )
        ),
        "review_ready_is_not_admission_ready": True,
        "private_truth_used": False,
        "provider_call_added_by_routing": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _review_ready(value):
    if value["opportunity_type"] == "EFFECT":
        return (
            value["relation_truth_state"] == "SUPPORTED_EFFECT"
            and value["constraint_binding"] == "ADEQUATE"
            and value["expected_cbit"] in {"HIGH", "MEDIUM"}
            and value["research_value_disposition"]
            in {"PRIORITIZE", "RETAIN"}
        )
    if value["opportunity_type"] == "INFORMATIVE_NULL":
        return (
            value["relation_truth_state"]
            in {"SUPPORTED_NULL", "WEAK", "INDIRECT", "CONFLICTED"}
            and value["null_information_role"]
            == "RULES_OUT_PLAUSIBLE_CAUSE"
            and value["constraint_binding"] == "ADEQUATE"
            and value["expected_cbit"] in {"HIGH", "MEDIUM"}
            and value["research_value_disposition"]
            in {"PRIORITIZE", "RETAIN"}
        )
    return (
        value["opportunity_type"] == "QUARANTINE_ALTERNATIVE"
        and value["constraint_binding"] in {"ADEQUATE", "PARTIAL"}
        and value["expected_cbit"] in {"HIGH", "MEDIUM"}
        and value["research_value_disposition"] in {"PRIORITIZE", "RETAIN"}
    )

