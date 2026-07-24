"""Single-escalation runtime with independent Provider quality judgment."""

from __future__ import annotations

from .contrastive_quality_contracts import quality_schema, validate_quality_receipt
from .contrastive_quality_gate import (
    ContrastivePacketQualityGate, validate_quality_gate_receipt,
)
from .contrastive_structural_reporting import item_record, selected_effect
from .contrastive_structural_runtime import ContrastiveStructuralRuntime
from .contrastive_trigger_policy import (
    ContrastiveStructureTriggerPolicy, validate_contrastive_trigger_receipt,
)
from .disagreement_case_failure import DisagreementCaseProviderFailure
from .local_contrastive_quality_provider import QUALITY_JUDGE_ROLE
from .structural_prior_pilot_runtime import (
    CALL_RATIO_LIMIT, TOKEN_RATIO_LIMIT, _add_work, _ratio, _status, _sum_work, _work,
)


DEFAULT_ASSIGNMENTS = (
    ("modular-27", "gemma-2-2b-it"),
    ("ratio-27", "qwen2.5-1.5b-instruct"),
    ("sets-27", "llama-3.2-1b-instruct"),
    ("bayes-27", "gemma-2-2b-it"),
    ("string-27", "qwen2.5-1.5b-instruct"),
    ("unit-27", "llama-3.2-1b-instruct"),
)


