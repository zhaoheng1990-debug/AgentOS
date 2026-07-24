"""Held-out exact-answer Harness with explicit Provider-input non-leakage audits."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from .benchmark_reliability import BenchmarkReliabilityCalibrator, BenchmarkReliabilityReceipt
from .benchmark_routing_calibration import BenchmarkRoutingCalibrator


FROZEN_ANSWER_BENCHMARK_VERSION = "frozen_answer_benchmark_harness_v0_1"
_FORBIDDEN_TRUTH_KEYS = {
    "answer_key", "benchmark_truths", "correct_answer", "expected_answer",
    "ground_truth", "hidden_answer", "hidden_answers", "truths",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _forbidden_paths(value: Any, path: str = "inputs") -> tuple[str, ...]:
    failures: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}"
            if str(key).lower() in _FORBIDDEN_TRUTH_KEYS:
                failures.append(child)
            failures.extend(_forbidden_paths(item, child))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            failures.extend(_forbidden_paths(item, f"{path}[{index}]"))
    elif isinstance(value, BenchmarkAnswerTruth):
        failures.append(f"{path}:truth_object")
    return tuple(failures)


@dataclass(frozen=True)
class BenchmarkQuestion:
    item_id: str
    prompt: str
    choices: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.item_id) or not self.prompt.strip():
            raise ValueError("benchmark_question_invalid")
        if self.choices and (len(self.choices) < 2 or len(self.choices) != len(set(self.choices))):
            raise ValueError("benchmark_question_choices_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {"item_id": self.item_id, "prompt": self.prompt, "choices": list(self.choices)}


@dataclass(frozen=True)
class BenchmarkAnswerTruth:
    item_id: str
    expected_answer: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.item_id) or not self.expected_answer:
            raise ValueError("benchmark_answer_truth_invalid")


@dataclass(frozen=True)
class BenchmarkProviderInputAudit:
    task_id: str
    task_contract_hash: str
    provider_input_hash: str
    public_input_hash: str
    status: str
    failures: tuple[str, ...]
    audit_hash: str

    def __post_init__(self) -> None:
        if self.status not in {"PASS_HIDDEN_ANSWER_ABSENT", "BLOCK_HIDDEN_ANSWER_RISK"}:
            raise ValueError("benchmark_provider_input_audit_status_invalid")
        if self.status.startswith("PASS") == bool(self.failures):
            raise ValueError("benchmark_provider_input_audit_failure_state_invalid")
        for value in (self.task_contract_hash, self.provider_input_hash, self.public_input_hash):
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("benchmark_provider_input_audit_hash_invalid")
        committed = {**self.__dict__, "failures": list(self.failures)}
        committed.pop("audit_hash")
        if self.audit_hash != _hash_payload(committed):
            raise ValueError("benchmark_provider_input_audit_commitment_invalid")

    @classmethod
    def create(cls, **values: Any) -> "BenchmarkProviderInputAudit":
        committed = {**values, "failures": list(values["failures"])}
        return cls(**values, audit_hash=_hash_payload(committed))

    def as_dict(self) -> dict[str, Any]:
        return {
            **{key: value for key, value in self.__dict__.items() if key != "audit_hash"},
            "failures": list(self.failures),
            "audit_hash": self.audit_hash,
        }


@dataclass(frozen=True)
class FrozenAnswerBenchmarkReceipt:
    receipt_id: str
    harness_id: str
    trial_id: str
    arm: str
    candidate_output_hash: str
    correct_count: int
    total_count: int
    exact_accuracy: float
    observed_cbit_gain: float
    errors_exposed: int
    errors_corrected: int
    evidence_refs: tuple[str, ...]
    provider_task_contract_hashes: tuple[str, ...]
    provider_input_audit_hashes: tuple[str, ...]
    telemetry_refs: tuple[str, ...]
    truth_commitment: str
    created_at: str
    receipt_hash: str
    harness_owned: bool = True
    semantic_provider_used: bool = False

    def __post_init__(self) -> None:
        if not self.harness_owned or self.semantic_provider_used:
            raise ValueError("frozen_answer_receipt_authority_invalid")
        if self.total_count < 1 or not 0 <= self.correct_count <= self.total_count:
            raise ValueError("frozen_answer_receipt_counts_invalid")
        if self.exact_accuracy != round(self.correct_count / self.total_count, 12):
            raise ValueError("frozen_answer_receipt_accuracy_invalid")
        if self.observed_cbit_gain != self.exact_accuracy:
            raise ValueError("frozen_answer_receipt_cbit_invalid")
        for values in (
            self.evidence_refs, self.provider_task_contract_hashes,
            self.provider_input_audit_hashes, self.telemetry_refs,
        ):
            if not values or len(values) != len(set(values)):
                raise ValueError("frozen_answer_receipt_lineage_invalid")
        for value in (
            self.candidate_output_hash, self.truth_commitment,
            *self.provider_task_contract_hashes, *self.provider_input_audit_hashes,
        ):
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("frozen_answer_receipt_hash_invalid")
        if any(not re.fullmatch(r"provider-telemetry://[0-9a-f]{64}", value) for value in self.telemetry_refs):
            raise ValueError("frozen_answer_receipt_telemetry_ref_invalid")
        if self.receipt_hash != _hash_payload(self._committed_dict()):
            raise ValueError("frozen_answer_receipt_commitment_invalid")

    def _committed_dict(self) -> dict[str, Any]:
        return {
            **{key: value for key, value in self.__dict__.items() if key != "receipt_hash"},
            "evidence_refs": list(self.evidence_refs),
            "provider_task_contract_hashes": list(self.provider_task_contract_hashes),
            "provider_input_audit_hashes": list(self.provider_input_audit_hashes),
            "telemetry_refs": list(self.telemetry_refs),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._committed_dict(),
            "receipt_hash": self.receipt_hash,
        }


class FrozenAnswerBenchmarkHarness:
    """Own hidden answers, audit Provider inputs, and score exact final answers."""

    module_id = FROZEN_ANSWER_BENCHMARK_VERSION
    capabilities = ("hidden_answer_isolation", "exact_answer_scoring", "observed_cbit_measurement")

    def __init__(
        self,
        *,
        harness_id: str,
        benchmark_id: str,
        questions: tuple[BenchmarkQuestion, ...],
        truths: tuple[BenchmarkAnswerTruth, ...],
        evidence_refs: tuple[str, ...],
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", harness_id) or not benchmark_id:
            raise ValueError("frozen_answer_harness_identity_invalid")
        question_ids = tuple(item.item_id for item in questions)
        truth_ids = tuple(item.item_id for item in truths)
        if not questions or len(set(question_ids)) != len(question_ids) or set(question_ids) != set(truth_ids):
            raise ValueError("frozen_answer_question_truth_alignment_invalid")
        if not evidence_refs or len(evidence_refs) != len(set(evidence_refs)):
            raise ValueError("frozen_answer_evidence_refs_invalid")
        self.harness_id = harness_id
        self.benchmark_id = benchmark_id
        self._questions = questions
        self._question_ids = question_ids
        self._truths = {item.item_id: item.expected_answer for item in truths}
        self.evidence_refs = evidence_refs
        self._truth_commitment = _hash_payload(sorted(self._truths.items()))
        self._reliability = BenchmarkReliabilityCalibrator(
            self._truths, self.evidence_refs, self._truth_commitment
        )
        self._routing_calibration = BenchmarkRoutingCalibrator(self._truths, self.evidence_refs, self._truth_commitment)

    @property
    def truth_commitment(self) -> str:
        return self._truth_commitment

    def provider_inputs(self, item_ids: tuple[str, ...] = ()) -> dict[str, Any]:
        if item_ids and (
            len(item_ids) != len(set(item_ids))
            or not set(item_ids).issubset(self._question_ids)
        ):
            raise ValueError("frozen_answer_public_slice_invalid")
        selected = set(item_ids)
        return {
            "benchmark_id": self.benchmark_id,
            "questions": [
                item.as_dict() for item in self._questions if not selected or item.item_id in selected
            ],
            "evidence_refs": list(self.evidence_refs),
        }

    def audit_provider_task(self, task: Any) -> BenchmarkProviderInputAudit:
        failures = list(_forbidden_paths(task.inputs))
        public = task.inputs.get("benchmark_public_input") if isinstance(task.inputs, dict) else None
        requested_ids = task.inputs.get("benchmark_item_ids", ()) if isinstance(task.inputs, dict) else ()
        expected_public = self.provider_inputs(tuple(requested_ids))
        if public != expected_public:
            failures.append("benchmark_public_input_mismatch")
        if set(task.allowed_evidence) != set(self.evidence_refs):
            failures.append("benchmark_provider_evidence_mismatch")
        return BenchmarkProviderInputAudit.create(
            task_id=task.task_id,
            task_contract_hash=task.contract_hash(),
            provider_input_hash=_hash_payload(task.inputs),
            public_input_hash=_hash_payload(public),
            status="PASS_HIDDEN_ANSWER_ABSENT" if not failures else "BLOCK_HIDDEN_ANSWER_RISK",
            failures=tuple(failures),
        )


    def evaluate(
        self,
        *,
        trial_id: str,
        arm: str,
        candidate_output: dict[str, Any],
        provider_input_audits: tuple[BenchmarkProviderInputAudit, ...],
        telemetry_refs: tuple[str, ...],
    ) -> FrozenAnswerBenchmarkReceipt:
        if not trial_id or not arm or not provider_input_audits or not telemetry_refs:
            raise ValueError("frozen_answer_evaluation_identity_incomplete")
        if any(item.status != "PASS_HIDDEN_ANSWER_ABSENT" for item in provider_input_audits):
            raise ValueError("frozen_answer_provider_input_audit_blocked")
        contract_hashes = tuple(item.task_contract_hash for item in provider_input_audits)
        if len(contract_hashes) != len(set(contract_hashes)):
            raise ValueError("frozen_answer_provider_task_audits_duplicate")
        answers = candidate_output.get("answers")
        if not isinstance(answers, list):
            raise ValueError("frozen_answer_candidate_answers_invalid")
        observed: dict[str, str] = {}
        for item in answers:
            if not isinstance(item, dict) or set(item) != {"item_id", "answer"}:
                raise ValueError("frozen_answer_candidate_item_invalid")
            if item["item_id"] in observed or not isinstance(item["answer"], str):
                raise ValueError("frozen_answer_candidate_item_duplicate_or_invalid")
            observed[item["item_id"]] = item["answer"].strip()
        if set(observed) != set(self._truths):
            raise ValueError("frozen_answer_candidate_coverage_mismatch")
        if candidate_output.get("evidence_refs") != list(self.evidence_refs):
            raise ValueError("frozen_answer_candidate_evidence_mismatch")
        correct = sum(observed[item_id] == answer for item_id, answer in self._truths.items())
        total = len(self._truths)
        created_at = _utc_now()
        committed = {
            "receipt_id": f"benchmark-{trial_id}-{arm.lower()}",
            "harness_id": self.harness_id,
            "trial_id": trial_id,
            "arm": arm,
            "candidate_output_hash": _hash_payload(candidate_output),
            "correct_count": correct,
            "total_count": total,
            "exact_accuracy": round(correct / total, 12),
            "observed_cbit_gain": round(correct / total, 12),
            "errors_exposed": total,
            "errors_corrected": correct,
            "evidence_refs": list(self.evidence_refs),
            "provider_task_contract_hashes": list(contract_hashes),
            "provider_input_audit_hashes": [item.audit_hash for item in provider_input_audits],
            "telemetry_refs": list(telemetry_refs),
            "truth_commitment": self._truth_commitment,
            "created_at": created_at,
            "harness_owned": True,
            "semantic_provider_used": False,
        }
        return FrozenAnswerBenchmarkReceipt(
            **{
                **committed,
                "evidence_refs": self.evidence_refs,
                "provider_task_contract_hashes": contract_hashes,
                "provider_input_audit_hashes": tuple(item.audit_hash for item in provider_input_audits),
                "telemetry_refs": telemetry_refs,
                "receipt_hash": _hash_payload(committed),
            }
        )

    def calibrate_reliability(self, **values: Any) -> BenchmarkReliabilityReceipt:
        return self._reliability.calibrate(**values)

    def candidate_union_ceiling(self, candidates: tuple[dict[str, Any], ...]) -> dict[str, Any]:
        return self._reliability.candidate_union_ceiling(candidates)

    def calibrate_routing(self, **values: Any) -> Any:
        return (self._routing_calibration.calibrate_case_adjudication if "case_adjudication_source_actions" in values else self._routing_calibration.calibrate_resolution_context if "context_source_actions" in values else self._routing_calibration.calibrate_disagreement_resolution if "resolver_peer_answer_by_item" in values else self._routing_calibration.calibrate_structural_operators if "second_model_by_item" in values else self._routing_calibration.calibrate_disagreement if "majority_answer_vector" in values else self._routing_calibration.calibrate_outcomes if "route_decisions" in values else self._routing_calibration.calibrate)(**values)
