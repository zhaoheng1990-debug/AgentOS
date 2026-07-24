"""Close and package the zero-Provider v0.55 stability audit."""

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
    source = REPO_ROOT / "outputs" / "evidence_first_v0_54"
    output = REPO_ROOT / "outputs" / "relation_stability_audit_v0_55"
    audit = read(output / "relation_stability_audit.json")
    witness_audit = read(output / "effect_witness_retrospective.json")
    source_closure = read(source / "closure.json")
    source_manifest = read(source / "manifest.json")
    baseline = audit["arm_summaries"]["A1_BASELINE"]
    delta = audit["arm_summaries"]["A2_COMPACT_DELTA"]
    report = "\n".join([
        "# Relation stability audit v0.55",
        "",
        "## Result",
        (
            f"- Pairwise relation Jaccard changed from "
            f"{baseline['mean_pairwise_relation_jaccard']:.3f} to "
            f"{delta['mean_pairwise_relation_jaccard']:.3f}."
        ),
        (
            f"- Mean union reference coverage changed from "
            f"{baseline['mean_union_reference_coverage']:.3f} to "
            f"{delta['mean_union_reference_coverage']:.3f}."
        ),
        (
            f"- Mean consensus reference coverage changed from "
            f"{baseline['mean_consensus_reference_coverage']:.3f} to "
            f"{delta['mean_consensus_reference_coverage']:.3f}."
        ),
        (
            f"- Reference-valid pairwise differences changed from "
            f"{baseline['reference_valid_pairwise_difference_count']} to "
            f"{delta['reference_valid_pairwise_difference_count']}."
        ),
        (
            f"- Unsupported relation occurrences: baseline "
            f"{baseline['unsupported_relation_occurrence_count']}, "
            f"experimental "
            f"{delta['unsupported_relation_occurrence_count']}."
        ),
        (
            f"- Diagnosis: `{audit['diagnosis']}`."
        ),
        (
            f"- Historical beneficial EFFECT misses with an independent "
            f"same-stage delta witness: "
            f"{witness_audit['retrospectively_witness_eligible_count']}/"
            f"{witness_audit['cell_count']}."
        ),
        "",
        "## Interpretation",
        (
            "- The lower Jaccard is not unsupported semantic drift. Every "
            "one of the 72 relation occurrences in each arm belongs to the "
            "exhaustive synthetic reference surface."
        ),
        (
            "- The experimental arm covers more valid relations across the "
            "collective, while its intersection across all three replications "
            "is smaller. The current metric conflates productive division of "
            "cognitive labor with loss of a stable shared core."
        ),
        (
            "- Jaccard should remain diagnostic but should not serve as a "
            "solo hard gate. The next frozen gate family should separately "
            "bound unsupported drift, preserve or improve union reference "
            "coverage, require a minimum consensus core, and forbid realized "
            "harmful acceptance."
        ),
        (
            "- Both v0.53 beneficial EFFECT rejections already had an exact "
            "same-relation, lineage-valid delta in another isolated "
            "replication. The missing capability is mechanical evidence "
            "organization, not another semantic Provider role."
        ),
        (
            "- This audit used no Provider calls and does not revise the "
            "formal v0.54 rejection or grant any authority."
        ),
    ])
    (output / "audit_report.md").write_text(report, encoding="utf-8")
    gate_candidate = artifact({
        "candidate_version": "dual_axis_relation_gate_candidate_v0_55",
        "source_audit_hash": audit["artifact_hash"],
        "status": "CANDIDATE_ONLY_PENDING_FRESH_PREREGISTRATION",
        "formal_outcome_metrics": {
            "maximum_unsupported_relation_occurrence_rate": 0.0,
            "minimum_union_reference_coverage_delta": 0.0,
            "minimum_consensus_reference_coverage": 0.25,
            "maximum_harmful_acceptance_count": 0,
        },
        "diagnostic_metrics": {
            "pairwise_relation_jaccard": (
                "OBSERVE_NOT_SOLO_HARD_GATE"
            ),
            "reference_valid_diversity_count": "OBSERVE",
        },
        "effect_lane_requirement": {
            "minimum_distinct_acceptance_lanes": 2,
            "minimum_effect_lane_acceptance_count": 2,
            "independent_cross_replication_witness_required": True,
        },
        "lineage_requirement": {
            "minimum_lineage_contract_coverage": 1.0,
            "delta_relation_distinctness_fail_closed": True,
        },
        "thresholds_may_not_be_retuned_on_v0_54_labels": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    })
    write(output / "dual_axis_gate_candidate.json", gate_candidate)
    ledger = artifact({
        "ledger_version": "relation_stability_ledger_v0_55",
        "source_v0_54_closure_hash": source_closure["artifact_hash"],
        "source_v0_54_manifest_hash": source_manifest["artifact_hash"],
        "source_audit_hash": audit["artifact_hash"],
        "source_gate_candidate_hash": gate_candidate["artifact_hash"],
        "source_effect_witness_audit_hash": witness_audit[
            "artifact_hash"
        ],
        "diagnosis": audit["diagnosis"],
        "formal_v0_54_decision_unchanged": True,
        "provider_calls_added": 0,
        "core_integration_authorized": False,
    })
    write(output / "ledger.json", ledger)
    replay = artifact({
        "replay_version": "relation_stability_replay_v0_55",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/audit_relation_stability.py",
            "python examples/audit_effect_witness_retrospective.py",
            "python examples/finalize_relation_stability_audit.py",
        ],
        "source_v0_54_pack_sha256": source_manifest[
            "return_pack_sha256"
        ],
        "provider_calls_required": 0,
    })
    write(output / "replay.json", replay)
    rollback = artifact({
        "rollback_version": "relation_stability_rollback_v0_55",
        "isolated_output_directory": str(output),
        "rollback_action": "Remove only this isolated output directory.",
        "agentos_core_files_touched": False,
    })
    write(output / "rollback_pointer.json", rollback)
    closure = artifact({
        "closure_version": "relation_stability_closure_v0_55",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": "DUAL_AXIS_GATE_READY_FOR_FRESH_PREREGISTRATION",
        "diagnosis": audit["diagnosis"],
        "formal_v0_54_decision_unchanged": True,
        "promotion_allowed": False,
        "core_integration_authorized": False,
    })
    write(output / "closure.json", closure)
    names = [
        "relation_stability_audit.json",
        "effect_witness_retrospective.json",
        "audit_report.md",
        "dual_axis_gate_candidate.json",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory = artifact({
        "inventory_version": "relation_stability_inventory_v0_55",
        "files": [{
            "path": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha(output / name),
        } for name in names],
    })
    write(output / "hash_inventory.json", inventory)
    pack = output / "relation_stability_audit_v0_55_return_pack.zip"
    zip_pack(
        pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest = artifact({
        "manifest_version": "relation_stability_manifest_v0_55",
        "return_pack": pack.name,
        "return_pack_sha256": sha(pack),
        "return_pack_bytes": pack.stat().st_size,
        "inventory_hash": inventory["artifact_hash"],
        "closure_hash": closure["artifact_hash"],
    })
    write(output / "manifest.json", manifest)
    print(json.dumps({
        "diagnosis": audit["diagnosis"],
        "state": closure["candidate_state"],
        "return_pack": str(pack),
        "sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
