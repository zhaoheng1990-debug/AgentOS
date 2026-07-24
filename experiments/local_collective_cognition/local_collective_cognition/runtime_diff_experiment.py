"""Runtime-derived candidate-diff revision experiment v0.35."""

from __future__ import annotations

import math

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_experiment import TASK_KIND
from .frontier_partial_admission import project_frontier_receipt
from .lineage_revision_experiment import (
    ARM_IDS,
    _call,
    _case_totals,
    _find_call,
    _provider_failure,
    _relation_reproducibility,
    _replication_surface,
    _revision_metrics,
    _runtime_metrics,
    _scoring_run,
)
from .provider_telemetry import hash_payload
from .runtime_candidate_diff import (
    DIFF_VERSION,
    derive_candidate_diff,
    runtime_diff_revision_schema,
)
from .runtime_diff_holdout import (
    REPLICATION_IDS,
    validate_runtime_diff_holdout,
)
from .runtime_escalation_policy import (
    POLICY_VERSION,
    derive_escalation_receipt,
)
from .selective_role_routing_experiment import _call_tokens, _metrics


RUNTIME_VERSION = "runtime_diff_experiment_v0_35"


def build_runtime_diff_preregistration(
    *, corpus, prior_analysis, prior_closure, prior_posthoc
):
    validate_runtime_diff_holdout(corpus)
    reasons = prior_posthoc.get("contract_failure_reason_counts", {})
    if (
        prior_analysis.get("decision") != "REJECT_LINEAGE_REVISION"
        or prior_analysis.get("candidate_state")
        != "LINEAGE_REVISION_REJECTED_STOP"
        or prior_closure.get("candidate_state")
        != "LINEAGE_REVISION_REJECTED_STOP"
        or prior_posthoc.get("status")
        != "POSTHOC_DECOMPOSITION_NOT_FROZEN_GATE"
        or reasons.get("REVISE_RELATION_OR_NOOP_INVALID", 0) <= 0
        or reasons.get("WORKER_ROUTE_MISMATCH", 0) <= 0
    ):
        raise ValueError("runtime_diff_prior_invalid")
    prior_total = int(prior_analysis["physical_total_tokens"])
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
        "source_trigger_policy_version": POLICY_VERSION,
        "source_candidate_diff_version": DIFF_VERSION,
        "frozen_hypothesis": (
            "Runtime-derived diffs can remove action-label and route-echo "
            "failures while preserving strict candidate lineage, allowing "
            "the triggered worker's actual content changes to be evaluated."
        ),
        "replication_ids": list(REPLICATION_IDS),
        "candidate_count_per_final_receipt": 3,
        "primary_contrast": "A2_REVISION_MINUS_A1_BASELINE",
        "success_gate": {
            "minimum_provider_completion_per_required_stage": 0.95,
            "minimum_prompt_identity_coverage": 1.0,
            "minimum_trigger_receipt_coverage": 0.95,
            "minimum_trigger_execution_coverage": 0.9,
            "minimum_lineage_contract_coverage": 0.9,
            "minimum_nonblock_coverage_per_arm": 0.9,
            "minimum_exact_three_coverage_per_arm": 0.9,
            "minimum_mean_gain": 0.15,
            "minimum_median_gain": 0.0,
            "minimum_win_rate": 0.55,
            "minimum_positive_replications": 2,
            "minimum_majority_positive_case_rate": 0.5,
            "maximum_severe_loss_rate": 0.2,
            "minimum_relation_jaccard_relative_to_baseline": -0.05,
            "minimum_triggered_revision_gross_median": 0.25,
            "minimum_triggered_revision_gross_win_rate": 0.55,
            "maximum_triggered_revision_gross_loss_rate": 0.25,
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.65),
        },
        "cost_policy": {
            "first_call_provider_payload_identical_between_arms": True,
            "runtime_trigger_adds_provider_tokens": False,
            "runtime_diff_adds_provider_tokens": False,
            "one_revision_worker_only_when_triggered": True,
            "no_separate_selector_call": True,
            "token_cost_already_subtracted_inside_realized_cbit": True,
            "cbit_per_token_is_diagnostic_not_acceptance_gate": True,
            "soft_expected_total_tokens": math.ceil(prior_total * 1.25),
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.65),
        },
        "trigger_policy_retuned_from_v0_33": False,
        "provider_declared_action_used": False,
        "provider_declared_route_used": False,
        "fresh_labels_available_during_inference": False,
        "external_semantic_panel_required": True,
        "selection_authority": False, "retention_write_allowed": False,
        "baseline_write_allowed": False, "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_runtime_diff_experiment(
    *, corpus, preregistration, adapter, checkpoint_callback=None
):
    validate_runtime_diff_holdout(corpus)
    _validate_preregistration(preregistration, corpus)
    refs = tuple(corpus["evidence_refs"])
    matrix = [
        (rep, arm, item) for rep in REPLICATION_IDS for arm in ARM_IDS
        for item in corpus["public_surface"]["items"]
    ]
    matrix.sort(key=lambda value: hash_payload([
        RUNTIME_VERSION, "STANDARD", value[0], value[1],
        value[2]["case_id"],
    ]))
    calls, raw_receipts = [], {}
    provisional_projections, final_projections = {}, {}
    trigger_receipts, revision_receipts, failures = {}, {}, []
    for rep, arm, canonical in matrix:
        item = _replication_surface(
            canonical, replication_id=rep,
            corpus_hash=corpus["artifact_hash"],
        )
        task = _standard_task(
            item=item, replication_id=rep, experimental_arm_id=arm,
            refs=refs, adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=rep, arm_id=arm, case_id=item["case_id"],
            stage="STANDARD_ONTOLOGY", route_id="A1_ONTOLOGY",
            task=task, envelope=envelope,
        )
        calls.append(call)
        raw_key = f"{rep}:{arm}:STANDARD_ONTOLOGY:{item['case_id']}"
        key = f"{rep}:{arm}:{item['case_id']}"
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            raw = envelope.normalized_result
            raw_receipts[raw_key] = raw
            projection = project_frontier_receipt(
                raw_receipt=raw, item=item, arm_id="A1_ONTOLOGY",
                evidence_refs=refs,
            )
            if arm == "A1_BASELINE":
                final_projections[key] = projection
            else:
                provisional_projections[key] = projection
                trigger = derive_escalation_receipt(
                    raw_receipt=raw, item=item,
                )
                trigger_receipts[key] = trigger
                if not trigger["triggered"]:
                    final_projections[key] = projection
        _checkpoint(
            checkpoint_callback, corpus, preregistration, calls,
            raw_receipts, provisional_projections, final_projections,
            trigger_receipts, revision_receipts, failures,
        )
    for key, trigger in sorted(trigger_receipts.items()):
        if not trigger["triggered"]:
            continue
        rep, arm, case_id = key.split(":", 2)
        canonical = next(
            value for value in corpus["public_surface"]["items"]
            if value["case_id"] == case_id
        )
        item = _replication_surface(
            canonical, replication_id=rep,
            corpus_hash=corpus["artifact_hash"],
        )
        provisional = raw_receipts[
            f"{rep}:{arm}:STANDARD_ONTOLOGY:{case_id}"
        ]
        task = _revision_task(
            item=item, replication_id=rep, trigger=trigger,
            provisional=provisional, refs=refs, adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=rep, arm_id=arm, case_id=case_id,
            stage="LINEAGE_REVISION_WORKER",
            route_id=trigger["route_id"], task=task, envelope=envelope,
        )
        calls.append(call)
        raw_key = f"{rep}:{arm}:LINEAGE_REVISION_WORKER:{case_id}"
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            raw = envelope.normalized_result
            raw_receipts[raw_key] = raw
            diff = derive_candidate_diff(
                provisional_receipt=provisional, final_receipt=raw,
                trigger=trigger, item=item,
            )
            if diff["failures"]:
                failures.append({
                    "replication_id": rep, "arm_id": arm,
                    "case_id": case_id, "stage": "RUNTIME_DIFF",
                    "failures": diff["failures"],
                    "raw_receipt_hash": hash_payload(raw),
                })
            else:
                revision_receipts[key] = diff
                final_projections[key] = project_frontier_receipt(
                    raw_receipt=raw, item=item, arm_id="A1_ONTOLOGY",
                    evidence_refs=refs,
                )
        _checkpoint(
            checkpoint_callback, corpus, preregistration, calls,
            raw_receipts, provisional_projections, final_projections,
            trigger_receipts, revision_receipts, failures,
        )
    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_trigger_policy_version": POLICY_VERSION,
        "source_candidate_diff_version": DIFF_VERSION,
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id, "task_calls": calls,
        "raw_receipts": raw_receipts,
        "provisional_projections": provisional_projections,
        "final_projections": final_projections,
        "trigger_receipts": trigger_receipts,
        "revision_receipts": revision_receipts, "failures": failures,
        "raw_receipts_preserved_before_projection": True,
        "private_truth_exposed": False,
        "provider_declared_action_used": False,
        "provider_declared_route_used": False,
        "trigger_policy_retuned_from_v0_33": False,
        "selection_authority": False, "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_runtime_diff_experiment(*, corpus, preregistration, run):
    validate_runtime_diff_holdout(corpus)
    _validate_preregistration(preregistration, corpus)
    _validate_run(run, corpus, preregistration)
    ledgers, case_deltas, rep_metrics = {}, {}, {}
    for rep in REPLICATION_IDS:
        ledger = build_realized_cbit_ledger(
            corpus=corpus, run=_scoring_run(run, replication_id=rep),
        )
        ledgers[rep] = ledger
        totals = _case_totals(ledger)
        deltas = {
            item["case_id"]: round(
                totals[(item["case_id"], "A2_REVISION")]["net"]
                - totals[(item["case_id"], "A1_BASELINE")]["net"], 6
            ) for item in corpus["public_surface"]["items"]
        }
        case_deltas[rep] = deltas
        rep_metrics[rep] = {
            "arm_tokens": {
                arm: ledger["arm_metrics"][arm]["total_tokens"]
                for arm in ARM_IDS
            },
            "contrast": _metrics(list(deltas.values())),
        }
    pooled = [
        value for values in case_deltas.values() for value in values.values()
    ]
    metrics = _metrics(pooled)
    majority = round(sum(
        sum(case_deltas[rep][case] > 0 for rep in REPLICATION_IDS) >= 2
        for case in case_deltas[REPLICATION_IDS[0]]
    ) / corpus["case_count"], 6)
    positive_reps = sum(
        value["contrast"]["mean"] > 0 for value in rep_metrics.values()
    )
    runtime = _runtime_metrics(run, corpus)
    revision = _revision_metrics(corpus, run, ledgers)
    relation = {
        arm: _relation_reproducibility(
            {"formal_projections": run["final_projections"]},
            arm_id=arm, corpus=corpus,
        ) for arm in ARM_IDS
    }
    total_tokens = sum(_call_tokens(value) for value in run["task_calls"])
    gate = preregistration["success_gate"]
    gross = revision["triggered_gross_candidate_uplift"]
    conditions = {
        "minimum_provider_completion_per_required_stage": all(
            value >= gate["minimum_provider_completion_per_required_stage"]
            for value in runtime[
                "provider_completion_per_required_stage"
            ].values()
        ),
        "minimum_prompt_identity_coverage": runtime[
            "prompt_identity_coverage"
        ] >= gate["minimum_prompt_identity_coverage"],
        "minimum_trigger_receipt_coverage": runtime[
            "trigger_receipt_coverage"
        ] >= gate["minimum_trigger_receipt_coverage"],
        "minimum_trigger_execution_coverage": runtime[
            "trigger_execution_coverage"
        ] >= gate["minimum_trigger_execution_coverage"],
        "minimum_lineage_contract_coverage": runtime[
            "lineage_contract_coverage"
        ] >= gate["minimum_lineage_contract_coverage"],
        "minimum_nonblock_coverage_per_arm": all(
            value >= gate["minimum_nonblock_coverage_per_arm"]
            for value in runtime["final_nonblock_coverage_per_arm"].values()
        ),
        "minimum_exact_three_coverage_per_arm": all(
            value >= gate["minimum_exact_three_coverage_per_arm"]
            for value in runtime[
                "final_exact_three_coverage_per_arm"
            ].values()
        ),
        "minimum_mean_gain": metrics["mean"] >= gate["minimum_mean_gain"],
        "minimum_median_gain": metrics["median"]
        >= gate["minimum_median_gain"],
        "minimum_win_rate": metrics["win_rate"]
        >= gate["minimum_win_rate"],
        "minimum_positive_replications": positive_reps
        >= gate["minimum_positive_replications"],
        "minimum_majority_positive_case_rate": majority
        >= gate["minimum_majority_positive_case_rate"],
        "maximum_severe_loss_rate": metrics["severe_loss_rate"]
        <= gate["maximum_severe_loss_rate"],
        "minimum_relation_jaccard_relative_to_baseline": (
            relation["A2_REVISION"]["mean_pairwise_relation_jaccard"]
            - relation["A1_BASELINE"]["mean_pairwise_relation_jaccard"]
            >= gate["minimum_relation_jaccard_relative_to_baseline"]
        ),
        "minimum_triggered_revision_gross_median": (
            gross is not None and gross["median"]
            >= gate["minimum_triggered_revision_gross_median"]
        ),
        "minimum_triggered_revision_gross_win_rate": (
            gross is not None and gross["win_rate"]
            >= gate["minimum_triggered_revision_gross_win_rate"]
        ),
        "maximum_triggered_revision_gross_loss_rate": (
            gross is not None and gross["loss_count"] / gross["count"]
            <= gate["maximum_triggered_revision_gross_loss_rate"]
        ),
        "hard_runaway_total_tokens": total_tokens
        <= gate["hard_runaway_total_tokens"],
        "authority_boundary_preserved": all(
            run.get(key) is False for key in (
                "selection_authority", "retention_authority",
                "production_authority",
            )
        ),
    }
    passed = all(conditions.values())
    decision = "PASS_RUNTIME_DIFF" if passed else "REJECT_RUNTIME_DIFF"
    state = (
        "RUNTIME_DIFF_PASSED_READY_EXTERNAL_PANEL"
        if passed else "RUNTIME_DIFF_REJECTED_STOP"
    )
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "replication_ledgers": ledgers, "case_deltas": case_deltas,
        "replication_metrics": rep_metrics,
        "pooled_contrast_metrics": metrics,
        "majority_positive_case_rate": majority,
        "positive_replication_count": positive_reps,
        "runtime_metrics": runtime, "revision_metrics": revision,
        "relation_reproducibility": relation,
        "physical_total_tokens": total_tokens,
        "conditions": conditions,
        "runtime_diff_gate": "PASS" if passed else "REJECT",
        "decision": decision, "external_semantic_panel_authorized": passed,
        "core_integration_authorized": False, "candidate_state": state,
        "selection_authority": False, "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _revision_task(
    *, item, replication_id, trigger, provisional, refs, adapter
):
    prompts = {
        "MECHANISM": "Improve mechanism coverage where it adds Cbit.",
        "ADVERSARIAL": "Use counterevidence to repair weak candidates.",
        "COORDINATE_SHIFT": "Repair collapsed object coordinates.",
    }
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-DIFF-"
            f"{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            f"{prompts[trigger['route_id']]} Inspect the provisional receipt "
            "and return the best final three-candidate receipt using exactly "
            "the same candidate IDs. Preserve a candidate unchanged when no "
            "specific revision has clear expected value. Do not declare "
            "action labels or repeat the route; Runtime computes the diff."
        ),
        inputs={
            "stage": "RUNTIME_DIFF_REVISION",
            "replication_id": replication_id,
            "runtime_diagnostic": trigger,
            "provisional_receipt": provisional,
            "public_case": item, "private_outcome_available": False,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=runtime_diff_revision_schema(
            item=item, refs=refs, provisional_receipt=provisional,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _standard_task(
    *, item, replication_id, experimental_arm_id, refs, adapter
):
    from .collaborative_stability_experiment import exact_three_schema

    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-"
            f"{experimental_arm_id}-{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            "Build a compact object census and return exactly three strongest "
            "evidence-bound, distinct, falsifiable problem candidates."
        ),
        inputs={
            "stage": "STANDARD_ONTOLOGY",
            "replication_id": replication_id,
            "arm_id": "A1_ONTOLOGY", "public_case": item,
            "private_outcome_available": False,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=exact_three_schema(
            item=item, arm_id="A1_ONTOLOGY", refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _checkpoint(
    callback, corpus, preregistration, calls, raw_receipts,
    provisional_projections, final_projections, trigger_receipts,
    revision_receipts, failures,
):
    if callback is None:
        return
    commitment = {
        "progress_version": "runtime_diff_progress_v0_35",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "completed_task_count": len(calls), "task_calls": list(calls),
        "raw_receipts": dict(raw_receipts),
        "provisional_projections": dict(provisional_projections),
        "final_projections": dict(final_projections),
        "trigger_receipts": dict(trigger_receipts),
        "revision_receipts": dict(revision_receipts),
        "failures": list(failures),
        "original_receipts_preserved": True, "resume_authority": False,
    }
    callback({**commitment, "artifact_hash": hash_payload(commitment)})


def _validate_preregistration(preregistration, corpus):
    commitment = {
        key: value for key, value in preregistration.items()
        if key != "artifact_hash"
    }
    if (
        preregistration.get("artifact_hash") != hash_payload(commitment)
        or preregistration.get("source_corpus_hash") != corpus["artifact_hash"]
    ):
        raise ValueError("runtime_diff_preregistration_invalid")


def _validate_run(run, corpus, preregistration):
    commitment = {
        key: value for key, value in run.items() if key != "run_hash"
    }
    if (
        run.get("run_hash") != hash_payload(commitment)
        or run.get("source_corpus_hash") != corpus["artifact_hash"]
        or run.get("source_preregistration_hash")
        != preregistration["artifact_hash"]
    ):
        raise ValueError("runtime_diff_run_invalid")
