"""Close v0.23 as a structural failure without external annotation."""

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

from local_collective_cognition.cognitive_action_relational_witness_holdout import (  # noqa: E402
    CASES,
    evidence_text,
)
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
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_deterministic_zip(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source, member_name in members:
            info = zipfile.ZipInfo(
                member_name,
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes())


def build_diagnostics(corpus, run, analysis):
    case_by_id = {case.case_id: case for case in CASES}
    bindings = corpus["private_provenance"]["bindings"]
    public = {
        item["conflict_id"]: item
        for item in corpus["public_surface"]["items"]
    }
    call_receipts = {
        (call["stage"], call["conflict_id"]): call["normalized_result"]
        for call in run["provider_calls"]
    }
    records, categories = [], Counter()
    for failure in run["failures"]:
        conflict_id = failure["conflict_id"]
        case = case_by_id[bindings[conflict_id]["case_id"]]
        if failure["stage"] != "RELATIONAL_WITNESS":
            category = "BASELINE_GATE_FAILURE"
            receipt = call_receipts.get(("BASELINE_SOURCE", conflict_id))
            checks = {}
        else:
            receipt = failure.get("provider_receipt_preserved") or {}
            checks = _receipt_checks(
                receipt,
                item=public[conflict_id],
                design_stratum=case.design_stratum,
            )
            category = _primary_category(checks)
        categories[category] += 1
        records.append({
            "conflict_id": conflict_id,
            "case_id": case.case_id,
            "object_family": case.object_family,
            "design_stratum": case.design_stratum,
            "stage": failure["stage"],
            "status": failure["status"],
            "validation_errors": failure["validation_errors"],
            "primary_failure_category": category,
            "mechanical_checks": checks,
            "provider_receipt": receipt,
        })
    commitment = {
        "diagnostic_version": (
            "relational_witness_structural_diagnostics_v0_23"
        ),
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "failure_category_counts": dict(categories),
        "failure_records": records,
        "completed_relational_witness_count": (
            analysis["completed_challenge_count"]
        ),
        "external_panel_informative": False,
        "post_hoc_diagnostic_only": True,
        "construction_strata_are_not_reference_truth": True,
        "gate_effect": False,
        "reference_revision_allowed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _receipt_checks(receipt, *, item, design_stratum):
    text = evidence_text(item)
    spans = receipt.get("support_spans")
    status = receipt.get("definition_source_status")
    relation = receipt.get("support_relation")
    expected_status = {
        "POSITIVE_DEFINITION": "AVAILABLE",
        "COMPOSITIONAL_DERIVATION": "AVAILABLE",
        "OPEN_SURFACE": "UNSPECIFIED",
        "MISSING_SPECIFICATION": "MISSING",
    }[design_stratum]
    return {
        "requested_object_quote_exact_pre_candidate": (
            receipt.get("requested_object_quote") in text
        ),
        "source_status_quote_exact_pre_candidate": (
            receipt.get("source_status_quote") in text
        ),
        "source_status_quote_is_support_span_member": (
            isinstance(spans, list)
            and receipt.get("source_status_quote") in spans
        ),
        "all_support_spans_exact_pre_candidate": (
            isinstance(spans, list)
            and bool(spans)
            and all(
                isinstance(span, str) and span in text for span in spans
            )
        ),
        "candidate_option_text_declared_unused": (
            receipt.get("candidate_option_text_used_as_evidence") is False
        ),
        "source_status_matches_private_construction": (
            status == expected_status
        ),
        "available_defines_has_explanatory_steps": (
            status == "AVAILABLE"
            and relation == "DEFINES"
            and bool(receipt.get("derivation_steps"))
        ),
        "missing_source_has_anti_entailment": (
            status != "MISSING"
            or (
                relation == "INDICATES_ABSENCE"
                and receipt.get("candidate_entailment") == "NONE"
                and receipt.get("contextual_default") == "NONE"
            )
        ),
    }


def _primary_category(checks):
    if not checks["source_status_matches_private_construction"]:
        return "SOURCE_STATUS_SEMANTIC_FAILURE"
    if not (
        checks["requested_object_quote_exact_pre_candidate"]
        and checks["source_status_quote_exact_pre_candidate"]
        and checks["source_status_quote_is_support_span_member"]
        and checks["all_support_spans_exact_pre_candidate"]
    ):
        return "GROUNDING_CONTRACT_FAILURE"
    if checks["available_defines_has_explanatory_steps"]:
        return "INTERFACE_OVERCONSTRAINT"
    return "RELATION_CONTRACT_FAILURE"


def render_report(analysis, diagnostics):
    observations = [
        f"Baseline and relational coverage are {analysis['cell_coverage']}.",
        f"All six admitted relational witnesses fail validation; completed challenge count is {analysis['completed_challenge_count']}.",
        f"Failure categories are {diagnostics['failure_category_counts']}.",
        f"Token ratio is {analysis['relational_to_baseline_token_ratio']}, slightly above the frozen 1.55 ceiling.",
        f"Baseline has {analysis['failure_counts'].get('BASELINE_GATE', 0)} gate failure.",
    ]
    interpretations = [
        "The experiment cannot estimate semantic correction because Runtime correctly preserves baseline on every rejected witness.",
        "Two receipts are semantically plausible but rejected by a needless interface rule that forbids explanatory steps for direct definitions.",
        "Two receipts violate exact grounding, showing that a larger schema does not itself prevent candidate-side language or fabricated ellipsis from entering evidence fields.",
        "Two receipts preserve the central cognitive error: one promotes an open as-of request to an available definition, while one collapses a missing named source into ordinary underspecification.",
        "The relational representation exposes the error location more clearly than v0.22, but this contract is not yet usable as an execution path.",
    ]
    unknowns = [
        "No external semantic reference is requested because the candidate arm produced zero completed outputs and no changes.",
        "Private construction strata diagnose designed mechanisms but are not external semantic truth.",
        "Whether a smaller relation contract can preserve the useful distinctions without interface collapse remains untested.",
    ]
    intuition = [
        "Stop v0.23 here; do not salvage or relabel the frozen run.",
        "The next contract should permit explanatory derivation text regardless of direct or compositional relation, while keeping exact quote checks strict.",
        "Separate source availability classification from candidate entailment into two Provider steps or two independently validated subreceipts.",
        "Add a Runtime contradiction gate: explicit unavailable, absent, or missing-source evidence must veto AVAILABLE before synthesis.",
        "Use another fresh holdout and lower the witness output budget before external annotation.",
    ]
    lines = ["# Relational Witness Structural Closure v0.23", ""]
    for title, values in (
        ("Observations", observations),
        ("Interpretations", interpretations),
        ("Unknowns", unknowns),
        ("Intuition Triggers", intuition),
    ):
        lines.extend((f"## {title}", ""))
        lines.extend(f"- {value}" for value in values)
        lines.append("")
    lines.extend((
        "State: `RELATIONAL_WITNESS_STRUCTURAL_VALIDATION_FAILED_NO_EXTERNAL_PANEL`",
        "",
    ))
    return "\n".join(lines)


def main():
    output = REPO_ROOT / "outputs" / "relational_witness_v0_23"
    corpus = read(output / "relational_witness_corpus_frozen.json")
    preregistration = read(
        output / "relational_witness_preregistration.json"
    )
    run = read(output / "relational_witness_run.json")
    analysis = read(output / "relational_witness_analysis.json")
    telemetry = read(output / "relational_witness_telemetry.json")
    diagnostics = build_diagnostics(corpus, run, analysis)
    diagnostics_path = output / "relational_witness_diagnostics.json"
    report_path = output / "RELATIONAL_WITNESS_STRUCTURAL_CLOSURE.md"
    write(diagnostics_path, diagnostics)
    report_path.write_text(
        render_report(analysis, diagnostics),
        encoding="utf-8",
    )
    state = "RELATIONAL_WITNESS_STRUCTURAL_VALIDATION_FAILED_NO_EXTERNAL_PANEL"
    ledger_commitment = {
        "ledger_version": "relational_witness_phase_ledger_v0_23",
        "phases": [
            {
                "phase": "G0_PREREGISTRATION",
                "status": "PASS",
                "hash": preregistration["artifact_hash"],
            },
            {
                "phase": "G1_FRESH_HOLDOUT",
                "status": "PASS",
                "hash": corpus["artifact_hash"],
            },
            {
                "phase": "G2_CANDIDATE_RUN",
                "status": "FAIL_STRUCTURAL",
                "cell_coverage": analysis["cell_coverage"],
                "challenged_count": analysis["challenged_count"],
                "completed_challenge_count": (
                    analysis["completed_challenge_count"]
                ),
                "relational_witness_validation_rate": (
                    analysis["relational_witness_validation_rate"]
                ),
            },
            {
                "phase": "G3_EXTERNAL_REFERENCE",
                "status": "NOT_RUN_NOT_INFORMATIVE",
            },
        ],
        "baseline_insertion": "No Baseline Object Update; experiment only",
    }
    ledger = {
        **ledger_commitment,
        "artifact_hash": hash_payload(ledger_commitment),
    }
    ledger_path = output / "phase_ledger.json"
    write(ledger_path, ledger)
    replay_commitment = {
        "pointer_version": "relational_witness_replay_v0_23",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_relational_witness_selective.py",
            "python examples/run_relational_witness_selective.py",
            "python examples/finalize_relational_witness_structural.py",
        ],
        "frozen_preregistration_hash": preregistration["artifact_hash"],
        "frozen_corpus_hash": corpus["artifact_hash"],
        "reference_revision_allowed": False,
    }
    replay_path = output / "replay_pointer.json"
    write(replay_path, {
        **replay_commitment,
        "artifact_hash": hash_payload(replay_commitment),
    })
    rollback_commitment = {
        "pointer_version": "relational_witness_rollback_v0_23",
        "scope": "experiment-only; AgentOS CoreSlim excluded",
        "rollback_action": "quarantine v0.23 code and outputs",
        "baseline_mutation_to_reverse": False,
        "retention_mutation_to_reverse": False,
    }
    rollback_path = output / "rollback_pointer.json"
    write(rollback_path, {
        **rollback_commitment,
        "artifact_hash": hash_payload(rollback_commitment),
    })
    closure_commitment = {
        "closure_version": "relational_witness_structural_closure_v0_23",
        "preregistration_hash": preregistration["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "telemetry_hash": telemetry["artifact_hash"],
        "diagnostics_hash": diagnostics["artifact_hash"],
        "candidate_state": state,
        "external_panel_generated": False,
        "external_panel_informative": False,
        "promotion_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    closure = {
        **closure_commitment,
        "artifact_hash": hash_payload(closure_commitment),
    }
    closure_path = output / "closure.json"
    write(closure_path, closure)
    members = (
        (
            output / "relational_witness_preregistration.json",
            "relational_witness_preregistration.json",
        ),
        (
            output / "relational_witness_corpus_frozen.json",
            "relational_witness_corpus_frozen.json",
        ),
        (
            output / "relational_witness_run.json",
            "relational_witness_run.json",
        ),
        (
            output / "relational_witness_analysis.json",
            "relational_witness_analysis.json",
        ),
        (diagnostics_path, diagnostics_path.name),
        (report_path, report_path.name),
        (ledger_path, ledger_path.name),
        (replay_path, replay_path.name),
        (rollback_path, rollback_path.name),
        (closure_path, closure_path.name),
    )
    return_pack = output / "relational_witness_v0_23_return_pack.zip"
    write_deterministic_zip(return_pack, members)
    inventory_paths = [source for source, _ in members] + [return_pack]
    inventory_commitment = {
        "inventory_version": "relational_witness_hash_inventory_v0_23",
        "items": [{
            "path": str(path.relative_to(output)).replace("\\", "/"),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        } for path in inventory_paths],
    }
    inventory = {
        **inventory_commitment,
        "artifact_hash": hash_payload(inventory_commitment),
    }
    inventory_path = output / "hash_inventory.json"
    write(inventory_path, inventory)
    manifest_commitment = {
        "manifest_version": "relational_witness_manifest_v0_23",
        "closure_hash": closure["artifact_hash"],
        "inventory_hash": inventory["artifact_hash"],
        "candidate_state": state,
        "external_reference_available": False,
        "promotion_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    manifest = {
        **manifest_commitment,
        "artifact_hash": hash_payload(manifest_commitment),
    }
    manifest_path = output / "manifest.json"
    write(manifest_path, manifest)
    print(json.dumps({
        "candidate_state": state,
        "failure_category_counts": diagnostics["failure_category_counts"],
        "cell_coverage": analysis["cell_coverage"],
        "completed_challenge_count": analysis["completed_challenge_count"],
        "relational_witness_validation_rate": (
            analysis["relational_witness_validation_rate"]
        ),
        "relational_to_baseline_token_ratio": (
            analysis["relational_to_baseline_token_ratio"]
        ),
        "external_panel_generated": False,
        "return_pack": str(return_pack),
        "return_pack_sha256": sha256_file(return_pack),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
