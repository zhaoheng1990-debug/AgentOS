"""Clean A0/A1 experiment with partial admission and frontier candidates."""

from __future__ import annotations

import math
from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_fresh_holdout import validate_frontier_artifact
from .frontier_partial_admission import (
    EPISTEMIC_BASES,
    LANES,
    OBJECT_TYPES,
    STRUCTURAL_ORIGINS,
    TEST_COSTS,
    project_frontier_receipt,
)
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "frontier_gray_experiment_v0_27"
TASK_KIND = "FRONTIER_GRAY_CBIT_EXPERIMENT"
ARM_IDS = ("A0_DIRECT", "A1_ONTOLOGY")


def native_schema(*, item, arm_id, refs):
    object_ids = [
        value["object_id"] for value in item["object_registry"]
    ]
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    candidate = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "candidate_id", "lane", "question", "source_object_id",
            "target_object_id", "constraint_object_ids",
            "epistemic_basis", "structural_origin", "falsifier",
            "required_observation", "evidence_span_ids",
            "estimated_test_cost",
        ],
        "properties": {
            "candidate_id": {"type": "string"},
            "lane": {"type": "string", "enum": list(LANES)},
            "question": {"type": "string"},
            "source_object_id": {
                "type": "string", "enum": object_ids
            },
            "target_object_id": {
                "type": "string", "enum": object_ids
            },
            "constraint_object_ids": {
                "type": "array", "items": {
                    "type": "string", "enum": object_ids
                },
            },
            "epistemic_basis": {
                "type": "string", "enum": list(EPISTEMIC_BASES)
            },
            "structural_origin": {
                "type": "string", "enum": list(STRUCTURAL_ORIGINS)
            },
            "falsifier": {"type": "string"},
            "required_observation": {"type": "string"},
            "evidence_span_ids": {
                "type": "array", "items": {
                    "type": "string", "enum": span_ids
                },
            },
            "estimated_test_cost": {
                "type": "string", "enum": list(TEST_COSTS)
            },
        },
    }
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "arm_id": {"type": "string", "enum": [arm_id]},
        "problem_candidates": {
            "type": "array",
            "minItems": 2,
            "maxItems": 3,
            "items": candidate,
        },
        "selected_problem_id": {"type": "string"},
        "rationale": {"type": "string"},
        "evidence_refs": {
            "type": "array", "items": {
                "type": "string", "enum": list(refs)
            },
        },
    }
    if arm_id == "A1_ONTOLOGY":
        properties["object_census"] = {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "object_id", "object_type", "anchor_span_ids"
                ],
                "properties": {
                    "object_id": {
                        "type": "string", "enum": object_ids
                    },
                    "object_type": {
                        "type": "string", "enum": list(OBJECT_TYPES)
                    },
                    "anchor_span_ids": {
                        "type": "array", "items": {
                            "type": "string", "enum": span_ids
                        },
                    },
                },
            },
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def run_frontier_batch(*, artifact, adapter, mode, checkpoint_callback=None):
    if mode not in {"PREFLIGHT", "FRESH_HOLDOUT"}:
        raise ValueError("frontier_batch_mode_invalid")
    validate_frontier_artifact(
        artifact, preflight=mode == "PREFLIGHT"
    )
    refs = tuple(artifact["evidence_refs"])
    matrix = [
        (arm_id, item)
        for arm_id in ARM_IDS
        for item in artifact["public_surface"]["items"]
    ]
    matrix.sort(key=lambda value: hash_payload([
        RUNTIME_VERSION, mode, value[0], value[1]["case_id"]
    ]))
    calls, raw_receipts, projections, failures = [], {}, {}, []
    for arm_id, item in matrix:
        task = _task(item, arm_id, refs, adapter, mode)
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(arm_id, item["case_id"], task, envelope)
        calls.append(call)
        key = f"{arm_id}:{item['case_id']}"
        if envelope.status != "COMPLETED":
            failures.append({
                "arm_id": arm_id,
                "case_id": item["case_id"],
                "stage": "PROVIDER_INVOCATION",
                "status": envelope.status,
                "invocation_receipt": envelope.invocation_receipt.as_dict(),
            })
            _checkpoint(
                checkpoint_callback,
                artifact=artifact,
                mode=mode,
                calls=calls,
                raw_receipts=raw_receipts,
                projections=projections,
                failures=failures,
            )
            continue
        raw = envelope.normalized_result
        projection = project_frontier_receipt(
            raw_receipt=raw,
            item=item,
            arm_id=arm_id,
            evidence_refs=refs,
        )
        raw_receipts[key] = raw
        projections[key] = projection
        _checkpoint(
            checkpoint_callback,
            artifact=artifact,
            mode=mode,
            calls=calls,
            raw_receipts=raw_receipts,
            projections=projections,
            failures=failures,
        )
    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "mode": mode,
        "source_artifact_hash": artifact["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "raw_receipts": raw_receipts,
        "projections": projections,
        "failures": failures,
        "raw_receipts_preserved_before_projection": True,
        "arm_native_schemas": True,
        "whole_receipt_block_reserved_for_boundary_failure": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_frontier_preflight(*, artifact, run):
    validate_frontier_artifact(artifact, preflight=True)
    _validate_run(run, artifact=artifact, mode="PREFLIGHT")
    expected = artifact["case_count"] * len(ARM_IDS)
    nonblock = sum(
        value["receipt_state"] != "BLOCK"
        for value in run["projections"].values()
    )
    at_least_two = sum(
        len(value["eligible_candidate_ids"]) >= 2
        for value in run["projections"].values()
    )
    total_tokens = sum(_call_tokens(value) for value in run["task_calls"])
    conditions = {
        "provider_completion_coverage": (
            len(run["raw_receipts"]) == expected
        ),
        "nonblock_projection_coverage": nonblock == expected,
        "two_eligible_candidates_per_task": at_least_two == expected,
        "raw_receipts_preserved": (
            len(run["raw_receipts"]) == len(run["projections"])
            and run["raw_receipts_preserved_before_projection"] is True
        ),
        "arm_native_schema_separation": all(
            call["schema_has_object_census"]
            == (call["arm_id"] == "A1_ONTOLOGY")
            for call in run["task_calls"]
        ),
        "maximum_average_tokens_per_task": (
            total_tokens / expected <= 6000
        ),
    }
    passed = all(conditions.values())
    average = math.ceil(total_tokens / expected)
    commitment = {
        "analysis_version": "frontier_preflight_analysis_v0_27",
        "source_run_hash": run["run_hash"],
        "expected_task_count": expected,
        "provider_completed_count": len(run["raw_receipts"]),
        "nonblock_projection_count": nonblock,
        "two_candidate_projection_count": at_least_two,
        "total_tokens": total_tokens,
        "average_tokens_per_task": average,
        "recommended_fresh_holdout_token_budget": math.ceil(
            average * 24 * 1.25
        ),
        "conditions": conditions,
        "preflight_gate": "PASS" if passed else "REJECT",
        "fresh_holdout_authorized": passed,
        "candidate_state": (
            "FRONTIER_PREFLIGHT_PASSED_READY_FRESH_HOLDOUT"
            if passed else "FRONTIER_PREFLIGHT_REJECTED_STOP"
        ),
        "semantic_claim_allowed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def build_frontier_preregistration(
    *, corpus, preflight_analysis
):
    validate_frontier_artifact(corpus, preflight=False)
    if (
        preflight_analysis.get("preflight_gate") != "PASS"
        or preflight_analysis.get("fresh_holdout_authorized") is not True
        or preflight_analysis.get("semantic_claim_allowed") is not False
    ):
        raise ValueError("frontier_preflight_not_authorized")
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preflight_analysis_hash": preflight_analysis["artifact_hash"],
        "frozen_hypothesis": (
            "A clean ontology-first arm improves realized effective Cbit over "
            "direct problem generation when both use arm-native receipts and "
            "field-level gray admission."
        ),
        "primary_metric": "mean_effective_cbit_per_case",
        "same_cbit_weights_for_core_and_frontier": True,
        "informative_null_has_positive_cbit": True,
        "whole_receipt_block_only_for_boundary_failure": True,
        "success_gate": {
            "minimum_provider_completion_per_arm": 0.95,
            "minimum_nonblock_projection_per_arm": 0.9,
            "minimum_eligible_candidates_per_case": 1.5,
            "minimum_a1_cbit_gain_per_case": 0.05,
            "minimum_a1_cbit_efficiency_ratio_to_a0": 0.9,
            "maximum_total_tokens": preflight_analysis[
                "recommended_fresh_holdout_token_budget"
            ],
        },
        "fresh_labels_available_during_inference": False,
        "external_semantic_panel_required": True,
        "selection_authority": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def analyze_frontier_holdout(*, corpus, preregistration, run):
    validate_frontier_artifact(corpus, preflight=False)
    _validate_run(run, artifact=corpus, mode="FRESH_HOLDOUT")
    if (
        preregistration.get("source_corpus_hash")
        != corpus["artifact_hash"]
        or preregistration.get("artifact_hash") != hash_payload({
            key: value for key, value in preregistration.items()
            if key != "artifact_hash"
        })
    ):
        raise ValueError("frontier_preregistration_invalid")
    ledger = build_realized_cbit_ledger(corpus=corpus, run=run)
    expected = corpus["case_count"]
    arm_runtime = {}
    for arm_id in ARM_IDS:
        calls = [
            value for value in run["task_calls"]
            if value["arm_id"] == arm_id
        ]
        projections = [
            value for key, value in run["projections"].items()
            if key.startswith(arm_id + ":")
        ]
        nonblock = sum(
            value["receipt_state"] != "BLOCK" for value in projections
        )
        eligible = sum(
            len(value["eligible_candidate_ids"])
            for value in projections
        )
        quarantined = sum(
            component["disposition"] == "QUARANTINED_COMPONENT"
            for value in projections
            for component in [
                *value["candidate_components"],
                *value["census_components"],
            ]
        )
        arm_runtime[arm_id] = {
            "provider_completion_coverage": round(
                len(projections) / expected, 6
            ),
            "nonblock_projection_coverage": round(
                nonblock / expected, 6
            ),
            "eligible_candidates_per_case": round(
                eligible / expected, 6
            ),
            "quarantined_component_count": quarantined,
            "total_tokens": sum(_call_tokens(value) for value in calls),
        }
    a0 = ledger["arm_metrics"]["A0_DIRECT"]
    a1 = ledger["arm_metrics"]["A1_ONTOLOGY"]
    comparison_valid = all(
        arm_runtime[arm_id]["provider_completion_coverage"] >= 0.95
        and arm_runtime[arm_id]["nonblock_projection_coverage"] >= 0.9
        for arm_id in ARM_IDS
    )
    gain = (
        round(
            a1["mean_effective_cbit_per_case"]
            - a0["mean_effective_cbit_per_case"],
            6,
        )
        if comparison_valid else None
    )
    efficiency_ratio = (
        round(
            a1["realized_cbit_per_1k_tokens"]
            / a0["realized_cbit_per_1k_tokens"],
            6,
        )
        if comparison_valid
        and a0["realized_cbit_per_1k_tokens"] > 0 else None
    )
    total_tokens = sum(
        value["total_tokens"] for value in arm_runtime.values()
    )
    gate = preregistration["success_gate"]
    conditions = {
        "minimum_provider_completion_per_arm": all(
            value["provider_completion_coverage"]
            >= gate["minimum_provider_completion_per_arm"]
            for value in arm_runtime.values()
        ),
        "minimum_nonblock_projection_per_arm": all(
            value["nonblock_projection_coverage"]
            >= gate["minimum_nonblock_projection_per_arm"]
            for value in arm_runtime.values()
        ),
        "minimum_eligible_candidates_per_case": all(
            value["eligible_candidates_per_case"]
            >= gate["minimum_eligible_candidates_per_case"]
            for value in arm_runtime.values()
        ),
        "minimum_a1_cbit_gain_per_case": (
            gain is not None
            and gain >= gate["minimum_a1_cbit_gain_per_case"]
        ),
        "minimum_a1_cbit_efficiency_ratio_to_a0": (
            efficiency_ratio is not None
            and efficiency_ratio
            >= gate["minimum_a1_cbit_efficiency_ratio_to_a0"]
        ),
        "maximum_total_tokens": (
            total_tokens <= gate["maximum_total_tokens"]
        ),
        "same_cbit_weights_for_core_and_frontier": (
            ledger["lane_specific_score_weights_present"] is False
            and preregistration[
                "same_cbit_weights_for_core_and_frontier"
            ] is True
        ),
        "authority_boundary_preserved": all(
            run.get(value) is False
            for value in (
                "selection_authority", "retention_authority",
                "production_authority",
            )
        ),
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "realized_cbit_ledger": ledger,
        "arm_runtime_metrics": arm_runtime,
        "comparison_valid": comparison_valid,
        "a1_cbit_gain_per_case": gain,
        "a1_cbit_efficiency_ratio_to_a0": efficiency_ratio,
        "total_tokens": total_tokens,
        "conditions": conditions,
        "frontier_holdout_gate": "PASS" if passed else "REJECT",
        "external_semantic_panel_authorized": passed,
        "core_integration_authorized": False,
        "candidate_state": (
            "FRONTIER_GRAY_HOLDOUT_PASSED_READY_EXTERNAL_PANEL"
            if passed else "FRONTIER_GRAY_HOLDOUT_REJECTED_STOP"
        ),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _task(item, arm_id, refs, adapter, mode):
    if arm_id == "A0_DIRECT":
        method = (
            "Generate problem candidates directly. Do not construct or return "
            "an ontology. A FRONTIER candidate is allowed only when it is "
            "falsifiable and structurally distinct."
        )
    else:
        method = (
            "First build a compact object census using only registered objects, "
            "then generate problem candidates. Preserve stable constraints. A "
            "FRONTIER candidate is allowed only when it is falsifiable and "
            "structurally distinct."
        )
    return ProviderCognitiveTask(
        task_id=f"{RUNTIME_VERSION}-{mode}-{arm_id}-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            f"{method} Return two or three candidates. CORE and FRONTIER use "
            "the same quality standard. Weak evidence is allowed only when "
            "marked SPECULATIVE with a non-evidence structural origin, a "
            "falsifier, a required observation, and bounded test cost. Never "
            "claim promotion or factual authority."
        ),
        inputs={
            "stage": "GRAY_PROBLEM_ADMISSION",
            "mode": mode,
            "arm_id": arm_id,
            "public_case": item,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=native_schema(
            item=item, arm_id=arm_id, refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _call(arm_id, case_id, task, envelope):
    commitment = {
        "arm_id": arm_id,
        "case_id": case_id,
        "status": envelope.status,
        "task_contract_hash": task.contract_hash(),
        "task_input_keys": sorted(task.inputs),
        "schema_top_level_keys": sorted(
            task.expected_schema["properties"]
        ),
        "schema_has_object_census": (
            "object_census" in task.expected_schema["properties"]
        ),
        "private_truth_exposed": False,
        "invocation_receipt": envelope.invocation_receipt.as_dict(),
    }
    return {**commitment, "call_hash": hash_payload(commitment)}


def _validate_run(run, *, artifact, mode):
    commitment = {
        key: value for key, value in run.items() if key != "run_hash"
    }
    if (
        run.get("run_hash") != hash_payload(commitment)
        or run.get("mode") != mode
        or run.get("source_artifact_hash") != artifact["artifact_hash"]
        or run.get("raw_receipts_preserved_before_projection") is not True
    ):
        raise ValueError("frontier_batch_run_invalid")


def _call_tokens(call):
    usage = call["invocation_receipt"].get("token_usage") or {}
    return int(
        usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    ) + int(
        usage.get("completion_tokens") or usage.get("output_tokens") or 0
    )


def _checkpoint(
    callback,
    *,
    artifact,
    mode,
    calls,
    raw_receipts,
    projections,
    failures,
):
    if callback is None:
        return
    commitment = {
        "progress_version": "frontier_batch_progress_v0_27",
        "mode": mode,
        "source_artifact_hash": artifact["artifact_hash"],
        "completed_task_count": len(calls),
        "task_calls": list(calls),
        "raw_receipts": dict(raw_receipts),
        "projections": dict(projections),
        "failures": list(failures),
        "original_receipts_preserved": True,
        "resume_authority": False,
    }
    callback({
        **commitment,
        "artifact_hash": hash_payload(commitment),
    })
