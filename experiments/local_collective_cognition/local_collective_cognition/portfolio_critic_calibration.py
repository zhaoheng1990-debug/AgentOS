"""Reference-backed PortfolioCritic mechanism calibration v0.60."""

from __future__ import annotations

import copy

from .marginal_scarcity_transfer_holdout import (
    validate_marginal_scarcity_transfer_holdout_v0_59_1,
)
from .provider_telemetry import hash_payload
from .reference_completeness_audit import (
    AUDIT_ROLES,
    validate_reference_completeness_audit,
)


RUNTIME_VERSION = "portfolio_critic_calibration_v0_60"


def build_portfolio_critic_preregistration(
    *,
    corpus,
    reference_audit,
    discovery_run,
    discovery_analysis,
    discovery_closure,
):
    validate_marginal_scarcity_transfer_holdout_v0_59_1(corpus)
    validate_reference_completeness_audit(
        audit=reference_audit, corpus=corpus
    )
    for value in (
        discovery_run,
        discovery_analysis,
        discovery_closure,
    ):
        _validate_hash(value)
    if reference_audit.get("reference_complete") is not True:
        raise ValueError("portfolio_critic_reference_incomplete")
    if (
        discovery_analysis.get("decision")
        != "REJECT_MARGINAL_SCARCITY_TRANSFER_DISCOVERY"
        or discovery_analysis.get("wrong_target_consensus_count") != 0
        or discovery_closure.get(
            "target_discovery_transfer_supported"
        ) is not True
        or discovery_closure.get(
            "displacement_selection_transfer_supported"
        ) is not False
    ):
        raise ValueError("portfolio_critic_source_not_admissible")
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_reference_audit_hash": reference_audit["artifact_hash"],
        "source_discovery_run_hash": discovery_run["run_hash"],
        "source_discovery_analysis_hash": discovery_analysis[
            "artifact_hash"
        ],
        "source_discovery_closure_hash": discovery_closure[
            "artifact_hash"
        ],
        "required_candidate_cell_count": discovery_analysis[
            "consensus_count"
        ],
        "required_critic_case_count": corpus["case_count"],
        "required_context_isolated_roles": list(AUDIT_ROLES),
        "candidate_displacement_states": ["UNRESOLVED"],
        "protected_relation_states": ["SUPPORTED_EFFECT"],
        "discovery_proposed_drop_is_advisory_only": True,
        "minimum_replacement_count": discovery_analysis[
            "consensus_count"
        ],
        "minimum_target_position_coverage": 5,
        "minimum_drop_pool_coverage": 3,
        "minimum_corrective_override_count": 1,
        "maximum_harmful_replacement_count": 0,
        "maximum_protected_knowledge_loss_count": 0,
        "maximum_critic_conflict_count": 0,
        "required_nonconsensus_abstention_rate": 1.0,
        "provider_calls_allowed": 0,
        "formal_scope": "REVEALED_MECHANISM_CALIBRATION_ONLY",
        "fresh_generalization_claim_allowed": False,
        "core_integration_authorized": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def build_portfolio_critic_receipts(
    *,
    corpus,
    reference_audit,
    preregistration,
    corpus_validator=validate_marginal_scarcity_transfer_holdout_v0_59_1,
    runtime_version=RUNTIME_VERSION,
):
    corpus_validator(corpus)
    validate_reference_completeness_audit(
        audit=reference_audit, corpus=corpus
    )
    _validate_hash(preregistration)
    if (
        reference_audit.get("artifact_hash")
        != preregistration["source_reference_audit_hash"]
    ):
        raise ValueError("portfolio_critic_reference_binding_invalid")
    raw = reference_audit["raw_receipts"]
    receipts = {}
    source_receipt_hashes = {}
    for item in corpus["public_surface"]["items"]:
        case_id = item["case_id"]
        slot_assessments = []
        source_receipt_hashes[case_id] = {}
        role_maps = {}
        for role in preregistration["required_context_isolated_roles"]:
            source = raw[f"{role}:{case_id}"]
            source_receipt_hashes[case_id][role] = hash_payload(source)
            role_maps[role] = {
                value["relation_id"]: value
                for value in source["relation_assessments"]
            }
        for active in item["frozen_active_portfolio"]:
            relation_id = (
                f"REL-{active['source_object_id']}-"
                f"{active['target_object_id']}"
            )
            states = {
                role: role_maps[role][relation_id][
                    "relation_truth_state"
                ]
                for role in preregistration[
                    "required_context_isolated_roles"
                ]
            }
            unique_states = set(states.values())
            consensus_state = (
                next(iter(unique_states))
                if len(unique_states) == 1 else "CONFLICT"
            )
            slot_assessments.append({
                "pool_candidate_id": active["pool_candidate_id"],
                "source_object_id": active["source_object_id"],
                "target_object_id": active["target_object_id"],
                "role_states": states,
                "role_assessment_hashes": {
                    role: hash_payload(role_maps[role][relation_id])
                    for role in preregistration[
                        "required_context_isolated_roles"
                    ]
                },
                "consensus_state": consensus_state,
                "candidate_displacement_eligible": (
                    consensus_state
                    in preregistration["candidate_displacement_states"]
                ),
                "protected_relation": (
                    consensus_state
                    in preregistration["protected_relation_states"]
                ),
            })
        eligible = [
            value["pool_candidate_id"]
            for value in slot_assessments
            if value["candidate_displacement_eligible"]
        ]
        conflicts = sum(
            value["consensus_state"] == "CONFLICT"
            for value in slot_assessments
        )
        commitment = {
            "critic_version": runtime_version,
            "case_id": case_id,
            "source_corpus_hash": corpus["artifact_hash"],
            "source_reference_audit_hash": reference_audit[
                "artifact_hash"
            ],
            "source_role_receipt_hashes": source_receipt_hashes[case_id],
            "slot_assessments": slot_assessments,
            "eligible_pool_ids": eligible,
            "conflict_count": conflicts,
            "critic_state": (
                "READY_UNIQUE_DISPLACEMENT"
                if len(eligible) == 1 and conflicts == 0
                else "BLOCK_AMBIGUOUS_OR_CONFLICTED"
            ),
            "final_drop_authority": False,
        }
        receipts[case_id] = {
            **commitment,
            "artifact_hash": hash_payload(commitment),
        }
    commitment = {
        "artifact_version": runtime_version,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_reference_audit_hash": reference_audit["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_receipt_hashes": source_receipt_hashes,
        "critic_receipts": receipts,
        "critic_case_count": len(receipts),
        "provider_calls_added": 0,
        "source_provider_receipt_count": len(raw),
        "final_drop_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_kernel_displacement(
    *,
    corpus,
    preregistration,
    discovery_run,
    critic_artifact,
):
    validate_marginal_scarcity_transfer_holdout_v0_59_1(corpus)
    for value in (preregistration, discovery_run, critic_artifact):
        _validate_hash(value)
    if (
        discovery_run.get("run_hash")
        != preregistration["source_discovery_run_hash"]
        or critic_artifact.get("source_preregistration_hash")
        != preregistration["artifact_hash"]
    ):
        raise ValueError("kernel_displacement_source_binding_invalid")
    items = {
        value["case_id"]: value
        for value in corpus["public_surface"]["items"]
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
                selected_drop=None,
                advisory_drop=None,
                critic_hash=None,
            )
            continue
        critic = critic_artifact["critic_receipts"][case_id]
        if (
            critic["critic_state"] != "READY_UNIQUE_DISPLACEMENT"
            or len(critic["eligible_pool_ids"]) != 1
        ):
            decisions[key] = _decision(
                rep=rep,
                case_id=case_id,
                state="BLOCK_CRITIC_AMBIGUOUS_OR_CONFLICTED",
                before=item["frozen_active_portfolio"],
                after=None,
                relation=None,
                selected_drop=None,
                advisory_drop=consensus["proposed_drop_pool_id"],
                critic_hash=critic["artifact_hash"],
            )
            continue
        selected_drop = critic["eligible_pool_ids"][0]
        relation = {
            "pool_candidate_id": f"CRITIC:{rep}",
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
            state="REPLACED_MECHANISM_CALIBRATION_ONLY",
            before=item["frozen_active_portfolio"],
            after=after,
            relation=relation,
            selected_drop=selected_drop,
            advisory_drop=consensus["proposed_drop_pool_id"],
            critic_hash=critic["artifact_hash"],
        )
    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_discovery_run_hash": discovery_run["run_hash"],
        "source_critic_artifact_hash": critic_artifact["artifact_hash"],
        "decisions": decisions,
        "provider_calls_used": 0,
        "discovery_proposed_drop_used_as_authority": False,
        "private_truth_used_during_selection": False,
        "formal_scope": "REVEALED_MECHANISM_CALIBRATION_ONLY",
        "core_integration_authorized": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_kernel_displacement(*, corpus, preregistration, run):
    validate_marginal_scarcity_transfer_holdout_v0_59_1(corpus)
    _validate_hash(preregistration)
    _validate_hash(run)
    bindings = corpus["private_provenance"]["bindings"]
    uplifts = []
    abstentions = 0
    harmful = 0
    protected_loss = 0
    conflicts = 0
    corrective_overrides = 0
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
        if decision["state"] != "REPLACED_MECHANISM_CALIBRATION_ONLY":
            conflicts += 1
            cells.append({**decision, "realized_gross_cbit": 0.0})
            continue
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
        loss = not set(binding["protected_pool_ids"]).issubset(retained)
        protected_loss += loss
        target_positions.add(target["source_object_id"])
        drop_pools.add(decision["kernel_selected_drop_pool_id"])
        corrected = (
            decision["advisory_discovery_drop_pool_id"]
            != decision["kernel_selected_drop_pool_id"]
            and correct_drop
        )
        corrective_overrides += corrected
        cells.append({
            **decision,
            "exact_hidden_target": exact_target,
            "correct_hidden_drop": correct_drop,
            "corrective_override": corrected,
            "realized_gross_cbit": uplift,
            "protected_knowledge_loss": loss,
        })
    nonconsensus = sum(
        value["state"] == "ABSTAIN_NONCONSENSUS"
        for value in run["decisions"].values()
    )
    mean = sum(uplifts) / len(uplifts) if uplifts else 0.0
    ordered = sorted(uplifts)
    median = (
        (
            ordered[(len(ordered) - 1) // 2]
            + ordered[len(ordered) // 2]
        ) / 2
        if ordered else 0.0
    )
    conditions = {
        "minimum_replacement_count": (
            len(uplifts) >= preregistration["minimum_replacement_count"]
        ),
        "minimum_target_position_coverage": (
            len(target_positions)
            >= preregistration["minimum_target_position_coverage"]
        ),
        "minimum_drop_pool_coverage": (
            len(drop_pools)
            >= preregistration["minimum_drop_pool_coverage"]
        ),
        "minimum_corrective_override_count": (
            corrective_overrides
            >= preregistration["minimum_corrective_override_count"]
        ),
        "maximum_harmful_replacement_count": (
            harmful
            <= preregistration["maximum_harmful_replacement_count"]
        ),
        "maximum_protected_knowledge_loss_count": (
            protected_loss
            <= preregistration["maximum_protected_knowledge_loss_count"]
        ),
        "maximum_critic_conflict_count": (
            conflicts
            <= preregistration["maximum_critic_conflict_count"]
        ),
        "required_nonconsensus_abstention_rate": (
            abstentions / nonconsensus if nonconsensus else 1.0
        ) >= preregistration["required_nonconsensus_abstention_rate"],
        "provider_calls_allowed": (
            run["provider_calls_used"]
            == preregistration["provider_calls_allowed"]
        ),
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "replacement_count": len(uplifts),
        "abstention_count": abstentions,
        "critic_conflict_count": conflicts,
        "corrective_override_count": corrective_overrides,
        "target_position_coverage": len(target_positions),
        "covered_target_source_positions": sorted(target_positions),
        "drop_pool_coverage": len(drop_pools),
        "covered_drop_pool_ids": sorted(drop_pools),
        "realized_gross_cbit_mean": round(mean, 6),
        "realized_gross_cbit_median": round(median, 6),
        "harmful_replacement_count": harmful,
        "protected_knowledge_loss_count": protected_loss,
        "cells": cells,
        "conditions": conditions,
        "decision": (
            "PASS_PORTFOLIO_CRITIC_MECHANISM_CALIBRATION"
            if passed else "REJECT_PORTFOLIO_CRITIC_MECHANISM_CALIBRATION"
        ),
        "candidate_state": (
            "PORTFOLIO_CRITIC_READY_FOR_FRESH_HOLDOUT"
            if passed else "PORTFOLIO_CRITIC_MECHANISM_REJECTED"
        ),
        "fresh_generalization_claim": False,
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
    advisory_drop,
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
        "advisory_discovery_drop_pool_id": advisory_drop,
        "source_critic_receipt_hash": critic_hash,
        "final_drop_authority": "KERNEL_MECHANICAL_POLICY",
        "replacement_authority": "REVEALED_MECHANISM_CALIBRATION_ONLY",
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _validate_hash(value):
    field = "run_hash" if "run_hash" in value else "artifact_hash"
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError("portfolio_critic_source_hash_invalid")
