"""Live problem-quality lifecycle smoke over frozen LIFE-COG3R project evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


CORE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CORE_ROOT.parent
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
    AgendaCandidate,
    CascadingInvalidationGraph,
    CreditLedger,
    EndogenousAgendaLoop,
    JsonlCreditEventStore,
    OpenProblem,
    ProviderTaskRouter,
    SOURCE_GROUP,
    SOURCE_HUMAN_BASELINE,
    SOURCE_MEMBER,
)
from agentos_runtime import (  # noqa: E402
    DeliberationSeed,
    FeedbackCreditSubject,
    ProblemQualityLifecycleRuntime,
    ProblemTrialPlan,
)
from examples.project_source_group_cognition_smoke import (  # noqa: E402
    LiveProviderSpec,
    OpenAICompatibleJsonAdapter,
    default_paths,
    load_source_dossier,
)


DEFAULT_PROBLEM_SNAPSHOT = (
    CORE_ROOT / "examples" / "fixtures" / "life_cog3r_problem_seed_v0_1.json"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _hash_payload(payload: Any) -> str:
    return _hash_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _seed_from_snapshot(snapshot: dict[str, Any], source_refs: tuple[str, ...]) -> DeliberationSeed:
    payload = snapshot["deliberation_seed"]
    evidence_refs = tuple(
        next(ref for ref in source_refs if ref.endswith(suffix))
        for suffix in (
            "#LIFE_COG3R_IndependentQA_v0_1.json",
            "#LIFE_COG3R_MachineVerdict_v0_1.json",
        )
    )
    return DeliberationSeed.create(
        seed_id=payload["seed_id"],
        source_problem_id=payload["source_problem_id"],
        objective=payload["objective"],
        research_object=payload["research_object"],
        project_scope=payload["project_scope"],
        evidence_refs=evidence_refs,
        rival_explanations=tuple(payload["rival_explanations"]),
        operationalization=payload["operationalization"],
        falsifier=payload["falsifier"],
        required_harnesses=tuple(payload["required_harnesses"]),
        unresolved_conflicts=tuple(payload["unresolved_conflicts"]),
        expected_cbit_gain=payload["expected_cbit_gain"],
        agenda_selection_receipt_ref=payload["agenda_selection_receipt_ref"],
    )


def _message_payload(snapshot: dict[str, Any], message_type: str) -> dict[str, Any]:
    return next(
        item["payload"]
        for item in snapshot["messages"]
        if item["message_type"] == message_type
    )


def _run_independent_source_harness(dossier: dict[str, Any]) -> dict[str, Any]:
    qa = dossier["independent_structural_qa"]
    verdict = dossier["machine_verdict"]
    negative_control_section = dossier["pm_summary"].split("## Real Negative Controls", 1)[1].split("## Integrity", 1)[0]
    pass_values = [
        match.group(1) == "True"
        for match in re.finditer(r"\|\s*(True|False)\s*\|\s*$", negative_control_section, flags=re.MULTILINE)
    ]
    premise_discrimination = 1.0 if pass_values and any(pass_values) and not all(pass_values) else 0.0
    row_coverage = min(1.0, len(pass_values) / max(1, qa["negative_control_rows"]))
    rival_reduction = 0.0
    observed_cbit = round(
        0.30 * premise_discrimination + 0.20 * row_coverage + 0.50 * rival_reduction,
        12,
    )
    result = {
        "harness_id": "life-cog3r-independent-source-evidence-harness-v0-1",
        "source_project": dossier["source_project"],
        "machine_classification": verdict["machine_classification"],
        "g6_negative_controls": verdict["gates"]["G6_negative_controls"],
        "negative_control_rows": qa["negative_control_rows"],
        "negative_control_interventions": qa["negative_control_interventions"],
        "negative_control_pass_count": sum(pass_values),
        "negative_control_fail_count": len(pass_values) - sum(pass_values),
        "all_source_hash_checks_pass": all(qa["source_hash_checks"].values()),
        "structural_qa_pass": qa["structural_qa_pass"],
        "all_interventions_failed_claim_supported": bool(pass_values) and not any(pass_values),
        "observed_cbit_measurement": {
            "value": observed_cbit,
            "measurement_method": (
                "bounded_source_replay_proxy=0.30*premise_discrimination+"
                "0.20*row_coverage+0.50*rival_reduction"
            ),
            "components": {
                "premise_discrimination": premise_discrimination,
                "row_coverage": row_coverage,
                "rival_reduction": rival_reduction,
            },
            "proxy_boundary": "source_replay_cbit_proxy_not_ontological_information_measure",
        },
        "evidence_refs": dossier["source_refs"],
        "created_at": _utc_now(),
    }
    result["receipt_hash"] = _hash_payload(result)
    return result


class _AgendaFeedbackSink:
    def __init__(self, loop: EndogenousAgendaLoop) -> None:
        self.loop = loop

    def record_agenda_feedback(self, feedback):
        return self.loop.record_feedback(feedback)


class _CapturingAdapter:
    def __init__(self, delegate: OpenAICompatibleJsonAdapter) -> None:
        self.delegate = delegate
        self.profile = delegate.profile
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        return self.delegate.invoke(task)


def _reconstruct_agenda(snapshot: dict[str, Any], seed: DeliberationSeed) -> EndogenousAgendaLoop:
    candidates = _message_payload(snapshot, "PROBLEM_CANDIDATE_SET")["problem_candidates"]
    reviews = _message_payload(snapshot, "PROBLEM_CRITIQUE")["candidate_reviews"]
    assessments = _message_payload(snapshot, "RESEARCHABILITY_REPORT")["assessments"]
    candidate = next(item for item in candidates if item["problem_id"] == seed.source_problem_id)
    review = next(item for item in reviews if item["problem_id"] == seed.source_problem_id)
    assessment = next(item for item in assessments if item["problem_id"] == seed.source_problem_id)
    loop = EndogenousAgendaLoop(minimum_priority=0.2)
    loop.register_problem(
        OpenProblem(
            problem_id=seed.source_problem_id,
            statement=seed.objective,
            research_object=seed.research_object,
            scope=seed.project_scope,
            evidence_refs=seed.evidence_refs,
            rival_explanations=seed.rival_explanations,
        )
    )
    loop.propose(
        AgendaCandidate(
            candidate_id=f"agenda-{seed.source_problem_id}",
            problem_id=seed.source_problem_id,
            proposed_question=seed.objective,
            scope=seed.project_scope,
            provider_support_receipt_ref=seed.agenda_selection_receipt_ref,
            evidence_refs=seed.evidence_refs,
            expected_cbit_gain=seed.expected_cbit_gain,
            falsifiability=assessment["falsifiability"],
            tractability=assessment["tractability"],
            urgency=candidate["urgency"],
            novelty=candidate["novelty"],
            negative_transfer_risk=review["negative_transfer_risk"],
            normalized_cost=assessment["normalized_cost"],
        )
    )
    loop.select_candidate(
        f"agenda-{seed.source_problem_id}",
        seed.agenda_selection_receipt_ref,
    )
    return loop


def run_smoke(source_pack: Path, gate_file: Path, problem_snapshot_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = json.loads(problem_snapshot_path.read_text(encoding="utf-8"))
    dossier, source_inventory = load_source_dossier(source_pack, gate_file)
    seed = _seed_from_snapshot(snapshot, tuple(dossier["source_refs"]))
    source_harness = _run_independent_source_harness(dossier)
    harness_evidence_ref = f"evidence://life-cog3r-source-harness/{source_harness['receipt_hash']}"
    _write_json(output_dir / "source_hash_inventory.json", source_inventory)
    _write_json(output_dir / "independent_source_harness_receipt.json", source_harness)

    quality_spec = LiveProviderSpec(
        "deepseek",
        "deepseek-v4-pro",
        "https://api.deepseek.com/chat/completions",
        "DEEPSEEK_API_KEY",
        "problem_quality_assessment",
        3200,
        {"thinking": {"type": "disabled"}},
    )
    outcome_spec = LiveProviderSpec(
        "deepseek",
        "deepseek-v4-pro",
        "https://api.deepseek.com/chat/completions",
        "DEEPSEEK_API_KEY",
        "problem_trial_outcome_interpretation",
        3600,
        {"thinking": {"type": "disabled"}},
    )
    live_adapters = [
        _CapturingAdapter(OpenAICompatibleJsonAdapter(quality_spec)),
        _CapturingAdapter(OpenAICompatibleJsonAdapter(quality_spec)),
        _CapturingAdapter(OpenAICompatibleJsonAdapter(outcome_spec)),
        _CapturingAdapter(OpenAICompatibleJsonAdapter(outcome_spec)),
    ]
    router = ProviderTaskRouter(live_adapters)
    compact_evidence = {
        "frozen_acceptance_gates": dossier["frozen_acceptance_gates"],
        "machine_verdict": dossier["machine_verdict"],
        "independent_structural_qa": dossier["independent_structural_qa"],
        "pm_summary": dossier["pm_summary"],
        "source_refs": dossier["source_refs"],
    }
    runtime = ProblemQualityLifecycleRuntime(
        lifecycle_id="life-cog3r-problem-quality-live",
        seed=seed,
        provider_router=router,
        workspace_root=output_dir / "quality_lifecycle_public",
        admitted_evidence_refs=tuple((*dossier["source_refs"], harness_evidence_ref)),
        evidence_payload=compact_evidence,
    )

    candidate_payload = _message_payload(snapshot, "PROBLEM_CANDIDATE_SET")
    raw_candidates = candidate_payload["problem_candidates"]
    baseline_candidates = [item for item in raw_candidates if item["problem_id"] != seed.source_problem_id]
    assessment_refs = tuple(dossier["source_refs"])
    runtime.assess_problem(
        candidate_id=seed.source_problem_id,
        source_kind=SOURCE_GROUP,
        source_subject_id="life-cog3r-group-agenda",
        problem_statement=seed.objective,
        evidence_refs=assessment_refs,
    )
    for candidate in baseline_candidates:
        runtime.assess_problem(
            candidate_id=candidate["problem_id"],
            source_kind=SOURCE_MEMBER,
            source_subject_id="life-cog3r-problem-framer",
            problem_statement=candidate["question"],
            evidence_refs=assessment_refs,
        )
    runtime.assess_problem(
        candidate_id="LIFE_COG3R_HUMAN_BASELINE",
        source_kind=SOURCE_HUMAN_BASELINE,
        source_subject_id="life-cog3r-pm-gate-owner",
        problem_statement=(
            "Do the LIFE_COG3R negative controls preserve enough intervention validity and power "
            "to support retaining any G4 generalization-gap conclusion under the frozen G6 gate?"
        ),
        evidence_refs=assessment_refs,
    )
    evaluation = runtime.freeze_prospective_evaluation()
    _write_json(output_dir / "prospective_problem_quality_evaluation.json", evaluation.as_dict())

    lifecycle_path = "QUALITY_GATE_REJECTED"
    outcome = None
    feedback = None
    approval_error = ""
    try:
        plan = ProblemTrialPlan.create(
            trial_id="life-cog3r-problem-quality-source-trial",
            problem_id=seed.source_problem_id,
            required_harnesses=seed.required_harnesses,
            measurable_outcomes=(
                "negative_control_pass_fail_distribution",
                "all_interventions_failed_claim_support",
                "observed_cbit_gain",
                "residual_problem_definition",
            ),
            stop_conditions=("frozen_source_harness_receipt_interpreted",),
            budget={"source_replays": 1, "provider_interpretations": 1},
            rollback_ref="rollback://life-cog3r-problem-quality-source-trial",
        )
        runtime.approve_for_trial(
            trial_plan=plan,
            kernel_authorization_ref="kernel://life-cog3r-problem-quality-approved",
        )
        harness_receipts = {
            name: f"harness://{_hash_payload([name, source_harness['receipt_hash']])}"
            for name in seed.required_harnesses
        }
        runtime.activate_trial(
            kernel_execution_authorization_ref="kernel://life-cog3r-problem-quality-execution",
            harness_execution_receipts=harness_receipts,
        )
        independent_ref = harness_receipts[seed.required_harnesses[0]]
        outcome_errors = []
        for _ in range(3):
            try:
                outcome = runtime.record_outcome(
                    trial_evidence_refs=(harness_evidence_ref,),
                    harness_result_summary=source_harness,
                    independent_harness_receipt_ref=independent_ref,
                )
                break
            except (RuntimeError, ValueError) as exc:
                outcome_errors.append(str(exc))
        if outcome is None:
            raise RuntimeError(f"problem_quality_live_outcome_retries_exhausted:{outcome_errors}")
        agenda_loop = _reconstruct_agenda(snapshot, seed)
        ledger = CreditLedger(JsonlCreditEventStore(output_dir / "credit_events.jsonl"))
        graph = CascadingInvalidationGraph()
        feedback = runtime.apply_feedback(
            agenda_feedback_sink=_AgendaFeedbackSink(agenda_loop),
            credit_ledger=ledger,
            invalidation_graph=graph,
            credit_subjects=(
                FeedbackCreditSubject("life-cog3r-group-agenda", "agent"),
                FeedbackCreditSubject("deepseek", "provider"),
            ),
        )
        _write_json(output_dir / "problem_outcome_receipt.json", outcome.as_dict())
        _write_json(output_dir / "agenda_feedback_receipt.json", feedback.as_dict())
        _write_json(
            output_dir / "credit_profiles.json",
            {
                subject: ledger.profile(subject).as_dict()
                for subject in ("life-cog3r-group-agenda", "deepseek")
            },
        )
        lifecycle_path = "AUTHORIZED_SOURCE_TRIAL_COMPLETED"
    except ValueError as exc:
        if str(exc) != "problem_trial_quality_gate_failed":
            raise
        approval_error = str(exc)
        rejection = runtime.reject_for_trial(
            reason="prospective_quality_gate_failed_and_independent_source_harness_contradicted_problem_premise",
            kernel_adjudication_ref="kernel://life-cog3r-problem-quality-rejected",
            evidence_refs=tuple((*seed.evidence_refs, harness_evidence_ref)),
        )
        agenda_loop = _reconstruct_agenda(snapshot, seed)
        ledger = CreditLedger(JsonlCreditEventStore(output_dir / "credit_events.jsonl"))
        graph = CascadingInvalidationGraph()
        feedback = runtime.apply_feedback(
            agenda_feedback_sink=_AgendaFeedbackSink(agenda_loop),
            credit_ledger=ledger,
            invalidation_graph=graph,
            credit_subjects=(
                FeedbackCreditSubject("life-cog3r-group-agenda", "agent"),
                FeedbackCreditSubject("deepseek", "provider"),
            ),
        )
        _write_json(output_dir / "problem_quality_rejection_receipt.json", rejection.as_dict())
        _write_json(output_dir / "agenda_feedback_receipt.json", feedback.as_dict())
        _write_json(
            output_dir / "credit_profiles.json",
            {
                subject: ledger.profile(subject).as_dict()
                for subject in ("life-cog3r-group-agenda", "deepseek")
            },
        )

    lifecycle_snapshot = runtime.snapshot()
    _write_json(output_dir / "problem_quality_lifecycle_snapshot.json", lifecycle_snapshot.as_dict())
    replay = runtime.verify_replay()
    quality_tasks = [
        task
        for adapter in live_adapters
        for task in adapter.tasks
        if task.task_kind == "problem_quality_assessment"
    ]
    provider_task_audit = {
        "quality_task_count": len(quality_tasks),
        "uniform_input_surface": len({tuple(sorted(task.inputs)) for task in quality_tasks}) == 1,
        "tasks": [
            {
                "task_id": task.task_id,
                "task_kind": task.task_kind,
                "input_keys": sorted(task.inputs),
                "blind_candidate_id": task.inputs.get("candidate_id", ""),
                "source_kind_visible": "source_kind" in task.inputs,
                "source_subject_id_visible": "source_subject_id" in task.inputs,
            }
            for task in quality_tasks
        ],
    }
    provider_task_audit["audit_hash"] = _hash_payload(provider_task_audit)
    _write_json(output_dir / "provider_task_blinding_audit.json", provider_task_audit)
    group_observation = next(
        item for item in lifecycle_snapshot.observations if item.source_kind == SOURCE_GROUP
    )
    source_claim_mechanically_contradicted = not source_harness["all_interventions_failed_claim_supported"]
    quality_rejection_supported = (
        lifecycle_path == "QUALITY_GATE_REJECTED"
        and not evaluation.group_trial_gate_passed
        and source_claim_mechanically_contradicted
        and approval_error == "problem_trial_quality_gate_failed"
        and lifecycle_snapshot.state == "INVALIDATED"
        and feedback is not None
        and feedback.agenda_resolution == "INVALIDATED"
        and feedback.invalidation_receipt is not None
    )
    completed_trial_supported = (
        lifecycle_path == "AUTHORIZED_SOURCE_TRIAL_COMPLETED"
        and outcome is not None
        and feedback is not None
        and outcome.publication_authorized is False
        and feedback.route_selection_authority is False
    )
    gates = {
        "group_member_human_problem_set_compared": len(lifecycle_snapshot.observations) >= 4,
        "quality_provider_inputs_were_blinded": len(quality_tasks) == len(lifecycle_snapshot.observations)
        and provider_task_audit["uniform_input_surface"]
        and all(
            "source_kind" not in task.inputs
            and "source_subject_id" not in task.inputs
            and str(task.inputs.get("candidate_id", "")).startswith("blind-")
            for task in quality_tasks
        ),
        "prospective_quality_prediction_frozen": evaluation.frozen and not evaluation.execution_authorized,
        "group_vs_best_member_verdict_present": bool(evaluation.verdict_vs_best_member),
        "group_vs_human_verdict_present": bool(evaluation.verdict_vs_human_baseline),
        "independent_source_harness_recomputed": source_harness["structural_qa_pass"]
        and source_harness["all_source_hash_checks_pass"]
        and source_harness["negative_control_pass_count"] + source_harness["negative_control_fail_count"]
        == source_harness["negative_control_rows"],
        "quality_gate_or_authorized_trial_closed": quality_rejection_supported or completed_trial_supported,
        "candidate_never_self_promoted": lifecycle_snapshot.state != "ACTIVE",
        "no_publication_authority_leaked": outcome is None or outcome.publication_authorized is False,
        "quality_lifecycle_replay_valid": replay["valid"],
    }
    result = {
        "smoke_id": "life-cog3r-problem-quality-lifecycle-v0-1",
        "status": "PASS" if all(gates.values()) else "FAIL",
        "created_at": _utc_now(),
        "source_project": dossier["source_project"],
        "lifecycle_path": lifecycle_path,
        "lifecycle_state": lifecycle_snapshot.state,
        "selected_problem_id": seed.source_problem_id,
        "selected_question": seed.objective,
        "group_quality_score": group_observation.quality_score,
        "verdict_vs_best_member": evaluation.verdict_vs_best_member,
        "verdict_vs_human_baseline": evaluation.verdict_vs_human_baseline,
        "group_trial_gate_passed": evaluation.group_trial_gate_passed,
        "group_trial_gate_failures": list(evaluation.group_trial_gate_failures),
        "source_claim_mechanically_contradicted": source_claim_mechanically_contradicted,
        "gates": gates,
        "replay": replay,
        "boundary": (
            "This smoke compares a frozen group-selected problem with raw framer candidates and a PM-derived human baseline. "
            "It proves either evidence-backed quality interception or an explicitly authorized source-evidence trial; it does "
            "not establish general group superiority, independent member problem generation, or autonomous publication authority."
        ),
    }
    _write_json(output_dir / "smoke_result.json", result)

    manifest_files = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            manifest_files.append(
                {
                    "path": path.relative_to(output_dir).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": _hash_bytes(path.read_bytes()),
                }
            )
    manifest = {"status": result["status"], "files": manifest_files}
    manifest["manifest_hash"] = _hash_payload(manifest)
    _write_json(output_dir / "manifest.json", manifest)
    return result


def main() -> int:
    default_pack, default_gate = default_paths()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pack", type=Path, default=default_pack)
    parser.add_argument("--gate-file", type=Path, default=default_gate)
    parser.add_argument("--problem-snapshot", type=Path, default=DEFAULT_PROBLEM_SNAPSHOT)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "outputs" / f"problem_quality_lifecycle_smoke_{timestamp}",
    )
    args = parser.parse_args()
    try:
        result = run_smoke(args.source_pack, args.gate_file, args.problem_snapshot, args.output_dir)
    except Exception as exc:
        failure = {
            "status": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
            "created_at": _utc_now(),
        }
        _write_json(args.output_dir.resolve() / "smoke_failure.json", failure)
        print(json.dumps(failure, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
