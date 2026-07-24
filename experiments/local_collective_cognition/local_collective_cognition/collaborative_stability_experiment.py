"""Role-collaborative stabilization experiment v0.29."""

from __future__ import annotations

import copy
import math
from collections import Counter, defaultdict
from itertools import combinations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .collaborative_stability_holdout import (
    REPLICATION_IDS,
    validate_collaborative_stability_holdout,
)
from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_experiment import TASK_KIND, native_schema
from .frontier_partial_admission import project_frontier_receipt
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "collaborative_stability_experiment_v0_29"
ARM_IDS = ("A0_DIRECT", "A1_ONTOLOGY", "A2_COLLAB")
BASELINE_ARM_IDS = ("A0_DIRECT", "A1_ONTOLOGY")
ROLE_IDS = ("MECHANISM", "ADVERSARIAL", "COORDINATE_SHIFT")


def build_collaborative_preregistration(
    *, corpus, prior_analysis, prior_closure
):
    validate_collaborative_stability_holdout(corpus)
    failed_prior = {
        key for key, value in prior_analysis.get("conditions", {}).items()
        if value is False
    }
    if (
        prior_closure.get("candidate_state")
        != "FRONTIER_STABILITY_REJECTED_STOP"
        or prior_closure.get("stability_gate") != "REJECT"
        or prior_closure.get("core_integration_authorized") is not False
        or prior_analysis.get("decision")
        != "REJECT_NO_STABLE_CBIT_GAIN"
        or failed_prior != {
            "minimum_cross_replication_positive_consistency",
            "minimum_pooled_case_win_rate",
        }
    ):
        raise ValueError("collaborative_stability_prior_invalid")
    prior_total = int(prior_analysis["total_tokens"])
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "frozen_causal_question": (
            "When candidate count is fixed, can three context-isolated "
            "cognitive roles plus an evidence-only selector convert the "
            "positive but heavy-tailed ontology signal into majority-stable "
            "net realized Cbit after charging all collaboration tokens?"
        ),
        "replication_ids": list(REPLICATION_IDS),
        "role_ids": list(ROLE_IDS),
        "candidate_count_per_final_receipt": 3,
        "selector_can_generate_new_candidates": False,
        "primary_contrast": "A2_COLLAB_MINUS_A1_ONTOLOGY",
        "secondary_contrast": "A2_COLLAB_MINUS_A0_DIRECT",
        "cost_policy": {
            "all_proposer_and_selector_tokens_charged_to_a2": True,
            "token_cost_already_subtracted_inside_realized_cbit": True,
            "cbit_per_token_is_diagnostic_not_acceptance_gate": True,
            "soft_expected_total_tokens": prior_total * 4,
            "hard_runaway_total_tokens": math.ceil(prior_total * 6),
            "higher_cbit_higher_cost_can_pass": True,
        },
        "success_gate": {
            "minimum_provider_completion_by_stage": 0.95,
            "minimum_final_nonblock_coverage_per_arm": 0.9,
            "minimum_exact_three_coverage_per_arm": 0.9,
            "minimum_a2_mean_gain_vs_a1": 0.25,
            "minimum_a2_median_gain_vs_a1": 0.0,
            "minimum_a2_win_rate_vs_a1": 0.55,
            "minimum_positive_a2_replications_vs_a1": 2,
            "minimum_majority_positive_case_rate_vs_a1": 0.5,
            "minimum_a2_mean_gain_vs_a0": 0.25,
            "minimum_a2_median_gain_vs_a0": 0.0,
            "maximum_a2_severe_loss_rate_vs_a1": 0.15,
            "minimum_a2_relation_jaccard_relative_to_a1": -0.05,
            "hard_runaway_total_tokens": math.ceil(prior_total * 6),
        },
        "fresh_labels_available_during_inference": False,
        "external_semantic_panel_required": True,
        "selection_authority": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def exact_three_schema(*, item, arm_id, refs):
    schema = copy.deepcopy(
        native_schema(item=item, arm_id=arm_id, refs=refs)
    )
    schema["properties"]["problem_candidates"]["minItems"] = 3
    schema["properties"]["problem_candidates"]["maxItems"] = 3
    return schema


