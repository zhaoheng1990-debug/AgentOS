"""Private-outcome decomposition for v0.56."""

from __future__ import annotations

import copy
from collections import Counter

from .effect_witness_experiment import RUNTIME_VERSION
from .evidence_first_posthoc import analyze_evidence_first_posthoc
from .provider_telemetry import hash_payload


POSTHOC_VERSION = "effect_witness_posthoc_v0_56"


def analyze_effect_witness_posthoc(*, corpus, run, analysis):
    base = analyze_evidence_first_posthoc(
        corpus=corpus, run=run, analysis=analysis
    )
    cells = []
    effect_outcomes = Counter()
    blocked = Counter()
    for cell in base["cells"]:
        key = (
            f"{cell['replication_id']}:A2_COMPACT_DELTA:"
            f"{cell['case_id']}"
        )
        rep, arm, case_id = key.split(":", 2)
        delta = run["raw_receipts"][
            f"{rep}:{arm}:PROVIDER_COMPACT_DELTA:{case_id}"
        ]
        gate = run["replacement_gate_receipts"][key]
        witnesses = run["independent_effect_witness_receipts"].get(
            key, []
        )
        lane = delta["proposed_admission_lane"]
        if lane == "EFFECT":
            effect_outcomes[cell["classification"]] += 1
            if not gate["accepted"]:
                blocked[gate["reason"]] += 1
        cells.append({
            **copy.deepcopy(cell),
            "proposed_admission_lane": lane,
            "proposed_relation": {
                "source_object_id": delta["source_object_id"],
                "target_object_id": delta["target_object_id"],
            },
            "independent_effect_witness_count": len(witnesses),
            "independent_effect_witnesses": copy.deepcopy(witnesses),
            "protected_supported_null": gate[
                "protected_supported_null"
            ],
            "effect_witness_used": gate.get(
                "independent_effect_witness_used", False
            ),
        })
    beneficial_effect = effect_outcomes["BENEFICIAL_REJECTED"]
    harmful_effect = effect_outcomes["HARMFUL_PREVENTED"]
    witnessed_beneficial = sum(
        value["proposed_admission_lane"] == "EFFECT"
        and value["classification"] == "BENEFICIAL_REJECTED"
        and value["independent_effect_witness_count"] > 0
        for value in cells
    )
    protected_beneficial = sum(
        value["proposed_admission_lane"] == "EFFECT"
        and value["classification"] == "BENEFICIAL_REJECTED"
        and value["protected_supported_null"] is True
        for value in cells
    )
    commitment = {
        key: copy.deepcopy(value)
        for key, value in base.items()
        if key not in {"artifact_hash", "cells"}
    }
    commitment.update({
        "posthoc_version": POSTHOC_VERSION,
        "source_runtime_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "effect_outcome_distribution": dict(effect_outcomes),
        "effect_block_reason_distribution": dict(blocked),
        "beneficial_effect_rejected_count": beneficial_effect,
        "harmful_effect_prevented_count": harmful_effect,
        "witnessed_beneficial_effect_rejected_count": witnessed_beneficial,
        "protected_beneficial_effect_rejected_count": protected_beneficial,
        "cells": cells,
        "formal_decision_unchanged": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    })
    return {**commitment, "artifact_hash": hash_payload(commitment)}
