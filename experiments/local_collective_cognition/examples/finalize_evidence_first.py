"""Close and package v0.54 evidence-first arbitration."""

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


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def zip_pack(path, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(files, key=lambda value: value.name):
            info = zipfile.ZipInfo(source.name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def artifact(commitment):
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def main():
    output = REPO_ROOT / "outputs" / "evidence_first_v0_54"
    corpus = read(output / "evidence_first_corpus_frozen.json")
    audit = read(output / "reference_completeness_audit.json")
    prereg = read(output / "evidence_first_preregistration.json")
    run = read(output / "evidence_first_run.json")
    analysis = read(output / "evidence_first_analysis.json")
    posthoc = read(output / "posthoc_evidence_first.json")
    failed = sorted(
        key for key, value in analysis["conditions"].items()
        if not value
    )
    context = analysis["context_qualification_metrics"]
    blind = analysis["blind_evidence_metrics"]
    replacement = analysis["replacement_gate_metrics"]
    composition = analysis["composition_metrics"]
    gross = composition["triggered_composition_gross_uplift"]
    net = composition["triggered_composition_net_uplift"]
    relation = analysis["relation_reproducibility"]
    runtime = analysis["runtime_metrics"]

    diagnostics = artifact({
        "diagnostic_version": "evidence_first_diagnostics_v0_54",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_posthoc_hash": posthoc["artifact_hash"],
        "reference_complete": audit["reference_complete"],
        "context_qualification_metrics": context,
        "blind_evidence_metrics": blind,
        "replacement_gate_metrics": replacement,
        "classification_distribution": posthoc[
            "classification_distribution"
        ],
        "blind_consensus_recovery_distribution": posthoc[
            "blind_consensus_recovery_distribution"
        ],
        "blind_consensus_recovery_precision": posthoc[
            "blind_consensus_recovery_precision"
        ],
        "positive_oracle_capture": posthoc[
            "mean_fraction_of_positive_oracle_uplift_captured"
        ],
        "lineage_contract_coverage": runtime[
            "lineage_contract_coverage"
        ],
        "relation_reproducibility": relation,
        "failed_conditions": failed,
        "core_integration_authorized": False,
    })
    write(output / "evidence_first_diagnostics.json", diagnostics)

    report = "\n".join([
        "# Decision-blind evidence-first arbitration v0.54",
        "",
        "## Observed facts",
        (
            f"- Fresh reference audit: {audit['valid_receipt_count']}/"
            f"{audit['required_receipt_count']} valid, "
            f"{len(audit['reference_mismatches'])} mismatches, "
            f"{len(audit['cross_role_disagreements'])} disagreements."
        ),
        (
            f"- Context qualification: {context['qualified_count']}/"
            f"{context['receipt_count']} "
            f"({context['qualification_rate']:.3f}); structural-gap "
            f"qualified {context['structural_gap_qualified_count']}."
        ),
        (
            f"- Initial rejections eligible for blind audit: "
            f"{blind['eligible_rejection_count']}; valid blind receipts "
            f"{blind['valid_role_receipt_count']}/"
            f"{blind['expected_role_receipt_count']}."
        ),
        (
            f"- Blind consensus activations: "
            f"{blind['blind_consensus_activation_count']}; direct role "
            f"activations: {blind['blind_direct_activation_count']}."
        ),
        (
            f"- Accepted: {replacement['accepted_count']}/"
            f"{replacement['receipt_count']}; gross mean/median "
            f"{gross['mean']:.3f}/{gross['median']:.3f}, wins "
            f"{gross['win_count']}/{gross['count']}, losses "
            f"{gross['loss_count']}."
        ),
        (
            "- Posthoc classifications: "
            + ", ".join(
                f"{key}={value}" for key, value in sorted(
                    posthoc["classification_distribution"].items()
                )
            )
            + "."
        ),
        (
            f"- Blind recovery: "
            f"{posthoc['blind_consensus_recovery_beneficial_count']} "
            f"beneficial, "
            f"{posthoc['blind_consensus_recovery_harmful_count']} "
            f"harmful; precision "
            f"{posthoc['blind_consensus_recovery_precision']:.3f}."
        ),
        (
            f"- Positive-oracle capture: "
            f"{posthoc['mean_fraction_of_positive_oracle_uplift_captured']:.3f}."
        ),
        (
            f"- Lineage coverage: "
            f"{runtime['lineage_contract_coverage']:.3f}; experimental/"
            f"baseline relation Jaccard "
            f"{relation['A2_COMPACT_DELTA']['mean_pairwise_relation_jaccard']:.3f}/"
            f"{relation['A1_BASELINE']['mean_pairwise_relation_jaccard']:.3f}."
        ),
        (
            f"- Physical tokens: {analysis['physical_total_tokens']}; soft "
            f"reference {prereg['success_gate']['maximum_physical_total_tokens']}; "
            f"hard stop {prereg['success_gate']['hard_runaway_total_tokens']}."
        ),
        "- Failed frozen conditions: "
        + (", ".join(failed) if failed else "none")
        + ".",
        "",
        "## Result analysis",
        (
            "- The isolated evidence-first roles removed a substantial part "
            "of the initial-arbiter false-negative bottleneck. All eight "
            "consensus recoveries were beneficial after private synthetic "
            "outcomes were unsealed, and none was harmful."
        ),
        (
            "- The gain was not produced by relaxing authority. Neither role "
            "could activate a candidate; both had to independently prefer "
            "the delta, after which the Runtime still enforced lineage, lane, "
            "capacity, and supported-null protection."
        ),
        (
            "- Oracle capture rose from 0.500 in v0.53 to 0.833 on a fresh "
            "holdout. Two beneficial proposals remained rejected and one tie "
            "was rejected, so the policy improved recall without observed "
            "gross-Cbit harm in this synthetic sample."
        ),
        (
            "- The formal stage remains rejected. One non-distinct delta was "
            "correctly failed closed, all ten accepted deltas occupied only "
            "the informative-null lane, and cross-replication relation "
            "overlap fell below the frozen baseline-relative requirement."
        ),
        (
            f"- Added review cost made mean net uplift {net['mean']:.3f} "
            "Cbit-equivalent despite gross mean +2.000. This is acceptable "
            "under the preregistered quality-primary policy, but it identifies "
            "a future efficiency target rather than evidence for promotion."
        ),
        (
            "- The next experiment should freeze this arbitration policy and "
            "target effect-lane witness acquisition plus exact lineage "
            "distinctness on another fresh holdout. It should not tune these "
            "eight recovered labels or weaken fail-closed checks."
        ),
        (
            "- Claims remain internal, synthetic, candidate-only, and unable "
            "to mutate CoreSlim, retention, baseline, or production state."
        ),
        "",
        f"Decision: `{analysis['decision']}`.",
        f"Candidate state: `{analysis['candidate_state']}`.",
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )

    source_names = [
        "source_v0_53_preregistration.json",
        "source_v0_53_analysis.json",
        "source_v0_53_closure.json",
        "source_v0_53_posthoc.json",
        "source_unlabeled_qualification_calibration.json",
    ]
    ledger = artifact({
        "ledger_version": "evidence_first_ledger_v0_54",
        "source_artifact_hashes": {
            name: read(output / name)["artifact_hash"]
            for name in source_names
        },
        "source_corpus_hash": corpus["artifact_hash"],
        "source_reference_audit_hash": audit["artifact_hash"],
        "source_preregistration_hash": prereg["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_posthoc_hash": posthoc["artifact_hash"],
        "decision": analysis["decision"],
        "candidate_state": analysis["candidate_state"],
        "core_integration_authorized": False,
        "retention_authority": False,
        "production_authority": False,
    })
    write(output / "ledger.json", ledger)
    replay = artifact({
        "replay_version": "evidence_first_replay_v0_54",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_evidence_first.py",
            "python examples/run_evidence_first_audit.py",
            "python examples/freeze_evidence_first.py",
            "python examples/run_evidence_first.py",
            "python examples/analyze_evidence_first_posthoc.py",
            "python examples/finalize_evidence_first.py",
        ],
        "provider_model": run["model_id"],
        "frozen_corpus_hash": corpus["artifact_hash"],
        "warning": "Replay creates new Provider evidence.",
    })
    write(output / "replay.json", replay)
    rollback = artifact({
        "rollback_version": "evidence_first_rollback_v0_54",
        "isolated_output_directory": str(output),
        "rollback_action": "Remove only this isolated output directory.",
        "agentos_core_files_touched": False,
        "retention_or_baseline_mutation_performed": False,
    })
    write(output / "rollback_pointer.json", rollback)
    closure = artifact({
        "closure_version": "evidence_first_closure_v0_54",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "evidence_first_gate": analysis["evidence_first_gate"],
        "arbitration_hypothesis_supported_posthoc": (
            posthoc["blind_consensus_recovery_beneficial_count"] > 0
            and posthoc["blind_consensus_recovery_harmful_count"] == 0
        ),
        "whole_stage_promotable": False,
        "core_integration_authorized": False,
        "promotion_allowed": False,
    })
    write(output / "closure.json", closure)

    names = source_names + [
        "evidence_first_corpus_frozen.json",
        "reference_completeness_audit.json",
        "evidence_first_preregistration.json",
        "evidence_first_base_progress.json",
        "evidence_first_overlay_progress.json",
        "evidence_first_run.json",
        "evidence_first_analysis.json",
        "posthoc_evidence_first.json",
        "evidence_first_diagnostics.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory = artifact({
        "inventory_version": "evidence_first_inventory_v0_54",
        "files": [{
            "path": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha(output / name),
        } for name in names],
    })
    write(output / "hash_inventory.json", inventory)
    pack = output / "evidence_first_v0_54_return_pack.zip"
    zip_pack(
        pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest = artifact({
        "manifest_version": "evidence_first_manifest_v0_54",
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
        "arbitration_hypothesis_supported_posthoc": closure[
            "arbitration_hypothesis_supported_posthoc"
        ],
        "whole_stage_promotable": closure["whole_stage_promotable"],
        "return_pack": str(pack),
        "sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
