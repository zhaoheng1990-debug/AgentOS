"""Private-outcome diagnostic decomposition for completed v0.36 evidence."""

from __future__ import annotations

import copy
from collections import Counter

from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_partial_admission import project_frontier_receipt
from .independent_arbitration_experiment import (
    ARM_IDS,
    RUNTIME_VERSION,
)
from .independent_arbitration_holdout import REPLICATION_IDS
from .provider_telemetry import hash_payload
from .selective_role_routing_experiment import _metrics


POSTHOC_VERSION = "independent_arbitration_posthoc_v0_36"


def analyze_independent_arbitration_posthoc(*, corpus, run, analysis):
    counter_uplifts, selected_uplifts, oracle_uplifts = [], [], []
    regrets, captured = [], []
    selected_outcomes = Counter()
    cells = []
    items = {
        value["case_id"]: value
        for value in corpus["public_surface"]["items"]
    }
    refs = tuple(corpus["evidence_refs"])
    for key, receipt in sorted(run["arbitration_receipts"].items()):
        rep, arm, case_id = key.split(":", 2)
        if rep not in REPLICATION_IDS or arm != "A2_ARBITRATED":
            continue
        item = items[case_id]
        base = run["raw_receipts"][
            f"{rep}:{arm}:STANDARD_ONTOLOGY:{case_id}"
        ]
        counter = run["raw_receipts"][
            f"{rep}:{arm}:INDEPENDENT_COUNTERPROPOSAL:{case_id}"
        ]
        selected = run["raw_receipts"][
            f"{rep}:{arm}:RUNTIME_MATERIALIZED:{case_id}"
        ]
        pool = run["candidate_pools"][key]
        base_score, _ = _score_receipt(
            corpus=corpus, item=item, raw=base, refs=refs,
            arm_id="BASE_POSTHOC",
        )
        counter_score, _ = _score_receipt(
            corpus=corpus, item=item, raw=counter, refs=refs,
            arm_id="COUNTER_POSTHOC",
        )
        selected_score, _ = _score_receipt(
            corpus=corpus, item=item, raw=selected, refs=refs,
            arm_id="SELECTED_POSTHOC",
        )
        pooled_raw = {
            "case_id": case_id,
            "arm_id": "A1_ONTOLOGY",
            "problem_candidates": [],
            "selected_problem_id": pool["candidates"][0][
                "pool_candidate_id"
            ],
            "rationale": "Private-outcome diagnostic pool only.",
            "evidence_refs": list(refs),
            "object_census": copy.deepcopy(base["object_census"]),
        }
        relation_by_candidate = {}
        source_by_candidate = {}
        for entry in pool["candidates"]:
            candidate = copy.deepcopy(entry["candidate"])
            candidate["candidate_id"] = entry["pool_candidate_id"]
            pooled_raw["problem_candidates"].append(candidate)
            relation_by_candidate[entry["pool_candidate_id"]] = entry[
                "relation_id"
            ]
            source_by_candidate[entry["pool_candidate_id"]] = entry[
                "source_id"
            ]
        _, pool_entries = _score_receipt(
            corpus=corpus, item=item, raw=pooled_raw, refs=refs,
            arm_id="POOL_POSTHOC",
        )
        best_by_relation = {}
        by_candidate = {}
        for entry in pool_entries:
            candidate_id = entry["candidate_id"]
            by_candidate[candidate_id] = entry
            relation = relation_by_candidate[candidate_id]
            incumbent = best_by_relation.get(relation)
            if incumbent is None or (
                entry["realized_effective_cbit"],
                candidate_id,
            ) > (
                incumbent["realized_effective_cbit"],
                incumbent["candidate_id"],
            ):
                best_by_relation[relation] = entry
        oracle_entries = sorted(
            best_by_relation.values(),
            key=lambda value: (
                value["realized_effective_cbit"],
                value["candidate_id"],
            ),
            reverse=True,
        )[:3]
        oracle_score = sum(
            value["realized_effective_cbit"] for value in oracle_entries
        )
        for lineage in receipt["lineage"]:
            outcome = by_candidate[lineage["pool_candidate_id"]][
                "outcome_state"
            ]
            selected_outcomes[(lineage["source_id"], outcome)] += 1
        counter_uplift = counter_score - base_score
        selected_uplift = selected_score - base_score
        oracle_uplift = oracle_score - base_score
        regret = oracle_score - selected_score
        counter_uplifts.append(counter_uplift)
        selected_uplifts.append(selected_uplift)
        oracle_uplifts.append(oracle_uplift)
        regrets.append(regret)
        if oracle_uplift > 0:
            captured.append(selected_uplift / oracle_uplift)
        cells.append({
            "replication_id": rep,
            "case_id": case_id,
            "base_gross_cbit": round(base_score, 6),
            "counter_gross_cbit": round(counter_score, 6),
            "selected_gross_cbit": round(selected_score, 6),
            "pool_oracle_gross_cbit": round(oracle_score, 6),
            "counter_minus_base": round(counter_uplift, 6),
            "selected_minus_base": round(selected_uplift, 6),
            "oracle_minus_base": round(oracle_uplift, 6),
            "arbitration_regret": round(regret, 6),
            "selected_pool_candidate_ids": [
                value["pool_candidate_id"]
                for value in receipt["lineage"]
            ],
            "oracle_pool_candidate_ids": [
                value["candidate_id"] for value in oracle_entries
            ],
        })
    outcome_distribution = {
        f"{source}:{outcome}": count
        for (source, outcome), count in sorted(
            selected_outcomes.items()
        )
    }
    commitment = {
        "posthoc_version": POSTHOC_VERSION,
        "source_runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "formal_decision_unchanged": True,
        "private_synthetic_outcomes_used": True,
        "counterproposal_gross_uplift": _metrics(counter_uplifts),
        "selected_gross_uplift": _metrics(selected_uplifts),
        "pool_oracle_gross_uplift": _metrics(oracle_uplifts),
        "arbitration_regret": _metrics(regrets),
        "mean_fraction_of_positive_oracle_uplift_captured": round(
            sum(captured) / len(captured) if captured else 0.0, 6
        ),
        "positive_oracle_cell_count": len(captured),
        "selected_source_outcome_distribution": outcome_distribution,
        "cells": cells,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _score_receipt(*, corpus, item, raw, refs, arm_id):
    projection = project_frontier_receipt(
        raw_receipt=raw,
        item=item,
        arm_id="A1_ONTOLOGY",
        evidence_refs=refs,
    )
    commitment = {
        "task_calls": [{
            "arm_id": arm_id,
            "case_id": item["case_id"],
            "invocation_receipt": {
                "token_usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "provider_calls": 0,
                },
            },
        }],
        "projections": {
            f"{arm_id}:{item['case_id']}": projection,
        },
    }
    scoring_run = {
        **commitment,
        "run_hash": hash_payload(commitment),
    }
    ledger = build_realized_cbit_ledger(
        corpus=corpus, run=scoring_run
    )
    entries = ledger["entries"]
    return (
        sum(value["realized_effective_cbit"] for value in entries),
        entries,
    )
