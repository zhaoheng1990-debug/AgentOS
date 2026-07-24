"""Write v0.39 private-outcome truth-value calibration audit."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.truth_value_posthoc import (  # noqa: E402
    analyze_truth_value_posthoc,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    output = REPO_ROOT / "outputs" / "truth_value_v0_39"
    posthoc = analyze_truth_value_posthoc(
        corpus=read(output / "truth_value_corpus_frozen.json"),
        run=read(output / "truth_value_run.json"),
        analysis=read(output / "truth_value_analysis.json"),
    )
    write(output / "posthoc_truth_value_calibration.json", posthoc)
    print(json.dumps({
        "counterproposal": posthoc["counterproposal_gross_uplift"],
        "selected": posthoc["selected_gross_uplift"],
        "pool_oracle": posthoc["pool_oracle_gross_uplift"],
        "regret": posthoc["composition_regret"],
        "positive_oracle_cell_count": posthoc[
            "positive_oracle_cell_count"
        ],
        "mean_positive_oracle_fraction_captured": posthoc[
            "mean_fraction_of_positive_oracle_uplift_captured"
        ],
        "selected_outcomes": posthoc[
            "selected_source_outcome_distribution"
        ],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())

