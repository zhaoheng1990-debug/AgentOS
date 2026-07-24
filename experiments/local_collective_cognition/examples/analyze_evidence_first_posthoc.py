"""Write v0.54 private-outcome audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.evidence_first_posthoc import (  # noqa: E402
    analyze_evidence_first_posthoc,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    output = REPO_ROOT / "outputs" / "evidence_first_v0_54"
    posthoc = analyze_evidence_first_posthoc(
        corpus=read(output / "evidence_first_corpus_frozen.json"),
        run=read(output / "evidence_first_run.json"),
        analysis=read(output / "evidence_first_analysis.json"),
    )
    write(output / "posthoc_evidence_first.json", posthoc)
    print(json.dumps({
        "classifications": posthoc["classification_distribution"],
        "gated": posthoc["gated_gross_uplift"],
        "oracle": posthoc["pool_oracle_gross_uplift"],
        "capture": posthoc[
            "mean_fraction_of_positive_oracle_uplift_captured"
        ],
        "blind_recovery_distribution": posthoc[
            "blind_consensus_recovery_distribution"
        ],
        "blind_recovery_precision": posthoc[
            "blind_consensus_recovery_precision"
        ],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
