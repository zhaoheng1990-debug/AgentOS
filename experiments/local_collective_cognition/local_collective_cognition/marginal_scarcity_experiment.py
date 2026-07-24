"""Target-blind dual-role discovery panel v0.57."""

from __future__ import annotations

import copy
from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .frontier_experiment import TASK_KIND
from .marginal_scarcity_contract import (
    CONTRACT_VERSION,
    DISCOVERY_ROLES,
    build_discovery_view,
    discovery_schema,
    validate_discovery_receipt,
)
from .marginal_scarcity_holdout import (
    validate_marginal_scarcity_holdout,
)
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "marginal_scarcity_discovery_experiment_v0_57"


def build_discovery_preregistration(*, corpus, reference_audit):
    validate_marginal_scarcity_holdout(corpus)
    _validate_hash(reference_audit)
    if (
        reference_audit.get("reference_complete") is not True
        or reference_audit.get("reference_mismatches")
        or reference_audit.get("cross_role_disagreements")
    ):
        raise ValueError("marginal_scarcity_reference_not_complete")
    required = corpus["case_count"] * 3 * len(DISCOVERY_ROLES)
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_reference_audit_hash": reference_audit["artifact_hash"],
        "source_contract_version": CONTRACT_VERSION,
        "required_receipt_count": required,
        "minimum_receipt_coverage": 1.0,
        "minimum_consensus_count": 6,
        "minimum_exact_target_consensus_count": 3,
        "minimum_cross_replication_target_witness_count": 2,
        "maximum_active_relation_proposal_count": 0,
        "maximum_provider_calls": required,
        "hard_token_ceiling": 300000,
        "roles_are_context_isolated": True,
        "designed_target_available_during_inference": False,
        "formal_replacement_authorized": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_discovery_panel(
    *,
    corpus,
    preregistration,
    adapter,
    corpus_validator=validate_marginal_scarcity_holdout,
    runtime_version=RUNTIME_VERSION,
):
    corpus_validator(corpus)
    _validate_hash(preregistration)
    refs = tuple(corpus["evidence_refs"])
    calls, receipts, failures = [], {}, []
    for rep in corpus["replication_ids"]:
        for canonical in corpus["public_surface"]["items"]:
            item = _replication_item(
                canonical, rep=rep, corpus_hash=corpus["artifact_hash"]
            )
            view = build_discovery_view(
                item=item, corpus_hash=corpus["artifact_hash"]
            )
            for role in DISCOVERY_ROLES:
                task = _task(
                    view=view, role=role, rep=rep,
                    refs=refs, adapter=adapter,
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
                contract_failures = validate_discovery_receipt(
                    receipt=receipt, view=view, role=role, refs=refs
                )
                if contract_failures:
                    failures.append({
                        **call, "contract_failures": contract_failures
                    })
                    continue
                receipts[
                    f"{rep}:{item['case_id']}:{role}"
                ] = receipt
    consensus = {}
    for rep in corpus["replication_ids"]:
        for item in corpus["public_surface"]["items"]:
            values = [
                receipts.get(f"{rep}:{item['case_id']}:{role}")
                for role in DISCOVERY_ROLES
            ]
            if None in values:
                continue
            left, right = values
            agreed = all(
                left[field] == right[field]
                for field in (
                    "source_object_id", "target_object_id",
                    "proposed_drop_pool_id",
                )
            )
            consensus[f"{rep}:{item['case_id']}"] = {
                "agreed": agreed,
                "source_object_id": (
                    left["source_object_id"] if agreed else None
                ),
                "target_object_id": (
                    left["target_object_id"] if agreed else None
                ),
                "proposed_drop_pool_id": (
                    left["proposed_drop_pool_id"] if agreed else None
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
        "private_truth_exposed": False,
        "replacement_executed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_discovery_panel(*, corpus, preregistration, run):
    _validate_hash(run)
    bindings = corpus["private_provenance"]["bindings"]
    exact, active, witnesses = 0, 0, Counter()
    for key, value in run["consensus_candidates"].items():
        if not value["agreed"]:
            continue
        _rep, case_id = key.split(":", 1)
        relation = (
            value["source_object_id"], value["target_object_id"]
        )
        target = bindings[case_id]["designed_target_relation"]
        expected = (
            target["source_object_id"], target["target_object_id"]
        )
        exact += relation == expected
        witnesses[(case_id, relation)] += 1
        item = next(
            x for x in corpus["public_surface"]["items"]
            if x["case_id"] == case_id
        )
        active += relation in {
            (x["source_object_id"], x["target_object_id"])
            for x in item["frozen_active_portfolio"]
        }
    consensus_count = sum(
        value["agreed"]
        for value in run["consensus_candidates"].values()
    )
    witness_count = sum(value >= 2 for value in witnesses.values())
    tokens = sum(
        value["token_usage"]["total_tokens"]
        for value in run["task_calls"]
    )
    conditions = {
        "minimum_receipt_coverage": (
            len(run["receipts"])
            / preregistration["required_receipt_count"]
            >= preregistration["minimum_receipt_coverage"]
        ),
        "minimum_consensus_count": (
            consensus_count >= preregistration["minimum_consensus_count"]
        ),
        "minimum_exact_target_consensus_count": (
            exact >= preregistration["minimum_exact_target_consensus_count"]
        ),
        "minimum_cross_replication_target_witness_count": (
            witness_count
            >= preregistration[
                "minimum_cross_replication_target_witness_count"
            ]
        ),
        "maximum_active_relation_proposal_count": (
            active <= preregistration[
                "maximum_active_relation_proposal_count"
            ]
        ),
        "hard_token_ceiling": (
            tokens <= preregistration["hard_token_ceiling"]
        ),
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "receipt_count": len(run["receipts"]),
        "consensus_count": consensus_count,
        "exact_target_consensus_count": exact,
        "cross_replication_target_witness_count": witness_count,
        "active_relation_proposal_count": active,
        "physical_total_tokens": tokens,
        "conditions": conditions,
        "decision": (
            "PASS_MARGINAL_SCARCITY_DISCOVERY"
            if passed else "REJECT_MARGINAL_SCARCITY_DISCOVERY"
        ),
        "candidate_state": (
            "DISCOVERY_READY_FOR_REPLACEMENT_GATE"
            if passed else "DISCOVERY_REJECTED_STOP"
        ),
        "formal_replacement_authorized": False,
        "core_integration_authorized": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _task(
    *, view, role, rep, refs, adapter,
    runtime_version=RUNTIME_VERSION,
):
    return ProviderCognitiveTask(
        task_id=f"{runtime_version}-{rep}-{role}-{view['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Independently identify the omitted relation with the highest "
            "evidence-bound marginal Cbit and the active slot it should "
            "replace. Do not assume every effect is valuable. The other "
            "role and private reference are unavailable."
        ),
        inputs={
            "discovery_role": role,
            "discovery_view": view,
            "other_role_available": False,
            "private_truth_available": False,
            "replacement_authority": False,
        },
        allowed_evidence=list(refs),
        expected_schema=discovery_schema(
            view=view, role=role, refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _replication_item(item, *, rep, corpus_hash):
    result = copy.deepcopy(item)
    result["object_registry"].sort(
        key=lambda x: hash_payload(
            [corpus_hash, rep, "OBJECT", x["object_id"]]
        )
    )
    result["evidence_spans"].sort(
        key=lambda x: hash_payload(
            [corpus_hash, rep, "SPAN", x["span_id"]]
        )
    )
    return result


def _validate_hash(value):
    field = "run_hash" if "run_hash" in value else "artifact_hash"
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError("marginal_scarcity_source_hash_invalid")
