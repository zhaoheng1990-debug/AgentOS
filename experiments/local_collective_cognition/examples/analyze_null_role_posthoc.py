"""Write v0.40 private-outcome null-role calibration audit."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.null_role_posthoc import (  # noqa: E402
    analyze_null_role_posthoc,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    output = REPO_ROOT / "outputs" / "null_role_v0_40"
    posthoc = analyze_null_role_posthoc(
        corpus=read(output / "null_role_corpus_frozen.json"),
        run=read(output / "null_role_run.json"),
        analysis=read(output / "null_role_analysis.json"),
    )
    write(output / "posthoc_null_role_calibration.json", posthoc)
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

