"""Private-outcome audit for admission-opportunity routing v0.46."""

from __future__ import annotations

import copy
from collections import Counter

from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_partial_admission import project_frontier_receipt
from .provider_telemetry import hash_payload
from .selective_role_routing_experiment import _metrics
from .opportunity_routing_experiment import RUNTIME_VERSION, SHARED_ARM_ID
from .opportunity_routing_holdout import REPLICATION_IDS


POSTHOC_VERSION = "opportunity_routing_posthoc_v0_46"


def analyze_opportunity_routing_posthoc(*, corpus, run, analysis):
    gated_uplifts, proposed_uplifts, oracle_uplifts, regrets = [], [], [], []
    capture = []
    classifications, reasons = Counter(), Counter()
    cells = []
    items = {
        value["case_id"]: value
        for value in corpus["public_surface"]["items"]
    }
    refs = tuple(corpus["evidence_refs"])
    for key, gate in sorted(run["replacement_gate_receipts"].items()):
        rep, arm, case_id = key.split(":", 2)
        if rep not in REPLICATION_IDS or arm != "A2_COMPACT_DELTA":
            continue
        item = items[case_id]
        base = run["raw_receipts"][
            f"{rep}:{SHARED_ARM_ID}:STANDARD_OPPORTUNITY:{case_id}"
        ]
        proposed = run["raw_receipts"][
            f"{rep}:{arm}:RUNTIME_PROPOSED:{case_id}"
        ]
        gated = run["raw_receipts"][
            f"{rep}:{arm}:RUNTIME_GATED:{case_id}"
        ]
        pool = run["candidate_pools"][key]
        composition = run["proposed_composition_receipts"][key]
        base_score, _ = _score(
            corpus=corpus, item=item, raw=base, refs=refs,
            arm_id="BASE_POSTHOC",
        )
        proposed_score, _ = _score(
            corpus=corpus, item=item, raw=proposed, refs=refs,
            arm_id="PROPOSED_POSTHOC",
        )
        gated_score, _ = _score(
            corpus=corpus, item=item, raw=gated, refs=refs,
            arm_id="GATED_POSTHOC",
        )
        pool_entries, relation_by_id = [], {}
        for pool_entry in pool["candidates"]:
            candidate = copy.deepcopy(pool_entry["candidate"])
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
                "candidate_id": pool_entry["pool_candidate_id"],
            }
            pool_entries.append(scored)
            relation_by_id[pool_entry["pool_candidate_id"]] = (
                pool_entry["relation_id"]
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
        proposed_uplift = proposed_score - base_score
        gated_uplift = gated_score - base_score
        oracle_uplift = oracle_score - base_score
        regret = oracle_score - gated_score
        if proposed_uplift > 0 and gate["accepted"]:
            classification = "BENEFICIAL_ACCEPTED"
        elif proposed_uplift > 0:
            classification = "BENEFICIAL_REJECTED"
        elif proposed_uplift < 0 and gate["accepted"]:
            classification = "HARMFUL_ACCEPTED"
        elif proposed_uplift < 0:
            classification = "HARMFUL_PREVENTED"
        elif gate["accepted"]:
            classification = "TIE_ACCEPTED"
        else:
            classification = "TIE_REJECTED"
        classifications[classification] += 1
        reasons[gate["reason"]] += 1
        proposed_uplifts.append(proposed_uplift)
        gated_uplifts.append(gated_uplift)
        oracle_uplifts.append(oracle_uplift)
        regrets.append(regret)
        if oracle_uplift > 0:
            capture.append(gated_uplift / oracle_uplift)
        semantic_scores = {
            value["pool_candidate_id"]: value
            for value in composition["scored_candidates"]
        }
        selected_ids = {
            value["pool_candidate_id"]
            for value in composition["lineage"]
        }
        diagnostics = []
        for entry in pool["candidates"]:
            candidate_id = entry["pool_candidate_id"]
            outcome = by_id.get(candidate_id)
            diagnostics.append({
                "pool_candidate_id": candidate_id,
                "relation_id": entry["relation_id"],
                "source_id": entry["source_id"],
                "selected_by_composer": candidate_id in selected_ids,
                "calibrated_semantic_score": semantic_scores[
                    candidate_id
                ]["calibrated_score"],
                "realized_effective_cbit": (
                    outcome["realized_effective_cbit"]
                    if outcome is not None else None
                ),
                "outcome_state": (
                    outcome["outcome_state"]
                    if outcome is not None else "QUARANTINED"
                ),
            })
        cells.append({
            "replication_id": rep,
            "case_id": case_id,
            "gate_accepted": gate["accepted"],
            "gate_reason": gate["reason"],
            "classification": classification,
            "base_gross_cbit": round(base_score, 6),
            "proposed_gross_cbit": round(proposed_score, 6),
            "gated_gross_cbit": round(gated_score, 6),
            "pool_oracle_gross_cbit": round(oracle_score, 6),
            "proposed_minus_base": round(proposed_uplift, 6),
            "gated_minus_base": round(gated_uplift, 6),
            "oracle_minus_base": round(oracle_uplift, 6),
            "gate_regret": round(regret, 6),
            "opportunity_routing": copy.deepcopy(
                run["opportunity_routing_receipts"][key]
            ),
            "candidate_diagnostics": diagnostics,
        })
    commitment = {
        "posthoc_version": POSTHOC_VERSION,
        "source_runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "formal_decision_unchanged": True,
        "physical_total_tokens": analysis["physical_total_tokens"],
        "shared_standard_call_count": run[
            "physical_shared_standard_call_count"
        ],
        "private_synthetic_outcomes_used": True,
        "proposed_gross_uplift": _metrics(proposed_uplifts),
        "gated_gross_uplift": _metrics(gated_uplifts),
        "pool_oracle_gross_uplift": _metrics(oracle_uplifts),
        "gate_regret": _metrics(regrets),
        "classification_distribution": dict(classifications),
        "gate_reason_distribution": dict(reasons),
        "positive_oracle_cell_count": len(capture),
        "mean_fraction_of_positive_oracle_uplift_captured": round(
            sum(capture) / len(capture) if capture else 0.0, 6
        ),
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

