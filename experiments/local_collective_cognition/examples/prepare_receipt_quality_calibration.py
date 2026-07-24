"""Freeze the independent corpus and prepare GPT/Gemini annotation packs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.receipt_quality_calibration_corpus import (  # noqa: E402
    build_receipt_quality_corpus_artifact,
    validate_receipt_quality_corpus_artifact,
)
from local_collective_cognition.receipt_quality_candidate_calibration import (  # noqa: E402
    CALIBRATION_VERSION,
    FROZEN_GATES,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.structure_reference_panel_pack import (  # noqa: E402
    build_reference_panel,
    validate_reference_panel,
)


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _write(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", default="outputs/receipt_quality_calibration_v0_1",
    )
    args = parser.parse_args()
    corpus = build_receipt_quality_corpus_artifact()
    validate_receipt_quality_corpus_artifact(corpus)
    packs, manifest = build_reference_panel(semantic_artifact=corpus)
    validate_reference_panel(
        packs=packs, manifest=manifest, semantic_artifact=corpus,
    )
    output = _resolve(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    names = {
        "annotation-lane-a": "gpt_5_6_receipt_quality_pack.json",
        "annotation-lane-b": "gemini_3_1_receipt_quality_pack.json",
    }
    calibration_commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "corpus_artifact_hash": corpus["artifact_hash"],
        "corpus_spec_hash": corpus["corpus_spec"]["spec_hash"],
        "panel_id": manifest["panel_id"],
        "lane_pack_hashes": manifest["lane_pack_hashes"],
        "frozen_gates": FROZEN_GATES,
        "reference_labels_available": False,
        "post_reference_gate_adaptation_allowed": False,
        "selection_authority": False,
        "retention_authority": False,
    }
    calibration_contract = {
        **calibration_commitment,
        "contract_hash": hash_payload(calibration_commitment),
    }
    _write(output / "private_receipt_quality_corpus.json", corpus)
    for pack in packs:
        _write(output / names[pack["lane_id"]], pack)
    _write(output / "private_panel_manifest.json", manifest)
    _write(output / "candidate_calibration_contract.json", calibration_contract)
    print(json.dumps({
        "corpus_artifact_hash": corpus["artifact_hash"],
        "corpus_spec_hash": corpus["corpus_spec"]["spec_hash"],
        "panel_id": manifest["panel_id"],
        "candidate_count": manifest["candidate_count"],
        "criterion_count": manifest["criterion_count"],
        "panel_state": manifest["reference_state"],
        "pack_hashes": manifest["lane_pack_hashes"],
        "private_manifest_hash": manifest["manifest_hash"],
        "calibration_contract_hash": calibration_contract["contract_hash"],
        "output_dir": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
