"""Freeze and audit the v0.57 construction-only holdout."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.marginal_scarcity_holdout import (  # noqa: E402
    audit_marginal_scarcity_construction,
    build_marginal_scarcity_holdout,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def artifact(value):
    return {**value, "artifact_hash": hash_payload(value)}


def main():
    output = REPO_ROOT / "outputs" / "marginal_scarcity_v0_57"
    output.mkdir(parents=True, exist_ok=True)
    corpus = build_marginal_scarcity_holdout()
    audit = audit_marginal_scarcity_construction(corpus)
    write(output / "marginal_scarcity_corpus_frozen.json", corpus)
    write(output / "construction_audit.json", audit)
    closure = artifact({
        "closure_version": "marginal_scarcity_construction_v0_57",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_audit_hash": audit["artifact_hash"],
        "candidate_state": (
            "MARGINAL_SCARCITY_READY_FOR_REFERENCE_AUDIT"
            if audit["valid_cell_count"] == corpus["case_count"]
            else "MARGINAL_SCARCITY_CONSTRUCTION_REJECTED"
        ),
        "formal_experiment_authorized": False,
        "provider_calls_used": 0,
        "promotion_allowed": False,
    })
    write(output / "closure.json", closure)
    files = [
        "marginal_scarcity_corpus_frozen.json",
        "construction_audit.json",
        "closure.json",
    ]
    inventory = artifact({
        "inventory_version": "marginal_scarcity_inventory_v0_57",
        "files": [{
            "path": name,
            "bytes": (output / name).stat().st_size,
            "sha256": hashlib.sha256(
                (output / name).read_bytes()
            ).hexdigest(),
        } for name in files],
    })
    write(output / "hash_inventory.json", inventory)
    print(json.dumps({
        "corpus_hash": corpus["artifact_hash"],
        "valid_cells": audit["valid_cell_count"],
        "minimum_uplift": audit[
            "minimum_designed_gross_cbit_uplift"
        ],
        "state": closure["candidate_state"],
        "formal_experiment_authorized": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
