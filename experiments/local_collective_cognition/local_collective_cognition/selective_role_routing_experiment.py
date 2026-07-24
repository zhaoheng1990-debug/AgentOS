"""Provider-backed selective role routing experiment v0.30."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from itertools import combinations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .collaborative_stability_experiment import (
    ROLE_IDS,
    exact_three_schema,
)
from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_experiment import TASK_KIND
from .frontier_partial_admission import project_frontier_receipt
from .provider_telemetry import hash_payload
from .selective_role_routing_holdout import (
    REPLICATION_IDS,
    SHADOW_AUDIT_REPLICATION_ID,
    validate_selective_role_routing_holdout,
)


RUNTIME_VERSION = "selective_role_routing_experiment_v0_30"
ROUTE_IDS = ("A1_ONTOLOGY", *ROLE_IDS)
FORMAL_ARM_IDS = ("A1_BASELINE", "A2_ROUTED")


def build_routing_preregistration(
    *, corpus, prior_analysis, prior_closure, prior_posthoc
):
    validate_selective_role_routing_holdout(corpus)
    if (
        prior_closure.get("candidate_state")
        != "COLLABORATIVE_STABILITY_REJECTED_STOP"
        or prior_closure.get("collaborative_stability_gate") != "REJECT"
        or prior_closure.get("core_integration_authorized") is not False
        or prior_analysis.get("decision")
        != "REJECT_COLLABORATIVE_STABILIZATION"
        or prior_posthoc.get("status")
        != "POSTHOC_CEILING_NOT_FROZEN_GATE"
        or prior_posthoc.get(
            "pre_execution_role_router_oracle", {}
        ).get("mean", 0) <= 0
        or prior_posthoc.get(
            "pre_execution_role_router_oracle", {}
        ).get("majority_positive_case_count", 0) < 5
    ):
        raise ValueError("selective_role_routing_prior_invalid")
    prior_total = int(prior_analysis["total_tokens"])
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
        "frozen_hypothesis": (
            "A provider-backed structural router can choose one specialized "
            "cognitive path before execution and outperform a single ontology "
            "baseline in majority-stable net realized Cbit after charging both "
            "router and selected-worker tokens."
        ),
        "route_ids": list(ROUTE_IDS),
        "replication_ids": list(REPLICATION_IDS),
        "shadow_audit_replication_id": SHADOW_AUDIT_REPLICATION_ID,
        "candidate_count_per_final_receipt": 3,
        "primary_contrast": "A2_ROUTED_MINUS_A1_BASELINE",
        "cost_policy": {
            "router_and_selected_worker_tokens_charged_to_a2": True,
            "shadow_counterfactual_tokens_excluded_from_deployment_path": True,
            "shadow_tokens_included_in_physical_resource_cap": True,
            "token_cost_already_subtracted_inside_realized_cbit": True,
            "cbit_per_token_is_diagnostic_not_acceptance_gate": True,
            "soft_expected_total_tokens": prior_total,
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.5),
        },
        "success_gate": {
            "minimum_provider_completion_by_formal_stage": 0.95,
            "minimum_shadow_audit_projection_coverage": 0.9,
            "minimum_final_nonblock_coverage_per_arm": 0.9,
            "minimum_exact_three_coverage_per_arm": 0.9,
            "minimum_routed_mean_gain": 0.15,
            "minimum_routed_median_gain": 0.0,
            "minimum_routed_win_rate": 0.55,
            "minimum_positive_routed_replications": 2,
            "minimum_majority_positive_case_rate": 0.5,
            "maximum_routed_severe_loss_rate": 0.2,
            "minimum_routed_relation_jaccard_relative_to_baseline": -0.05,
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.5),
        },
        "fresh_labels_available_during_inference": False,
        "shadow_audit_changes_formal_decision": False,
        "external_semantic_panel_required": True,
        "selection_authority": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_selective_routing_experiment(
    *, corpus, preregistration, adapter, checkpoint_callback=None
):
    validate_selective_role_routing_holdout(corpus)
    _validate_preregistration(preregistration, corpus=corpus)
    refs = tuple(corpus["evidence_refs"])
    calls, raw_receipts, route_receipts = [], {}, {}
    formal_projections, shadow_route_projections = {}, {}
    failures = []
    cells = [
        (replication_id, item)
        for replication_id in REPLICATION_IDS
        for item in corpus["public_surface"]["items"]
    ]
    first_phase = [
        (replication_id, item, stage)
        for replication_id, item in cells
        for stage in ("BASELINE", "ROUTER")
    ]
    first_phase.sort(key=lambda value: hash_payload([
        RUNTIME_VERSION, "FIRST_PHASE", value[0],
        value[1]["case_id"], value[2],
    ]))
    for replication_id, canonical_item, stage in first_phase:
        item = _replication_surface(
            canonical_item, replication_id=replication_id,
            corpus_hash=corpus["artifact_hash"],
        )
        task = (
            _baseline_task(item, replication_id, refs, adapter)
            if stage == "BASELINE"
            else _router_task(item, replication_id, refs, adapter)
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=replication_id,
            case_id=item["case_id"],
            stage=stage,
            route_id=None,
            task=task,
            envelope=envelope,
        )
        calls.append(call)
        key = f"{replication_id}:{stage}:{item['case_id']}"
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            raw = envelope.normalized_result
            raw_receipts[key] = raw
            if stage == "BASELINE":
                formal_projections[
                    f"{replication_id}:A1_BASELINE:{item['case_id']}"
                ] = project_frontier_receipt(
                    raw_receipt=raw,
                    item=item,
                    arm_id="A1_ONTOLOGY",
                    evidence_refs=refs,
                )
            else:
                route_failures = _route_failures(
                    raw, item=item, refs=refs
                )
                if route_failures:
                    failures.append({
                        "replication_id": replication_id,
                        "case_id": item["case_id"],
                        "stage": "ROUTER_VALIDATION",
                        "failures": route_failures,
                        "route_receipt_hash": hash_payload(raw),
                    })
                else:
                    route_receipts[
                        f"{replication_id}:{item['case_id']}"
                    ] = raw
        _checkpoint(
            checkpoint_callback, corpus=corpus,
            preregistration=preregistration, calls=calls,
            raw_receipts=raw_receipts,
            route_receipts=route_receipts,
            formal_projections=formal_projections,
            shadow_route_projections=shadow_route_projections,
            failures=failures,
        )

    routed_cells = sorted(cells, key=lambda value: hash_payload([
        RUNTIME_VERSION, "ROUTED_WORKER", value[0],
        value[1]["case_id"],
    ]))
    for replication_id, canonical_item in routed_cells:
        route = route_receipts.get(
            f"{replication_id}:{canonical_item['case_id']}"
        )
        if route is None:
            continue
        item = _replication_surface(
            canonical_item, replication_id=replication_id,
            corpus_hash=corpus["artifact_hash"],
        )
        route_id = route["route_id"]
        task = _worker_task(
            item, replication_id, route_id, refs, adapter,
            stage="ROUTED_WORKER",
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=replication_id,
            case_id=item["case_id"],
            stage="ROUTED_WORKER",
            route_id=route_id,
            task=task,
            envelope=envelope,
        )
        calls.append(call)
        key = (
            f"{replication_id}:ROUTED_WORKER:{route_id}:"
            f"{item['case_id']}"
        )
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            raw = envelope.normalized_result
            raw_receipts[key] = raw
            projection = project_frontier_receipt(
                raw_receipt=raw,
                item=item,
                arm_id="A1_ONTOLOGY",
                evidence_refs=refs,
            )
            formal_projections[
                f"{replication_id}:A2_ROUTED:{item['case_id']}"
            ] = projection
            if replication_id == SHADOW_AUDIT_REPLICATION_ID:
                shadow_route_projections[
                    f"{replication_id}:{route_id}:{item['case_id']}"
                ] = projection
        _checkpoint(
            checkpoint_callback, corpus=corpus,
            preregistration=preregistration, calls=calls,
            raw_receipts=raw_receipts,
            route_receipts=route_receipts,
            formal_projections=formal_projections,
            shadow_route_projections=shadow_route_projections,
            failures=failures,
        )

    shadow_matrix = [
        (item, route_id)
        for item in corpus["public_surface"]["items"]
        for route_id in ROUTE_IDS
    ]
    shadow_matrix.sort(key=lambda value: hash_payload([
        RUNTIME_VERSION, "SHADOW", value[0]["case_id"], value[1],
    ]))
    for canonical_item, route_id in shadow_matrix:
        shadow_key = (
            f"{SHADOW_AUDIT_REPLICATION_ID}:{route_id}:"
            f"{canonical_item['case_id']}"
        )
        if shadow_key in shadow_route_projections:
            continue
        item = _replication_surface(
            canonical_item,
            replication_id=SHADOW_AUDIT_REPLICATION_ID,
            corpus_hash=corpus["artifact_hash"],
        )
        task = _worker_task(
            item, SHADOW_AUDIT_REPLICATION_ID, route_id,
            refs, adapter, stage="SHADOW_WORKER",
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=SHADOW_AUDIT_REPLICATION_ID,
            case_id=item["case_id"],
            stage="SHADOW_WORKER",
            route_id=route_id,
            task=task,
            envelope=envelope,
        )
        calls.append(call)
        raw_key = (
            f"{SHADOW_AUDIT_REPLICATION_ID}:SHADOW_WORKER:"
            f"{route_id}:{item['case_id']}"
        )
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            raw = envelope.normalized_result
            raw_receipts[raw_key] = raw
            shadow_route_projections[shadow_key] = (
                project_frontier_receipt(
                    raw_receipt=raw,
                    item=item,
                    arm_id="A1_ONTOLOGY",
                    evidence_refs=refs,
                )
            )
        _checkpoint(
            checkpoint_callback, corpus=corpus,
            preregistration=preregistration, calls=calls,
            raw_receipts=raw_receipts,
            route_receipts=route_receipts,
            formal_projections=formal_projections,
            shadow_route_projections=shadow_route_projections,
            failures=failures,
        )

    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "replication_ids": list(REPLICATION_IDS),
        "route_ids": list(ROUTE_IDS),
        "shadow_audit_replication_id": SHADOW_AUDIT_REPLICATION_ID,
        "task_calls": calls,
        "raw_receipts": raw_receipts,
        "route_receipts": route_receipts,
        "formal_projections": formal_projections,
        "shadow_route_projections": shadow_route_projections,
        "failures": failures,
        "raw_receipts_preserved_before_projection": True,
        "private_truth_exposed": False,
        "shadow_audit_changes_formal_decision": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_selective_routing_experiment(
    *, corpus, preregistration, run
):
    validate_selective_role_routing_holdout(corpus)
    _validate_preregistration(preregistration, corpus=corpus)
    _validate_run(run, corpus=corpus, preregistration=preregistration)
    ledgers, case_deltas, replication_metrics = {}, {}, {}
    for replication_id in REPLICATION_IDS:
        scoring_run = _formal_scoring_run(
            run, replication_id=replication_id
        )
        ledger = build_realized_cbit_ledger(
            corpus=corpus, run=scoring_run
        )
        ledgers[replication_id] = ledger
        totals = defaultdict(float)
        for entry in ledger["entries"]:
            totals[(entry["case_id"], entry["arm_id"])] += entry[
                "realized_effective_cbit"
            ]
        deltas = {
            case_id: round(
                totals[(case_id, "A2_ROUTED")]
                - totals[(case_id, "A1_BASELINE")],
                6,
            )
            for case_id in sorted(
                item["case_id"]
                for item in corpus["public_surface"]["items"]
            )
        }
        case_deltas[replication_id] = deltas
        replication_metrics[replication_id] = {
            "a1_cbit_per_case": ledger["arm_metrics"][
                "A1_BASELINE"
            ]["mean_effective_cbit_per_case"],
            "a2_cbit_per_case": ledger["arm_metrics"][
                "A2_ROUTED"
            ]["mean_effective_cbit_per_case"],
            "a1_total_tokens": ledger["arm_metrics"][
                "A1_BASELINE"
            ]["total_tokens"],
            "a2_total_tokens": ledger["arm_metrics"][
                "A2_ROUTED"
            ]["total_tokens"],
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
        ) / corpus["case_count"],
        6,
    )
    positive_replications = sum(
        value["contrast"]["mean"] > 0
        for value in replication_metrics.values()
    )
    relation_reproducibility = {
        arm_id: _relation_reproducibility(
            run, arm_id=arm_id, corpus=corpus
        )
        for arm_id in FORMAL_ARM_IDS
    }
    runtime_metrics = _runtime_metrics(run, corpus=corpus)
    route_distribution = dict(Counter(
        value["route_id"] for value in run["route_receipts"].values()
    ))
    shadow_audit = _shadow_regret_audit(
        corpus=corpus, run=run
    )
    physical_tokens = sum(
        _call_tokens(value) for value in run["task_calls"]
    )
    formal_path_tokens = sum(
        ledger["arm_metrics"][arm_id]["total_tokens"]
        for ledger in ledgers.values()
        for arm_id in FORMAL_ARM_IDS
    )
    gate = preregistration["success_gate"]
    conditions = {
        "minimum_provider_completion_by_formal_stage": all(
            value >= gate[
                "minimum_provider_completion_by_formal_stage"
            ]
            for value in runtime_metrics[
                "provider_completion_by_formal_stage"
            ].values()
        ),
        "minimum_shadow_audit_projection_coverage": (
            runtime_metrics["shadow_audit_projection_coverage"]
            >= gate["minimum_shadow_audit_projection_coverage"]
        ),
        "minimum_final_nonblock_coverage_per_arm": all(
            value >= gate["minimum_final_nonblock_coverage_per_arm"]
            for value in runtime_metrics[
                "final_nonblock_coverage_per_arm"
            ].values()
        ),
        "minimum_exact_three_coverage_per_arm": all(
            value >= gate["minimum_exact_three_coverage_per_arm"]
            for value in runtime_metrics[
                "exact_three_coverage_per_arm"
            ].values()
        ),
        "minimum_routed_mean_gain": (
            pooled_metrics["mean"]
            >= gate["minimum_routed_mean_gain"]
        ),
        "minimum_routed_median_gain": (
            pooled_metrics["median"]
            >= gate["minimum_routed_median_gain"]
        ),
        "minimum_routed_win_rate": (
            pooled_metrics["win_rate"]
            >= gate["minimum_routed_win_rate"]
        ),
        "minimum_positive_routed_replications": (
            positive_replications
            >= gate["minimum_positive_routed_replications"]
        ),
        "minimum_majority_positive_case_rate": (
            majority_positive_case_rate
            >= gate["minimum_majority_positive_case_rate"]
        ),
        "maximum_routed_severe_loss_rate": (
            pooled_metrics["severe_loss_rate"]
            <= gate["maximum_routed_severe_loss_rate"]
        ),
        "minimum_routed_relation_jaccard_relative_to_baseline": (
            relation_reproducibility["A2_ROUTED"][
                "mean_pairwise_relation_jaccard"
            ]
            - relation_reproducibility["A1_BASELINE"][
                "mean_pairwise_relation_jaccard"
            ]
            >= gate[
                "minimum_routed_relation_jaccard_relative_to_baseline"
            ]
        ),
        "hard_runaway_total_tokens": (
            physical_tokens <= gate["hard_runaway_total_tokens"]
        ),
        "formal_path_cost_accounting_complete": (
            formal_path_tokens == _formal_physical_tokens(run)
        ),
        "shadow_tokens_excluded_from_formal_path": all(
            value["stage"] != "SHADOW_WORKER"
            for ledger in ledgers.values()
            for value in ledger.get("task_calls", ())
        ),
        "authority_boundary_preserved": all(
            run.get(value) is False
            for value in (
                "selection_authority", "retention_authority",
                "production_authority",
            )
        ),
    }
    passed = all(conditions.values())
    if passed:
        decision = "PASS_SELECTIVE_ROLE_ROUTING"
        state = "SELECTIVE_ROLE_ROUTING_PASSED_READY_EXTERNAL_PANEL"
    elif physical_tokens > gate["hard_runaway_total_tokens"]:
        decision = "STOP_RESOURCE_RUNAWAY"
        state = "SELECTIVE_ROLE_ROUTING_RESOURCE_STOP"
    else:
        decision = "REJECT_SELECTIVE_ROLE_ROUTING"
        state = "SELECTIVE_ROLE_ROUTING_REJECTED_STOP"
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "replication_ledgers": ledgers,
        "case_deltas": case_deltas,
        "replication_metrics": replication_metrics,
        "pooled_contrast_metrics": pooled_metrics,
        "majority_positive_case_rate": majority_positive_case_rate,
        "positive_replication_count": positive_replications,
        "relation_reproducibility": relation_reproducibility,
        "runtime_metrics": runtime_metrics,
        "route_distribution": route_distribution,
        "shadow_regret_audit": shadow_audit,
        "formal_path_tokens": formal_path_tokens,
        "shadow_audit_tokens": physical_tokens - formal_path_tokens,
        "physical_total_tokens": physical_tokens,
        "soft_expected_total_tokens": preregistration[
            "cost_policy"
        ]["soft_expected_total_tokens"],
        "soft_cost_warning": (
            physical_tokens
            > preregistration["cost_policy"]["soft_expected_total_tokens"]
        ),
        "conditions": conditions,
        "selective_routing_gate": "PASS" if passed else "REJECT",
        "decision": decision,
        "external_semantic_panel_authorized": passed,
        "cross_provider_stability_established": False,
        "core_integration_authorized": False,
        "candidate_state": state,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _replication_surface(item, *, replication_id, corpus_hash):
    return {
        **item,
        "object_registry": sorted(
            item["object_registry"],
            key=lambda value: hash_payload([
                corpus_hash, replication_id, "OBJECT",
                value["object_id"],
            ]),
        ),
        "evidence_spans": sorted(
            item["evidence_spans"],
            key=lambda value: hash_payload([
                corpus_hash, replication_id, "SPAN", value["span_id"],
            ]),
        ),
    }


def _baseline_task(item, replication_id, refs, adapter):
    return _generation_task(
        item=item, replication_id=replication_id,
        route_id="A1_ONTOLOGY", refs=refs, adapter=adapter,
        stage="BASELINE",
    )


def _router_task(item, replication_id, refs, adapter):
    object_ids = [
        value["object_id"] for value in item["object_registry"]
    ]
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "case_id", "route_id", "focal_object_ids",
            "evidence_span_ids", "expected_cbit_source",
            "uncertainty_risk", "route_rationale",
            "stop_condition", "evidence_refs",
        ],
        "properties": {
            "case_id": {
                "type": "string", "enum": [item["case_id"]]
            },
            "route_id": {
                "type": "string", "enum": list(ROUTE_IDS)
            },
            "focal_object_ids": {
                "type": "array", "minItems": 1, "uniqueItems": True,
                "items": {"type": "string", "enum": object_ids},
            },
            "evidence_span_ids": {
                "type": "array", "minItems": 1, "uniqueItems": True,
                "items": {"type": "string", "enum": span_ids},
            },
            "expected_cbit_source": {
                "type": "string",
                "enum": [
                    "DIRECT_EVIDENCE_SYNTHESIS",
                    "MECHANISM_RESOLUTION",
                    "COUNTEREVIDENCE_DISCRIMINATION",
                    "OBJECT_OR_COORDINATE_REFRAMING",
                ],
            },
            "uncertainty_risk": {
                "type": "string",
                "enum": ["LOW", "MEDIUM", "HIGH"],
            },
            "route_rationale": {"type": "string"},
            "stop_condition": {"type": "string"},
            "evidence_refs": {
                "type": "array",
                "items": {"type": "string", "enum": list(refs)},
            },
        },
    }
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-ROUTER-"
            f"{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            "Choose exactly one cognitive route before candidate generation. "
            "Use A1_ONTOLOGY when evidence relations are already direct; "
            "MECHANISM for interacting processes; ADVERSARIAL when confounds, "
            "counterevidence, or measurement alternatives dominate; and "
            "COORDINATE_SHIFT when the focal object, proxy, or coordinate may "
            "be wrong. Maximize expected net uncertainty reduction, not role "
            "novelty. Return only the routing receipt."
        ),
        inputs={
            "stage": "PROVIDER_BACKED_STRUCTURAL_ROUTING",
            "replication_id": replication_id,
            "public_case": item,
            "available_routes": list(ROUTE_IDS),
            "private_outcome_available": False,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=schema,
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _worker_task(
    item, replication_id, route_id, refs, adapter, *, stage
):
    return _generation_task(
        item=item, replication_id=replication_id,
        route_id=route_id, refs=refs, adapter=adapter, stage=stage,
    )


def _generation_task(
    *, item, replication_id, route_id, refs, adapter, stage
):
    prompts = {
        "A1_ONTOLOGY": (
            "Build a compact object census and synthesize the three strongest "
            "evidence-bound problem candidates."
        ),
        "MECHANISM": (
            "Map interacting mechanisms and choose three relations with the "
            "strongest mechanistic uncertainty reduction."
        ),
        "ADVERSARIAL": (
            "Challenge the obvious explanation, prioritize counterevidence "
            "and discriminating tests, and return three candidates."
        ),
        "COORDINATE_SHIFT": (
            "Question the focal object, proxy, or coordinate and return three "
            "structurally reframed but evidence-bounded candidates."
        ),
    }
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-{stage}-{route_id}-"
            f"{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            f"{prompts[route_id]} Return exactly three distinct relations. "
            "Use one quality standard for CORE and FRONTIER, preserve "
            "uncertainty, and make every candidate falsifiable."
        ),
        inputs={
            "stage": stage,
            "replication_id": replication_id,
            "route_id": route_id,
            "receipt_arm_id": "A1_ONTOLOGY",
            "public_case": item,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=exact_three_schema(
            item=item, arm_id="A1_ONTOLOGY", refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _route_failures(route, *, item, refs):
    if not isinstance(route, dict):
        return ["ROUTE_NOT_OBJECT"]
    failures = []
    if route.get("case_id") != item["case_id"]:
        failures.append("CASE_BINDING_MISMATCH")
    if route.get("route_id") not in ROUTE_IDS:
        failures.append("ROUTE_ID_INVALID")
    if route.get("evidence_refs") != list(refs):
        failures.append("EVIDENCE_SCOPE_MISMATCH")
    return failures


def _call(
    *, replication_id, case_id, stage, route_id, task, envelope
):
    commitment = {
        "replication_id": replication_id,
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
        "case_id": call["case_id"],
        "stage": call["stage"],
        "route_id": call["route_id"],
        "status": call["status"],
        "invocation_receipt": call["invocation_receipt"],
    }


def _formal_scoring_run(run, *, replication_id):
    calls, projections = [], {}
    case_ids = sorted({
        value["case_id"] for value in run["task_calls"]
        if value["replication_id"] == replication_id
    })
    for case_id in case_ids:
        baseline = _find_call(
            run, replication_id, case_id, stage="BASELINE"
        )
        if baseline is not None:
            calls.append({
                "arm_id": "A1_BASELINE",
                "case_id": case_id,
                "invocation_receipt": baseline["invocation_receipt"],
            })
        baseline_projection = run["formal_projections"].get(
            f"{replication_id}:A1_BASELINE:{case_id}"
        )
        if baseline_projection is not None:
            projections[f"A1_BASELINE:{case_id}"] = baseline_projection
        router = _find_call(
            run, replication_id, case_id, stage="ROUTER"
        )
        worker = _find_call(
            run, replication_id, case_id, stage="ROUTED_WORKER"
        )
        path_calls = [
            value for value in (router, worker) if value is not None
        ]
        calls.append({
            "arm_id": "A2_ROUTED",
            "case_id": case_id,
            "invocation_receipt": {
                "token_usage": _combined_usage(path_calls),
                "derived_cost_receipt": True,
                "source_call_hashes": [
                    value["call_hash"] for value in path_calls
                ],
            },
        })
        routed_projection = run["formal_projections"].get(
            f"{replication_id}:A2_ROUTED:{case_id}"
        )
        if routed_projection is not None:
            projections[f"A2_ROUTED:{case_id}"] = routed_projection
    commitment = {"task_calls": calls, "projections": projections}
    return {**commitment, "run_hash": hash_payload(commitment)}


def _shadow_regret_audit(*, corpus, run):
    replication_id = SHADOW_AUDIT_REPLICATION_ID
    router_calls = {
        value["case_id"]: value
        for value in run["task_calls"]
        if value["replication_id"] == replication_id
        and value["stage"] == "ROUTER"
    }
    task_calls, projections = [], {}
    for item in corpus["public_surface"]["items"]:
        case_id = item["case_id"]
        router = router_calls.get(case_id)
        for route_id in ROUTE_IDS:
            worker = _find_route_worker_call(
                run, replication_id, case_id, route_id
            )
            path_calls = [
                value for value in (router, worker)
                if value is not None
            ]
            task_calls.append({
                "arm_id": route_id,
                "case_id": case_id,
                "invocation_receipt": {
                    "token_usage": _combined_usage(path_calls),
                },
            })
            projection = run["shadow_route_projections"].get(
                f"{replication_id}:{route_id}:{case_id}"
            )
            if projection is not None:
                projections[f"{route_id}:{case_id}"] = projection
    commitment = {"task_calls": task_calls, "projections": projections}
    scoring_run = {
        **commitment, "run_hash": hash_payload(commitment)
    }
    ledger = build_realized_cbit_ledger(
        corpus=corpus, run=scoring_run
    )
    totals = defaultdict(float)
    for entry in ledger["entries"]:
        totals[(entry["case_id"], entry["arm_id"])] += entry[
            "realized_effective_cbit"
        ]
    regrets, exact = [], 0
    selected_routes, best_routes = {}, {}
    for item in corpus["public_surface"]["items"]:
        case_id = item["case_id"]
        scores = {
            route_id: totals[(case_id, route_id)]
            for route_id in ROUTE_IDS
        }
        selected = run["route_receipts"].get(
            f"{replication_id}:{case_id}", {}
        ).get("route_id")
        best_score = max(scores.values())
        best = sorted(
            route_id for route_id, score in scores.items()
            if score == best_score
        )
        selected_score = scores.get(selected, 0.0)
        regret = best_score - selected_score
        regrets.append(regret)
        exact += selected in best
        selected_routes[case_id] = selected
        best_routes[case_id] = best
    return {
        "audit_version": "selective_role_routing_shadow_regret_v0_30",
        "replication_id": replication_id,
        "source_scoring_ledger_hash": ledger["artifact_hash"],
        "route_scores_include_router_and_one_worker_cost": True,
        "selected_routes": selected_routes,
        "best_routes_by_private_synthetic_outcome": best_routes,
        "top1_or_tied_accuracy": round(exact / corpus["case_count"], 6),
        "mean_regret": round(sum(regrets) / len(regrets), 6),
        "median_regret": _median(regrets),
        "within_quarter_cbit_rate": round(
            sum(value <= 0.25 for value in regrets) / len(regrets),
            6,
        ),
        "private_outcomes_used_for_posthoc_audit_only": True,
        "changes_formal_decision": False,
    }


def _runtime_metrics(run, *, corpus):
    expected = corpus["case_count"] * len(REPLICATION_IDS)
    completion = {}
    for stage in ("BASELINE", "ROUTER", "ROUTED_WORKER"):
        completion[stage] = round(
            sum(
                value["stage"] == stage
                and value["status"] == "COMPLETED"
                for value in run["task_calls"]
            ) / expected,
            6,
        )
    nonblock, exact_three = {}, {}
    for arm_id in FORMAL_ARM_IDS:
        values = [
            value
            for key, value in run["formal_projections"].items()
            if f":{arm_id}:" in key
        ]
        nonblock[arm_id] = round(
            sum(value["receipt_state"] != "BLOCK" for value in values)
            / expected,
            6,
        )
        exact_three[arm_id] = round(
            sum(
                len(value["eligible_candidate_ids"]) == 3
                for value in values
            ) / expected,
            6,
        )
    shadow_expected = corpus["case_count"] * len(ROUTE_IDS)
    return {
        "provider_completion_by_formal_stage": completion,
        "final_nonblock_coverage_per_arm": nonblock,
        "exact_three_coverage_per_arm": exact_three,
        "shadow_audit_projection_coverage": round(
            len(run["shadow_route_projections"]) / shadow_expected,
            6,
        ),
        "failure_count": len(run["failures"]),
    }


def _relation_reproducibility(run, *, arm_id, corpus):
    scores, exact = [], 0
    for item in corpus["public_surface"]["items"]:
        relations = {}
        for replication_id in REPLICATION_IDS:
            projection = run["formal_projections"].get(
                f"{replication_id}:{arm_id}:{item['case_id']}"
            )
            relations[replication_id] = {
                (
                    value["normalized_candidate"]["source_object_id"],
                    value["normalized_candidate"]["target_object_id"],
                )
                for value in (
                    projection["candidate_components"]
                    if projection else ()
                )
                if value["disposition"] != "QUARANTINED_COMPONENT"
            }
        for left, right in combinations(REPLICATION_IDS, 2):
            union = relations[left] | relations[right]
            scores.append(
                len(relations[left] & relations[right]) / len(union)
                if union else 1.0
            )
            exact += relations[left] == relations[right]
    return {
        "pair_count": len(scores),
        "mean_pairwise_relation_jaccard": round(
            sum(scores) / len(scores), 6
        ),
        "exact_pair_match_count": exact,
    }


def _metrics(values):
    return {
        "count": len(values),
        "mean": round(sum(values) / len(values), 6),
        "median": _median(values),
        "win_count": sum(value > 0 for value in values),
        "tie_count": sum(value == 0 for value in values),
        "loss_count": sum(value < 0 for value in values),
        "win_rate": round(
            sum(value > 0 for value in values) / len(values), 6
        ),
        "severe_loss_count": sum(value < -1.0 for value in values),
        "severe_loss_rate": round(
            sum(value < -1.0 for value in values) / len(values), 6
        ),
    }


def _median(values):
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    return round(
        ordered[midpoint]
        if len(ordered) % 2
        else (ordered[midpoint - 1] + ordered[midpoint]) / 2,
        6,
    )


def _find_call(run, replication_id, case_id, *, stage):
    return next((
        value for value in run["task_calls"]
        if value["replication_id"] == replication_id
        and value["case_id"] == case_id
        and value["stage"] == stage
    ), None)


def _find_route_worker_call(
    run, replication_id, case_id, route_id
):
    return next((
        value for value in run["task_calls"]
        if value["replication_id"] == replication_id
        and value["case_id"] == case_id
        and value["route_id"] == route_id
        and value["stage"] in {"ROUTED_WORKER", "SHADOW_WORKER"}
    ), None)


def _combined_usage(calls):
    prompt = completion = provider_calls = 0
    for call in calls:
        usage = call["invocation_receipt"].get("token_usage") or {}
        prompt += int(
            usage.get("prompt_tokens") or usage.get("input_tokens") or 0
        )
        completion += int(
            usage.get("completion_tokens")
            or usage.get("output_tokens") or 0
        )
        provider_calls += int(usage.get("provider_calls") or 1)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "provider_calls": provider_calls,
    }


def _formal_physical_tokens(run):
    return sum(
        _call_tokens(value)
        for value in run["task_calls"]
        if value["stage"] in {
            "BASELINE", "ROUTER", "ROUTED_WORKER",
        }
    )


def _validate_preregistration(preregistration, *, corpus):
    commitment = {
        key: value for key, value in preregistration.items()
        if key != "artifact_hash"
    }
    if (
        preregistration.get("artifact_hash") != hash_payload(commitment)
        or preregistration.get("source_corpus_hash")
        != corpus["artifact_hash"]
    ):
        raise ValueError("routing_preregistration_invalid")


def _validate_run(run, *, corpus, preregistration):
    commitment = {
        key: value for key, value in run.items() if key != "run_hash"
    }
    if (
        run.get("run_hash") != hash_payload(commitment)
        or run.get("source_corpus_hash") != corpus["artifact_hash"]
        or run.get("source_preregistration_hash")
        != preregistration["artifact_hash"]
    ):
        raise ValueError("selective_routing_run_invalid")


def _checkpoint(
    callback, *, corpus, preregistration, calls, raw_receipts,
    route_receipts, formal_projections, shadow_route_projections,
    failures,
):
    if callback is None:
        return
    commitment = {
        "progress_version": "selective_role_routing_progress_v0_30",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "completed_task_count": len(calls),
        "task_calls": list(calls),
        "raw_receipts": dict(raw_receipts),
        "route_receipts": dict(route_receipts),
        "formal_projections": dict(formal_projections),
        "shadow_route_projections": dict(shadow_route_projections),
        "failures": list(failures),
        "original_receipts_preserved": True,
        "resume_authority": False,
    }
    callback({
        **commitment,
        "artifact_hash": hash_payload(commitment),
    })


def _call_tokens(call):
    usage = call["invocation_receipt"].get("token_usage") or {}
    return int(
        usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    ) + int(
        usage.get("completion_tokens") or usage.get("output_tokens") or 0
    )
