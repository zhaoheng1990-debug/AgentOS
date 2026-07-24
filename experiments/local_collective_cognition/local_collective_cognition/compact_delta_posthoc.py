"""Private-outcome audit for compact semantic-delta composition v0.42."""

from __future__ import annotations

import copy
from collections import Counter

from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_partial_admission import project_frontier_receipt
from .provider_telemetry import hash_payload
from .selective_role_routing_experiment import _metrics
from .compact_delta_experiment import RUNTIME_VERSION
from .compact_delta_holdout import REPLICATION_IDS


POSTHOC_VERSION = "compact_delta_posthoc_v0_42"


def analyze_compact_delta_posthoc(*, corpus, run, analysis):
    selected_uplifts, oracle_uplifts = [], []
    regrets, capture = [], []
    selected_outcomes, value_outcomes = Counter(), Counter()
    null_outcomes = Counter()
    cells = []
    items = {
        value["case_id"]: value
        for value in corpus["public_surface"]["items"]
    }
    refs = tuple(corpus["evidence_refs"])
    for key, composition in sorted(run["composition_receipts"].items()):
        rep, arm, case_id = key.split(":", 2)
        if rep not in REPLICATION_IDS or arm != "A2_COMPACT_DELTA":
            continue
        item = items[case_id]
        base = run["raw_receipts"][
            f"{rep}:{arm}:STANDARD_COMPACT_DELTA:{case_id}"
        ]
        selected = run["raw_receipts"][
            f"{rep}:{arm}:RUNTIME_COMPOSED:{case_id}"
        ]
        pool = run["candidate_pools"][key]
        base_score, _ = _score(
            corpus=corpus, item=item, raw=base, refs=refs,
            arm_id="BASE_POSTHOC",
        )
        selected_score, _ = _score(
            corpus=corpus, item=item, raw=selected, refs=refs,
            arm_id="SELECTED_POSTHOC",
        )
        relation_by_id = {}
        pool_entries = []
        for entry in pool["candidates"]:
            candidate = copy.deepcopy(entry["candidate"])
            candidate["candidate_id"] = "C1"
            diagnostic_raw = {
                "case_id": case_id,
                "arm_id": "A1_ONTOLOGY",
                "problem_candidates": [candidate],
                "selected_problem_id": "C1",
                "rationale": "Single-candidate private diagnostic.",
                "evidence_refs": list(refs),
                "object_census": copy.deepcopy(base["object_census"]),
            }
            _, scored_entries = _score(
                corpus=corpus, item=item, raw=diagnostic_raw,
                refs=refs, arm_id="POOL_POSTHOC",
            )
            if not scored_entries:
                continue
            scored = {
                **scored_entries[0],
                "candidate_id": entry["pool_candidate_id"],
            }
            pool_entries.append(scored)
            relation_by_id[entry["pool_candidate_id"]] = entry[
                "relation_id"
            ]
        by_id = {
            value["candidate_id"]: value for value in pool_entries
        }
        best_by_relation = {}
        for entry in pool_entries:
            relation = relation_by_id[entry["candidate_id"]]
            incumbent = best_by_relation.get(relation)
            if incumbent is None or (
                entry["realized_effective_cbit"],
                entry["candidate_id"],
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
        selected_ids = {
            value["pool_candidate_id"] for value in composition["lineage"]
        }
        semantic_scores = {
            value["pool_candidate_id"]: value
            for value in composition["scored_candidates"]
        }
        candidate_diagnostics = []
        for entry in pool["candidates"]:
            candidate_id = entry["pool_candidate_id"]
            outcome = by_id.get(candidate_id)
            semantic = semantic_scores[candidate_id]
            candidate_diagnostics.append({
                "pool_candidate_id": candidate_id,
                "relation_id": entry["relation_id"],
                "source_id": entry["source_id"],
                "selected": candidate_id in selected_ids,
                "calibrated_semantic_score": semantic[
                    "calibrated_score"
                ],
                "realized_effective_cbit": (
                    outcome["realized_effective_cbit"]
                    if outcome is not None else None
                ),
                "outcome_state": (
                    outcome["outcome_state"]
                    if outcome is not None else "QUARANTINED"
                ),
            })
        for lineage in composition["lineage"]:
            entry = by_id[lineage["pool_candidate_id"]]
            selected_outcomes[(
                lineage["source_id"], entry["outcome_state"]
            )] += 1
        for scored in composition["scored_candidates"]:
            eligible_entry = by_id.get(scored["pool_candidate_id"])
            outcome = (
                eligible_entry["outcome_state"]
                if eligible_entry is not None else "QUARANTINED"
            )
            compact_delta = scored["provider_candidate_value"]
            value_outcomes[(
                scored["source_id"],
                compact_delta["research_value_disposition"],
                compact_delta["relation_truth_state"],
                outcome,
            )] += 1
            if compact_delta["relation_truth_state"] == "SUPPORTED_NULL":
                null_outcomes[(
                    compact_delta["null_information_role"],
                    compact_delta["research_value_disposition"],
                    outcome,
                )] += 1
        selected_uplift = selected_score - base_score
        oracle_uplift = oracle_score - base_score
        regret = oracle_score - selected_score
        selected_uplifts.append(selected_uplift)
        oracle_uplifts.append(oracle_uplift)
        regrets.append(regret)
        if oracle_uplift > 0:
            capture.append(selected_uplift / oracle_uplift)
        cells.append({
            "replication_id": rep,
            "case_id": case_id,
            "base_gross_cbit": round(base_score, 6),
            "selected_gross_cbit": round(selected_score, 6),
            "pool_oracle_gross_cbit": round(oracle_score, 6),
            "selected_minus_base": round(selected_uplift, 6),
            "oracle_minus_base": round(oracle_uplift, 6),
            "composition_regret": round(regret, 6),
            "candidate_diagnostics": candidate_diagnostics,
        })
    commitment = {
        "posthoc_version": POSTHOC_VERSION,
        "source_runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "formal_decision_unchanged": True,
        "private_synthetic_outcomes_used": True,
        "delta_standalone_comparison_defined": False,
        "delta_standalone_reason": (
            "A one-candidate delta is not a complete three-candidate arm."
        ),
        "raw_trigger_count": sum(
            value["triggered"]
            for value in run["trigger_receipts"].values()
        ),
        "qualified_count": sum(
            value["qualified"]
            for value in run["qualification_receipts"].values()
        ),
        "valid_delta_composition_count": len(
            run["composition_receipts"]
        ),
        "invalid_delta_contract_count": sum(
            value.get("stage") == "COUNTER_COMPACT_DELTA_CONTRACT"
            for value in run["failures"]
        ),
        "selected_gross_uplift": _metrics(selected_uplifts),
        "pool_oracle_gross_uplift": _metrics(oracle_uplifts),
        "composition_regret": _metrics(regrets),
        "mean_fraction_of_positive_oracle_uplift_captured": round(
            sum(capture) / len(capture) if capture else 0.0, 6
        ),
        "positive_oracle_cell_count": len(capture),
        "selected_source_outcome_distribution": {
            f"{source}:{outcome}": count
            for (source, outcome), count in sorted(
                selected_outcomes.items()
            )
        },
        "compact_delta_outcome_distribution": {
            f"{source}:{disposition}:{truth}:{outcome}": count
            for (source, disposition, truth, outcome), count in sorted(
                value_outcomes.items()
            )
        },
        "supported_null_outcome_distribution": {
            f"{null_state}:{disposition}:{outcome}": count
            for (null_state, disposition, outcome), count in sorted(
                null_outcomes.items()
            )
        },
        "cells": cells,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _score(*, corpus, item, raw, refs, arm_id):
    projection = project_frontier_receipt(
        raw_receipt=raw, item=item, arm_id="A1_ONTOLOGY",
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
        **commitment, "run_hash": hash_payload(commitment)
    }
    ledger = build_realized_cbit_ledger(
        corpus=corpus, run=scoring_run
    )
    entries = ledger["entries"]
    return (
        sum(value["realized_effective_cbit"] for value in entries),
        entries,
    )

