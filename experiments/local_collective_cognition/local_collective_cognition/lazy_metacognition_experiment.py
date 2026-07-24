"""Receipt-native lazy metacognition experiment v0.32."""

from __future__ import annotations

import copy
import math
from collections import Counter, defaultdict

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .collaborative_stability_experiment import exact_three_schema
from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_experiment import TASK_KIND
from .frontier_partial_admission import project_frontier_receipt
from .lazy_metacognition_holdout import (
    REPLICATION_IDS,
    validate_lazy_metacognition_holdout,
)
from .provider_telemetry import hash_payload
from .selective_role_routing_experiment import (
    ROUTE_IDS,
    _call_tokens,
    _combined_usage,
    _generation_task,
    _metrics,
    _relation_reproducibility,
    _replication_surface,
)


RUNTIME_VERSION = "lazy_metacognition_experiment_v0_32"
ARM_IDS = ("A1_BASELINE", "A2_LAZY")
SPECIALIZED_ROUTE_IDS = tuple(
    value for value in ROUTE_IDS if value != "A1_ONTOLOGY"
)
GAIN_BANDS = ("NEGATIVE", "NEUTRAL", "POSITIVE", "HIGH_POSITIVE")
UNCERTAINTY_STATES = ("LOW", "MEDIUM", "HIGH")
ANTI_ADDITIVE_RISKS = (
    "REDUNDANT_WITH_DIRECT_SYNTHESIS",
    "WEAK_EVIDENCE_BINDING",
    "COORDINATION_OR_TOKEN_FRICTION",
    "OBJECT_MISMATCH",
    "NEGATIVE_TRANSFER",
    "NONE",
)


