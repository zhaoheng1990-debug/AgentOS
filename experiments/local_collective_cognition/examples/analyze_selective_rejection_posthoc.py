"""Write the v0.52 private-outcome audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.selective_rejection_posthoc import (  # noqa: E402
    analyze_selective_rejection_posthoc,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    output = REPO_ROOT / "outputs" / "selective_rejection_v0_52"
    posthoc = analyze_selective_rejection_posthoc(
        corpus=read(output / "selective_rejection_corpus_frozen.json"),
        run=read(output / "selective_rejection_run.json"),
        analysis=read(output / "selective_rejection_analysis.json"),
    )
    write(output / "posthoc_selective_rejection.json", posthoc)
    print(json.dumps({
        "classifications": posthoc["classification_distribution"],
        "gated": posthoc["gated_gross_uplift"],
        "oracle": posthoc["pool_oracle_gross_uplift"],
        "capture": posthoc[
            "mean_fraction_of_positive_oracle_uplift_captured"
        ],
        "coordinated_recovery_count": posthoc[
            "coordinated_recovery_count"
        ],
        "coordinated_recovery_beneficial": posthoc[
            "coordinated_recovery_beneficial_count"
        ],
        "coordinated_recovery_harmful": posthoc[
            "coordinated_recovery_harmful_count"
        ],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
