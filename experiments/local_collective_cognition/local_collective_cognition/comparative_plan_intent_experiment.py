"""Single-call comparative plan-intent experiment v0.31."""

from __future__ import annotations

import copy
import math
from collections import Counter, defaultdict

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .collaborative_stability_experiment import exact_three_schema
from .comparative_plan_intent_holdout import (
    REPLICATION_IDS,
    validate_comparative_plan_intent_holdout,
)
from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_experiment import TASK_KIND
from .frontier_partial_admission import project_frontier_receipt
from .provider_telemetry import hash_payload
from .selective_role_routing_experiment import (
    ROUTE_IDS,
    _call_tokens,
    _metrics,
    _relation_reproducibility,
    _replication_surface,
)


RUNTIME_VERSION = "comparative_plan_intent_experiment_v0_31"
ARM_IDS = ("A1_BASELINE", "A2_PLAN_INTENT")
BANDS = ("NEGATIVE", "NEUTRAL", "POSITIVE", "HIGH_POSITIVE")
RISKS = (
    "REDUNDANT_WITH_DIRECT_SYNTHESIS", "WEAK_EVIDENCE_BINDING",
    "COORDINATION_OR_TOKEN_FRICTION", "OBJECT_MISMATCH",
    "NEGATIVE_TRANSFER", "NONE",
)


