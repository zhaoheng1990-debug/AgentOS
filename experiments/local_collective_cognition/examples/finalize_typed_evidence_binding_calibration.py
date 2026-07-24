"""Close and package the v0.63 typed evidence-binding calibration."""

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
    predecessor = (
        REPO_ROOT / "outputs" / "relation_evidence_binding_v0_62_1"
    )
    output = REPO_ROOT / "outputs" / "typed_evidence_binding_v0_63"
    preregistration = read(output / "preregistration.json")
    binding = read(output / "binding_run.json")
    source_closure = read(predecessor / "closure.json")
    state_path = output / "state_run.json"
    analysis_path = output / "analysis.json"
    state = read(state_path) if state_path.exists() else None
    analysis = read(analysis_path) if analysis_path.exists() else None
    if analysis is not None:
        decision = analysis["decision"]
        candidate_state = analysis["candidate_state"]
        core_eligible = analysis["core_contract_sync_eligible"]
    else:
        decision = "REJECT_TYPED_EVIDENCE_BINDING_CONSENSUS_GATE"
        candidate_state = "TYPED_BINDING_CONSENSUS_INSUFFICIENT_STOP"
        core_eligible = False
    lineage = artifact({
        "lineage_version": "typed_evidence_binding_lineage_v0_63",
        "source_v0_62_1_closure_hash": source_closure["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_binding_run_hash": binding["run_hash"],
        "source_state_run_hash": state["run_hash"] if state else None,
        "source_analysis_hash": (
            analysis["artifact_hash"] if analysis else None
        ),
        "corpus_changed": False,
        "revealed_mechanism_calibration_only": True,
        "truth_labels_exposed_to_provider": False,
    })
    write(output / "lineage.json", lineage)
    report_lines = [
        "# Typed evidence-binding calibration v0.63",
        "",
        "## Frozen mechanism",
        (
            "- Binding roles separately emit primary, corroborating, "
            "counterevidence, and gap spans without truth-state authority."
        ),
        (
            "- Primary evidence requires strict cross-role set equality. "
            "Nonconflicting auxiliary evidence is retained as a typed union; "
            "cross-type disagreement blocks the relation."
        ),
        (
            "- State assessment runs only after complete binding consensus "
            "and must cite every admitted primary span."
        ),
        "",
        "## Binding result",
        (
            f"- Receipts: {len(binding['raw_receipts'])}/"
            f"{preregistration['required_binding_receipt_count']}; relation "
            f"consensus: {binding['binding_relation_consensus_count']}/"
            f"{preregistration['required_binding_relation_consensus_count']}."
        ),
        (
            f"- Conflicts: {len(binding['binding_conflicts'])}; contract "
            f"failures: {len(binding['contract_failures'])}; auxiliary "
            f"divergences retained: "
            f"{len(binding['auxiliary_evidence_divergences'])}."
        ),
    ]
    if analysis is not None and state is not None:
        report_lines.extend([
            "",
            "## State result",
            (
                f"- Receipts: {analysis['state_receipt_count']}/"
                f"{preregistration['required_state_receipt_count']}; "
                f"contract failures: {len(state['contract_failures'])}."
            ),
            (
                f"- Reference mismatches: "
                f"{len(analysis['state_reference_mismatches'])}; cross-role "
                f"disagreements: "
                f"{len(analysis['state_cross_role_disagreements'])}."
            ),
            (
                f"- Required PC-TRAFFIC REL-O3-O1 recovery: "
                f"{analysis['required_coordinate_recovered']}."
            ),
            (
                f"- Provider calls: {analysis['provider_call_count']}; "
                f"physical tokens: {analysis['physical_total_tokens']}."
            ),
        ])
    else:
        report_lines.extend([
            "",
            "## State result",
            "- State assessment was not executed because binding did not pass.",
        ])
    report_lines.extend([
        "",
        "## Decision",
        f"- Decision: `{decision}`.",
        f"- Candidate state: `{candidate_state}`.",
        (
            f"- AgentOS contract sync eligible: "
            f"`{str(core_eligible).lower()}`."
        ),
        "- No fresh-generalization, retention-write, or production authority.",
    ])
    (output / "experiment_report.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )
    ledger = artifact({
        "ledger_version": "typed_evidence_binding_ledger_v0_63",
        "source_lineage_hash": lineage["artifact_hash"],
        "decision": decision,
        "candidate_state": candidate_state,
        "state_assessment_executed": state is not None,
        "core_contract_sync_eligible": core_eligible,
        "fresh_generalization_claim": False,
        "retention_write_allowed": False,
        "production_authority": False,
    })
    write(output / "ledger.json", ledger)
    replay = artifact({
        "replay_version": "typed_evidence_binding_replay_v0_63",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/run_typed_evidence_binding_calibration.py",
            "python examples/finalize_typed_evidence_binding_calibration.py",
        ],
        "warning": "Replay creates new Provider receipts.",
    })
    write(output / "replay.json", replay)
    rollback = artifact({
        "rollback_version": "typed_evidence_binding_rollback_v0_63",
        "isolated_output_directory": str(output),
        "rollback_action": "Remove only this isolated output directory.",
        "agentos_core_files_touched": False,
    })
    write(output / "rollback_pointer.json", rollback)
    closure = artifact({
        "closure_version": "typed_evidence_binding_closure_v0_63",
        "source_ledger_hash": ledger["artifact_hash"],
        "decision": decision,
        "candidate_state": candidate_state,
        "core_contract_sync_eligible": core_eligible,
        "state_assessment_executed": state is not None,
        "fresh_generalization_claim": False,
        "promotion_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    })
    write(output / "closure.json", closure)
    names = [
        "preregistration.json",
        "binding_run.json",
        *(
            ["state_run.json", "analysis.json"]
            if state is not None and analysis is not None
            else []
        ),
        "lineage.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory = artifact({
        "inventory_version": "typed_evidence_binding_inventory_v0_63",
        "files": [{
            "path": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha(output / name),
        } for name in names],
    })
    write(output / "hash_inventory.json", inventory)
    pack = output / "typed_evidence_binding_v0_63.zip"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted([*names, "hash_inventory.json"]):
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (output / name).read_bytes())
    manifest = artifact({
        "manifest_version": "typed_evidence_binding_manifest_v0_63",
        "return_pack": pack.name,
        "return_pack_sha256": sha(pack),
        "return_pack_bytes": pack.stat().st_size,
        "inventory_hash": inventory["artifact_hash"],
        "closure_hash": closure["artifact_hash"],
    })
    write(output / "manifest.json", manifest)
    print(json.dumps({
        "decision": decision,
        "state": candidate_state,
        "core_contract_sync_eligible": core_eligible,
        "return_pack": str(pack),
        "sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
