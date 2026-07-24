"""External orchestration protocol for the local collective-cognition pilot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .frozen_answer_harness import BenchmarkProviderInputAudit, FrozenAnswerBenchmarkHarness
from .pilot_benchmark import PILOT_ANSWER_SCHEMA, PILOT_ITEM_ANSWER_SCHEMA
from .pilot_reporting import PilotArmReport, build_pilot_report
from .provider_telemetry import ProviderInvocationTelemetry, ProviderTelemetryLedger


PILOT_TASK_KINDS = (
    "pilot_solo_answer",
    "pilot_disagreement_review",
    "pilot_disagreement_argument",
    "pilot_disagreement_adjudication",
    "pilot_constrained_tool_action",
    "pilot_hierarchical_tool_action",
    "pilot_plan_intent_action",
    "pilot_problem_formulation",
    "pilot_problem_critique",
    "pilot_problem_revision",
    "pilot_object_structure_expansion",
    "pilot_structure_packet_quality",
    "pilot_team_synthesis",
    "pilot_32b_baseline",
)


@dataclass(frozen=True)
class RoleRun:
    role_id: str
    model_id: str
    result: dict[str, Any]
    tasks: tuple[ProviderCognitiveTask, ...]
    audits: tuple[BenchmarkProviderInputAudit, ...]
    telemetry: tuple[ProviderInvocationTelemetry, ...]


class LocalCollectiveCognitionProtocol:
    """Run deterministic local arms while keeping held-out truth in the Harness."""

    def __init__(
        self,
        *,
        harness: FrozenAnswerBenchmarkHarness,
        small_adapters: dict[str, Any],
        baseline_adapter: Any,
        telemetry_ledger: ProviderTelemetryLedger,
        reviewer_model_id: str,
        synthesizer_model_id: str,
        max_role_attempts: int = 2,
    ) -> None:
        if len(small_adapters) < 2 or reviewer_model_id not in small_adapters or synthesizer_model_id not in small_adapters:
            raise ValueError("pilot_small_team_configuration_invalid")
        self.harness = harness
        self.small_adapters = dict(small_adapters)
        self.baseline_adapter = baseline_adapter
        self.telemetry_ledger = telemetry_ledger
        self.reviewer_model_id = reviewer_model_id
        self.synthesizer_model_id = synthesizer_model_id
        self.max_role_attempts = max_role_attempts
        self.item_ids = tuple(item["item_id"] for item in harness.provider_inputs()["questions"])

    def execute_role(self, **values: Any) -> RoleRun:
        return self._run_role(**values)

    def execute_item(
        self,
        *,
        role_id: str,
        adapter: Any,
        task_kind: str,
        role_instruction: str,
        round_context: dict[str, Any],
        item_id: str,
    ) -> RoleRun:
        if item_id not in self.item_ids:
            raise ValueError("pilot_execute_item_unknown")
        return self._run_role_attempts(
            role_id=f"{role_id}-{item_id}",
            adapter=adapter,
            task_kind=task_kind,
            objective=self._answer_objective(role_instruction) + f" Return only target item {item_id}.",
            round_context={**self._context_for_item(round_context, item_id), "target_item_id": item_id},
            expected_item_ids=(item_id,),
            item_id=item_id,
        )

    def score_arm(self, *args: Any, **kwargs: Any) -> PilotArmReport:
        return self._score_arm(*args, **kwargs)

    def majority_result(self, proposals: tuple[RoleRun, ...]) -> tuple[dict[str, Any], tuple[str, ...]]:
        return self._majority_result(proposals)

    @staticmethod
    def slice_item_run(run: RoleRun, item_id: str) -> RoleRun:
        tasks = tuple(item for item in run.tasks if item.inputs.get("benchmark_item_ids") == [item_id])
        task_ids = {item.task_id for item in tasks}
        audits = tuple(item for item in run.audits if item.task_id in task_ids)
        telemetry = tuple(item for item in run.telemetry if item.task_id in task_ids)
        answers = [item for item in run.result["answers"] if item["item_id"] == item_id]
        if len(answers) != 1 or not tasks or not audits or not telemetry:
            raise ValueError("pilot_item_run_slice_incomplete")
        return RoleRun(
            role_id=run.role_id + "-slice-" + item_id,
            model_id=run.model_id,
            result={"answers": answers, "evidence_refs": run.result["evidence_refs"]},
            tasks=tasks,
            audits=audits,
            telemetry=telemetry,
        )

    def run(
        self,
        experiment_id: str,
        *,
        baseline_run: RoleRun | None = None,
        baseline_observer: Callable[[RoleRun], Any] | None = None,
        prepare_small_models: Callable[[], Any] | None = None,
    ) -> dict[str, Any]:
        if not experiment_id:
            raise ValueError("pilot_experiment_id_required")

        baseline = baseline_run or self._run_role(
            role_id="deepseek-32b-solo",
            adapter=self.baseline_adapter,
            task_kind="pilot_32b_baseline",
            objective=self._answer_objective("Solve independently as the large-model baseline."),
            round_context={"role": "independent_large_model_baseline"},
            itemwise=True,
        )
        if baseline_observer is not None and baseline_run is None:
            baseline_observer(baseline)
        baseline_arm = self._score_arm(experiment_id, "DEEPSEEK_32B_SOLO", (baseline,), baseline.result, 1)

        if prepare_small_models is not None:
            prepare_small_models()

        role_prompts = (
            "Solve independently. Check formal constraints before selecting each option.",
            "Solve independently as a verifier. Recompute arithmetic and logic rather than guessing.",
            "Solve independently as a skeptic. Search for counterexamples and confounders.",
        )
        proposals = tuple(
            self._run_role(
                role_id=f"independent-{index + 1}",
                adapter=adapter,
                task_kind="pilot_solo_answer",
                objective=self._answer_objective(role_prompts[index % len(role_prompts)]),
                round_context={"role": f"independent_member_{index + 1}", "peer_outputs": "withheld"},
                itemwise=True,
            )
            for index, adapter in enumerate(self.small_adapters.values())
        )
        solo_arms = tuple(
            self._score_arm(experiment_id, f"SMALL_SOLO_{run.model_id}", (run,), run.result, 1)
            for run in proposals
        )

        majority_result, disagreement_ids = self._majority_result(proposals)
        majority_arm = self._score_arm(
            experiment_id, "SMALL_MAJORITY_NO_COMMUNICATION", proposals, majority_result, 1
        )

        public_proposals = [self._public_role_output(item) for item in proposals]
        review = self._run_role(
            role_id="disagreement-reviewer",
            adapter=self.small_adapters[self.reviewer_model_id],
            task_kind="pilot_disagreement_review",
            objective=self._answer_objective(
                "Review the independent proposals, focus on disagreements, identify reasoning errors, and recommend a complete answer vector."
            ),
            round_context={"role": "reviewer", "disagreement_item_ids": list(disagreement_ids), "independent_proposals": public_proposals},
            itemwise=True,
        )
        synthesis = self._run_role(
            role_id="team-synthesizer",
            adapter=self.small_adapters[self.synthesizer_model_id],
            task_kind="pilot_team_synthesis",
            objective=self._answer_objective(
                "Synthesize a final answer independently from the public questions, three proposals, and reviewer output. Do not follow majority when its reasoning is weaker."
            ),
            round_context={
                "role": "synthesizer",
                "disagreement_item_ids": list(disagreement_ids),
                "independent_proposals": public_proposals,
                "reviewer_output": self._public_role_output(review),
            },
            itemwise=True,
        )
        iterative_runs = (*proposals, review, synthesis)
        iterative_arm = self._score_arm(
            experiment_id, "SMALL_ITERATIVE_TEAM", iterative_runs, synthesis.result, 3
        )

        return build_pilot_report(
            experiment_id=experiment_id,
            solo_arms=solo_arms,
            majority_arm=majority_arm,
            iterative_arm=iterative_arm,
            baseline_arm=baseline_arm,
            disagreement_count=len(disagreement_ids),
        )

    def _run_role(
        self,
        *,
        role_id: str,
        adapter: Any,
        task_kind: str,
        objective: str,
        round_context: dict[str, Any],
        itemwise: bool = False,
    ) -> RoleRun:
        if itemwise:
            item_runs = tuple(
                self._run_role_attempts(
                    role_id=f"{role_id}-{item_id}",
                    adapter=adapter,
                    task_kind=task_kind,
                    objective=objective + f" Return only target item {item_id}.",
                    round_context={
                        **self._context_for_item(round_context, item_id),
                        "target_item_id": item_id,
                    },
                    expected_item_ids=(item_id,),
                    item_id=item_id,
                )
                for item_id in self.item_ids
            )
            return RoleRun(
                role_id=role_id,
                model_id=adapter.profile.model_id,
                result={
                    "answers": [run.result["answers"][0] for run in item_runs],
                    "evidence_refs": list(self.harness.evidence_refs),
                },
                tasks=tuple(item for run in item_runs for item in run.tasks),
                audits=tuple(item for run in item_runs for item in run.audits),
                telemetry=tuple(item for run in item_runs for item in run.telemetry),
            )
        return self._run_role_attempts(
            role_id=role_id,
            adapter=adapter,
            task_kind=task_kind,
            objective=objective,
            round_context=round_context,
            expected_item_ids=self.item_ids,
        )

    def _run_role_attempts(
        self,
        *,
        role_id: str,
        adapter: Any,
        task_kind: str,
        objective: str,
        round_context: dict[str, Any],
        expected_item_ids: tuple[str, ...],
        item_id: str = "",
    ) -> RoleRun:
        tasks: list[ProviderCognitiveTask] = []
        audits: list[BenchmarkProviderInputAudit] = []
        last_result: dict[str, Any] | None = None
        last_errors: tuple[str, ...] = ()
        for attempt in range(1, self.max_role_attempts + 1):
            task = ProviderCognitiveTask(
                task_id=f"{role_id}-attempt-{attempt}",
                task_kind=task_kind,
                objective=objective,
                inputs={
                    "benchmark_public_input": self.harness.provider_inputs((item_id,)) if item_id else self.harness.provider_inputs(),
                    "benchmark_item_ids": [item_id] if item_id else [],
                    "round_context": {
                        **round_context,
                        "attempt": attempt,
                        "previous_output": last_result if attempt > 1 else None,
                        "previous_format_errors": list(last_errors),
                    },
                },
                allowed_evidence=list(self.harness.evidence_refs),
                expected_schema=PILOT_ITEM_ANSWER_SCHEMA if item_id else PILOT_ANSWER_SCHEMA,
                timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
            )
            audit = self.harness.audit_provider_task(task)
            if audit.status != "PASS_HIDDEN_ANSWER_ABSENT":
                raise ValueError("pilot_provider_input_audit_blocked")
            tasks.append(task)
            audits.append(audit)
            envelope = ProviderTaskRouter([adapter]).route(task)
            last_result = envelope.normalized_result
            last_errors = (
                self._item_answer_errors(last_result, item_id)
                if item_id
                else self._answer_errors(last_result, expected_item_ids)
            )
            if envelope.status == "COMPLETED" and not last_errors and last_result is not None:
                task_ids = tuple(item.task_id for item in tasks)
                normalized_result = (
                    {
                        "answers": [{
                            "item_id": last_result["item_id"],
                            "answer": last_result["answer"],
                            "confidence": float(last_result["confidence"]),
                        }],
                        "evidence_refs": last_result["evidence_refs"],
                    }
                    if item_id
                    else last_result
                )
                return RoleRun(
                    role_id=role_id,
                    model_id=adapter.profile.model_id,
                    result=normalized_result,
                    tasks=tuple(tasks),
                    audits=tuple(audits),
                    telemetry=self.telemetry_ledger.items(task_ids=task_ids),
                )
            if envelope.status != "COMPLETED":
                last_errors = (*last_errors, *envelope.validation_errors)
        raise RuntimeError(f"pilot_role_failed:{role_id}:{','.join(last_errors)}")

    def _score_arm(
        self,
        experiment_id: str,
        arm_id: str,
        runs: tuple[RoleRun, ...],
        result: dict[str, Any],
        rounds: int,
    ) -> PilotArmReport:
        projected = self._project(result)
        tasks = tuple(task for run in runs for task in run.tasks)
        audits = tuple(audit for run in runs for audit in run.audits)
        telemetry = tuple(item for run in runs for item in run.telemetry)
        receipt = self.harness.evaluate(
            trial_id=experiment_id,
            arm=arm_id,
            candidate_output=projected,
            provider_input_audits=audits,
            telemetry_refs=tuple(item.evidence_ref for item in telemetry),
        )
        return PilotArmReport(
            arm_id=arm_id,
            rounds=rounds,
            model_ids=tuple(run.model_id for run in runs),
            answer_vector=tuple((item["item_id"], item["answer"]) for item in projected["answers"]),
            harness_receipt=receipt,
            telemetry=telemetry,
            task_ids=tuple(item.task_id for item in tasks),
        )

    def _majority_result(self, proposals: tuple[RoleRun, ...]) -> tuple[dict[str, Any], tuple[str, ...]]:
        maps = [dict((item["item_id"], item["answer"]) for item in self._project(run.result)["answers"]) for run in proposals]
        fallback = maps[list(self.small_adapters).index(self.reviewer_model_id)]
        answers = []
        disagreements = []
        for item_id in self.item_ids:
            values = [item[item_id] for item in maps]
            counts = {value: values.count(value) for value in set(values)}
            winner, count = max(counts.items(), key=lambda item: (item[1], item[0]))
            if len(counts) > 1:
                disagreements.append(item_id)
            if count == 1:
                winner = fallback[item_id]
            answers.append({"item_id": item_id, "answer": winner})
        return {"answers": answers, "evidence_refs": list(self.harness.evidence_refs)}, tuple(disagreements)

    def _project(self, result: dict[str, Any]) -> dict[str, Any]:
        answer_map = {item["item_id"]: item["answer"].strip().upper() for item in result["answers"]}
        return {
            "answers": [{"item_id": item_id, "answer": answer_map[item_id]} for item_id in self.item_ids],
            "evidence_refs": list(self.harness.evidence_refs),
        }

    def _answer_errors(
        self,
        result: dict[str, Any] | None,
        expected_item_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        if not isinstance(result, dict) or not isinstance(result.get("answers"), list):
            return ("answers_missing",)
        observed: dict[str, str] = {}
        failures: list[str] = []
        for item in result["answers"]:
            if not isinstance(item, dict) or not isinstance(item.get("item_id"), str) or not isinstance(item.get("answer"), str):
                failures.append("answer_item_invalid")
                continue
            item_id = item["item_id"]
            answer = item["answer"].strip().upper()
            if item_id in observed:
                failures.append(f"answer_duplicate:{item_id}")
            observed[item_id] = answer
            if answer not in {"A", "B", "C", "D"}:
                failures.append(f"answer_label_invalid:{item_id}")
        if set(observed) != set(expected_item_ids):
            failures.append("answer_coverage_mismatch")
        if result.get("evidence_refs") != list(self.harness.evidence_refs):
            failures.append("evidence_refs_mismatch")
        return tuple(dict.fromkeys(failures))

    def _item_answer_errors(self, result: dict[str, Any] | None, item_id: str) -> tuple[str, ...]:
        if not isinstance(result, dict):
            return ("item_answer_missing",)
        failures = []
        if result.get("item_id") != item_id:
            failures.append("item_id_mismatch")
        answer = result.get("answer")
        if not isinstance(answer, str) or answer.strip().upper() not in {"A", "B", "C", "D"}:
            failures.append("answer_label_invalid")
        confidence = result.get("confidence")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 <= float(confidence) <= 1.0
        ):
            failures.append("confidence_invalid")
        if result.get("evidence_refs") != list(self.harness.evidence_refs):
            failures.append("evidence_refs_mismatch")
        return tuple(failures)

    @staticmethod
    def _context_for_item(context: dict[str, Any], item_id: str) -> dict[str, Any]:
        filtered = dict(context)
        proposals = []
        for proposal in context.get("independent_proposals", []):
            proposal_copy = {**proposal, "result": dict(proposal["result"])}
            proposal_copy["result"]["answers"] = [
                item for item in proposal["result"].get("answers", []) if item.get("item_id") == item_id
            ]
            proposals.append(proposal_copy)
        if proposals:
            filtered["independent_proposals"] = proposals
        reviewer = context.get("reviewer_output")
        if reviewer:
            reviewer_copy = {**reviewer, "result": dict(reviewer["result"])}
            reviewer_copy["result"]["answers"] = [
                item for item in reviewer["result"].get("answers", []) if item.get("item_id") == item_id
            ]
            filtered["reviewer_output"] = reviewer_copy
        return filtered

    @staticmethod
    def _public_role_output(run: RoleRun) -> dict[str, Any]:
        return {"role_id": run.role_id, "model_id": run.model_id, "result": run.result}

    @staticmethod
    def _answer_objective(role_instruction: str) -> str:
        return (
            role_instruction
            + " Use only answer labels A, B, C, or D. "
            + "Report calibrated confidence from 0 to 1, return no explanation fields, and copy evidence_refs exactly."
        )


def role_run_as_dict(run: RoleRun) -> dict[str, Any]:
    return {
        "role_id": run.role_id,
        "model_id": run.model_id,
        "result": run.result,
        "tasks": [dict(item.__dict__) for item in run.tasks],
        "audits": [item.as_dict() for item in run.audits],
        "telemetry": [item.as_dict() for item in run.telemetry],
    }


def role_run_from_dict(payload: dict[str, Any]) -> RoleRun:
    audits = []
    for item in payload["audits"]:
        audits.append(BenchmarkProviderInputAudit(
            **{**item, "failures": tuple(item["failures"])}
        ))
    telemetry = []
    for item in payload["telemetry"]:
        telemetry.append(ProviderInvocationTelemetry(
            **{**item, "evidence_refs": tuple(item["evidence_refs"])}
        ))
    return RoleRun(
        role_id=payload["role_id"],
        model_id=payload["model_id"],
        result=payload["result"],
        tasks=tuple(ProviderCognitiveTask(**item) for item in payload["tasks"]),
        audits=tuple(audits),
        telemetry=tuple(telemetry),
    )
