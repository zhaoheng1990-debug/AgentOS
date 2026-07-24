"""Close and package the v0.39 mathematically infeasible contract run."""
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
    output = REPO_ROOT / "outputs" / "truth_value_v0_39"
    corpus = read(output / "truth_value_corpus_frozen.json")
    preregistration = read(output / "truth_value_preregistration.json")
    progress = read(output / "truth_value_progress.json")
    progress_commitment = {
        key: value for key, value in progress.items()
        if key != "artifact_hash"
    }
    if progress["artifact_hash"] != hash_payload(progress_commitment):
        raise ValueError("progress_hash_invalid")
    expected = corpus["case_count"] * 3 * 2
    contract_failures = [
        value for value in progress["failures"]
        if value["stage"] == "STANDARD_TRUTH_VALUE_CONTRACT"
    ]
    invalid_count = len(contract_failures)
    maximum_possible_coverage = round(
        (expected - invalid_count) / expected, 6
    )
    threshold = preregistration["success_gate"][
        "minimum_standard_truth_value_contract_coverage"
    ]
    if maximum_possible_coverage >= threshold:
        raise ValueError("early_stop_not_mathematically_required")
    reason_counts = Counter(
        reason.split(":", 1)[0]
        for failure in contract_failures
        for reason in failure["failures"]
    )
    analysis_commitment = {
        "analysis_version": "truth_value_early_stop_v0_39",
        "source_progress_hash": progress["artifact_hash"],
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "completed_provider_call_count": progress[
            "completed_task_count"
        ],
        "expected_standard_call_count": expected,
        "observed_standard_contract_failure_count": invalid_count,
        "maximum_possible_standard_contract_coverage": (
            maximum_possible_coverage
        ),
        "frozen_minimum_standard_contract_coverage": threshold,
        "contract_failure_reason_counts": dict(reason_counts),
        "provider_calls_replayed": False,
        "private_synthetic_outcomes_used": False,
        "formal_benchmark_completed": False,
        "decision": "STOP_CONTRACT_INFEASIBLE",
        "candidate_state": "TRUTH_VALUE_CONTRACT_STOP",
        "external_semantic_panel_authorized": False,
        "core_integration_authorized": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    analysis = {
        **analysis_commitment,
        "artifact_hash": hash_payload(analysis_commitment),
    }
    write(output / "truth_value_early_stop_analysis.json", analysis)
    report = "\n".join([
        "# Truth-state / research-value separation v0.39",
        "",
        "## Early stop",
        (
            f"- Provider calls completed: "
            f"{progress['completed_task_count']}."
        ),
        (
            f"- Standard contract failures already observed: "
            f"{invalid_count}."
        ),
        (
            f"- Frozen minimum coverage: {threshold:.3f}; maximum possible "
            f"coverage after these failures: "
            f"{maximum_possible_coverage:.4f}."
        ),
        (
            "- Failure reasons: "
            f"{json.dumps(dict(reason_counts), sort_keys=True)}."
        ),
        "",
        "## Interpretation",
        (
            "- The contract incorrectly treated null discrimination as "
            "valid only when current evidence already supported a null."
        ),
        (
            "- Provider receipts used null discrimination prospectively: "
            "an indirect or weak candidate can still be valuable because a "
            "future null would rule out a plausible cause or constrain a "
            "boundary."
        ),
        (
            "- The next contract must model null information role as "
            "independent from current relation truth state."
        ),
        (
            "- No private outcomes were opened, no failed cell was replayed, "
            "and no CoreSlim, retention, baseline, selection, or production "
            "state was written."
        ),
        "",
        "Decision: `STOP_CONTRACT_INFEASIBLE`.",
        "Candidate state: `TRUTH_VALUE_CONTRACT_STOP`.",
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )
    ledger_commitment = {
        "ledger_version": "truth_value_early_stop_ledger_v0_39",
        "source_progress_hash": progress["artifact_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "decision": analysis["decision"],
        "candidate_state": analysis["candidate_state"],
        "formal_benchmark_completed": False,
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
        "replay_version": "truth_value_replay_v0_39",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_truth_value.py",
            "python examples/run_truth_value.py",
        ],
        "warning": (
            "Replay creates new Provider evidence and should stop once the "
            "frozen coverage gate becomes mathematically impossible."
        ),
    }
    replay = {
        **replay_commitment,
        "artifact_hash": hash_payload(replay_commitment),
    }
    write(output / "replay.json", replay)
    rollback_commitment = {
        "rollback_version": "truth_value_rollback_v0_39",
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
        "closure_version": "truth_value_closure_v0_39",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "formal_benchmark_completed": False,
        "promotion_allowed": False,
        "core_integration_authorized": False,
    }
    closure = {
        **closure_commitment,
        "artifact_hash": hash_payload(closure_commitment),
    }
    write(output / "closure.json", closure)
    names = [
        "source_v0_38_analysis.json",
        "source_v0_38_closure.json",
        "source_v0_38_posthoc.json",
        "truth_value_corpus_frozen.json",
        "truth_value_preregistration.json",
        "truth_value_progress.json",
        "truth_value_early_stop_analysis.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "truth_value_inventory_v0_39",
        "files": [
            {
                "path": name,
                "bytes": (output / name).stat().st_size,
                "sha256": sha(output / name),
            }
            for name in names
        ],
    }
    inventory = {
        **inventory_commitment,
        "artifact_hash": hash_payload(inventory_commitment),
    }
    write(output / "hash_inventory.json", inventory)
    pack = output / "truth_value_v0_39_return_pack.zip"
    zip_pack(
        pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "truth_value_manifest_v0_39",
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
        "maximum_possible_coverage": maximum_possible_coverage,
        "return_pack": str(pack),
        "sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
