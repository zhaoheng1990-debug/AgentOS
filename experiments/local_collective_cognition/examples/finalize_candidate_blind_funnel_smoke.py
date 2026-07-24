"""Close the v0.24 candidate-blind funnel structural smoke."""

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

from local_collective_cognition.cognitive_action_candidate_blind_funnel_holdout import (  # noqa: E402
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
    bindings = corpus["private_provenance"]["bindings"]
    public = {
        item["conflict_id"]: item
        for item in corpus["public_surface"]["items"]
    }
    accepted = set(run["source_status_receipts"])
    source_calls = {
        call["conflict_id"]: call["normalized_result"]
        for call in run["provider_calls"]
        if call["stage"] == "SOURCE_STATUS"
        and call["status"] == "COMPLETED"
    }
    records, categories = [], Counter()
    raw_matches = 0
    false_available = 0
    for conflict_id, receipt in sorted(source_calls.items()):
        binding = bindings[conflict_id]
        expected = binding["source_status"]
        observed = receipt["definition_source_status"]
        text = evidence_text(public[conflict_id])
        spans = receipt["support_spans"]
        status_match = observed == expected
        raw_matches += int(status_match)
        false_available += int(
            observed == "AVAILABLE" and expected != "AVAILABLE"
        )
        checks = {
            "requested_object_quote_exact": (
                receipt["requested_object_quote"] in text
            ),
            "source_status_quote_exact": (
                receipt["source_status_quote"] in text
            ),
            "all_support_spans_exact": all(
                span in text for span in spans
            ),
            "source_status_matches_private_construction": status_match,
        }
        if not status_match:
            category = "SOURCE_STATUS_SEMANTIC_FAILURE"
        elif conflict_id not in accepted:
            category = "QUOTE_REPRODUCTION_FAILURE"
        else:
            category = "PASS"
        categories[category] += 1
        records.append({
            "conflict_id": conflict_id,
            "case_id": binding["case_id"],
            "object_family": binding["object_family"],
            "expected_source_status": expected,
            "provider_source_status": observed,
            "source_receipt_accepted": conflict_id in accepted,
            "primary_diagnostic_category": category,
            "mechanical_checks": checks,
            "provider_receipt": receipt,
        })
    commitment = {
        "diagnostic_version": (
            "candidate_blind_funnel_smoke_diagnostics_v0_24"
        ),
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "diagnostic_category_counts": dict(categories),
        "raw_provider_status_construction_match_rate": round(
            raw_matches / len(source_calls), 6
        ),
        "accepted_receipt_status_construction_match_rate": (
            analysis["source_status_construction_match_rate"]
        ),
        "false_available_promotion_count": false_available,
        "source_records": records,
        "candidate_blindness_mechanically_verified": (
            analysis["source_candidate_blind_rate"] == 1.0
        ),
        "construction_metadata_is_not_external_semantic_truth": True,
        "post_hoc_diagnostic_only": True,
        "gate_effect": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def render_report(analysis, diagnostics):
    observations = [
        f"Candidate blindness is {analysis['source_candidate_blind_rate']}; all eight source tasks omit candidate text.",
        f"Source receipt validation is {analysis['source_receipt_validation_rate']} and output coverage is {analysis['output_coverage']}.",
        f"Raw Provider status matches synthetic construction on {diagnostics['raw_provider_status_construction_match_rate']:.3f} of objects; accepted-receipt match is {analysis['source_status_construction_match_rate']:.3f}.",
        f"Diagnostic categories are {diagnostics['diagnostic_category_counts']}.",
        f"False AVAILABLE promotion count is {diagnostics['false_available_promotion_count']}.",
        f"One AVAILABLE object enters entailment and its receipt validates; total cost is {analysis['total_tokens']} tokens across {analysis['provider_call_count']} calls.",
    ]
    interpretations = [
        "Candidate blindness removes the v0.23 pattern in which open evidence is promoted by candidate-side language.",
        "Three source judgments have the intended status but fail because the Provider reproduces evidence with ellipsis, paraphrase, or grammatical normalization.",
        "The remaining semantic error preserves the important missing-versus-unspecified confusion, so candidate blindness alone does not solve source ontology.",
        "Exact evidence integrity should remain mechanical, but exact string reproduction should not be delegated to the Provider.",
        "The adaptive funnel behaves correctly: only accepted AVAILABLE receipts trigger candidate entailment.",
    ]
    unknowns = [
        "This is synthetic structural smoke evidence, not external semantic validation.",
        "Only one entailment receipt is observed, so the second-stage reliability estimate is weak.",
        "A full fresh holdout remains unauthorized because the smoke gate rejects.",
    ]
    intuition = [
        "Stop v0.24 without rerun or external annotation.",
        "Runtime should segment evidence deterministically and assign immutable span IDs before the Provider call.",
        "The Provider should select span IDs and semantic relations, never reproduce evidence strings.",
        "Keep the candidate-blind availability stage and adaptive entailment route.",
        "Retest the ID-based contract on another fresh smoke set before expanding the benchmark.",
    ]
    lines = ["# Candidate-Blind Funnel Structural Smoke v0.24", ""]
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
        "Gate: `REJECT`",
        "State: `CANDIDATE_BLIND_FUNNEL_SMOKE_REJECTED_STOP`",
        "",
    ))
    return "\n".join(lines)


