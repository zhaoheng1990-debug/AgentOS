"""Bridge real Provider telemetry and held-out Harness outcomes into Cognitive Work."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from agentos_kernel import CognitiveWorkRoundObservation
from agentos_runtime import CognitiveWorkAccountingRuntime, CognitiveWorkRoundReceipt

from .frozen_answer_harness import FrozenAnswerBenchmarkReceipt
from .provider_telemetry import ProviderInvocationTelemetry


COGNITIVE_WORK_EXECUTION_BRIDGE_VERSION = "cognitive_work_execution_bridge_v0_1"


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CognitiveWorkExecutionBridgeReceipt:
    bridge_receipt_id: str
    trajectory_id: str
    round_index: int
    harness_receipt_hash: str
    telemetry_hashes: tuple[str, ...]
    observation_hash: str
    cognitive_work_receipt_hash: str
    control_hash: str
    bridge_hash: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.bridge_receipt_id):
            raise ValueError("cognitive_work_bridge_receipt_identity_invalid")
        if self.round_index < 1 or not self.telemetry_hashes:
            raise ValueError("cognitive_work_bridge_receipt_round_or_telemetry_invalid")
        for value in (
            self.harness_receipt_hash, *self.telemetry_hashes,
            self.observation_hash, self.cognitive_work_receipt_hash, self.control_hash,
        ):
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("cognitive_work_bridge_receipt_hash_invalid")
        committed = {**self.__dict__, "telemetry_hashes": list(self.telemetry_hashes)}
        committed.pop("bridge_hash")
        if self.bridge_hash != _hash_payload(committed):
            raise ValueError("cognitive_work_bridge_receipt_commitment_invalid")

    @classmethod
    def create(cls, **values: Any) -> "CognitiveWorkExecutionBridgeReceipt":
        committed = {**values, "telemetry_hashes": list(values["telemetry_hashes"])}
        return cls(**values, bridge_hash=_hash_payload(committed))

    def as_dict(self) -> dict[str, Any]:
        return {
            **{key: value for key, value in self.__dict__.items() if key != "bridge_hash"},
            "telemetry_hashes": list(self.telemetry_hashes),
            "bridge_hash": self.bridge_hash,
            "baseline_write_authority": False,
            "production_activation": False,
        }


class CognitiveWorkExecutionBridge:
    """Admit exact execution measurements only after Harness/telemetry alignment."""

    module_id = COGNITIVE_WORK_EXECUTION_BRIDGE_VERSION

    def __init__(self, cognitive_work_runtime: CognitiveWorkAccountingRuntime) -> None:
        self.runtime = cognitive_work_runtime

    def submit_round(
        self,
        *,
        bridge_receipt_id: str,
        trajectory_id: str,
        context_key: str,
        round_index: int,
        stage: str,
        topology_id: str,
        agent_ids: tuple[str, ...],
        telemetry: tuple[ProviderInvocationTelemetry, ...],
        harness_receipt: FrozenAnswerBenchmarkReceipt,
        kernel_authorization_ref: str,
    ) -> CognitiveWorkExecutionBridgeReceipt:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", bridge_receipt_id):
            raise ValueError("cognitive_work_bridge_receipt_id_invalid")
        self._validate_sources(telemetry, harness_receipt)
        telemetry_refs = tuple(item.evidence_ref for item in telemetry)
        harness_ref = f"benchmark-harness://{harness_receipt.receipt_hash}"
        evidence_refs = tuple(dict.fromkeys((*harness_receipt.evidence_refs, *telemetry_refs, harness_ref)))
        observation = CognitiveWorkRoundObservation(
            observation_id=f"{bridge_receipt_id}-observation",
            trajectory_id=trajectory_id,
            project_scope=self.runtime.project_scope,
            context_key=context_key,
            round_index=round_index,
            stage=stage,
            topology_id=topology_id,
            agent_ids=agent_ids,
            model_ids=tuple(dict.fromkeys(item.model_id for item in telemetry)),
            input_tokens=sum(item.input_tokens for item in telemetry),
            output_tokens=sum(item.output_tokens for item in telemetry),
            cached_tokens=sum(item.cached_tokens for item in telemetry),
            provider_calls=len(telemetry),
            tool_calls=sum(item.tool_calls for item in telemetry),
            latency_ms=sum(item.latency_ms for item in telemetry),
            api_cost=round(sum(item.api_cost for item in telemetry), 12),
            tool_cost=round(sum(item.tool_cost for item in telemetry), 12),
            observed_cbit_gain=harness_receipt.observed_cbit_gain,
            errors_exposed=harness_receipt.errors_exposed,
            errors_corrected=harness_receipt.errors_corrected,
            evidence_refs=evidence_refs,
            harness_receipt_ref=harness_ref,
        )
        receipt: CognitiveWorkRoundReceipt = self.runtime.account_round(
            receipt_id=f"{bridge_receipt_id}-cognitive-work",
            observation=observation,
            kernel_authorization_ref=kernel_authorization_ref,
        )
        return CognitiveWorkExecutionBridgeReceipt.create(
            bridge_receipt_id=bridge_receipt_id,
            trajectory_id=trajectory_id,
            round_index=round_index,
            harness_receipt_hash=harness_receipt.receipt_hash,
            telemetry_hashes=tuple(item.telemetry_hash for item in telemetry),
            observation_hash=observation.observation_hash,
            cognitive_work_receipt_hash=receipt.receipt_hash,
            control_hash=receipt.kernel_control.decision_hash,
        )

    @staticmethod
    def _validate_sources(
        telemetry: tuple[ProviderInvocationTelemetry, ...],
        harness_receipt: FrozenAnswerBenchmarkReceipt,
    ) -> None:
        if not telemetry or len({item.telemetry_hash for item in telemetry}) != len(telemetry):
            raise ValueError("cognitive_work_bridge_telemetry_invalid")
        telemetry_contracts = {item.task_contract_hash for item in telemetry}
        if telemetry_contracts != set(harness_receipt.provider_task_contract_hashes):
            raise ValueError("cognitive_work_bridge_provider_task_lineage_mismatch")
        telemetry_refs = tuple(item.evidence_ref for item in telemetry)
        if telemetry_refs != harness_receipt.telemetry_refs:
            raise ValueError("cognitive_work_bridge_telemetry_ref_mismatch")
        completed_contracts = {
            item.task_contract_hash for item in telemetry
            if item.status == "COMPLETED" and item.output_hash
        }
        if completed_contracts != telemetry_contracts:
            raise ValueError("cognitive_work_bridge_requires_completed_telemetry_per_task")
        if not harness_receipt.harness_owned or harness_receipt.semantic_provider_used:
            raise ValueError("cognitive_work_bridge_harness_authority_invalid")