def build_lazy_metacognition_preregistration(
    *, corpus, prior_analysis, prior_closure
):
    validate_lazy_metacognition_holdout(corpus)
    prior_plans = prior_analysis.get("plan_metrics", {})
    if (
        prior_analysis.get("decision") != "REJECT_COMPARATIVE_PLAN_INTENT"
        or prior_analysis.get("candidate_state")
        != "COMPARATIVE_PLAN_INTENT_REJECTED_STOP"
        or prior_closure.get("candidate_state")
        != "COMPARATIVE_PLAN_INTENT_REJECTED_STOP"
        or prior_plans.get("selected_route_distribution")
        != {"A1_ONTOLOGY": 24}
        or prior_plans.get("execution_mode_distribution")
        != {"NO_ESCALATION": 24}
    ):
        raise ValueError("lazy_metacognition_prior_invalid")
    prior_total = int(prior_analysis["total_tokens"])
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "frozen_hypothesis": (
            "Embedding a compact escalation trigger in the ordinary "
            "candidate receipt, and paying for a specialized role only when "
            "that trigger fires, can improve net realized Cbit without the "
            "fixed comparative-planning tax observed in v0.31."
        ),
        "route_ids": list(ROUTE_IDS),
        "specialized_route_ids": list(SPECIALIZED_ROUTE_IDS),
        "replication_ids": list(REPLICATION_IDS),
        "candidate_count_per_final_receipt": 3,
        "primary_contrast": "A2_LAZY_MINUS_A1_BASELINE",
        "success_gate": {
            "minimum_provider_completion_per_required_stage": 0.95,
            "minimum_trigger_contract_coverage": 0.9,
            "minimum_trigger_execution_coverage": 0.9,
            "minimum_nonblock_coverage_per_arm": 0.9,
            "minimum_exact_three_coverage_per_arm": 0.9,
            "minimum_mean_gain": 0.15,
            "minimum_median_gain": 0.0,
            "minimum_win_rate": 0.55,
            "minimum_positive_replications": 2,
            "minimum_majority_positive_case_rate": 0.5,
            "maximum_severe_loss_rate": 0.2,
            "minimum_relation_jaccard_relative_to_baseline": -0.05,
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.25),
        },
        "cost_policy": {
            "baseline_calls_per_cell": 1,
            "lazy_base_calls_per_cell": 1,
            "specialized_calls_only_when_triggered": True,
            "token_cost_already_subtracted_inside_realized_cbit": True,
            "cbit_per_token_is_diagnostic_not_acceptance_gate": True,
            "soft_expected_total_tokens": prior_total,
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.25),
        },
        "trigger_rate_is_acceptance_gate": False,
        "fresh_labels_available_during_inference": False,
        "external_semantic_panel_required": True,
        "selection_authority": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_lazy_metacognition_experiment(
    *, corpus, preregistration, adapter, checkpoint_callback=None
):
    validate_lazy_metacognition_holdout(corpus)
    _validate_preregistration(preregistration, corpus)
    refs = tuple(corpus["evidence_refs"])
    first_stage = [
        (replication_id, arm_id, item)
        for replication_id in REPLICATION_IDS
        for arm_id in ARM_IDS
        for item in corpus["public_surface"]["items"]
    ]
    first_stage.sort(key=lambda value: hash_payload([
        RUNTIME_VERSION, "FIRST_STAGE", value[0], value[1],
        value[2]["case_id"],
    ]))
    calls = []
    raw_receipts = {}
    provisional_projections = {}
    final_projections = {}
    trigger_receipts = {}
    failures = []

    for replication_id, arm_id, canonical_item in first_stage:
        item = _replication_surface(
            canonical_item,
            replication_id=replication_id,
            corpus_hash=corpus["artifact_hash"],
        )
        stage = "BASELINE" if arm_id == "A1_BASELINE" else "LAZY_BASE"
        task = _base_task(
            item=item,
            replication_id=replication_id,
            arm_id=arm_id,
            refs=refs,
            adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=replication_id,
            arm_id=arm_id,
            case_id=item["case_id"],
            stage=stage,
            route_id="A1_ONTOLOGY",
            task=task,
            envelope=envelope,
        )
        calls.append(call)
        raw_key = (
            f"{replication_id}:{arm_id}:{stage}:{item['case_id']}"
        )
        final_key = f"{replication_id}:{arm_id}:{item['case_id']}"
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            raw = envelope.normalized_result
            raw_receipts[raw_key] = raw
            if arm_id == "A2_LAZY":
                trigger_failures = _trigger_failures(raw, item=item)
                if trigger_failures:
                    failures.append({
                        "replication_id": replication_id,
                        "arm_id": arm_id,
                        "case_id": item["case_id"],
                        "stage": "TRIGGER_CONTRACT",
                        "failures": trigger_failures,
                        "raw_receipt_hash": hash_payload(raw),
                    })
                    _checkpoint(
                        checkpoint_callback, corpus, preregistration,
                        calls, raw_receipts, provisional_projections,
                        final_projections, trigger_receipts, failures,
                    )
                    continue
                trigger_receipts[final_key] = raw["escalation_trigger"]
            projection = project_frontier_receipt(
                raw_receipt=raw,
                item=item,
                arm_id="A1_ONTOLOGY",
                evidence_refs=refs,
            )
            if arm_id == "A1_BASELINE":
                final_projections[final_key] = projection
            else:
                provisional_projections[final_key] = projection
                if not raw["escalation_trigger"]["triggered"]:
                    final_projections[final_key] = projection
        _checkpoint(
            checkpoint_callback, corpus, preregistration,
            calls, raw_receipts, provisional_projections,
            final_projections, trigger_receipts, failures,
        )

    escalations = sorted(
        (
            key,
            trigger,
        )
        for key, trigger in trigger_receipts.items()
        if trigger["triggered"]
    )
    for key, trigger in escalations:
        replication_id, arm_id, case_id = key.split(":", 2)
        canonical_item = next(
            value for value in corpus["public_surface"]["items"]
            if value["case_id"] == case_id
        )
        item = _replication_surface(
            canonical_item,
            replication_id=replication_id,
            corpus_hash=corpus["artifact_hash"],
        )
        route_id = trigger["route_id"]
        task = _generation_task(
            item=item,
            replication_id=replication_id,
            route_id=route_id,
            refs=refs,
            adapter=adapter,
            stage="LAZY_SPECIALIZED_WORKER",
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=replication_id,
            arm_id=arm_id,
            case_id=case_id,
            stage="LAZY_SPECIALIZED_WORKER",
            route_id=route_id,
            task=task,
            envelope=envelope,
        )
        calls.append(call)
        raw_key = (
            f"{replication_id}:{arm_id}:LAZY_SPECIALIZED_WORKER:"
            f"{case_id}"
        )
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            raw = envelope.normalized_result
            raw_receipts[raw_key] = raw
            final_projections[key] = project_frontier_receipt(
                raw_receipt=raw,
                item=item,
                arm_id="A1_ONTOLOGY",
                evidence_refs=refs,
            )
        _checkpoint(
            checkpoint_callback, corpus, preregistration,
            calls, raw_receipts, provisional_projections,
            final_projections, trigger_receipts, failures,
        )

    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "replication_ids": list(REPLICATION_IDS),
        "task_calls": calls,
        "raw_receipts": raw_receipts,
        "provisional_projections": provisional_projections,
        "final_projections": final_projections,
        "trigger_receipts": trigger_receipts,
        "failures": failures,
        "raw_receipts_preserved_before_projection": True,
        "private_truth_exposed": False,
        "trigger_rate_changes_acceptance_gate": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_lazy_metacognition_experiment(
    *, corpus, preregistration, run
):
    validate_lazy_metacognition_holdout(corpus)
    _validate_preregistration(preregistration, corpus)
    _validate_run(run, corpus, preregistration)
    ledgers = {}
    case_deltas = {}
    replication_metrics = {}
    for replication_id in REPLICATION_IDS:
        scoring_run = _scoring_run(run, replication_id=replication_id)
        ledger = build_realized_cbit_ledger(
            corpus=corpus,
            run=scoring_run,
        )
        ledgers[replication_id] = ledger
        totals = defaultdict(float)
        for entry in ledger["entries"]:
            totals[(entry["case_id"], entry["arm_id"])] += entry[
                "realized_effective_cbit"
            ]
        deltas = {
            item["case_id"]: round(
                totals[(item["case_id"], "A2_LAZY")]
                - totals[(item["case_id"], "A1_BASELINE")],
                6,
            )
            for item in corpus["public_surface"]["items"]
        }
        case_deltas[replication_id] = deltas
        replication_metrics[replication_id] = {
            "arm_cbit_per_case": {
                arm: ledger["arm_metrics"][arm][
                    "mean_effective_cbit_per_case"
                ]
                for arm in ARM_IDS
            },
            "arm_tokens": {
                arm: ledger["arm_metrics"][arm]["total_tokens"]
                for arm in ARM_IDS
            },
            "contrast": _metrics(list(deltas.values())),
        }

    pooled = [
        value
        for replication in case_deltas.values()
        for value in replication.values()
    ]
    pooled_metrics = _metrics(pooled)
    majority_positive_case_rate = round(
        sum(
            sum(
                case_deltas[replication_id][case_id] > 0
                for replication_id in REPLICATION_IDS
            ) >= 2
            for case_id in case_deltas[REPLICATION_IDS[0]]
        )
        / corpus["case_count"],
        6,
    )
    positive_replications = sum(
        value["contrast"]["mean"] > 0
        for value in replication_metrics.values()
    )
    relation_reproducibility = {
        arm_id: _relation_reproducibility(
            {"formal_projections": run["final_projections"]},
            arm_id=arm_id,
            corpus=corpus,
        )
        for arm_id in ARM_IDS
    }
    runtime_metrics = _runtime_metrics(run, corpus)
    trigger_metrics = _trigger_metrics(run, case_deltas)
    physical_total_tokens = sum(
        _call_tokens(value) for value in run["task_calls"]
    )
    gate = preregistration["success_gate"]
    conditions = {
        "minimum_provider_completion_per_required_stage": all(
            value >= gate["minimum_provider_completion_per_required_stage"]
            for value in runtime_metrics[
                "provider_completion_per_required_stage"
            ].values()
        ),
        "minimum_trigger_contract_coverage": (
            runtime_metrics["trigger_contract_coverage"]
            >= gate["minimum_trigger_contract_coverage"]
        ),
        "minimum_trigger_execution_coverage": (
            runtime_metrics["trigger_execution_coverage"]
            >= gate["minimum_trigger_execution_coverage"]
        ),
        "minimum_nonblock_coverage_per_arm": all(
            value >= gate["minimum_nonblock_coverage_per_arm"]
            for value in runtime_metrics[
                "final_nonblock_coverage_per_arm"
            ].values()
        ),
        "minimum_exact_three_coverage_per_arm": all(
            value >= gate["minimum_exact_three_coverage_per_arm"]
            for value in runtime_metrics[
                "final_exact_three_coverage_per_arm"
            ].values()
        ),
        "minimum_mean_gain": (
            pooled_metrics["mean"] >= gate["minimum_mean_gain"]
        ),
        "minimum_median_gain": (
            pooled_metrics["median"] >= gate["minimum_median_gain"]
        ),
        "minimum_win_rate": (
            pooled_metrics["win_rate"] >= gate["minimum_win_rate"]
        ),
        "minimum_positive_replications": (
            positive_replications >= gate["minimum_positive_replications"]
        ),
        "minimum_majority_positive_case_rate": (
            majority_positive_case_rate
            >= gate["minimum_majority_positive_case_rate"]
        ),
        "maximum_severe_loss_rate": (
            pooled_metrics["severe_loss_rate"]
            <= gate["maximum_severe_loss_rate"]
        ),
        "minimum_relation_jaccard_relative_to_baseline": (
            relation_reproducibility["A2_LAZY"][
                "mean_pairwise_relation_jaccard"
            ]
            - relation_reproducibility["A1_BASELINE"][
                "mean_pairwise_relation_jaccard"
            ]
            >= gate["minimum_relation_jaccard_relative_to_baseline"]
        ),
        "hard_runaway_total_tokens": (
            physical_total_tokens <= gate["hard_runaway_total_tokens"]
        ),
        "authority_boundary_preserved": all(
            run.get(key) is False
            for key in (
                "selection_authority",
                "retention_authority",
                "production_authority",
            )
        ),
    }
    passed = all(conditions.values())
    decision = (
        "PASS_LAZY_METACOGNITION"
        if passed
        else "REJECT_LAZY_METACOGNITION"
    )
    state = (
        "LAZY_METACOGNITION_PASSED_READY_EXTERNAL_PANEL"
        if passed
        else "LAZY_METACOGNITION_REJECTED_STOP"
    )
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "replication_ledgers": ledgers,
        "case_deltas": case_deltas,
        "replication_metrics": replication_metrics,
        "pooled_contrast_metrics": pooled_metrics,
        "majority_positive_case_rate": majority_positive_case_rate,
        "positive_replication_count": positive_replications,
        "runtime_metrics": runtime_metrics,
        "trigger_metrics": trigger_metrics,
        "relation_reproducibility": relation_reproducibility,
        "physical_total_tokens": physical_total_tokens,
        "soft_cost_warning": (
            physical_total_tokens
            > preregistration["cost_policy"]["soft_expected_total_tokens"]
        ),
        "conditions": conditions,
        "lazy_metacognition_gate": "PASS" if passed else "REJECT",
        "decision": decision,
        "external_semantic_panel_authorized": passed,
        "core_integration_authorized": False,
        "candidate_state": state,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _base_task(*, item, replication_id, arm_id, refs, adapter):
    lazy = arm_id == "A2_LAZY"
    if lazy:
        objective = (
            "Build a compact object census and return exactly three strongest "
            "evidence-bound, distinct, falsifiable problem candidates. Then "
            "emit one compact escalation trigger. Escalate only when a "
            "specific specialized route has positive expected net Cbit after "
            "coordination and token cost; otherwise keep A1_ONTOLOGY. Do not "
            "perform a full four-route comparison."
        )
        schema = _lazy_schema(item=item, refs=refs)
        stage = "ONTOLOGY_WITH_LAZY_TRIGGER"
    else:
        objective = (
            "Build a compact object census and return exactly three strongest "
            "evidence-bound, distinct, falsifiable problem candidates."
        )
        schema = exact_three_schema(
            item=item,
            arm_id="A1_ONTOLOGY",
            refs=refs,
        )
        stage = "ONTOLOGY_BASELINE"
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-{arm_id}-"
            f"{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=objective,
        inputs={
            "stage": stage,
            "replication_id": replication_id,
            "arm_id": arm_id,
            "receipt_arm_id": "A1_ONTOLOGY",
            "public_case": item,
            "available_specialized_routes": list(SPECIALIZED_ROUTE_IDS),
            "private_outcome_available": False,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=schema,
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _lazy_schema(*, item, refs):
    schema = copy.deepcopy(exact_three_schema(
        item=item,
        arm_id="A1_ONTOLOGY",
        refs=refs,
    ))
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    schema["required"].append("escalation_trigger")
    schema["properties"]["escalation_trigger"] = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "triggered",
            "route_id",
            "uncertainty_state",
            "expected_net_gain_band",
            "anti_additive_risks",
            "evidence_span_ids",
            "trigger_reason",
            "stop_condition",
        ],
        "properties": {
            "triggered": {"type": "boolean"},
            "route_id": {
                "type": "string",
                "enum": list(ROUTE_IDS),
            },
            "uncertainty_state": {
                "type": "string",
                "enum": list(UNCERTAINTY_STATES),
            },
            "expected_net_gain_band": {
                "type": "string",
                "enum": list(GAIN_BANDS),
            },
            "anti_additive_risks": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "enum": list(ANTI_ADDITIVE_RISKS),
                },
            },
            "evidence_span_ids": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {"type": "string", "enum": span_ids},
            },
            "trigger_reason": {"type": "string"},
            "stop_condition": {"type": "string"},
        },
    }
    return schema


