"""Prospective selection orchestration for fresh v0.64 cases."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload
from .selection_retention_fresh_contracts import (
    RUNTIME_VERSION,
    SELECTION_ROLES,
    build_selection_consensus,
    selection_schema,
    validate_hash_bound,
    validate_selection_receipt,
)
from .selection_retention_fresh_holdout import (
    validate_selection_retention_fresh_holdout,
)
from .selection_retention_fresh_provider_helpers import (
    call_record,
    failed_call,
)


def build_state_consensus_surface(
    *,
    corpus: dict[str, Any],
    binding_run: dict[str, Any],
    state_run: dict[str, Any],
    binding_state_analysis: dict[str, Any],
) -> dict[str, Any]:
    validate_selection_retention_fresh_holdout(corpus)
    for value in (binding_run, state_run, binding_state_analysis):
        validate_hash_bound(value)
    if binding_state_analysis.get("selection_stage_authorized") is not True:
        raise ValueError("fresh_selection_not_authorized")
    receipts = {}
    for item in corpus["public_surface"]["items"]:
        case_id = item["case_id"]
        assessor = state_run["raw_receipts"][f"STATE_ASSESSOR:{case_id}"]
        skeptic = state_run["raw_receipts"][f"STATE_SKEPTIC:{case_id}"]
        commitment = {
            "case_id": case_id,
            "source_binding_consensus_hash": binding_run[
                "consensus_receipts"
            ][case_id]["artifact_hash"],
            "source_state_receipt_hashes": {
                "STATE_ASSESSOR": hash_payload(assessor),
                "STATE_SKEPTIC": hash_payload(skeptic),
            },
            "relation_assessments": assessor["relation_assessments"],
            "cross_role_agreement": True,
            "private_truth_exposed": False,
        }
        receipts[case_id] = {
            **commitment,
            "artifact_hash": hash_payload(commitment),
        }
    commitment = {
        "surface_version": RUNTIME_VERSION,
        "source_binding_state_analysis_hash": binding_state_analysis[
            "artifact_hash"
        ],
        "receipts": receipts,
        "consequence_known": False,
        "retention_state_known": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_selection_panel(
    *,
    corpus: dict[str, Any],
    preregistration: dict[str, Any],
    state_surface: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    validate_selection_retention_fresh_holdout(corpus)
    for value in (preregistration, state_surface):
        validate_hash_bound(value)
    refs = tuple(corpus["evidence_refs"])
    calls: list[dict[str, Any]] = []
    receipts: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for role in SELECTION_ROLES:
        for item in corpus["public_surface"]["items"]:
            case_id = item["case_id"]
            task = _selection_task(
                item=item,
                role=role,
                state_receipt=state_surface["receipts"][case_id],
                refs=refs,
                adapter=adapter,
            )
            envelope = ProviderTaskRouter([adapter]).route(task)
            call = call_record(role, case_id, task, envelope)
            calls.append(call)
            if envelope.status != "COMPLETED":
                failures.append(failed_call(call, envelope))
                continue
            receipt = envelope.normalized_result
            contract_failures = validate_selection_receipt(
                receipt=receipt,
                item=item,
                role=role,
                refs=refs,
            )
            if contract_failures:
                failures.append({
                    **call,
                    "contract_failures": contract_failures,
                    "invalid_receipt": receipt,
                })
                continue
            receipts[f"{role}:{case_id}"] = receipt
    consensus = {}
    disagreements = []
    for item in corpus["public_surface"]["items"]:
        case_id = item["case_id"]
        left = receipts.get(f"{SELECTION_ROLES[0]}:{case_id}")
        right = receipts.get(f"{SELECTION_ROLES[1]}:{case_id}")
        if left is None or right is None:
            continue
        value = build_selection_consensus(
            item=item, left=left, right=right
        )
        consensus[case_id] = value
        disagreements.extend(
            {"case_id": case_id, "reason": reason}
            for reason in value["disagreements"]
        )
    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_state_surface_hash": state_surface["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "raw_receipts": receipts,
        "contract_failures": failures,
        "consensus_receipts": consensus,
        "cross_role_disagreements": disagreements,
        "consequence_exposed": False,
        "selection_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_selection_panel(
    *,
    corpus: dict[str, Any],
    preregistration: dict[str, Any],
    selection_run: dict[str, Any],
) -> dict[str, Any]:
    validate_selection_retention_fresh_holdout(corpus)
    for value in (preregistration, selection_run):
        validate_hash_bound(value)
    mismatches = []
    private = corpus["private_provenance"]["bindings"]
    for case_id, consensus in selection_run["consensus_receipts"].items():
        reference = private[case_id]
        fields = {
            "selected_ref": reference["expected_selected_ref"],
            "rejected_refs": sorted(reference["expected_rejected_refs"]),
            "deferred_refs": sorted(reference["expected_deferred_refs"]),
        }
        for field, expected in fields.items():
            if consensus[field] != expected:
                mismatches.append({
                    "case_id": case_id,
                    "field": field,
                    "expected": expected,
                    "observed": consensus[field],
                })
    conditions = {
        "required_receipts": (
            len(selection_run["raw_receipts"])
            == preregistration["required_selection_receipt_count"]
        ),
        "required_consensus": (
            len(selection_run["consensus_receipts"])
            == preregistration["required_selection_consensus_count"]
        ),
        "no_contract_failures": not selection_run["contract_failures"],
        "no_cross_role_disagreements": not selection_run[
            "cross_role_disagreements"
        ],
        "no_reference_mismatches": not mismatches,
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_selection_run_hash": selection_run["run_hash"],
        "conditions": conditions,
        "reference_mismatches": mismatches,
        "selection_receipt_count": len(selection_run["raw_receipts"]),
        "selection_consensus_count": len(
            selection_run["consensus_receipts"]
        ),
        "decision": (
            "PASS_FRESH_PROSPECTIVE_SELECTION"
            if passed
            else "REJECT_FRESH_PROSPECTIVE_SELECTION"
        ),
        "consequence_stage_authorized": passed,
        "consequence_known_during_selection": False,
        "selection_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _selection_task(
    *,
    item: dict[str, Any],
    role: str,
    state_receipt: dict[str, Any],
    refs: tuple[str, ...],
    adapter: Any,
) -> ProviderCognitiveTask:
    role_prompt = {
        SELECTION_ROLES[0]: "Rank and partition the prospective alternatives.",
        SELECTION_ROLES[1]: (
            "Challenge the prospective ranking for overclaim and path risk."
        ),
    }[role]
    return ProviderCognitiveTask(
        task_id=f"{RUNTIME_VERSION}-{role}-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            f"{role_prompt} Select exactly one alternative, reject dominated "
            "alternatives, and defer evidence-insufficient alternatives. "
            "Prefer a bounded source-policy change supported by an effect "
            "relation over preserving a drifting baseline; defer a source "
            "whose relation remains unresolved. This is prospective: no "
            "outcome, consequence, validity, or retention information exists. "
            "Do not claim final authority."
        ),
        inputs={
            "selection_role": role,
            "public_item": item,
            "typed_state_consensus": state_receipt,
            "consequence_available": False,
        },
        allowed_evidence=list(refs),
        expected_schema=selection_schema(
            item=item, role=role, refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
