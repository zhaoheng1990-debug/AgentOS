"""Freeze the all-new v0.64 selection-retention holdout."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.selection_retention_fresh_contracts import (  # noqa: E402
    build_fresh_preregistration,
    validate_hash_bound,
)
from local_collective_cognition.selection_retention_fresh_holdout import (  # noqa: E402
    audit_selection_retention_fresh_holdout,
    build_selection_retention_fresh_holdout,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def artifact(value: dict) -> dict:
    return {**value, "artifact_hash": hash_payload(value)}


def main() -> int:
    source = REPO_ROOT / "outputs" / "typed_evidence_binding_v0_63"
    output = REPO_ROOT / "outputs" / "selection_retention_fresh_v0_64"
    output.mkdir(parents=True, exist_ok=True)

    source_closure = read(source / "closure.json")
    validate_hash_bound(source_closure)
    corpus = build_selection_retention_fresh_holdout()
    audit = audit_selection_retention_fresh_holdout(corpus)
    preregistration = build_fresh_preregistration(
        corpus=corpus,
        construction_audit=audit,
        source_closure=source_closure,
    )
    rollback = artifact({
        "rollback_version": "selection_retention_fresh_rollback_v0_64",
        "rollback_target_commit": "3daa69a",
        "rollback_scope": "V0_64_EXPERIMENT_AND_CONDITIONAL_ALPHA_22",
        "source_v0_63_closure_hash": source_closure["artifact_hash"],
        "frozen_corpus_hash": corpus["artifact_hash"],
        "frozen_preregistration_hash": preregistration["artifact_hash"],
        "production_state_unchanged": True,
        "retention_state_unchanged": True,
        "baseline_state_unchanged": True,
    })

    write(output / "fresh_corpus_frozen.json", corpus)
    write(output / "construction_audit.json", audit)
    write(output / "preregistration.json", preregistration)
    write(output / "rollback_pointer.json", rollback)
    print(json.dumps({
        "case_count": corpus["case_count"],
        "relation_count": corpus["relation_count"],
        "corpus_hash": corpus["artifact_hash"],
        "construction_audit_hash": audit["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "maximum_provider_tasks": preregistration[
            "maximum_provider_tasks"
        ],
        "hard_token_ceiling": preregistration["hard_token_ceiling"],
        "formal_execution_authorized": audit[
            "formal_execution_authorized"
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
