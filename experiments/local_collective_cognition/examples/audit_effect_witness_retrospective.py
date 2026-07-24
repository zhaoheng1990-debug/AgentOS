"""Audit v0.53 EFFECT misses with the v0.55 witness contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.effect_witness_contract import (  # noqa: E402
    CONTRACT_VERSION,
    derive_independent_effect_witnesses,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    source = REPO_ROOT / "outputs" / "context_qualification_v0_53"
    output = REPO_ROOT / "outputs" / "relation_stability_audit_v0_55"
    run = read(source / "context_qualification_run.json")
    posthoc = read(source / "posthoc_context_qualification.json")
    cells = []
    for cell in posthoc["cells"]:
        if (
            cell["classification"] != "BENEFICIAL_REJECTED"
            or cell["gate_reason"] != "BOUND_LANE_REQUIREMENT_NOT_MET"
        ):
            continue
        rep = cell["replication_id"]
        case_id = cell["case_id"]
        arm = "A2_COMPACT_DELTA"
        delta = run["raw_receipts"][
            f"{rep}:{arm}:PROVIDER_COMPACT_DELTA:{case_id}"
        ]
        witnesses = derive_independent_effect_witnesses(
            raw_receipts=run["raw_receipts"],
            lineage_valid_keys=run["lineage_valid_keys"],
            source_replication_id=rep,
            arm_id=arm,
            case_id=case_id,
            source_object_id=delta["source_object_id"],
            target_object_id=delta["target_object_id"],
        )
        cells.append({
            "replication_id": rep,
            "case_id": case_id,
            "relation": {
                "source_object_id": delta["source_object_id"],
                "target_object_id": delta["target_object_id"],
            },
            "old_witness_count": len(
                cell["pairwise_displacement_receipt"].get(
                    "cross_replication_witnesses", []
                )
            ),
            "independent_delta_witnesses": witnesses,
            "retrospectively_witness_eligible": bool(witnesses),
        })
    commitment = {
        "audit_version": "effect_witness_retrospective_v0_55",
        "source_run_hash": run["run_hash"],
        "source_posthoc_hash": posthoc["artifact_hash"],
        "source_contract_version": CONTRACT_VERSION,
        "cell_count": len(cells),
        "retrospectively_witness_eligible_count": sum(
            value["retrospectively_witness_eligible"]
            for value in cells
        ),
        "cells": cells,
        "provider_calls_added": 0,
        "private_truth_used_for_witness_derivation": False,
        "historical_decision_unchanged": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    audit = {
        **commitment, "artifact_hash": hash_payload(commitment)
    }
    write(output / "effect_witness_retrospective.json", audit)
    print(json.dumps({
        "cell_count": audit["cell_count"],
        "eligible": audit[
            "retrospectively_witness_eligible_count"
        ],
        "provider_calls_added": 0,
        "historical_decision_unchanged": True,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
