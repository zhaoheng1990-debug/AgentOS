"""Finalize the v0.15 whole-object K3 adjudication and freeze the reference."""

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

from local_collective_cognition.clarification_reference_first_panel import (  # noqa: E402
    build_reference_first_final_analysis,
    build_reference_first_reference,
    render_reference_first_final_analysis,
    validate_reference_first_adjudication,
    validate_reference_first_adjudication_response,
    validate_reference_first_final_analysis,
    validate_reference_first_reference,
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
                and candidate.get("panel_version") == pack["panel_version"]
                and candidate.get("adjudication_version") == pack["adjudication_version"]
                and candidate.get("panel_id") == pack["panel_id"]
                and candidate.get("adjudication_pack_hash") == pack["pack_hash"]
            ):
                matches.append((candidate, name))
    if len(matches) != 1:
        raise ValueError(f"reference_first_k3_bundle_match_invalid:{[name for _, name in matches]}")
    return matches[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", default=r"C:/Users/ZH/Downloads/Kimi_Agent_裁定结果摘要 (10).zip")
    parser.add_argument("--output-dir", default="outputs/clarification_reference_first_v0_15")
    args = parser.parse_args()
    output = resolve(args.output_dir)
    bundle = resolve(args.bundle)
    corpus = read(output / "private_reference_first_corpus.json")
    agreement_analysis = read(output / "panel_agreement_analysis.json")
    pack = read(output / "kimi_k3_reference_first_adjudication_pack.json")
    manifest = read(output / "private_reference_first_adjudication_manifest.json")
    validate_reference_first_adjudication(pack=pack, manifest=manifest)
    response, member = read_exact_response(bundle, pack=pack)
    validate_reference_first_adjudication_response(response, pack=pack)
    reference = build_reference_first_reference(
        adjudication_pack=pack,
        adjudication_manifest=manifest,
        response=response,
    )
    validate_reference_first_reference(
        reference,
        source_inputs={"adjudication_pack": pack, "adjudication_manifest": manifest, "response": response},
    )
    analysis = build_reference_first_final_analysis(
        corpus_artifact=corpus,
        agreement_analysis=agreement_analysis,
        adjudication_pack=pack,
        adjudication_manifest=manifest,
        response=response,
        reference=reference,
    )
    validate_reference_first_final_analysis(
        analysis,
        corpus_artifact=corpus,
        agreement_analysis=agreement_analysis,
        adjudication_pack=pack,
        adjudication_manifest=manifest,
        response=response,
        reference=reference,
    )
    bundle_sha256 = hashlib.sha256(bundle.read_bytes()).hexdigest()
    receipt_commitment = {
        "ingest_version": "clarification_reference_first_k3_ingest_v0_15",
        "bundle_name": bundle.name,
        "bundle_sha256": bundle_sha256,
        "selected_member": member,
        "adjudication_pack_hash": pack["pack_hash"],
        "adjudication_response_hash": hash_payload(response),
        "frozen_reference_hash": reference["artifact_hash"],
        "final_analysis_hash": analysis["artifact_hash"],
    }
    receipt = {**receipt_commitment, "artifact_hash": hash_payload(receipt_commitment)}
    progress_commitment = {
        "progress_version": "clarification_reference_first_reference_frozen_v0_15",
        "source_corpus_hash": corpus["artifact_hash"],
        "frozen_reference_hash": reference["artifact_hash"],
        "final_analysis_hash": analysis["artifact_hash"],
        "k3_ingestion_receipt_hash": receipt["artifact_hash"],
        "current_phase": "REFERENCE_FROZEN_AWAITING_LOCAL_ROLE_OUTPUTS",
        "local_role_collection_allowed": True,
        "coordinator_run_allowed": False,
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    progress = {**progress_commitment, "artifact_hash": hash_payload(progress_commitment)}
    write(output / "kimi_k3_reference_first_response.json", response)
    write(output / "reference_first_model_panel_reference_candidate.json", reference)
    write(output / "final_panel_analysis.json", analysis)
    (output / "FINAL_PANEL_ANALYSIS.md").write_text(render_reference_first_final_analysis(analysis), encoding="utf-8")
    write(output / "k3_ingestion_receipt.json", receipt)
    write(output / "reference_frozen_progress.json", progress)
    print(json.dumps({
        "bundle_member": member,
        "bundle_sha256": bundle_sha256,
        "adjudication_response_hash": hash_payload(response),
        "reference_hash": reference["artifact_hash"],
        "reference_state": reference["candidate_state"],
        "cross_axis_inconsistency_count": reference["cross_axis_inconsistency_count"],
        "analysis_hash": analysis["artifact_hash"],
        "mean_adjudication_confidence": analysis["mean_adjudication_confidence"],
        "decision_basis_counts": analysis["decision_basis_counts"],
        "selected_source_lane_counts": analysis["selected_source_lane_counts"],
        "hard_basis_granularity_outcomes": analysis["hard_basis_granularity_outcomes"],
        "current_phase": progress["current_phase"],
        "local_role_collection_allowed": progress["local_role_collection_allowed"],
        "coordinator_run_allowed": progress["coordinator_run_allowed"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
