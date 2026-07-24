"""Write v0.42 private-outcome compact-delta audit."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.compact_delta_posthoc import (  # noqa: E402
    analyze_compact_delta_posthoc,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    output = REPO_ROOT / "outputs" / "compact_delta_v0_42"
    posthoc = analyze_compact_delta_posthoc(
        corpus=read(output / "compact_delta_corpus_frozen.json"),
        run=read(output / "compact_delta_run.json"),
        analysis=read(output / "compact_delta_analysis.json"),
    )
    write(output / "posthoc_compact_delta_calibration.json", posthoc)
    print(json.dumps({
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
        "raw_trigger_count": posthoc["raw_trigger_count"],
        "qualified_count": posthoc["qualified_count"],
        "valid_delta_composition_count": posthoc[
            "valid_delta_composition_count"
        ],
        "invalid_delta_contract_count": posthoc[
            "invalid_delta_contract_count"
        ],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())