def run_collaborative_experiment(
    *, corpus, preregistration, adapter, checkpoint_callback=None
):
    validate_collaborative_stability_holdout(corpus)
    _validate_preregistration(preregistration, corpus=corpus)
    refs = tuple(corpus["evidence_refs"])
    cells = [
        (replication_id, item)
        for replication_id in REPLICATION_IDS
        for item in corpus["public_surface"]["items"]
    ]
    calls, raw_receipts, projections = [], {}, {}
    proposal_projections, candidate_pools, selector_receipts = {}, {}, {}
    failures = []

    first_phase = [
        (replication_id, item, stage_id)
        for replication_id, item in cells
        for stage_id in (*BASELINE_ARM_IDS, *ROLE_IDS)
    ]
    first_phase.sort(key=lambda value: hash_payload([
        RUNTIME_VERSION, "FIRST_PHASE", value[0], value[1]["case_id"],
        value[2],
    ]))
    for replication_id, canonical_item, stage_id in first_phase:
        item = _replication_surface(
            canonical_item,
            replication_id=replication_id,
            corpus_hash=corpus["artifact_hash"],
        )
        if stage_id in BASELINE_ARM_IDS:
            task = _baseline_task(
                item, replication_id, stage_id, refs, adapter
            )
            stage = "BASELINE"
            experimental_arm_id = stage_id
            role_id = None
        else:
            task = _proposer_task(
                item, replication_id, stage_id, refs, adapter
            )
            stage = "PROPOSER"
            experimental_arm_id = "A2_COLLAB"
            role_id = stage_id
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=replication_id,
            case_id=item["case_id"],
            experimental_arm_id=experimental_arm_id,
            stage=stage,
            role_id=role_id,
            task=task,
            envelope=envelope,
        )
        calls.append(call)
        key = _stage_key(
            replication_id, item["case_id"], experimental_arm_id,
            role_id=role_id,
        )
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            raw = envelope.normalized_result
            raw_receipts[key] = raw
            receipt_arm = (
                experimental_arm_id
                if stage == "BASELINE" else "A1_ONTOLOGY"
            )
            projection = project_frontier_receipt(
                raw_receipt=raw,
                item=item,
                arm_id=receipt_arm,
                evidence_refs=refs,
            )
            if stage == "BASELINE":
                projections[
                    f"{replication_id}:{experimental_arm_id}:"
                    f"{item['case_id']}"
                ] = projection
            else:
                proposal_projections[key] = projection
        _checkpoint(
            checkpoint_callback, corpus=corpus,
            preregistration=preregistration, calls=calls,
            raw_receipts=raw_receipts, projections=projections,
            proposal_projections=proposal_projections,
            candidate_pools=candidate_pools,
            selector_receipts=selector_receipts, failures=failures,
        )

    selector_cells = sorted(cells, key=lambda value: hash_payload([
        RUNTIME_VERSION, "SELECTOR", value[0], value[1]["case_id"],
    ]))
    for replication_id, canonical_item in selector_cells:
        item = _replication_surface(
            canonical_item,
            replication_id=replication_id,
            corpus_hash=corpus["artifact_hash"],
        )
        pool = _candidate_pool(
            replication_id=replication_id,
            case_id=item["case_id"],
            proposal_projections=proposal_projections,
        )
        pool_key = f"{replication_id}:A2_COLLAB:{item['case_id']}"
        candidate_pools[pool_key] = pool
        task = _selector_task(
            item, replication_id, pool, refs, adapter,
            corpus_hash=corpus["artifact_hash"],
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=replication_id,
            case_id=item["case_id"],
            experimental_arm_id="A2_COLLAB",
            stage="SELECTOR",
            role_id="EVIDENCE_SELECTOR",
            task=task,
            envelope=envelope,
        )
        calls.append(call)
        selector_key = (
            f"{replication_id}:A2_COLLAB:EVIDENCE_SELECTOR:"
            f"{item['case_id']}"
        )
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            selector = envelope.normalized_result
            raw_receipts[selector_key] = selector
            selector_receipts[pool_key] = selector
            selector_failures = _selector_failures(
                selector, item=item, pool=pool, refs=refs
            )
            if selector_failures:
                failures.append({
                    "replication_id": replication_id,
                    "case_id": item["case_id"],
                    "experimental_arm_id": "A2_COLLAB",
                    "stage": "SELECTOR_VALIDATION",
                    "failures": selector_failures,
                    "selector_receipt_hash": hash_payload(selector),
                })
            else:
                projections[pool_key] = _assemble_collab_projection(
                    selector=selector,
                    pool=pool,
                    item=item,
                    refs=refs,
                    replication_id=replication_id,
                    proposal_projections=proposal_projections,
                )
        _checkpoint(
            checkpoint_callback, corpus=corpus,
            preregistration=preregistration, calls=calls,
            raw_receipts=raw_receipts, projections=projections,
            proposal_projections=proposal_projections,
            candidate_pools=candidate_pools,
            selector_receipts=selector_receipts, failures=failures,
        )

    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "replication_ids": list(REPLICATION_IDS),
        "role_ids": list(ROLE_IDS),
        "task_calls": calls,
        "raw_receipts": raw_receipts,
        "final_projections": projections,
        "proposal_projections": proposal_projections,
        "candidate_pools": candidate_pools,
        "selector_receipts": selector_receipts,
        "failures": failures,
        "raw_receipts_preserved_before_projection": True,
        "selector_new_candidate_generation_allowed": False,
        "private_truth_exposed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_collaborative_experiment(*, corpus, preregistration, run):
    validate_collaborative_stability_holdout(corpus)
    _validate_preregistration(preregistration, corpus=corpus)
    _validate_run(run, corpus=corpus, preregistration=preregistration)
    ledgers, case_totals = {}, {}
    replication_metrics = {}
    contrasts = {"A1_MINUS_A0": {}, "A2_MINUS_A1": {}, "A2_MINUS_A0": {}}
    for replication_id in REPLICATION_IDS:
        scoring_run = _scoring_run(run, replication_id=replication_id)
        ledger = build_realized_cbit_ledger(
            corpus=corpus, run=scoring_run
        )
        ledgers[replication_id] = ledger
        totals = defaultdict(float)
        for entry in ledger["entries"]:
            totals[(entry["case_id"], entry["arm_id"])] += entry[
                "realized_effective_cbit"
            ]
        case_totals[replication_id] = {
            f"{case_id}:{arm_id}": round(value, 6)
            for (case_id, arm_id), value in totals.items()
        }
        deltas = {
            "A1_MINUS_A0": _case_deltas(
                corpus, totals, "A1_ONTOLOGY", "A0_DIRECT"
            ),
            "A2_MINUS_A1": _case_deltas(
                corpus, totals, "A2_COLLAB", "A1_ONTOLOGY"
            ),
            "A2_MINUS_A0": _case_deltas(
                corpus, totals, "A2_COLLAB", "A0_DIRECT"
            ),
        }
        for name, values in deltas.items():
            contrasts[name][replication_id] = values
        replication_metrics[replication_id] = {
            "arm_cbit_per_case": {
                arm_id: ledger["arm_metrics"][arm_id][
                    "mean_effective_cbit_per_case"
                ]
                for arm_id in ARM_IDS
            },
            "arm_total_tokens": {
                arm_id: ledger["arm_metrics"][arm_id]["total_tokens"]
                for arm_id in ARM_IDS
            },
            "contrasts": {
                name: _contrast_metrics(values)
                for name, values in deltas.items()
            },
        }

    pooled = {
        name: [
            value
            for replication in values.values()
            for value in replication.values()
        ]
        for name, values in contrasts.items()
    }
    pooled_metrics = {
        name: _contrast_metrics(values)
        for name, values in pooled.items()
    }
    majority_positive_case_rates = {
        name: round(
            sum(
                sum(
                    contrasts[name][replication_id][case_id] > 0
                    for replication_id in REPLICATION_IDS
                ) >= 2
                for case_id in contrasts[name][REPLICATION_IDS[0]]
            ) / corpus["case_count"],
            6,
        )
        for name in contrasts
    }
    relation_reproducibility = {
        arm_id: _relation_reproducibility(
            run, arm_id=arm_id, corpus=corpus
        )
        for arm_id in ARM_IDS
    }
    runtime_metrics = _runtime_metrics(run, corpus=corpus)
    total_tokens = sum(_call_tokens(value) for value in run["task_calls"])
    gate = preregistration["success_gate"]
    a2a1 = pooled_metrics["A2_MINUS_A1"]
    a2a0 = pooled_metrics["A2_MINUS_A0"]
    positive_replications = sum(
        replication_metrics[replication_id]["contrasts"][
            "A2_MINUS_A1"
        ]["mean"] > 0
        for replication_id in REPLICATION_IDS
    )
    conditions = {
        "minimum_provider_completion_by_stage": all(
            value >= gate["minimum_provider_completion_by_stage"]
            for value in runtime_metrics[
                "provider_completion_by_stage"
            ].values()
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
        "minimum_a2_mean_gain_vs_a1": (
            a2a1["mean"] >= gate["minimum_a2_mean_gain_vs_a1"]
        ),
        "minimum_a2_median_gain_vs_a1": (
            a2a1["median"] >= gate["minimum_a2_median_gain_vs_a1"]
        ),
        "minimum_a2_win_rate_vs_a1": (
            a2a1["win_rate"] >= gate["minimum_a2_win_rate_vs_a1"]
        ),
        "minimum_positive_a2_replications_vs_a1": (
            positive_replications
            >= gate["minimum_positive_a2_replications_vs_a1"]
        ),
        "minimum_majority_positive_case_rate_vs_a1": (
            majority_positive_case_rates["A2_MINUS_A1"]
            >= gate["minimum_majority_positive_case_rate_vs_a1"]
        ),
        "minimum_a2_mean_gain_vs_a0": (
            a2a0["mean"] >= gate["minimum_a2_mean_gain_vs_a0"]
        ),
        "minimum_a2_median_gain_vs_a0": (
            a2a0["median"] >= gate["minimum_a2_median_gain_vs_a0"]
        ),
        "maximum_a2_severe_loss_rate_vs_a1": (
            a2a1["severe_loss_rate"]
            <= gate["maximum_a2_severe_loss_rate_vs_a1"]
        ),
        "minimum_a2_relation_jaccard_relative_to_a1": (
            relation_reproducibility["A2_COLLAB"][
                "mean_pairwise_relation_jaccard"
            ]
            - relation_reproducibility["A1_ONTOLOGY"][
                "mean_pairwise_relation_jaccard"
            ]
            >= gate["minimum_a2_relation_jaccard_relative_to_a1"]
        ),
        "hard_runaway_total_tokens": (
            total_tokens <= gate["hard_runaway_total_tokens"]
        ),
        "all_a2_tokens_charged": _a2_cost_accounting_complete(
            run, ledgers=ledgers
        ),
        "selector_did_not_generate_candidates": all(
            _selector_is_pool_subset(
                selector=run["selector_receipts"][key],
                pool=pool,
            )
            for key, pool in run["candidate_pools"].items()
            if key in run["selector_receipts"]
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
        decision = "PASS_COLLABORATIVE_STABILIZATION"
        state = "COLLABORATIVE_STABILITY_PASSED_READY_EXTERNAL_PANEL"
    elif total_tokens > gate["hard_runaway_total_tokens"]:
        decision = "STOP_RESOURCE_RUNAWAY"
        state = "COLLABORATIVE_STABILITY_RESOURCE_STOP"
    else:
        decision = "REJECT_COLLABORATIVE_STABILIZATION"
        state = "COLLABORATIVE_STABILITY_REJECTED_STOP"
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "replication_ledgers": ledgers,
        "case_totals": case_totals,
        "contrasts": contrasts,
        "replication_metrics": replication_metrics,
        "pooled_contrast_metrics": pooled_metrics,
        "majority_positive_case_rates": majority_positive_case_rates,
        "relation_reproducibility": relation_reproducibility,
        "runtime_metrics": runtime_metrics,
        "positive_a2_replications_vs_a1": positive_replications,
        "total_tokens": total_tokens,
        "soft_expected_total_tokens": preregistration[
            "cost_policy"
        ]["soft_expected_total_tokens"],
        "soft_cost_warning": (
            total_tokens
            > preregistration["cost_policy"]["soft_expected_total_tokens"]
        ),
        "conditions": conditions,
        "collaborative_stability_gate": "PASS" if passed else "REJECT",
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
                corpus_hash, replication_id, "OBJECT", value["object_id"],
            ]),
        ),
        "evidence_spans": sorted(
            item["evidence_spans"],
            key=lambda value: hash_payload([
                corpus_hash, replication_id, "SPAN", value["span_id"],
            ]),
        ),
    }


