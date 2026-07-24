"""Kernel-owned synthetic replacement gate for v0.58."""

from __future__ import annotations

import copy

from .marginal_scarcity_holdout import (
    validate_marginal_scarcity_holdout,
)
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "marginal_scarcity_replacement_gate_v0_58"


def build_replacement_preregistration(
    *, corpus, discovery_preregistration, discovery_run,
    discovery_analysis, discovery_closure,
):
    validate_marginal_scarcity_holdout(corpus)
    for value in (
        discovery_preregistration,
        discovery_run,
        discovery_analysis,
        discovery_closure,
    ):
        _validate_hash(value)
    if (
        discovery_analysis.get("decision")
        != "PASS_MARGINAL_SCARCITY_DISCOVERY"
        or discovery_closure.get("replacement_gate_ready") is not True
    ):
        raise ValueError("replacement_source_not_ready")
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_discovery_preregistration_hash": (
            discovery_preregistration["artifact_hash"]
        ),
        "source_discovery_run_hash": discovery_run["run_hash"],
        "source_discovery_analysis_hash": discovery_analysis[
            "artifact_hash"
        ],
        "source_discovery_closure_hash": discovery_closure[
            "artifact_hash"
        ],
        "only_allowed_drop_pool_id": "BASE:C3",
        "minimum_replacement_count": 6,
        "minimum_realized_gross_cbit_mean": 2.0,
        "minimum_realized_gross_cbit_median": 2.0,
        "maximum_harmful_replacement_count": 0,
        "maximum_protected_knowledge_loss_count": 0,
        "required_nonconsensus_abstention_rate": 1.0,
        "provider_calls_allowed": 0,
        "formal_replacement_scope": "SYNTHETIC_CANDIDATE_ONLY",
        "core_integration_authorized": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_replacement_gate(*, corpus, preregistration, discovery_run):
    validate_marginal_scarcity_holdout(corpus)
    _validate_hash(preregistration)
    _validate_hash(discovery_run)
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
                rep=rep, case_id=case_id, state="ABSTAIN_NONCONSENSUS",
                before=item["frozen_active_portfolio"], after=None,
                relation=None, drop=None,
            )
            continue
        drop = consensus["proposed_drop_pool_id"]
        if drop != preregistration["only_allowed_drop_pool_id"]:
            decisions[key] = _decision(
                rep=rep, case_id=case_id, state="BLOCK_WRONG_DROP",
                before=item["frozen_active_portfolio"], after=None,
                relation=None, drop=drop,
            )
            continue
        relation = {
            "pool_candidate_id": f"DISCOVERY:{rep}",
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
            rep=rep, case_id=case_id, state="REPLACED_CANDIDATE_ONLY",
            before=item["frozen_active_portfolio"], after=after,
            relation=relation, drop=drop,
        )
    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_discovery_run_hash": discovery_run["run_hash"],
        "decisions": decisions,
        "provider_calls_used": 0,
        "private_truth_used_during_gate": False,
        "formal_replacement_scope": "SYNTHETIC_CANDIDATE_ONLY",
        "core_integration_authorized": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_replacement_gate(*, corpus, preregistration, run):
    _validate_hash(run)
    bindings = corpus["private_provenance"]["bindings"]
    uplifts, harmful, protected_loss, abstentions = [], 0, 0, 0
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
        loss = not {"BASE:C1", "BASE:C2"}.issubset(retained)
        protected_loss += loss
        cells.append({
            **decision,
            "exact_hidden_target": exact,
            "realized_gross_cbit": uplift,
            "protected_knowledge_loss": loss,
        })
    ordered = sorted(uplifts)
    median = (
        (ordered[(len(ordered) - 1) // 2] + ordered[len(ordered) // 2])
        / 2 if ordered else 0.0
    )
    nonconsensus = sum(
        value["state"] == "ABSTAIN_NONCONSENSUS"
        for value in run["decisions"].values()
    )
    conditions = {
        "minimum_replacement_count": (
            len(uplifts) >= preregistration["minimum_replacement_count"]
        ),
        "minimum_realized_gross_cbit_mean": (
            sum(uplifts) / len(uplifts)
            >= preregistration["minimum_realized_gross_cbit_mean"]
            if uplifts else False
        ),
        "minimum_realized_gross_cbit_median": (
            median >= preregistration[
                "minimum_realized_gross_cbit_median"
            ]
        ),
        "maximum_harmful_replacement_count": (
            harmful
            <= preregistration["maximum_harmful_replacement_count"]
        ),
        "maximum_protected_knowledge_loss_count": (
            protected_loss
            <= preregistration[
                "maximum_protected_knowledge_loss_count"
            ]
        ),
        "required_nonconsensus_abstention_rate": (
            abstentions / nonconsensus if nonconsensus else 1.0
        ) >= preregistration["required_nonconsensus_abstention_rate"],
        "provider_calls_allowed": run["provider_calls_used"] == 0,
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "replacement_count": len(uplifts),
        "abstention_count": abstentions,
        "realized_gross_cbit_mean": (
            round(sum(uplifts) / len(uplifts), 6) if uplifts else 0.0
        ),
        "realized_gross_cbit_median": round(median, 6),
        "harmful_replacement_count": harmful,
        "protected_knowledge_loss_count": protected_loss,
        "cells": cells,
        "conditions": conditions,
        "decision": (
            "PASS_MARGINAL_SCARCITY_REPLACEMENT"
            if passed else "REJECT_MARGINAL_SCARCITY_REPLACEMENT"
        ),
        "candidate_state": (
            "REPLACEMENT_REPLICATED_CANDIDATE_ONLY"
            if passed else "REPLACEMENT_REJECTED_STOP"
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
        "replacement_authority": "SYNTHETIC_CANDIDATE_ONLY",
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _validate_hash(value):
    field = "run_hash" if "run_hash" in value else "artifact_hash"
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError("replacement_source_hash_invalid")
