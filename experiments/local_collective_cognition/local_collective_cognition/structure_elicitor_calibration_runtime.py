"""Direct capability calibration for local and Ollama structure elicitors."""

from __future__ import annotations

import re

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .contrastive_structural_contracts import (
    contrastive_batch_schema,
    normalize_contrastive_batch_payload,
)
from .ephemeral_structural_prior_contracts import STRUCTURAL_PRIOR_TASK_KIND
from .local_structure_packet_provider import LocalQualityGatedStructureAdapter, STRUCTURE_ELICITOR_ROLE
from .ollama_provider import OllamaJsonAdapter
from .provider_telemetry import hash_payload
from .structure_elicitor_calibration_eval import build_profile, evaluate_packet
from .structure_elicitor_calibration_holdout import CASES, EVIDENCE_REFS


CALIBRATION_ELICITOR_ROLE = "direct_calibration_contrastive_structure_elicitor"


class OllamaStructurePacketAdapter(OllamaJsonAdapter):
    """Give Ollama the same packet-focused message surface as the small models."""

    def _messages(self, task):
        context = task.inputs.get("round_context", {})
        if task.task_kind == STRUCTURAL_PRIOR_TASK_KIND and context.get("role") == STRUCTURE_ELICITOR_ROLE:
            return LocalQualityGatedStructureAdapter._structure_messages(task)
        return super()._messages(task)


class StructureElicitorCalibrationRuntime:
    def __init__(self, *, cases=CASES, evidence_refs=EVIDENCE_REFS,
                 evaluation_scope="CALIBRATION_ONLY"):
        if not cases or len({item.item_id for item in cases}) != len(cases):
            raise ValueError("structure_calibration_cases_invalid")
        self.cases = tuple(cases)
        self.evidence_refs = tuple(evidence_refs)
        self.evaluation_scope = evaluation_scope

    def evaluate_model(self, *, experiment_id, adapter):
        outcomes, trials = [], []
        for case in self.cases:
            task = self._task(
                experiment_id, adapter.profile.model_id, case,
                timeout_seconds=min(900, adapter.profile.max_timeout_seconds),
            )
            envelope = ProviderTaskRouter([adapter]).route(task)
            invocation = envelope.invocation_receipt.as_dict()
            ledger = getattr(adapter, "telemetry_ledger", None)
            telemetry = ledger.items(task_ids=(task.task_id,)) if ledger is not None else ()
            work_usage = {
                "provider_calls": len(telemetry),
                "input_tokens": sum(item.input_tokens for item in telemetry),
                "output_tokens": sum(item.output_tokens for item in telemetry),
            } if telemetry else None
            packet = None
            failures = list(envelope.validation_errors)
            if envelope.status == "COMPLETED":
                try:
                    normalized = normalize_contrastive_batch_payload(
                        envelope.normalized_result,
                        item_ids=(case.item_id,),
                        evidence_refs=self.evidence_refs,
                    )
                    packet = normalized["packets"][0]
                except ValueError as exc:
                    failures.append(str(exc))
            outcome = evaluate_packet(
                case=case,
                packet=packet,
                model_id=adapter.profile.model_id,
                provider_id=adapter.profile.provider_id,
                task_hash=task.contract_hash(),
                invocation_receipt=invocation,
                provider_status=envelope.status,
                provider_failures=tuple(dict.fromkeys(failures)),
                work_usage=work_usage,
                telemetry_hashes=tuple(item.telemetry_hash for item in telemetry),
                evaluation_scope=self.evaluation_scope,
            )
            outcomes.append(outcome)
            trials.append({
                "item_id": case.item_id,
                "public_input": case.public_input(),
                "truth_commitment": case.truth_commitment(),
                "packet": packet,
                "outcome": outcome,
                "invocation_receipt": invocation,
            })
        profile = build_profile(
            model_id=adapter.profile.model_id,
            provider_id=adapter.profile.provider_id,
            outcomes=tuple(outcomes),
        )
        commitment = {
            "experiment_id": experiment_id,
            "model_id": adapter.profile.model_id,
            "provider_id": adapter.profile.provider_id,
            "trials": trials,
            "profile": profile,
        }
        return {**commitment, "model_run_hash": hash_payload(commitment)}

    def _task(self, experiment_id, model_id, case, *, timeout_seconds):
        safe_model = re.sub(r"[^A-Za-z0-9_.-]", "-", model_id)
        return ProviderCognitiveTask(
            task_id=f"{experiment_id}-{safe_model}-{case.item_id}",
            task_kind=STRUCTURAL_PRIOR_TASK_KIND,
            objective=(
                "Elicit exactly two complete rival object structures, their decisive contrast, "
                "and one question that distinguishes them. Do not solve the task or select an answer."
            ),
            inputs={
                "benchmark_public_input": {"questions": [case.public_input()]},
                "benchmark_item_ids": [case.item_id],
                "round_context": {
                    "role": STRUCTURE_ELICITOR_ROLE,
                    "calibration_role": CALIBRATION_ELICITOR_ROLE,
                    "hidden_truth": "unavailable",
                },
                "audit_context": {"truth_commitment": case.truth_commitment()},
            },
            allowed_evidence=list(self.evidence_refs),
            expected_schema=contrastive_batch_schema((case.item_id,)),
            timeout_seconds=timeout_seconds,
            failure_semantics="record_zero_quality_calibration_trial_without_retrying_the_runtime",
        )
