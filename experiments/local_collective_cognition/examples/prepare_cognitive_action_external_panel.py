"""Generate independent GPT-5.6 and Gemini-3.1 annotation packs for v0.16."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_external_panel import build_external_panel, validate_external_panel  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default=str(REPO_ROOT / "outputs" / "cognitive_action_overnight_v0_16"))
    args = parser.parse_args()
    source = Path(args.source_dir)
    output = source / "external_panel"
    output.mkdir(parents=True, exist_ok=True)
    corpus = read(source / "fresh_action_corpus_frozen.json")
    role_run = read(source / "fresh_action_role_run.json")
    coordinator_run = read(source / "blind_coordinator_arms_run.json")
    packs, manifest = build_external_panel(corpus=corpus, role_run=role_run, coordinator_run=coordinator_run)
    validate_external_panel(packs=packs, manifest=manifest, corpus=corpus, role_run=role_run, coordinator_run=coordinator_run)
    names = {
        "annotation-lane-a": "gpt_5_6_cognitive_action_fresh_pack.json",
        "annotation-lane-b": "gemini_3_1_cognitive_action_fresh_pack.json",
    }
    generated = []
    for pack in packs:
        path = output / names[pack["lane_id"]]
        write(path, pack)
        zip_path = path.with_suffix(".zip")
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
            archive.write(path, arcname=path.name)
        generated.extend((path, zip_path))
    write(output / "private_external_panel_manifest.json", manifest)
    readme = (
        "# Cognitive Action External Panel v0.16\n\n"
        "Upload `gpt_5_6_cognitive_action_fresh_pack.zip` only to GPT-5.6 and "
        "`gemini_3_1_cognitive_action_fresh_pack.zip` only to Gemini 3.1. Ask each model to follow the embedded "
        "response contract and return one JSON object. Do not provide either model with local-role, DeepSeek baseline, "
        "coordinator, peer-annotation, or construction context. Return both JSON responses to AgentOS; a whole-object "
        "Kimi K3 adjudication pack will then be generated only for disagreements.\n"
    )
    (output / "README.md").write_text(readme, encoding="utf-8")
    generated.extend((output / "private_external_panel_manifest.json", output / "README.md"))
    inventory_commitment = {
        "inventory_version": "cognitive_action_external_panel_inventory_v0_16",
        "items": [{"path": path.name, "size_bytes": path.stat().st_size, "sha256": file_hash(path)} for path in generated],
    }
    inventory = {**inventory_commitment, "artifact_hash": hash_payload(inventory_commitment)}
    write(output / "hash_inventory.json", inventory)
    combined = source / "cognitive_action_external_panel_v0_16_return_pack.zip"
    with ZipFile(combined, "w", compression=ZIP_DEFLATED) as archive:
        for path in (*generated, output / "hash_inventory.json"):
            archive.write(path, arcname=f"external_panel/{path.name}")
    print(json.dumps({
        "panel_id": manifest["panel_id"],
        "manifest_hash": manifest["manifest_hash"],
        "gpt_pack_hash": next(pack["pack_hash"] for pack in packs if pack["lane_id"] == "annotation-lane-a"),
        "gemini_pack_hash": next(pack["pack_hash"] for pack in packs if pack["lane_id"] == "annotation-lane-b"),
        "case_count": manifest["candidate_count"],
        "current_phase": manifest["current_phase"],
        "return_pack": str(combined),
        "return_pack_sha256": file_hash(combined),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

