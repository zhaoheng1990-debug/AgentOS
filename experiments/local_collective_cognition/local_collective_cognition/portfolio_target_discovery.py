"""Target-only omitted-relation discovery for v0.61."""

from __future__ import annotations

import copy
from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload
from .portfolio_critic_fresh_holdout import (
    validate_portfolio_critic_fresh_holdout,
)


RUNTIME_VERSION = "portfolio_target_discovery_v0_61"
TARGET_ROLES = ("TARGET_PROPOSER", "TARGET_SKEPTIC")


def build_target_view(
    *, item, corpus_hash, runtime_version=RUNTIME_VERSION
):
    commitment = {
        "view_version": runtime_version,
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
        "private_truth_available": False,
        "topology_label_available": False,
        "drop_selection_requested": False,
        "replacement_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def target_schema(*, view, role, refs):
    objects = [
        value["object_id"] for value in view["object_registry"]
    ]
    spans = [value["span_id"] for value in view["evidence_spans"]]
    properties = {
        "case_id": {"type": "string", "enum": [view["case_id"]]},
        "target_role": {"type": "string", "enum": [role]},
        "source_view_hash": {
            "type": "string", "enum": [view["artifact_hash"]],
        },
        "source_object_id": {"type": "string", "enum": objects},
        "target_object_id": {"type": "string", "enum": objects},
        "evidence_span_ids": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
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


def validate_target_receipt(*, receipt, view, role, refs):
    failures = []
    if receipt.get("case_id") != view["case_id"]:
        failures.append("CASE_MISMATCH")
    if receipt.get("target_role") != role:
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
    if "proposed_drop_pool_id" in receipt:
        failures.append("DROP_FIELD_FORBIDDEN")
    return failures


def run_target_discovery(
    *,
    corpus,
    preregistration,
    adapter,
    corpus_validator=validate_portfolio_critic_fresh_holdout,
    runtime_version=RUNTIME_VERSION,
):
    corpus_validator(corpus)
    _validate_hash(preregistration)
    refs = tuple(corpus["evidence_refs"])
    calls = []
    receipts = {}
    failures = []
    for rep in corpus["replication_ids"]:
        for canonical in corpus["public_surface"]["items"]:
            item = _replication_item(
                canonical, rep=rep, corpus_hash=corpus["artifact_hash"]
            )
            view = build_target_view(
                item=item,
                corpus_hash=corpus["artifact_hash"],
                runtime_version=runtime_version,
            )
            for role in TARGET_ROLES:
                task = _task(
                    view=view,
                    role=role,
                    rep=rep,
                    refs=refs,
                    adapter=adapter,
                    runtime_version=runtime_version,
                )
                envelope = ProviderTaskRouter([adapter]).route(task)
                usage = envelope.invocation_receipt.token_usage
                call = {
                    "replication_id": rep,
                    "case_id": item["case_id"],
                    "role": role,
                    "status": envelope.status,
                    "token_usage": dict(usage),
                    "task_id": task.task_id,
                }
                calls.append(call)
                if envelope.status != "COMPLETED":
                    failures.append({**call, "failure": envelope.error})
                    continue
                receipt = envelope.normalized_result
                contract_failures = validate_target_receipt(
                    receipt=receipt,
                    view=view,
                    role=role,
                    refs=refs,
                )
                if contract_failures:
                    failures.append({
                        **call,
                        "contract_failures": contract_failures,
                    })
                    continue
                receipts[f"{rep}:{item['case_id']}:{role}"] = receipt
    consensus = {}
    for rep in corpus["replication_ids"]:
        for item in corpus["public_surface"]["items"]:
            values = [
                receipts.get(f"{rep}:{item['case_id']}:{role}")
                for role in TARGET_ROLES
            ]
            if None in values:
                continue
            left, right = values
            agreed = all(
                left[field] == right[field]
                for field in ("source_object_id", "target_object_id")
            )
            consensus[f"{rep}:{item['case_id']}"] = {
                "agreed": agreed,
                "source_object_id": (
                    left["source_object_id"] if agreed else None
                ),
                "target_object_id": (
                    left["target_object_id"] if agreed else None
                ),
            }
    commitment = {
        "runtime_version": runtime_version,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "receipts": receipts,
        "consensus_candidates": consensus,
        "failures": failures,
        "drop_field_available": False,
        "private_truth_exposed": False,
        "replacement_executed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_target_discovery(
    *,
    corpus,
    preregistration,
    run,
    corpus_validator=validate_portfolio_critic_fresh_holdout,
    runtime_version=RUNTIME_VERSION,
):
    corpus_validator(corpus)
    _validate_hash(preregistration)
    _validate_hash(run)
    bindings = corpus["private_provenance"]["bindings"]
    items = {
        value["case_id"]: value
        for value in corpus["public_surface"]["items"]
    }
    exact = 0
    wrong = 0
    active = 0
    witnesses = Counter()
    target_positions = set()
    cells = []
    for key, value in sorted(run["consensus_candidates"].items()):
        rep, case_id = key.split(":", 1)
        if not value["agreed"]:
            cells.append({
                "replication_id": rep,
                "case_id": case_id,
                "agreed": False,
            })
            continue
        relation = (
            value["source_object_id"],
            value["target_object_id"],
        )
        target = bindings[case_id]["designed_target_relation"]
        expected = (
            target["source_object_id"],
            target["target_object_id"],
        )
        target_match = relation == expected
        is_active = relation in {
            (entry["source_object_id"], entry["target_object_id"])
            for entry in items[case_id]["frozen_active_portfolio"]
        }
        exact += target_match
        wrong += not target_match
        active += is_active
        if target_match:
            witnesses[case_id] += 1
            target_positions.add(expected[0])
        cells.append({
            "replication_id": rep,
            "case_id": case_id,
            "agreed": True,
            "relation": {
                "source_object_id": relation[0],
                "target_object_id": relation[1],
            },
            "target_match": target_match,
            "active_relation": is_active,
        })
    consensus_count = sum(
        value["agreed"]
        for value in run["consensus_candidates"].values()
    )
    cross_replication = sum(value >= 2 for value in witnesses.values())
    tokens = sum(
        value["token_usage"]["total_tokens"]
        for value in run["task_calls"]
    )
    conditions = {
        "minimum_receipt_coverage": (
            len(run["receipts"])
            / preregistration["required_target_receipt_count"]
            >= preregistration["minimum_target_receipt_coverage"]
        ),
        "minimum_consensus_count": (
            consensus_count
            >= preregistration["minimum_target_consensus_count"]
        ),
        "minimum_exact_target_consensus_count": (
            exact
            >= preregistration["minimum_exact_target_consensus_count"]
        ),
        "minimum_cross_replication_target_witness_count": (
            cross_replication
            >= preregistration[
                "minimum_cross_replication_target_witness_count"
            ]
        ),
        "minimum_target_position_coverage": (
            len(target_positions)
            >= preregistration["minimum_target_position_coverage"]
        ),
        "maximum_wrong_target_consensus_count": (
            wrong
            <= preregistration["maximum_wrong_target_consensus_count"]
        ),
        "maximum_active_relation_proposal_count": (
            active
            <= preregistration["maximum_active_relation_proposal_count"]
        ),
        "maximum_target_provider_calls": (
            len(run["task_calls"])
            <= preregistration["maximum_target_provider_calls"]
        ),
        "hard_target_token_ceiling": (
            tokens <= preregistration["hard_target_token_ceiling"]
        ),
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": runtime_version,
        "source_run_hash": run["run_hash"],
        "receipt_count": len(run["receipts"]),
        "consensus_count": consensus_count,
        "exact_target_consensus_count": exact,
        "wrong_target_consensus_count": wrong,
        "cross_replication_target_witness_count": cross_replication,
        "target_position_coverage": len(target_positions),
        "covered_target_source_positions": sorted(target_positions),
        "active_relation_proposal_count": active,
        "physical_total_tokens": tokens,
        "cells": cells,
        "conditions": conditions,
        "decision": (
            "PASS_FRESH_TARGET_ONLY_DISCOVERY"
            if passed else "REJECT_FRESH_TARGET_ONLY_DISCOVERY"
        ),
        "candidate_state": (
            "FRESH_TARGETS_READY_FOR_PORTFOLIO_CRITIC"
            if passed else "FRESH_TARGET_DISCOVERY_REJECTED_STOP"
        ),
        "replacement_authorized": False,
        "core_integration_authorized": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _task(
    *,
    view,
    role,
    rep,
    refs,
    adapter,
    runtime_version=RUNTIME_VERSION,
):
    role_prompt = {
        "TARGET_PROPOSER": (
            "Identify the omitted relation with the strongest evidence-bound "
            "marginal Cbit."
        ),
        "TARGET_SKEPTIC": (
            "Independently challenge overclaim, then identify the omitted "
            "relation with the strongest evidence-bound marginal Cbit."
        ),
    }[role]
    return ProviderCognitiveTask(
        task_id=f"{runtime_version}-{rep}-{role}-{view['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            f"{role_prompt} Return only the omitted target relation and its "
            "evidence. Do not choose, rank, or mention an active portfolio "
            "slot to drop; displacement is owned by a separate critic and "
            "the Kernel. The other role and private reference are unavailable."
        ),
        inputs={
            "target_role": role,
            "target_view": view,
            "other_role_available": False,
            "private_truth_available": False,
            "drop_selection_requested": False,
            "replacement_authority": False,
        },
        allowed_evidence=list(refs),
        expected_schema=target_schema(view=view, role=role, refs=refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _replication_item(item, *, rep, corpus_hash):
    result = copy.deepcopy(item)
    result["object_registry"].sort(
        key=lambda value: hash_payload(
            [corpus_hash, rep, "OBJECT", value["object_id"]]
        )
    )
    result["evidence_spans"].sort(
        key=lambda value: hash_payload(
            [corpus_hash, rep, "SPAN", value["span_id"]]
        )
    )
    return result


def _validate_hash(value):
    field = "run_hash" if "run_hash" in value else "artifact_hash"
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError("portfolio_target_source_hash_invalid")
