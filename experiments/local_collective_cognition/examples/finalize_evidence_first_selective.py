"""Freeze v0.22 diagnostics and blinded external annotation packs."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_evidence_first_holdout import (  # noqa: E402
    CASES,
)
from local_collective_cognition.cognitive_action_evidence_first_panel import (  # noqa: E402
    build_evidence_first_external_panel,
    validate_evidence_first_external_panel,
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
    output = REPO_ROOT / "outputs" / "evidence_first_selective_v0_22"
    corpus = read(output / "evidence_first_corpus_frozen.json")
    preregistration = read(output / "evidence_first_preregistration.json")
    run = read(output / "evidence_first_run.json")
    analysis = read(output / "evidence_first_analysis.json")
    telemetry = read(output / "evidence_first_telemetry.json")
    diagnostics = build_diagnostics(corpus, run, analysis)
    diagnostics_path = output / "evidence_first_structural_diagnostics.json"
    report_path = output / "EVIDENCE_FIRST_CANDIDATE_ANALYSIS.md"
    write(diagnostics_path, diagnostics)
    report_path.write_text(
        render_analysis(analysis, diagnostics),
        encoding="utf-8",
    )

    packs, panel_manifest = build_evidence_first_external_panel(
        corpus=corpus,
        run=run,
    )
    validate_evidence_first_external_panel(
        packs=packs,
        manifest=panel_manifest,
        source_inputs={"corpus": corpus, "run": run},
    )
    panel_dir = output / "external_panel"
    panel_dir.mkdir(exist_ok=True)
    lane_names = []
    for pack in packs:
        name = f"{pack['lane_id'].lower()}_evidence_first_pack.json"
        write(panel_dir / name, pack)
        lane_names.append(name)
    panel_manifest_path = (
        panel_dir / "evidence_first_external_panel_manifest.json"
    )
    write(panel_manifest_path, panel_manifest)

    ledger_commitment = {
        "ledger_version": "evidence_first_phase_ledger_v0_22",
        "phases": [
            {"phase": "G0_PREREGISTRATION", "status": "PASS", "hash": preregistration["artifact_hash"]},
            {"phase": "G1_FRESH_HOLDOUT", "status": "PASS", "hash": corpus["artifact_hash"]},
            {
                "phase": "G2_CANDIDATE_RUN",
                "status": "PASS_STRUCTURAL_PENDING_EXTERNAL_PANEL",
                "cell_coverage": analysis["cell_coverage"],
                "challenged_count": analysis["challenged_count"],
                "completed_challenge_count": analysis["completed_challenge_count"],
                "witness_validation_rate": analysis["witness_validation_rate"],
            },
            {"phase": "G3_EXTERNAL_REFERENCE", "status": "PENDING", "panel_id": panel_manifest["panel_id"]},
        ],
        "baseline_insertion": "No Baseline Object Update; experiment candidate only",
    }
    ledger = {**ledger_commitment, "artifact_hash": hash_payload(ledger_commitment)}
    write(output / "phase_ledger.json", ledger)
    replay_commitment = {
        "pointer_version": "evidence_first_replay_v0_22",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_evidence_first_selective.py",
            "python examples/run_evidence_first_selective.py",
            "python examples/finalize_evidence_first_selective.py",
        ],
        "frozen_preregistration_hash": preregistration["artifact_hash"],
        "frozen_corpus_hash": corpus["artifact_hash"],
        "reference_revision_allowed": False,
    }
    write(output / "replay_pointer.json", {
        **replay_commitment,
        "artifact_hash": hash_payload(replay_commitment),
    })
    rollback_commitment = {
        "pointer_version": "evidence_first_rollback_v0_22",
        "scope": "experiment-only; AgentOS CoreSlim excluded",
        "rollback_action": "quarantine v0.22 code and outputs after hash verification",
        "baseline_mutation_to_reverse": False,
        "retention_mutation_to_reverse": False,
    }
    write(output / "rollback_pointer.json", {
        **rollback_commitment,
        "artifact_hash": hash_payload(rollback_commitment),
    })
    names = [
        "evidence_first_preregistration.json",
        "evidence_first_corpus_frozen.json",
        "evidence_first_run.json",
        "evidence_first_analysis.json",
        "evidence_first_telemetry.json",
        diagnostics_path.name,
        report_path.name,
        "phase_ledger.json",
        "replay_pointer.json",
        "rollback_pointer.json",
        *[f"external_panel/{name}" for name in lane_names],
        "external_panel/evidence_first_external_panel_manifest.json",
    ]
    inventory_commitment = {
        "inventory_version": "evidence_first_hash_inventory_v0_22",
        "items": [{
            "path": name,
            "size_bytes": (output / name).stat().st_size,
            "sha256": sha256_file(output / name),
        } for name in names],
    }
    inventory = {
        **inventory_commitment,
        "artifact_hash": hash_payload(inventory_commitment),
    }
    inventory_path = output / "hash_inventory.json"
    write(inventory_path, inventory)
    manifest_commitment = {
        "manifest_version": "evidence_first_manifest_v0_22",
        "preregistration_hash": preregistration["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "telemetry_hash": telemetry["artifact_hash"],
        "diagnostics_hash": diagnostics["artifact_hash"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "inventory_hash": inventory["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "external_reference_available": False,
        "baseline_promotion_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    manifest = {
        **manifest_commitment,
        "artifact_hash": hash_payload(manifest_commitment),
    }
    manifest_path = output / "manifest.json"
    write(manifest_path, manifest)
    zip_path = output / "evidence_first_external_panel_v0_22.zip"
    members = [
        *[(panel_dir / name, name) for name in lane_names],
        (panel_manifest_path, "PRIVATE_evidence_first_external_panel_manifest.json"),
        (report_path, report_path.name),
        (diagnostics_path, diagnostics_path.name),
        (inventory_path, inventory_path.name),
        (manifest_path, manifest_path.name),
    ]
    write_deterministic_zip(zip_path, members)
    print(json.dumps({
        "panel_id": panel_manifest["panel_id"],
        "lane_pack_hashes": panel_manifest["lane_pack_hashes"],
        "external_panel_pack": str(zip_path),
        "external_panel_pack_sha256": sha256_file(zip_path),
        "cell_coverage": analysis["cell_coverage"],
        "challenged_count": analysis["challenged_count"],
        "completed_challenge_count": analysis["completed_challenge_count"],
        "witness_validation_rate": analysis["witness_validation_rate"],
        "changed_object_count": analysis["changed_object_count"],
        "selective_to_baseline_token_ratio": analysis["selective_to_baseline_token_ratio"],
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


def build_diagnostics(corpus, run, analysis):
    case_by_id = {case.case_id: case for case in CASES}
    bindings = corpus["private_provenance"]["bindings"]
    records = []
    for record in run["challenge_records"]:
        case = case_by_id[bindings[record["conflict_id"]]["case_id"]]
        records.append({
            "conflict_id": record["conflict_id"],
            "case_id": case.case_id,
            "object_family": case.object_family,
            "design_stratum": case.design_stratum,
            "status": record["status"],
            "witness_mode": (record.get("verified_witness") or {}).get("witness_mode"),
            "changed_axes": record.get("changed_axes", []),
        })
    commitment = {
        "diagnostic_version": "evidence_first_structural_diagnostics_v0_22",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "challenge_records": records,
        "post_hoc_diagnostic_only": True,
        "reference_revision_allowed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def render_analysis(analysis, diagnostics):
    records = diagnostics["challenge_records"]
    invalid = [record for record in records if record["status"] != "COMPLETED"]
    changed = [record for record in records if record["changed_axes"]]
    observations = [
        f"Cell coverage is {analysis['cell_coverage']}.",
        f"Six objects are challenged; {analysis['completed_challenge_count']} complete and witness validation rate is {analysis['witness_validation_rate']}.",
        f"Changed-axis counts are {analysis['changed_axis_counts']} across {analysis['changed_object_count']} objects.",
        f"Selective/baseline token ratio is {analysis['selective_to_baseline_token_ratio']}.",
        f"Invalid challenge records are {invalid}.",
        f"Changed challenge records are {changed}.",
    ]
    interpretations = [
        "Evidence-first sequencing sharply limits answer churn compared with unconditional axis decomposition.",
        "The rejected witness paraphrases an exact support span; preserving baseline demonstrates the mechanical boundary is active.",
        "Both changed objects are missing-specification constructions, but their witnesses are labeled positive definition. This may be a real correction or a repeated confusion between a named request and an available definition.",
        "Without external labels, changed outputs are candidate differences rather than corrections.",
    ]
    unknowns = [
        "Whether either changed missing-specification object is corrected or harmed.",
        "Whether unchanged challenged objects were already correct.",
        "Whether the 1.733 token ratio yields positive net Cbit.",
    ]
    intuition = [
        "If the two changes are harms, witness ordering alone is insufficient; witness modes need contrastive negative tests.",
        "If they are corrections, selective evidence-first challenge may be useful despite one rejected witness.",
        "Do not tune against these 16 objects after external scoring.",
    ]
    lines = ["# Evidence-First Selective Candidate Analysis v0.22", ""]
    for title, values in (("Observations", observations), ("Interpretations", interpretations), ("Unknowns", unknowns), ("Intuition Triggers", intuition)):
        lines.extend((f"## {title}", ""))
        lines.extend(f"- {value}" for value in values)
        lines.append("")
    lines.extend(("State: `EVIDENCE_FIRST_SELECTIVE_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL`", ""))
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
