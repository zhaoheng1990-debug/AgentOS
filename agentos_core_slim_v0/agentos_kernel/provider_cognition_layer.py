"""Provider-backed cognition policy boundary for AgentOS runtime decisions.

This module defines which runtime operations require model/provider cognition
instead of local string or boolean classification. The Kernel remains the
decision owner: providers supply bounded semantic judgments, while local code
performs schema checks, boundary enforcement, replay, hashing, and rollback.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


PROVIDER_COGNITION_LAYER_ID = "provider_backed_runtime_cognition_layer_v0_2"

PROVIDER_REQUIRED = "PROVIDER_REQUIRED"
PROVIDER_OPTIONAL = "PROVIDER_OPTIONAL"
PROVIDER_FORBIDDEN = "PROVIDER_FORBIDDEN"

PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT = "PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT"
BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING = "BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING"
PASS_MECHANICAL_RUNTIME_OPERATION = "PASS_MECHANICAL_RUNTIME_OPERATION"
BLOCKED_UNKNOWN_COGNITION_OPERATION = "BLOCKED_UNKNOWN_COGNITION_OPERATION"


def _hash_payload(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CognitionOperationContract:
    operation_id: str
    layer: str
    provider_requirement: str
    provider_role: str
    runtime_role: str
    required_provider_outputs: tuple[str, ...]
    fail_closed_behavior: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "layer": self.layer,
            "provider_requirement": self.provider_requirement,
            "provider_role": self.provider_role,
            "runtime_role": self.runtime_role,
            "required_provider_outputs": list(self.required_provider_outputs),
            "fail_closed_behavior": self.fail_closed_behavior,
        }


PROVIDER_REQUIRED_OPERATIONS: tuple[CognitionOperationContract, ...] = (
    CognitionOperationContract(
        "temporal_sro_constraint_field_resolution",
        "kernel",
        PROVIDER_REQUIRED,
        "identify task constraint field, hidden constraints, reuse mode, transfer risk, and candidate operator set",
        "validate schema, record SRO receipt, enforce scope and SafetyKernel boundary",
        ("constraint_field", "hidden_constraints", "reuse_mode", "transfer_risk", "operator_candidates", "confidence"),
        "block_or_candidate_only_no_local_semantic_guess",
    ),
    CognitionOperationContract(
        "structural_routing_operator_fiber_ranking",
        "kernel",
        PROVIDER_REQUIRED,
        "rank operator compatibility and explain why each operator applies or does not apply",
        "check registered operators, capability envelopes, forbidden actions, and replayability",
        ("ranked_operator_fiber", "applicability_reason", "non_applicability_reason", "risk_notes", "confidence"),
        "block_route_selection_until_provider_support_receipt",
    ),
    CognitionOperationContract(
        "utility_policy_selection",
        "kernel",
        PROVIDER_REQUIRED,
        "estimate expected utility, Cbit gain, residual risk, and anti-additive pressure for candidate routes",
        "apply hard gates, permission policy, rollback requirements, and final decision envelope",
        ("utility_estimate", "cbit_gain_estimate", "risk_estimate", "anti_additive_signal", "selected_policy_candidate"),
        "defer_policy_selection_no_local_best_guess",
    ),
    CognitionOperationContract(
        "memory_retention_candidate_evaluation",
        "memory_runtime",
        PROVIDER_REQUIRED,
        "judge transferability, future Cbit gain, supersession, negative transfer, scope, freshness, and reuse value",
        "write only candidate/project-scoped records when authorized; hash, replay, rollback, and expose review packet",
        ("transferability", "future_cbit_gain", "negative_transfer_risk", "scope", "freshness", "recommended_state"),
        "keep_pending_or_quarantine_without_provider_support_receipt",
    ),
    CognitionOperationContract(
        "operator_memory_functional_equivalence_review",
        "memory_runtime",
        PROVIDER_REQUIRED,
        "compare traces by functional equivalence, failure boundary, output improvement, and reuse conditions",
        "validate evidence refs, candidate state, durable write authorization, and replay evidence",
        ("operator_family", "functional_equivalence", "failure_boundary", "reuse_conditions", "confidence"),
        "block_operator_promotion_or_keep_candidate",
    ),
    CognitionOperationContract(
        "validity_drift_watch_assessment",
        "memory_runtime",
        PROVIDER_REQUIRED,
        "detect stale reuse risk, temporal drift, scope mismatch, contradiction, and revalidation need",
        "enforce validity map, drift watch records, quarantine, revocation, and blocked reuse",
        ("drift_type", "stale_reuse_risk", "scope_mismatch", "revalidation_need", "recommended_action"),
        "quarantine_or_revalidate_no_silent_reuse",
    ),
    CognitionOperationContract(
        "evidence_relevance_and_claim_support",
        "evidence_runtime",
        PROVIDER_REQUIRED,
        "judge whether source passages support the claimed object, dimension, timeframe, and scope",
        "preserve source hashes, citation provenance, freshness policy, and candidate-only state",
        ("supported_claims", "unsupported_claims", "evidence_scope", "freshness", "confidence"),
        "do_not_accept_evidence_without_provider_support_judgment",
    ),
    CognitionOperationContract(
        "plugin_object_event_extraction",
        "plugin_middleware",
        PROVIDER_REQUIRED,
        "extract plugin-defined objects, events, relations, and source-backed fields",
        "dedupe mechanically, validate required fields, retain missing fields, and prevent unsupported promotion",
        ("entities", "events", "entity_type", "source_links", "missing_fields", "confidence"),
        "candidate_only_or_insufficient_materials_report",
    ),
    CognitionOperationContract(
        "plugin_scope_synthesis",
        "plugin_middleware",
        PROVIDER_REQUIRED,
        "synthesize a plugin-owned scope from evidence, contradictions, structure, quantitative signals, and uncertainty",
        "render plugin projection, cite references, mark baseline candidate state, and keep provenance separate from prose",
        ("scope_sections", "key_judgments", "quantitative_tables", "uncertainties", "next_evidence_actions"),
        "insufficient_scope_report_no_template_fallback",
    ),
    CognitionOperationContract(
        "next_iteration_action_selection",
        "automation_middleware",
        PROVIDER_REQUIRED,
        "choose next high-Cbit action, object switch, search dimension, or stop condition from current evidence state",
        "execute only authorized local/harness actions, log action receipts, and enforce rollback",
        ("next_action", "expected_cbit_gain", "stop_condition", "object_switch_candidate", "risk_notes"),
        "stop_or_request_direction_no_local_semantic_guess",
    ),
)

MECHANICAL_RUNTIME_OPERATIONS: tuple[CognitionOperationContract, ...] = (
    CognitionOperationContract(
        "schema_validation",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "validate JSON schemas, required fields, types, and enum membership",
        (),
        "fail_schema_validation",
    ),
    CognitionOperationContract(
        "hash_replay_rollback",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "compute hashes, replay receipts, rollback local writes, and verify absence checks",
        (),
        "fail_replay_or_rollback",
    ),
    CognitionOperationContract(
        "capability_permission_boundary",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "enforce capability envelopes, allowed paths, forbidden actions, and SafetyKernel hard stops",
        (),
        "block_forbidden_action",
    ),
    CognitionOperationContract(
        "artifact_packaging_manifest",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "package artifacts, generate manifests, and inventory hashes",
        (),
        "fail_packaging",
    ),
)


class ProviderBackedRuntimeCognitionLayer:
    """Kernel-owned policy boundary for provider-supported cognition."""

    layer_id = PROVIDER_COGNITION_LAYER_ID
    final_decision_owner = "AgentOSKernel"
    provider_final_decision_owner = False

    def __init__(self) -> None:
        contracts = PROVIDER_REQUIRED_OPERATIONS + MECHANICAL_RUNTIME_OPERATIONS
        self._contracts = {contract.operation_id: contract for contract in contracts}

    def contract(self) -> dict[str, Any]:
        provider_required = [item.as_dict() for item in PROVIDER_REQUIRED_OPERATIONS]
        mechanical = [item.as_dict() for item in MECHANICAL_RUNTIME_OPERATIONS]
        payload = {
            "layer_id": self.layer_id,
            "purpose": "route provider-supported semantic work while preserving kernel-owned cognition, final decision, and mechanical runtime enforcement",
            "provider_final_decision_owner": False,
            "final_decision_owner": self.final_decision_owner,
            "provider_required_operations": provider_required,
            "mechanical_runtime_operations": mechanical,
            "invariant": "runtime_remains_cognitive_subject; provider_supports_bounded_semantic_work; local_runtime_code_owns_validation_enforcement_recording_replay_and_final_candidate_state",
        }
        payload["contract_hash"] = _hash_payload(payload)
        return payload

    def operation_contract(self, operation_id: str) -> dict[str, Any]:
        contract = self._contracts.get(operation_id)
        if not contract:
            return {
                "operation_id": operation_id,
                "status": BLOCKED_UNKNOWN_COGNITION_OPERATION,
                "reason": "operation_not_registered_in_provider_cognition_layer",
            }
        return contract.as_dict()

    def audit_operation(self, operation_id: str, runtime_record: dict[str, Any]) -> dict[str, Any]:
        contract = self._contracts.get(operation_id)
        if not contract:
            return {
                "operation_id": operation_id,
                "status": BLOCKED_UNKNOWN_COGNITION_OPERATION,
                "provider_required": None,
                "runtime_record_hash": _hash_payload(runtime_record),
            }

        if contract.provider_requirement == PROVIDER_FORBIDDEN:
            return {
                "operation_id": operation_id,
                "status": PASS_MECHANICAL_RUNTIME_OPERATION,
                "provider_required": False,
                "runtime_cognitive_owner": self.final_decision_owner,
                "provider_support_role": "forbidden_for_deterministic_runtime_boundary",
                "runtime_role": contract.runtime_role,
                "runtime_record_hash": _hash_payload(runtime_record),
            }

        support_receipt = runtime_record.get("provider_support_receipt")
        missing_outputs = self._missing_provider_outputs(contract, support_receipt)
        if missing_outputs:
            return {
                "operation_id": operation_id,
                "status": BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING,
                "provider_required": True,
                "runtime_cognitive_owner": self.final_decision_owner,
                "provider_support_role": "semantic_support_required",
                "missing_provider_outputs": missing_outputs,
                "fail_closed_behavior": contract.fail_closed_behavior,
                "runtime_record_hash": _hash_payload(runtime_record),
            }

        receipt_hash = runtime_record.get("provider_support_receipt_hash") or _hash_payload(support_receipt)
        return {
            "operation_id": operation_id,
            "status": PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
            "provider_required": True,
            "runtime_cognitive_owner": self.final_decision_owner,
            "provider_support_role": "semantic_support_present",
            "runtime_role": contract.runtime_role,
            "provider_support_receipt_hash": receipt_hash,
            "runtime_record_hash": _hash_payload(runtime_record),
        }

    def audit_pipeline(self, operation_records: list[dict[str, Any]]) -> dict[str, Any]:
        audits = [self.audit_operation(item.get("operation_id", ""), item) for item in operation_records]
        hard_blocks = [item for item in audits if item["status"] in {BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING, BLOCKED_UNKNOWN_COGNITION_OPERATION}]
        return {
            "layer_id": self.layer_id,
            "status": "BLOCKED" if hard_blocks else "PASS",
            "operation_count": len(audits),
            "blocked_count": len(hard_blocks),
            "audits": audits,
            "pipeline_hash": _hash_payload(audits),
        }

    @staticmethod
    def _missing_provider_outputs(contract: CognitionOperationContract, judgment: Any) -> list[str]:
        if not isinstance(judgment, dict):
            return list(contract.required_provider_outputs)
        return [field for field in contract.required_provider_outputs if field not in judgment]
