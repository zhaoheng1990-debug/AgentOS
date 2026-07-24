"""Finalize the v0.18 Kimi K3 reference and external evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_selective_evaluation import (  # noqa: E402
    build_selective_external_evaluation,
    build_selective_external_reference,
    render_selective_external_evaluation,
    validate_selective_external_evaluation,
)
from local_collective_cognition.cognitive_action_selective_panel import (  # noqa: E402
    validate_selective_adjudication_response,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--k3-response",
        default=r"C:\Users\ZH\Downloads\selective_adjudication_result_kimi_k3.json",
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "outputs" / "selective_escalation_v0_18"),
    )
    args = parser.parse_args()
    output = Path(args.output_dir)
    panel_dir = output / "external_panel"
    raw_dir = panel_dir / "raw_received"
    raw_dir.mkdir(parents=True, exist_ok=True)
    response_path = Path(args.k3_response)
    response = read(response_path)
    pack = read(panel_dir / "kimi_k3_selective_adjudication_pack.json")
    manifest = read(panel_dir / "selective_adjudication_manifest.json")
    validate_selective_adjudication_response(response, pack=pack)
    raw_path = raw_dir / f"KIMI_K3_{response_path.name}"
    shutil.copyfile(response_path, raw_path)
    write(panel_dir / "KIMI_K3_validated_adjudication_response.json", response)
    reference = build_selective_external_reference(
        adjudication_pack=pack,
        adjudication_manifest=manifest,
        adjudication_response=response,
    )
    baseline = read(output / "selective_baseline_run.json")
    admission = read(output / "selective_admission_plan.json")
    selective_run = read(output / "selective_adjudication_run.json")
    runtime_analysis = read(output / "selective_analysis.json")
    preregistration = read(output / "selective_preregistration.json")
    evaluation = build_selective_external_evaluation(
        reference=reference,
        baseline_run=baseline,
        admission_plan=admission,
        selective_run=selective_run,
        runtime_analysis=runtime_analysis,
        preregistration=preregistration,
    )
    validate_selective_external_evaluation(
        evaluation,
        reference=reference,
        baseline_run=baseline,
        admission_plan=admission,
        selective_run=selective_run,
        runtime_analysis=runtime_analysis,
        preregistration=preregistration,
    )
    write(panel_dir / "selective_external_reference_candidate.json", reference)
    write(panel_dir / "selective_external_evaluation.json", evaluation)
    report_path = panel_dir / "SELECTIVE_EXTERNAL_EVALUATION.md"
    report_path.write_text(
        render_selective_external_evaluation(evaluation),
        encoding="utf-8",
    )
    closure_commitment = {
        "closure_version": "selective_external_evaluation_closure_v0_18",
        "panel_id": manifest["panel_id"],
        "adjudication_manifest_hash": manifest["manifest_hash"],
        "k3_source_path": str(response_path),
        "k3_raw_copy": str(raw_path.relative_to(output)).replace("\\", "/"),
        "k3_raw_sha256": sha256_file(raw_path),
        "k3_response_hash": hash_payload(response),
        "reference_hash": reference["artifact_hash"],
        "evaluation_hash": evaluation["artifact_hash"],
        "anti_additive_gate": evaluation["anti_additive_gate"],
        "candidate_state": evaluation["candidate_state"],
        "baseline_promotion_allowed": evaluation["baseline_promotion_allowed"],
        "retention_write_allowed": False,
        "production_authority": False,
    }
    closure = {**closure_commitment, "artifact_hash": hash_payload(closure_commitment)}
    write(panel_dir / "selective_external_evaluation_closure.json", closure)
    pack_path = output / "selective_external_evaluation_v0_18_return_pack.zip"
    pack_names = (
        "KIMI_K3_validated_adjudication_response.json",
        "selective_external_reference_candidate.json",
        "selective_external_evaluation.json",
        "SELECTIVE_EXTERNAL_EVALUATION.md",
        "selective_external_evaluation_closure.json",
    )
    with zipfile.ZipFile(pack_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in pack_names:
            zip_info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            zip_info.compress_type = zipfile.ZIP_DEFLATED
            zip_info.external_attr = 0o644 << 16
            archive.writestr(zip_info, (panel_dir / name).read_bytes())
    inventory_paths = [panel_dir / name for name in pack_names] + [raw_path, pack_path]
    inventory_commitment = {
        "inventory_version": "selective_external_evaluation_hash_inventory_v0_18",
        "items": [
            {
                "path": str(path.relative_to(output)).replace("\\", "/"),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in inventory_paths
        ],
    }
    inventory = {**inventory_commitment, "artifact_hash": hash_payload(inventory_commitment)}
    write(panel_dir / "selective_external_evaluation_hash_inventory.json", inventory)
    print(json.dumps({
        "reference_hash": reference["artifact_hash"],
        "evaluation_hash": evaluation["artifact_hash"],
        "anti_additive_gate": evaluation["anti_additive_gate"],
        "candidate_state": evaluation["candidate_state"],
        "admission_metrics": evaluation["admission_metrics"],
        "axis_correct": evaluation["arm_metrics"]["SINGLE_MODEL_BASELINE"]["axis_correct"],
        "primary_correct_cells": evaluation["arm_metrics"]["SINGLE_MODEL_BASELINE"]["primary_correct_cell_count"],
        "all_correct_cells": evaluation["arm_metrics"]["SINGLE_MODEL_BASELINE"]["all_correct_cell_count"],
        "full_tuple_correct": evaluation["arm_metrics"]["SINGLE_MODEL_BASELINE"]["full_tuple_correct"],
        "return_pack": str(pack_path),
        "return_pack_sha256": sha256_file(pack_path),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
