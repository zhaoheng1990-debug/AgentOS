"""Finalize the v0.19 Kimi K3 reference and external evaluation."""

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

from local_collective_cognition.cognitive_action_evidence_evaluation import (  # noqa: E402
    build_evidence_external_evaluation,
    build_evidence_external_reference,
    render_evidence_external_evaluation,
    validate_evidence_external_evaluation,
)
from local_collective_cognition.cognitive_action_evidence_panel import (  # noqa: E402
    validate_evidence_adjudication_response,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_deterministic_zip(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source, member_name in members:
            info = zipfile.ZipInfo(member_name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--k3-response",
        default=(
            r"C:\Users\ZH\.codex\attachments"
            r"\5ee719cc-4c34-4d9a-b089-11c23c92bd32\pasted-text.txt"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "outputs" / "evidence_state_calibration_v0_19"),
    )
    args = parser.parse_args()
    output = Path(args.output_dir)
    panel_dir = output / "external_panel"
    raw_dir = panel_dir / "raw_received"
    raw_dir.mkdir(parents=True, exist_ok=True)

    response_path = Path(args.k3_response)
    response = read(response_path)
    pack = read(panel_dir / "kimi_k3_evidence_adjudication_pack.json")
    manifest = read(panel_dir / "evidence_adjudication_manifest.json")
    validate_evidence_adjudication_response(response, pack=pack)

    raw_path = raw_dir / f"KIMI_K3_{response_path.name}"
    shutil.copyfile(response_path, raw_path)
    validated_path = panel_dir / "KIMI_K3_validated_adjudication_response.json"
    write(validated_path, response)

    reference = build_evidence_external_reference(
        adjudication_pack=pack,
        adjudication_manifest=manifest,
        adjudication_response=response,
    )
    run = read(output / "evidence_calibration_run.json")
    analysis = read(output / "evidence_calibration_analysis.json")
    preregistration = read(output / "evidence_preregistration.json")
    evaluation = build_evidence_external_evaluation(
        reference=reference,
        run=run,
        analysis=analysis,
        preregistration=preregistration,
    )
    corpus = read(output / "evidence_fresh_corpus_frozen.json")
    validate_evidence_external_evaluation(
        evaluation,
        reference=reference,
        run=run,
        analysis=analysis,
        preregistration=preregistration,
    )

    reference_path = panel_dir / "evidence_external_reference_candidate.json"
    evaluation_path = panel_dir / "evidence_external_evaluation.json"
    report_path = panel_dir / "EVIDENCE_EXTERNAL_EVALUATION.md"
    write(reference_path, reference)
    write(evaluation_path, evaluation)
    report_path.write_text(
        render_evidence_external_evaluation(evaluation),
        encoding="utf-8",
    )
    diagnostics = build_diagnostics(corpus, evaluation)
    diagnostics_path = panel_dir / "evidence_external_error_diagnostics.json"
    write(diagnostics_path, diagnostics)

    closure_commitment = {
        "closure_version": "evidence_external_evaluation_closure_v0_19",
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
        "selection_authority": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    closure = {
        **closure_commitment,
        "artifact_hash": hash_payload(closure_commitment),
    }
    closure_path = panel_dir / "evidence_external_evaluation_closure.json"
    write(closure_path, closure)

    pack_path = output / "evidence_external_evaluation_v0_19_return_pack.zip"
    pack_members = (
        (panel_dir / "kimi_k3_evidence_adjudication_pack.json", "kimi_k3_evidence_adjudication_pack.json"),
        (panel_dir / "evidence_adjudication_manifest.json", "evidence_adjudication_manifest.json"),
        (validated_path, validated_path.name),
        (reference_path, reference_path.name),
        (evaluation_path, evaluation_path.name),
        (report_path, report_path.name),
        (diagnostics_path, diagnostics_path.name),
        (closure_path, closure_path.name),
    )
    write_deterministic_zip(pack_path, pack_members)

    inventory_paths = [source for source, _ in pack_members] + [raw_path, pack_path]
    inventory_commitment = {
        "inventory_version": "evidence_external_evaluation_hash_inventory_v0_19",
        "items": [
            {
                "path": str(path.relative_to(output)).replace("\\", "/"),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in inventory_paths
        ],
    }
    inventory = {
        **inventory_commitment,
        "artifact_hash": hash_payload(inventory_commitment),
    }
    write(
        panel_dir / "evidence_external_evaluation_hash_inventory.json",
        inventory,
    )

    print(json.dumps({
        "reference_hash": reference["artifact_hash"],
        "evaluation_hash": evaluation["artifact_hash"],
        "reference_state_distributions": evaluation["reference_state_distributions"],
        "arm_metrics": evaluation["arm_metrics"],
        "admission_metrics": evaluation["admission_metrics"],
        "gate_conditions": evaluation["preregistered_gate_conditions"],
        "anti_additive_gate": evaluation["anti_additive_gate"],
        "candidate_state": evaluation["candidate_state"],
        "return_pack": str(pack_path),
        "return_pack_sha256": sha256_file(pack_path),
    }, indent=2, sort_keys=True))


def build_diagnostics(corpus, evaluation):
    bindings = corpus["private_provenance"]["bindings"]
    records = []
    for record in evaluation["admission_records"]["CONTRASTIVE_SOURCE_CALIBRATOR"]:
        binding = bindings[record["conflict_id"]]
        records.append({
            **record,
            "case_id": binding["case_id"],
            "object_family": binding["object_family"],
        })
    commitment = {
        "diagnostic_version": "evidence_external_error_diagnostics_v0_19",
        "evaluation_hash": evaluation["artifact_hash"],
        "records": records,
        "post_hoc_diagnostic_only": True,
        "gate_effect": False,
        "reference_revision_allowed": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


if __name__ == "__main__":
    raise SystemExit(main())
