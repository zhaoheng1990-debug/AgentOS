"""Ingest an identity-aware K3 record as shadow evidence only."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import shutil
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.structure_reference_panel_shadow import (  # noqa: E402
    build_shadow_reference,
)


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load(path):
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/structure_reference_panel_v0_1"
    parser.add_argument("--record", required=True)
    parser.add_argument("--output-dir", default=base)
    args = parser.parse_args()
    record_path = _resolve(args.record)
    output = _resolve(args.output_dir)
    packs = (_load(f"{base}/gpt_5_6_annotation_pack.json"), _load(f"{base}/gemini_3_1_annotation_pack.json"))
    responses = (
        _load(f"{base}/gpt_5_6_annotation_response.json"),
        _load(f"{base}/gemini_3_1_annotation_response.json"),
    )
    artifact = build_shadow_reference(
        record=_load(record_path), source_file_sha256=sha256(record_path.read_bytes()).hexdigest(),
        adjudication_pack=_load(f"{base}/kimi_k3_adjudication_pack.json"),
        adjudication_manifest=_load(f"{base}/private_adjudication_manifest.json"),
        panel_packs=packs, panel_manifest=_load(f"{base}/private_panel_manifest.json"),
        annotation_responses=responses,
    )
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(record_path, output / "external_identity_aware_adjudication_record.json")
    target = output / "identity_aware_shadow_reference_candidate.json"
    target.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "candidate_state": artifact["candidate_state"], "semantic_content_consistent": True,
        "protocol_compliant": False, "declared_hash_verified": artifact["source_declared_hash_verified"],
        "label_count": artifact["label_count"], "artifact_hash": artifact["artifact_hash"],
        "output": str(target),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
