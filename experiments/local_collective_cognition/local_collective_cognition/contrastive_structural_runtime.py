"""Selective, amortized runtime for compact contrastive structure packets."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .collective_protocol import RoleRun
from .contrastive_structural_contracts import (
    build_contrastive_batch_receipt, contrastive_batch_schema,
    normalize_contrastive_batch_payload, validate_contrastive_batch_receipt,
)
from .contrastive_structural_reporting import (
    audit_packet_quality, item_record, selected_effect,
)
from .contrastive_trigger_policy import (
    ContrastiveStructureTriggerPolicy, validate_contrastive_trigger_receipt,
)
from .disagreement_case_failure import DisagreementCaseProviderFailure
from .ephemeral_structural_prior_contracts import STRUCTURAL_PRIOR_TASK_KIND
from .problem_formulation_contracts import (
    problem_definition_schema, validate_problem_definition_receipt,
)
from .structural_prior_pilot_runtime import (
    CALL_RATIO_LIMIT, TOKEN_RATIO_LIMIT, StructuralPriorPilotRuntime,
    _add_work, _ratio, _status, _sum_work, _work,
)


DEFAULT_ASSIGNMENTS = (
    ("modular-26", "gemma-2-2b-it"),
    ("ratio-26", "qwen2.5-1.5b-instruct"),
    ("sets-26", "llama-3.2-1b-instruct"),
    ("bayes-26", "gemma-2-2b-it"),
    ("string-26", "qwen2.5-1.5b-instruct"),
    ("unit-26", "llama-3.2-1b-instruct"),
)


class ContrastiveStructuralRuntime(StructuralPriorPilotRuntime):
    def __init__(self, base, *, trigger_policy=None):
        super().__init__(base)
        self.trigger_policy = trigger_policy or ContrastiveStructureTriggerPolicy()

    def run(self, *, experiment_id, assignments=DEFAULT_ASSIGNMENTS):
        controls = [self._definition_run(item_id, model_id, "CONTROL")
                    for item_id, model_id in assignments]
        trigger = self.trigger_policy.evaluate(
            experiment_id=experiment_id, definition_runs=tuple(controls),
        )
        validate_contrastive_trigger_receipt(trigger)
        selected_ids = tuple(trigger["selected_item_ids"])
        try:
            structure = self._batch_structure_run(
                selected_ids, self._elicitor(assignments, selected_ids), trigger,
            ) if selected_ids else None
        except DisagreementCaseProviderFailure as exc:
            raise exc.prepend(tuple(controls)) from exc
        packets = ({packet["item_id"]: packet for packet in structure.result["packets"]}
                   if structure else {})
        revisions = {}
        for item_id, proposer_id in assignments:
            if item_id in packets:
                revisions[item_id] = self._redefine(
                    item_id, proposer_id, packets[item_id],
                    structure.result["contrastive_batch_receipt"],
                )
        control_by_id = {run.result["problem_receipt"]["item_id"]: run for run in controls}
        finals = [revisions.get(item_id, control_by_id[item_id])
                  for item_id, _ in assignments]
        audit = self.base.harness.audit_paired_definitions(
            experiment_id=experiment_id,
            controls=tuple(run.result["problem_receipt"] for run in controls),
            treatments=tuple(run.result["problem_receipt"] for run in finals),
            prior_receipt_hashes=(
                (structure.result["contrastive_batch_receipt"]["receipt_hash"],)
                if structure else ()
            ),
        )
        control_work = _sum_work(_work(run) for run in controls)
        incremental = _sum_work([
            *([_work(structure)] if structure else []),
            *(_work(run) for run in revisions.values()),
        ])
        selective_work = _add_work(control_work, incremental)
        call_ratio = _ratio(selective_work["provider_calls"], control_work["provider_calls"])
        token_ratio = _ratio(selective_work["total_tokens"], control_work["total_tokens"])
        cost_passed = call_ratio <= CALL_RATIO_LIMIT and token_ratio <= TOKEN_RATIO_LIMIT
        packet_audit = audit_packet_quality(self.base.harness, packets)
        downstream_status = _status(audit) if selected_ids else "NO_LOW_CONFIDENCE_TRIGGER"
        cognitive_status = (
            "REJECTED_EXACT_PUBLIC_PROMPT_RESTATEMENT"
            if packet_audit["exact_public_prompt_restatements"]
            else "INCONCLUSIVE_PACKET_SEMANTIC_QUALITY_UNVERIFIED"
        ) if selected_ids else "NO_LOW_CONFIDENCE_TRIGGER"
        return {
            "experiment_id": experiment_id,
            "protocol": {
                "protocol_version": "selective_contrastive_structure_mini_pilot_v0_2",
                "benchmark_id": self.base.harness.benchmark_id,
                "fresh_holdout": True, "truth_blind_trigger": True,
                "trigger_budget_items": self.trigger_policy.max_items,
                "one_batch_call_for_selected_items": True,
                "same_proposer_before_after": True,
                "cross_model_structure_elicitor": bool(structure),
                "structural_prior_state": "EPHEMERAL_CANDIDATE",
                "retention_or_baseline_promotion_authorized": False,
                "claim_boundary": "six_item_minimum_validation_not_production_evidence",
                "call_ratio_limit": CALL_RATIO_LIMIT,
                "token_ratio_limit": TOKEN_RATIO_LIMIT,
            },
            "trigger_receipt": trigger,
            "structure_batch": structure.result if structure else None,
            "packet_quality_audit": packet_audit,
            "items": [item_record(item_id, proposer_id, control_by_id[item_id],
                                  revisions.get(item_id), packets.get(item_id), _work)
                      for item_id, proposer_id in assignments],
            "paired_outcome_receipt": audit,
            "selected_effect": selected_effect(audit, selected_ids),
            "work": {
                "control": control_work, "incremental_structure_and_revision": incremental,
                "selective_total": selective_work, "selective_call_ratio": call_ratio,
                "selective_token_ratio": token_ratio, "cost_gate_passed": cost_passed,
            },
            "selected_items": len(selected_ids),
            "downstream_field_outcome_status": downstream_status,
            "cognitive_hypothesis_status": cognitive_status,
            "hypothesis_status": (
                cognitive_status if cost_passed else cognitive_status + "_COST_NOT_CLEARED"
            ),
        }

    def _batch_structure_run(self, item_ids, model_id, trigger):
        adapter = self.base.small_adapters[model_id]
        task = ProviderCognitiveTask(
            task_id="contrastive-structure-" + "-".join(item_ids),
            task_kind=STRUCTURAL_PRIOR_TASK_KIND,
            objective=(
                "For each public task, provide exactly two complete rival object-structure "
                "hypotheses, the decisive contrast between them, and one question whose answer "
                "would distinguish them. Keep each field compact. Do not select answer labels "
                "or use a problem taxonomy. Put the two hypotheses, contrast, and question in "
                "each compact packet string. Runtime treats packet semantics as opaque and "
                "binds item IDs and admitted evidence mechanically."
            ),
            inputs={
                "benchmark_public_input": self.base.harness.provider_inputs(item_ids),
                "benchmark_item_ids": list(item_ids),
                "audit_context": {"trigger_receipt": trigger},
                "round_context": {
                    "role": "batched_contrastive_structure_elicitor",
                    "problem_taxonomy": "withheld", "hidden_truth": "unavailable",
                },
            },
            allowed_evidence=list(self.base.harness.evidence_refs),
            expected_schema=contrastive_batch_schema(item_ids),
            timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        )
        audit = self.base.harness.audit_provider_task(task)
        if audit.status != "PASS_HIDDEN_ANSWER_ABSENT":
            raise ValueError("contrastive_structure_provider_input_audit_blocked")
        envelope = ProviderTaskRouter([adapter]).route(task)
        telemetry = self.base.telemetry_ledger.items(task_ids=(task.task_id,))
        run = RoleRun(
            role_id=task.task_id, model_id=model_id,
            result=envelope.normalized_result if isinstance(envelope.normalized_result, dict) else {},
            tasks=(task,), audits=(audit,), telemetry=telemetry,
        )
        if envelope.status != "COMPLETED":
            raise DisagreementCaseProviderFailure(
                stage="CONTRASTIVE_STRUCTURE", run=run,
                failures=tuple(envelope.validation_errors),
            )
        try:
            normalized = normalize_contrastive_batch_payload(
                run.result, item_ids=item_ids, evidence_refs=self.base.harness.evidence_refs,
            )
            receipt = build_contrastive_batch_receipt(
                task=task, payload=normalized, provider_payload=run.result,
                trigger_receipt_hash=trigger["receipt_hash"],
                provider_id=adapter.profile.provider_id, model_id=model_id,
            )
            validate_contrastive_batch_receipt(
                receipt, task=task, payload=normalized, provider_payload=run.result,
                trigger_receipt_hash=trigger["receipt_hash"],
            )
        except ValueError as exc:
            raise DisagreementCaseProviderFailure(
                stage="CONTRASTIVE_STRUCTURE", run=run, failures=(str(exc),),
            ) from exc
        return RoleRun(
            role_id=run.role_id, model_id=run.model_id,
            result={**normalized, "contrastive_batch_receipt": receipt},
            tasks=run.tasks, audits=run.audits, telemetry=run.telemetry,
        )

    def _redefine(self, item_id, model_id, packet, batch_receipt):
        self._reset_calibration(model_id)
        run = self._execute(
            role_id=f"contrastive-revision-{model_id}-{item_id}", model_id=model_id,
            task_kind="pilot_problem_formulation",
            objective=(
                "Reconsider the cognitive object using the compact rival structures and their "
                "discriminating question. Select mode, family, target, and critical constraint; "
                "reject both hypotheses if the public task does not support them."
            ),
            item_id=item_id,
            round_context={
                "role": "contrastive_problem_reviser",
                "problem_candidate_id": "SELECTIVE_PROBLEM",
                "contrastive_structure_packet": packet,
                "contrastive_batch_receipt_hash": batch_receipt["receipt_hash"],
                "peer_problem": "withheld",
            },
            schema=problem_definition_schema(item_id, "SELECTIVE_PROBLEM"),
            stage="CONTRASTIVE_REDEFINITION",
        )
        validate_problem_definition_receipt(
            run.result["problem_receipt"], task=run.tasks[-1],
            decision_receipt=run.result["decision_receipt"],
        )
        return run

    def _elicitor(self, assignments, selected_ids):
        proposers = {model_id for item_id, model_id in assignments if item_id in selected_ids}
        independent = sorted(set(self.base.small_adapters) - proposers)
        if not independent:
            raise ValueError("contrastive_structure_independent_elicitor_unavailable")
        return independent[0]
