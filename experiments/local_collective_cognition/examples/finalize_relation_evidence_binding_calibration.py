"""Close and package the v0.62/v0.62.1 binding-gate rejection."""

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
    initial = (
        REPO_ROOT / "outputs" / "relation_evidence_binding_v0_62"
    )
    output = (
        REPO_ROOT / "outputs" / "relation_evidence_binding_v0_62_1"
    )
    initial_preregistration = read(initial / "preregistration.json")
    initial_run = read(initial / "binding_run.json")
    preregistration = read(output / "preregistration.json")
    run = read(output / "binding_run.json")
    write(
        output / "v0_62_initial_preregistration.json",
        initial_preregistration,
    )
    write(output / "v0_62_initial_binding_run.json", initial_run)
    repair = artifact({
        "repair_version": "relation_evidence_binding_repair_v0_62_1",
        "source_initial_preregistration_hash": initial_preregistration[
            "artifact_hash"
        ],
        "source_initial_run_hash": initial_run["run_hash"],
        "repaired_preregistration_hash": preregistration["artifact_hash"],
        "repaired_run_hash": run["run_hash"],
        "corpus_changed": False,
        "truth_state_labels_exposed_to_provider": False,
        "repair_changes": [
            "EXACT_EXPLICIT and COREFERENCE are coarse BOUND equivalents",
            "Runtime derives binding_state from source and target binding",
        ],
        "initial_binding_receipt_count": len(
            initial_run["raw_receipts"]
        ),
        "initial_relation_consensus_count": initial_run[
            "binding_relation_consensus_count"
        ],
        "initial_conflict_count": len(initial_run["binding_conflicts"]),
        "initial_contract_failure_count": len(
            initial_run["contract_failures"]
        ),
        "repaired_binding_receipt_count": len(run["raw_receipts"]),
        "repaired_relation_consensus_count": run[
            "binding_relation_consensus_count"
        ],
        "repaired_conflict_count": len(run["binding_conflicts"]),
        "repaired_contract_failure_count": len(run["contract_failures"]),
        "repaired_subtype_divergence_count": len(
            run["binding_subtype_divergences"]
        ),
        "further_gate_relaxation_allowed": False,
    })
    write(output / "repair_lineage.json", repair)
    report = "\n".join([
        "# Relation-evidence binding calibration v0.62.1",
        "",
        "## Architecture",
        (
            "- Stage A separates relation-evidence identity binding from "
            "truth-state judgment. EVIDENCE_BINDER and BINDING_SKEPTIC "
            "cannot emit EFFECT, NULL, or UNRESOLVED."
        ),
        (
            "- Stage B may run only after every focal relation has a "
            "conflict-free binding consensus. It consumes the consensus "
            "hash and may cite only admitted spans."
        ),
        "",
        "## Initial v0.62",
        (
            f"- Binding receipts: {len(initial_run['raw_receipts'])}/"
            f"{initial_preregistration['required_binding_receipt_count']}; "
            f"relation consensus: "
            f"{initial_run['binding_relation_consensus_count']}/30."
        ),
        (
            f"- Binding conflicts: "
            f"{len(initial_run['binding_conflicts'])}; contract failures: "
            f"{len(initial_run['contract_failures'])}."
        ),
        (
            "- All five explicit conflicts were only "
            "EXACT_EXPLICIT-versus-COREFERENCE target-outcome granularity."
        ),
        "",
        "## Bounded v0.62.1 repair",
        (
            "- The corpus and revealed reference labels were unchanged. "
            "Runtime treated exact and coreferential BOUND identities as "
            "coarse equivalents and derived binding_state mechanically."
        ),
        (
            f"- Binding receipts: {len(run['raw_receipts'])}/"
            f"{preregistration['required_binding_receipt_count']}; relation "
            f"consensus: {run['binding_relation_consensus_count']}/30."
        ),
        (
            f"- Contract failures: {len(run['contract_failures'])}; "
            f"subtype divergences retained as diagnostics: "
            f"{len(run['binding_subtype_divergences'])}."
        ),
        (
            f"- Remaining core conflicts: {len(run['binding_conflicts'])}."
        ),
        (
            "- Both remaining conflicts are PC-HVAC supported effects. "
            "Binder included the shared replication summary S6 beside the "
            "primary intervention span, while Skeptic retained only the "
            "primary span. Object identity, outcome identity, binding state, "
            "and evidence design all agree."
        ),
        "",
        "## Decision",
        "- Decision: `REJECT_RELATION_EVIDENCE_BINDING_CONSENSUS_GATE`.",
        (
            "- Candidate state: "
            "`BINDING_EVIDENCE_SET_CONSENSUS_INSUFFICIENT_STOP`."
        ),
        "- State assessment was not run in either revision.",
        "- No further relaxation is allowed on these revealed receipts.",
        "- No Core, retention, baseline, selection, or production authority.",
        "",
        "## Interpretation",
        (
            "- The object-binding decomposition removed the original "
            "identity ambiguity and improved strict relation consensus from "
            "20/30 to 28/30. The remaining bottleneck is representational: "
            "primary causal evidence and corroborating replication evidence "
            "occupy one untyped span set."
        ),
        (
            "- The next calibration should introduce separate "
            "primary_evidence_span_ids and corroborating_evidence_span_ids. "
            "Runtime may require primary-span agreement while preserving the "
            "union of nonconflicting corroboration, instead of forcing exact "
            "set equality or silently discarding replication evidence."
        ),
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )
    ledger = artifact({
        "ledger_version": "relation_evidence_binding_ledger_v0_62_1",
        "source_initial_run_hash": initial_run["run_hash"],
        "source_repaired_run_hash": run["run_hash"],
        "source_repair_hash": repair["artifact_hash"],
        "decision": "REJECT_RELATION_EVIDENCE_BINDING_CONSENSUS_GATE",
        "candidate_state": (
            "BINDING_EVIDENCE_SET_CONSENSUS_INSUFFICIENT_STOP"
        ),
        "state_assessment_executed": False,
        "core_integration_authorized": False,
    })
    write(output / "ledger.json", ledger)
    replay = artifact({
        "replay_version": "relation_evidence_binding_replay_v0_62_1",
        "working_directory": str(PACK_ROOT),
        "environment": {"AGENTOS_BINDING_REVISION": "v0_62_1"},
        "commands": [
            "python examples/run_relation_evidence_binding_calibration.py",
            (
                "python examples/"
                "finalize_relation_evidence_binding_calibration.py"
            ),
        ],
        "warning": "Replay creates new Provider binding evidence.",
    })
    write(output / "replay.json", replay)
    rollback = artifact({
        "rollback_version": "relation_evidence_binding_rollback_v0_62_1",
        "isolated_output_directory": str(output),
        "rollback_action": "Remove only this isolated output directory.",
        "agentos_core_files_touched": False,
    })
    write(output / "rollback_pointer.json", rollback)
    closure = artifact({
        "closure_version": "relation_evidence_binding_closure_v0_62_1",
        "source_ledger_hash": ledger["artifact_hash"],
        "decision": ledger["decision"],
        "candidate_state": ledger["candidate_state"],
        "typed_evidence_set_calibration_required": True,
        "state_assessment_executed": False,
        "fresh_generalization_claim": False,
        "promotion_allowed": False,
        "core_integration_authorized": False,
    })
    write(output / "closure.json", closure)
    names = [
        "v0_62_initial_preregistration.json",
        "v0_62_initial_binding_run.json",
        "preregistration.json",
        "binding_run.json",
        "repair_lineage.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory = artifact({
        "inventory_version": (
            "relation_evidence_binding_inventory_v0_62_1"
        ),
        "files": [{
            "path": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha(output / name),
        } for name in names],
    })
    write(output / "hash_inventory.json", inventory)
    pack = output / "relation_evidence_binding_v0_62_1.zip"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(names + ["hash_inventory.json"]):
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (output / name).read_bytes())
    manifest = artifact({
        "manifest_version": "relation_evidence_binding_manifest_v0_62_1",
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
        "relation_consensus": run["binding_relation_consensus_count"],
        "remaining_conflicts": len(run["binding_conflicts"]),
        "state_assessment_executed": False,
        "return_pack": str(pack),
        "sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
