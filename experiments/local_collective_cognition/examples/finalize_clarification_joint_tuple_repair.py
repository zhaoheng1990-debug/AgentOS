"""Finalize the v0.14 Kimi-K3 full-tuple repair and recalibration."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from zipfile import ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_joint_fresh_panel_calibration import (  # noqa: E402
    build_joint_fresh_panel_calibration,
    validate_joint_fresh_panel_calibration,
)
from local_collective_cognition.clarification_joint_tuple_repair import (  # noqa: E402
    build_joint_tuple_repair_analysis,
    build_joint_tuple_repaired_reference,
    render_joint_tuple_repair_analysis,
    validate_joint_tuple_repair_analysis,
    validate_joint_tuple_repair_pack,
    validate_joint_tuple_repair_response,
    validate_joint_tuple_repaired_reference,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def read(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def read_exact_response(bundle, *, pack):
    matches = []
    with ZipFile(bundle) as archive:
        for name in archive.namelist():
            if Path(name).suffix.casefold() != ".json":
                continue
            try:
                candidate = json.loads(archive.read(name).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if (
                isinstance(candidate, dict)
                and candidate.get("repair_version") == pack["repair_version"]
                and candidate.get("source_panel_id") == pack["source_panel_id"]
                and candidate.get("repair_pack_hash") == pack["pack_hash"]
            ):
                matches.append((candidate, name))
    if len(matches) != 1:
        raise ValueError(f"joint_tuple_repair_bundle_match_invalid:{[name for _, name in matches]}")
    return matches[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", default=r"C:/Users/ZH/Downloads/Kimi_Agent_裁定结果摘要 (9).zip")
    parser.add_argument("--source-dir", default="outputs/clarification_joint_fresh_v0_13")
    parser.add_argument("--repair-dir", default="outputs/clarification_joint_tuple_repair_v0_14")
    args = parser.parse_args()
    source = resolve(args.source_dir)
    output = resolve(args.repair_dir)
    bundle = resolve(args.bundle)
    pack = read(output / "kimi_k3_joint_tuple_repair_pack.json")
    manifest = read(output / "private_joint_tuple_repair_manifest.json")
    source_reference = read(source / "joint_fresh_model_panel_reference_candidate.json")
    validate_joint_tuple_repair_pack(pack=pack, manifest=manifest)
    response, member = read_exact_response(bundle, pack=pack)
    validate_joint_tuple_repair_response(response, pack=pack)
    repaired_reference = build_joint_tuple_repaired_reference(
        source_reference=source_reference,
        repair_pack=pack,
        repair_manifest=manifest,
        repair_response=response,
    )
    validate_joint_tuple_repaired_reference(
        repaired_reference,
        source_reference=source_reference,
        repair_pack=pack,
        repair_manifest=manifest,
        repair_response=response,
    )
    corpus = read(source / "private_joint_corpus.json")
    run = read(source / "candidate_run.json")
    prior_calibration = read(source / "panel_recalibration.json")
    repaired_calibration = build_joint_fresh_panel_calibration(
        corpus_artifact=corpus,
        run=run,
        panel_reference=repaired_reference,
    )
    validate_joint_fresh_panel_calibration(
        repaired_calibration,
        corpus_artifact=corpus,
        run=run,
        panel_reference=repaired_reference,
    )
    analysis = build_joint_tuple_repair_analysis(
        source_reference=source_reference,
        repaired_reference=repaired_reference,
        repair_response=response,
        prior_calibration=prior_calibration,
        repaired_calibration=repaired_calibration,
    )
    validate_joint_tuple_repair_analysis(
        analysis,
        source_reference=source_reference,
        repaired_reference=repaired_reference,
        repair_response=response,
        prior_calibration=prior_calibration,
        repaired_calibration=repaired_calibration,
    )
    bundle_sha256 = hashlib.sha256(bundle.read_bytes()).hexdigest()
    receipt_commitment = {
        "ingest_version": "clarification_joint_tuple_repair_ingest_v0_14",
        "bundle_name": bundle.name,
        "bundle_sha256": bundle_sha256,
        "selected_member": member,
        "repair_pack_hash": pack["pack_hash"],
        "repair_response_hash": hash_payload(response),
        "repaired_reference_hash": repaired_reference["artifact_hash"],
        "repaired_calibration_hash": repaired_calibration["artifact_hash"],
        "analysis_hash": analysis["artifact_hash"],
    }
    receipt = {**receipt_commitment, "artifact_hash": hash_payload(receipt_commitment)}
    write(output / "kimi_k3_joint_tuple_repair_response.json", response)
    write(output / "joint_tuple_repaired_model_panel_reference_candidate.json", repaired_reference)
    write(output / "repaired_panel_recalibration.json", repaired_calibration)
    write(output / "final_repair_analysis.json", analysis)
    (output / "FINAL_REPAIR_ANALYSIS.md").write_text(render_joint_tuple_repair_analysis(analysis), encoding="utf-8")
    write(output / "ingestion_receipt.json", receipt)
    print(json.dumps({
        "bundle_member": member,
        "bundle_sha256": bundle_sha256,
        "repair_response_hash": hash_payload(response),
        "reference_hash": repaired_reference["artifact_hash"],
        "reference_state": repaired_reference["candidate_state"],
        "cross_axis_inconsistency_count": repaired_reference["cross_axis_inconsistency_count"],
        "calibration_hash": repaired_calibration["artifact_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "repair_change_counts": analysis["repair_change_counts"],
        "mean_repair_confidence": analysis["mean_repair_confidence"],
        "candidate_metrics": repaired_calibration["candidate_metrics"],
        "candidate_metric_deltas": analysis["candidate_metric_deltas"],
        "transfer_recommendation": analysis["transfer_recommendation"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
