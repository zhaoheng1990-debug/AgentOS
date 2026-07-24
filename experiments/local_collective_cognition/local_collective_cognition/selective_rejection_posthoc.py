"""Private-outcome audit for selective rejection v0.52."""

from __future__ import annotations

import copy

from .provider_telemetry import hash_payload
from .reference_complete_portfolio_posthoc import (
    analyze_reference_complete_portfolio_posthoc,
)


POSTHOC_VERSION = "selective_rejection_posthoc_v0_52"


def analyze_selective_rejection_posthoc(*, corpus, run, analysis):
    base = analyze_reference_complete_portfolio_posthoc(
        corpus=corpus, run=run, analysis=analysis
    )
    initial_accepts = {
        key
        for key, value in run[
            "pairwise_displacement_receipts"
        ].items()
        if value["portfolio_decision"] == "ACTIVATE_DELTA"
    }
    coordinated_accepts = {
        key
        for key, value in run["replacement_gate_receipts"].items()
        if value.get("coordinator_approved") is True
        and value["accepted"] is True
    }
    cells = []
    for value in base["cells"]:
        key = (
            f"{value['replication_id']}:A2_COMPACT_DELTA:"
            f"{value['case_id']}"
        )
        cells.append({
            **value,
            "initial_arbiter_accepted": key in initial_accepts,
            "coordinated_recovery": key in coordinated_accepts,
            "challenge_receipt": copy.deepcopy(
                run["rejection_challenge_receipts"].get(key)
            ),
            "coordination_receipt": copy.deepcopy(
                run["rejection_coordination_receipts"].get(key)
            ),
        })
    recovered = [
        value for value in cells if value["coordinated_recovery"]
    ]
    recovered_beneficial = sum(
        value["classification"] == "BENEFICIAL_ACCEPTED"
        for value in recovered
    )
    recovered_harmful = sum(
        value["classification"] == "HARMFUL_ACCEPTED"
        for value in recovered
    )
    commitment = {
        key: copy.deepcopy(value)
        for key, value in base.items()
        if key != "artifact_hash"
    }
    commitment.update({
        "posthoc_version": POSTHOC_VERSION,
        "source_runtime_version": analysis["analysis_version"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "coordinated_recovery_count": len(recovered),
        "coordinated_recovery_beneficial_count": recovered_beneficial,
        "coordinated_recovery_harmful_count": recovered_harmful,
        "coordinated_recovery_precision": round(
            recovered_beneficial / len(recovered) if recovered else 0.0,
            6,
        ),
        "cells": cells,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    })
    return {**commitment, "artifact_hash": hash_payload(commitment)}
