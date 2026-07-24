"""Close and package the v0.61/v0.61.1 reference-gate rejection."""

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
    initial = REPO_ROOT / "outputs" / "portfolio_critic_fresh_v0_61"
    output = REPO_ROOT / "outputs" / "portfolio_critic_fresh_v0_61_1"
    initial_corpus = read(initial / "fresh_corpus_frozen.json")
    initial_construction = read(initial / "construction_audit.json")
    initial_reference = read(
        initial / "reference_completeness_audit.json"
    )
    repaired_corpus = read(output / "fresh_corpus_frozen.json")
    repaired_construction = read(output / "construction_audit.json")
    repaired_reference = read(
        output / "reference_completeness_audit.json"
    )
    write(output / "v0_61_initial_corpus.json", initial_corpus)
    write(
        output / "v0_61_initial_construction_audit.json",
        initial_construction,
    )
    write(
        output / "v0_61_initial_reference_failure.json",
        initial_reference,
    )
    repair = artifact({
        "repair_version": "portfolio_critic_fresh_repair_v0_61_1",
        "source_failed_corpus_hash": initial_corpus["artifact_hash"],
        "source_failed_reference_hash": initial_reference["artifact_hash"],
        "repaired_corpus_hash": repaired_corpus["artifact_hash"],
        "repaired_reference_hash": repaired_reference["artifact_hash"],
        "changed_evidence_coordinates": [
            "PC-GENOME:S3",
            "PC-TRAFFIC:S2",
        ],
        "hidden_targets_changed": False,
        "topologies_changed": False,
        "portfolios_changed": False,
        "expected_actions_changed": False,
        "gates_changed": False,
        "initial_mismatch_count": len(
            initial_reference["reference_mismatches"]
        ),
        "initial_disagreement_count": len(
            initial_reference["cross_role_disagreements"]
        ),
        "repaired_mismatch_count": len(
            repaired_reference["reference_mismatches"]
        ),
        "repaired_disagreement_count": len(
            repaired_reference["cross_role_disagreements"]
        ),
        "further_repair_allowed": False,
    })
    write(output / "repair_lineage.json", repair)
    mismatches = repaired_reference["reference_mismatches"]
    report = "\n".join([
        "# Fresh PortfolioCritic holdout v0.61.1",
        "",
        "## Construction",
        (
            f"- Six fresh cases passed "
            f"{repaired_construction['valid_cell_count']}/"
            f"{repaired_construction['cell_count']} mechanical checks."
        ),
        (
            "- UNIQUE_UNRESOLVED, NO_UNRESOLVED, and "
            "MULTIPLE_UNRESOLVED topologies each have two cases; hidden "
            "target sources cover O2 through O6."
        ),
        (
            "- Target-only discovery, PortfolioCritic aggregation, and "
            "selective Kernel action contracts were implemented and unit "
            "tested before formal Provider execution."
        ),
        "",
        "## Reference-gate lineage",
        (
            "- Initial v0.61: 12/12 contract-valid reference receipts, "
            "three private-reference mismatches, and one cross-role "
            "disagreement. Formal discovery did not run."
        ),
        (
            "- v0.61.1 changed only PC-GENOME:S3 and PC-TRAFFIC:S2 to "
            "bind each intervention explicitly to its focal outcome. No "
            "target, topology, portfolio, expected action, or gate changed."
        ),
        (
            "- Repaired v0.61.1: 12/12 contract-valid receipts and zero "
            "cross-role disagreement, but two remaining mismatches."
        ),
        *[
            (
                f"- {value['role']} classified "
                f"{value['case_id']}:{value['relation_id']} as "
                f"{value['observed_state']} instead of "
                f"{value['expected_state']}."
            )
            for value in mismatches
        ],
        "",
        "## Decision",
        "- Decision: `REJECT_FRESH_PORTFOLIO_REFERENCE_GATE`.",
        (
            "- Candidate state: "
            "`REFERENCE_SEMANTIC_SUPPORT_INSUFFICIENT_STOP`."
        ),
        "- Target discovery and Kernel actions were not run.",
        "- No third construction repair is allowed on these revealed cases.",
        "- No Core, retention, baseline, selection, or production authority.",
        "",
        "## Interpretation",
        (
            "- Both repaired reference roles treated a matched demand-regime "
            "intervention as insufficiently bound to object O3, even though "
            "the span states that it removed corridor-delay drift. Runtime "
            "cannot override that Provider-backed uncertainty with private "
            "construction truth."
        ),
        (
            "- This rejects the current reference semantic support, not the "
            "target-only or three-topology architecture, which never reached "
            "formal execution."
        ),
        (
            "- The next high-Cbit calibration should separate relation-"
            "evidence object binding from truth-state assessment. A Provider "
            "must first emit an explicit source-object, target-object, "
            "intervention, and outcome binding receipt; only a second role "
            "may classify EFFECT, NULL, or UNRESOLVED."
        ),
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )
    ledger = artifact({
        "ledger_version": "portfolio_critic_fresh_ledger_v0_61_1",
        "source_initial_corpus_hash": initial_corpus["artifact_hash"],
        "source_initial_reference_hash": initial_reference["artifact_hash"],
        "source_repaired_corpus_hash": repaired_corpus["artifact_hash"],
        "source_repaired_reference_hash": repaired_reference[
            "artifact_hash"
        ],
        "source_repair_hash": repair["artifact_hash"],
        "decision": "REJECT_FRESH_PORTFOLIO_REFERENCE_GATE",
        "candidate_state": "REFERENCE_SEMANTIC_SUPPORT_INSUFFICIENT_STOP",
        "formal_target_discovery_executed": False,
        "kernel_actions_executed": False,
        "core_integration_authorized": False,
    })
    write(output / "ledger.json", ledger)
    replay = artifact({
        "replay_version": "portfolio_critic_fresh_replay_v0_61_1",
        "working_directory": str(PACK_ROOT),
        "environment": {"AGENTOS_PORTFOLIO_REVISION": "v0_61_1"},
        "commands": [
            "python examples/prepare_portfolio_critic_fresh.py",
            "python examples/run_portfolio_critic_fresh_audit.py",
            "python examples/finalize_portfolio_critic_fresh_rejection.py",
        ],
        "warning": "Replay creates new Provider reference evidence.",
    })
    write(output / "replay.json", replay)
    rollback = artifact({
        "rollback_version": "portfolio_critic_fresh_rollback_v0_61_1",
        "isolated_output_directory": str(output),
        "rollback_action": "Remove only this isolated output directory.",
        "agentos_core_files_touched": False,
    })
    write(output / "rollback_pointer.json", rollback)
    closure = artifact({
        "closure_version": "portfolio_critic_fresh_closure_v0_61_1",
        "source_ledger_hash": ledger["artifact_hash"],
        "decision": ledger["decision"],
        "candidate_state": ledger["candidate_state"],
        "object_evidence_binding_calibration_required": True,
        "formal_target_discovery_executed": False,
        "fresh_generalization_claim": False,
        "promotion_allowed": False,
        "core_integration_authorized": False,
    })
    write(output / "closure.json", closure)
    names = [
        "v0_61_initial_corpus.json",
        "v0_61_initial_construction_audit.json",
        "v0_61_initial_reference_failure.json",
        "fresh_corpus_frozen.json",
        "construction_audit.json",
        "construction_closure.json",
        "reference_completeness_audit.json",
        "repair_lineage.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory = artifact({
        "inventory_version": "portfolio_critic_fresh_inventory_v0_61_1",
        "files": [{
            "path": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha(output / name),
        } for name in names],
    })
    write(output / "hash_inventory.json", inventory)
    pack = output / "portfolio_critic_fresh_v0_61_1.zip"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(names + ["hash_inventory.json"]):
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (output / name).read_bytes())
    manifest = artifact({
        "manifest_version": "portfolio_critic_fresh_manifest_v0_61_1",
        "return_pack": pack.name,
        "return_pack_sha256": sha(pack),
        "return_pack_bytes": pack.stat().st_size,
        "inventory_hash": inventory["artifact_hash"],
        "closure_hash": closure["artifact_hash"],
    })
    write(output / "manifest.json", manifest)
    print(json.dumps({
        "decision": ledger["decision"],
        "state": ledger["candidate_state"],
        "remaining_mismatches": len(mismatches),
        "formal_target_discovery_executed": False,
        "return_pack": str(pack),
        "sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
