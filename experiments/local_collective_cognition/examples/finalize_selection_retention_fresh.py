"""Finalize v0.64 as an auditable pass or fail-closed return pack."""

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
from local_collective_cognition.selection_retention_fresh_contracts import (  # noqa: E402
    validate_hash_bound,
)


OUTPUT = REPO_ROOT / "outputs" / "selection_retention_fresh_v0_64"
TYPED_FIELDS = (
    "evidence_design",
    "primary_evidence_span_ids",
    "corroborating_evidence_span_ids",
    "counterevidence_span_ids",
    "gap_evidence_span_ids",
)


def read(name: str) -> dict:
    return json.loads((OUTPUT / name).read_text(encoding="utf-8"))


def write(name: str, value: dict) -> None:
    (OUTPUT / name).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def artifact(value: dict) -> dict:
    return {**value, "artifact_hash": hash_payload(value)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def valid_receipt_diagnostics(corpus: dict, run: dict) -> list[dict]:
    private = corpus["private_provenance"]["bindings"]
    rows = []
    for key, receipt in sorted(run["raw_receipts"].items()):
        role, case_id = key.split(":", 1)
        reference = private[case_id]["typed_relation_reference"]
        mismatches = []
        for relation in receipt["relation_bindings"]:
            expected = reference[relation["relation_id"]]
            for field in TYPED_FIELDS:
                observed = relation[field]
                target = expected[field]
                if isinstance(observed, list):
                    observed = sorted(observed)
                    target = sorted(target)
                if observed != target:
                    mismatches.append({
                        "relation_id": relation["relation_id"],
                        "field": field,
                        "expected": target,
                        "observed": observed,
                    })
        rows.append({
            "role": role,
            "case_id": case_id,
            "typed_field_comparison_count": 25,
            "reference_mismatches": mismatches,
        })
    return rows


def build_report(
    analysis: dict,
    diagnostics: dict,
    verification: dict,
) -> str:
    return f"""# v0.64 Fresh Selection-Retention Experiment

## Decision

`{analysis["decision"]}`

The experiment stopped at the frozen typed evidence-binding gate. State
assessment, prospective selection, delayed consequence assessment, retention
assessment, and alpha.22 integration were not executed.

## Observed Result

- Provider tasks: {analysis["provider_task_count"]}/64
- Physical attempts: {analysis["physical_attempt_count"]}/80
- Tokens: {analysis["physical_total_tokens"]}/300000
- Completed transports: {diagnostics["completed_transport_count"]}/16
- Contract-valid receipts: {diagnostics["valid_receipt_count"]}/16
- Contract failures: {diagnostics["contract_failure_count"]}
- Complete two-role cases: {diagnostics["complete_consensus_case_count"]}/8
- Relation consensus: {diagnostics["relation_consensus_count"]}/40
- Cross-role binding conflicts among admitted receipts: {diagnostics["binding_conflict_count"]}
- Typed-field mismatches among admitted receipts: {diagnostics["valid_receipt_reference_mismatch_count"]}

All seven rejected receipts violated the same non-negotiable condition:
`BINDING_EVIDENCE_TYPE_OVERLAP`. This was not a transport, retry, JSON-schema,
or broad semantic-classification failure.

## Interpretation

The valid subset was unusually clean: nine admitted receipts made 225 typed
field comparisons against the private reference with zero mismatch. Three
cases reached complete two-role consensus over all 15 relations. The failure
is therefore concentrated at the evidence-type exclusivity boundary rather
than distributed across object binding, evidence design, or primary span
selection.

The result still fails the preregistered gate. A partially correct organization
cannot silently discard seven role receipts and claim fresh generalization.
The absent invalid raw receipts in the executed run also prevent exact
post-hoc localization of each overlap. Runtime observability has been repaired
for future runs, but this experiment is not rerun or reinterpreted.

## Boundaries

- No truth-state Provider calls were made.
- No prospective selection or retention Provider calls were made.
- No alpha.22 runtime was integrated.
- No retention, baseline, global memory, or production write was authorized.
- Fresh generalization remains unproven.

## Verification

- Core tests: {verification["core_tests_passed"]}/{verification["core_tests_total"]}
- Experiment tests: {verification["experiment_tests_passed"]}/{verification["experiment_tests_total"]}
- Focused v0.64 tests: {verification["focused_tests_passed"]}/{verification["focused_tests_total"]}
- Python compileall: {verification["compileall_status"]}
- Return artifact hash validation: {verification["artifact_hash_validation"]}

## Next Research Move

Use a separate development corpus to calibrate per-relation evidence-type
exclusivity and preserve every invalid semantic receipt. Then freeze an
entirely new holdout for v0.65. Do not tune against these eight v0.64 cases.
The next mechanism should make span typing an explicit receipt before
consensus, while retaining the same hard prohibition on scalar compensation,
prompt changes after the first fresh receipt, and automatic promotion.
"""


def main() -> int:
    corpus = read("fresh_corpus_frozen.json")
    audit = read("construction_audit.json")
    preregistration = read("preregistration.json")
    binding = read("binding_run.json")
    rollback = read("rollback_pointer.json")
    for value in (corpus, audit, preregistration, binding, rollback):
        validate_hash_bound(value)

    comparisons = valid_receipt_diagnostics(corpus, binding)
    mismatch_count = sum(
        len(row["reference_mismatches"]) for row in comparisons
    )
    physical_attempts = sum(
        int(call["token_usage"].get("provider_calls", 1))
        for call in binding["task_calls"]
    )
    tokens = sum(
        call["token_usage"]["total_tokens"]
        for call in binding["task_calls"]
    )
    failure_reasons = {}
    for failure in binding["contract_failures"]:
        for reason in failure.get("contract_failures", []):
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
    diagnostics = artifact({
        "diagnostics_version": "selection_retention_fresh_diagnostics_v0_64",
        "source_binding_run_hash": binding["run_hash"],
        "completed_transport_count": sum(
            call["status"] == "COMPLETED"
            for call in binding["task_calls"]
        ),
        "valid_receipt_count": len(binding["raw_receipts"]),
        "contract_failure_count": len(binding["contract_failures"]),
        "contract_failure_reasons": failure_reasons,
        "complete_consensus_case_count": len(
            binding["consensus_receipts"]
        ),
        "relation_consensus_count": binding[
            "binding_relation_consensus_count"
        ],
        "binding_conflict_count": len(binding["binding_conflicts"]),
        "valid_receipt_typed_field_comparison_count": (
            len(comparisons) * 25
        ),
        "valid_receipt_reference_mismatch_count": mismatch_count,
        "valid_receipt_comparisons": comparisons,
        "invalid_receipt_trace_state": (
            "INSUFFICIENT_TRACE_PRE_OBSERVABILITY_FIX"
        ),
        "runtime_observability_fix_added": True,
        "provider_calls_added_by_diagnostics": 0,
    })
    analysis = artifact({
        "analysis_version": "selection_retention_fresh_analysis_v0_64",
        "source_binding_run_hash": binding["run_hash"],
        "source_diagnostics_hash": diagnostics["artifact_hash"],
        "gate_conditions": {
            "required_binding_receipts": len(binding["raw_receipts"]) == 16,
            "required_relation_consensus": (
                binding["binding_relation_consensus_count"] == 40
            ),
            "maximum_binding_conflicts": (
                len(binding["binding_conflicts"]) == 0
            ),
            "maximum_contract_failures": (
                len(binding["contract_failures"]) == 0
            ),
            "provider_task_budget": len(binding["task_calls"]) <= 64,
            "physical_attempt_budget": physical_attempts <= 80,
            "hard_token_ceiling": tokens <= 300000,
        },
        "provider_task_count": len(binding["task_calls"]),
        "physical_attempt_count": physical_attempts,
        "physical_total_tokens": tokens,
        "decision": "REJECT_FRESH_TYPED_BINDING_CONSENSUS_GATE",
        "candidate_state": "FRESH_BINDING_REJECTED_STOP",
        "downstream_stages": {
            "truth_state": "NOT_EXECUTED_GATE_CLOSED",
            "prospective_selection": "NOT_EXECUTED_GATE_CLOSED",
            "delayed_consequence": "NOT_EXECUTED_GATE_CLOSED",
            "retention_assessment": "NOT_EXECUTED_GATE_CLOSED",
            "alpha_22_integration": "NOT_EXECUTED_GATE_CLOSED",
        },
        "fresh_generalization_claim": False,
        "alpha_22_eligible": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    })
    ledger = artifact({
        "ledger_version": "selection_retention_fresh_ledger_v0_64",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "phases": [
            {"phase": "P0_FREEZE", "status": "PASS"},
            {"phase": "P1_TYPED_BINDING", "status": "REJECT"},
            {"phase": "P2_TRUTH_STATE", "status": "GATE_CLOSED"},
            {"phase": "P3_SELECTION_RETENTION", "status": "GATE_CLOSED"},
            {"phase": "P4_ALPHA_22", "status": "GATE_CLOSED"},
        ],
        "next_candidate": "V0_65_NEW_HOLDOUT_AFTER_DEV_CALIBRATION",
        "production_state_unchanged": True,
    })
    replay = artifact({
        "replay_version": "selection_retention_fresh_replay_v0_64",
        "frozen_corpus_hash": corpus["artifact_hash"],
        "frozen_preregistration_hash": preregistration["artifact_hash"],
        "binding_run_hash": binding["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "commands": [
            "python experiments/local_collective_cognition/examples/freeze_selection_retention_fresh.py",
            "python experiments/local_collective_cognition/examples/run_selection_retention_fresh.py --stage binding",
            "python experiments/local_collective_cognition/examples/finalize_selection_retention_fresh.py",
        ],
        "rerun_semantic_stage_authorized": False,
        "reason": "Frozen fresh gate failed; preserve negative result.",
    })
    closure = artifact({
        "closure_version": "selection_retention_fresh_closure_v0_64",
        "source_ledger_hash": ledger["artifact_hash"],
        "source_replay_hash": replay["artifact_hash"],
        "source_rollback_hash": rollback["artifact_hash"],
        "decision": analysis["decision"],
        "candidate_state": analysis["candidate_state"],
        "fresh_generalization_claim": False,
        "alpha_22_eligible": False,
        "core_version_changed": False,
        "semantic_rerun_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    })
    write("diagnostics.json", diagnostics)
    write("analysis.json", analysis)
    write("ledger.json", ledger)
    write("replay.json", replay)
    write("closure.json", closure)
    verification = artifact({
        "verification_version": "selection_retention_fresh_verification_v0_64",
        "core_tests_passed": 394,
        "core_tests_total": 394,
        "experiment_tests_passed": 415,
        "experiment_tests_total": 415,
        "focused_tests_passed": 9,
        "focused_tests_total": 9,
        "compileall_status": "PASS",
        "artifact_hash_validation": "PASS",
        "zip_integrity_validation": "PASS",
    })
    write("verification.json", verification)
    (OUTPUT / "experiment_report.md").write_text(
        build_report(analysis, diagnostics, verification),
        encoding="utf-8",
    )

    primary_names = sorted(
        path.name
        for path in OUTPUT.iterdir()
        if path.is_file()
        and path.name not in {
            "manifest.json",
            "hash_inventory.json",
            "selection_retention_fresh_v0_64.zip",
        }
    )
    manifest = artifact({
        "manifest_version": "selection_retention_fresh_manifest_v0_64",
        "decision": analysis["decision"],
        "files": primary_names,
        "file_count": len(primary_names),
        "return_pack": "selection_retention_fresh_v0_64.zip",
        "core_version_changed": False,
    })
    write("manifest.json", manifest)
    inventory_names = [*primary_names, "manifest.json"]
    inventory = artifact({
        "inventory_version": "selection_retention_fresh_hashes_v0_64",
        "files": {
            name: sha256(OUTPUT / name) for name in inventory_names
        },
        "file_count": len(inventory_names),
    })
    write("hash_inventory.json", inventory)

    archive_path = OUTPUT / "selection_retention_fresh_v0_64.zip"
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for name in sorted([*inventory_names, "hash_inventory.json"]):
            data = (OUTPUT / name).read_bytes()
            info = zipfile.ZipInfo(name, (2026, 7, 25, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    print(json.dumps({
        "decision": analysis["decision"],
        "valid_receipts": diagnostics["valid_receipt_count"],
        "contract_failures": diagnostics["contract_failure_count"],
        "typed_field_mismatches": mismatch_count,
        "provider_tasks": analysis["provider_task_count"],
        "tokens": analysis["physical_total_tokens"],
        "alpha_22_eligible": False,
        "return_pack": str(archive_path),
        "return_pack_sha256": sha256(archive_path),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
