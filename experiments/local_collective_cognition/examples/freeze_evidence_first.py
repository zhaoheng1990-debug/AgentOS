"""Freeze v0.54 preregistration after reference audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.evidence_first_experiment import (  # noqa: E402
    build_evidence_first_preregistration,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    output = REPO_ROOT / "outputs" / "evidence_first_v0_54"
    values = {
        key: read(output / name)
        for key, name in (
            ("corpus", "evidence_first_corpus_frozen.json"),
            ("audit", "reference_completeness_audit.json"),
            (
                "calibration",
                "source_unlabeled_qualification_calibration.json",
            ),
            ("prior_prereg", "source_v0_53_preregistration.json"),
            ("prior_analysis", "source_v0_53_analysis.json"),
            ("prior_closure", "source_v0_53_closure.json"),
            ("prior_posthoc", "source_v0_53_posthoc.json"),
        )
    }
    prereg = build_evidence_first_preregistration(
        corpus=values["corpus"],
        reference_audit=values["audit"],
        calibration=values["calibration"],
        prior_preregistration=values["prior_prereg"],
        prior_analysis=values["prior_analysis"],
        prior_closure=values["prior_closure"],
        prior_posthoc=values["prior_posthoc"],
    )
    write(output / "evidence_first_preregistration.json", prereg)
    print(json.dumps({
        "preregistration_hash": prereg["artifact_hash"],
        "minimum_blind_consensus": prereg["success_gate"][
            "minimum_blind_consensus_activation_count"
        ],
        "soft_tokens": prereg["success_gate"][
            "maximum_physical_total_tokens"
        ],
        "hard_tokens": prereg["success_gate"][
            "hard_runaway_total_tokens"
        ],
        "formal_run_authorized": True,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
