"""Fresh selective PortfolioCritic and Kernel action runtime v0.61."""

from __future__ import annotations

import copy

from .portfolio_critic_fresh_holdout import (
    validate_portfolio_critic_fresh_holdout,
)
from .portfolio_target_discovery import TARGET_ROLES
from .provider_telemetry import hash_payload
from .reference_completeness_audit import (
    AUDIT_ROLES,
    validate_reference_completeness_audit,
)


RUNTIME_VERSION = "portfolio_critic_fresh_runtime_v0_61"


def build_fresh_preregistration(
    *,
    corpus,
    reference_audit,
    source_calibration_closure,
    corpus_validator=validate_portfolio_critic_fresh_holdout,
    runtime_version=RUNTIME_VERSION,
):
    corpus_validator(corpus)
    validate_reference_completeness_audit(
        audit=reference_audit, corpus=corpus
    )
    _validate_hash(source_calibration_closure)
    if reference_audit.get("reference_complete") is not True:
        raise ValueError("fresh_critic_reference_incomplete")
    if (
        source_calibration_closure.get("decision")
        != "PASS_PORTFOLIO_CRITIC_MECHANISM_CALIBRATION"
        or source_calibration_closure.get("fresh_holdout_required") is not True
        or source_calibration_closure.get("promotion_allowed") is not False
    ):
        raise ValueError("fresh_critic_source_calibration_invalid")
    target_receipts = (
        corpus["case_count"]
        * len(corpus["replication_ids"])
        * len(TARGET_ROLES)
    )
    commitment = {
        "preregistration_version": runtime_version,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_reference_audit_hash": reference_audit["artifact_hash"],
        "source_calibration_closure_hash": source_calibration_closure[
            "artifact_hash"
        ],
        "required_target_receipt_count": target_receipts,
        "minimum_target_receipt_coverage": 1.0,
        "minimum_target_consensus_count": 9,
        "minimum_exact_target_consensus_count": 9,
        "minimum_cross_replication_target_witness_count": 4,
        "minimum_target_position_coverage": 5,
        "maximum_wrong_target_consensus_count": 0,
        "maximum_active_relation_proposal_count": 0,
        "maximum_target_provider_calls": target_receipts,
        "hard_target_token_ceiling": 300000,
        "required_critic_case_count": corpus["case_count"],
        "required_context_isolated_roles": list(AUDIT_ROLES),
        "candidate_displacement_states": ["UNRESOLVED"],
        "protected_relation_states": ["SUPPORTED_EFFECT"],
        "minimum_unique_replacement_count": 2,
        "required_unique_topology_case_coverage": 2,
        "required_no_eligible_topology_case_coverage": 2,
        "required_ambiguous_topology_case_coverage": 2,
        "required_no_eligible_abstention_rate": 1.0,
        "required_ambiguous_abstention_rate": 1.0,
        "maximum_harmful_replacement_count": 0,
        "maximum_protected_knowledge_loss_count": 0,
        "maximum_critic_conflict_count": 0,
        "critic_provider_calls_allowed": 0,
        "target_drop_field_forbidden": True,
        "formal_scope": "FRESH_SYNTHETIC_CANDIDATE_ONLY",
        "core_integration_authorized": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_fresh_kernel_actions(
    *,
    corpus,
    preregistration,
    target_run,
    target_analysis,
    critic_artifact,
    corpus_validator=validate_portfolio_critic_fresh_holdout,
    runtime_version=RUNTIME_VERSION,
):
    corpus_validator(corpus)
    for value in (
        preregistration,
        target_run,
        target_analysis,
        critic_artifact,
    ):
        _validate_hash(value)
    if target_analysis.get("decision") != "PASS_FRESH_TARGET_ONLY_DISCOVERY":
        raise ValueError("fresh_target_discovery_not_ready")
    if (
        target_run.get("run_hash") != target_analysis["source_run_hash"]
        or critic_artifact.get("source_preregistration_hash")
        != preregistration["artifact_hash"]
    ):
        raise ValueError("fresh_kernel_source_binding_invalid")
    items = {
        value["case_id"]: value
        for value in corpus["public_surface"]["items"]
    }
    decisions = {}
    for key, consensus in sorted(
        target_run["consensus_candidates"].items()
    ):
        rep, case_id = key.split(":", 1)
        item = items[case_id]
        if not consensus["agreed"]:
            decisions[key] = _decision(
                rep=rep,
                case_id=case_id,
                state="ABSTAIN_TARGET_NONCONSENSUS",
                before=item["frozen_active_portfolio"],
                after=None,
                relation=None,
                selected_drop=None,
                eligible=[],
                critic_hash=None,
            )
            continue
        critic = critic_artifact["critic_receipts"][case_id]
        eligible = critic["eligible_pool_ids"]
        if critic["conflict_count"]:
            decisions[key] = _decision(
                rep=rep,
                case_id=case_id,
                state="BLOCK_CRITIC_SEMANTIC_CONFLICT",
                before=item["frozen_active_portfolio"],
                after=None,
                relation=None,
                selected_drop=None,
                eligible=eligible,
                critic_hash=critic["artifact_hash"],
            )
            continue
        if not eligible:
            decisions[key] = _decision(
                rep=rep,
                case_id=case_id,
                state="ABSTAIN_NO_ELIGIBLE_DISPLACEMENT",
                before=item["frozen_active_portfolio"],
                after=None,
                relation=None,
                selected_drop=None,
                eligible=eligible,
                critic_hash=critic["artifact_hash"],
            )
            continue
        if len(eligible) > 1:
            decisions[key] = _decision(
                rep=rep,
                case_id=case_id,
                state="ABSTAIN_AMBIGUOUS_DISPLACEMENT",
                before=item["frozen_active_portfolio"],
                after=None,
                relation=None,
                selected_drop=None,
                eligible=eligible,
                critic_hash=critic["artifact_hash"],
            )
            continue
        selected_drop = eligible[0]
        relation = {
            "pool_candidate_id": f"FRESH:{rep}",
            "source_object_id": consensus["source_object_id"],
            "target_object_id": consensus["target_object_id"],
            "evidence_span_ids": [],
        }
        after = [
            copy.deepcopy(value)
            for value in item["frozen_active_portfolio"]
            if value["pool_candidate_id"] != selected_drop
        ] + [relation]
        decisions[key] = _decision(
            rep=rep,
            case_id=case_id,
            state="REPLACED_FRESH_CANDIDATE_ONLY",
            before=item["frozen_active_portfolio"],
            after=after,
            relation=relation,
            selected_drop=selected_drop,
            eligible=eligible,
            critic_hash=critic["artifact_hash"],
        )
    commitment = {
        "runtime_version": runtime_version,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_target_run_hash": target_run["run_hash"],
        "source_target_analysis_hash": target_analysis["artifact_hash"],
        "source_critic_artifact_hash": critic_artifact["artifact_hash"],
        "decisions": decisions,
        "critic_provider_calls_used": 0,
        "private_truth_used_during_selection": False,
        "formal_scope": "FRESH_SYNTHETIC_CANDIDATE_ONLY",
        "core_integration_authorized": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_fresh_kernel_actions(
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
    unique_cases = set()
    no_eligible_cases = set()
    ambiguous_cases = set()
    unique_consensus = 0
    no_eligible_consensus = 0
    ambiguous_consensus = 0
    unique_replacements = 0
    no_eligible_abstentions = 0
    ambiguous_abstentions = 0
    target_nonconsensus = 0
    critic_conflicts = 0
    harmful = 0
    protected_loss = 0
    uplifts = []
    cells = []
    for key, decision in sorted(run["decisions"].items()):
        _rep, case_id = key.split(":", 1)
        binding = bindings[case_id]
        topology = binding["topology"]
        state = decision["state"]
        if state == "ABSTAIN_TARGET_NONCONSENSUS":
            target_nonconsensus += 1
            cells.append({
                **decision,
                "topology": topology,
                "action_correct": True,
                "action_evaluated": False,
            })
            continue
        if state == "BLOCK_CRITIC_SEMANTIC_CONFLICT":
            critic_conflicts += 1
        action_correct = False
        if topology == "UNIQUE_UNRESOLVED":
            unique_consensus += 1
            unique_cases.add(case_id)
            if state == "REPLACED_FRESH_CANDIDATE_ONLY":
                unique_replacements += 1
                target = binding["designed_target_relation"]
                exact_target = (
                    decision["admitted_relation"]["source_object_id"]
                    == target["source_object_id"]
                    and decision["admitted_relation"]["target_object_id"]
                    == target["target_object_id"]
                )
                correct_drop = (
                    decision["kernel_selected_drop_pool_id"]
                    == binding["designed_drop_pool_id"]
                )
                uplift = (
                    binding["designed_gross_cbit_uplift"]
                    if exact_target and correct_drop else -2.0
                )
                uplifts.append(uplift)
                harmful += uplift < 0
                retained = {
                    value["pool_candidate_id"]
                    for value in decision["after_portfolio"]
                }
                loss = not set(binding["protected_pool_ids"]).issubset(
                    retained
                )
                protected_loss += loss
                action_correct = exact_target and correct_drop and not loss
                cells.append({
                    **decision,
                    "topology": topology,
                    "action_correct": action_correct,
                    "action_evaluated": True,
                    "exact_hidden_target": exact_target,
                    "correct_hidden_drop": correct_drop,
                    "realized_gross_cbit": uplift,
                    "protected_knowledge_loss": loss,
                })
                continue
        elif topology == "NO_UNRESOLVED":
            no_eligible_consensus += 1
            no_eligible_cases.add(case_id)
            action_correct = state == "ABSTAIN_NO_ELIGIBLE_DISPLACEMENT"
            no_eligible_abstentions += action_correct
        elif topology == "MULTIPLE_UNRESOLVED":
            ambiguous_consensus += 1
            ambiguous_cases.add(case_id)
            action_correct = state == "ABSTAIN_AMBIGUOUS_DISPLACEMENT"
            ambiguous_abstentions += action_correct
        cells.append({
            **decision,
            "topology": topology,
            "action_correct": action_correct,
            "action_evaluated": True,
        })
    mean = sum(uplifts) / len(uplifts) if uplifts else 0.0
    conditions = {
        "minimum_unique_replacement_count": (
            unique_replacements
            >= preregistration["minimum_unique_replacement_count"]
        ),
        "required_unique_topology_case_coverage": (
            len(unique_cases)
            >= preregistration["required_unique_topology_case_coverage"]
        ),
        "required_no_eligible_topology_case_coverage": (
            len(no_eligible_cases)
            >= preregistration[
                "required_no_eligible_topology_case_coverage"
            ]
        ),
        "required_ambiguous_topology_case_coverage": (
            len(ambiguous_cases)
            >= preregistration[
                "required_ambiguous_topology_case_coverage"
            ]
        ),
        "required_no_eligible_abstention_rate": (
            no_eligible_abstentions / no_eligible_consensus
            if no_eligible_consensus else 0.0
        ) >= preregistration["required_no_eligible_abstention_rate"],
        "required_ambiguous_abstention_rate": (
            ambiguous_abstentions / ambiguous_consensus
            if ambiguous_consensus else 0.0
        ) >= preregistration["required_ambiguous_abstention_rate"],
        "maximum_harmful_replacement_count": (
            harmful
            <= preregistration["maximum_harmful_replacement_count"]
        ),
        "maximum_protected_knowledge_loss_count": (
            protected_loss
            <= preregistration["maximum_protected_knowledge_loss_count"]
        ),
        "maximum_critic_conflict_count": (
            critic_conflicts
            <= preregistration["maximum_critic_conflict_count"]
        ),
        "critic_provider_calls_allowed": (
            run["critic_provider_calls_used"]
            == preregistration["critic_provider_calls_allowed"]
        ),
    }
    passed = all(conditions.values()) and all(
        value["action_correct"]
        for value in cells if value["action_evaluated"]
    )
    commitment = {
        "analysis_version": runtime_version,
        "source_run_hash": run["run_hash"],
        "unique_consensus_count": unique_consensus,
        "unique_replacement_count": unique_replacements,
        "no_eligible_consensus_count": no_eligible_consensus,
        "no_eligible_abstention_count": no_eligible_abstentions,
        "ambiguous_consensus_count": ambiguous_consensus,
        "ambiguous_abstention_count": ambiguous_abstentions,
        "target_nonconsensus_count": target_nonconsensus,
        "critic_conflict_count": critic_conflicts,
        "unique_topology_case_coverage": len(unique_cases),
        "no_eligible_topology_case_coverage": len(no_eligible_cases),
        "ambiguous_topology_case_coverage": len(ambiguous_cases),
        "realized_gross_cbit_mean": round(mean, 6),
        "harmful_replacement_count": harmful,
        "protected_knowledge_loss_count": protected_loss,
        "cells": cells,
        "conditions": conditions,
        "decision": (
            "PASS_FRESH_PORTFOLIO_CRITIC_SELECTIVITY"
            if passed else "REJECT_FRESH_PORTFOLIO_CRITIC_SELECTIVITY"
        ),
        "candidate_state": (
            "FRESH_PORTFOLIO_CRITIC_GENERALIZATION_CANDIDATE"
            if passed else "FRESH_PORTFOLIO_CRITIC_REJECTED_STOP"
        ),
        "fresh_generalization_supported": passed,
        "core_integration_authorized": False,
        "promotion_allowed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _decision(
    *,
    rep,
    case_id,
    state,
    before,
    after,
    relation,
    selected_drop,
    eligible,
    critic_hash,
):
    commitment = {
        "replication_id": rep,
        "case_id": case_id,
        "state": state,
        "before_portfolio": copy.deepcopy(before),
        "after_portfolio": copy.deepcopy(after),
        "admitted_relation": copy.deepcopy(relation),
        "kernel_selected_drop_pool_id": selected_drop,
        "critic_eligible_pool_ids": list(eligible),
        "source_critic_receipt_hash": critic_hash,
        "final_drop_authority": "KERNEL_SELECTIVE_POLICY",
        "replacement_authority": "FRESH_SYNTHETIC_CANDIDATE_ONLY",
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _validate_hash(value):
    field = "run_hash" if "run_hash" in value else "artifact_hash"
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError("portfolio_critic_fresh_source_hash_invalid")
