"""Score all v0.84 arms against the frozen typed reference."""

import json
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.admission_v9_typed_scoring import (  # noqa: E402
    score_ternary_boundary_reference,
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    source = ROOT / "outputs" / "admission_v9_fresh_holdout_v0_84"
    external = ROOT / "outputs" / "admission_v9_external_panel_v0_84"
    score = score_ternary_boundary_reference(
        reference=read(
            external / "typed_admission_reference_candidate_v0_84.json"
        ),
        baseline_run=read(source / "baseline_run.json"),
        atomic_run=read(source / "atomic_run.json"),
        staged_run=read(source / "staged_run.json"),
        candidate_run=read(source / "candidate_run.json"),
    )
    path = external / "typed_reference_score_v0_84.json"
    path.write_text(
        json.dumps(score, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps({
        "baseline": _summary(score["baseline"]),
        "atomic": _summary(score["atomic"]),
        "staged": _summary(score["staged"]),
        "candidate": _summary(score["candidate"]),
        "atomic_to_staged": _change_summary(
            score["atomic_to_staged"]
        ),
        "staged_to_candidate": _change_summary(
            score["staged_to_candidate"]
        ),
        "candidate_accuracy_delta_vs_staged": (
            score["candidate_accuracy_delta_vs_staged"]
        ),
        "candidate_macro_f1_delta_vs_staged": (
            score["candidate_macro_f1_delta_vs_staged"]
        ),
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
        "reference_distribution": value["reference_distribution"],
    }


def _change_summary(value):
    return {
        "corrected_count": value["corrected_count"],
        "harmed_count": value["harmed_count"],
    }


if __name__ == "__main__":
    main()
