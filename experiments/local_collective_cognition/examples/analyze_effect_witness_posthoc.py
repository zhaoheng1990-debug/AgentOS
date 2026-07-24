"""Write v0.56 private-outcome decomposition."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.effect_witness_posthoc import (  # noqa: E402
    analyze_effect_witness_posthoc,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    output = REPO_ROOT / "outputs" / "effect_witness_v0_56"
    posthoc = analyze_effect_witness_posthoc(
        corpus=read(output / "effect_witness_corpus_frozen.json"),
        run=read(output / "effect_witness_run.json"),
        analysis=read(output / "effect_witness_analysis.json"),
    )
    write(output / "posthoc_effect_witness.json", posthoc)
    print(json.dumps({
        "classifications": posthoc["classification_distribution"],
        "effect_outcomes": posthoc["effect_outcome_distribution"],
        "effect_block_reasons": posthoc[
            "effect_block_reason_distribution"
        ],
        "witnessed_beneficial_effect_rejected": posthoc[
            "witnessed_beneficial_effect_rejected_count"
        ],
        "protected_beneficial_effect_rejected": posthoc[
            "protected_beneficial_effect_rejected_count"
        ],
        "oracle_capture": posthoc[
            "mean_fraction_of_positive_oracle_uplift_captured"
        ],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
