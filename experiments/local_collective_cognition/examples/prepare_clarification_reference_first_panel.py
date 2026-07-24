"""Freeze the v0.15 unlabeled corpus and coherent GPT/Gemini panel packs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_reference_first_holdout import (  # noqa: E402
    build_reference_first_holdout,
    validate_reference_first_holdout,
)
from local_collective_cognition.clarification_reference_first_panel import (  # noqa: E402
    build_reference_first_panel,
    validate_reference_first_panel,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/clarification_reference_first_v0_15")
    args = parser.parse_args()
    output = resolve(args.output_dir)
    corpus = build_reference_first_holdout()
    validate_reference_first_holdout(corpus)
    packs, manifest = build_reference_first_panel(corpus_artifact=corpus)
    validate_reference_first_panel(packs=packs, manifest=manifest, corpus_artifact=corpus)
    output.mkdir(parents=True, exist_ok=True)
    write(output / "private_reference_first_corpus.json", corpus)
    write(output / "private_reference_first_panel_manifest.json", manifest)
    names = {
        "annotation-lane-a": "gpt_5_6_reference_first_pack.json",
        "annotation-lane-b": "gemini_3_1_reference_first_pack.json",
    }
    for pack in packs:
        path = output / names[pack["lane_id"]]
        write(path, pack)
        with ZipFile(path.with_suffix(".zip"), "w", compression=ZIP_DEFLATED) as archive:
            archive.write(path, arcname=path.name)
    protocol_commitment = {
        "protocol_version": "clarification_reference_first_protocol_v0_15",
        "source_corpus_hash": corpus["artifact_hash"],
        "panel_manifest_hash": manifest["manifest_hash"],
        "phase_order": [
            "FREEZE_UNLABELED_CORPUS",
            "COLLECT_COHERENT_GPT_GEMINI_FULL_TUPLES",
            "ADJUDICATE_WHOLE_OBJECT_DISAGREEMENTS_WITH_KIMI_K3",
            "FREEZE_COHERENT_REFERENCE",
            "COLLECT_LOCAL_ROLE_OUTPUTS",
            "RUN_DEEPSEEK_COORDINATOR",
            "SCORE_WITHOUT_REFERENCE_REVISION",
        ],
        "current_phase": "AWAITING_COHERENT_GPT_GEMINI_FULL_TUPLES",
        "candidate_run_allowed": False,
        "reference_revision_after_candidate_run_allowed": False,
        "ground_truth_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    protocol = {**protocol_commitment, "artifact_hash": hash_payload(protocol_commitment)}
    write(output / "reference_first_protocol.json", protocol)
    print(json.dumps({
        "corpus_hash": corpus["artifact_hash"],
        "panel_id": manifest["panel_id"],
        "gpt_pack_hash": next(pack["pack_hash"] for pack in packs if pack["lane_id"] == "annotation-lane-a"),
        "gemini_pack_hash": next(pack["pack_hash"] for pack in packs if pack["lane_id"] == "annotation-lane-b"),
        "case_count": manifest["candidate_count"],
        "current_phase": protocol["current_phase"],
        "candidate_run_allowed": protocol["candidate_run_allowed"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