def _trigger_failures(raw, *, item):
    trigger = raw.get("escalation_trigger")
    if not isinstance(trigger, dict):
        return ["ESCALATION_TRIGGER_MISSING"]
    failures = []
    triggered = trigger.get("triggered")
    route_id = trigger.get("route_id")
    gain_band = trigger.get("expected_net_gain_band")
    uncertainty = trigger.get("uncertainty_state")
    if triggered is False and (
        route_id != "A1_ONTOLOGY"
        or gain_band not in ("NEGATIVE", "NEUTRAL")
    ):
        failures.append("NO_TRIGGER_REQUIRES_A1_NONPOSITIVE_GAIN")
    if triggered is True and (
        route_id not in SPECIALIZED_ROUTE_IDS
        or gain_band not in ("POSITIVE", "HIGH_POSITIVE")
        or uncertainty not in ("MEDIUM", "HIGH")
    ):
        failures.append("TRIGGER_REQUIRES_SPECIALIZED_POSITIVE_GAIN")
    if not isinstance(triggered, bool):
        failures.append("TRIGGERED_NOT_BOOLEAN")
    allowed_spans = {
        value["span_id"] for value in item["evidence_spans"]
    }
    spans = trigger.get("evidence_span_ids")
    if (
        not isinstance(spans, list)
        or not spans
        or any(value not in allowed_spans for value in spans)
    ):
        failures.append("TRIGGER_EVIDENCE_SCOPE_INVALID")
    return failures


