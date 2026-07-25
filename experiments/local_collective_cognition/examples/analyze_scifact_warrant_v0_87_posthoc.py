"""Generate the non-gating official-metric audit for frozen v0.87."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.factorized_benchmarks.scifact_v0_87_posthoc import (  # noqa: E402
    build_official_sentence_audit,
)


def main() -> None:
    output = ROOT / "outputs" / "scifact_warrant_v0_87"
    audit = build_official_sentence_audit(
        panel=_read(output / "holdout_private.json"),
        run=_read(output / "warrant_run.json"),
        evaluation=_read(output / "evaluation.json"),
    )
    path = output / "posthoc_official_sentence_audit.json"
    path.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        key: audit[key] for key in (
            "correct_sentence_count",
            "predicted_sentence_count",
            "gold_sentence_count",
            "sentence_precision",
            "sentence_recall",
            "sentence_f1",
            "overselected_sentence_count",
            "unrecovered_gold_sentence_count",
            "descriptive_posthoc_only",
            "preregistered_gate_changed",
            "gate_authority",
        )
    }, indent=2))


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
