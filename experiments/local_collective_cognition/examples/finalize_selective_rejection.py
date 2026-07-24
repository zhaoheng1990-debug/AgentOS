"""Close and package v0.52 selective rejection."""

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
    output = REPO_ROOT / "outputs" / "selective_rejection_v0_52"
    prior_prereg = read(output / "source_v0_51_preregistration.json")
    prior_analysis = read(output / "source_v0_51_analysis.json")
    prior_closure = read(output / "source_v0_51_closure.json")
    prior_posthoc = read(output / "source_v0_51_posthoc.json")
    corpus = read(output / "selective_rejection_corpus_frozen.json")
    audit = read(output / "reference_completeness_audit.json")
    prereg = read(output / "selective_rejection_preregistration.json")
    run = read(output / "selective_rejection_run.json")
    analysis = read(output / "selective_rejection_analysis.json")
    posthoc = read(output / "posthoc_selective_rejection.json")
    failed = sorted(
        key for key, value in analysis["conditions"].items()
        if not value
    )
    qualifications = list(run["qualification_receipts"].values())
    route_distribution = Counter(
        value["route_id"] for value in qualifications
    )
    qualified_route_distribution = Counter(
        value["route_id"] for value in qualifications
        if value["qualified"]
    )
    below_spread = sum(
        value["semantic_score_spread"]
        < value["thresholds"]["minimum_semantic_spread"]
        for value in qualifications
    )
    challenge_decisions = Counter(
        value["challenge_decision"]
        for value in run["rejection_challenge_receipts"].values()
    )
    coordination_decisions = Counter(
        value["coordination_decision"]
        for value in run["rejection_coordination_receipts"].values()
    )
    diagnostics_commitment = {
        "diagnostic_version": "selective_rejection_diagnostics_v0_52",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_posthoc_hash": posthoc["artifact_hash"],
        "source_reference_audit_hash": audit["artifact_hash"],
        "reference_complete": audit["reference_complete"],
        "reference_mismatch_count": len(
            audit["reference_mismatches"]
        ),
        "reference_cross_role_disagreement_count": len(
            audit["cross_role_disagreements"]
        ),
        "raw_trigger_count": analysis[
            "composition_metrics"
        ]["raw_trigger_count"],
        "qualification_count": len(qualifications),
        "qualified_count": sum(
            value["qualified"] for value in qualifications
        ),
        "qualification_route_distribution": dict(route_distribution),
        "qualified_route_distribution": dict(
            qualified_route_distribution
        ),
        "below_semantic_spread_threshold_count": below_spread,
        "challenge_decision_distribution": dict(challenge_decisions),
        "coordination_decision_distribution": dict(
            coordination_decisions
        ),
        "selective_rejection_metrics": analysis[
            "selective_rejection_metrics"
        ],
        "classification_distribution": posthoc[
            "classification_distribution"
        ],
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
    write(output / "selective_rejection_diagnostics.json", diagnostics)

    composition = analysis["composition_metrics"]
    gross = composition["triggered_composition_gross_uplift"]
    net = composition["triggered_composition_net_uplift"]
    replacement = analysis["replacement_gate_metrics"]
    selective = analysis["selective_rejection_metrics"]
    report = "\n".join([
        "# Selective rejection challenge experiment v0.52",
        "",
        "## Observed facts",
        (
            f"- Reference audit: {audit['valid_receipt_count']}/"
            f"{audit['required_receipt_count']} valid, "
            f"{len(audit['reference_mismatches'])} mismatches, "
            f"{len(audit['cross_role_disagreements'])} role disagreements."
        ),
        (
            f"- Raw triggers: {composition['raw_trigger_count']}; qualified "
            f"and authorized: {composition['qualified_count']}."
        ),
        (
            f"- Accepted: {replacement['accepted_count']}/"
            f"{replacement['receipt_count']}; gross mean/median "
            f"{gross['mean']:.3f}/{gross['median']:.3f}, wins "
            f"{gross['win_count']}/{gross['count']}, losses "
            f"{gross['loss_count']}."
        ),
        (
            f"- Initial rejections eligible for challenge: "
            f"{selective['eligible_rejection_count']}; reopened "
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
            f"- Positive-oracle capture inside the valid review set: "
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
            "- The selective mechanism produced one challenge and one "
            "coordination receipt. Both were contract-valid. The coordinator "
            "recovered the rejected delta without granting direct activation "
            "authority to the challenger."
        ),
        (
            "- Private synthetic posthoc confirmed that the recovered delta "
            "was beneficial. All three accepted cells gained +2.0 gross Cbit "
            "and no accepted cell was harmful."
        ),
        (
            "- This is positive mechanism evidence but not a sufficient "
            "replication. Only one initial rejection reached the challenger, "
            "below the frozen minimum of two, and only three proposals could "
            "be accepted, below the frozen minimum of five."
        ),
        (
            f"- {below_spread}/24 qualification receipts fell below the "
            "frozen semantic-spread threshold. The fresh rotated holdout "
            "produced more balanced standard candidate sets, so the v0.41 "
            "qualification policy admitted only three ADVERSARIAL routes."
        ),
        (
            "- The bottleneck has moved upstream from portfolio precision "
            "and recall to cross-distribution qualification calibration. "
            "The next experiment should audit runtime-derived qualification "
            "signals on a new fresh holdout before repeating selective "
            "challenge."
        ),
        (
            f"- Mean accepted-cell token penalty was "
            f"{composition['mean_delta_token_penalty_cbit']:.3f} "
            f"Cbit-equivalent and mean net uplift was {net['mean']:.3f}. "
            "Cost remains secondary to gross cognitive quality."
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
        "ledger_version": "selective_rejection_ledger_v0_52",
        "source_prior_preregistration_hash": prior_prereg["artifact_hash"],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
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
        "replay_version": "selective_rejection_replay_v0_52",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_selective_rejection.py",
            "python examples/run_selective_rejection_audit.py",
            "python examples/freeze_selective_rejection.py",
            "python examples/run_selective_rejection.py",
            "python examples/analyze_selective_rejection_posthoc.py",
            "python examples/finalize_selective_rejection.py",
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
        "rollback_version": "selective_rejection_rollback_v0_52",
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
        "closure_version": "selective_rejection_closure_v0_52",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "selective_rejection_gate": analysis[
            "selective_rejection_gate"
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
        "source_v0_51_preregistration.json",
        "source_v0_51_analysis.json",
        "source_v0_51_closure.json",
        "source_v0_51_posthoc.json",
        "selective_rejection_corpus_frozen.json",
        "reference_completeness_audit.json",
        "selective_rejection_preregistration.json",
        "selective_rejection_base_progress.json",
        "selective_rejection_overlay_progress.json",
        "selective_rejection_run.json",
        "selective_rejection_analysis.json",
        "posthoc_selective_rejection.json",
        "selective_rejection_diagnostics.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "selective_rejection_inventory_v0_52",
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
    pack = output / "selective_rejection_v0_52_return_pack.zip"
    zip_pack(
        pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "selective_rejection_manifest_v0_52",
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
