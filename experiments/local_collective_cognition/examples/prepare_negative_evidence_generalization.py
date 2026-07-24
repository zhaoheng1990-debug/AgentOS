"""Freeze v0.2 generalization protocol and create blind annotation packs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.negative_evidence_generalization_calibration import (  # noqa: E402
    CALIBRATION_VERSION,
    FROZEN_GATES,
)
from local_collective_cognition.negative_evidence_generalization_fusion import (  # noqa: E402
    ARM_LANES,
)
from local_collective_cognition.negative_evidence_generalization_holdout import (  # noqa: E402
    build_generalization_corpus_artifact,
    validate_generalization_corpus_artifact,
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
        "--output-dir", default="outputs/negative_evidence_generalization_v0_2",
    )
    args = parser.parse_args()
    corpus = build_generalization_corpus_artifact()
    validate_generalization_corpus_artifact(corpus)
    packs, manifest = build_reference_panel(semantic_artifact=corpus)
    validate_reference_panel(
        packs=packs, manifest=manifest, semantic_artifact=corpus,
    )
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "corpus_artifact_hash": corpus["artifact_hash"],
        "corpus_spec_hash": corpus["corpus_spec"]["spec_hash"],
        "panel_id": manifest["panel_id"],
        "lane_pack_hashes": manifest["lane_pack_hashes"],
        "frozen_gates": FROZEN_GATES,
        "arm_lanes": {arm: list(lanes) for arm, lanes in ARM_LANES.items()},
        "reference_labels_available": False,
        "post_reference_adaptation_allowed": False,
        "construction_categories_are_ground_truth": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    contract = {**commitment, "contract_hash": hash_payload(commitment)}
    output = _resolve(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    names = {
        "annotation-lane-a": "gpt_5_6_negative_generalization_pack.json",
        "annotation-lane-b": "gemini_3_1_negative_generalization_pack.json",
    }
    _write(output / "private_negative_generalization_corpus.json", corpus)
    for pack in packs:
        path = output / names[pack["lane_id"]]
        _write(path, pack)
        with ZipFile(path.with_suffix(".zip"), "w", compression=ZIP_DEFLATED) as archive:
            archive.write(path, arcname=path.name)
    _write(output / "private_panel_manifest.json", manifest)
    _write(output / "generalization_calibration_contract.json", contract)
    print(json.dumps({
        "corpus_artifact_hash": corpus["artifact_hash"],
        "corpus_spec_hash": corpus["corpus_spec"]["spec_hash"],
        "panel_id": manifest["panel_id"],
        "candidate_count": manifest["candidate_count"],
        "pack_hashes": manifest["lane_pack_hashes"],
        "contract_hash": contract["contract_hash"],
        "output_dir": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
