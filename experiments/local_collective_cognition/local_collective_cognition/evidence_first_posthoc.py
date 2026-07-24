"""Private-outcome audit for evidence-first arbitration v0.54."""

from __future__ import annotations

import copy
from collections import Counter

from .evidence_first_contract import AUDIT_ROLES
from .evidence_first_experiment import RUNTIME_VERSION
from .provider_telemetry import hash_payload
from .reference_complete_portfolio_posthoc import (
    analyze_reference_complete_portfolio_posthoc,
)


POSTHOC_VERSION = "evidence_first_arbitration_posthoc_v0_54"


def analyze_evidence_first_posthoc(*, corpus, run, analysis):
    base = analyze_reference_complete_portfolio_posthoc(
        corpus=corpus, run=run, analysis=analysis
    )
    initial = run["pairwise_displacement_receipts"]
    gates = run["replacement_gate_receipts"]
    role_receipts = run["blind_evidence_receipts"]
    recoveries = Counter()
    augmented_cells = []
    for cell in base["cells"]:
        key = (
            f"{cell['replication_id']}:A2_COMPACT_DELTA:"
            f"{cell['case_id']}"
        )
        initial_receipt = initial[key]
        gate = gates[key]
        blind = [
            copy.deepcopy(role_receipts[f"{key}:{role}"])
            for role in AUDIT_ROLES
            if f"{key}:{role}" in role_receipts
        ]
        recovered = bool(
            initial_receipt["portfolio_decision"] != "ACTIVATE_DELTA"
            and gate.get("blind_evidence_consensus") is True
            and gate["accepted"] is True
        )
        if recovered:
            if cell["proposed_minus_base"] > 0:
                recovery_class = "BENEFICIAL_RECOVERED"
            elif cell["proposed_minus_base"] < 0:
                recovery_class = "HARMFUL_RECOVERED"
            else:
                recovery_class = "TIE_RECOVERED"
            recoveries[recovery_class] += 1
        else:
            recovery_class = "NOT_RECOVERED"
        augmented_cells.append({
            **copy.deepcopy(cell),
            "initial_portfolio_decision": initial_receipt[
                "portfolio_decision"
            ],
            "initial_marginal_information_preference": initial_receipt[
                "marginal_information_preference"
            ],
            "blind_role_receipts": blind,
            "blind_consensus": gate.get(
                "blind_evidence_consensus", False
            ),
            "blind_consensus_recovery": recovered,
            "blind_recovery_classification": recovery_class,
        })
    recovered_total = sum(recoveries.values())
    beneficial = recoveries["BENEFICIAL_RECOVERED"]
    harmful = recoveries["HARMFUL_RECOVERED"]
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
        "formal_decision_unchanged": True,
        "blind_consensus_recovery_distribution": dict(recoveries),
        "blind_consensus_recovery_count": recovered_total,
        "blind_consensus_recovery_beneficial_count": beneficial,
        "blind_consensus_recovery_harmful_count": harmful,
        "blind_consensus_recovery_precision": round(
            beneficial / recovered_total if recovered_total else 0.0,
            6,
        ),
        "private_synthetic_outcomes_used_only_posthoc": True,
        "cells": augmented_cells,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    })
    return {**commitment, "artifact_hash": hash_payload(commitment)}
