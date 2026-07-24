"""Freeze and mechanically audit the v0.59 transfer holdout."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.marginal_scarcity_transfer_holdout import (  # noqa: E402
    audit_marginal_scarcity_transfer,
    audit_marginal_scarcity_transfer_v0_59_1,
    build_marginal_scarcity_transfer_holdout,
    build_marginal_scarcity_transfer_holdout_v0_59_1,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def artifact(value):
    return {**value, "artifact_hash": hash_payload(value)}


def main():
    revision = os.environ.get("AGENTOS_TRANSFER_REVISION", "v0_59")
    if revision not in {"v0_59", "v0_59_1"}:
        raise ValueError("transfer_revision_invalid")
    output = (
        REPO_ROOT / "outputs" / f"marginal_scarcity_transfer_{revision}"
    )
    output.mkdir(parents=True, exist_ok=True)
    if revision == "v0_59_1":
        corpus = build_marginal_scarcity_transfer_holdout_v0_59_1()
        audit = audit_marginal_scarcity_transfer_v0_59_1(corpus)
    else:
        corpus = build_marginal_scarcity_transfer_holdout()
        audit = audit_marginal_scarcity_transfer(corpus)
    write(output / "transfer_corpus_frozen.json", corpus)
    write(output / "construction_audit.json", audit)
    closure = artifact({
        "closure_version": "marginal_scarcity_transfer_construction_v0_59",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_audit_hash": audit["artifact_hash"],
        "candidate_state": (
            "TRANSFER_READY_FOR_REFERENCE_AUDIT"
            if (
                audit["valid_cell_count"] == corpus["case_count"]
                and audit["target_position_coverage"] == 5
                and audit["drop_pool_balance_valid"]
            )
            else "TRANSFER_CONSTRUCTION_REJECTED"
        ),
        "formal_experiment_authorized": False,
        "provider_calls_used": 0,
        "promotion_allowed": False,
    })
    write(output / "construction_closure.json", closure)
    print(json.dumps({
        "revision": revision,
        "corpus_hash": corpus["artifact_hash"],
        "valid_cells": audit["valid_cell_count"],
        "target_position_coverage": audit["target_position_coverage"],
        "drop_pool_counts": audit["drop_pool_counts"],
        "state": closure["candidate_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