def build_plan_intent_preregistration(
    *, corpus, prior_analysis, prior_closure, prior_posthoc
):
    validate_comparative_plan_intent_holdout(corpus)
    if (
        prior_closure.get("candidate_state")
        != "SELECTIVE_ROLE_ROUTING_REJECTED_STOP"
        or prior_analysis.get("decision")
        != "REJECT_SELECTIVE_ROLE_ROUTING"
        or prior_posthoc.get("status")
        != "POSTHOC_DECOMPOSITION_NOT_FROZEN_GATE"
        or prior_posthoc.get("shadow_oracle_mean_gain_vs_baseline", 0)
        <= 0
    ):
        raise ValueError("comparative_plan_intent_prior_invalid")
    prior_total = int(prior_analysis["physical_total_tokens"])
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
        "frozen_hypothesis": (
            "A single Provider call that compares all route utilities, permits "
            "no escalation, and binds generated candidates to the selected "
            "plan intent can improve majority-stable net Cbit without a "
            "separate router-call penalty."
        ),
        "route_ids": list(ROUTE_IDS),
        "replication_ids": list(REPLICATION_IDS),
        "candidate_count_per_receipt": 3,
        "primary_contrast": "A2_PLAN_INTENT_MINUS_A1_BASELINE",
        "success_gate": {
            "minimum_provider_completion_per_arm": 0.95,
            "minimum_plan_consistency_coverage": 0.9,
            "minimum_nonblock_coverage_per_arm": 0.9,
            "minimum_exact_three_coverage_per_arm": 0.9,
            "minimum_mean_gain": 0.15,
            "minimum_median_gain": 0.0,
            "minimum_win_rate": 0.55,
            "minimum_positive_replications": 2,
            "minimum_majority_positive_case_rate": 0.5,
            "maximum_severe_loss_rate": 0.2,
            "minimum_relation_jaccard_relative_to_baseline": -0.05,
            "hard_runaway_total_tokens": math.ceil(prior_total * 0.75),
        },
        "cost_policy": {
            "one_provider_call_per_arm_cell": True,
            "token_cost_already_subtracted_inside_realized_cbit": True,
            "cbit_per_token_is_diagnostic_not_acceptance_gate": True,
            "soft_expected_total_tokens": math.ceil(prior_total * 0.5),
            "hard_runaway_total_tokens": math.ceil(prior_total * 0.75),
        },
        "fresh_labels_available_during_inference": False,
        "external_semantic_panel_required": True,
        "selection_authority": False, "retention_write_allowed": False,
        "baseline_write_allowed": False, "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_plan_intent_experiment(
    *, corpus, preregistration, adapter, checkpoint_callback=None
):
    validate_comparative_plan_intent_holdout(corpus)
    _validate_prereg(preregistration, corpus)
    refs = tuple(corpus["evidence_refs"])
    matrix = [
        (replication_id, arm_id, item)
        for replication_id in REPLICATION_IDS
        for arm_id in ARM_IDS
        for item in corpus["public_surface"]["items"]
    ]
    matrix.sort(key=lambda value: hash_payload([
        RUNTIME_VERSION, value[0], value[1], value[2]["case_id"]
    ]))
    calls, raw_receipts, projections, plan_receipts, failures = (
        [], {}, {}, {}, []
    )
    for replication_id, arm_id, canonical_item in matrix:
        item = _replication_surface(
            canonical_item, replication_id=replication_id,
            corpus_hash=corpus["artifact_hash"],
        )
        task = _task(item, replication_id, arm_id, refs, adapter)
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(replication_id, arm_id, item["case_id"], task, envelope)
        calls.append(call)
        key = f"{replication_id}:{arm_id}:{item['case_id']}"
        if envelope.status != "COMPLETED":
            failures.append({**call, "failure_stage": "PROVIDER"})
        else:
            raw = envelope.normalized_result
            raw_receipts[key] = raw
            if arm_id == "A2_PLAN_INTENT":
                plan_failures = _plan_failures(raw)
                if plan_failures:
                    failures.append({
                        "replication_id": replication_id,
                        "arm_id": arm_id, "case_id": item["case_id"],
                        "failure_stage": "PLAN_CONSISTENCY",
                        "failures": plan_failures,
                        "raw_receipt_hash": hash_payload(raw),
                    })
                    _checkpoint(
                        checkpoint_callback, corpus, preregistration,
                        calls, raw_receipts, projections, plan_receipts,
                        failures,
                    )
                    continue
                plan_receipts[key] = raw["plan_intent"]
            projections[key] = project_frontier_receipt(
                raw_receipt=raw, item=item, arm_id="A1_ONTOLOGY",
                evidence_refs=refs,
            )
        _checkpoint(
            checkpoint_callback, corpus, preregistration, calls,
            raw_receipts, projections, plan_receipts, failures,
        )
    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls, "raw_receipts": raw_receipts,
        "projections": projections, "plan_receipts": plan_receipts,
        "failures": failures,
        "raw_receipts_preserved_before_projection": True,
        "one_provider_call_per_arm_cell": True,
        "private_truth_exposed": False,
        "selection_authority": False, "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_plan_intent_experiment(*, corpus, preregistration, run):
    validate_comparative_plan_intent_holdout(corpus)
    _validate_prereg(preregistration, corpus)
    _validate_run(run, corpus, preregistration)
    ledgers, case_deltas, replication_metrics = {}, {}, {}
    for replication_id in REPLICATION_IDS:
        calls = [
            {"arm_id": value["arm_id"], "case_id": value["case_id"],
             "invocation_receipt": value["invocation_receipt"]}
            for value in run["task_calls"]
            if value["replication_id"] == replication_id
        ]
        projections = {
            key.split(":", 1)[1]: value
            for key, value in run["projections"].items()
            if key.startswith(replication_id + ":")
        }
        sub = {"task_calls": calls, "projections": projections}
        sub["run_hash"] = hash_payload(sub)
        ledger = build_realized_cbit_ledger(corpus=corpus, run=sub)
        ledgers[replication_id] = ledger
        totals = defaultdict(float)
        for entry in ledger["entries"]:
            totals[(entry["case_id"], entry["arm_id"])] += entry[
                "realized_effective_cbit"
            ]
        deltas = {
            item["case_id"]: round(
                totals[(item["case_id"], "A2_PLAN_INTENT")]
                - totals[(item["case_id"], "A1_BASELINE")], 6
            )
            for item in corpus["public_surface"]["items"]
        }
        case_deltas[replication_id] = deltas
        replication_metrics[replication_id] = {
            "arm_cbit_per_case": {
                arm: ledger["arm_metrics"][arm][
                    "mean_effective_cbit_per_case"
                ] for arm in ARM_IDS
            },
            "arm_tokens": {
                arm: ledger["arm_metrics"][arm]["total_tokens"]
                for arm in ARM_IDS
            },
            "contrast": _metrics(list(deltas.values())),
        }
    pooled = [
        value for values in case_deltas.values()
        for value in values.values()
    ]
    metrics = _metrics(pooled)
    majority = round(sum(
        sum(case_deltas[rep][case] > 0 for rep in REPLICATION_IDS) >= 2
        for case in case_deltas[REPLICATION_IDS[0]]
    ) / corpus["case_count"], 6)
    positive_reps = sum(
        value["contrast"]["mean"] > 0
        for value in replication_metrics.values()
    )
    runtime = _runtime_metrics(run, corpus)
    relation = {
        arm: _relation_reproducibility(
            {"formal_projections": run["projections"]},
            arm_id=arm, corpus=corpus
        ) for arm in ARM_IDS
    }
    plan_metrics = _plan_metrics(run)
    total_tokens = sum(_call_tokens(value) for value in run["task_calls"])
    gate = preregistration["success_gate"]
    conditions = {
        "minimum_provider_completion_per_arm": all(
            value >= gate["minimum_provider_completion_per_arm"]
            for value in runtime["provider_completion_per_arm"].values()
        ),
        "minimum_plan_consistency_coverage": (
            runtime["plan_consistency_coverage"]
            >= gate["minimum_plan_consistency_coverage"]
        ),
        "minimum_nonblock_coverage_per_arm": all(
            value >= gate["minimum_nonblock_coverage_per_arm"]
            for value in runtime["nonblock_coverage_per_arm"].values()
        ),
        "minimum_exact_three_coverage_per_arm": all(
            value >= gate["minimum_exact_three_coverage_per_arm"]
            for value in runtime["exact_three_coverage_per_arm"].values()
        ),
        "minimum_mean_gain": metrics["mean"] >= gate["minimum_mean_gain"],
        "minimum_median_gain": (
            metrics["median"] >= gate["minimum_median_gain"]
        ),
        "minimum_win_rate": metrics["win_rate"] >= gate["minimum_win_rate"],
        "minimum_positive_replications": (
            positive_reps >= gate["minimum_positive_replications"]
        ),
        "minimum_majority_positive_case_rate": (
            majority >= gate["minimum_majority_positive_case_rate"]
        ),
        "maximum_severe_loss_rate": (
            metrics["severe_loss_rate"] <= gate["maximum_severe_loss_rate"]
        ),
        "minimum_relation_jaccard_relative_to_baseline": (
            relation["A2_PLAN_INTENT"]["mean_pairwise_relation_jaccard"]
            - relation["A1_BASELINE"]["mean_pairwise_relation_jaccard"]
            >= gate["minimum_relation_jaccard_relative_to_baseline"]
        ),
        "hard_runaway_total_tokens": (
            total_tokens <= gate["hard_runaway_total_tokens"]
        ),
        "one_call_per_arm_cell": len(run["task_calls"]) == (
            corpus["case_count"] * len(REPLICATION_IDS) * 2
        ),
        "authority_boundary_preserved": all(
            run.get(key) is False for key in (
                "selection_authority", "retention_authority",
                "production_authority",
            )
        ),
    }
    passed = all(conditions.values())
    decision = (
        "PASS_COMPARATIVE_PLAN_INTENT"
        if passed else "REJECT_COMPARATIVE_PLAN_INTENT"
    )
    state = (
        "COMPARATIVE_PLAN_INTENT_PASSED_READY_EXTERNAL_PANEL"
        if passed else "COMPARATIVE_PLAN_INTENT_REJECTED_STOP"
    )
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "replication_ledgers": ledgers,
        "case_deltas": case_deltas,
        "replication_metrics": replication_metrics,
        "pooled_contrast_metrics": metrics,
        "majority_positive_case_rate": majority,
        "positive_replication_count": positive_reps,
        "runtime_metrics": runtime,
        "relation_reproducibility": relation,
        "plan_metrics": plan_metrics,
        "total_tokens": total_tokens,
        "soft_cost_warning": total_tokens > preregistration[
            "cost_policy"
        ]["soft_expected_total_tokens"],
        "conditions": conditions,
        "plan_intent_gate": "PASS" if passed else "REJECT",
        "decision": decision,
        "external_semantic_panel_authorized": passed,
        "core_integration_authorized": False,
        "candidate_state": state,
        "selection_authority": False, "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _task(item, replication_id, arm_id, refs, adapter):
    if arm_id == "A1_BASELINE":
        objective = (
            "Build a compact object census and return exactly three strongest "
            "evidence-bound, distinct, falsifiable problem candidates."
        )
        schema = exact_three_schema(
            item=item, arm_id="A1_ONTOLOGY", refs=refs
        )
        stage = "ONTOLOGY_BASELINE"
    else:
        objective = (
            "In one receipt, compare all four cognitive routes before "
            "candidate generation. Estimate net Cbit after friction and "
            "anti-additive risk. Select A1_ONTOLOGY as NO_ESCALATION whenever "
            "specialization lacks a clear advantage. Then generate exactly "
            "three distinct candidates bound to the selected route."
        )
        schema = _plan_schema(item=item, refs=refs)
        stage = "COMPARATIVE_PLAN_INTENT_AND_EXECUTION"
    return ProviderCognitiveTask(
        task_id=f"{RUNTIME_VERSION}-{replication_id}-{arm_id}-{item['case_id']}",
        task_kind=TASK_KIND, objective=objective,
        inputs={
            "stage": stage, "replication_id": replication_id,
            "arm_id": arm_id, "public_case": item,
            "available_routes": list(ROUTE_IDS),
            "private_outcome_available": False,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs), expected_schema=schema,
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _plan_schema(*, item, refs):
    schema = copy.deepcopy(exact_three_schema(
        item=item, arm_id="A1_ONTOLOGY", refs=refs
    ))
    candidate = schema["properties"]["problem_candidates"]["items"]
    candidate["required"].append("plan_route_id")
    candidate["properties"]["plan_route_id"] = {
        "type": "string", "enum": list(ROUTE_IDS)
    }
    assessment = {
        "type": "object", "additionalProperties": False,
        "required": [
            "route_id", "expected_net_cbit_band", "fit_reason",
            "anti_additive_risks", "confidence",
        ],
        "properties": {
            "route_id": {"type": "string", "enum": list(ROUTE_IDS)},
            "expected_net_cbit_band": {
                "type": "string", "enum": list(BANDS)
            },
            "fit_reason": {"type": "string"},
            "anti_additive_risks": {
                "type": "array", "uniqueItems": True,
                "items": {"type": "string", "enum": list(RISKS)},
            },
            "confidence": {
                "type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]
            },
        },
    }
    schema["required"].append("plan_intent")
    schema["properties"]["plan_intent"] = {
        "type": "object", "additionalProperties": False,
        "required": [
            "route_assessments", "selected_route_id",
            "execution_mode", "selection_margin", "global_stop_condition",
        ],
        "properties": {
            "route_assessments": {
                "type": "array", "minItems": 4, "maxItems": 4,
                "items": assessment,
            },
            "selected_route_id": {
                "type": "string", "enum": list(ROUTE_IDS)
            },
            "execution_mode": {
                "type": "string",
                "enum": ["NO_ESCALATION", "SPECIALIZED_ROUTE"],
            },
            "selection_margin": {
                "type": "string",
                "enum": ["INSUFFICIENT", "SMALL", "CLEAR"],
            },
            "global_stop_condition": {"type": "string"},
        },
    }
    return schema


def _plan_failures(raw):
    plan = raw.get("plan_intent")
    if not isinstance(plan, dict):
        return ["PLAN_INTENT_MISSING"]
    failures = []
    assessments = plan.get("route_assessments")
    if not isinstance(assessments, list) or {
        value.get("route_id") for value in assessments
        if isinstance(value, dict)
    } != set(ROUTE_IDS):
        failures.append("ROUTE_ASSESSMENTS_INCOMPLETE")
        return failures
    selected = plan.get("selected_route_id")
    ranks = {value: index for index, value in enumerate(BANDS)}
    scores = {
        value["route_id"]: ranks[value["expected_net_cbit_band"]]
        for value in assessments
    }
    if selected not in scores or scores[selected] != max(scores.values()):
        failures.append("SELECTED_ROUTE_NOT_MAX_UTILITY")
    if (
        selected == "A1_ONTOLOGY"
        and plan.get("execution_mode") != "NO_ESCALATION"
    ) or (
        selected != "A1_ONTOLOGY"
        and plan.get("execution_mode") != "SPECIALIZED_ROUTE"
    ):
        failures.append("EXECUTION_MODE_MISMATCH")
    if (
        plan.get("selection_margin") == "INSUFFICIENT"
        and selected != "A1_ONTOLOGY"
    ):
        failures.append("INSUFFICIENT_MARGIN_MUST_NOT_ESCALATE")
    candidates = raw.get("problem_candidates")
    if not isinstance(candidates, list) or any(
        value.get("plan_route_id") != selected
        for value in candidates if isinstance(value, dict)
    ):
        failures.append("CANDIDATE_PLAN_ROUTE_MISMATCH")
    return failures


def _call(replication_id, arm_id, case_id, task, envelope):
    commitment = {
        "replication_id": replication_id, "arm_id": arm_id,
        "case_id": case_id, "status": envelope.status,
        "task_contract_hash": task.contract_hash(),
        "private_truth_exposed": False,
        "invocation_receipt": envelope.invocation_receipt.as_dict(),
    }
    return {**commitment, "call_hash": hash_payload(commitment)}


def _runtime_metrics(run, corpus):
    expected = corpus["case_count"] * len(REPLICATION_IDS)
    completion, nonblock, exact = {}, {}, {}
    for arm in ARM_IDS:
        calls = [v for v in run["task_calls"] if v["arm_id"] == arm]
        values = [
            v for key, v in run["projections"].items()
            if f":{arm}:" in key
        ]
        completion[arm] = round(
            sum(v["status"] == "COMPLETED" for v in calls) / expected, 6
        )
        nonblock[arm] = round(
            sum(v["receipt_state"] != "BLOCK" for v in values) / expected, 6
        )
        exact[arm] = round(
            sum(len(v["eligible_candidate_ids"]) == 3 for v in values)
            / expected, 6
        )
    return {
        "provider_completion_per_arm": completion,
        "nonblock_coverage_per_arm": nonblock,
        "exact_three_coverage_per_arm": exact,
        "plan_consistency_coverage": round(
            len(run["plan_receipts"]) / expected, 6
        ),
        "failure_count": len(run["failures"]),
    }


def _plan_metrics(run):
    routes = Counter()
    modes = Counter()
    margins = Counter()
    bands = Counter()
    risks = Counter()
    for plan in run["plan_receipts"].values():
        routes[plan["selected_route_id"]] += 1
        modes[plan["execution_mode"]] += 1
        margins[plan["selection_margin"]] += 1
        for value in plan["route_assessments"]:
            bands[
                f"{value['route_id']}:{value['expected_net_cbit_band']}"
            ] += 1
            for risk in value["anti_additive_risks"]:
                risks[f"{value['route_id']}:{risk}"] += 1
    return {
        "selected_route_distribution": dict(routes),
        "execution_mode_distribution": dict(modes),
        "selection_margin_distribution": dict(margins),
        "route_band_counts": dict(bands),
        "anti_additive_risk_counts": dict(risks),
    }


def _validate_prereg(prereg, corpus):
    commitment = {k: v for k, v in prereg.items() if k != "artifact_hash"}
    if (
        prereg.get("artifact_hash") != hash_payload(commitment)
        or prereg.get("source_corpus_hash") != corpus["artifact_hash"]
    ):
        raise ValueError("plan_intent_preregistration_invalid")


def _validate_run(run, corpus, prereg):
    commitment = {k: v for k, v in run.items() if k != "run_hash"}
    if (
        run.get("run_hash") != hash_payload(commitment)
        or run.get("source_corpus_hash") != corpus["artifact_hash"]
        or run.get("source_preregistration_hash") != prereg["artifact_hash"]
    ):
        raise ValueError("plan_intent_run_invalid")


def _checkpoint(callback, corpus, prereg, calls, raw, projections, plans, failures):
    if callback is None:
        return
    commitment = {
        "progress_version": "comparative_plan_intent_progress_v0_31",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": prereg["artifact_hash"],
        "completed_task_count": len(calls), "task_calls": list(calls),
        "raw_receipts": dict(raw), "projections": dict(projections),
        "plan_receipts": dict(plans), "failures": list(failures),
        "original_receipts_preserved": True, "resume_authority": False,
    }
    callback({**commitment, "artifact_hash": hash_payload(commitment)})
