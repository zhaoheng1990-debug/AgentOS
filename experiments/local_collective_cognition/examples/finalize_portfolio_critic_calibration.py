"""Close and package the v0.60 PortfolioCritic calibration."""

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


def main():
    source = (
        REPO_ROOT / "outputs" / "marginal_scarcity_transfer_v0_59_1"
    )
    output = (
        REPO_ROOT / "outputs" / "portfolio_critic_calibration_v0_60"
    )
    preregistration = read(output / "preregistration.json")
    critic = read(output / "portfolio_critic_receipts.json")
    run = read(output / "kernel_displacement_run.json")
    analysis = read(output / "analysis.json")
    source_closure = read(source / "closure.json")
    write(output / "source_transfer_closure.json", source_closure)
    replacements = [
        value for value in analysis["cells"]
        if value["state"] == "REPLACED_MECHANISM_CALIBRATION_ONLY"
    ]
    corrected = [
        value for value in replacements
        if value["corrective_override"]
    ]
    report = "\n".join([
        "# PortfolioCritic mechanism calibration v0.60",
        "",
        "## Result",
        f"- Decision: `{analysis['decision']}`.",
        (
            f"- Critic cases: {critic['critic_case_count']}/"
            f"{preregistration['required_critic_case_count']}; source "
            f"Provider receipts: {critic['source_provider_receipt_count']}."
        ),
        (
            f"- Candidate replacements: "
            f"{analysis['replacement_count']}; nonconsensus abstentions: "
            f"{analysis['abstention_count']}."
        ),
        (
            f"- Corrective Kernel overrides: "
            f"{analysis['corrective_override_count']}."
        ),
        (
            f"- Target-position coverage: "
            f"{analysis['target_position_coverage']}/5; drop-pool "
            f"coverage: {analysis['drop_pool_coverage']}/3."
        ),
        (
            f"- Realized gross Cbit mean/median: "
            f"{analysis['realized_gross_cbit_mean']:.1f}/"
            f"{analysis['realized_gross_cbit_median']:.1f}."
        ),
        (
            f"- Harmful replacements: "
            f"{analysis['harmful_replacement_count']}; protected losses: "
            f"{analysis['protected_knowledge_loss_count']}; critic "
            f"conflicts: {analysis['critic_conflict_count']}."
        ),
        "- New Provider calls: 0.",
        "- Fresh-generalization claim: false.",
        "",
        "## Corrected cells",
        *[
            (
                f"- {value['replication_id']}:{value['case_id']}: "
                f"{value['advisory_discovery_drop_pool_id']} -> "
                f"{value['kernel_selected_drop_pool_id']}."
            )
            for value in corrected
        ],
        "",
        "## Interpretation",
        (
            "- v0.59.1 combined target discovery and displacement choice "
            "inside one semantic receipt. v0.60 treats the proposed drop "
            "as advisory, aggregates two existing context-isolated "
            "Provider judgments for every active relation, and lets the "
            "Kernel select only a unique UNRESOLVED slot."
        ),
        (
            "- The repair is Provider-backed rather than Provider-free. "
            "It reuses twelve semantic reference receipts and the frozen "
            "discovery receipts; zero new calls means no posthoc semantic "
            "retuning, not absence of Provider cognition."
        ),
        (
            "- All six prior wrong-drop consensuses were corrected without "
            "changing target candidates or consulting private truth during "
            "selection. A reference-role conflict would block the whole "
            "case rather than be averaged away."
        ),
        (
            "- This revealed-data calibration supports the decomposition "
            "mechanism only. A new holdout must freeze this architecture "
            "before labels and test both target discovery and critic-backed "
            "displacement end to end."
        ),
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )
    ledger = artifact({
        "ledger_version": "portfolio_critic_ledger_v0_60",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_critic_artifact_hash": critic["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "decision": analysis["decision"],
        "candidate_state": analysis["candidate_state"],
        "new_provider_calls": 0,
        "fresh_generalization_claim": False,
        "core_integration_authorized": False,
    })
    write(output / "ledger.json", ledger)
    replay = artifact({
        "replay_version": "portfolio_critic_replay_v0_60",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/run_portfolio_critic_calibration.py",
            "python examples/finalize_portfolio_critic_calibration.py",
        ],
        "warning": (
            "Replay is deterministic and reuses frozen Provider receipts."
        ),
    })
    write(output / "replay.json", replay)
    rollback = artifact({
        "rollback_version": "portfolio_critic_rollback_v0_60",
        "isolated_output_directory": str(output),
        "rollback_action": "Remove only this isolated output directory.",
        "agentos_core_files_touched": False,
    })
    write(output / "rollback_pointer.json", rollback)
    closure = artifact({
        "closure_version": "portfolio_critic_closure_v0_60",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "decomposition_mechanism_supported": True,
        "fresh_holdout_required": True,
        "fresh_generalization_claim": False,
        "promotion_allowed": False,
        "core_integration_authorized": False,
    })
    write(output / "closure.json", closure)
    names = [
        "source_transfer_closure.json",
        "preregistration.json",
        "portfolio_critic_receipts.json",
        "kernel_displacement_run.json",
        "analysis.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory = artifact({
        "inventory_version": "portfolio_critic_inventory_v0_60",
        "files": [{
            "path": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha(output / name),
        } for name in names],
    })
    write(output / "hash_inventory.json", inventory)
    pack = output / "portfolio_critic_calibration_v0_60.zip"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(names + ["hash_inventory.json"]):
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (output / name).read_bytes())
    manifest = artifact({
        "manifest_version": "portfolio_critic_manifest_v0_60",
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
        "corrective_overrides": len(corrected),
        "return_pack": str(pack),
        "sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
