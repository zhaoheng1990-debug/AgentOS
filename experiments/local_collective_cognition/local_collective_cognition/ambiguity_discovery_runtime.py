"""Provider-backed runtime for the paired unstated-ambiguity holdout."""

from __future__ import annotations

import re

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .ambiguity_discovery_contracts import STATES, TASK_KIND, discovery_schema, normalize_discovery_payload
from .provider_telemetry import hash_payload
from .unstated_ambiguity_holdout import (
    CASES, EVIDENCE_REFS, HOLDOUT_SPEC, NULL, POSITIVE, validate_holdout_spec,
)


RUNTIME_VERSION = "ambiguity_discovery_runtime_v0_3"


class AmbiguityDiscoveryRuntime:
    def __init__(self, *, cases=CASES, holdout_spec=HOLDOUT_SPEC,
                 spec_validator=validate_holdout_spec, evidence_refs=EVIDENCE_REFS):
        spec_validator(cases=cases, spec=holdout_spec)
        self.cases = tuple(cases)
        self.evidence_refs = tuple(evidence_refs)

    def evaluate_model(self, *, experiment_id, adapter):
        trials = []
        for case in self.cases:
            task = self._task(experiment_id, adapter.profile.model_id, case,
                              min(900, adapter.profile.max_timeout_seconds), self.evidence_refs)
            envelope = ProviderTaskRouter([adapter]).route(task)
            invocation = envelope.invocation_receipt.as_dict()
            provider_payload = envelope.normalized_result if envelope.status == "COMPLETED" else None
            payload, failures = None, list(envelope.validation_errors)
            if envelope.status == "COMPLETED":
                try:
                    payload, normalization_warnings = normalize_discovery_payload(
                        envelope.normalized_result, item_id=case.item_id,
                        evidence_refs=self.evidence_refs,
                    )
                    failures.extend(normalization_warnings)
                except ValueError as exc:
                    failures.append(str(exc))
            telemetry = self._telemetry(adapter, task.task_id)
            outcome = self._outcome(
                case, provider_payload, payload, envelope.status, failures, telemetry, invocation,
            )
            trials.append({
                "item_id": case.item_id, "public_input": case.public_input(),
                "truth_commitment": case.truth_commitment(),
                "provider_payload": provider_payload, "payload": payload,
                "outcome": outcome, "invocation_receipt": invocation,
            })
        profile = self._profile(adapter, trials)
        commitment = {
            "runtime_version": RUNTIME_VERSION, "experiment_id": experiment_id,
            "model_id": adapter.profile.model_id,
            "provider_id": adapter.profile.provider_id, "trials": trials, "profile": profile,
        }
        return {**commitment, "model_run_hash": hash_payload(commitment)}

    @staticmethod
    def _task(experiment_id, model_id, case, timeout, evidence_refs=EVIDENCE_REFS):
        safe = re.sub(r"[^A-Za-z0-9_.-]", "-", model_id)
        return ProviderCognitiveTask(
            task_id=f"{experiment_id}-{safe}-{case.item_id}", task_kind=TASK_KIND,
            objective=(
                "Classify whether the requested output object has at least two materially plausible, "
                "incompatible interpretations. Do not assume ambiguity. Use NO_MATERIAL_AMBIGUITY when "
                "object, unit, boundary, direction, and operation are sufficiently explicit. For "
                "AMBIGUITY_PRESENT, provide two rivals, the decisive contrast, and one discriminating "
                "question without solving. For NO_MATERIAL_AMBIGUITY, leave all four structure fields empty."
            ),
            inputs={"public_task": case.public_input(),
                    "audit_context": {"truth_commitment": case.truth_commitment()}},
            allowed_evidence=list(evidence_refs),
            expected_schema=discovery_schema(case.item_id, evidence_refs=evidence_refs),
            timeout_seconds=timeout,
            failure_semantics="record_failed_discovery_without_retrying_runtime_or_inventing_state",
        )

    @staticmethod
    def _telemetry(adapter, task_id):
        ledger = getattr(adapter, "telemetry_ledger", None)
        return ledger.items(task_ids=(task_id,)) if ledger is not None else ()

    @staticmethod
    def _outcome(case, provider_payload, payload, status, failures, telemetry, invocation):
        state = provider_payload.get("discovery_state") if isinstance(provider_payload, dict) else None
        observed = state if state in STATES else "UNAVAILABLE"
        commitment = {
            "item_id": case.item_id, "truth_commitment": case.truth_commitment(),
            "expected_state": case.expected_state, "observed_state": observed,
            "state_correct": observed == case.expected_state,
            "positive_hit": case.expected_state == POSITIVE and observed == POSITIVE,
            "null_correct": case.expected_state == NULL and observed == NULL,
            "false_positive": case.expected_state == NULL and observed == POSITIVE,
            "packet_contract_valid": payload is not None,
            "provider_status": status, "provider_failures": list(dict.fromkeys(failures)),
            "provider_calls": len(telemetry),
            "input_tokens": sum(item.input_tokens for item in telemetry),
            "output_tokens": sum(item.output_tokens for item in telemetry),
            "telemetry_hashes": [item.telemetry_hash for item in telemetry],
            "invocation_receipt_hash": invocation.get("receipt_hash", ""),
            "harness_owned": True, "provider_self_scored": False,
        }
        return {**commitment, "outcome_hash": hash_payload(commitment)}

    def _profile(self, adapter, trials):
        outcomes = [trial["outcome"] for trial in trials]
        positives = [item for item in outcomes if item["expected_state"] == POSITIVE]
        nulls = [item for item in outcomes if item["expected_state"] == NULL]
        recall = sum(item["positive_hit"] for item in positives) / len(positives)
        specificity = sum(item["null_correct"] for item in nulls) / len(nulls)
        commitment = {
            "model_id": adapter.profile.model_id, "provider_id": adapter.profile.provider_id,
            "independent_trials": len(outcomes),
            "successful_provider_trials": sum(item["provider_status"] == "COMPLETED" for item in outcomes),
            "detection_accuracy": sum(item["state_correct"] for item in outcomes) / len(outcomes),
            "positive_recall": recall, "null_specificity": specificity,
            "balanced_accuracy": (recall + specificity) / 2,
            "null_false_positive_rate": sum(item["false_positive"] for item in nulls) / len(nulls),
            "uncertain_or_unavailable": sum(item["observed_state"] in {"UNCERTAIN", "UNAVAILABLE"} for item in outcomes),
            "uncertain_states": sum(item["observed_state"] == "UNCERTAIN" for item in outcomes),
            "unavailable_states": sum(item["observed_state"] == "UNAVAILABLE" for item in outcomes),
            "packet_contract_successes": sum(item["packet_contract_valid"] for item in outcomes),
            "positive_packet_contract_rate": sum(
                item["expected_state"] == POSITIVE and item["packet_contract_valid"] for item in outcomes
            ) / len(positives),
            "total_provider_calls": sum(item["provider_calls"] for item in outcomes),
            "total_tokens": sum(item["input_tokens"] + item["output_tokens"] for item in outcomes),
            "outcome_hashes": [item["outcome_hash"] for item in outcomes],
            "selection_authority": False, "retention_authority": False,
        }
        return {**commitment, "profile_hash": hash_payload(commitment)}
