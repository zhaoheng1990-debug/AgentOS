"""Retention-candidate orchestration for fresh v0.64 cases."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload
from .selection_retention_fresh_contracts import (
    RETENTION_ROLES,
    RUNTIME_VERSION,
    build_retention_consensus,
    retention_schema,
    validate_hash_bound,
    validate_retention_receipt,
)
from .selection_retention_fresh_holdout import (
    validate_selection_retention_fresh_holdout,
)
from .selection_retention_fresh_provider_helpers import (
    call_record,
    failed_call,
    physical_attempts,
    token_count,
)


def run_retention_panel(
    *,
    corpus: dict[str, Any],
    preregistration: dict[str, Any],
    selection_run: dict[str, Any],
    consequence_packets: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    validate_selection_retention_fresh_holdout(corpus)
    for value in (
        preregistration,
        selection_run,
        consequence_packets,
    ):
        validate_hash_bound(value)
    calls: list[dict[str, Any]] = []
    receipts: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for role in RETENTION_ROLES:
        for item in corpus["public_surface"]["items"]:
            case_id = item["case_id"]
            selection = selection_run["consensus_receipts"][case_id]
            consequence = consequence_packets["packets"][case_id]
            refs = (
                *tuple(corpus["evidence_refs"]),
                consequence["consequence_ref"],
            )
            task = _retention_task(
                item=item,
                role=role,
                selection=selection,
                consequence=consequence,
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
            contract_failures = validate_retention_receipt(
                receipt=receipt,
                case_id=case_id,
                role=role,
                selection_hash=selection["artifact_hash"],
                consequence_hash=consequence["artifact_hash"],
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
        left = receipts.get(f"{RETENTION_ROLES[0]}:{case_id}")
        right = receipts.get(f"{RETENTION_ROLES[1]}:{case_id}")
        if left is None or right is None:
            continue
        value = build_retention_consensus(
            case_id=case_id, left=left, right=right
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
        "source_selection_run_hash": selection_run["run_hash"],
        "source_consequence_batch_hash": consequence_packets[
            "artifact_hash"
        ],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "raw_receipts": receipts,
        "contract_failures": failures,
        "consensus_receipts": consensus,
        "cross_role_disagreements": disagreements,
        "consequence_assignment_state": "UNASSIGNED",
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_retention_panel(
    *,
    corpus: dict[str, Any],
    preregistration: dict[str, Any],
    binding_run: dict[str, Any],
    state_run: dict[str, Any],
    selection_run: dict[str, Any],
    retention_run: dict[str, Any],
) -> dict[str, Any]:
    validate_selection_retention_fresh_holdout(corpus)
    for value in (
        preregistration,
        binding_run,
        state_run,
        selection_run,
        retention_run,
    ):
        validate_hash_bound(value)
    mismatches = []
    private = corpus["private_provenance"]["bindings"]
    for case_id, consensus in retention_run["consensus_receipts"].items():
        expected = private[case_id]["expected_retention_candidate_state"]
        observed = consensus["recommended_candidate_state"]
        if observed != expected:
            mismatches.append({
                "case_id": case_id,
                "expected": expected,
                "observed": observed,
            })
    calls = [
        *binding_run["task_calls"],
        *state_run["task_calls"],
        *selection_run["task_calls"],
        *retention_run["task_calls"],
    ]
    attempts = physical_attempts(calls)
    tokens = token_count(calls)
    conditions = {
        "required_receipts": (
            len(retention_run["raw_receipts"])
            == preregistration["required_retention_receipt_count"]
        ),
        "required_consensus": (
            len(retention_run["consensus_receipts"])
            == preregistration["required_retention_consensus_count"]
        ),
        "no_contract_failures": not retention_run["contract_failures"],
        "no_cross_role_disagreements": not retention_run[
            "cross_role_disagreements"
        ],
        "no_reference_mismatches": not mismatches,
        "provider_task_budget": (
            len(calls) <= preregistration["maximum_provider_tasks"]
        ),
        "physical_attempt_budget": (
            attempts <= preregistration["maximum_physical_attempts"]
        ),
        "hard_token_ceiling": (
            tokens <= preregistration["hard_token_ceiling"]
        ),
        "consequence_remains_unassigned": (
            retention_run["consequence_assignment_state"] == "UNASSIGNED"
        ),
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_retention_run_hash": retention_run["run_hash"],
        "conditions": conditions,
        "retention_reference_mismatches": mismatches,
        "retention_receipt_count": len(retention_run["raw_receipts"]),
        "retention_consensus_count": len(
            retention_run["consensus_receipts"]
        ),
        "provider_task_count": len(calls),
        "physical_attempt_count": attempts,
        "physical_total_tokens": tokens,
        "decision": (
            "PASS_FRESH_SELECTION_RETENTION_GENERALIZATION"
            if passed
            else "REJECT_FRESH_SELECTION_RETENTION_GENERALIZATION"
        ),
        "candidate_state": (
            "SELECTION_RETENTION_READY_FOR_SHADOW_ORCHESTRATION"
            if passed
            else "SELECTION_RETENTION_REJECTED_STOP"
        ),
        "fresh_generalization_claim": passed,
        "alpha_22_eligible": passed,
        "consequence_assignment_state": "UNASSIGNED",
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _retention_task(
    *,
    item: dict[str, Any],
    role: str,
    selection: dict[str, Any],
    consequence: dict[str, Any],
    refs: tuple[str, ...],
    adapter: Any,
) -> ProviderCognitiveTask:
    role_prompt = {
        RETENTION_ROLES[0]: (
            "Assess the project-scoped retention candidate from delayed "
            "consequence evidence."
        ),
        RETENTION_ROLES[1]: (
            "Challenge validity, transferability, and negative-value risk "
            "before recommending a candidate state."
        ),
    }[role]
    return ProviderCognitiveTask(
        task_id=f"{RUNTIME_VERSION}-{role}-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            f"{role_prompt} Validity is noncompensable: STALE or DRIFTED "
            "evidence must be quarantined even if observed Cbit is positive. "
            "For CURRENT evidence, positive Cbit with positive applicability "
            "may enter PENDING_RETENTION_REVIEW; negative Cbit must remain "
            "PENDING_SELECTION_EVIDENCE. Consequence assignment stays "
            "UNASSIGNED. Never authorize retention, baseline, or production "
            "writes."
        ),
        inputs={
            "retention_role": role,
            "public_item": item,
            "prospective_selection_consensus": selection,
            "delayed_consequence_packet": consequence,
        },
        allowed_evidence=list(refs),
        expected_schema=retention_schema(
            case_id=item["case_id"],
            role=role,
            selection_hash=selection["artifact_hash"],
            consequence_hash=consequence["artifact_hash"],
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
