"""Build an anonymous Kimi K3 pack from GPT/Gemini disagreements."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.structure_reference_panel_disagreement import (  # noqa: E402
    build_adjudication_bundle, validate_adjudication_bundle,
)
from local_collective_cognition.structure_reference_panel_pack import (  # noqa: E402
    validate_reference_panel,
)


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load(path):
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/structure_reference_panel_v0_1"
    parser.add_argument("--gpt-pack", default=f"{base}/gpt_5_6_annotation_pack.json")
    parser.add_argument("--gemini-pack", default=f"{base}/gemini_3_1_annotation_pack.json")
    parser.add_argument("--private-panel-manifest", default=f"{base}/private_panel_manifest.json")
    parser.add_argument("--semantic-source", default="outputs/structure_semantic_judge_v0_1_retry2.json")
    parser.add_argument("--gpt-response", required=True)
    parser.add_argument("--gemini-response", required=True)
    parser.add_argument("--output-dir", default=base)
    args = parser.parse_args()
    packs = (_load(args.gpt_pack), _load(args.gemini_pack))
    panel_manifest = _load(args.private_panel_manifest)
    validate_reference_panel(
        packs=packs, manifest=panel_manifest, semantic_artifact=_load(args.semantic_source),
    )
    responses = (_load(args.gpt_response), _load(args.gemini_response))
    pack, manifest = build_adjudication_bundle(
        packs=packs, panel_manifest=panel_manifest, responses=responses,
    )
    validate_adjudication_bundle(
        pack=pack, manifest=manifest, panel_packs=packs,
        panel_manifest=panel_manifest, responses=responses,
    )
    output = _resolve(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "kimi_k3_adjudication_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True), encoding="utf-8",
    )
    (output / "private_adjudication_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8",
    )
    response_names = {
        "annotation-lane-a": "gpt_5_6_annotation_response.json",
        "annotation-lane-b": "gemini_3_1_annotation_response.json",
    }
    for response in responses:
        (output / response_names[response["lane_id"]]).write_text(
            json.dumps(response, indent=2, sort_keys=True), encoding="utf-8",
        )
    print(json.dumps({
        "state": manifest["reference_state"], "agreement_count": manifest["agreement_count"],
        "disagreement_count": manifest["disagreement_count"], "pack_hash": pack["pack_hash"],
        "output_dir": str(output), "validated_responses": list(response_names.values()),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
