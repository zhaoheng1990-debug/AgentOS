"""Freeze the v0.57 target-blind discovery preregistration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.marginal_scarcity_experiment import build_discovery_preregistration  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    output = REPO_ROOT / "outputs" / "marginal_scarcity_v0_57"
    prereg = build_discovery_preregistration(
        corpus=read(output / "marginal_scarcity_corpus_frozen.json"),
        reference_audit=read(output / "reference_completeness_audit.json"),
    )
    (output / "discovery_preregistration.json").write_text(
        json.dumps(prereg, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({
        "preregistration_hash": prereg["artifact_hash"],
        "required_receipts": prereg["required_receipt_count"],
        "minimum_consensus": prereg["minimum_consensus_count"],
        "minimum_exact_target": prereg[
            "minimum_exact_target_consensus_count"
        ],
        "formal_replacement_authorized": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