def _baseline_task(item, replication_id, arm_id, refs, adapter):
    if arm_id == "A0_DIRECT":
        method = (
            "Generate candidates directly without an object census."
        )
    else:
        method = (
            "Build a compact object census before generating candidates."
        )
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-{arm_id}-"
            f"{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            f"{method} Return exactly three distinct problem candidates. "
            "Use one common quality standard for CORE and FRONTIER. Preserve "
            "uncertainty, bind evidence and constraints, and make every "
            "candidate falsifiable."
        ),
        inputs={
            "stage": "EQUAL_COUNT_BASELINE",
            "replication_id": replication_id,
            "arm_id": arm_id,
            "public_case": item,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=exact_three_schema(
            item=item, arm_id=arm_id, refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _proposer_task(item, replication_id, role_id, refs, adapter):
    role_prompts = {
        "MECHANISM": (
            "Map plausible mechanisms and choose relations with the strongest "
            "evidence-bound uncertainty reduction."
        ),
        "ADVERSARIAL": (
            "Challenge the obvious explanation, search for counterevidence, "
            "and propose discriminating tests or informative nulls."
        ),
        "COORDINATE_SHIFT": (
            "Switch focal objects or coordinates and expose a structurally "
            "distinct but falsifiable relation."
        ),
    }
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-A2-{role_id}-"
            f"{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            f"{role_prompts[role_id]} First build a compact object census. "
            "Return exactly three distinct candidates. Do not communicate "
            "with other proposers and do not claim promotion authority."
        ),
        inputs={
            "stage": "ISOLATED_ROLE_PROPOSAL",
            "replication_id": replication_id,
            "experimental_arm_id": "A2_COLLAB",
            "receipt_arm_id": "A1_ONTOLOGY",
            "role_id": role_id,
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


def _selector_task(
    item, replication_id, pool, refs, adapter, *, corpus_hash
):
    pool_ids = [value["pool_candidate_id"] for value in pool["candidates"]]
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "case_id", "arm_id", "selected_candidate_ids",
            "selected_problem_id", "rationale", "evidence_refs",
        ],
        "properties": {
            "case_id": {
                "type": "string", "enum": [item["case_id"]]
            },
            "arm_id": {
                "type": "string", "enum": ["A2_COLLAB"]
            },
            "selected_candidate_ids": {
                "type": "array", "minItems": 3, "maxItems": 3,
                "uniqueItems": True,
                "items": {"type": "string", "enum": pool_ids},
            },
            "selected_problem_id": {
                "type": "string", "enum": pool_ids
            },
            "rationale": {"type": "string"},
            "evidence_refs": {
                "type": "array",
                "items": {"type": "string", "enum": list(refs)},
            },
        },
    }
    ordered_pool = sorted(
        pool["candidates"],
        key=lambda value: hash_payload([
            corpus_hash, replication_id, "POOL",
            value["pool_candidate_id"],
        ]),
    )
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-A2-SELECTOR-"
            f"{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            "Select exactly three candidates from the supplied pool. You may "
            "not rewrite or generate candidates. Select distinct object "
            "relations that maximize evidence support, counterevidence "
            "coverage, constraint awareness, falsifiability, and expected "
            "uncertainty reduction. Frontier status receives no bonus."
        ),
        inputs={
            "stage": "EVIDENCE_ONLY_POOL_SELECTION",
            "replication_id": replication_id,
            "arm_id": "A2_COLLAB",
            "public_case": item,
            "candidate_pool": ordered_pool,
            "candidate_pool_hash": pool["artifact_hash"],
            "selection_criteria": [
                "EVIDENCE_SUPPORT", "COUNTEREVIDENCE",
                "CONSTRAINT_COVERAGE", "FALSIFIABILITY",
                "RELATION_DIVERSITY", "EXPECTED_UNCERTAINTY_REDUCTION",
            ],
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=schema,
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _call(
    *, replication_id, case_id, experimental_arm_id, stage, role_id,
    task, envelope,
):
    commitment = {
        "replication_id": replication_id,
        "case_id": case_id,
        "experimental_arm_id": experimental_arm_id,
        "stage": stage,
        "role_id": role_id,
        "status": envelope.status,
        "task_contract_hash": task.contract_hash(),
        "private_truth_exposed": False,
        "invocation_receipt": envelope.invocation_receipt.as_dict(),
    }
    return {**commitment, "call_hash": hash_payload(commitment)}


def _stage_key(
    replication_id, case_id, experimental_arm_id, *, role_id
):
    if role_id is None:
        return f"{replication_id}:{experimental_arm_id}:{case_id}"
    return (
        f"{replication_id}:{experimental_arm_id}:{role_id}:{case_id}"
    )


def _provider_failure(call):
    return {
        "replication_id": call["replication_id"],
        "case_id": call["case_id"],
        "experimental_arm_id": call["experimental_arm_id"],
        "stage": call["stage"],
        "role_id": call["role_id"],
        "status": call["status"],
        "invocation_receipt": call["invocation_receipt"],
    }


def _candidate_pool(
    *, replication_id, case_id, proposal_projections
):
    candidates = []
    for role_id in ROLE_IDS:
        key = (
            f"{replication_id}:A2_COLLAB:{role_id}:{case_id}"
        )
        projection = proposal_projections.get(key)
        if projection is None:
            continue
        eligible = [
            value for value in projection["candidate_components"]
            if value["disposition"] != "QUARANTINED_COMPONENT"
        ]
        for index, component in enumerate(eligible, 1):
            pool_id = (
                f"{role_id}-{index}-{component['candidate_id']}"
            )
            candidate = {
                **component["normalized_candidate"],
                "candidate_id": pool_id,
            }
            candidates.append({
                "pool_candidate_id": pool_id,
                "role_id": role_id,
                "candidate": candidate,
                "source_projection_hash": projection["artifact_hash"],
            })
    candidates.sort(key=lambda value: value["pool_candidate_id"])
    commitment = {
        "pool_version": "collaborative_candidate_pool_v0_29",
        "replication_id": replication_id,
        "case_id": case_id,
        "candidates": candidates,
        "candidate_generation_by_selector_allowed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _selector_failures(selector, *, item, pool, refs):
    if not isinstance(selector, dict):
        return ["SELECTOR_NOT_OBJECT"]
    failures = []
    if selector.get("case_id") != item["case_id"]:
        failures.append("CASE_BINDING_MISMATCH")
    if selector.get("arm_id") != "A2_COLLAB":
        failures.append("ARM_BINDING_MISMATCH")
    if selector.get("evidence_refs") != list(refs):
        failures.append("EVIDENCE_SCOPE_MISMATCH")
    selected = selector.get("selected_candidate_ids")
    pool_by_id = {
        value["pool_candidate_id"]: value
        for value in pool["candidates"]
    }
    if (
        not isinstance(selected, list)
        or len(selected) != 3
        or len(set(selected)) != 3
        or not set(selected).issubset(pool_by_id)
    ):
        failures.append("SELECTED_IDS_INVALID")
        return failures
    if selector.get("selected_problem_id") not in selected:
        failures.append("PRIMARY_SELECTION_NOT_INCLUDED")
    relations = {
        (
            pool_by_id[value]["candidate"]["source_object_id"],
            pool_by_id[value]["candidate"]["target_object_id"],
        )
        for value in selected
    }
    if len(relations) != 3:
        failures.append("SELECTED_RELATIONS_NOT_DISTINCT")
    return failures


def _assemble_collab_projection(
    *, selector, pool, item, refs, replication_id,
    proposal_projections,
):
    pool_by_id = {
        value["pool_candidate_id"]: value
        for value in pool["candidates"]
    }
    candidates = [
        pool_by_id[value]["candidate"]
        for value in selector["selected_candidate_ids"]
    ]
    census = {}
    for role_id in ROLE_IDS:
        key = (
            f"{replication_id}:A2_COLLAB:{role_id}:"
            f"{item['case_id']}"
        )
        projection = proposal_projections.get(key)
        if projection is None:
            continue
        for component in projection["census_components"]:
            if component["disposition"] != "QUARANTINED_COMPONENT":
                value = component["normalized_object"]
                census.setdefault(value["object_id"], value)
    raw = {
        "case_id": item["case_id"],
        "arm_id": "A1_ONTOLOGY",
        "problem_candidates": candidates,
        "selected_problem_id": selector["selected_problem_id"],
        "rationale": selector["rationale"],
        "evidence_refs": list(refs),
        "object_census": [
            census[key] for key in sorted(census)
        ],
    }
    return project_frontier_receipt(
        raw_receipt=raw,
        item=item,
        arm_id="A1_ONTOLOGY",
        evidence_refs=refs,
    )


def _scoring_run(run, *, replication_id):
    scoring_calls = []
    projections = {}
    for arm_id in BASELINE_ARM_IDS:
        for call in run["task_calls"]:
            if (
                call["replication_id"] == replication_id
                and call["experimental_arm_id"] == arm_id
                and call["stage"] == "BASELINE"
            ):
                scoring_calls.append({
                    "arm_id": arm_id,
                    "case_id": call["case_id"],
                    "invocation_receipt": call["invocation_receipt"],
                })
        for key, projection in run["final_projections"].items():
            if key.startswith(f"{replication_id}:{arm_id}:"):
                projections[key.split(":", 1)[1]] = projection
    case_ids = sorted({
        call["case_id"] for call in run["task_calls"]
        if call["replication_id"] == replication_id
    })
    for case_id in case_ids:
        path_calls = [
            call for call in run["task_calls"]
            if call["replication_id"] == replication_id
            and call["case_id"] == case_id
            and call["experimental_arm_id"] == "A2_COLLAB"
            and call["stage"] in {"PROPOSER", "SELECTOR"}
        ]
        scoring_calls.append({
            "arm_id": "A2_COLLAB",
            "case_id": case_id,
            "invocation_receipt": {
                "token_usage": _combined_usage(path_calls),
                "derived_cost_receipt": True,
                "source_call_hashes": [
                    value["call_hash"] for value in path_calls
                ],
            },
        })
        projection = run["final_projections"].get(
            f"{replication_id}:A2_COLLAB:{case_id}"
        )
        if projection is not None:
            projections[f"A2_COLLAB:{case_id}"] = projection
    commitment = {
        "task_calls": scoring_calls,
        "projections": projections,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


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


def _case_deltas(corpus, totals, positive_arm, reference_arm):
    return {
        case_id: round(
            totals[(case_id, positive_arm)]
            - totals[(case_id, reference_arm)],
            6,
        )
        for case_id in sorted(
            item["case_id"]
            for item in corpus["public_surface"]["items"]
        )
    }


def _contrast_metrics(values):
    if isinstance(values, dict):
        values = list(values.values())
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    median = (
        ordered[midpoint]
        if len(ordered) % 2
        else (ordered[midpoint - 1] + ordered[midpoint]) / 2
    )
    return {
        "count": len(values),
        "mean": round(sum(values) / len(values), 6),
        "median": round(median, 6),
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
        "positive_sum": round(
            sum(value for value in values if value > 0), 6
        ),
        "negative_sum": round(
            sum(value for value in values if value < 0), 6
        ),
    }


def _runtime_metrics(run, *, corpus):
    expected_cells = corpus["case_count"] * len(REPLICATION_IDS)
    expected_by_stage = {
        "BASELINE_A0": expected_cells,
        "BASELINE_A1": expected_cells,
        "PROPOSER": expected_cells * len(ROLE_IDS),
        "SELECTOR": expected_cells,
    }
    completed_by_stage = Counter()
    for call in run["task_calls"]:
        if call["status"] != "COMPLETED":
            continue
        if call["stage"] == "BASELINE":
            key = (
                "BASELINE_A0"
                if call["experimental_arm_id"] == "A0_DIRECT"
                else "BASELINE_A1"
            )
        else:
            key = call["stage"]
        completed_by_stage[key] += 1
    completion = {
        key: round(completed_by_stage[key] / expected, 6)
        for key, expected in expected_by_stage.items()
    }
    nonblock, exact_three = {}, {}
    for arm_id in ARM_IDS:
        values = [
            projection
            for key, projection in run["final_projections"].items()
            if f":{arm_id}:" in key
        ]
        nonblock[arm_id] = round(
            sum(value["receipt_state"] != "BLOCK" for value in values)
            / expected_cells,
            6,
        )
        exact_three[arm_id] = round(
            sum(
                len(value["eligible_candidate_ids"]) == 3
                for value in values
            ) / expected_cells,
            6,
        )
    return {
        "expected_final_cells_per_arm": expected_cells,
        "provider_completion_by_stage": completion,
        "final_nonblock_coverage_per_arm": nonblock,
        "exact_three_coverage_per_arm": exact_three,
        "failure_count": len(run["failures"]),
    }


def _relation_reproducibility(run, *, arm_id, corpus):
    jaccards = []
    exact = 0
    for item in corpus["public_surface"]["items"]:
        relations = {}
        for replication_id in REPLICATION_IDS:
            projection = run["final_projections"].get(
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
            score = (
                len(relations[left] & relations[right]) / len(union)
                if union else 1.0
            )
            jaccards.append(score)
            exact += relations[left] == relations[right]
    return {
        "pair_count": len(jaccards),
        "mean_pairwise_relation_jaccard": round(
            sum(jaccards) / len(jaccards), 6
        ),
        "exact_pair_match_count": exact,
    }


def _a2_cost_accounting_complete(run, *, ledgers):
    physical = sum(
        _call_tokens(value)
        for value in run["task_calls"]
        if value["experimental_arm_id"] == "A2_COLLAB"
    )
    accounted = sum(
        ledger["arm_metrics"]["A2_COLLAB"]["total_tokens"]
        for ledger in ledgers.values()
    )
    return physical == accounted


def _selector_is_pool_subset(*, selector, pool):
    selected = selector.get("selected_candidate_ids")
    return (
        isinstance(selected, list)
        and set(selected).issubset({
            value["pool_candidate_id"] for value in pool["candidates"]
        })
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
        raise ValueError("collaborative_preregistration_invalid")


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
        raise ValueError("collaborative_run_invalid")


def _checkpoint(
    callback, *, corpus, preregistration, calls, raw_receipts,
    projections, proposal_projections, candidate_pools,
    selector_receipts, failures,
):
    if callback is None:
        return
    commitment = {
        "progress_version": "collaborative_stability_progress_v0_29",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "completed_task_count": len(calls),
        "task_calls": list(calls),
        "raw_receipts": dict(raw_receipts),
        "final_projections": dict(projections),
        "proposal_projections": dict(proposal_projections),
        "candidate_pools": dict(candidate_pools),
        "selector_receipts": dict(selector_receipts),
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
