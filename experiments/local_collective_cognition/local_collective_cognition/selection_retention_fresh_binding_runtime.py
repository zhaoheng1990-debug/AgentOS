"""Fresh typed-binding and truth-state orchestration for v0.64."""

from __future__ import annotations

from typing import Any

from .provider_telemetry import hash_payload
from .selection_retention_fresh_binding_tasks import (
    binding_task,
    run_role_tasks,
    state_task,
)
from .selection_retention_fresh_contracts import (
    BINDING_ROLES,
    RUNTIME_VERSION,
    STATE_ROLES,
    expected_states,
    validate_hash_bound,
)
from .selection_retention_fresh_holdout import (
    validate_selection_retention_fresh_holdout,
)
from .selection_retention_fresh_provider_helpers import (
    physical_attempts,
    token_count,
)
from .typed_evidence_binding_contracts import (
    build_typed_consensus,
    validate_typed_binding_receipt,
    validate_typed_state_receipt,
)


def run_fresh_binding_panel(
    *,
    corpus: dict[str, Any],
    preregistration: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    validate_selection_retention_fresh_holdout(corpus)
    validate_hash_bound(preregistration)
    refs = tuple(corpus["evidence_refs"])
    calls, receipts, failures = run_role_tasks(
        roles=BINDING_ROLES,
        items=corpus["public_surface"]["items"],
        task_factory=lambda role, item: binding_task(
            item=item, role=role, refs=refs, adapter=adapter
        ),
        validator=lambda role, item, receipt: (
            validate_typed_binding_receipt(
                receipt=receipt, item=item, role=role, refs=refs
            )
        ),
        adapter=adapter,
    )
    consensus_receipts: dict[str, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    divergences: list[dict[str, Any]] = []
    consensus_count = 0
    for item in corpus["public_surface"]["items"]:
        case_id = item["case_id"]
        left = receipts.get(f"{BINDING_ROLES[0]}:{case_id}")
        right = receipts.get(f"{BINDING_ROLES[1]}:{case_id}")
        if left is None or right is None:
            continue
        consensus, case_conflicts, case_divergences = build_typed_consensus(
            item=item,
            left=left,
            right=right,
            version=preregistration["preregistration_version"],
        )
        consensus_receipts[case_id] = consensus
        conflicts.extend(case_conflicts)
        divergences.extend(case_divergences)
        consensus_count += consensus["relation_consensus_count"]
    ready = (
        len(receipts)
        == preregistration["required_binding_receipt_count"]
        and consensus_count
        == preregistration["required_binding_relation_consensus_count"]
        and len(conflicts)
        <= preregistration["maximum_binding_conflict_count"]
        and len(failures)
        <= preregistration["maximum_binding_contract_failure_count"]
    )
    return _run_artifact(
        preregistration=preregistration,
        corpus=corpus,
        adapter=adapter,
        task_calls=calls,
        raw_receipts=receipts,
        contract_failures=failures,
        consensus_receipts=consensus_receipts,
        binding_relation_consensus_count=consensus_count,
        binding_conflicts=conflicts,
        auxiliary_evidence_divergences=divergences,
        binding_ready_for_state_assessment=ready,
        private_truth_exposed=False,
        truth_state_assessed=False,
    )


def run_fresh_state_panel(
    *,
    corpus: dict[str, Any],
    preregistration: dict[str, Any],
    binding_run: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    validate_selection_retention_fresh_holdout(corpus)
    validate_hash_bound(preregistration)
    validate_hash_bound(binding_run)
    if binding_run.get("binding_ready_for_state_assessment") is not True:
        raise ValueError("fresh_binding_panel_not_ready")
    refs = tuple(corpus["evidence_refs"])
    bindings = binding_run["consensus_receipts"]
    calls, receipts, failures = run_role_tasks(
        roles=STATE_ROLES,
        items=corpus["public_surface"]["items"],
        task_factory=lambda role, item: state_task(
            item=item,
            role=role,
            binding_receipt=bindings[item["case_id"]],
            refs=refs,
            adapter=adapter,
        ),
        validator=lambda role, item, receipt: (
            validate_typed_state_receipt(
                receipt=receipt,
                item=item,
                role=role,
                binding_receipt=bindings[item["case_id"]],
                refs=refs,
            )
        ),
        adapter=adapter,
    )
    return _run_artifact(
        preregistration=preregistration,
        corpus=corpus,
        adapter=adapter,
        task_calls=calls,
        raw_receipts=receipts,
        contract_failures=failures,
        source_binding_run_hash=binding_run["run_hash"],
        private_truth_exposed=False,
        binding_consensus_required=True,
    )


def analyze_fresh_binding_state(
    *,
    corpus: dict[str, Any],
    preregistration: dict[str, Any],
    binding_run: dict[str, Any],
    state_run: dict[str, Any],
) -> dict[str, Any]:
    validate_selection_retention_fresh_holdout(corpus)
    for value in (preregistration, binding_run, state_run):
        validate_hash_bound(value)
    expected = expected_states(corpus)
    role_states: dict[str, dict[str, str]] = {}
    mismatches: list[dict[str, Any]] = []
    for key, receipt in state_run["raw_receipts"].items():
        role, case_id = key.split(":", 1)
        states = {
            value["relation_id"]: value["relation_truth_state"]
            for value in receipt["relation_assessments"]
        }
        role_states[key] = states
        for relation_id, expected_state in expected[case_id].items():
            observed = states.get(relation_id)
            if observed != expected_state:
                mismatches.append({
                    "role": role,
                    "case_id": case_id,
                    "relation_id": relation_id,
                    "expected_state": expected_state,
                    "observed_state": observed,
                })
    disagreements: list[dict[str, Any]] = []
    for case_id, relations in expected.items():
        left = role_states.get(f"{STATE_ROLES[0]}:{case_id}", {})
        right = role_states.get(f"{STATE_ROLES[1]}:{case_id}", {})
        for relation_id in relations:
            if left.get(relation_id) != right.get(relation_id):
                disagreements.append({
                    "case_id": case_id,
                    "relation_id": relation_id,
                    "assessor_state": left.get(relation_id),
                    "skeptic_state": right.get(relation_id),
                })
    calls = [*binding_run["task_calls"], *state_run["task_calls"]]
    total_tokens = token_count(calls)
    conditions = {
        "binding_receipts": (
            len(binding_run["raw_receipts"])
            == preregistration["required_binding_receipt_count"]
        ),
        "binding_relation_consensus": (
            binding_run["binding_relation_consensus_count"]
            == preregistration["required_binding_relation_consensus_count"]
        ),
        "binding_conflicts": not binding_run["binding_conflicts"],
        "binding_contract_failures": not binding_run["contract_failures"],
        "state_receipts": (
            len(state_run["raw_receipts"])
            == preregistration["required_state_receipt_count"]
        ),
        "state_contract_failures": not state_run["contract_failures"],
        "state_reference_mismatches": not mismatches,
        "state_cross_role_disagreements": not disagreements,
        "provider_task_budget": (
            len(calls) <= preregistration["maximum_provider_tasks"]
        ),
        "physical_attempt_budget": (
            physical_attempts(calls)
            <= preregistration["maximum_physical_attempts"]
        ),
        "hard_token_ceiling": (
            total_tokens <= preregistration["hard_token_ceiling"]
        ),
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_binding_run_hash": binding_run["run_hash"],
        "source_state_run_hash": state_run["run_hash"],
        "binding_receipt_count": len(binding_run["raw_receipts"]),
        "binding_relation_consensus_count": binding_run[
            "binding_relation_consensus_count"
        ],
        "binding_conflict_count": len(binding_run["binding_conflicts"]),
        "auxiliary_evidence_divergence_count": len(
            binding_run["auxiliary_evidence_divergences"]
        ),
        "state_receipt_count": len(state_run["raw_receipts"]),
        "state_reference_mismatches": mismatches,
        "state_cross_role_disagreements": disagreements,
        "provider_task_count": len(calls),
        "physical_attempt_count": physical_attempts(calls),
        "physical_total_tokens": total_tokens,
        "conditions": conditions,
        "decision": (
            "PASS_FRESH_TYPED_BINDING_STATE"
            if passed
            else "REJECT_FRESH_TYPED_BINDING_STATE"
        ),
        "selection_stage_authorized": passed,
        "fresh_generalization_claim": passed,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _run_artifact(
    *,
    preregistration: dict[str, Any],
    corpus: dict[str, Any],
    adapter: Any,
    **values: Any,
) -> dict[str, Any]:
    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        **values,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}
