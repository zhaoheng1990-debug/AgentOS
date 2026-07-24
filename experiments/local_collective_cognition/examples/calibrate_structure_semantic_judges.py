"""Build the candidate-only semantic-judge policy from the finalized model panel."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.structure_reference_judge_calibration import (  # noqa: E402
    build_reference_judge_calibration, validate_reference_judge_calibration,
)


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load(path):
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/structure_reference_panel_v0_1"
    parser.add_argument("--reference", default=f"{base}/model_panel_reference_candidate.json")
    parser.add_argument("--panel-manifest", default=f"{base}/private_panel_manifest.json")
    parser.add_argument("--semantic-source", default="outputs/structure_semantic_judge_v0_1_retry2.json")
    parser.add_argument("--output", default="outputs/structure_reference_judge_calibration_v0_1.json")
    args = parser.parse_args()
    reference, manifest, semantic = _load(args.reference), _load(args.panel_manifest), _load(args.semantic_source)
    artifact = build_reference_judge_calibration(
        reference_artifact=reference, panel_manifest=manifest, semantic_artifact=semantic,
    )
    validate_reference_judge_calibration(
        artifact, reference_artifact=reference, panel_manifest=manifest, semantic_artifact=semantic,
    )
    output = _resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "candidate_state": artifact["candidate_state"],
        "policy_candidate": artifact["policy_candidate"],
        "artifact_hash": artifact["artifact_hash"], "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