def main():
    output = REPO_ROOT / "outputs" / "candidate_blind_funnel_v0_24"
    corpus = read(output / "candidate_blind_funnel_corpus_frozen.json")
    preregistration = read(
        output / "candidate_blind_funnel_preregistration.json"
    )
    run = read(output / "candidate_blind_funnel_run.json")
    analysis = read(output / "candidate_blind_funnel_analysis.json")
    telemetry = read(output / "candidate_blind_funnel_telemetry.json")
    diagnostics = build_diagnostics(corpus, run, analysis)
    diagnostics_path = output / "candidate_blind_funnel_diagnostics.json"
    report_path = output / "CANDIDATE_BLIND_FUNNEL_SMOKE_CLOSURE.md"
    write(diagnostics_path, diagnostics)
    report_path.write_text(
        render_report(analysis, diagnostics),
        encoding="utf-8",
    )
    ledger_commitment = {
        "ledger_version": "candidate_blind_funnel_phase_ledger_v0_24",
        "phases": [
            {
                "phase": "G0_PREREGISTRATION",
                "status": "PASS",
                "hash": preregistration["artifact_hash"],
            },
            {
                "phase": "G1_FRESH_SYNTHETIC_SMOKE",
                "status": "PASS",
                "hash": corpus["artifact_hash"],
            },
            {
                "phase": "G2_CANDIDATE_BLIND_FUNNEL_RUN",
                "status": "REJECT",
                "gate_conditions": (
                    analysis["preregistered_gate_conditions"]
                ),
            },
            {
                "phase": "G3_FULL_FRESH_HOLDOUT",
                "status": "NOT_AUTHORIZED",
            },
            {
                "phase": "G4_EXTERNAL_REFERENCE",
                "status": "NOT_RUN",
            },
        ],
        "baseline_insertion": "No Baseline Object Update; smoke only",
    }
    ledger = {
        **ledger_commitment,
        "artifact_hash": hash_payload(ledger_commitment),
    }
    ledger_path = output / "phase_ledger.json"
    write(ledger_path, ledger)
    replay_commitment = {
        "pointer_version": "candidate_blind_funnel_replay_v0_24",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_candidate_blind_funnel_smoke.py",
            "python examples/run_candidate_blind_funnel_smoke.py",
            "python examples/finalize_candidate_blind_funnel_smoke.py",
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
        "pointer_version": "candidate_blind_funnel_rollback_v0_24",
        "scope": "experiment-only; AgentOS CoreSlim excluded",
        "rollback_action": "quarantine v0.24 code and smoke outputs",
        "baseline_mutation_to_reverse": False,
        "retention_mutation_to_reverse": False,
    }
    rollback_path = output / "rollback_pointer.json"
    write(rollback_path, {
        **rollback_commitment,
        "artifact_hash": hash_payload(rollback_commitment),
    })
    closure_commitment = {
        "closure_version": "candidate_blind_funnel_smoke_closure_v0_24",
        "preregistration_hash": preregistration["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "telemetry_hash": telemetry["artifact_hash"],
        "diagnostics_hash": diagnostics["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "structural_smoke_gate": analysis["structural_smoke_gate"],
        "full_fresh_holdout_authorized": False,
        "external_panel_generated": False,
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
            output / "candidate_blind_funnel_preregistration.json",
            "candidate_blind_funnel_preregistration.json",
        ),
        (
            output / "candidate_blind_funnel_corpus_frozen.json",
            "candidate_blind_funnel_corpus_frozen.json",
        ),
        (
            output / "candidate_blind_funnel_run.json",
            "candidate_blind_funnel_run.json",
        ),
        (
            output / "candidate_blind_funnel_analysis.json",
            "candidate_blind_funnel_analysis.json",
        ),
        (diagnostics_path, diagnostics_path.name),
        (report_path, report_path.name),
        (ledger_path, ledger_path.name),
        (replay_path, replay_path.name),
        (rollback_path, rollback_path.name),
        (closure_path, closure_path.name),
    )
    return_pack = output / "candidate_blind_funnel_v0_24_return_pack.zip"
    write_deterministic_zip(return_pack, members)
    inventory_paths = [source for source, _ in members] + [return_pack]
    inventory_commitment = {
        "inventory_version": "candidate_blind_funnel_inventory_v0_24",
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
        "manifest_version": "candidate_blind_funnel_manifest_v0_24",
        "closure_hash": closure["artifact_hash"],
        "inventory_hash": inventory["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "full_fresh_holdout_authorized": False,
        "external_reference_available": False,
        "promotion_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    manifest = {
        **manifest_commitment,
        "artifact_hash": hash_payload(manifest_commitment),
    }
    write(output / "manifest.json", manifest)
    print(json.dumps({
        "candidate_state": analysis["candidate_state"],
        "structural_smoke_gate": analysis["structural_smoke_gate"],
        "diagnostic_category_counts": (
            diagnostics["diagnostic_category_counts"]
        ),
        "raw_provider_status_construction_match_rate": (
            diagnostics["raw_provider_status_construction_match_rate"]
        ),
        "false_available_promotion_count": (
            diagnostics["false_available_promotion_count"]
        ),
        "full_fresh_holdout_authorized": False,
        "external_panel_generated": False,
        "return_pack": str(return_pack),
        "return_pack_sha256": sha256_file(return_pack),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
