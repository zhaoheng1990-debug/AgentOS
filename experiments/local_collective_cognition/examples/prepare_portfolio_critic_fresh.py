"""Freeze and mechanically audit the v0.61 fresh holdout."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.portfolio_critic_fresh_holdout import (  # noqa: E402
    audit_portfolio_critic_fresh_holdout,
    audit_portfolio_critic_fresh_holdout_v0_61_1,
    build_portfolio_critic_fresh_holdout,
    build_portfolio_critic_fresh_holdout_v0_61_1,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def artifact(value):
    return {**value, "artifact_hash": hash_payload(value)}


def main():
    revision = os.environ.get("AGENTOS_PORTFOLIO_REVISION", "v0_61")
    if revision not in {"v0_61", "v0_61_1"}:
        raise ValueError("portfolio_revision_invalid")
    output = (
        REPO_ROOT / "outputs" / f"portfolio_critic_fresh_{revision}"
    )
    output.mkdir(parents=True, exist_ok=True)
    if revision == "v0_61_1":
        corpus = build_portfolio_critic_fresh_holdout_v0_61_1()
        audit = audit_portfolio_critic_fresh_holdout_v0_61_1(corpus)
    else:
        corpus = build_portfolio_critic_fresh_holdout()
        audit = audit_portfolio_critic_fresh_holdout(corpus)
    write(output / "fresh_corpus_frozen.json", corpus)
    write(output / "construction_audit.json", audit)
    ready = (
        audit["valid_cell_count"] == corpus["case_count"]
        and audit["topology_balance_valid"]
        and audit["target_position_coverage"] == 5
    )
    closure = artifact({
        "closure_version": "portfolio_critic_fresh_construction_v0_61",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_audit_hash": audit["artifact_hash"],
        "candidate_state": (
            "FRESH_PORTFOLIO_READY_FOR_REFERENCE_AUDIT"
            if ready else "FRESH_PORTFOLIO_CONSTRUCTION_REJECTED"
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
        "topology_counts": audit["topology_counts"],
        "target_position_coverage": audit["target_position_coverage"],
        "state": closure["candidate_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
