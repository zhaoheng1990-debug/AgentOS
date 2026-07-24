"""Close and package the v0.25 immutable span-ID funnel smoke."""

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
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(files, key=lambda value: value.name):
            info = zipfile.ZipInfo(source.name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def main():
    output = REPO_ROOT / "outputs" / "span_id_funnel_v0_25"
    prereg = read(output / "span_id_funnel_preregistration.json")
    corpus = read(output / "span_id_funnel_corpus_frozen.json")
    run = read(output / "span_id_funnel_run.json")
    analysis = read(output / "span_id_funnel_analysis.json")
    telemetry = read(output / "span_id_funnel_telemetry.json")
    bindings = corpus["private_provenance"]["bindings"]
    transition_counts = Counter()
    mismatch_records = []
    for conflict_id, receipt in run["source_status_receipts"].items():
        expected = bindings[conflict_id]["source_status"]
        observed = receipt["definition_source_status"]
        transition_counts[f"{expected}->{observed}"] += 1
        if expected != observed:
            mismatch_records.append({
                "conflict_id": conflict_id,
                "case_id": bindings[conflict_id]["case_id"],
                "expected_source_status": expected,
                "observed_source_status": observed,
                "requested_object_span_ids": receipt[
                    "requested_object_span_ids"
                ],
                "source_status_span_ids": receipt[
                    "source_status_span_ids"
                ],
                "provider_rationale": receipt["rationale"],
            })

    diagnostics = {
        "diagnostic_version": "span_id_funnel_diagnostics_v0_25",
        "source_run_hash": run["run_hash"],
        "provider_completed_source_status_counts": dict(Counter(
            call["normalized_result"]["definition_source_status"]
            for call in run["provider_calls"]
            if call["stage"] == "SOURCE_STATUS"
            and call["status"] == "COMPLETED"
            and call["normalized_result"]
        )),
        "validated_source_status_counts": analysis[
            "source_status_distribution"
        ],
        "failure_records": run["failures"],
        "quote_copy_transport_present": False,
        "runtime_owned_span_pack_count": len(run["evidence_span_packs"]),
        "source_status_transition_counts": dict(transition_counts),
        "source_status_mismatch_records": mismatch_records,
        "semantic_reference_available": False,
    }
    diagnostics["artifact_hash"] = hash_payload(diagnostics)
    write(output / "span_id_funnel_diagnostics.json", diagnostics)

    observations = [
        (
            f"Runtime generated and revalidated "
            f"{len(run['evidence_span_packs'])}/{corpus['case_count']} "
            "immutable evidence span packs."
        ),
        (
            f"{len(run['source_status_receipts'])}/{corpus['case_count']} "
            "source receipts passed ID and relation validation."
        ),
        (
            f"Source-status construction match was "
            f"{analysis['source_status_construction_match_rate']}; false "
            f"AVAILABLE promotions were "
            f"{analysis['false_available_promotion_count']}."
        ),
        (
            f"{analysis['entailment_call_count']} AVAILABLE branches were "
            f"routed to entailment; output coverage was "
            f"{analysis['output_coverage']}."
        ),
        (
            f"The run used {analysis['provider_call_count']} calls and "
            f"{analysis['total_tokens']} tokens."
        ),
    ]
    if analysis["structural_smoke_gate"] == "PASS":
        interpretation = [
            "Immutable Runtime-owned span references removed quote-copy transport failures on this fresh synthetic smoke.",
            "The result authorizes a larger fresh holdout only; it does not establish semantic correctness or production fitness.",
        ]
        next_step = (
            "Freeze v0.26 full fresh holdout before any prompt or threshold "
            "change; retain the same span contract and cost gate."
        )
    else:
        interpretation = [
            "The transport contract succeeded, so the rejection localizes to source-status semantics and the resulting cost expansion.",
            "Both MISSING objects collapsed to UNSPECIFIED; both UNSPECIFIED and both CONFLICTED objects were promoted to AVAILABLE.",
            "The conflicted receipts selected only the first local definition, consistent with premature closure before an all-span counterevidence scan.",
            "The failed mechanism must stop here; no full holdout or external panel is authorized.",
        ]
        next_step = (
            "Diagnose the failed gate without rerunning or tuning on these "
            "eight objects; any repair requires another fresh smoke."
        )
    report = "\n".join([
        "# Immutable span-ID funnel v0.25 closure",
        "",
        "## Observations",
        *[f"- {value}" for value in observations],
        "",
        "## Interpretation",
        *[f"- {value}" for value in interpretation],
        "",
        "## Unknowns",
        "- Synthetic construction metadata is not external semantic gold.",
        "- Eight objects cannot estimate generalization or role-calibration gain.",
        "- Span granularity may alter difficulty on longer or nested evidence.",
        "",
        "## Intuition prompts",
        "- Is evidence identity a more stable collaboration primitive than evidence prose?",
        "- Does source-status cognition improve when evidence transport is no longer a generation task?",
        "- At what span granularity does mechanical integrity begin to hide semantic ambiguity?",
        "",
        "## Next step",
        next_step,
        "",
        f"Candidate state: `{analysis['candidate_state']}`.",
        "No retention, baseline, selection, or production authority is granted.",
    ])
    (output / "experiment_report.md").write_text(report, encoding="utf-8")

    ledger_commitment = {
        "ledger_version": "span_id_funnel_ledger_v0_25",
        "source_preregistration_hash": prereg["artifact_hash"],
        "source_corpus_hash": corpus["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_telemetry_hash": telemetry["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "structural_smoke_gate": analysis["structural_smoke_gate"],
        "full_fresh_holdout_authorized": analysis[
            "full_fresh_holdout_authorized"
        ],
        "external_panel_generated": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    ledger = {**ledger_commitment, "artifact_hash": hash_payload(ledger_commitment)}
    write(output / "ledger.json", ledger)

    replay_commitment = {
        "replay_version": "span_id_funnel_replay_v0_25",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_span_id_funnel_smoke.py",
            "python examples/run_span_id_funnel_smoke.py",
            "python examples/finalize_span_id_funnel_smoke.py",
            "pytest -q",
        ],
        "frozen_corpus_hash": corpus["artifact_hash"],
        "frozen_preregistration_hash": prereg["artifact_hash"],
        "provider_model": "deepseek-r1:32b",
        "warning": "Replay creates new Provider evidence and is not the original run.",
    }
    replay = {**replay_commitment, "artifact_hash": hash_payload(replay_commitment)}
    write(output / "replay.json", replay)

    rollback_commitment = {
        "rollback_version": "span_id_funnel_rollback_v0_25",
        "isolated_output_directory": str(output),
        "rollback_action": "Remove only this isolated experiment output directory.",
        "agentos_core_files_touched": False,
        "retention_or_baseline_mutation_performed": False,
        "previous_candidate_state": "CANDIDATE_BLIND_FUNNEL_SMOKE_REJECTED_STOP",
    }
    rollback = {
        **rollback_commitment,
        "artifact_hash": hash_payload(rollback_commitment),
    }
    write(output / "rollback_pointer.json", rollback)

    closure_commitment = {
        "closure_version": "span_id_funnel_closure_v0_25",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "structural_smoke_gate": analysis["structural_smoke_gate"],
        "full_fresh_holdout_authorized": analysis[
            "full_fresh_holdout_authorized"
        ],
        "external_panel_generated": False,
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
        "span_id_funnel_preregistration.json",
        "span_id_funnel_corpus_frozen.json",
        "span_id_funnel_run.json",
        "span_id_funnel_analysis.json",
        "span_id_funnel_telemetry.json",
        "span_id_funnel_diagnostics.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "span_id_funnel_inventory_v0_25",
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

    return_pack = output / "span_id_funnel_v0_25_return_pack.zip"
    deterministic_zip(
        return_pack,
        [output / name for name in [*inventory_names, "hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "span_id_funnel_manifest_v0_25",
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
        "structural_smoke_gate": analysis["structural_smoke_gate"],
        "full_fresh_holdout_authorized": analysis[
            "full_fresh_holdout_authorized"
        ],
        "external_panel_generated": False,
        "return_pack": str(return_pack),
        "return_pack_sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
