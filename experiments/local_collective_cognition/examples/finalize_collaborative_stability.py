"""Close and package the v0.29 collaborative stability experiment."""

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
from local_collective_cognition.collaborative_stability_posthoc import (  # noqa: E402
    analyze_collaborative_posthoc,
)


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


def main():
    output = REPO_ROOT / "outputs" / "collaborative_stability_v0_29"
    prior_analysis = read(output / "source_v0_28_analysis.json")
    prior_closure = read(output / "source_v0_28_closure.json")
    corpus = read(
        output / "collaborative_stability_corpus_frozen.json"
    )
    prereg = read(
        output / "collaborative_stability_preregistration.json"
    )
    run = read(output / "collaborative_stability_run.json")
    analysis = read(output / "collaborative_stability_analysis.json")
    posthoc = analyze_collaborative_posthoc(
        corpus=corpus, run=run, analysis=analysis
    )
    write(output / "posthoc_routing_diagnostics.json", posthoc)

    role_selection = Counter()
    pool_relation_counts = []
    for key, selector in run["selector_receipts"].items():
        pool = run["candidate_pools"][key]
        pool_by_id = {
            value["pool_candidate_id"]: value
            for value in pool["candidates"]
        }
        pool_relation_counts.append(len({
            (
                value["candidate"]["source_object_id"],
                value["candidate"]["target_object_id"],
            )
            for value in pool["candidates"]
        }))
        for selected_id in selector.get("selected_candidate_ids", ()):
            if selected_id in pool_by_id:
                role_selection[
                    pool_by_id[selected_id]["role_id"]
                ] += 1
    failed_conditions = sorted(
        key for key, value in analysis["conditions"].items()
        if value is False
    )
    diagnostics_commitment = {
        "diagnostic_version": "collaborative_stability_diagnostics_v0_29",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "raw_receipt_count": len(run["raw_receipts"]),
        "expected_raw_receipt_count": (
            corpus["case_count"] * len(corpus["replication_ids"]) * 6
        ),
        "provider_failure_records": run["failures"],
        "raw_receipts_preserved_before_projection": run[
            "raw_receipts_preserved_before_projection"
        ],
        "runtime_metrics": analysis["runtime_metrics"],
        "pooled_contrast_metrics": analysis[
            "pooled_contrast_metrics"
        ],
        "majority_positive_case_rates": analysis[
            "majority_positive_case_rates"
        ],
        "relation_reproducibility": analysis[
            "relation_reproducibility"
        ],
        "selected_candidate_source_role_counts": dict(role_selection),
        "mean_distinct_relations_per_candidate_pool": round(
            sum(pool_relation_counts) / len(pool_relation_counts), 6
        ) if pool_relation_counts else 0.0,
        "failed_frozen_conditions": failed_conditions,
        "posthoc_routing_diagnostics_hash": posthoc["artifact_hash"],
        "cost": {
            "total_tokens": analysis["total_tokens"],
            "soft_expected_total_tokens": analysis[
                "soft_expected_total_tokens"
            ],
            "soft_cost_warning": analysis["soft_cost_warning"],
            "all_a2_tokens_charged": analysis["conditions"][
                "all_a2_tokens_charged"
            ],
            "token_efficiency_is_acceptance_gate": False,
        },
        "external_semantic_panel_present": False,
        "cross_provider_stability_established": False,
        "synthetic_outcomes_are_real_world_truth": False,
    }
    diagnostics = {
        **diagnostics_commitment,
        "artifact_hash": hash_payload(diagnostics_commitment),
    }
    write(
        output / "collaborative_stability_diagnostics.json",
        diagnostics,
    )

    rows = [
        "| Rep | A0 Cbit/case | A1 Cbit/case | A2 Cbit/case | A1-A0 mean | A2-A1 mean | A2-A1 median | A2-A1 wins |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for replication_id, metric in analysis[
        "replication_metrics"
    ].items():
        arms = metric["arm_cbit_per_case"]
        a1a0 = metric["contrasts"]["A1_MINUS_A0"]
        a2a1 = metric["contrasts"]["A2_MINUS_A1"]
        rows.append(
            f"| {replication_id} | {arms['A0_DIRECT']:.3f} | "
            f"{arms['A1_ONTOLOGY']:.3f} | "
            f"{arms['A2_COLLAB']:.3f} | {a1a0['mean']:.3f} | "
            f"{a2a1['mean']:.3f} | {a2a1['median']:.3f} | "
            f"{a2a1['win_count']}/{a2a1['count']} |"
        )
    a1a0 = analysis["pooled_contrast_metrics"]["A1_MINUS_A0"]
    a2a1 = analysis["pooled_contrast_metrics"]["A2_MINUS_A1"]
    a2a0 = analysis["pooled_contrast_metrics"]["A2_MINUS_A0"]
    if analysis["collaborative_stability_gate"] == "PASS":
        phenomena = [
            "Role collaboration improved both mean and median net Cbit beyond the equal-count ontology baseline.",
            "The gain survived full proposer and selector token charging and majority-stability gates.",
            "Evidence-only selection converted a diverse candidate pool into a stable three-relation final receipt without generating new candidates.",
        ]
        next_step = (
            "Generate an independent GPT/Gemini/Kimi semantic panel packet "
            "before considering any generalized runtime candidate."
        )
    elif analysis["decision"] == "STOP_RESOURCE_RUNAWAY":
        phenomena = [
            "The collaboration pipeline crossed the frozen runaway cap.",
            "No cognitive-gain claim is authorized regardless of partial scores.",
        ]
        next_step = (
            "Stop and inspect response or retry tails before another fresh run."
        )
    else:
        phenomena = [
            "Role collaboration failed at least one frozen stability or net-Cbit condition.",
            (
                "The failure shape distinguishes candidate-volume control, "
                "selector quality, relation reproducibility, and full "
                "coordination cost."
            ),
            "Negative and null outcomes remain preserved; no threshold was changed after freeze.",
        ]
        next_step = (
            "Stop v0.29. Use the failed-condition and object-level contrasts "
            "to select one new mechanism; do not tune on these ten labels."
        )
    report = "\n".join([
        "# Role-collaborative cognitive stabilization v0.29",
        "",
        "## Observed facts",
        (
            f"- {len(run['raw_receipts'])}/"
            f"{diagnostics['expected_raw_receipt_count']} raw Provider "
            "receipts were preserved."
        ),
        (
            f"- Equal-count A1-A0 mean/median: {a1a0['mean']:.3f}/"
            f"{a1a0['median']:.3f} Cbit per case."
        ),
        (
            f"- Full-cost A2-A1 mean/median: {a2a1['mean']:.3f}/"
            f"{a2a1['median']:.3f}; win rate {a2a1['win_rate']:.3f}."
        ),
        (
            f"- Full-cost A2-A0 mean/median: {a2a0['mean']:.3f}/"
            f"{a2a0['median']:.3f}."
        ),
        (
            "- Majority-positive case rate for A2-A1: "
            f"{analysis['majority_positive_case_rates']['A2_MINUS_A1']:.3f}."
        ),
        (
            "- A1/A2 relation-set reproducibility: "
            f"{analysis['relation_reproducibility']['A1_ONTOLOGY']['mean_pairwise_relation_jaccard']:.3f}/"
            f"{analysis['relation_reproducibility']['A2_COLLAB']['mean_pairwise_relation_jaccard']:.3f}."
        ),
        (
            f"- Total physical tokens: {analysis['total_tokens']}; "
            f"soft warning: {analysis['soft_cost_warning']}."
        ),
        (
            "- Failed frozen conditions: "
            + (", ".join(failed_conditions) if failed_conditions else "none")
            + "."
        ),
        (
            "- Posthoc role-router oracle mean/median net gain: "
            f"{posthoc['pre_execution_role_router_oracle']['mean']:.3f}/"
            f"{posthoc['pre_execution_role_router_oracle']['median']:.3f}; "
            f"wins {posthoc['pre_execution_role_router_oracle']['win_count']}/"
            f"{posthoc['pre_execution_role_router_oracle']['count']}."
        ),
        (
            "- Posthoc full-pool oracle gross/net mean delta versus A1: "
            f"{posthoc['full_pool_oracle']['gross_delta_vs_a1']['mean']:.3f}/"
            f"{posthoc['full_pool_oracle']['net_delta_vs_a1_after_full_collaboration_cost']['mean']:.3f}."
        ),
        "",
        *rows,
        "",
        "## Phenomena",
        *[f"- {value}" for value in phenomena],
        "",
        "## Interpretation boundary",
        "- Posthoc oracle results use private synthetic outcomes only to estimate headroom; they are not deployable policies and do not change the frozen rejection.",
        "- All arms produced exactly three final candidates when the contract was satisfied.",
        "- A2 paid for three isolated proposers plus the evidence selector; Cbit per token was not a separate gate.",
        "- The selector could only choose pool IDs and could not synthesize a new candidate.",
        "- Synthetic outcome metadata is not real-world truth or cross-provider validation.",
        "- No CoreSlim, retention, baseline, selection, or production write occurred.",
        "",
        "## Intuition prompts",
        "- Did the selector combine complementary roles, or repeatedly favor one role?",
        "- Did collaboration improve the median object, or only discover rare large winners?",
        "- Is any loss caused by weak proposal diversity, selector ranking, or collaboration cost?",
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
        "ledger_version": "collaborative_stability_closure_ledger_v0_29",
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
        "replay_version": "collaborative_stability_replay_v0_29",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_collaborative_stability.py",
            "python examples/run_collaborative_stability.py",
            "python examples/finalize_collaborative_stability.py",
            "pytest -q tests/test_collaborative_stability_experiment.py",
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
        "rollback_version": "collaborative_stability_rollback_v0_29",
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
        "closure_version": "collaborative_stability_closure_v0_29",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "collaborative_stability_gate": analysis[
            "collaborative_stability_gate"
        ],
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
        "source_v0_28_analysis.json",
        "source_v0_28_closure.json",
        "collaborative_stability_corpus_frozen.json",
        "collaborative_stability_preregistration.json",
        "collaborative_stability_progress.json",
        "collaborative_stability_run.json",
        "collaborative_stability_analysis.json",
        "collaborative_stability_diagnostics.json",
        "posthoc_routing_diagnostics.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "collaborative_stability_inventory_v0_29",
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
    return_pack = (
        output / "collaborative_stability_v0_29_return_pack.zip"
    )
    deterministic_zip(
        return_pack,
        [output / name for name in [*inventory_names, "hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "collaborative_stability_manifest_v0_29",
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
        "collaborative_stability_gate": analysis[
            "collaborative_stability_gate"
        ],
        "external_semantic_panel_authorized": analysis[
            "external_semantic_panel_authorized"
        ],
        "core_integration_authorized": False,
        "return_pack": str(return_pack),
        "return_pack_sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
