"""Prepare blind GPT-5.6 and Gemini-3.1 annotation packs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.structure_elicitor_fresh_eval import (  # noqa: E402
    validate_calibration_artifact, validate_fresh_artifact,
)
from local_collective_cognition.structure_reference_panel_pack import (  # noqa: E402
    build_reference_panel, validate_reference_panel,
)
from local_collective_cognition.structure_semantic_judge_artifact import (  # noqa: E402
    validate_semantic_artifact,
)


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load(path):
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def _write(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration-source", default="outputs/structure_elicitor_calibration_v0_2.json")
    parser.add_argument("--fresh-source", default="outputs/structure_elicitor_fresh_holdout_v0_1.json")
    parser.add_argument("--semantic-source", default="outputs/structure_semantic_judge_v0_1_retry2.json")
    parser.add_argument("--output-dir", default="outputs/structure_reference_panel_v0_1")
    args = parser.parse_args()
    calibration, fresh, semantic = (
        _load(args.calibration_source), _load(args.fresh_source), _load(args.semantic_source),
    )
    validate_calibration_artifact(calibration)
    validate_fresh_artifact(fresh, calibration_artifact=calibration)
    validate_semantic_artifact(
        semantic, calibration_artifact=calibration, fresh_artifact=fresh,
    )
    packs, manifest = build_reference_panel(semantic_artifact=semantic)
    validate_reference_panel(
        packs=packs, manifest=manifest, semantic_artifact=semantic,
    )
    output = _resolve(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    names = {
        "annotation-lane-a": "gpt_5_6_annotation_pack.json",
        "annotation-lane-b": "gemini_3_1_annotation_pack.json",
    }
    for pack in packs:
        _write(output / names[pack["lane_id"]], pack)
    _write(output / "private_panel_manifest.json", manifest)
    print(json.dumps({
        "panel_id": manifest["panel_id"], "state": manifest["reference_state"],
        "candidate_count": manifest["candidate_count"], "criterion_count": manifest["criterion_count"],
        "output_dir": str(output), "pack_hashes": manifest["lane_pack_hashes"],
        "private_manifest_hash": manifest["manifest_hash"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
