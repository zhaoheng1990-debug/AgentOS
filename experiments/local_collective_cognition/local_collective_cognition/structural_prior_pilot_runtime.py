"""Paired control/treatment runtime for on-demand structural-prior synthesis."""

from __future__ import annotations

from .collective_protocol import RoleRun
from .disagreement_case_failure import DisagreementCaseProviderFailure
from .ephemeral_structural_prior_contracts import (
    STRUCTURAL_PRIOR_TASK_KIND, build_structural_prior_receipt,
    structural_prior_schema, validate_structural_prior_receipt,
)
from .problem_formulation_case_runtime import ProblemFormulationCaseRuntime
from .problem_formulation_contracts import (
    problem_definition_schema, validate_problem_definition_receipt,
)


DEFAULT_PAIRED_ASSIGNMENTS = (
    ("modular-25", "gemma-2-2b-it", "qwen2.5-1.5b-instruct", "CONTROL_FIRST"),
    ("bayes-25", "qwen2.5-1.5b-instruct", "llama-3.2-1b-instruct", "TREATMENT_FIRST"),
    ("string-25", "llama-3.2-1b-instruct", "gemma-2-2b-it", "CONTROL_FIRST"),
    ("ratio-25", "gemma-2-2b-it", "llama-3.2-1b-instruct", "TREATMENT_FIRST"),
    ("sets-25", "qwen2.5-1.5b-instruct", "gemma-2-2b-it", "CONTROL_FIRST"),
    ("unit-25", "llama-3.2-1b-instruct", "qwen2.5-1.5b-instruct", "TREATMENT_FIRST"),
)
CALL_RATIO_LIMIT = 1.5
TOKEN_RATIO_LIMIT = 4.0


class StructuralPriorPilotRuntime(ProblemFormulationCaseRuntime):
    def run(self, *, experiment_id, assignments=DEFAULT_PAIRED_ASSIGNMENTS):
        controls, treatments, records, failures = [], [], [], []
        for item_id, proposer_id, elicitor_id, order in assignments:
            completed = {}
            try:
                if order == "CONTROL_FIRST":
                    control = self._definition_run(item_id, proposer_id, "CONTROL")
                    completed["control_work"] = _work(control)
                    prior = self._structure_run(item_id, elicitor_id)
                    completed["structural_prior_work"] = _work(prior)
                    treatment = self._definition_run(
                        item_id, proposer_id, "TREATMENT", prior=prior,
                    )
                else:
                    prior = self._structure_run(item_id, elicitor_id)
                    completed["structural_prior_work"] = _work(prior)
                    treatment = self._definition_run(
                        item_id, proposer_id, "TREATMENT", prior=prior,
                    )
                    completed["treatment_definition_work"] = _work(treatment)
                    control = self._definition_run(item_id, proposer_id, "CONTROL")
            except DisagreementCaseProviderFailure as exc:
                failures.append({
                    "item_id": item_id, "proposer_model_id": proposer_id,
                    "structure_elicitor_model_id": elicitor_id, "execution_order": order,
                    "completed_work": completed, **exc.as_dict(),
                })
                continue
            controls.append(control.result["problem_receipt"])
            treatments.append(treatment.result["problem_receipt"])
            records.append({
                "item_id": item_id, "proposer_model_id": proposer_id,
                "structure_elicitor_model_id": elicitor_id, "execution_order": order,
                "structural_prior": prior.result,
                "control_problem": control.result,
                "treatment_problem": treatment.result,
                "control_work": _work(control), "structural_prior_work": _work(prior),
                "treatment_definition_work": _work(treatment),
            })
        prior_hashes = [item["structural_prior"]["structural_prior_receipt"]["receipt_hash"]
                        for item in records]
        audit = self.base.harness.audit_paired_definitions(
            experiment_id=experiment_id, controls=tuple(controls),
            treatments=tuple(treatments), prior_receipt_hashes=tuple(prior_hashes),
        )
        control_work = _sum_work(item["control_work"] for item in records)
        prior_work = _sum_work(item["structural_prior_work"] for item in records)
        treatment_definition_work = _sum_work(
            item["treatment_definition_work"] for item in records
        )
        treatment_work = _add_work(prior_work, treatment_definition_work)
        cognitive_status = _status(audit)
        call_ratio = _ratio(treatment_work["provider_calls"], control_work["provider_calls"])
        token_ratio = _ratio(treatment_work["total_tokens"], control_work["total_tokens"])
        cost_passed = call_ratio <= CALL_RATIO_LIMIT and token_ratio <= TOKEN_RATIO_LIMIT
        return {
            "experiment_id": experiment_id,
            "protocol": {
                "protocol_version": "ephemeral_object_structure_expansion_mini_pilot_v0_1",
                "benchmark_id": self.base.harness.benchmark_id,
                "paired_same_proposer": True, "cross_model_structure_elicitor": True,
                "enum_calibration_reset_per_definition": True,
                "structural_prior_state": "EPHEMERAL_CANDIDATE",
                "structural_prior_truth_access": False,
                "retention_or_baseline_promotion_authorized": False,
                "claim_boundary": "six_item_minimum_validation_not_production_evidence",
                "inherited_call_ratio_limit": CALL_RATIO_LIMIT,
                "inherited_token_ratio_limit": TOKEN_RATIO_LIMIT,
            },
            "items": records, "pair_failures": failures,
            "paired_outcome_receipt": audit,
            "work": {
                "control": control_work, "structural_prior": prior_work,
                "treatment_definition": treatment_definition_work,
                "treatment_total": treatment_work,
                "treatment_call_ratio": call_ratio,
                "treatment_token_ratio": token_ratio,
                "cost_gate_passed": cost_passed,
            },
            "paired_items_completed": len(records),
            "paired_items_failed": len(failures),
            "cognitive_hypothesis_status": cognitive_status,
            "hypothesis_status": _combined_status(
                cognitive_status, cost_passed, len(records), len(assignments),
            ),
        }

    def _structure_run(self, item_id, model_id):
        run = self._execute(
            role_id=f"structural-prior-{model_id}-{item_id}", model_id=model_id,
            task_kind=STRUCTURAL_PRIOR_TASK_KIND,
            objective=(
                "Before any problem taxonomy is shown, expand the object's possible structure "
                "from the public task. Identify entities, relations, invariants, boundary "
                "conditions, and one question that distinguishes the leading structures. "
                "Do not select or mention an answer label."
            ),
            item_id=item_id,
            round_context={"role": "isolated_object_structure_elicitor",
                           "problem_taxonomy": "withheld", "peer_output": "withheld"},
            schema=structural_prior_schema(item_id), stage="STRUCTURAL_PRIOR",
        )
        receipt = build_structural_prior_receipt(
            task=run.tasks[-1], payload=run.result,
            provider_id=self.base.small_adapters[model_id].profile.provider_id,
            model_id=model_id,
        )
        validate_structural_prior_receipt(receipt, payload=run.result, task=run.tasks[-1])
        return RoleRun(
            role_id=run.role_id, model_id=run.model_id,
            result={**run.result, "structural_prior_receipt": receipt},
            tasks=run.tasks, audits=run.audits, telemetry=run.telemetry,
        )

    def _definition_run(self, item_id, model_id, arm, prior=None):
        self._reset_calibration(model_id)
        prior_packet = None if prior is None else {
            "payload": {key: value for key, value in prior.result.items()
                        if key != "structural_prior_receipt"},
            "receipt": prior.result["structural_prior_receipt"],
        }
        run = self._execute(
            role_id=f"structural-prior-{arm.lower()}-{model_id}-{item_id}",
            model_id=model_id, task_kind="pilot_problem_formulation",
            objective=(
                "Define the cognitive object before planning: mode, problem family, target "
                "quantity, and most important public constraint. Use the candidate-only "
                "structural prior when present, but independently reject it if unsupported."
            ),
            item_id=item_id,
            round_context={
                "role": "paired_problem_definer", "paired_arm": arm,
                "problem_candidate_id": arm + "_PROBLEM",
                "ephemeral_structure_prior": prior_packet or "NONE",
                "peer_problem": "withheld",
            },
            schema=problem_definition_schema(item_id, arm + "_PROBLEM"),
            stage=arm + "_PROBLEM_DEFINITION",
        )
        validate_problem_definition_receipt(
            run.result["problem_receipt"], task=run.tasks[-1],
            decision_receipt=run.result["decision_receipt"],
        )
        return run

    def _reset_calibration(self, model_id):
        pool = self.base.small_adapters[model_id].pool
        reset = getattr(pool, "reset_enum_calibration", None)
        if reset:
            reset(model_id)


