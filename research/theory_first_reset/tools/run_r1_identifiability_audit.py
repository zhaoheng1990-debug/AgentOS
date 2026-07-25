#!/usr/bin/env python3
"""Run the zero-Provider R1 archived organizational identifiability audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPO_ROOT / "research/theory_first_reset/R1_ARCHIVE_INPUT_MANIFEST.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs/r1_organizational_identifiability_v0_1"


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=True, indent=2, sort_keys=True)
        handle.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def total_tokens(run: dict[str, Any]) -> int:
    return sum(
        int(call.get("token_usage", {}).get("total_tokens", 0))
        for call in run.get("task_calls", [])
    )


def provider_calls(run: dict[str, Any]) -> int:
    return sum(
        int(call.get("token_usage", {}).get("provider_calls", 0))
        for call in run.get("task_calls", [])
    )


def partition_dispositions(run: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for case_id, partition in run["partitions"].items():
        if "derived_records" in partition:
            records = {
                record["span_id"]: record["disposition"]
                for record in partition["derived_records"]
            }
        else:
            records = {}
            disposition_sets = (
                ("evidence_span_ids", "ADMIT_EVIDENCE"),
                ("context_span_ids", "RETAIN_CONTEXT"),
                ("rejected_span_ids", "REJECT"),
            )
            for field, disposition in disposition_sets:
                for span_id in partition.get(field, []):
                    if span_id in records:
                        raise ValueError(
                            f"{run['arm_id']}:{case_id}:{span_id} appears in multiple partitions"
                        )
                    records[span_id] = disposition
        for span_id, disposition in records.items():
            result[span_id] = {
                "case_id": str(case_id),
                "disposition": disposition,
            }
    return result


def transition_class(upstream_correct: bool, downstream_correct: bool) -> str:
    if not upstream_correct and downstream_correct:
        return "CORRECTED"
    if upstream_correct and not downstream_correct:
        return "INTRODUCED_ERROR"
    if upstream_correct and downstream_correct:
        return "RETAINED_CORRECT"
    return "RETAINED_ERROR"


def phi_for_errors(rows: list[dict[str, Any]]) -> float | None:
    upstream = [0 if row["upstream_correct"] else 1 for row in rows]
    downstream = [0 if row["downstream_correct"] else 1 for row in rows]
    mean_upstream = sum(upstream) / len(upstream)
    mean_downstream = sum(downstream) / len(downstream)
    variance_upstream = sum((value - mean_upstream) ** 2 for value in upstream) / len(rows)
    variance_downstream = (
        sum((value - mean_downstream) ** 2 for value in downstream) / len(rows)
    )
    if variance_upstream == 0 or variance_downstream == 0:
        return None
    covariance = sum(
        (left - mean_upstream) * (right - mean_downstream)
        for left, right in zip(upstream, downstream)
    ) / len(rows)
    return covariance / math.sqrt(variance_upstream * variance_downstream)


def summarize_transition(
    comparison_id: str,
    round_id: str,
    unit_type: str,
    rows: list[dict[str, Any]],
    cost: dict[str, Any],
    sequential_chain: bool,
    notes: list[str],
) -> dict[str, Any]:
    counts = {
        label: sum(row["transition_class"] == label for row in rows)
        for label in (
            "CORRECTED",
            "INTRODUCED_ERROR",
            "RETAINED_CORRECT",
            "RETAINED_ERROR",
        )
    }
    changed_count = sum(bool(row["changed"]) for row in rows)
    upstream_correct = counts["INTRODUCED_ERROR"] + counts["RETAINED_CORRECT"]
    downstream_correct = counts["CORRECTED"] + counts["RETAINED_CORRECT"]
    oracle_correct = (
        counts["CORRECTED"]
        + counts["INTRODUCED_ERROR"]
        + counts["RETAINED_CORRECT"]
    )
    correction_opportunities = counts["CORRECTED"] + counts["RETAINED_ERROR"]
    upstream_correct_retention = (
        counts["RETAINED_CORRECT"] / upstream_correct if upstream_correct else None
    )
    correction_rate = (
        counts["CORRECTED"] / correction_opportunities
        if correction_opportunities
        else None
    )
    transition_precision = (
        counts["CORRECTED"]
        / (counts["CORRECTED"] + counts["INTRODUCED_ERROR"])
        if counts["CORRECTED"] + counts["INTRODUCED_ERROR"]
        else None
    )
    net = counts["CORRECTED"] - counts["INTRODUCED_ERROR"]
    incremental_tokens = cost.get("incremental_tokens")
    return {
        "comparison_id": comparison_id,
        "round_id": round_id,
        "unit_type": unit_type,
        "unit_count": len(rows),
        "changed_output_count": changed_count,
        "corrected_count": counts["CORRECTED"],
        "introduced_error_count": counts["INTRODUCED_ERROR"],
        "retained_correct_count": counts["RETAINED_CORRECT"],
        "retained_error_count": counts["RETAINED_ERROR"],
        "net_correctness_units": net,
        "upstream_accuracy": upstream_correct / len(rows),
        "downstream_accuracy": downstream_correct / len(rows),
        "upstream_correct_retention": upstream_correct_retention,
        "correction_rate_given_upstream_error": correction_rate,
        "transition_precision": transition_precision,
        "oracle_union_correct_count": oracle_correct,
        "oracle_union_accuracy": oracle_correct / len(rows),
        "downstream_gap_to_oracle_units": oracle_correct - downstream_correct,
        "downstream_gap_to_oracle_rate": (oracle_correct - downstream_correct)
        / len(rows),
        "composition_loss_units": (
            oracle_correct - downstream_correct if sequential_chain else None
        ),
        "composition_loss_identifiable": sequential_chain,
        "paired_error_phi": phi_for_errors(rows),
        "paired_error_phi_scope": "OUTPUT_ERROR_ASSOCIATION_NOT_ROLE_INDEPENDENCE",
        "incremental_tokens_per_net_correction": (
            incremental_tokens / net
            if incremental_tokens is not None and net > 0
            else None
        ),
        "cost": cost,
        "notes": notes,
    }


def validate_inputs(manifest: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for item in manifest["files"]:
        path = REPO_ROOT / item["path"]
        exists = path.is_file()
        actual_bytes = path.stat().st_size if exists else None
        actual_hash = sha256_file(path) if exists else None
        rows.append(
            {
                "path": item["path"],
                "exists": exists,
                "expected_bytes": item["bytes"],
                "actual_bytes": actual_bytes,
                "expected_sha256": item["sha256"],
                "actual_sha256": actual_hash,
                "valid": exists
                and actual_bytes == item["bytes"]
                and actual_hash == item["sha256"],
            }
        )
    valid = all(row["valid"] for row in rows)
    return {
        "validation_version": "agentos_r1_input_validation_v0_1",
        "manifest_path": str(MANIFEST_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "expected_file_count": manifest["file_count"],
        "validated_file_count": sum(row["valid"] for row in rows),
        "all_inputs_valid": valid,
        "provider_calls_during_audit": 0,
        "files": rows,
    }


def build_v065() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    a0 = read_json(REPO_ROOT / "outputs/benchmark_bridge_v0_65/holdout_a0_score.json")
    a1 = read_json(REPO_ROOT / "outputs/benchmark_bridge_v0_65/holdout_a1_score.json")
    downstream = {case["case_id"]: case for case in a1["cases"]}
    rows = []
    for upstream in a0["cases"]:
        candidate = downstream[upstream["case_id"]]
        upstream_correct = bool(upstream["label_correct"])
        downstream_correct = bool(candidate["label_correct"])
        rows.append(
            {
                "round_id": "v0.65",
                "comparison_id": "A0_ONE_PASS_TO_A1_STAGED",
                "unit_type": "case",
                "unit_id": upstream["case_id"],
                "case_id": upstream["case_id"],
                "reference": upstream["expected_label"],
                "upstream_output": upstream["predicted_label"],
                "downstream_output": candidate["predicted_label"],
                "upstream_correct": upstream_correct,
                "downstream_correct": downstream_correct,
                "changed": upstream["predicted_label"] != candidate["predicted_label"],
                "transition_class": transition_class(
                    upstream_correct, downstream_correct
                ),
                "upstream_evidence_f1": upstream["evidence_f1"],
                "downstream_evidence_f1": candidate["evidence_f1"],
            }
        )
    cost = {
        "upstream_arm_tokens": a0["physical_total_tokens"],
        "downstream_arm_tokens": a1["physical_total_tokens"],
        "incremental_tokens": a1["physical_total_tokens"] - a0["physical_total_tokens"],
        "downstream_to_upstream_token_ratio": a1["physical_total_tokens"]
        / a0["physical_total_tokens"],
        "comparison_cost_scope": "INDEPENDENT_ARM_TOTALS",
    }
    summary = summarize_transition(
        "A0_ONE_PASS_TO_A1_STAGED",
        "v0.65",
        "case",
        rows,
        cost,
        sequential_chain=False,
        notes=[
            "The arms differ as complete workflows; the final-to-oracle gap is not a causal coordinator loss.",
            "Evidence F1 improves on 8 cases and declines on 2, while decision correctness loses one case.",
        ],
    )
    summary["auxiliary"] = {
        "upstream_evidence_f1": a0["evidence_f1"],
        "downstream_evidence_f1": a1["evidence_f1"],
        "evidence_improved_case_count": sum(
            row["downstream_evidence_f1"] > row["upstream_evidence_f1"]
            for row in rows
        ),
        "evidence_harmed_case_count": sum(
            row["downstream_evidence_f1"] < row["upstream_evidence_f1"]
            for row in rows
        ),
        "downstream_missing_label_count": sum(
            row["downstream_output"] is None for row in rows
        ),
    }
    return rows, summary


def build_typed_transition(
    round_id: str,
    comparison_id: str,
    reference_path: str,
    upstream_path: str,
    downstream_path: str,
    score_path: str,
    incremental_stage_name: str,
    sequential_chain: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    reference = read_json(REPO_ROOT / reference_path)
    upstream_run = read_json(REPO_ROOT / upstream_path)
    downstream_run = read_json(REPO_ROOT / downstream_path)
    score = read_json(REPO_ROOT / score_path)
    references = {label["span_id"]: label for label in reference["labels"]}
    upstream = partition_dispositions(upstream_run)
    downstream = partition_dispositions(downstream_run)
    if set(references) != set(upstream) or set(references) != set(downstream):
        raise ValueError(f"{comparison_id}: span identity mismatch")
    rows = []
    for span_id in sorted(references):
        ref = references[span_id]
        before = upstream[span_id]
        after = downstream[span_id]
        upstream_correct = before["disposition"] == ref["disposition"]
        downstream_correct = after["disposition"] == ref["disposition"]
        rows.append(
            {
                "round_id": round_id,
                "comparison_id": comparison_id,
                "unit_type": "span",
                "unit_id": span_id,
                "case_id": ref["case_id"],
                "reference": ref["disposition"],
                "upstream_output": before["disposition"],
                "downstream_output": after["disposition"],
                "upstream_correct": upstream_correct,
                "downstream_correct": downstream_correct,
                "changed": before["disposition"] != after["disposition"],
                "transition_class": transition_class(
                    upstream_correct, downstream_correct
                ),
            }
        )
    upstream_tokens = total_tokens(upstream_run)
    downstream_tokens = total_tokens(downstream_run)
    cost = {
        "upstream_stage_tokens": upstream_tokens,
        "incremental_stage": incremental_stage_name,
        "incremental_tokens": downstream_tokens,
        "observed_chain_tokens": upstream_tokens + downstream_tokens,
        "upstream_stage_provider_calls": provider_calls(upstream_run),
        "incremental_stage_provider_calls": provider_calls(downstream_run),
        "comparison_cost_scope": "SEQUENTIAL_STAGE_CALLS",
    }
    summary = summarize_transition(
        comparison_id,
        round_id,
        "span",
        rows,
        cost,
        sequential_chain=sequential_chain,
        notes=[
            "The stage effect is identifiable; independent role information is not.",
            "All correctness labels come from the frozen external typed reference.",
        ],
    )
    summary["auxiliary"] = {
        "score_version": score["score_version"],
        "experimental_decision": score["experimental_decision"],
        "candidate_acceptance_authorized": score["candidate_acceptance_authorized"],
    }
    return rows, summary


def build_v088() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    evaluation = read_json(
        REPO_ROOT / "outputs/scifact_evidence_scope_v0_88/evaluation.json"
    )
    baseline_run = read_json(
        REPO_ROOT / "outputs/scifact_evidence_scope_v0_88/baseline_run.json"
    )
    evidence_run = read_json(
        REPO_ROOT / "outputs/scifact_evidence_scope_v0_88/evidence_run.json"
    )
    scope_run = read_json(
        REPO_ROOT / "outputs/scifact_evidence_scope_v0_88/scope_run.json"
    )
    downstream = {
        str(case["case_id"]): case for case in evaluation["candidate"]["case_scores"]
    }
    rows = []
    for upstream in evaluation["baseline"]["case_scores"]:
        candidate = downstream[str(upstream["case_id"])]
        upstream_correct = bool(upstream["label_correct"])
        downstream_correct = bool(candidate["label_correct"])
        rows.append(
            {
                "round_id": "v0.88",
                "comparison_id": "DIRECT_WARRANT_TO_EVIDENCESET_CLAIMSCOPE",
                "unit_type": "case",
                "unit_id": str(upstream["case_id"]),
                "case_id": str(upstream["case_id"]),
                "reference": upstream["gold_state"],
                "upstream_output": upstream["predicted_state"],
                "downstream_output": candidate["predicted_state"],
                "upstream_correct": upstream_correct,
                "downstream_correct": downstream_correct,
                "changed": upstream["predicted_state"] != candidate["predicted_state"],
                "transition_class": transition_class(
                    upstream_correct, downstream_correct
                ),
                "upstream_harmful_strong": bool(
                    upstream["harmful_strong_candidate"]
                ),
                "downstream_harmful_strong": bool(
                    candidate["harmful_strong_candidate"]
                ),
                "upstream_correct_sentence_count": upstream[
                    "correct_sentence_count"
                ],
                "downstream_correct_sentence_count": candidate[
                    "correct_sentence_count"
                ],
                "upstream_overselected_sentence_count": upstream[
                    "overselected_sentence_count"
                ],
                "downstream_overselected_sentence_count": candidate[
                    "overselected_sentence_count"
                ],
            }
        )
    baseline_tokens = total_tokens(baseline_run)
    evidence_tokens = total_tokens(evidence_run)
    scope_tokens = total_tokens(scope_run)
    chain_tokens = evidence_tokens + scope_tokens
    cost = {
        "direct_baseline_tokens": baseline_tokens,
        "evidence_set_stage_tokens": evidence_tokens,
        "claim_scope_stage_tokens": scope_tokens,
        "candidate_chain_tokens": chain_tokens,
        "incremental_tokens": chain_tokens - baseline_tokens,
        "candidate_to_baseline_token_ratio": chain_tokens / baseline_tokens,
        "comparison_cost_scope": "ALTERNATIVE_WORKFLOW_TOTALS",
    }
    summary = summarize_transition(
        "DIRECT_WARRANT_TO_EVIDENCESET_CLAIMSCOPE",
        "v0.88",
        "case",
        rows,
        cost,
        sequential_chain=False,
        notes=[
            "Three corrections are exactly offset by three introduced errors.",
            "The candidate chain increases sentence recall but loses precision and adds two harmful strong candidates.",
            "The direct arm is not a prefix of the candidate chain, so causal composition loss is not identified.",
        ],
    )
    summary["auxiliary"] = {
        "upstream_sentence_precision": evaluation["baseline"]["sentence_precision"],
        "downstream_sentence_precision": evaluation["candidate"][
            "sentence_precision"
        ],
        "upstream_sentence_recall": evaluation["baseline"]["sentence_recall"],
        "downstream_sentence_recall": evaluation["candidate"]["sentence_recall"],
        "upstream_sentence_f1": evaluation["baseline"]["sentence_f1"],
        "downstream_sentence_f1": evaluation["candidate"]["sentence_f1"],
        "harmful_strong_removed_count": sum(
            row["upstream_harmful_strong"]
            and not row["downstream_harmful_strong"]
            for row in rows
        ),
        "harmful_strong_added_count": sum(
            not row["upstream_harmful_strong"]
            and row["downstream_harmful_strong"]
            for row in rows
        ),
        "development_decision": evaluation["development_decision"],
    }
    return rows, summary


def build_v089() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    evaluation = read_json(
        REPO_ROOT / "outputs/scifact_claim_atom_binding_v0_89/evaluation.json"
    )
    posthoc = read_json(
        REPO_ROOT / "outputs/scifact_claim_atom_binding_v0_89/posthoc_audit.json"
    )
    evidence_run = read_json(
        REPO_ROOT / "outputs/scifact_claim_atom_binding_v0_89/evidence_run.json"
    )
    scope_run = read_json(
        REPO_ROOT / "outputs/scifact_claim_atom_binding_v0_89/scope_run.json"
    )
    binding_run = read_json(
        REPO_ROOT / "outputs/scifact_claim_atom_binding_v0_89/binding_run.json"
    )
    challenge_run = read_json(
        REPO_ROOT / "outputs/scifact_claim_atom_binding_v0_89/challenge_run.json"
    )
    posthoc_rows = {
        str(row["case_id"]): row for row in posthoc["descriptive_rows"]
    }
    rows = []
    for transition in evaluation["paired"]["case_transitions"]:
        case_id = str(transition["case_id"])
        detail = posthoc_rows[case_id]
        upstream_correct = bool(transition["baseline_correct"])
        downstream_correct = bool(transition["candidate_correct"])
        rows.append(
            {
                "round_id": "v0.89",
                "comparison_id": "SCOPE_PREFIX_TO_BINDING_CHALLENGE_VETO",
                "unit_type": "case",
                "unit_id": case_id,
                "case_id": case_id,
                "reference": detail["gold_state"],
                "upstream_output": transition["baseline_action"],
                "downstream_output": transition["candidate_action"],
                "upstream_correct": upstream_correct,
                "downstream_correct": downstream_correct,
                "changed": transition["baseline_action"]
                != transition["candidate_action"],
                "transition_class": transition_class(
                    upstream_correct, downstream_correct
                ),
                "vetoed": bool(transition["vetoed"]),
                "valid_semantic_veto": bool(detail["valid_semantic_veto"]),
                "binding_receipt_valid": bool(detail["binding_receipt_valid"]),
                "baseline_harmful_strong": bool(
                    detail["baseline_harmful_strong"]
                ),
                "closure_class": detail["closure_class"],
                "refutation_polarity_asymmetry": bool(
                    detail["refutation_polarity_asymmetry"]
                ),
            }
        )
    evidence_tokens = total_tokens(evidence_run)
    scope_tokens = total_tokens(scope_run)
    binding_tokens = total_tokens(binding_run)
    challenge_tokens = total_tokens(challenge_run)
    prefix_tokens = evidence_tokens + scope_tokens
    addon_tokens = binding_tokens + challenge_tokens
    cost = {
        "shared_evidence_stage_tokens": evidence_tokens,
        "scope_prefix_stage_tokens": scope_tokens,
        "upstream_prefix_tokens": prefix_tokens,
        "binding_stage_tokens": binding_tokens,
        "challenge_stage_tokens": challenge_tokens,
        "incremental_tokens": addon_tokens,
        "full_chain_tokens": prefix_tokens + addon_tokens,
        "full_chain_to_prefix_token_ratio": (prefix_tokens + addon_tokens)
        / prefix_tokens,
        "comparison_cost_scope": "SHARED_PREFIX_PLUS_SEQUENTIAL_ADDON",
    }
    summary = summarize_transition(
        "SCOPE_PREFIX_TO_BINDING_CHALLENGE_VETO",
        "v0.89",
        "case",
        rows,
        cost,
        sequential_chain=True,
        notes=[
            "The addon removes one harmful strong candidate through fail-closed invalid binding, not a valid semantic correction.",
            "All nine valid semantic vetoes are false vetoes under the frozen reference.",
            "Binding and challenger contributions are coupled and cannot be assigned unique causal credit.",
        ],
    )
    summary["auxiliary"] = {
        "veto_count": evaluation["paired"]["veto_count"],
        "valid_semantic_veto_count": posthoc["valid_semantic_veto_count"],
        "valid_semantic_false_veto_count": posthoc[
            "valid_semantic_false_veto_count"
        ],
        "valid_semantic_correct_harm_veto_count": posthoc[
            "valid_semantic_correct_harm_veto_count"
        ],
        "fail_closed_harmful_baseline_count": posthoc[
            "fail_closed_harmful_baseline_count"
        ],
        "provider_binding_failure_count": posthoc[
            "provider_binding_failure_count"
        ],
        "refutation_polarity_asymmetry_count": posthoc[
            "refutation_polarity_asymmetry_count"
        ],
        "upstream_strong_correct_retention": evaluation["paired"][
            "correct_strong_retention"
        ],
        "upstream_sentence_f1": evaluation["baseline"]["sentence_f1"],
        "downstream_sentence_f1": evaluation["candidate"]["sentence_f1"],
        "development_decision": evaluation["development_decision"],
    }
    return rows, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()

    manifest = read_json(MANIFEST_PATH)
    input_validation = validate_inputs(manifest)
    if not input_validation["all_inputs_valid"]:
        write_json(output_dir / "input_validation.json", input_validation)
        raise SystemExit("R1 input validation failed; analysis was not run")

    all_rows: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []

    rows, summary = build_v065()
    all_rows.extend(rows)
    comparisons.append(summary)

    rows, summary = build_typed_transition(
        "v0.82",
        "ATOMIC_TO_STAGED_CONTEXT",
        "outputs/admission_v7_external_panel_v0_82/typed_admission_reference_candidate_v0_82.json",
        "outputs/admission_v7_fresh_holdout_v0_82/atomic_run.json",
        "outputs/admission_v7_fresh_holdout_v0_82/candidate_run.json",
        "outputs/admission_v7_external_panel_v0_82/typed_reference_score_v0_82.json",
        "A16_STAGED_CONTEXT_UTILITY_ADDON",
        sequential_chain=True,
    )
    all_rows.extend(rows)
    comparisons.append(summary)

    rows, summary = build_typed_transition(
        "v0.84",
        "STAGED_CONTEXT_TO_TERNARY_REVIEW",
        "outputs/admission_v9_external_panel_v0_84/typed_admission_reference_candidate_v0_84.json",
        "outputs/admission_v9_fresh_holdout_v0_84/staged_run.json",
        "outputs/admission_v9_fresh_holdout_v0_84/candidate_run.json",
        "outputs/admission_v9_external_panel_v0_84/typed_reference_score_v0_84.json",
        "A18_TERNARY_BOUNDARY_REVIEW",
        sequential_chain=True,
    )
    score_v084 = read_json(
        REPO_ROOT
        / "outputs/admission_v9_external_panel_v0_84/typed_reference_score_v0_84.json"
    )
    summary["auxiliary"]["atomic_to_staged_from_frozen_score"] = {
        "corrected_count": score_v084["atomic_to_staged"]["corrected_count"],
        "introduced_error_count": score_v084["atomic_to_staged"]["harmed_count"],
        "net_correctness_units": score_v084["atomic_to_staged"]["corrected_count"]
        - score_v084["atomic_to_staged"]["harmed_count"],
        "scope": "DESCRIPTIVE_ONLY_FULL_ATOMIC_RUN_NOT_IN_R1_MANIFEST",
    }
    all_rows.extend(rows)
    comparisons.append(summary)

    rows, summary = build_v088()
    all_rows.extend(rows)
    comparisons.append(summary)

    rows, summary = build_v089()
    all_rows.extend(rows)
    comparisons.append(summary)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "input_validation.json", input_validation)
    write_json(
        output_dir / "transition_ledger.json",
        {
            "ledger_version": "agentos_r1_transition_ledger_v0_1",
            "row_count": len(all_rows),
            "provider_calls_during_audit": 0,
            "private_source_text_copied": False,
            "rows": all_rows,
        },
    )
    summary_document = {
        "summary_version": "agentos_r1_organizational_identifiability_v0_1",
        "status": "R1_COMPLETE_BOUNDED",
        "evidence_coordinate": "INTERNAL_PROJECT_EVIDENCE",
        "object_before_proxy": {
            "ontology_object": "COGNITIVE_ORGANIZATION",
            "observable_proxy": "FROZEN_SAME_UNIT_STAGE_TRANSITIONS",
            "metrics": [
                "CORRECTED",
                "INTRODUCED_ERROR",
                "RETAINED_CORRECT",
                "RETAINED_ERROR",
                "ORACLE_UNION_GAP",
                "PAIRED_ERROR_PHI",
                "INCREMENTAL_TOKENS",
            ],
        },
        "comparisons": comparisons,
        "cross_round_result": {
            "positive_net_comparisons": [
                item["comparison_id"]
                for item in comparisons
                if item["net_correctness_units"] > 0
            ],
            "zero_net_comparisons": [
                item["comparison_id"]
                for item in comparisons
                if item["net_correctness_units"] == 0
            ],
            "negative_net_comparisons": [
                item["comparison_id"]
                for item in comparisons
                if item["net_correctness_units"] < 0
            ],
            "interpretation": "LOCAL_STAGE_EFFECTS_EXIST_BUT_POSITIVE_COLLECTIVE_COGNITION_IS_NOT_IDENTIFIED",
        },
        "theory_variables": {
            "R_representation_adequacy": {
                "status": "HETEROGENEOUS_LOCAL_EFFECT_IDENTIFIED",
                "result": "A16 repairs reject/context representation in v0.82; later representation expansions are neutral or harmful at final decision level.",
            },
            "U_unique_conditional_role_information": {
                "status": "NOT_IDENTIFIABLE",
                "reason": "Roles are sequential, share upstream framing, and do not emit blind commensurate judgments under matched access and budget.",
            },
            "K_composition_fidelity": {
                "status": "PARTIALLY_IDENTIFIED",
                "result": "Conservation is perfect in v0.82, loses 4 of 43 upstream-correct spans in v0.84, and retains only 6 of 17 upstream-correct cases in v0.89.",
            },
            "E_error_dependence": {
                "status": "OUTPUT_ASSOCIATION_ONLY",
                "reason": "Paired error phi is computable, but it is not an estimate of independent role error correlation.",
            },
            "F_coordination_friction": {
                "status": "OPERATIONAL_COST_IDENTIFIED_SEMANTIC_FRICTION_PARTIAL",
                "result": "Every added workflow has positive token cost; four of five final comparisons have nonpositive net correctness.",
            },
        },
        "not_identifiable": [
            "UNIQUE_ROLE_INFORMATION",
            "BEST_MEMBER_SUPERIORITY",
            "INDEPENDENT_ROLE_ERROR_CORRELATION",
            "COORDINATOR_SYNERGY",
            "GENERALIZATION_TO_FRESH_TASKS",
        ],
        "authority": {
            "provider_calls": False,
            "fresh_holdout_consumed": False,
            "runtime_changes": False,
            "core_writes": False,
            "retention_writes": False,
            "baseline_promotion": False,
        },
    }
    write_json(output_dir / "summary.json", summary_document)

    primary_outputs = [
        output_dir / "input_validation.json",
        output_dir / "transition_ledger.json",
        output_dir / "summary.json",
    ]
    hash_inventory = {
        "inventory_version": "agentos_r1_output_hash_inventory_v0_1",
        "source_manifest_sha256": sha256_file(MANIFEST_PATH),
        "files": [
            {
                "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in primary_outputs
        ],
    }
    write_json(output_dir / "hash_inventory.json", hash_inventory)
    closure = {
        "closure_version": "agentos_r1_closure_v0_1",
        "status": "R1_COMPLETE_BOUNDED",
        "input_validation": "PASS",
        "comparison_count": len(comparisons),
        "ledger_row_count": len(all_rows),
        "provider_calls_during_audit": 0,
        "fresh_holdout_consumed": False,
        "source_files_modified": False,
        "next_stage": "R2_ORGANIZATION_THEORY_PACKET",
        "promotion_authority": False,
        "hash_inventory_sha256": sha256_file(output_dir / "hash_inventory.json"),
    }
    write_json(output_dir / "closure.json", closure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