def _scoring_run(run, *, replication_id):
    task_calls = []
    projections = {}
    case_ids = sorted(
        key.rsplit(":", 1)[-1]
        for key in run["final_projections"]
        if key.startswith(f"{replication_id}:A1_BASELINE:")
    )
    for case_id in case_ids:
        baseline = _find_call(
            run,
            replication_id=replication_id,
            arm_id="A1_BASELINE",
            case_id=case_id,
            stage="BASELINE",
        )
        if baseline is not None:
            task_calls.append({
                "arm_id": "A1_BASELINE",
                "case_id": case_id,
                "invocation_receipt": baseline["invocation_receipt"],
            })
        lazy_base = _find_call(
            run,
            replication_id=replication_id,
            arm_id="A2_LAZY",
            case_id=case_id,
            stage="LAZY_BASE",
        )
        worker = _find_call(
            run,
            replication_id=replication_id,
            arm_id="A2_LAZY",
            case_id=case_id,
            stage="LAZY_SPECIALIZED_WORKER",
        )
        path_calls = [
            value for value in (lazy_base, worker)
            if value is not None
        ]
        if path_calls:
            task_calls.append({
                "arm_id": "A2_LAZY",
                "case_id": case_id,
                "invocation_receipt": {
                    "token_usage": _combined_usage(path_calls),
                    "derived_cost_receipt": True,
                    "source_call_hashes": [
                        value["call_hash"] for value in path_calls
                    ],
                },
            })
        for arm_id in ARM_IDS:
            source = f"{replication_id}:{arm_id}:{case_id}"
            if source in run["final_projections"]:
                projections[f"{arm_id}:{case_id}"] = run[
                    "final_projections"
                ][source]
    commitment = {
        "task_calls": task_calls,
        "projections": projections,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def _runtime_metrics(run, corpus):
    expected = corpus["case_count"] * len(REPLICATION_IDS)
    base_stages = ("BASELINE", "LAZY_BASE")
    completion = {}
    for stage in base_stages:
        calls = [
            value for value in run["task_calls"]
            if value["stage"] == stage
        ]
        completion[stage] = round(
            sum(value["status"] == "COMPLETED" for value in calls)
            / expected,
            6,
        )
    triggered = [
        value for value in run["trigger_receipts"].values()
        if value["triggered"]
    ]
    workers = [
        value for value in run["task_calls"]
        if value["stage"] == "LAZY_SPECIALIZED_WORKER"
    ]
    if triggered:
        completion["LAZY_SPECIALIZED_WORKER"] = round(
            sum(value["status"] == "COMPLETED" for value in workers)
            / len(triggered),
            6,
        )
        execution_coverage = round(
            sum(
                key in run["final_projections"]
                for key, value in run["trigger_receipts"].items()
                if value["triggered"]
            )
            / len(triggered),
            6,
        )
    else:
        execution_coverage = 1.0
    nonblock = {}
    exact = {}
    for arm_id in ARM_IDS:
        values = [
            value
            for key, value in run["final_projections"].items()
            if f":{arm_id}:" in key
        ]
        nonblock[arm_id] = round(
            sum(value["receipt_state"] != "BLOCK" for value in values)
            / expected,
            6,
        )
        exact[arm_id] = round(
            sum(len(value["eligible_candidate_ids"]) == 3 for value in values)
            / expected,
            6,
        )
    return {
        "provider_completion_per_required_stage": completion,
        "trigger_contract_coverage": round(
            len(run["trigger_receipts"]) / expected,
            6,
        ),
        "trigger_execution_coverage": execution_coverage,
        "final_nonblock_coverage_per_arm": nonblock,
        "final_exact_three_coverage_per_arm": exact,
        "failure_count": len(run["failures"]),
    }


def _trigger_metrics(run, case_deltas):
    route_distribution = Counter()
    gain_distribution = Counter()
    uncertainty_distribution = Counter()
    risk_distribution = Counter()
    triggered_deltas = []
    untriggered_deltas = []
    for key, trigger in run["trigger_receipts"].items():
        replication_id, _arm_id, case_id = key.split(":", 2)
        route_distribution[trigger["route_id"]] += 1
        gain_distribution[trigger["expected_net_gain_band"]] += 1
        uncertainty_distribution[trigger["uncertainty_state"]] += 1
        for risk in trigger["anti_additive_risks"]:
            risk_distribution[risk] += 1
        target = (
            triggered_deltas if trigger["triggered"]
            else untriggered_deltas
        )
        target.append(case_deltas[replication_id][case_id])
    total = len(run["trigger_receipts"])
    triggered_count = len(triggered_deltas)
    return {
        "trigger_count": triggered_count,
        "trigger_rate": round(
            triggered_count / total if total else 0.0,
            6,
        ),
        "route_distribution": dict(route_distribution),
        "gain_band_distribution": dict(gain_distribution),
        "uncertainty_distribution": dict(uncertainty_distribution),
        "anti_additive_risk_distribution": dict(risk_distribution),
        "triggered_contrast": (
            _metrics(triggered_deltas) if triggered_deltas else None
        ),
        "untriggered_contrast": (
            _metrics(untriggered_deltas) if untriggered_deltas else None
        ),
        "triggered_win_precision": round(
            sum(value > 0 for value in triggered_deltas)
            / triggered_count
            if triggered_count
            else 0.0,
            6,
        ),
    }


def _call(
    *,
    replication_id,
    arm_id,
    case_id,
    stage,
    route_id,
    task,
    envelope,
):
    commitment = {
        "replication_id": replication_id,
        "arm_id": arm_id,
        "case_id": case_id,
        "stage": stage,
        "route_id": route_id,
        "status": envelope.status,
        "task_contract_hash": task.contract_hash(),
        "private_truth_exposed": False,
        "invocation_receipt": envelope.invocation_receipt.as_dict(),
    }
    return {**commitment, "call_hash": hash_payload(commitment)}


def _provider_failure(call):
    return {
        "replication_id": call["replication_id"],
        "arm_id": call["arm_id"],
        "case_id": call["case_id"],
        "stage": call["stage"],
        "route_id": call["route_id"],
        "status": call["status"],
        "invocation_receipt": call["invocation_receipt"],
    }


def _find_call(
    run, *, replication_id, arm_id, case_id, stage
):
    return next(
        (
            value for value in run["task_calls"]
            if value["replication_id"] == replication_id
            and value["arm_id"] == arm_id
            and value["case_id"] == case_id
            and value["stage"] == stage
        ),
        None,
    )


def _validate_preregistration(preregistration, corpus):
    commitment = {
        key: value
        for key, value in preregistration.items()
        if key != "artifact_hash"
    }
    if (
        preregistration.get("artifact_hash") != hash_payload(commitment)
        or preregistration.get("source_corpus_hash")
        != corpus["artifact_hash"]
    ):
        raise ValueError("lazy_metacognition_preregistration_invalid")


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
        raise ValueError("lazy_metacognition_run_invalid")


def _checkpoint(
    callback,
    corpus,
    preregistration,
    calls,
    raw_receipts,
    provisional_projections,
    final_projections,
    trigger_receipts,
    failures,
):
    if callback is None:
        return
    commitment = {
        "progress_version": "lazy_metacognition_progress_v0_32",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "completed_task_count": len(calls),
        "task_calls": list(calls),
        "raw_receipts": dict(raw_receipts),
        "provisional_projections": dict(provisional_projections),
        "final_projections": dict(final_projections),
        "trigger_receipts": dict(trigger_receipts),
        "failures": list(failures),
        "original_receipts_preserved": True,
        "resume_authority": False,
    }
    callback({
        **commitment,
        "artifact_hash": hash_payload(commitment),
    })
