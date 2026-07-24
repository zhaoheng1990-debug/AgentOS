"""Zero-Provider delayed consequence binding for v0.64."""

from __future__ import annotations

from typing import Any

from .provider_telemetry import hash_payload
from .selection_retention_fresh_contracts import (
    RUNTIME_VERSION,
    validate_hash_bound,
)
from .selection_retention_fresh_holdout import (
    validate_selection_retention_fresh_holdout,
)


def build_delayed_consequence_packets(
    *,
    corpus: dict[str, Any],
    selection_run: dict[str, Any],
    selection_analysis: dict[str, Any],
) -> dict[str, Any]:
    validate_selection_retention_fresh_holdout(corpus)
    for value in (selection_run, selection_analysis):
        validate_hash_bound(value)
    if selection_analysis.get("consequence_stage_authorized") is not True:
        raise ValueError("fresh_consequence_not_authorized")
    packets = {}
    private = corpus["private_provenance"]["bindings"]
    validity_evidence = {
        "CURRENT": (
            "The selected source interface and project-object boundary remain "
            "current at delayed observation; no drift was detected."
        ),
        "STALE": (
            "The delayed evidence timestamp exceeds the frozen validity "
            "boundary for the selected source."
        ),
        "DRIFTED": (
            "The selected source interface changed after selection, so the "
            "observed consequence is outside the original validity boundary."
        ),
        "UNKNOWN": (
            "The delayed observation could not establish whether the selected "
            "source boundary remained valid."
        ),
    }
    for case_id, selection in selection_run["consensus_receipts"].items():
        reference = private[case_id]
        commitment = {
            "packet_version": RUNTIME_VERSION,
            "case_id": case_id,
            "source_selection_consensus_hash": selection["artifact_hash"],
            "selected_ref": selection["selected_ref"],
            "consequence_ref": reference["consequence_ref"],
            "observed_cbit_gain": reference["observed_cbit_gain"],
            "observed_cost": reference["observed_cost"],
            "applicability_delta": reference["applicability_delta"],
            "validity_evidence": validity_evidence[
                reference["validity_state"]
            ],
            "observation_state": "DELAYED_OBSERVATION_BOUND",
            "assignment_state": "UNASSIGNED",
            "retention_candidate_state": "UNASSESSED",
            "production_write_allowed": False,
        }
        packets[case_id] = {
            **commitment,
            "artifact_hash": hash_payload(commitment),
        }
    commitment = {
        "batch_version": RUNTIME_VERSION,
        "source_selection_analysis_hash": selection_analysis["artifact_hash"],
        "packets": packets,
        "assignment_state": "UNASSIGNED",
        "provider_calls_added": 0,
        "private_reference_labels_exposed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}
