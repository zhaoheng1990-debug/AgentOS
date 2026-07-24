"""Freeze v0.19 candidate analysis and external panel packs."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_evidence_holdout import CASES  # noqa: E402
from local_collective_cognition.cognitive_action_evidence_panel import build_evidence_external_panel, validate_evidence_external_panel  # noqa: E402
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
    output = REPO_ROOT / "outputs" / "evidence_state_calibration_v0_19"
    corpus = read(output / "evidence_fresh_corpus_frozen.json")
    prereg = read(output / "evidence_preregistration.json")
    run = read(output / "evidence_calibration_run.json")
    analysis = read(output / "evidence_calibration_analysis.json")
    report_path = output / "EVIDENCE_STATE_CALIBRATION_ANALYSIS.md"
    report_path.write_text(render_analysis(corpus, run, analysis), encoding="utf-8")
    packs, panel_manifest = build_evidence_external_panel(corpus=corpus, run=run)
    validate_evidence_external_panel(packs=packs, manifest=panel_manifest)
    panel_dir = output / "external_panel"
    panel_dir.mkdir(exist_ok=True)
    lane_names = []
    for pack in packs:
        name = f"{pack['lane_id'].lower()}_evidence_annotation_pack.json"
        write(panel_dir / name, pack)
        lane_names.append(name)
    write(panel_dir / "evidence_external_panel_manifest.json", panel_manifest)
    ledger_commitment = {
        "ledger_version": "evidence_state_calibration_phase_ledger_v0_19",
        "phases": [
            {"phase": "G0_PREREGISTRATION", "status": "PASS", "hash": prereg["artifact_hash"]},
            {"phase": "G1_FRESH_HOLDOUT", "status": "PASS", "hash": corpus["artifact_hash"]},
            {"phase": "G2_BLIND_ARMS", "status": "PASS_STRUCTURAL_PENDING_EXTERNAL_PANEL", "coverage": analysis["coverage"], "failures": len(run["failures"])},
            {"phase": "G3_EXTERNAL_REFERENCE", "status": "PENDING", "panel_id": panel_manifest["panel_id"]},
        ],
        "baseline_insertion": "No Baseline Object Update; experiment candidate only",
    }
    ledger = {**ledger_commitment, "artifact_hash": hash_payload(ledger_commitment)}
    write(output / "phase_ledger.json", ledger)
    replay_commitment = {
        "pointer_version": "evidence_state_calibration_replay_v0_19",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_evidence_calibration.py",
            "python examples/run_evidence_calibration.py",
            "python examples/finalize_evidence_calibration.py",
        ],
        "reference_revision_allowed": False,
    }
    replay = {**replay_commitment, "artifact_hash": hash_payload(replay_commitment)}
    write(output / "replay_pointer.json", replay)
    rollback_commitment = {
        "pointer_version": "evidence_state_calibration_rollback_v0_19",
        "scope": "experiment-only; CoreSlim excluded",
        "rollback_action": "quarantine v0.19 code and outputs after hash verification",
        "automatic_rollback_executed": False,
    }
    rollback = {**rollback_commitment, "artifact_hash": hash_payload(rollback_commitment)}
    write(output / "rollback_pointer.json", rollback)
    names = [
        "evidence_preregistration.json", "evidence_fresh_corpus_frozen.json",
        "evidence_calibration_run.json", "evidence_calibration_analysis.json",
        "evidence_calibration_telemetry.json", report_path.name,
        "phase_ledger.json", "replay_pointer.json", "rollback_pointer.json",
        *[f"external_panel/{name}" for name in lane_names],
        "external_panel/evidence_external_panel_manifest.json",
    ]
    inventory_commitment = {
        "inventory_version": "evidence_state_calibration_hash_inventory_v0_19",
        "items": [{"path": name, "size_bytes": (output / name).stat().st_size, "sha256": sha256_file(output / name)} for name in names],
    }
    inventory = {**inventory_commitment, "artifact_hash": hash_payload(inventory_commitment)}
    write(output / "hash_inventory.json", inventory)
    manifest_commitment = {
        "manifest_version": "evidence_state_calibration_manifest_v0_19",
        "preregistration_hash": prereg["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "inventory_hash": inventory["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "baseline_promotion_allowed": False,
        "retention_write_allowed": False,
    }
    manifest = {**manifest_commitment, "artifact_hash": hash_payload(manifest_commitment)}
    write(output / "manifest.json", manifest)
    pack_path = output / "evidence_state_calibration_external_panel_v0_19.zip"
    with zipfile.ZipFile(pack_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in lane_names:
            archive.write(panel_dir / name, arcname=name)
        archive.write(panel_dir / "evidence_external_panel_manifest.json", arcname="PRIVATE_evidence_external_panel_manifest.json")
        archive.write(report_path, arcname=report_path.name)
    print(json.dumps({
        "panel_id": panel_manifest["panel_id"],
        "lane_pack_hashes": panel_manifest["lane_pack_hashes"],
        "manifest_hash": manifest["artifact_hash"],
        "inventory_hash": inventory["artifact_hash"],
        "return_pack": str(pack_path),
        "return_pack_sha256": sha256_file(pack_path),
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


def render_analysis(corpus, run, analysis):
    case_by_id = {case.case_id: case for case in CASES}
    bindings = corpus["private_provenance"]["bindings"]
    outputs = {arm: Counter() for arm in ("FREE_LABEL_CONTROL", "CONTRASTIVE_SOURCE_CALIBRATOR")}
    sources = {}
    for output in run["outputs"]:
        case = case_by_id[bindings[output["conflict_id"]]["case_id"]]
        outputs[output["arm"]][(case.design_stratum, output["payload"]["evidence_state"])] += 1
        if output["definition_source_receipt"]:
            sources[output["conflict_id"]] = output["definition_source_receipt"]["definition_source"]
    observations = [
        f"Arm coverage is {analysis['coverage']} with {len(run['failures'])} rejected outputs.",
        f"Evidence-state distributions are {analysis['evidence_state_distributions']}.",
        f"Definition-source distribution is {analysis['definition_source_distribution']}.",
        f"Posthoc design diagnostics, not truth labels, are { {arm: {str(key): value for key, value in counts.items()} for arm, counts in outputs.items()} }.",
        f"Calibrator/control token ratio is {analysis['calibrator_to_control_token_ratio']}.",
    ]
    interpretations = [
        "The contrastive source representation partially breaks the control arm's direct-definition collapse.",
        "Three soft and five opaque outputs are now exposed, but coverage and remaining direct over-promotion prevent a gain claim.",
        "Runtime coherence rejection remains active; no cross-arm substitution repaired the seven failed objects.",
    ]
    unknowns = [
        "External labels are required for admission precision, soft recall, evidence accuracy, and selected-object loss.",
        "The hidden construction strata are design commitments rather than semantic reference truth.",
    ]
    intuition = [
        "If external recall improves, definition source is a better gating primitive than free evidence-state labels.",
        "If soft cases remain direct, the next change should challenge explicit-definition evidence rather than add more source categories.",
    ]
    lines = ["# Evidence-State Calibration v0.19 Candidate Analysis", ""]
    for title, values in (("Observations", observations), ("Interpretations", interpretations), ("Unknowns", unknowns), ("Intuition Triggers", intuition)):
        lines.extend((f"## {title}", "", *[f"- {value}" for value in values], ""))
    lines.extend(("State: `EVIDENCE_CALIBRATION_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL`", ""))
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
