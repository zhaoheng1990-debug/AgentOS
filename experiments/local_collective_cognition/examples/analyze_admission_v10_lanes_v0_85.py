"""Validate v0.85 lanes and freeze the paired mutation result."""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.admission_v10_lane_analysis import (  # noqa: E402
    build_lane_analysis,
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpt-response", required=True)
    parser.add_argument("--gemini-response", required=True)
    args = parser.parse_args()
    source = ROOT / "outputs" / "admission_v10_development_v0_85"
    output = ROOT / "outputs" / "admission_v10_external_panel_v0_85"
    packs = (
        read(output / "gpt_5_6_study_relation_pack_v0_85.json"),
        read(output / "gemini_3_1_study_relation_pack_v0_85.json"),
    )
    responses = (
        read(Path(args.gpt_response)),
        read(Path(args.gemini_response)),
    )
    analysis = build_lane_analysis(
        packs=packs,
        panel_manifest=read(output / "panel_manifest_private.json"),
        responses=responses,
        evaluation=read(source / "development_evaluation.json"),
    )
    write(output / "lane_analysis.json", analysis)
    raw = output / "raw_received"
    raw.mkdir(exist_ok=True)
    shutil.copyfile(
        args.gpt_response,
        raw / "ANNOTATION_LANE_A_GPT5_6_response.json",
    )
    shutil.copyfile(
        args.gemini_response,
        raw / "ANNOTATION_LANE_B_Gemini3_1_response.json",
    )
    inventory_path = output / "hash_inventory.json"
    inventory = read(inventory_path)
    analysis_path = output / "lane_analysis.json"
    inventory[analysis_path.name] = {
        "sha256": hashlib.sha256(analysis_path.read_bytes()).hexdigest(),
        "size": analysis_path.stat().st_size,
    }
    write(inventory_path, dict(sorted(inventory.items())))
    print(json.dumps({
        "agreement_count": analysis["agreement_count"],
        "disagreement_count": analysis["disagreement_count"],
        "mutation_outcome_counts": analysis["mutation_outcome_counts"],
        "mechanism_decision": analysis["mechanism_decision"],
        "control_adjudication_required": (
            analysis[
                "control_adjudication_required_for_mechanism_decision"
            ]
        ),
        "artifact_hash": analysis["artifact_hash"],
    }, indent=2))


if __name__ == "__main__":
    main()
