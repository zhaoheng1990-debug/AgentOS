"""Score v0.76 and v0.80 against the frozen typed reference."""

import json
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.admission_v5_typed_scoring import (  # noqa: E402
    score_typed_reference,
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    source = ROOT / "outputs" / "admission_v5_fresh_holdout_v0_80"
    external = ROOT / "outputs" / "admission_v5_external_panel_v0_80"
    score = score_typed_reference(
        reference=read(
            external / "typed_admission_reference_candidate_v0_80.json"
        ),
        baseline_run=read(source / "baseline_run.json"),
        candidate_run=read(source / "candidate_run.json"),
    )
    path = external / "typed_reference_score_v0_80.json"
    path.write_text(
        json.dumps(score, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps({
        "baseline": _summary(score["baseline"]),
        "candidate": _summary(score["candidate"]),
        "corrected_span_count": len(score["corrected_spans"]),
        "harmed_span_count": len(score["harmed_spans"]),
        "accuracy_delta": score["accuracy_delta"],
        "macro_f1_delta": score["macro_f1_delta"],
        "semantic_result": score["semantic_result"],
        "automatic_promotion_decision": (
            score["automatic_promotion_decision"]
        ),
        "output": str(path),
    }, indent=2))


def _summary(value):
    return {
        "accuracy": value["accuracy"],
        "macro_f1": value["macro_f1"],
        "per_class_f1": {
            name: metrics["f1"]
            for name, metrics in value["per_class"].items()
        },
        "predicted_distribution": value["predicted_distribution"],
    }


if __name__ == "__main__":
    main()
