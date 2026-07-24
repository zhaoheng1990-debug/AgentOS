"""Close and package the rejected v0.59/v0.59.1 transfer experiment."""

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
    initial = REPO_ROOT / "outputs" / "marginal_scarcity_transfer_v0_59"
    output = (
        REPO_ROOT / "outputs" / "marginal_scarcity_transfer_v0_59_1"
    )
    initial_corpus = read(initial / "transfer_corpus_frozen.json")
    initial_reference = read(
        initial / "reference_completeness_audit.json"
    )
    corpus = read(output / "transfer_corpus_frozen.json")
    construction = read(output / "construction_audit.json")
    reference = read(output / "reference_completeness_audit.json")
    preregistration = read(output / "transfer_preregistration.json")
    run = read(output / "discovery_run.json")
    analysis = read(output / "discovery_analysis.json")
    write(output / "v0_59_initial_corpus.json", initial_corpus)
    write(
        output / "v0_59_initial_reference_failure.json",
        initial_reference,
    )
    repair = artifact({
        "repair_version": "marginal_scarcity_transfer_repair_v0_59_1",
        "source_failed_corpus_hash": initial_corpus["artifact_hash"],
        "source_failed_reference_hash": initial_reference["artifact_hash"],
        "repaired_corpus_hash": corpus["artifact_hash"],
        "repaired_reference_hash": reference["artifact_hash"],
        "changed_evidence_coordinates": [
            "MT-CROP:S3",
            "MT-ORBIT:S4",
        ],
        "hidden_target_changed": False,
        "designed_drop_changed": False,
        "portfolio_changed": False,
        "gate_changed": False,
        "initial_reference_mismatch_count": len(
            initial_reference["reference_mismatches"]
        ),
        "initial_reference_disagreement_count": len(
            initial_reference["cross_role_disagreements"]
        ),
        "repaired_reference_complete": reference["reference_complete"],
    })
    write(output / "repair_lineage.json", repair)
    agreed = [
        value for value in analysis["cells"] if value["agreed"]
    ]
    wrong_drop = sum(
        value["target_match"] and not value["drop_match"]
        for value in agreed
    )
    nonconsensus = len(analysis["cells"]) - len(agreed)
    failed = [
        key for key, value in analysis["conditions"].items()
        if not value
    ]
    report = "\n".join([
        "# Marginal-scarcity fresh transfer v0.59.1",
        "",
        "## Construction lineage",
        (
            "- The initial v0.59 reference gate produced 12/12 valid "
            "receipts but three private-reference mismatches and one "
            "cross-role disagreement. Formal discovery did not run."
        ),
        (
            "- v0.59.1 changed only MT-CROP:S3 and MT-ORBIT:S4 to bind "
            "the focal outcome and distinguish absence of evidence from "
            "evidence of null. Hidden targets, drop pools, portfolios, "
            "roles, and gates remained frozen."
        ),
        (
            f"- The repaired reference gate passed "
            f"{reference['valid_receipt_count']}/"
            f"{reference['required_receipt_count']} with zero mismatch "
            "and zero disagreement."
        ),
        "",
        "## Formal result",
        f"- Decision: `{analysis['decision']}`.",
        (
            f"- Receipts: {analysis['receipt_count']}/"
            f"{preregistration['required_receipt_count']}; role consensus "
            f"{analysis['consensus_count']}/18."
        ),
        (
            f"- Exact hidden-target consensus: "
            f"{analysis['exact_target_consensus_count']}/18; wrong-target "
            f"consensus: {analysis['wrong_target_consensus_count']}."
        ),
        (
            f"- Target-source position coverage: "
            f"{analysis['target_source_position_coverage']}/5 "
            f"({', '.join(analysis['covered_target_source_positions'])})."
        ),
        (
            f"- Exact target-and-drop consensus: "
            f"{analysis['exact_target_and_drop_consensus_count']}/18; "
            f"wrong-drop exact-target consensus: {wrong_drop}."
        ),
        (
            f"- Correct drop-pool coverage: "
            f"{analysis['drop_pool_coverage']}/3 "
            f"({', '.join(analysis['covered_drop_pool_ids'])})."
        ),
        (
            f"- Nonconsensus cells: {nonconsensus}; Provider tokens: "
            f"{analysis['physical_total_tokens']}."
        ),
        f"- Failed frozen conditions: `{', '.join(failed)}`.",
        "- Replacement was not run and no mutation was authorized.",
        "",
        "## Interpretation",
        (
            "- Omitted-relation discovery generalized beyond the fixed "
            "O4->O1 target: every one of fourteen consensuses was correct "
            "and all five target positions were recovered."
        ),
        (
            "- Displacement selection did not generalize. BASE:C3 was "
            "never correctly selected when it held the unresolved active "
            "relation, despite successful selection of BASE:C1 and "
            "BASE:C2 elsewhere."
        ),
        (
            "- Several receipts named the weak active relation in their "
            "rationale but emitted a different drop pool. This is evidence "
            "that target discovery and displacement selection should be "
            "separate cognitive actions with separately validated receipts."
        ),
        (
            "- The next experiment should keep the fourteen frozen target "
            "consensuses and test a dedicated, reference-backed portfolio "
            "critic against a mechanical Kernel safety gate. It must not "
            "rerun or retune the revealed target labels."
        ),
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )
    ledger = artifact({
        "ledger_version": "marginal_scarcity_transfer_ledger_v0_59_1",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_construction_audit_hash": construction["artifact_hash"],
        "source_reference_audit_hash": reference["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_repair_hash": repair["artifact_hash"],
        "decision": analysis["decision"],
        "candidate_state": analysis["candidate_state"],
        "replacement_executed": False,
        "core_integration_authorized": False,
    })
    write(output / "ledger.json", ledger)
    replay = artifact({
        "replay_version": "marginal_scarcity_transfer_replay_v0_59_1",
        "working_directory": str(PACK_ROOT),
        "environment": {
            "AGENTOS_TRANSFER_REVISION": "v0_59_1",
        },
        "commands": [
            "python examples/prepare_marginal_scarcity_transfer.py",
            "python examples/run_marginal_scarcity_transfer_audit.py",
            "python examples/freeze_marginal_scarcity_transfer.py",
            "python examples/run_marginal_scarcity_transfer.py",
            "python examples/finalize_marginal_scarcity_transfer.py",
        ],
        "provider_model": run["model_id"],
        "warning": "Replay creates new Provider evidence.",
    })
    write(output / "replay.json", replay)
    rollback = artifact({
        "rollback_version": (
            "marginal_scarcity_transfer_rollback_v0_59_1"
        ),
        "isolated_output_directory": str(output),
        "rollback_action": "Remove only this isolated output directory.",
        "agentos_core_files_touched": False,
    })
    write(output / "rollback_pointer.json", rollback)
    closure = artifact({
        "closure_version": (
            "marginal_scarcity_transfer_closure_v0_59_1"
        ),
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "target_discovery_transfer_supported": True,
        "displacement_selection_transfer_supported": False,
        "replacement_executed": False,
        "promotion_allowed": False,
        "core_integration_authorized": False,
    })
    write(output / "closure.json", closure)
    names = [
        "v0_59_initial_corpus.json",
        "v0_59_initial_reference_failure.json",
        "transfer_corpus_frozen.json",
        "construction_audit.json",
        "construction_closure.json",
        "reference_completeness_audit.json",
        "transfer_preregistration.json",
        "discovery_run.json",
        "discovery_analysis.json",
        "repair_lineage.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory = artifact({
        "inventory_version": (
            "marginal_scarcity_transfer_inventory_v0_59_1"
        ),
        "files": [{
            "path": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha(output / name),
        } for name in names],
    })
    write(output / "hash_inventory.json", inventory)
    pack = output / "marginal_scarcity_transfer_v0_59_1.zip"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(names + ["hash_inventory.json"]):
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (output / name).read_bytes())
    manifest = artifact({
        "manifest_version": (
            "marginal_scarcity_transfer_manifest_v0_59_1"
        ),
        "return_pack": pack.name,
        "return_pack_sha256": sha(pack),
        "return_pack_bytes": pack.stat().st_size,
        "inventory_hash": inventory["artifact_hash"],
        "closure_hash": closure["artifact_hash"],
    })
    write(output / "manifest.json", manifest)
    print(json.dumps({
        "decision": analysis["decision"],
        "target_discovery_transfer_supported": True,
        "displacement_selection_transfer_supported": False,
        "return_pack": str(pack),
        "sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
