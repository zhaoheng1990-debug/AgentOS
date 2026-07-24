"""Close and package the v0.28 frontier stability experiment."""

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
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def deterministic_zip(path, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(files, key=lambda value: value.name):
            info = zipfile.ZipInfo(source.name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def posthoc_stability_diagnostics(analysis, run):
    pooled_deltas = sorted(
        value
        for replication in analysis["case_deltas"].values()
        for value in replication.values()
    )
    midpoint = len(pooled_deltas) // 2
    median = (
        pooled_deltas[midpoint - 1] + pooled_deltas[midpoint]
    ) / 2
    arm_reproducibility = {}
    for arm_id in ("A0_DIRECT", "A1_ONTOLOGY"):
        cbit_changes = []
        relation_jaccards = []
        exact_relation_matches = 0
        for case_id in analysis["case_deltas"]["R1"]:
            totals = []
            relation_sets = []
            for replication_id in ("R1", "R2"):
                entries = [
                    value
                    for value in analysis["replication_ledgers"][
                        replication_id
                    ]["entries"]
                    if value["arm_id"] == arm_id
                    and value["case_id"] == case_id
                ]
                totals.append(sum(
                    value["realized_effective_cbit"] for value in entries
                ))
                projection = run["projections"][
                    f"{replication_id}:{arm_id}:{case_id}"
                ]
                relation_sets.append({
                    (
                        value["normalized_candidate"]["source_object_id"],
                        value["normalized_candidate"]["target_object_id"],
                    )
                    for value in projection["candidate_components"]
                    if value["disposition"] != "QUARANTINED_COMPONENT"
                })
            cbit_changes.append(abs(totals[1] - totals[0]))
            union = relation_sets[0] | relation_sets[1]
            jaccard = (
                len(relation_sets[0] & relation_sets[1]) / len(union)
                if union else 1.0
            )
            relation_jaccards.append(jaccard)
            exact_relation_matches += relation_sets[0] == relation_sets[1]
        arm_reproducibility[arm_id] = {
            "mean_absolute_cross_replication_cbit_change": round(
                sum(cbit_changes) / len(cbit_changes), 6
            ),
            "mean_relation_set_jaccard": round(
                sum(relation_jaccards) / len(relation_jaccards), 6
            ),
            "exact_relation_set_match_count": exact_relation_matches,
        }
    return {
        "status": "POSTHOC_DIAGNOSTIC_NOT_GATE",
        "pooled_delta_mean": round(
            sum(pooled_deltas) / len(pooled_deltas), 6
        ),
        "pooled_delta_median": round(median, 6),
        "pooled_positive_delta_sum": round(
            sum(value for value in pooled_deltas if value > 0), 6
        ),
        "pooled_negative_delta_sum": round(
            sum(value for value in pooled_deltas if value < 0), 6
        ),
        "arm_reproducibility": arm_reproducibility,
    }


def main():
    output = REPO_ROOT / "outputs" / "frontier_stability_v0_28"
    prior_analysis = read(output / "source_v0_27_analysis.json")
    prior_closure = read(output / "source_v0_27_closure.json")
    corpus = read(output / "frontier_stability_corpus_frozen.json")
    prereg = read(output / "frontier_stability_preregistration.json")
    run = read(output / "frontier_stability_run.json")
    analysis = read(output / "frontier_stability_analysis.json")
    posthoc = posthoc_stability_diagnostics(analysis, run)

    diagnostics_commitment = {
        "diagnostic_version": "frontier_stability_diagnostics_v0_28",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "raw_receipt_count": len(run["raw_receipts"]),
        "expected_receipt_count": (
            corpus["case_count"] * len(corpus["replication_ids"]) * 2
        ),
        "provider_failure_records": run["failures"],
        "raw_receipts_preserved_before_projection": run[
            "raw_receipts_preserved_before_projection"
        ],
        "replication_metrics": analysis["replication_metrics"],
        "pooled_case_win_rate": analysis["pooled_case_win_rate"],
        "cross_replication_positive_consistency": analysis[
            "cross_replication_positive_consistency"
        ],
        "pooled_severe_loss_rate": analysis[
            "pooled_severe_loss_rate"
        ],
        "pooled_frontier_cbit_delta": analysis[
            "pooled_frontier_cbit_delta"
        ],
        "cost": {
            "a0_total_tokens": analysis["a0_total_tokens"],
            "a1_total_tokens": analysis["a1_total_tokens"],
            "total_tokens": analysis["total_tokens"],
            "soft_expected_total_tokens": analysis[
                "soft_expected_total_tokens"
            ],
            "soft_cost_warning": analysis["soft_cost_warning"],
            "token_efficiency_is_acceptance_gate": False,
        },
        "posthoc_stability_diagnostics": posthoc,
        "external_semantic_panel_present": False,
        "cross_provider_stability_established": False,
        "synthetic_outcomes_are_real_world_truth": False,
    }
    diagnostics = {
        **diagnostics_commitment,
        "artifact_hash": hash_payload(diagnostics_commitment),
    }
    write(output / "frontier_stability_diagnostics.json", diagnostics)

    rows = [
        "| Rep | A0 Cbit/case | A1 Cbit/case | Gain | Wins | Ties | Losses | Severe losses | Frontier delta | A0 tokens | A1 tokens |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for replication_id, metric in analysis[
        "replication_metrics"
    ].items():
        rows.append(
            f"| {replication_id} | {metric['a0_cbit_per_case']:.3f} | "
            f"{metric['a1_cbit_per_case']:.3f} | "
            f"{metric['a1_gain_per_case']:.3f} | "
            f"{metric['case_win_count']} | {metric['case_tie_count']} | "
            f"{metric['case_loss_count']} | "
            f"{metric['severe_loss_count']} | "
            f"{metric['a1_frontier_cbit_delta']:.3f} | "
            f"{metric['a0_total_tokens']} | "
            f"{metric['a1_total_tokens']} |"
        )
    if analysis["stability_gate"] == "PASS":
        phenomena = [
            "Ontology-first cognition produced positive net realized Cbit gain in both order-isolated replications.",
            (
                "The gain survived explicit token-cost subtraction; additional "
                "tokens were accepted because net Cbit, not raw output volume, "
                "cleared the frozen gate."
            ),
            (
                "Frontier candidates did not require a lane bonus to contribute "
                "non-negative pooled outcome value."
            ),
        ]
        next_step = (
            "Send the frozen receipts to an independent external semantic "
            "panel. Do not authorize CoreSlim, retention, or baseline writes."
        )
    elif analysis["decision"] == "STOP_RESOURCE_RUNAWAY":
        phenomena = [
            "The run crossed the frozen resource runaway cap.",
            "No stability claim is authorized even if some Cbit metrics improved.",
        ]
        next_step = (
            "Stop and inspect transport or response-length tails before any "
            "fresh rerun."
        )
    else:
        phenomena = [
            "Ontology-first cognition did not produce sufficiently stable net Cbit gain across both replications.",
            "Negative and null outcomes remain part of the experiment record.",
        ]
        next_step = (
            "Stop without tuning on these labels; isolate the failed gate before "
            "designing another fresh holdout."
        )
    report = "\n".join([
        "# Frontier stability experiment v0.28",
        "",
        "## Observed facts",
        (
            f"- {len(run['raw_receipts'])}/"
            f"{diagnostics['expected_receipt_count']} Provider receipts were "
            "preserved before projection."
        ),
        (
            f"- Pooled case win rate: "
            f"{analysis['pooled_case_win_rate']:.3f}."
        ),
        (
            "- Cross-replication positive consistency: "
            f"{analysis['cross_replication_positive_consistency']:.3f}."
        ),
        (
            f"- Pooled severe-loss rate: "
            f"{analysis['pooled_severe_loss_rate']:.3f}."
        ),
        (
            f"- Pooled frontier Cbit delta: "
            f"{analysis['pooled_frontier_cbit_delta']:.3f}."
        ),
        (
            f"- A0/A1 tokens: {analysis['a0_total_tokens']}/"
            f"{analysis['a1_total_tokens']}; total "
            f"{analysis['total_tokens']}."
        ),
        (
            f"- Posthoc pooled mean/median A1 delta: "
            f"{posthoc['pooled_delta_mean']:.3f}/"
            f"{posthoc['pooled_delta_median']:.3f} Cbit per case."
        ),
        (
            "- Posthoc A0/A1 mean absolute cross-replication Cbit change: "
            f"{posthoc['arm_reproducibility']['A0_DIRECT']['mean_absolute_cross_replication_cbit_change']:.3f}/"
            f"{posthoc['arm_reproducibility']['A1_ONTOLOGY']['mean_absolute_cross_replication_cbit_change']:.3f}."
        ),
        (
            "- Posthoc A0/A1 relation-set Jaccard: "
            f"{posthoc['arm_reproducibility']['A0_DIRECT']['mean_relation_set_jaccard']:.3f}/"
            f"{posthoc['arm_reproducibility']['A1_ONTOLOGY']['mean_relation_set_jaccard']:.3f}."
        ),
        (
            f"- Soft cost warning: {analysis['soft_cost_warning']}; "
            "token efficiency was diagnostic, not an acceptance gate."
        ),
        "",
        *rows,
        "",
        "## Phenomena",
        *[f"- {value}" for value in phenomena],
        "",
        "## Interpretation boundary",
        "- Posthoc diagnostics describe the failure shape and do not modify the frozen gate or formal decision.",
        "- This tests order/context stability on synthetic object worlds, not cross-provider stability.",
        "- The same v0.27 Cbit weights were used; no frontier or ontology lane bonus was added.",
        "- Provider receipts remain candidate evidence and are not real-world truth.",
        "- The runtime preserved final authority and performed no CoreSlim, retention, baseline, selection, or production write.",
        "",
        "## Intuition prompts",
        "- Is the gain concentrated in object selection, counterevidence binding, or informative nulls?",
        "- Do any repeated case losses reveal a structural blind spot rather than stochastic variation?",
        "- Does the extra token cost buy new resolved uncertainty, or merely repeat the same reasoning?",
        "",
        "## Next step",
        next_step,
        "",
        f"Decision: `{analysis['decision']}`.",
        f"Candidate state: `{analysis['candidate_state']}`.",
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )

    ledger_commitment = {
        "ledger_version": "frontier_stability_closure_ledger_v0_28",
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": prereg["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_replication_ledger_hashes": {
            key: value["artifact_hash"]
            for key, value in analysis["replication_ledgers"].items()
        },
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "external_semantic_panel_authorized": analysis[
            "external_semantic_panel_authorized"
        ],
        "cross_provider_stability_established": False,
        "core_integration_authorized": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    ledger = {
        **ledger_commitment,
        "artifact_hash": hash_payload(ledger_commitment),
    }
    write(output / "ledger.json", ledger)

    replay_commitment = {
        "replay_version": "frontier_stability_replay_v0_28",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_frontier_stability.py",
            "python examples/run_frontier_stability.py",
            "python examples/finalize_frontier_stability.py",
            "pytest -q tests/test_frontier_stability_experiment.py",
        ],
        "provider_model": run["model_id"],
        "frozen_corpus_hash": corpus["artifact_hash"],
        "frozen_preregistration_hash": prereg["artifact_hash"],
        "warning": (
            "Replay creates new Provider evidence and is not the original run."
        ),
    }
    replay = {
        **replay_commitment,
        "artifact_hash": hash_payload(replay_commitment),
    }
    write(output / "replay.json", replay)

    rollback_commitment = {
        "rollback_version": "frontier_stability_rollback_v0_28",
        "isolated_output_directory": str(output),
        "rollback_action": (
            "Remove only this isolated experiment output directory."
        ),
        "agentos_core_files_touched": False,
        "retention_or_baseline_mutation_performed": False,
        "previous_candidate_state": prior_closure["candidate_state"],
    }
    rollback = {
        **rollback_commitment,
        "artifact_hash": hash_payload(rollback_commitment),
    }
    write(output / "rollback_pointer.json", rollback)

    closure_commitment = {
        "closure_version": "frontier_stability_closure_v0_28",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "stability_gate": analysis["stability_gate"],
        "external_semantic_panel_authorized": analysis[
            "external_semantic_panel_authorized"
        ],
        "cross_provider_stability_established": False,
        "core_integration_authorized": False,
        "promotion_allowed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    closure = {
        **closure_commitment,
        "artifact_hash": hash_payload(closure_commitment),
    }
    write(output / "closure.json", closure)

    inventory_names = [
        "source_v0_27_analysis.json",
        "source_v0_27_closure.json",
        "frontier_stability_corpus_frozen.json",
        "frontier_stability_preregistration.json",
        "frontier_stability_progress.json",
        "frontier_stability_run.json",
        "frontier_stability_analysis.json",
        "frontier_stability_diagnostics.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "frontier_stability_inventory_v0_28",
        "files": [
            {
                "path": name,
                "bytes": (output / name).stat().st_size,
                "sha256": sha256_file(output / name),
            }
            for name in inventory_names
        ],
    }
    inventory = {
        **inventory_commitment,
        "artifact_hash": hash_payload(inventory_commitment),
    }
    write(output / "hash_inventory.json", inventory)
    return_pack = output / "frontier_stability_v0_28_return_pack.zip"
    deterministic_zip(
        return_pack,
        [output / name for name in [*inventory_names, "hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "frontier_stability_manifest_v0_28",
        "return_pack": return_pack.name,
        "return_pack_sha256": sha256_file(return_pack),
        "return_pack_bytes": return_pack.stat().st_size,
        "inventory_hash": inventory["artifact_hash"],
        "closure_hash": closure["artifact_hash"],
    }
    manifest = {
        **manifest_commitment,
        "artifact_hash": hash_payload(manifest_commitment),
    }
    write(output / "manifest.json", manifest)
    print(json.dumps({
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "stability_gate": analysis["stability_gate"],
        "external_semantic_panel_authorized": analysis[
            "external_semantic_panel_authorized"
        ],
        "core_integration_authorized": False,
        "return_pack": str(return_pack),
        "return_pack_sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
