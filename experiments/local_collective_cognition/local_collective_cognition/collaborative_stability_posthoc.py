"""Posthoc ceilings for v0.29; never used by the frozen decision gate."""

from __future__ import annotations

from collections import Counter, defaultdict

from .collaborative_stability_experiment import REPLICATION_IDS, ROLE_IDS
from .frontier_cbit_ledger import CBIT_WEIGHTS
from .provider_telemetry import hash_payload


def analyze_collaborative_posthoc(*, corpus, run, analysis):
    role_deltas = defaultdict(list)
    routing_gains = []
    routing_by_case = defaultdict(list)
    routing_choices = Counter()
    pool_oracle_net_deltas = []
    pool_oracle_gross_deltas = []
    pool_relation_counts = []

    for replication_id in REPLICATION_IDS:
        ledger = analysis["replication_ledgers"][replication_id]
        for item in corpus["public_surface"]["items"]:
            case_id = item["case_id"]
            truth = corpus["private_provenance"]["bindings"][case_id]
            a1_entries = [
                value for value in ledger["entries"]
                if value["arm_id"] == "A1_ONTOLOGY"
                and value["case_id"] == case_id
            ]
            a1_net = sum(
                value["realized_effective_cbit"]
                for value in a1_entries
            )
            a1_gross = sum(
                value["realized_effective_cbit"]
                + value["token_cost"]
                + value["coordination_friction_cost"]
                + value["unsupported_promotion_risk"]
                for value in a1_entries
            )
            route_scores = {"A1_ONTOLOGY": a1_net}
            for role_id in ROLE_IDS:
                role_score = _role_net_score(
                    run=run,
                    replication_id=replication_id,
                    case_id=case_id,
                    role_id=role_id,
                    truth=truth,
                )
                role_deltas[role_id].append(role_score - a1_net)
                route_scores[role_id] = role_score
            choice, best_score = max(
                route_scores.items(), key=lambda value: value[1]
            )
            gain = best_score - a1_net
            routing_gains.append(gain)
            routing_by_case[case_id].append(gain)
            routing_choices[choice] += 1

            pool = run["candidate_pools"][
                f"{replication_id}:A2_COLLAB:{case_id}"
            ]
            best_by_relation = {}
            for value in pool["candidates"]:
                candidate = value["candidate"]
                relation = (
                    candidate["source_object_id"],
                    candidate["target_object_id"],
                )
                gross = _candidate_gross(candidate, truth)
                best_by_relation[relation] = max(
                    gross, best_by_relation.get(relation, float("-inf"))
                )
            pool_relation_counts.append(len(best_by_relation))
            oracle_gross = sum(
                sorted(best_by_relation.values(), reverse=True)[:3]
            )
            path_tokens = sum(
                _call_tokens(value)
                for value in run["task_calls"]
                if value["replication_id"] == replication_id
                and value["case_id"] == case_id
                and value["experimental_arm_id"] == "A2_COLLAB"
            )
            oracle_net = (
                oracle_gross
                - path_tokens / CBIT_WEIGHTS["tokens_per_cost_unit"]
            )
            pool_oracle_net_deltas.append(oracle_net - a1_net)
            pool_oracle_gross_deltas.append(oracle_gross - a1_gross)

    valid_a2_deltas = []
    for key in run["final_projections"]:
        if ":A2_COLLAB:" not in key:
            continue
        replication_id, _, case_id = key.split(":", 2)
        totals = analysis["case_totals"][replication_id]
        valid_a2_deltas.append(
            totals[f"{case_id}:A2_COLLAB"]
            - totals[f"{case_id}:A1_ONTOLOGY"]
        )
    selector_failures = [
        value for value in run["failures"]
        if value["stage"] == "SELECTOR_VALIDATION"
    ]
    commitment = {
        "diagnostic_version": "collaborative_stability_posthoc_v0_29",
        "status": "POSTHOC_CEILING_NOT_FROZEN_GATE",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "role_standalone_delta_vs_a1": {
            role_id: _metrics(values)
            for role_id, values in role_deltas.items()
        },
        "pre_execution_role_router_oracle": {
            **_metrics(routing_gains),
            "majority_positive_case_count": sum(
                sum(value > 0 for value in values) >= 2
                for values in routing_by_case.values()
            ),
            "case_count": len(routing_by_case),
            "route_choice_counts": dict(routing_choices),
        },
        "full_pool_oracle": {
            "gross_delta_vs_a1": _metrics(
                pool_oracle_gross_deltas
            ),
            "net_delta_vs_a1_after_full_collaboration_cost": _metrics(
                pool_oracle_net_deltas
            ),
            "mean_distinct_relations_per_pool": round(
                sum(pool_relation_counts) / len(pool_relation_counts),
                6,
            ),
        },
        "actual_valid_a2_cells": {
            **_metrics(valid_a2_deltas),
            "valid_cell_count": len(valid_a2_deltas),
        },
        "selector_validation_failure_count": len(selector_failures),
        "duplicate_relation_selection_failure_count": sum(
            "SELECTED_RELATIONS_NOT_DISTINCT"
            in value.get("failures", ())
            for value in selector_failures
        ),
        "uses_private_outcomes_for_ceiling_only": True,
        "deployable_policy_claimed": False,
        "changes_frozen_decision": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _role_net_score(
    *, run, replication_id, case_id, role_id, truth
):
    key = f"{replication_id}:A2_COLLAB:{role_id}:{case_id}"
    projection = run["proposal_projections"].get(key)
    if projection is None:
        return 0.0
    eligible = [
        value for value in projection["candidate_components"]
        if value["disposition"] != "QUARANTINED_COMPONENT"
    ]
    if not eligible:
        return 0.0
    quarantine_count = sum(
        value["disposition"] == "QUARANTINED_COMPONENT"
        for value in [
            *projection["candidate_components"],
            *projection["census_components"],
        ]
    )
    call = next(
        value for value in run["task_calls"]
        if value["replication_id"] == replication_id
        and value["case_id"] == case_id
        and value["role_id"] == role_id
    )
    token_cost = (
        _call_tokens(call)
        / len(eligible)
        / CBIT_WEIGHTS["tokens_per_cost_unit"]
    )
    friction = (
        quarantine_count
        / len(eligible)
        * CBIT_WEIGHTS["quarantined_component_friction"]
    )
    return sum(
        _candidate_gross(
            value["normalized_candidate"], truth
        ) - token_cost - friction
        for value in eligible
    )


def _candidate_gross(candidate, truth):
    relation = (
        candidate["source_object_id"],
        candidate["target_object_id"],
    )
    supported = {
        (
            value["source_object_id"],
            value["target_object_id"],
        )
        for value in truth["supported_targets"]
    }
    informative_null = {
        (
            value["source_object_id"],
            value["target_object_id"],
        )
        for value in truth["informative_null_targets"]
    }
    score = CBIT_WEIGHTS["falsifiability"]
    if relation in supported:
        score += CBIT_WEIGHTS["supported_target"]
    elif relation in informative_null:
        score += CBIT_WEIGHTS["informative_null"]
    score += (
        len(
            set(relation) & set(truth["primary_object_ids"])
        ) * CBIT_WEIGHTS["primary_object"]
    )
    score += (
        len(
            set(candidate["constraint_object_ids"])
            & set(truth["hidden_constraint_object_ids"])
        ) * CBIT_WEIGHTS["hidden_constraint"]
    )
    score += (
        len(
            set(candidate["evidence_span_ids"])
            & set(truth["counterevidence_span_ids"])
        ) * CBIT_WEIGHTS["counterevidence"]
    )
    if (
        candidate["lane"] == "CORE"
        and candidate["epistemic_basis"] == "SPECULATIVE"
    ):
        score -= CBIT_WEIGHTS["unsupported_core_speculation_risk"]
    return score


def _metrics(values):
    if not values:
        return {
            "count": 0, "mean": 0.0, "median": 0.0,
            "win_count": 0, "win_rate": 0.0,
            "severe_loss_count": 0,
        }
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    median = (
        ordered[midpoint]
        if len(ordered) % 2
        else (ordered[midpoint - 1] + ordered[midpoint]) / 2
    )
    return {
        "count": len(values),
        "mean": round(sum(values) / len(values), 6),
        "median": round(median, 6),
        "win_count": sum(value > 0 for value in values),
        "win_rate": round(
            sum(value > 0 for value in values) / len(values), 6
        ),
        "severe_loss_count": sum(value < -1.0 for value in values),
    }


def _call_tokens(call):
    usage = call["invocation_receipt"].get("token_usage") or {}
    return int(
        usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    ) + int(
        usage.get("completion_tokens") or usage.get("output_tokens") or 0
    )