def _work(run):
    return {
        "provider_calls": len(run.telemetry),
        "input_tokens": sum(item.input_tokens for item in run.telemetry),
        "output_tokens": sum(item.output_tokens for item in run.telemetry),
        "total_tokens": sum(item.input_tokens + item.output_tokens for item in run.telemetry),
        "inference_passes": run.result.get("decision_receipt", {}).get(
            "inference_passes", len(run.telemetry)
        ),
    }


def _sum_work(values):
    result = {key: 0 for key in (
        "provider_calls", "input_tokens", "output_tokens", "total_tokens", "inference_passes",
    )}
    for value in values:
        result = _add_work(result, value)
    return result


def _add_work(left, right):
    return {key: left[key] + right[key] for key in left}


def _ratio(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else None


def _status(audit):
    if audit["exact_definition_gain"] > 0 and audit["harmed_items"] == 0:
        return "PRELIMINARY_EXACT_OBJECT_SUPPORT"
    if audit["total_field_match_gain"] > 0 and audit["improved_items"] > audit["harmed_items"]:
        return "PRELIMINARY_FIELD_LEVEL_SUPPORT_ONLY"
    if audit["total_field_match_gain"] < 0 or audit["harmed_items"] > audit["improved_items"]:
        return "NEGATIVE_OR_ANTI_ADDITIVE_RESULT"
    return "INCONCLUSIVE_NO_OBJECT_GAIN"


def _combined_status(cognitive_status, cost_passed, completed, assigned):
    if completed < min(4, assigned):
        return "INSUFFICIENT_PAIRED_COVERAGE"
    if cognitive_status.startswith("PRELIMINARY") and not cost_passed:
        return cognitive_status + "_COST_NOT_CLEARED"
    return cognitive_status
