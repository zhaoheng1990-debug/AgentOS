"""Private-outcome audit for selective single-delta composition v0.41."""

from __future__ import annotations

import copy
from collections import Counter

from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_partial_admission import project_frontier_receipt
from .provider_telemetry import hash_payload
from .selective_role_routing_experiment import _metrics
from .selective_delta_experiment import RUNTIME_VERSION
from .selective_delta_holdout import REPLICATION_IDS


POSTHOC_VERSION = "selective_delta_posthoc_v0_41"


def analyze_selective_delta_posthoc(*, corpus, run, analysis):
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
        if rep not in REPLICATION_IDS or arm != "A2_SELECTIVE_DELTA":
            continue
        item = items[case_id]
        base = run["raw_receipts"][
            f"{rep}:{arm}:STANDARD_SELECTIVE_DELTA:{case_id}"
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
        relation_by_id = {}
        for entry in pool["candidates"]:
            candidate = copy.deepcopy(entry["candidate"])
            candidate["candidate_id"] = entry["pool_candidate_id"]
            pooled_raw["problem_candidates"].append(candidate)
            relation_by_id[entry["pool_candidate_id"]] = entry[
                "relation_id"
            ]
        _, pool_entries = _score(
            corpus=corpus, item=item, raw=pooled_raw, refs=refs,
            arm_id="POOL_POSTHOC",
        )
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
        for lineage in composition["lineage"]:
            entry = by_id[lineage["pool_candidate_id"]]
            selected_outcomes[(
                lineage["source_id"], entry["outcome_state"]
            )] += 1
        for scored in composition["scored_candidates"]:
            outcome = by_id[scored["pool_candidate_id"]][
                "outcome_state"
            ]
            selective_delta = scored["provider_candidate_value"]
            value_outcomes[(
                scored["source_id"],
                selective_delta["research_value_disposition"],
                selective_delta["relation_truth_state"],
                outcome,
            )] += 1
            if selective_delta["relation_truth_state"] == "SUPPORTED_NULL":
                null_outcomes[(
                    selective_delta["null_information_role"],
                    selective_delta["research_value_disposition"],
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
            value.get("stage") == "COUNTER_SELECTIVE_DELTA_CONTRACT"
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
        "selective_delta_outcome_distribution": {
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

