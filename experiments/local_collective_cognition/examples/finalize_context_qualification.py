"""Close and package v0.53 context qualification."""

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


def main():
    output = REPO_ROOT / "outputs" / "context_qualification_v0_53"
    prior_prereg = read(output / "source_v0_52_preregistration.json")
    prior_analysis = read(output / "source_v0_52_analysis.json")
    prior_closure = read(output / "source_v0_52_closure.json")
    prior_posthoc = read(output / "source_v0_52_posthoc.json")
    calibration = read(output / "unlabeled_qualification_calibration.json")
    corpus = read(output / "context_qualification_corpus_frozen.json")
    audit = read(output / "reference_completeness_audit.json")
    prereg = read(output / "context_qualification_preregistration.json")
    run = read(output / "context_qualification_run.json")
    analysis = read(output / "context_qualification_analysis.json")
    posthoc = read(output / "posthoc_context_qualification.json")
    failed = sorted(
        key for key, value in analysis["conditions"].items()
        if not value
    )
    classification_reason = Counter(
        (value["classification"], value["gate_reason"])
        for value in posthoc["cells"]
    )
    proposed_lanes = Counter(
        run["raw_receipts"][
            f"{key.split(':', 2)[0]}:{key.split(':', 2)[1]}:"
            f"PROVIDER_COMPACT_DELTA:{key.split(':', 2)[2]}"
        ]["proposed_admission_lane"]
        for key in run["materialization_receipts"]
    )
    diagnostics_commitment = {
        "diagnostic_version": "context_qualification_diagnostics_v0_53",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_posthoc_hash": posthoc["artifact_hash"],
        "source_reference_audit_hash": audit["artifact_hash"],
        "source_unlabeled_calibration_hash": calibration["artifact_hash"],
        "reference_complete": audit["reference_complete"],
        "reference_mismatch_count": len(
            audit["reference_mismatches"]
        ),
        "reference_cross_role_disagreement_count": len(
            audit["cross_role_disagreements"]
        ),
        "context_qualification_metrics": analysis[
            "context_qualification_metrics"
        ],
        "selective_rejection_metrics": analysis[
            "selective_rejection_metrics"
        ],
        "replacement_gate_metrics": analysis[
            "replacement_gate_metrics"
        ],
        "classification_distribution": posthoc[
            "classification_distribution"
        ],
        "classification_reason_distribution": [
            {
                "classification": key[0],
                "reason": key[1],
                "count": count,
            }
            for key, count in sorted(classification_reason.items())
        ],
        "proposed_lane_distribution": dict(proposed_lanes),
        "coordinated_recovery_beneficial_count": posthoc[
            "coordinated_recovery_beneficial_count"
        ],
        "coordinated_recovery_harmful_count": posthoc[
            "coordinated_recovery_harmful_count"
        ],
        "failed_conditions": failed,
        "core_integration_authorized": False,
    }
    diagnostics = {
        **diagnostics_commitment,
        "artifact_hash": hash_payload(diagnostics_commitment),
    }
    write(output / "context_qualification_diagnostics.json", diagnostics)

    context = analysis["context_qualification_metrics"]
    selective = analysis["selective_rejection_metrics"]
    composition = analysis["composition_metrics"]
    gross = composition["triggered_composition_gross_uplift"]
    net = composition["triggered_composition_net_uplift"]
    replacement = analysis["replacement_gate_metrics"]
    report = "\n".join([
        "# Context-normalized qualification experiment v0.53",
        "",
        "## Observed facts",
        (
            f"- Unlabeled calibration: v0.51 "
            f"{calibration['source_metrics']['V0_51']['new_qualified_count']}/24, "
            f"v0.52 "
            f"{calibration['source_metrics']['V0_52']['new_qualified_count']}/24; "
            f"cross-source rate range "
            f"{calibration['cross_source_rate_range']:.3f}."
        ),
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
            f"- Authorized deltas: "
            f"{analysis['runtime_metrics']['authorized_delta_call_count']}; "
            f"valid lineage and pairwise reviews: "
            f"{len(run['pairwise_displacement_valid_keys'])}."
        ),
        (
            f"- Accepted: {replacement['accepted_count']}/"
            f"{replacement['receipt_count']}; gross mean/median "
            f"{gross['mean']:.3f}/{gross['median']:.3f}, wins "
            f"{gross['win_count']}/{gross['count']}, losses "
            f"{gross['loss_count']}."
        ),
        (
            f"- Challenges: {selective['challenge_valid_count']}; reopen "
            f"{selective['reopen_count']}; coordinated activations "
            f"{selective['coordinated_activation_count']}."
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
            f"- Coordinated recovery: "
            f"{posthoc['coordinated_recovery_beneficial_count']} beneficial, "
            f"{posthoc['coordinated_recovery_harmful_count']} harmful."
        ),
        (
            f"- Positive-oracle capture: "
            f"{posthoc['mean_fraction_of_positive_oracle_uplift_captured']:.3f}."
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
            "- The context-normalized policy generalized to the fresh "
            "holdout at 19/24, matching the unlabeled calibration range. "
            "Seventeen qualifications used structural opportunity gaps. "
            "No Provider call, private outcome, or retuned absolute "
            "threshold was used by qualification."
        ),
        (
            "- Review volume rose from three valid proposals in v0.52 to "
            "seventeen. Seven were accepted and every accepted proposal "
            "gained +2.0 gross Cbit. There were no harmful acceptances."
        ),
        (
            "- Selective rejection now had enough support: twelve challenges "
            "produced seven reopenings and four coordinated activations. "
            "Private posthoc classified all four recoveries as beneficial."
        ),
        (
            "- Seven additional beneficial proposals were rejected and three "
            "ties were safely rejected, leaving positive-oracle capture at "
            "0.5. Two beneficial EFFECT proposals failed the bound-lane "
            "witness requirement; five beneficial proposals were not "
            "approved by selective arbitration."
        ),
        (
            "- The formal decision remained REJECT because one duplicate "
            "delta reduced lineage coverage below 1.0 and every accepted "
            "proposal belonged to INFORMATIVE_NULL, missing the frozen "
            "second-lane requirement. These are governance failures, not "
            "evidence of harmful qualification."
        ),
        (
            f"- Mean token penalty per accepted cell was "
            f"{composition['mean_delta_token_penalty_cbit']:.3f} "
            f"Cbit-equivalent and mean net uplift was {net['mean']:.3f}. "
            "Cost remains secondary to stable gross Cbit."
        ),
        (
            "- The next experiment should keep qualification frozen and "
            "separately test effect-lane witness acquisition and remaining "
            "arbiter false negatives. It must not relax lineage or "
            "fail-closed duplicate checks."
        ),
        (
            "- All outcomes remain synthetic, external, candidate-only, and "
            "unable to write CoreSlim, retention, baseline, selection, or "
            "production state."
        ),
        "",
        f"Decision: `{analysis['decision']}`.",
        f"Candidate state: `{analysis['candidate_state']}`.",
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )

    ledger_commitment = {
        "ledger_version": "context_qualification_ledger_v0_53",
        "source_prior_preregistration_hash": prior_prereg["artifact_hash"],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
        "source_calibration_hash": calibration["artifact_hash"],
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
    }
    ledger = {
        **ledger_commitment,
        "artifact_hash": hash_payload(ledger_commitment),
    }
    write(output / "ledger.json", ledger)

    replay_commitment = {
        "replay_version": "context_qualification_replay_v0_53",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_context_qualification.py",
            "python examples/run_context_qualification_audit.py",
            "python examples/freeze_context_qualification.py",
            "python examples/run_context_qualification.py",
            "python examples/analyze_context_qualification_posthoc.py",
            "python examples/finalize_context_qualification.py",
        ],
        "provider_model": run["model_id"],
        "frozen_corpus_hash": corpus["artifact_hash"],
        "warning": "Replay creates new Provider evidence.",
    }
    replay = {
        **replay_commitment,
        "artifact_hash": hash_payload(replay_commitment),
    }
    write(output / "replay.json", replay)

    rollback_commitment = {
        "rollback_version": "context_qualification_rollback_v0_53",
        "isolated_output_directory": str(output),
        "rollback_action": "Remove only this isolated output directory.",
        "agentos_core_files_touched": False,
        "retention_or_baseline_mutation_performed": False,
    }
    rollback = {
        **rollback_commitment,
        "artifact_hash": hash_payload(rollback_commitment),
    }
    write(output / "rollback_pointer.json", rollback)

    closure_commitment = {
        "closure_version": "context_qualification_closure_v0_53",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "context_qualification_gate": analysis[
            "context_qualification_gate"
        ],
        "core_integration_authorized": False,
        "promotion_allowed": False,
    }
    closure = {
        **closure_commitment,
        "artifact_hash": hash_payload(closure_commitment),
    }
    write(output / "closure.json", closure)

    names = [
        "source_v0_52_preregistration.json",
        "source_v0_52_analysis.json",
        "source_v0_52_closure.json",
        "source_v0_52_posthoc.json",
        "unlabeled_qualification_calibration.json",
        "context_qualification_corpus_frozen.json",
        "reference_completeness_audit.json",
        "context_qualification_preregistration.json",
        "context_qualification_base_progress.json",
        "context_qualification_overlay_progress.json",
        "context_qualification_run.json",
        "context_qualification_analysis.json",
        "posthoc_context_qualification.json",
        "context_qualification_diagnostics.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "context_qualification_inventory_v0_53",
        "files": [{
            "path": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha(output / name),
        } for name in names],
    }
    inventory = {
        **inventory_commitment,
        "artifact_hash": hash_payload(inventory_commitment),
    }
    write(output / "hash_inventory.json", inventory)
    pack = output / "context_qualification_v0_53_return_pack.zip"
    zip_pack(
        pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "context_qualification_manifest_v0_53",
        "return_pack": pack.name,
        "return_pack_sha256": sha(pack),
        "return_pack_bytes": pack.stat().st_size,
        "inventory_hash": inventory["artifact_hash"],
        "closure_hash": closure["artifact_hash"],
    }
    manifest = {
        **manifest_commitment,
        "artifact_hash": hash_payload(manifest_commitment),
    }
    write(output / "manifest.json", manifest)
    print(json.dumps({
        "decision": analysis["decision"],
        "state": analysis["candidate_state"],
        "return_pack": str(pack),
        "sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
