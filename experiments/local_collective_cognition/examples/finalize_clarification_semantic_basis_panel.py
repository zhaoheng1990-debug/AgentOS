"""Finalize the v0.11 model panel from an exact Kimi-K3 bundle member."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_semantic_basis_panel import build_semantic_basis_reference, validate_semantic_basis_adjudication, validate_semantic_basis_adjudication_response, validate_semantic_basis_reference
from local_collective_cognition.clarification_semantic_basis_panel_calibration import build_semantic_basis_panel_analysis, build_semantic_basis_panel_calibration, render_semantic_basis_panel_analysis, validate_semantic_basis_panel_calibration


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def read(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def read_exact_response(bundle, panel_id):
    with ZipFile(resolve(bundle)) as archive:
        matches = [name for name in archive.namelist() if panel_id in Path(name).name and Path(name).suffix.casefold() == ".json"]
        if len(matches) != 1:
            raise ValueError(f"semantic_basis_k3_bundle_match_invalid:{matches}")
        return json.loads(archive.read(matches[0]).decode("utf-8")), matches[0]


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/clarification_semantic_basis_v0_11"
    parser.add_argument("--bundle", default=r"C:/Users/ZH/Downloads/Kimi_Agent_裁定结果摘要 (7).zip")
    parser.add_argument("--output-dir", default=base)
    args = parser.parse_args()
    output = resolve(args.output_dir)
    corpus = read(f"{base}/private_semantic_basis_corpus.json")
    candidate_run = read(f"{base}/candidate_run.json")
    pack = read(f"{base}/kimi_k3_semantic_basis_adjudication_pack.json")
    manifest = read(f"{base}/private_semantic_basis_adjudication_manifest.json")
    validate_semantic_basis_adjudication(pack=pack, manifest=manifest)
    response, member = read_exact_response(args.bundle, pack["panel_id"])
    validate_semantic_basis_adjudication_response(response, pack=pack)
    reference = build_semantic_basis_reference(adjudication_pack=pack, adjudication_manifest=manifest, response=response)
    validate_semantic_basis_reference(reference, adjudication_pack=pack, adjudication_manifest=manifest, response=response)
    calibration = build_semantic_basis_panel_calibration(corpus_artifact=corpus, candidate_run=candidate_run, panel_reference=reference)
    validate_semantic_basis_panel_calibration(calibration, corpus_artifact=corpus, candidate_run=candidate_run, panel_reference=reference)
    analysis = build_semantic_basis_panel_analysis(calibration, panel_reference=reference)
    output.mkdir(parents=True, exist_ok=True)
    write(output / "kimi_k3_semantic_basis_response.json", response)
    write(output / "semantic_basis_model_panel_reference_candidate.json", reference)
    write(output / "panel_recalibration.json", calibration)
    write(output / "final_panel_analysis.json", analysis)
    (output / "FINAL_PANEL_ANALYSIS.md").write_text(render_semantic_basis_panel_analysis(analysis), encoding="utf-8")
    print(json.dumps({
        "bundle_member": member,
        "reference_hash": reference["artifact_hash"],
        "reference_state": reference["candidate_state"],
        "cross_axis_inconsistency_count": reference["cross_axis_inconsistency_count"],
        "calibration_hash": calibration["artifact_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "transfer_recommendation": calibration["transfer_recommendation"],
        "candidate_metrics": calibration["arm_metrics"]["SEMANTIC_BASIS_V0_11"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
