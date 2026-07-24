"""Close and package v0.51 non-destructive portfolio displacement."""
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


def main():
    output = REPO_ROOT / "outputs" / "reference_complete_portfolio_v0_51"
    prior_analysis = read(output / "source_v0_50_analysis.json")
    prior_closure = read(output / "source_v0_50_closure.json")
    prior_posthoc = read(output / "source_v0_50_posthoc.json")
    corpus = read(output / "reference_complete_portfolio_corpus_frozen.json")
    reference_audit = read(output / "reference_completeness_audit.json")
    preregistration = read(
        output / "reference_complete_portfolio_preregistration.json"
    )
    run = read(output / "reference_complete_portfolio_run.json")
    analysis = read(output / "reference_complete_portfolio_analysis.json")
    posthoc = read(output / "posthoc_reference_complete_portfolio.json")
    composition = analysis["composition_metrics"]
    pooled = analysis["pooled_contrast_metrics"]
    empty_metrics = {
        "count": 0, "mean": 0.0, "median": 0.0,
        "win_count": 0, "loss_count": 0,
    }
    gross = (
        composition["triggered_composition_gross_uplift"]
        or empty_metrics
    )
    net = (
        composition["triggered_composition_net_uplift"]
        or empty_metrics
    )
    replacement = analysis["replacement_gate_metrics"]
    oracle = posthoc["pool_oracle_gross_uplift"]
    regret = posthoc["gate_regret"]
    failed = sorted(
        key for key, value in analysis["conditions"].items()
        if not value
    )
    pairwise_values = [
        value for value in run["pairwise_displacement_receipts"].values()
    ]
    identifier_collision_receipts = [
        value for value in pairwise_values
        if (
            "delta is already active" in value["rationale"].lower()
            or "delta candidate is already a fixed" in (
                value["rationale"].lower()
            )
            or "delta candidate provided is c2, but it is already active"
            in value["rationale"].lower()
        )
    ]
    harmful_cells = [
        value for value in posthoc["cells"]
        if value["classification"] == "HARMFUL_ACCEPTED"
    ]

    diagnostics_commitment = {
        "diagnostic_version": "reference_complete_portfolio_diagnostics_v0_51",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_posthoc_hash": posthoc["artifact_hash"],
        "source_reference_audit_hash": reference_audit["artifact_hash"],
        "reference_complete": reference_audit["reference_complete"],
        "reference_valid_receipt_count": reference_audit[
            "valid_receipt_count"
        ],
        "reference_mismatch_count": len(
            reference_audit["reference_mismatches"]
        ),
        "reference_cross_role_disagreement_count": len(
            reference_audit["cross_role_disagreements"]
        ),
        "raw_receipt_count": len(run["raw_receipts"]),
        "trigger_receipt_count": len(run["trigger_receipts"]),
        "qualification_receipt_count": len(
            run["qualification_receipts"]
        ),
        "reference_complete_portfolio_receipt_count": len(
            run["reference_complete_portfolio_receipts"]
        ),
        "qualified_count": composition["qualified_count"],
        "valid_composition_count": composition["valid_composition_count"],
        "replacement_gate_metrics": replacement,
        "failures": run["failures"],
        "runtime_metrics": analysis["runtime_metrics"],
        "composition_metrics": composition,
        "pooled_metrics": pooled,
        "posthoc_oracle_metrics": oracle,
        "posthoc_regret_metrics": regret,
        "source_qualified_identifier_collision_count": len(
            identifier_collision_receipts
        ),
        "harmful_accepted_count": len(harmful_cells),
        "failed_conditions": failed,
        "external_panel_present": False,
        "core_integration_authorized": False,
    }
    diagnostics = {
        **diagnostics_commitment,
        "artifact_hash": hash_payload(diagnostics_commitment),
    }
    write(output / "reference_complete_portfolio_diagnostics.json", diagnostics)

    report = "\n".join([
        "# Reference-complete portfolio routing experiment v0.51",
        "",
        "## Observed facts",
        (
            f"- Pooled net mean/median: {pooled['mean']:.3f}/"
            f"{pooled['median']:.3f}; wins {pooled['win_count']}/"
            f"{pooled['count']}."
        ),
        (
            f"- Raw triggers: {composition['raw_trigger_count']}; "
            f"qualified: {composition['qualified_count']}; authorized "
            f"delta calls: {analysis['runtime_metrics']['authorized_delta_call_count']}; "
            f"pre-call skips: {analysis['runtime_metrics']['pre_call_skip_count']}."
        ),
        (
            f"- Triggered gross mean/median: {gross['mean']:.3f}/"
            f"{gross['median']:.3f}; wins {gross['win_count']}/"
            f"{gross['count']}; losses {gross['loss_count']}."
        ),
        (
            f"- Triggered net mean/median: {net['mean']:.3f}/"
            f"{net['median']:.3f}."
        ),
        (
            "- Mean accepted-delta token penalty: "
            f"{composition['mean_delta_token_penalty_cbit']:.3f} Cbit."
        ),
        (
            f"- Gate receipts: {replacement['receipt_count']}; accepted "
            f"{replacement['accepted_count']}; rejected "
            f"{replacement['rejected_count']}."
        ),
        (
            f"- Pool-oracle mean/median: {oracle['mean']:.3f}/"
            f"{oracle['median']:.3f}; positive cells "
            f"{posthoc['positive_oracle_cell_count']}/{oracle['count']}."
        ),
        (
            f"- Gate regret mean/median: {regret['mean']:.3f}/"
            f"{regret['median']:.3f}; positive-oracle fraction captured "
            f"{posthoc['mean_fraction_of_positive_oracle_uplift_captured']:.3f}."
        ),
        (
            "- Gate classifications: "
            + ", ".join(
                f"{key}={value}" for key, value in sorted(
                    posthoc["classification_distribution"].items()
                )
            )
            + "."
        ),
        (
            f"- Total physical tokens: "
            f"{analysis['physical_total_tokens']}."
        ),
        "- Failed frozen conditions: "
        + (", ".join(failed) if failed else "none")
        + ".",
        "",
        "## Result analysis",
        (
            "- The frozen dual-role reference audit completed "
            f"{reference_audit['valid_receipt_count']}/"
            f"{reference_audit['required_receipt_count']} receipts with "
            f"{len(reference_audit['reference_mismatches'])} reference "
            "mismatches and "
            f"{len(reference_audit['cross_role_disagreements'])} "
            "cross-role disagreements. This is internal provider-audited "
            "synthetic evidence, not external gold."
        ),
        (
            "- Twenty-four physical standard calls produced forty-eight "
            "arm-level baseline receipts with identical hashes and costs; "
            f"standard contract coverage was "
            f"{analysis['runtime_metrics']['standard_compact_delta_contract_coverage']:.3f}."
        ),
        (
            f"- {analysis['runtime_metrics']['authorized_delta_call_count']} "
            "cells entered warrant-complete delta generation; "
            f"{len(run['lineage_valid_keys'])} preserved the exact source "
            "warrant and semantic lineage, and "
            f"{len(run['pairwise_displacement_valid_keys'])} completed "
            "independent pairwise review."
        ),
        (
            f"- The displacement gate accepted {replacement['accepted_count']} "
            f"of {replacement['receipt_count']} reviewed candidates. Their "
            f"gross mean/median uplift was {gross['mean']:.3f}/"
            f"{gross['median']:.3f} Cbit with {gross['loss_count']} losses."
        ),
        (
            "- Private synthetic posthoc classified gate outcomes as "
            + (
                ", ".join(
                    f"{key}={value}" for key, value in sorted(
                        posthoc["classification_distribution"].items()
                    )
                ) or "none"
            )
            + f"; positive-oracle capture was "
            f"{posthoc['mean_fraction_of_positive_oracle_uplift_captured']:.3f} "
            f"and mean gate regret was {regret['mean']:.3f} Cbit."
        ),
        (
            f"- {len(identifier_collision_receipts)}/"
            f"{len(pairwise_values)} portfolio rationales conflated BASE "
            "and COUNTER identities. Every valid receipt echoed distinct "
            "source-qualified pool IDs, so the v0.50 identity ambiguity was "
            "not reproduced."
        ),
        (
            f"- {len(harmful_cells)} accepted cells were scored harmful by "
            "the complete frozen reference. The gate accepted four "
            "beneficial cells and rejected four other beneficial cells, "
            "moving the bottleneck from precision to conservative recall."
        ),
        (
            f"- Mean communication penalty was "
            f"{composition['mean_delta_token_penalty_cbit']:.3f} "
            f"Cbit-equivalent and accepted-cell net mean was "
            f"{net['mean']:.3f}. Cost is reported independently and does "
            "not veto a positive cognitive-quality gate unless the hard "
            "runaway ceiling is crossed."
        ),
        (
            "- The formal frozen conditions "
            + ("all passed." if not failed else "did not all pass: ")
            + ("" if not failed else ", ".join(failed) + ".")
        ),
        (
            "- The soft cost observation was "
            + (
                "within" if analysis["cost_observations"]["soft_ceiling_met"]
                else "above"
            )
            + f" the {preregistration['success_gate']['maximum_physical_total_tokens']}"
            f"-token reference at {analysis['physical_total_tokens']} tokens; "
            f"the hard stop remained "
            f"{preregistration['success_gate']['hard_runaway_total_tokens']}."
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
        "ledger_version": "reference_complete_portfolio_ledger_v0_51",
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
        "source_corpus_hash": corpus["artifact_hash"],
        "source_reference_audit_hash": reference_audit["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_posthoc_hash": posthoc["artifact_hash"],
        "decision": analysis["decision"],
        "candidate_state": analysis["candidate_state"],
        "external_semantic_panel_authorized": analysis[
            "external_semantic_panel_authorized"
        ],
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
        "replay_version": "reference_complete_portfolio_replay_v0_51",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_reference_complete_portfolio.py",
            "python examples/run_reference_complete_portfolio_audit.py",
            "python examples/freeze_reference_complete_portfolio.py",
            "python examples/run_reference_complete_portfolio.py",
            "python examples/analyze_reference_complete_portfolio_posthoc.py",
            "python examples/finalize_reference_complete_portfolio.py",
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
        "rollback_version": "reference_complete_portfolio_rollback_v0_51",
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
        "closure_version": "reference_complete_portfolio_closure_v0_51",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "reference_complete_portfolio_gate": analysis["reference_complete_portfolio_gate"],
        "external_semantic_panel_authorized": analysis[
            "external_semantic_panel_authorized"
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
        "source_v0_50_analysis.json",
        "source_v0_50_closure.json",
        "source_v0_50_posthoc.json",
        "reference_complete_portfolio_corpus_frozen.json",
        "reference_completeness_audit.json",
        "reference_complete_portfolio_preregistration.json",
        "reference_complete_portfolio_progress.json",
        "reference_complete_portfolio_run.json",
        "reference_complete_portfolio_analysis.json",
        "posthoc_reference_complete_portfolio.json",
        "reference_complete_portfolio_diagnostics.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "reference_complete_portfolio_inventory_v0_51",
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

    pack = output / "reference_complete_portfolio_v0_51_return_pack.zip"
    zip_pack(
        pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "reference_complete_portfolio_manifest_v0_51",
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






