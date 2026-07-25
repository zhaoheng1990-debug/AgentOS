"""Build the paired v0.84 lane-agreement result."""

import json
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.admission_v9_lane_analysis import (  # noqa: E402
    build_lane_agreement_analysis,
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    source = ROOT / "outputs" / "admission_v9_fresh_holdout_v0_84"
    output = ROOT / "outputs" / "admission_v9_external_panel_v0_84"
    analysis = build_lane_agreement_analysis(
        packs=(
            read(
                output
                / "gpt_5_6_ternary_boundary_admission_pack_v0_84.json"
            ),
            read(
                output
                / "gemini_3_1_ternary_boundary_admission_pack_v0_84.json"
            ),
        ),
        panel_manifest=read(output / "panel_manifest_private.json"),
        responses=(
            read(
                output
                / "raw_received/ANNOTATION_LANE_A_GPT5_6_response.json"
            ),
            read(
                output
                / "raw_received/ANNOTATION_LANE_B_Gemini3_1_response.json"
            ),
        ),
        adjudication_pack=read(
            output / "kimi_k3_ternary_boundary_pack_v0_84.json"
        ),
        adjudication_manifest=read(
            output / "adjudication_manifest_private.json"
        ),
        evaluation=read(source / "pre_reference_evaluation.json"),
    )
    path = output / "lane_agreement_analysis.json"
    path.write_text(
        json.dumps(analysis, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps({
        "agreement_count": analysis["agreement_count"],
        "disagreement_count": analysis["disagreement_count"],
        "semantic_agreement_rate": analysis["semantic_agreement_rate"],
        "mutation_outcome_counts": analysis["mutation_outcome_counts"],
        "mutation_semantic_decision": (
            analysis["mutation_semantic_decision"]
        ),
        "full_reference_state": analysis["full_reference_state"],
        "artifact_hash": analysis["artifact_hash"],
    }, indent=2))


if __name__ == "__main__":
    main()
