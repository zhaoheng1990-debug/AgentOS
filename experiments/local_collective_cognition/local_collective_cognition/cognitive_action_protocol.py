"""Stable cognitive actions and canonical receipts for local experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .provider_telemetry import hash_payload


ACTION_PROTOCOL_VERSION = "cognitive_action_protocol_v0_16"

ACTION_TYPES = (
    "DEFINE_OBJECT",
    "DECOMPOSE",
    "PROPOSE_HYPOTHESIS",
    "SUPPORT",
    "VERIFY",
    "VALIDATE",
    "FALSIFY",
    "PROPOSE_COUNTEREXAMPLE",
    "REPLICATE",
    "COMPARE",
    "REFRAME",
    "SYNTHESIZE",
    "ADJUDICATE",
    "EXTEND",
    "GENERATE_QUESTION",
    "AUDIT_UNCERTAINTY",
    "CLARIFY",
    "ABSTAIN",
    "STOP",
)

ROLE_ACTION_CAPABILITIES = {
    "OBJECT_GROUNDING": ("DEFINE_OBJECT", "COMPARE", "AUDIT_UNCERTAINTY", "CLARIFY", "ABSTAIN"),
    "PRAGMATIC_DEFAULT": ("COMPARE", "PROPOSE_HYPOTHESIS", "AUDIT_UNCERTAINTY", "CLARIFY", "ABSTAIN"),
    "ASSESSMENT_SKEPTIC": ("FALSIFY", "PROPOSE_COUNTEREXAMPLE", "AUDIT_UNCERTAINTY", "CLARIFY", "ABSTAIN"),
    "COORDINATOR": ("DECOMPOSE", "COMPARE", "SYNTHESIZE", "GENERATE_QUESTION", "CLARIFY", "ABSTAIN", "STOP"),
    "REPLICATOR": ("VERIFY", "VALIDATE", "REPLICATE", "AUDIT_UNCERTAINTY", "ABSTAIN"),
    "ADJUDICATOR": ("COMPARE", "ADJUDICATE", "AUDIT_UNCERTAINTY", "CLARIFY", "ABSTAIN"),
    "PROBLEM_FINDER": ("REFRAME", "EXTEND", "GENERATE_QUESTION", "AUDIT_UNCERTAINTY", "ABSTAIN"),
}

RESULT_STATES = ("CANDIDATE", "SUPPORTED", "CHALLENGED", "OPEN", "INCONCLUSIVE", "FAILED")


@dataclass(frozen=True)
class ActionCost:
    provider_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0

    def __post_init__(self) -> None:
        if any(value < 0 for value in asdict(self).values()):
            raise ValueError("cognitive_action_cost_negative")


def build_action_receipt(
    *,
    action_id: str,
    action_type: str,
    object_ref: str,
    actor_role: str,
    actor_instance: str,
    method: str,
    result_state: str,
    result: dict[str, Any],
    input_claim_refs: tuple[str, ...] = (),
    evidence_refs: tuple[str, ...] = (),
    support: tuple[str, ...] = (),
    counterevidence: tuple[str, ...] = (),
    uncertainty: float = 0.0,
    failure_boundary: str = "",
    changed_commitments: tuple[str, ...] = (),
    recommended_next_actions: tuple[str, ...] = (),
    cost: ActionCost | None = None,
) -> dict[str, Any]:
    commitment = {
        "protocol_version": ACTION_PROTOCOL_VERSION,
        "action_id": action_id,
        "action_type": action_type,
        "object_ref": object_ref,
        "input_claim_refs": list(input_claim_refs),
        "actor_role": actor_role,
        "actor_instance": actor_instance,
        "method": method,
        "evidence_refs": list(evidence_refs),
        "result_state": result_state,
        "result": result,
        "support": list(support),
        "counterevidence": list(counterevidence),
        "uncertainty": uncertainty,
        "failure_boundary": failure_boundary,
        "changed_commitments": list(changed_commitments),
        "recommended_next_actions": list(recommended_next_actions),
        "cost": asdict(cost or ActionCost()),
        "provider_semantic_choice": True,
        "runtime_final_state_authority": True,
        "provider_selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    receipt = {**commitment, "receipt_hash": hash_payload(commitment)}
    validate_action_receipt(receipt)
    return receipt


def validate_action_receipt(receipt: dict[str, Any]) -> None:
    if not isinstance(receipt, dict) or not receipt:
        raise ValueError("cognitive_action_receipt_invalid")
    commitment = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if receipt.get("receipt_hash") != hash_payload(commitment):
        raise ValueError("cognitive_action_receipt_hash_invalid")
    action_type = receipt.get("action_type")
    role = receipt.get("actor_role")
    if action_type not in ACTION_TYPES or role not in ROLE_ACTION_CAPABILITIES:
        raise ValueError("cognitive_action_type_or_role_invalid")
    if action_type not in ROLE_ACTION_CAPABILITIES[role]:
        raise ValueError("cognitive_action_outside_role_capability")
    if receipt.get("protocol_version") != ACTION_PROTOCOL_VERSION:
        raise ValueError("cognitive_action_protocol_version_invalid")
    if receipt.get("result_state") not in RESULT_STATES or not isinstance(receipt.get("result"), dict):
        raise ValueError("cognitive_action_result_invalid")
    for field in ("action_id", "object_ref", "actor_instance", "method"):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            raise ValueError(f"cognitive_action_{field}_invalid")
    for field in ("input_claim_refs", "evidence_refs", "support", "counterevidence", "changed_commitments"):
        values = receipt.get(field)
        if not isinstance(values, list) or len(values) != len(set(values)) or any(not isinstance(value, str) or not value for value in values):
            raise ValueError(f"cognitive_action_{field}_invalid")
    next_actions = receipt.get("recommended_next_actions")
    if not isinstance(next_actions, list) or len(next_actions) != len(set(next_actions)) or any(value not in ACTION_TYPES for value in next_actions):
        raise ValueError("cognitive_action_next_actions_invalid")
    uncertainty = receipt.get("uncertainty")
    if not isinstance(uncertainty, (int, float)) or isinstance(uncertainty, bool) or not 0 <= uncertainty <= 1:
        raise ValueError("cognitive_action_uncertainty_invalid")
    cost = receipt.get("cost")
    if not isinstance(cost, dict) or set(cost) != {"provider_calls", "input_tokens", "output_tokens", "latency_ms"}:
        raise ValueError("cognitive_action_cost_invalid")
    ActionCost(**cost)
    if receipt.get("provider_semantic_choice") is not True or receipt.get("runtime_final_state_authority") is not True:
        raise ValueError("cognitive_action_authority_boundary_invalid")
    if any(receipt.get(field) is not False for field in ("provider_selection_authority", "retention_authority", "production_authority")):
        raise ValueError("cognitive_action_forbidden_authority")


def allowed_actions(role_id: str) -> tuple[str, ...]:
    try:
        return ROLE_ACTION_CAPABILITIES[role_id]
    except KeyError as exc:
        raise ValueError("cognitive_action_role_unknown") from exc

