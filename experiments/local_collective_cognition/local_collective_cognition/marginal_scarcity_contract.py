"""Target-blind omitted-relation discovery contract v0.57."""

from __future__ import annotations

import copy

from .provider_telemetry import hash_payload


CONTRACT_VERSION = "marginal_scarcity_discovery_contract_v0_57"
DISCOVERY_ROLES = (
    "OMITTED_RELATION_PROPOSER",
    "EVIDENCE_SKEPTIC",
)


def build_discovery_view(*, item, corpus_hash):
    commitment = {
        "view_version": CONTRACT_VERSION,
        "case_id": item["case_id"],
        "source_corpus_hash": corpus_hash,
        "objective": item["research_goal"],
        "object_registry": copy.deepcopy(item["object_registry"]),
        "evidence_spans": copy.deepcopy(item["evidence_spans"]),
        "frozen_active_portfolio": copy.deepcopy(
            item["frozen_active_portfolio"]
        ),
        "active_portfolio_capacity": item[
            "active_portfolio_capacity"
        ],
        "designed_target_available": False,
        "private_truth_available": False,
        "replacement_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def discovery_schema(*, view, role, refs):
    objects = [
        value["object_id"] for value in view["object_registry"]
    ]
    spans = [value["span_id"] for value in view["evidence_spans"]]
    pools = [
        value["pool_candidate_id"]
        for value in view["frozen_active_portfolio"]
    ]
    properties = {
        "case_id": {"type": "string", "enum": [view["case_id"]]},
        "discovery_role": {"type": "string", "enum": [role]},
        "source_view_hash": {
            "type": "string", "enum": [view["artifact_hash"]],
        },
        "source_object_id": {"type": "string", "enum": objects},
        "target_object_id": {"type": "string", "enum": objects},
        "proposed_drop_pool_id": {"type": "string", "enum": pools},
        "evidence_span_ids": {
            "type": "array", "minItems": 1, "uniqueItems": True,
            "items": {"type": "string", "enum": spans},
        },
        "marginal_cbit": {
            "type": "string", "enum": ["HIGH", "MEDIUM", "LOW"],
        },
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


def validate_discovery_receipt(*, receipt, view, role, refs):
    failures = []
    if receipt.get("case_id") != view["case_id"]:
        failures.append("CASE_MISMATCH")
    if receipt.get("discovery_role") != role:
        failures.append("ROLE_MISMATCH")
    if receipt.get("source_view_hash") != view["artifact_hash"]:
        failures.append("VIEW_HASH_MISMATCH")
    active = {
        (value["source_object_id"], value["target_object_id"])
        for value in view["frozen_active_portfolio"]
    }
    relation = (
        receipt.get("source_object_id"),
        receipt.get("target_object_id"),
    )
    if relation in active or relation[0] == relation[1]:
        failures.append("RELATION_NOT_OMITTED")
    if receipt.get("evidence_refs") != list(refs):
        failures.append("EVIDENCE_REFS_MISMATCH")
    return failures