class QualityGatedStructuralRuntime(ContrastiveStructuralRuntime):
    def __init__(self, base):
        super().__init__(base, trigger_policy=ContrastiveStructureTriggerPolicy(max_items=1))
        self.quality_gate = ContrastivePacketQualityGate()

    def run(self, *, experiment_id, assignments=DEFAULT_ASSIGNMENTS):
        controls = [self._definition_run(item_id, model_id, "CONTROL")
                    for item_id, model_id in assignments]
        trigger = self.trigger_policy.evaluate(
            experiment_id=experiment_id, definition_runs=tuple(controls),
        )
        validate_contrastive_trigger_receipt(trigger)
        selected_ids = tuple(trigger["selected_item_ids"])
        if len(selected_ids) != 1:
            return self._no_trigger_report(experiment_id, assignments, controls, trigger)
        item_id = selected_ids[0]
        proposer_id = dict(assignments)[item_id]
        elicitor_id = self._elicitor(assignments, selected_ids)
        try:
            structure = self._batch_structure_run(selected_ids, elicitor_id, trigger)
            packet = structure.result["packets"][0]
            public_prompt = self.base.harness.provider_inputs((item_id,))["questions"][0]["prompt"]
            pre_gate = self._mechanical_pre_gate(packet, public_prompt)
            quality = None if pre_gate and pre_gate["status"] == "BLOCK" else self._quality_run(
                item_id, self._quality_judge(proposer_id, elicitor_id), packet,
                structure.result["contrastive_batch_receipt"],
            )
        except DisagreementCaseProviderFailure as exc:
            raise exc.prepend(tuple(controls)) from exc
        batch_payload = {key: value for key, value in structure.result.items()
                         if key != "contrastive_batch_receipt"}
        gate = self.quality_gate.evaluate(
            trigger_receipt=trigger,
            batch_receipt=structure.result["contrastive_batch_receipt"],
            batch_payload=batch_payload, packet=packet,
            quality_receipt=quality.result["quality_receipt"],
            public_prompt=public_prompt, proposer_model_id=proposer_id,
        ) if quality else None
        if gate:
            validate_quality_gate_receipt(gate)
        revision = (self._redefine(
            item_id, proposer_id, packet, structure.result["contrastive_batch_receipt"],
        ) if gate and gate["status"] == "ALLOW" else None)
        control_by_id = {run.result["problem_receipt"]["item_id"]: run for run in controls}
        finals = [revision if key == item_id and revision else control_by_id[key]
                  for key, _ in assignments]
        audit = self.base.harness.audit_paired_definitions(
            experiment_id=experiment_id,
            controls=tuple(run.result["problem_receipt"] for run in controls),
            treatments=tuple(run.result["problem_receipt"] for run in finals),
            prior_receipt_hashes=tuple(item for item in (
                structure.result["contrastive_batch_receipt"]["receipt_hash"],
                pre_gate["receipt_hash"] if pre_gate else None,
                quality.result["quality_receipt"]["receipt_hash"] if quality else None,
                gate["receipt_hash"] if gate else None,
            ) if item),
        )
        control_work = _sum_work(_work(run) for run in controls)
        incremental = _sum_work([
            _work(structure), *([_work(quality)] if quality else []),
            *([_work(revision)] if revision else []),
        ])
        total_work = _add_work(control_work, incremental)
        call_ratio = _ratio(total_work["provider_calls"], control_work["provider_calls"])
        token_ratio = _ratio(total_work["total_tokens"], control_work["total_tokens"])
        cost_passed = call_ratio <= CALL_RATIO_LIMIT and token_ratio <= TOKEN_RATIO_LIMIT
        downstream = (_status(audit) if revision else "NO_REVISION_MECHANICAL_BLOCKED"
                      if pre_gate and pre_gate["status"] == "BLOCK"
                      else "NO_REVISION_QUALITY_BLOCKED")
        cognitive = ("QUALITY_GATE_ADMITTED_" + downstream if revision
                     else "MECHANICAL_PRE_GATE_BLOCKED"
                     if pre_gate and pre_gate["status"] == "BLOCK"
                     else "QUALITY_GATE_BLOCKED")
        return {
            "experiment_id": experiment_id,
            "protocol": {
                "protocol_version": "provider_backed_packet_quality_gate_mini_pilot_v0_3",
                "benchmark_id": self.base.harness.benchmark_id, "fresh_holdout": True,
                "truth_blind_trigger": True, "trigger_budget_items": 1,
                "independent_elicitor_and_quality_judge": True,
                "provider_semantic_quality_receipt": True,
                "kernel_quality_gate": True,
                "retention_or_baseline_promotion_authorized": False,
                "call_ratio_limit": CALL_RATIO_LIMIT, "token_ratio_limit": TOKEN_RATIO_LIMIT,
            },
            "trigger_receipt": trigger, "structure_batch": structure.result,
            "capability_routing_receipt": self._capability_routing_receipt(),
            "mechanical_pre_gate_receipt": pre_gate,
            "quality_judgment": quality.result if quality else None,
            "quality_gate_receipt": gate,
            "items": [item_record(key, model, control_by_id[key],
                                  revision if key == item_id else None,
                                  packet if key == item_id else None, _work)
                      for key, model in assignments],
            "paired_outcome_receipt": audit,
            "selected_effect": selected_effect(audit, selected_ids),
            "work": {
                "control": control_work, "incremental_quality_path": incremental,
                "quality_gated_total": total_work,
                "quality_gated_call_ratio": call_ratio,
                "quality_gated_token_ratio": token_ratio, "cost_gate_passed": cost_passed,
            },
            "selected_items": 1, "revision_authorized": revision is not None,
            "downstream_field_outcome_status": downstream,
            "cognitive_hypothesis_status": cognitive,
            "hypothesis_status": cognitive if cost_passed else cognitive + "_COST_NOT_CLEARED",
        }

    def _mechanical_pre_gate(self, packet, public_prompt):
        del packet, public_prompt
        return None

    def _capability_routing_receipt(self):
        return None

    def _quality_run(self, item_id, model_id, packet, batch_receipt):
        self._reset_calibration(model_id)
        run = self._execute(
            role_id=f"packet-quality-{model_id}-{item_id}", model_id=model_id,
            task_kind="pilot_structure_packet_quality",
            objective=(
                "Independently audit whether the packet contains two complete rival object "
                "structures, a decisive contrast, a genuinely discriminating question, and "
                "semantic content beyond restating the public task."
            ),
            item_id=item_id,
            round_context={
                "role": QUALITY_JUDGE_ROLE, "contrastive_structure_packet": packet,
                "contrastive_batch_receipt_hash": batch_receipt["receipt_hash"],
                "elicitor_model_id": batch_receipt["model_id"],
            },
            schema=quality_schema(item_id), stage="PACKET_QUALITY",
        )
        validate_quality_receipt(
            run.result["quality_receipt"], task=run.tasks[-1], packet=packet,
            decision_receipt=run.result["decision_receipt"],
            batch_receipt_hash=batch_receipt["receipt_hash"],
        )
        return run

    def _quality_judge(self, proposer_id, elicitor_id):
        candidates = sorted(set(self.base.small_adapters) - {proposer_id, elicitor_id})
        if len(candidates) != 1:
            raise ValueError("contrastive_quality_independent_judge_unavailable")
        return candidates[0]

    def _no_trigger_report(self, experiment_id, assignments, controls, trigger):
        del assignments
        control_work = _sum_work(_work(run) for run in controls)
        return {
            "experiment_id": experiment_id, "trigger_receipt": trigger,
            "selected_items": 0, "work": {"control": control_work},
            "cognitive_hypothesis_status": "NO_LOW_CONFIDENCE_TRIGGER",
            "hypothesis_status": "NO_LOW_CONFIDENCE_TRIGGER",
        }
