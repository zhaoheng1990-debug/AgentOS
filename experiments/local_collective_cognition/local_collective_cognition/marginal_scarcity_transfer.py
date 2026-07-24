"""Fresh transfer discovery and replacement gates for v0.59."""

from __future__ import annotations

import copy
from collections import Counter

from .marginal_scarcity_contract import (
    CONTRACT_VERSION,
    DISCOVERY_ROLES,
)
from .marginal_scarcity_transfer_holdout import (
    validate_marginal_scarcity_transfer_holdout,
)
from .provider_telemetry import hash_payload
from .reference_completeness_audit import (
    validate_reference_completeness_audit,
)


RUNTIME_VERSION = "marginal_scarcity_transfer_v0_59"


def build_transfer_preregistration(
    *,
    corpus,
    reference_audit,
    source_replacement_closure,
    corpus_validator=validate_marginal_scarcity_transfer_holdout,
    runtime_version=RUNTIME_VERSION,
):
    corpus_validator(corpus)
    validate_reference_completeness_audit(
        audit=reference_audit, corpus=corpus
    )
    _validate_hash(source_replacement_closure)
    if reference_audit.get("reference_complete") is not True:
        raise ValueError("transfer_reference_not_complete")
    if (
        source_replacement_closure.get("decision")
        != "PASS_MARGINAL_SCARCITY_REPLACEMENT"
        or source_replacement_closure.get("promotion_allowed") is not False
    ):
        raise ValueError("source_replacement_closure_invalid")
    required = (
        corpus["case_count"]
        * len(corpus["replication_ids"])
        * len(DISCOVERY_ROLES)
    )
    commitment = {
        "preregistration_version": runtime_version,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_reference_audit_hash": reference_audit["artifact_hash"],
        "source_v0_58_replacement_closure_hash": (
            source_replacement_closure["artifact_hash"]
        ),
        "source_contract_version": CONTRACT_VERSION,
        "required_receipt_count": required,
        "minimum_receipt_coverage": 1.0,
        "minimum_consensus_count": 9,
        "minimum_exact_target_consensus_count": 9,
        "minimum_exact_target_and_drop_consensus_count": 6,
        "minimum_cross_replication_target_witness_count": 4,
        "minimum_target_source_position_coverage": 5,
        "minimum_drop_pool_coverage": 3,
        "maximum_wrong_target_consensus_count": 0,
        "maximum_active_relation_proposal_count": 0,
        "maximum_provider_calls": required,
        "hard_token_ceiling": 300000,
        "minimum_replacement_count": 6,
        "minimum_replacement_target_position_coverage": 5,
        "minimum_replacement_drop_pool_coverage": 3,
        "minimum_realized_gross_cbit_mean": 2.0,
        "minimum_realized_gross_cbit_median": 2.0,
        "maximum_harmful_replacement_count": 0,
        "maximum_protected_knowledge_loss_count": 0,
        "required_nonconsensus_abstention_rate": 1.0,
        "provider_calls_allowed_for_replacement": 0,
        "roles_are_context_isolated": True,
        "private_truth_available_during_inference": False,
        "formal_scope": "FRESH_SYNTHETIC_TRANSFER_CANDIDATE_ONLY",
        "core_integration_authorized": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def analyze_transfer_discovery(
    *,
    corpus,
    preregistration,
    run,
    corpus_validator=validate_marginal_scarcity_transfer_holdout,
    runtime_version=RUNTIME_VERSION,
):
    corpus_validator(corpus)
    _validate_hash(preregistration)
    _validate_hash(run)
    bindings = corpus["private_provenance"]["bindings"]
    exact_target = 0
    exact_target_and_drop = 0
    wrong_target = 0
    active = 0
    witnesses = Counter()
    target_positions = set()
    drop_pools = set()
    cells = []
    items = {
        value["case_id"]: value
        for value in corpus["public_surface"]["items"]
    }
    for key, value in sorted(run["consensus_candidates"].items()):
        rep, case_id = key.split(":", 1)
        if not value["agreed"]:
            cells.append({
                "replication_id": rep,
                "case_id": case_id,
                "agreed": False,
            })
            continue
        binding = bindings[case_id]
        relation = (
            value["source_object_id"],
            value["target_object_id"],
        )
        expected = (
            binding["designed_target_relation"]["source_object_id"],
            binding["designed_target_relation"]["target_object_id"],
        )
        target_match = relation == expected
        drop_match = (
            value["proposed_drop_pool_id"]
            == binding["designed_drop_pool_id"]
        )
        is_active = relation in {
            (entry["source_object_id"], entry["target_object_id"])
            for entry in items[case_id]["frozen_active_portfolio"]
        }
        exact_target += target_match
        exact_target_and_drop += target_match and drop_match
        wrong_target += not target_match
        active += is_active
        if target_match:
            witnesses[case_id] += 1
            target_positions.add(expected[0])
        if target_match and drop_match:
            drop_pools.add(binding["designed_drop_pool_id"])
        cells.append({
            "replication_id": rep,
            "case_id": case_id,
            "agreed": True,
            "relation": {
                "source_object_id": relation[0],
                "target_object_id": relation[1],
            },
            "target_match": target_match,
            "drop_match": drop_match,
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
            / preregistration["required_receipt_count"]
            >= preregistration["minimum_receipt_coverage"]
        ),
        "minimum_consensus_count": (
            consensus_count >= preregistration["minimum_consensus_count"]
        ),
        "minimum_exact_target_consensus_count": (
            exact_target
            >= preregistration["minimum_exact_target_consensus_count"]
        ),
        "minimum_exact_target_and_drop_consensus_count": (
            exact_target_and_drop
            >= preregistration[
                "minimum_exact_target_and_drop_consensus_count"
            ]
        ),
        "minimum_cross_replication_target_witness_count": (
            cross_replication
            >= preregistration[
                "minimum_cross_replication_target_witness_count"
            ]
        ),
        "minimum_target_source_position_coverage": (
            len(target_positions)
            >= preregistration["minimum_target_source_position_coverage"]
        ),
        "minimum_drop_pool_coverage": (
            len(drop_pools)
            >= preregistration["minimum_drop_pool_coverage"]
        ),
        "maximum_wrong_target_consensus_count": (
            wrong_target
            <= preregistration["maximum_wrong_target_consensus_count"]
        ),
        "maximum_active_relation_proposal_count": (
            active
            <= preregistration["maximum_active_relation_proposal_count"]
        ),
        "maximum_provider_calls": (
            len(run["task_calls"])
            <= preregistration["maximum_provider_calls"]
        ),
        "hard_token_ceiling": (
            tokens <= preregistration["hard_token_ceiling"]
        ),
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": runtime_version,
        "source_run_hash": run["run_hash"],
        "receipt_count": len(run["receipts"]),
        "consensus_count": consensus_count,
        "exact_target_consensus_count": exact_target,
        "exact_target_and_drop_consensus_count": exact_target_and_drop,
        "wrong_target_consensus_count": wrong_target,
        "cross_replication_target_witness_count": cross_replication,
        "target_source_position_coverage": len(target_positions),
        "covered_target_source_positions": sorted(target_positions),
        "drop_pool_coverage": len(drop_pools),
        "covered_drop_pool_ids": sorted(drop_pools),
        "active_relation_proposal_count": active,
        "physical_total_tokens": tokens,
        "cells": cells,
        "conditions": conditions,
        "decision": (
            "PASS_MARGINAL_SCARCITY_TRANSFER_DISCOVERY"
            if passed else "REJECT_MARGINAL_SCARCITY_TRANSFER_DISCOVERY"
        ),
        "candidate_state": (
            "TRANSFER_DISCOVERY_READY_FOR_REPLACEMENT"
            if passed else "TRANSFER_DISCOVERY_REJECTED_STOP"
        ),
        "formal_replacement_authorized": False,
        "core_integration_authorized": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_transfer_replacement(
    *,
    corpus,
    preregistration,
    discovery_run,
    discovery_analysis,
    corpus_validator=validate_marginal_scarcity_transfer_holdout,
    runtime_version=RUNTIME_VERSION,
):
    corpus_validator(corpus)
    for value in (preregistration, discovery_run, discovery_analysis):
        _validate_hash(value)
    if (
        discovery_analysis.get("decision")
        != "PASS_MARGINAL_SCARCITY_TRANSFER_DISCOVERY"
    ):
        raise ValueError("transfer_discovery_not_ready")
    items = {
        value["case_id"]: value
        for value in corpus["public_surface"]["items"]
    }
    allowed_drops = {
        case_id: value["designed_drop_pool_id"]
        for case_id, value in corpus["private_provenance"][
            "bindings"
        ].items()
    }
    decisions = {}
    for key, consensus in sorted(
        discovery_run["consensus_candidates"].items()
    ):
        rep, case_id = key.split(":", 1)
        item = items[case_id]
        if not consensus["agreed"]:
            decisions[key] = _decision(
                rep=rep,
                case_id=case_id,
                state="ABSTAIN_NONCONSENSUS",
                before=item["frozen_active_portfolio"],
                after=None,
                relation=None,
                drop=None,
            )
            continue
        drop = consensus["proposed_drop_pool_id"]
        if drop != allowed_drops[case_id]:
            decisions[key] = _decision(
                rep=rep,
                case_id=case_id,
                state="BLOCK_WRONG_DROP",
                before=item["frozen_active_portfolio"],
                after=None,
                relation=None,
                drop=drop,
            )
            continue
        relation = {
            "pool_candidate_id": f"TRANSFER:{rep}",
            "source_object_id": consensus["source_object_id"],
            "target_object_id": consensus["target_object_id"],
            "evidence_span_ids": [],
        }
        after = [
            copy.deepcopy(value)
            for value in item["frozen_active_portfolio"]
            if value["pool_candidate_id"] != drop
        ] + [relation]
        decisions[key] = _decision(
            rep=rep,
            case_id=case_id,
            state="REPLACED_CANDIDATE_ONLY",
            before=item["frozen_active_portfolio"],
            after=after,
            relation=relation,
            drop=drop,
        )
    commitment = {
        "runtime_version": runtime_version,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_discovery_run_hash": discovery_run["run_hash"],
        "source_discovery_analysis_hash": discovery_analysis["artifact_hash"],
        "decisions": decisions,
        "provider_calls_used": 0,
        "private_target_truth_used_during_gate": False,
        "drop_policy_frozen_before_discovery": True,
        "formal_scope": "FRESH_SYNTHETIC_TRANSFER_CANDIDATE_ONLY",
        "core_integration_authorized": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_transfer_replacement(
    *,
    corpus,
    preregistration,
    run,
    corpus_validator=validate_marginal_scarcity_transfer_holdout,
    runtime_version=RUNTIME_VERSION,
):
    corpus_validator(corpus)
    _validate_hash(preregistration)
    _validate_hash(run)
    bindings = corpus["private_provenance"]["bindings"]
    uplifts = []
    harmful = 0
    protected_loss = 0
    abstentions = 0
    target_positions = set()
    drop_pools = set()
    cells = []
    for key, decision in sorted(run["decisions"].items()):
        _rep, case_id = key.split(":", 1)
        binding = bindings[case_id]
        if decision["state"] == "ABSTAIN_NONCONSENSUS":
            abstentions += 1
            cells.append({**decision, "realized_gross_cbit": 0.0})
            continue
        if decision["state"] != "REPLACED_CANDIDATE_ONLY":
            cells.append({**decision, "realized_gross_cbit": 0.0})
            continue
        target = binding["designed_target_relation"]
        exact = (
            decision["admitted_relation"]["source_object_id"]
            == target["source_object_id"]
            and decision["admitted_relation"]["target_object_id"]
            == target["target_object_id"]
        )
        uplift = (
            binding["designed_gross_cbit_uplift"] if exact else -2.0
        )
        uplifts.append(uplift)
        harmful += uplift < 0
        retained = {
            value["pool_candidate_id"]
            for value in decision["after_portfolio"]
        }
        loss = not set(binding["protected_pool_ids"]).issubset(retained)
        protected_loss += loss
        target_positions.add(target["source_object_id"])
        drop_pools.add(decision["dropped_pool_id"])
        cells.append({
            **decision,
            "exact_hidden_target": exact,
            "realized_gross_cbit": uplift,
            "protected_knowledge_loss": loss,
        })
    ordered = sorted(uplifts)
    median = (
        (
            ordered[(len(ordered) - 1) // 2]
            + ordered[len(ordered) // 2]
        ) / 2
        if ordered else 0.0
    )
    nonconsensus = sum(
        value["state"] == "ABSTAIN_NONCONSENSUS"
        for value in run["decisions"].values()
    )
    mean = sum(uplifts) / len(uplifts) if uplifts else 0.0
    conditions = {
        "minimum_replacement_count": (
            len(uplifts) >= preregistration["minimum_replacement_count"]
        ),
        "minimum_replacement_target_position_coverage": (
            len(target_positions)
            >= preregistration[
                "minimum_replacement_target_position_coverage"
            ]
        ),
        "minimum_replacement_drop_pool_coverage": (
            len(drop_pools)
            >= preregistration["minimum_replacement_drop_pool_coverage"]
        ),
        "minimum_realized_gross_cbit_mean": (
            mean
            >= preregistration["minimum_realized_gross_cbit_mean"]
        ),
        "minimum_realized_gross_cbit_median": (
            median
            >= preregistration["minimum_realized_gross_cbit_median"]
        ),
        "maximum_harmful_replacement_count": (
            harmful
            <= preregistration["maximum_harmful_replacement_count"]
        ),
        "maximum_protected_knowledge_loss_count": (
            protected_loss
            <= preregistration["maximum_protected_knowledge_loss_count"]
        ),
        "required_nonconsensus_abstention_rate": (
            abstentions / nonconsensus if nonconsensus else 1.0
        ) >= preregistration["required_nonconsensus_abstention_rate"],
        "provider_calls_allowed_for_replacement": (
            run["provider_calls_used"]
            == preregistration["provider_calls_allowed_for_replacement"]
        ),
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": runtime_version,
        "source_run_hash": run["run_hash"],
        "replacement_count": len(uplifts),
        "abstention_count": abstentions,
        "replacement_target_position_coverage": len(target_positions),
        "covered_target_source_positions": sorted(target_positions),
        "replacement_drop_pool_coverage": len(drop_pools),
        "covered_drop_pool_ids": sorted(drop_pools),
        "realized_gross_cbit_mean": round(mean, 6),
        "realized_gross_cbit_median": round(median, 6),
        "harmful_replacement_count": harmful,
        "protected_knowledge_loss_count": protected_loss,
        "cells": cells,
        "conditions": conditions,
        "decision": (
            "PASS_MARGINAL_SCARCITY_TRANSFER_REPLACEMENT"
            if passed else "REJECT_MARGINAL_SCARCITY_TRANSFER_REPLACEMENT"
        ),
        "candidate_state": (
            "TRANSFER_REPLACEMENT_REPLICATED_CANDIDATE_ONLY"
            if passed else "TRANSFER_REPLACEMENT_REJECTED_STOP"
        ),
        "core_integration_authorized": False,
        "promotion_allowed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _decision(*, rep, case_id, state, before, after, relation, drop):
    commitment = {
        "replication_id": rep,
        "case_id": case_id,
        "state": state,
        "before_portfolio": copy.deepcopy(before),
        "after_portfolio": copy.deepcopy(after),
        "admitted_relation": copy.deepcopy(relation),
        "dropped_pool_id": drop,
        "replacement_authority": "FRESH_SYNTHETIC_CANDIDATE_ONLY",
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _validate_hash(value):
    field = "run_hash" if "run_hash" in value else "artifact_hash"
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError("marginal_scarcity_transfer_source_hash_invalid")
