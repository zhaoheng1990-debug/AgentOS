"""Freeze v0.5 veto-warrant protocol and blind annotation packs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.negative_evidence_warrant_calibration import CALIBRATION_VERSION, FROZEN_GATES
from local_collective_cognition.negative_evidence_warrant_fusion import ARM_LANES
from local_collective_cognition.negative_evidence_warrant_holdout import build_warrant_corpus_artifact, validate_warrant_corpus_artifact
from local_collective_cognition.negative_evidence_warrant_runtime import CONTROL_PROMPT_POLICY, RECOVERY_RUNTIME_VERSION
from local_collective_cognition.provider_telemetry import hash_payload
from local_collective_cognition.structure_reference_panel_pack import build_reference_panel, validate_reference_panel


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/negative_evidence_warrant_v0_5_1")
    args = parser.parse_args()
    output_dir = resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    corpus = build_warrant_corpus_artifact()
    validate_warrant_corpus_artifact(corpus)
    packs, manifest = build_reference_panel(semantic_artifact=corpus)
    validate_reference_panel(packs=packs, manifest=manifest, semantic_artifact=corpus)
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "runtime_version": RECOVERY_RUNTIME_VERSION,
        "control_prompt_policy": CONTROL_PROMPT_POLICY,
        "recovery_scope": "FULL_RUN_PRE_REFERENCE_CONTROL_PROMPT_RESTORATION",
        "predecessor_candidate_state": "CONSTRUCTION_FAILED_BEFORE_REFERENCE",
        "methodology_kernel": "v1.1",
        "theory_baseline": "AgentOS local collective cognition v0.32.1",
        "specific_objective": "test whether execution-worthy veto warrants preserve correction while recovering usable recall",
        "object_before_proxy": {
            "ontology_object": "execution-worthy negative evidence",
            "observable_proxy": "naive and warranted arm packet decisions",
            "metric": "accuracy, false-usable rate, usable recall, category risk, and provider cost",
        },
        "corpus_artifact_hash": corpus["artifact_hash"],
        "corpus_spec_hash": corpus["corpus_spec"]["spec_hash"],
        "panel_id": manifest["panel_id"],
        "lane_pack_hashes": manifest["lane_pack_hashes"],
        "frozen_gates": FROZEN_GATES,
        "arm_lanes": {key: list(value) for key, value in ARM_LANES.items()},
        "current_reference_labels_available": False,
        "post_current_reference_adaptation_allowed": False,
        "construction_categories_are_ground_truth": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    contract = {**commitment, "contract_hash": hash_payload(commitment)}
    write(output_dir / "private_negative_warrant_corpus.json", corpus)
    names = {
        "annotation-lane-a": "gpt_5_6_negative_warrant_pack.json",
        "annotation-lane-b": "gemini_3_1_negative_warrant_pack.json",
    }
    for pack in packs:
        path = output_dir / names[pack["lane_id"]]
        write(path, pack)
        with ZipFile(path.with_suffix(".zip"), "w", compression=ZIP_DEFLATED) as archive:
            archive.write(path, arcname=path.name)
    write(output_dir / "private_panel_manifest.json", manifest)
    write(output_dir / "warrant_calibration_contract.json", contract)
    print(json.dumps({
        "corpus_artifact_hash": corpus["artifact_hash"],
        "panel_id": manifest["panel_id"],
        "pack_hashes": manifest["lane_pack_hashes"],
        "contract_hash": contract["contract_hash"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
