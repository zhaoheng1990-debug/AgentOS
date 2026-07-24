"""Provider-backed orchestration for typed evidence binding v0.63."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .frontier_experiment import TASK_KIND
from .portfolio_critic_fresh_holdout import (
    validate_portfolio_critic_fresh_holdout_v0_61_1,
)
from .provider_telemetry import hash_payload
from .typed_evidence_binding_contracts import (
    AUXILIARY_SPAN_FIELDS,
    BINDING_ROLES,
    RUNTIME_VERSION,
    STATE_ROLES,
    build_typed_consensus,
    expected_states,
    relation_ids_for,
    typed_binding_schema,
    typed_state_schema,
    validate_hash_bound,
    validate_typed_binding_receipt,
    validate_typed_state_receipt,
)


def run_typed_binding_panel(
    *,
    corpus: dict[str, Any],
    preregistration: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    validate_portfolio_critic_fresh_holdout_v0_61_1(corpus)
    validate_hash_bound(preregistration)
    refs = tuple(corpus["evidence_refs"])
    calls: list[dict[str, Any]] = []
    receipts: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for role in BINDING_ROLES:
        for item in corpus["public_surface"]["items"]:
            task = _binding_task(
                item=item,
                role=role,
                refs=refs,
                adapter=adapter,
            )
            envelope = ProviderTaskRouter([adapter]).route(task)
            call = _call(role=role, item=item, task=task, envelope=envelope)
            calls.append(call)
            if envelope.status != "COMPLETED":
                failures.append({**call, "failure": envelope.error})
                continue
            receipt = envelope.normalized_result
            contract_failures = validate_typed_binding_receipt(
                receipt=receipt,
                item=item,
                role=role,
                refs=refs,
            )
            if contract_failures:
                failures.append({
                    **call,
                    "contract_failures": contract_failures,
                })
                continue
            receipts[f"{role}:{item['case_id']}"] = receipt
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
        consensus, case_conflicts, case_divergences = (
            build_typed_consensus(
                item=item,
                left=left,
                right=right,
                version=preregistration["preregistration_version"],
            )
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
        <= preregistration[
            "maximum_binding_contract_failure_count"
        ]
    )
    commitment = {
        "runtime_version": preregistration["preregistration_version"],
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "raw_receipts": receipts,
        "contract_failures": failures,
        "consensus_receipts": consensus_receipts,
        "binding_relation_consensus_count": consensus_count,
        "binding_conflicts": conflicts,
        "auxiliary_evidence_divergences": divergences,
        "binding_ready_for_state_assessment": ready,
        "private_truth_exposed": False,
        "truth_state_assessed": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def run_typed_state_panel(
    *,
    corpus: dict[str, Any],
    preregistration: dict[str, Any],
    binding_run: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    validate_portfolio_critic_fresh_holdout_v0_61_1(corpus)
    validate_hash_bound(preregistration)
    validate_hash_bound(binding_run)
    if binding_run.get("binding_ready_for_state_assessment") is not True:
        raise ValueError("typed_binding_panel_not_ready")
    refs = tuple(corpus["evidence_refs"])
    calls: list[dict[str, Any]] = []
    receipts: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for role in STATE_ROLES:
        for item in corpus["public_surface"]["items"]:
            binding = binding_run["consensus_receipts"][item["case_id"]]
            task = _state_task(
                item=item,
                role=role,
                binding_receipt=binding,
                refs=refs,
                adapter=adapter,
            )
            envelope = ProviderTaskRouter([adapter]).route(task)
            call = _call(role=role, item=item, task=task, envelope=envelope)
            calls.append(call)
            if envelope.status != "COMPLETED":
                failures.append({**call, "failure": envelope.error})
                continue
            receipt = envelope.normalized_result
            contract_failures = validate_typed_state_receipt(
                receipt=receipt,
                item=item,
                role=role,
                binding_receipt=binding,
                refs=refs,
            )
            if contract_failures:
                failures.append({
                    **call,
                    "contract_failures": contract_failures,
                })
                continue
            receipts[f"{role}:{item['case_id']}"] = receipt
    commitment = {
        "runtime_version": preregistration["preregistration_version"],
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_binding_run_hash": binding_run["run_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "raw_receipts": receipts,
        "contract_failures": failures,
        "private_truth_exposed": False,
        "binding_consensus_required": True,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_typed_state_panel(
    *,
    corpus: dict[str, Any],
    preregistration: dict[str, Any],
    binding_run: dict[str, Any],
    state_run: dict[str, Any],
) -> dict[str, Any]:
    validate_portfolio_critic_fresh_holdout_v0_61_1(corpus)
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
    for case_id, expected_relations in expected.items():
        left = role_states.get(f"{STATE_ROLES[0]}:{case_id}", {})
        right = role_states.get(f"{STATE_ROLES[1]}:{case_id}", {})
        for relation_id in expected_relations:
            if left.get(relation_id) != right.get(relation_id):
                disagreements.append({
                    "case_id": case_id,
                    "relation_id": relation_id,
                    "assessor_state": left.get(relation_id),
                    "skeptic_state": right.get(relation_id),
                })
    coordinate = preregistration["required_recovered_coordinate"]
    recovered = all(
        role_states.get(
            f"{role}:{coordinate['case_id']}", {}
        ).get(coordinate["relation_id"]) == coordinate["required_state"]
        for role in STATE_ROLES
    )
    calls = [*binding_run["task_calls"], *state_run["task_calls"]]
    tokens = sum(
        value["token_usage"]["total_tokens"] for value in calls
    )
    conditions = {
        "required_binding_receipt_count": (
            len(binding_run["raw_receipts"])
            == preregistration["required_binding_receipt_count"]
        ),
        "required_binding_relation_consensus_count": (
            binding_run["binding_relation_consensus_count"]
            == preregistration[
                "required_binding_relation_consensus_count"
            ]
        ),
        "maximum_binding_conflict_count": (
            len(binding_run["binding_conflicts"])
            <= preregistration["maximum_binding_conflict_count"]
        ),
        "maximum_binding_contract_failure_count": (
            len(binding_run["contract_failures"])
            <= preregistration[
                "maximum_binding_contract_failure_count"
            ]
        ),
        "required_state_receipt_count": (
            len(state_run["raw_receipts"])
            == preregistration["required_state_receipt_count"]
        ),
        "maximum_state_contract_failure_count": (
            len(state_run["contract_failures"])
            <= preregistration[
                "maximum_state_contract_failure_count"
            ]
        ),
        "maximum_state_reference_mismatch_count": (
            len(mismatches)
            <= preregistration["maximum_state_reference_mismatch_count"]
        ),
        "maximum_state_cross_role_disagreement_count": (
            len(disagreements)
            <= preregistration[
                "maximum_state_cross_role_disagreement_count"
            ]
        ),
        "required_recovered_coordinate": recovered,
        "maximum_provider_calls": (
            len(calls) <= preregistration["maximum_provider_calls"]
        ),
        "hard_token_ceiling": (
            tokens <= preregistration["hard_token_ceiling"]
        ),
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": preregistration["preregistration_version"],
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
        "required_coordinate_recovered": recovered,
        "provider_call_count": len(calls),
        "physical_total_tokens": tokens,
        "conditions": conditions,
        "decision": (
            "PASS_TYPED_EVIDENCE_BINDING_CALIBRATION"
            if passed
            else "REJECT_TYPED_EVIDENCE_BINDING_CALIBRATION"
        ),
        "candidate_state": (
            "TYPED_BINDING_READY_FOR_AGENTOS_CONTRACT_SYNC"
            if passed
            else "TYPED_BINDING_REJECTED_STOP"
        ),
        "core_contract_sync_eligible": passed,
        "fresh_generalization_claim": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _binding_task(
    *,
    item: dict[str, Any],
    role: str,
    refs: tuple[str, ...],
    adapter: Any,
) -> ProviderCognitiveTask:
    role_prompt = {
        "EVIDENCE_BINDER": (
            "Bind each relation to typed evidence without judging its truth "
            "state."
        ),
        "BINDING_SKEPTIC": (
            "Independently challenge object, outcome, and evidence-type "
            "binding without judging truth state."
        ),
    }[role]
    return ProviderCognitiveTask(
        task_id=f"{RUNTIME_VERSION}-{role}-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            f"{role_prompt} Assess all five relations exactly once. "
            "Primary evidence is the minimal direct span set that binds the "
            "source object to the focal outcome and determines the evidence "
            "design, including an explicit statement that a relation is "
            "untested. Corroborating evidence is additional same-direction "
            "support, counterevidence is additional opposing evidence, and "
            "gap evidence is additional evidence of missing coverage. Keep "
            "the four span sets disjoint. A replication summary is "
            "corroborating, not primary, when a direct intervention span "
            "already establishes the relation. Do not emit binding_state, "
            "EFFECT, NULL, UNRESOLVED, or any final decision."
        ),
        inputs={
            "binding_role": role,
            "public_item": item,
            "private_truth_available": False,
            "truth_state_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=typed_binding_schema(
            item=item,
            role=role,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _state_task(
    *,
    item: dict[str, Any],
    role: str,
    binding_receipt: dict[str, Any],
    refs: tuple[str, ...],
    adapter: Any,
) -> ProviderCognitiveTask:
    role_prompt = {
        "STATE_ASSESSOR": (
            "Classify each relation from the complete typed binding."
        ),
        "STATE_SKEPTIC": (
            "Challenge overclaim and underclaim before classifying each "
            "relation from the complete typed binding."
        ),
    }[role]
    return ProviderCognitiveTask(
        task_id=f"{RUNTIME_VERSION}-{role}-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            f"{role_prompt} Cite every admitted primary span. You may cite "
            "only corroborating, counter, and gap spans admitted under their "
            "matching typed fields. Corroboration alone cannot establish "
            "SUPPORTED_EFFECT or SUPPORTED_NULL. Use SUPPORTED_EFFECT only "
            "for a BOUND intervention or rollback that changed the focal "
            "outcome, SUPPORTED_NULL only for a BOUND matched comparison "
            "that found no focal-outcome difference, and UNRESOLVED for "
            "untested differences, OTHER designs, UNBOUND relations, or "
            "evidence insufficient after considering counter/gap evidence."
        ),
        inputs={
            "state_role": role,
            "public_item": item,
            "binding_consensus_receipt": binding_receipt,
            "private_truth_available": False,
        },
        allowed_evidence=list(refs),
        expected_schema=typed_state_schema(
            item=item,
            role=role,
            binding_receipt=binding_receipt,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _call(
    *,
    role: str,
    item: dict[str, Any],
    task: ProviderCognitiveTask,
    envelope: Any,
) -> dict[str, Any]:
    return {
        "role": role,
        "case_id": item["case_id"],
        "status": envelope.status,
        "token_usage": dict(envelope.invocation_receipt.token_usage),
        "task_id": task.task_id,
    }
