"""Write v0.47 private-outcome lineage-displacement audit."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.lineage_displacement_posthoc import (  # noqa: E402
    analyze_lineage_displacement_posthoc,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    output = REPO_ROOT / "outputs" / "lineage_displacement_v0_47"
    posthoc = analyze_lineage_displacement_posthoc(
        corpus=read(output / "lineage_displacement_corpus_frozen.json"),
        run=read(output / "lineage_displacement_run.json"),
        analysis=read(output / "lineage_displacement_analysis.json"),
    )
    write(output / "posthoc_lineage_displacement.json", posthoc)
    print(json.dumps({
        "proposed": posthoc["proposed_gross_uplift"],
        "gated": posthoc["gated_gross_uplift"],
        "pool_oracle": posthoc["pool_oracle_gross_uplift"],
        "regret": posthoc["gate_regret"],
        "classifications": posthoc["classification_distribution"],
        "positive_oracle_cell_count": posthoc[
            "positive_oracle_cell_count"
        ],
        "mean_positive_oracle_fraction_captured": posthoc[
            "mean_fraction_of_positive_oracle_uplift_captured"
        ],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())


