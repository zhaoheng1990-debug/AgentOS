"""Kernel-owned cognitive action contracts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any


COGNITIVE_ACTION_PROTOCOL_VERSION = "cognitive-action-receipt-v0.1"
COGNITIVE_ACTION_TYPES = (
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
COGNITIVE_ACTION_STATES = (
    "CANDIDATE",
    "SUPPORTED",
    "CHALLENGED",
    "OPEN",
    "INCONCLUSIVE",
    "FAILED",
)
ROLE_ACTION_CAPABILITIES = {
    "OBJECT_GROUNDING": (
        "DEFINE_OBJECT",
        "COMPARE",
        "AUDIT_UNCERTAINTY",
        "CLARIFY",
        "ABSTAIN",
    ),
    "PRAGMATIC_DEFAULT": (
        "COMPARE",
        "PROPOSE_HYPOTHESIS",
        "AUDIT_UNCERTAINTY",
        "CLARIFY",
        "ABSTAIN",
    ),
    "ASSESSMENT_SKEPTIC": (
        "FALSIFY",
        "PROPOSE_COUNTEREXAMPLE",
        "AUDIT_UNCERTAINTY",
        "CLARIFY",
        "ABSTAIN",
    ),
    "COORDINATOR": (
        "DECOMPOSE",
        "COMPARE",
        "SYNTHESIZE",
        "GENERATE_QUESTION",
        "CLARIFY",
        "ABSTAIN",
        "STOP",
    ),
    "REPLICATOR": (
        "VERIFY",
        "VALIDATE",
        "REPLICATE",
        "AUDIT_UNCERTAINTY",
        "ABSTAIN",
    ),
    "ADJUDICATOR": (
        "COMPARE",
        "ADJUDICATE",
        "AUDIT_UNCERTAINTY",
        "CLARIFY",
        "ABSTAIN",
    ),
    "PROBLEM_FINDER": (
        "REFRAME",
        "EXTEND",
        "GENERATE_QUESTION",
        "AUDIT_UNCERTAINTY",
        "ABSTAIN",
    ),
}


def _hash_payload(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _refs(name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    if len(values) != len(set(values)) or any(
        not isinstance(value, str) or not value for value in values
    ):
        raise ValueError(f"{name}_invalid")
    return values


@dataclass(frozen=True)
class CognitiveActionCost:
    provider_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0

    def __post_init__(self) -> None:
        if any(value < 0 for value in asdict(self).values()):
            raise ValueError("cognitive_action_cost_negative")


@dataclass(frozen=True)
class CognitiveActionReceipt:
    action_id: str
    action_type: str
    object_ref: str
    actor_role: str
    actor_instance: str
    method: str
    result_state: str
    result: dict[str, Any]
    input_claim_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    support: tuple[str, ...]
    counterevidence: tuple[str, ...]
    uncertainty: float
    failure_boundary: str
    changed_commitments: tuple[str, ...]
    recommended_next_actions: tuple[str, ...]
    cost: CognitiveActionCost
    receipt_hash: str
    protocol_version: str = COGNITIVE_ACTION_PROTOCOL_VERSION

    @classmethod
    def create(
        cls,
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
        cost: CognitiveActionCost | None = None,
    ) -> "CognitiveActionReceipt":
        values = {
            "protocol_version": COGNITIVE_ACTION_PROTOCOL_VERSION,
            "action_id": action_id,
            "action_type": action_type,
            "object_ref": object_ref,
            "actor_role": actor_role,
            "actor_instance": actor_instance,
            "method": method,
            "result_state": result_state,
            "result": dict(result),
            "input_claim_refs": tuple(input_claim_refs),
            "evidence_refs": tuple(evidence_refs),
            "support": tuple(support),
            "counterevidence": tuple(counterevidence),
            "uncertainty": uncertainty,
            "failure_boundary": failure_boundary,
            "changed_commitments": tuple(changed_commitments),
            "recommended_next_actions": tuple(
                recommended_next_actions
            ),
            "cost": cost or CognitiveActionCost(),
        }
        commitment = cls._commitment(values)
        return cls(**values, receipt_hash=_hash_payload(commitment))

    def __post_init__(self) -> None:
        for name in (
            "action_id",
            "object_ref",
            "actor_instance",
            "method",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(
                self, name
            ).strip():
                raise ValueError(f"cognitive_action_{name}_invalid")
        if self.protocol_version != COGNITIVE_ACTION_PROTOCOL_VERSION:
            raise ValueError("cognitive_action_protocol_version_invalid")
        allowed = ROLE_ACTION_CAPABILITIES.get(self.actor_role)
        if allowed is None or self.action_type not in allowed:
            raise ValueError("cognitive_action_outside_role_capability")
        if self.result_state not in COGNITIVE_ACTION_STATES:
            raise ValueError("cognitive_action_result_state_invalid")
        if not isinstance(self.result, dict):
            raise ValueError("cognitive_action_result_invalid")
        for name in (
            "input_claim_refs",
            "evidence_refs",
            "support",
            "counterevidence",
            "changed_commitments",
        ):
            _refs(f"cognitive_action_{name}", getattr(self, name))
        _refs(
            "cognitive_action_recommended_next_actions",
            self.recommended_next_actions,
        )
        if any(
            value not in COGNITIVE_ACTION_TYPES
            for value in self.recommended_next_actions
        ):
            raise ValueError("cognitive_action_next_action_unknown")
        if isinstance(self.uncertainty, bool) or not (
            0 <= self.uncertainty <= 1
        ):
            raise ValueError("cognitive_action_uncertainty_invalid")
        expected = _hash_payload(
            self._commitment({
                key: value
                for key, value in self.__dict__.items()
                if key != "receipt_hash"
            })
        )
        if self.receipt_hash != expected:
            raise ValueError("cognitive_action_receipt_hash_invalid")

    @staticmethod
    def _commitment(values: dict[str, Any]) -> dict[str, Any]:
        return {
            "protocol_version": values["protocol_version"],
            "action_id": values["action_id"],
            "action_type": values["action_type"],
            "object_ref": values["object_ref"],
            "actor_role": values["actor_role"],
            "actor_instance": values["actor_instance"],
            "method": values["method"],
            "result_state": values["result_state"],
            "result": values["result"],
            "input_claim_refs": list(values["input_claim_refs"]),
            "evidence_refs": list(values["evidence_refs"]),
            "support": list(values["support"]),
            "counterevidence": list(values["counterevidence"]),
            "uncertainty": values["uncertainty"],
            "failure_boundary": values["failure_boundary"],
            "changed_commitments": list(values["changed_commitments"]),
            "recommended_next_actions": list(
                values["recommended_next_actions"]
            ),
            "cost": asdict(values["cost"]),
            "provider_semantic_support": True,
            "kernel_final_state_authority": True,
            "retention_authority": False,
            "production_authority": False,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._commitment(self.__dict__),
            "receipt_hash": self.receipt_hash,
        }
