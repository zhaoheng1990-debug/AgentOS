"""Private-outcome audit for context qualification v0.53."""

from __future__ import annotations

import copy

from .provider_telemetry import hash_payload
from .selective_rejection_posthoc import (
    analyze_selective_rejection_posthoc,
)


POSTHOC_VERSION = "context_qualification_posthoc_v0_53"


def analyze_context_qualification_posthoc(*, corpus, run, analysis):
    base = analyze_selective_rejection_posthoc(
        corpus=corpus, run=run, analysis=analysis
    )
    commitment = {
        key: copy.deepcopy(value)
        for key, value in base.items() if key != "artifact_hash"
    }
    commitment.update({
        "posthoc_version": POSTHOC_VERSION,
        "source_runtime_version": analysis["analysis_version"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_unlabeled_calibration_hash": run[
            "source_unlabeled_calibration_hash"
        ],
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    })
    return {**commitment, "artifact_hash": hash_payload(commitment)}
