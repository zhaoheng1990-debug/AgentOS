"""Freeze v0.61 target-only and selective-action gates."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.portfolio_critic_fresh_runtime import (  # noqa: E402
    build_fresh_preregistration,
)
from local_collective_cognition.portfolio_critic_fresh_holdout import (  # noqa: E402
    validate_portfolio_critic_fresh_holdout,
    validate_portfolio_critic_fresh_holdout_v0_61_1,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    revision = os.environ.get("AGENTOS_PORTFOLIO_REVISION", "v0_61")
    if revision not in {"v0_61", "v0_61_1"}:
        raise ValueError("portfolio_revision_invalid")
    validator = (
        validate_portfolio_critic_fresh_holdout_v0_61_1
        if revision == "v0_61_1"
        else validate_portfolio_critic_fresh_holdout
    )
    runtime_version = f"portfolio_critic_fresh_runtime_{revision}"
    output = (
        REPO_ROOT / "outputs" / f"portfolio_critic_fresh_{revision}"
    )
    source = (
        REPO_ROOT / "outputs" / "portfolio_critic_calibration_v0_60"
    )
    preregistration = build_fresh_preregistration(
        corpus=read(output / "fresh_corpus_frozen.json"),
        reference_audit=read(
            output / "reference_completeness_audit.json"
        ),
        source_calibration_closure=read(source / "closure.json"),
        corpus_validator=validator,
        runtime_version=runtime_version,
    )
    (output / "preregistration.json").write_text(
        json.dumps(preregistration, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps({
        "revision": revision,
        "preregistration_hash": preregistration["artifact_hash"],
        "required_target_receipts": preregistration[
            "required_target_receipt_count"
        ],
        "minimum_target_consensus": preregistration[
            "minimum_target_consensus_count"
        ],
        "topology_case_coverage": {
            "unique": preregistration[
                "required_unique_topology_case_coverage"
            ],
            "none": preregistration[
                "required_no_eligible_topology_case_coverage"
            ],
            "multiple": preregistration[
                "required_ambiguous_topology_case_coverage"
            ],
        },
        "promotion_allowed": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
