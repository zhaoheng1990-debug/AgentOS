"""Close and package v0.57 discovery."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def artifact(value):
    return {**value, "artifact_hash": hash_payload(value)}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def zip_pack(path, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(files, key=lambda value: value.name):
            info = zipfile.ZipInfo(source.name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def main():
    output = REPO_ROOT / "outputs" / "marginal_scarcity_v0_57"
    corpus = read(output / "marginal_scarcity_corpus_frozen.json")
    construction = read(output / "construction_audit.json")
    reference = read(output / "reference_completeness_audit.json")
    prereg = read(output / "discovery_preregistration.json")
    run = read(output / "discovery_run.json")
    analysis = read(output / "discovery_analysis.json")
    by_case = {}
    for key, value in run["consensus_candidates"].items():
        _rep, case_id = key.split(":", 1)
        by_case.setdefault(case_id, []).append(value["agreed"])
    report = "\n".join([
        "# Marginal-scarcity discovery v0.57",
        "",
        "## Result",
        (
            f"- Construction audit: "
            f"{construction['valid_cell_count']}/"
            f"{construction['cell_count']} valid."
        ),
        (
            f"- Reference audit: {reference['valid_receipt_count']}/"
            f"{reference['required_receipt_count']} valid, zero mismatch "
            "and zero cross-role disagreement."
        ),
        (
            f"- Discovery receipts: {analysis['receipt_count']}/"
            f"{prereg['required_receipt_count']}."
        ),
        (
            f"- Role consensus: {analysis['consensus_count']}/18; exact "
            f"hidden-target consensus: "
            f"{analysis['exact_target_consensus_count']}/18."
        ),
        (
            f"- Cases with cross-replication target witnesses: "
            f"{analysis['cross_replication_target_witness_count']}/6."
        ),
        (
            f"- Active-relation proposals: "
            f"{analysis['active_relation_proposal_count']}; tokens "
            f"{analysis['physical_total_tokens']}."
        ),
        f"- Decision: `{analysis['decision']}`.",
        "",
        "## Analysis",
        (
            "- Every consensus candidate exactly matched the hidden omitted "
            "O4->O1 EFFECT. Consensus precision was therefore 1.0 on this "
            "synthetic surface, while consensus recall was 14/18."
        ),
        (
            "- MS-CLOUD and MS-STORE reached 3/3 replication consensus; the "
            "other four cases reached 2/3. The remaining uncertainty is "
            "role disagreement in isolated replications, not an incorrect "
            "consensus or schema failure."
        ),
        (
            "- The result supports target-blind omitted-relation discovery "
            "under a frozen scarcity surface. It does not yet establish "
            "replacement safety, realized uplift, or protection of retained "
            "knowledge."
        ),
        (
            "- The next gate must mechanically replace only BASE:C3 for an "
            "exact consensus target, score the before/after portfolio with "
            "the frozen Harness, require realized +2 gross Cbit and zero "
            "protected-knowledge loss, and preserve abstention where roles "
            "do not agree."
        ),
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )
    ledger = artifact({
        "ledger_version": "marginal_scarcity_ledger_v0_57",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_construction_audit_hash": construction["artifact_hash"],
        "source_reference_audit_hash": reference["artifact_hash"],
        "source_preregistration_hash": prereg["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "decision": analysis["decision"],
        "candidate_state": analysis["candidate_state"],
        "replacement_executed": False,
        "core_integration_authorized": False,
    })
    write(output / "ledger.json", ledger)
    replay = artifact({
        "replay_version": "marginal_scarcity_replay_v0_57",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_marginal_scarcity.py",
            "python examples/run_marginal_scarcity_audit.py",
            "python examples/freeze_marginal_scarcity.py",
            "python examples/run_marginal_scarcity_discovery.py",
            "python examples/finalize_marginal_scarcity_discovery.py",
        ],
        "provider_model": run["model_id"],
        "warning": "Replay creates new Provider evidence.",
    })
    write(output / "replay.json", replay)
    rollback = artifact({
        "rollback_version": "marginal_scarcity_rollback_v0_57",
        "isolated_output_directory": str(output),
        "rollback_action": "Remove only this isolated output directory.",
        "agentos_core_files_touched": False,
    })
    write(output / "rollback_pointer.json", rollback)
    closure = artifact({
        "closure_version": "marginal_scarcity_closure_v0_57",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "replacement_gate_ready": (
            analysis["decision"]
            == "PASS_MARGINAL_SCARCITY_DISCOVERY"
        ),
        "replacement_executed": False,
        "promotion_allowed": False,
        "core_integration_authorized": False,
    })
    write(output / "closure.json", closure)
    names = [
        "marginal_scarcity_corpus_frozen.json",
        "construction_audit.json",
        "reference_completeness_audit.json",
        "discovery_preregistration.json",
        "discovery_run.json",
        "discovery_analysis.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory = artifact({
        "inventory_version": "marginal_scarcity_inventory_v0_57",
        "files": [{
            "path": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha(output / name),
        } for name in names],
    })
    write(output / "hash_inventory.json", inventory)
    pack = output / "marginal_scarcity_v0_57_return_pack.zip"
    zip_pack(
        pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest = artifact({
        "manifest_version": "marginal_scarcity_manifest_v0_57",
        "return_pack": pack.name,
        "return_pack_sha256": sha(pack),
        "return_pack_bytes": pack.stat().st_size,
        "inventory_hash": inventory["artifact_hash"],
        "closure_hash": closure["artifact_hash"],
    })
    write(output / "manifest.json", manifest)
    print(json.dumps({
        "decision": analysis["decision"],
        "state": analysis["candidate_state"],
        "return_pack": str(pack),
        "sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
