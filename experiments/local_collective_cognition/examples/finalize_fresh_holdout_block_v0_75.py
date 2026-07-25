"""Finalize the v0.75 admission block without reading private gold."""

import json
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.fresh_holdout_block import (  # noqa: E402
    finalize_admission_block,
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    output = ROOT / "outputs" / "fresh_holdout_v0_75"
    candidate_path = output / "candidate_run.json"
    if candidate_path.exists():
        raise ValueError("fresh_holdout_candidate_run_already_exists")
    decision = finalize_admission_block(
        preregistration=read(output / "holdout_preregistration.json"),
        baseline_run=read(output / "baseline_run.json"),
    )
    (output / "holdout_block_decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
