"""Freeze the v0.59 transfer discovery and replacement gates."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.marginal_scarcity_transfer import (  # noqa: E402
    build_transfer_preregistration,
)
from local_collective_cognition.marginal_scarcity_transfer_holdout import (  # noqa: E402
    validate_marginal_scarcity_transfer_holdout,
    validate_marginal_scarcity_transfer_holdout_v0_59_1,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    revision = os.environ.get("AGENTOS_TRANSFER_REVISION", "v0_59")
    if revision not in {"v0_59", "v0_59_1"}:
        raise ValueError("transfer_revision_invalid")
    output = (
        REPO_ROOT / "outputs" / f"marginal_scarcity_transfer_{revision}"
    )
    source = (
        REPO_ROOT / "outputs" / "marginal_scarcity_replacement_v0_58"
    )
    preregistration = build_transfer_preregistration(
        corpus=read(output / "transfer_corpus_frozen.json"),
        reference_audit=read(
            output / "reference_completeness_audit.json"
        ),
        source_replacement_closure=read(source / "closure.json"),
        corpus_validator=(
            validate_marginal_scarcity_transfer_holdout_v0_59_1
            if revision == "v0_59_1"
            else validate_marginal_scarcity_transfer_holdout
        ),
        runtime_version=f"marginal_scarcity_transfer_{revision}",
    )
    (output / "transfer_preregistration.json").write_text(
        json.dumps(preregistration, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps({
        "revision": revision,
        "preregistration_hash": preregistration["artifact_hash"],
        "required_receipts": preregistration["required_receipt_count"],
        "minimum_exact_target": preregistration[
            "minimum_exact_target_consensus_count"
        ],
        "target_position_coverage": preregistration[
            "minimum_target_source_position_coverage"
        ],
        "drop_pool_coverage": preregistration[
            "minimum_drop_pool_coverage"
        ],
        "promotion_allowed": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
