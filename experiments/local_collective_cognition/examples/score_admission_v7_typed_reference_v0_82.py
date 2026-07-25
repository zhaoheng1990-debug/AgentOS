"""Score all v0.82 arms against the frozen typed reference."""

import json
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.admission_v7_typed_scoring import (  # noqa: E402
    score_staged_context_reference,
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    source = ROOT / "outputs" / "admission_v7_fresh_holdout_v0_82"
    external = ROOT / "outputs" / "admission_v7_external_panel_v0_82"
    score = score_staged_context_reference(
        reference=read(
            external / "typed_admission_reference_candidate_v0_82.json"
        ),
        baseline_run=read(source / "baseline_run.json"),
        atomic_run=read(source / "atomic_run.json"),
        candidate_run=read(source / "candidate_run.json"),
    )
    path = external / "typed_reference_score_v0_82.json"
    path.write_text(
        json.dumps(score, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps({
        "baseline": _summary(score["baseline"]),
        "atomic": _summary(score["atomic"]),
        "candidate": _summary(score["candidate"]),
        "corrected_span_count": len(
            score["atomic_to_candidate_corrected_spans"]
        ),
        "harmed_span_count": len(
            score["atomic_to_candidate_harmed_spans"]
        ),
        "accuracy_delta_vs_atomic": score["accuracy_delta_vs_atomic"],
        "macro_f1_delta_vs_atomic": score["macro_f1_delta_vs_atomic"],
        "conditions": score["preregistered_semantic_conditions"],
        "experimental_decision": score["experimental_decision"],
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
