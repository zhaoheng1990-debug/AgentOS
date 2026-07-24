"""Fresh dual-axis EFFECT witness experiment v0.56."""

from __future__ import annotations

import copy
import math

from .effect_witness_contract import (
    CONTRACT_VERSION,
    derive_independent_effect_witnesses,
)
from .effect_witness_holdout import validate_effect_witness_holdout
from .evidence_first_contract import (
    AUDIT_ROLES,
    apply_evidence_first_gate,
)
from .evidence_first_experiment import (
    analyze_evidence_first_experiment,
    run_evidence_first_experiment,
)
from .frontier_partial_admission import project_frontier_receipt
from .independent_arbitration_experiment import _replication_surface
from .provider_telemetry import hash_payload
from .relation_stability_audit import measure_relation_stability


RUNTIME_VERSION = "effect_witness_dual_axis_experiment_v0_56"


def build_effect_witness_preregistration(
    *,
    corpus,
    reference_audit,
    prior_preregistration,
    prior_analysis,
    prior_closure,
    prior_posthoc,
    stability_closure,
    gate_candidate,
):
    validate_effect_witness_holdout(corpus)
    for value in (
        reference_audit,
        prior_preregistration,
        prior_analysis,
        prior_closure,
        prior_posthoc,
        stability_closure,
        gate_candidate,
    ):
        _validate_hash(value)
    if (
        reference_audit.get("reference_complete") is not True
        or prior_closure.get("candidate_state")
        != "EVIDENCE_FIRST_ARBITRATION_REJECTED_STOP"
        or stability_closure.get("candidate_state")
        != "DUAL_AXIS_GATE_READY_FOR_FRESH_PREREGISTRATION"
        or gate_candidate.get("status")
        != "CANDIDATE_ONLY_PENDING_FRESH_PREREGISTRATION"
    ):
        raise ValueError("effect_witness_prior_invalid")
    prior_tokens = prior_analysis["physical_total_tokens"]
    success = copy.deepcopy(prior_preregistration["success_gate"])
    success.update({
        "minimum_accepted_composition_count": 6,
        "minimum_distinct_acceptance_lanes": 2,
        "minimum_effect_lane_acceptance_count": 2,
        "minimum_lineage_contract_coverage": 1.0,
        "maximum_unsupported_relation_occurrence_rate": 0.0,
        "minimum_union_reference_coverage_delta": 0.0,
        "minimum_consensus_reference_coverage": 0.25,
        "maximum_harmful_acceptance_count": 0,
        "maximum_physical_total_tokens": math.ceil(prior_tokens * 1.4),
        "hard_runaway_total_tokens": math.ceil(prior_tokens * 1.7),
        "required_shared_standard_call_count": corpus["case_count"] * 3,
    })
    commitment = {
        key: copy.deepcopy(value)
        for key, value in prior_preregistration.items()
        if key != "artifact_hash"
    }
    commitment.update({
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_reference_audit_hash": reference_audit["artifact_hash"],
        "source_prior_preregistration_hash": prior_preregistration[
            "artifact_hash"
        ],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
        "source_stability_closure_hash": stability_closure[
            "artifact_hash"
        ],
        "source_dual_axis_gate_candidate_hash": gate_candidate[
            "artifact_hash"
        ],
        "source_effect_witness_contract_version": CONTRACT_VERSION,
        "success_gate": success,
        "cost_policy": copy.deepcopy(
            prior_preregistration["cost_policy"]
        ),
        "evidence_first_policy_frozen_from_v0_54": True,
        "effect_witness_adds_provider_calls": False,
        "same_stage_independent_context_required": True,
        "jaccard_is_diagnostic_not_solo_gate": True,
        "fresh_labels_available_during_inference": False,
        "selection_authority": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    })
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_effect_witness_experiment(*, corpus, preregistration, adapter):
    validate_effect_witness_holdout(corpus)
    base = run_evidence_first_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
        holdout_validator=validate_effect_witness_holdout,
    )
    gates = copy.deepcopy(base["replacement_gate_receipts"])
    compositions = copy.deepcopy(base["composition_receipts"])
    projections = copy.deepcopy(base["final_projections"])
    raws = copy.deepcopy(base["raw_receipts"])
    witness_receipts = {}
    refs = tuple(corpus["evidence_refs"])
    items = {
        value["case_id"]: value
        for value in corpus["public_surface"]["items"]
    }
    for key in sorted(base["pairwise_displacement_valid_keys"]):
        rep, arm, case_id = key.split(":", 2)
        delta = raws[f"{rep}:{arm}:PROVIDER_COMPACT_DELTA:{case_id}"]
        witnesses = derive_independent_effect_witnesses(
            raw_receipts=raws,
            lineage_valid_keys=base["lineage_valid_keys"],
            source_replication_id=rep,
            arm_id=arm,
            case_id=case_id,
            source_object_id=delta["source_object_id"],
            target_object_id=delta["target_object_id"],
        )
        witness_receipts[key] = witnesses
        if delta["proposed_admission_lane"] != "EFFECT" or not witnesses:
            continue
        initial = base["pairwise_displacement_receipts"][key]
        blind = [
            base["blind_evidence_receipts"][f"{key}:{role}"]
            for role in AUDIT_ROLES
            if f"{key}:{role}" in base["blind_evidence_receipts"]
        ]
        final_raw, accepted, gate = apply_evidence_first_gate(
            provisional_receipt=raws[
                f"{rep}:SHARED_STANDARD:STANDARD_OPPORTUNITY:{case_id}"
            ],
            proposed_receipt=raws[
                f"{rep}:{arm}:RUNTIME_PROPOSED:{case_id}"
            ],
            composition_receipt=base[
                "proposed_composition_receipts"
            ][key],
            portfolio_view=base["pairwise_displacement_views"][key],
            lineage_delta=delta,
            cross_replication_witnesses=[
                f"DELTA:{value['witness_replication_id']}"
                for value in witnesses
            ],
            initial_receipt=initial,
            blind_receipts=blind,
        )
        gate_commitment = {
            name: value for name, value in gate.items()
            if name != "artifact_hash"
        }
        gate_commitment.update({
            "independent_effect_witness_used": True,
            "source_effect_witness_hashes": [
                value["artifact_hash"] for value in witnesses
            ],
        })
        gate = {
            **gate_commitment,
            "artifact_hash": hash_payload(gate_commitment),
        }
        gates[key] = gate
        compositions.pop(key, None)
        if accepted is not None:
            compositions[key] = accepted
        canonical = items[case_id]
        item = _replication_surface(
            canonical, replication_id=rep,
            corpus_hash=corpus["artifact_hash"],
        )
        projections[key] = project_frontier_receipt(
            raw_receipt=final_raw, item=item,
            arm_id="A1_ONTOLOGY", evidence_refs=refs,
        )
        raws[f"{rep}:{arm}:RUNTIME_GATED:{case_id}"] = final_raw
    commitment = {
        name: copy.deepcopy(value)
        for name, value in base.items() if name != "run_hash"
    }
    commitment.update({
        "runtime_version": RUNTIME_VERSION,
        "source_base_run_hash": base["run_hash"],
        "raw_receipts": raws,
        "final_projections": projections,
        "replacement_gate_receipts": gates,
        "composition_receipts": compositions,
        "independent_effect_witness_receipts": witness_receipts,
        "effect_witness_adds_provider_calls": False,
    })
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_effect_witness_experiment(*, corpus, preregistration, run):
    base = analyze_evidence_first_experiment(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
        holdout_validator=validate_effect_witness_holdout,
    )
    measured = measure_relation_stability(corpus=corpus, run=run)
    summaries = measured["arm_summaries"]
    baseline = summaries["A1_BASELINE"]
    delta = summaries["A2_COMPACT_DELTA"]
    gates = run["replacement_gate_receipts"].values()
    effect_accepted = sum(
        value["accepted"] and value["bound_lane"] == "EFFECT"
        for value in gates
    )
    effect_witnessed = sum(
        value.get("independent_effect_witness_used") is True
        and value["accepted"]
        for value in gates
    )
    conditions = copy.deepcopy(base["conditions"])
    conditions.pop("minimum_relation_jaccard_relative_to_baseline", None)
    gate = preregistration["success_gate"]
    conditions.update({
        "minimum_effect_lane_acceptance_count": (
            effect_accepted >= gate["minimum_effect_lane_acceptance_count"]
        ),
        "maximum_unsupported_relation_occurrence_rate": (
            delta["unsupported_relation_occurrence_rate"]
            <= gate["maximum_unsupported_relation_occurrence_rate"]
        ),
        "minimum_union_reference_coverage_delta": (
            delta["mean_union_reference_coverage"]
            - baseline["mean_union_reference_coverage"]
            >= gate["minimum_union_reference_coverage_delta"]
        ),
        "minimum_consensus_reference_coverage": (
            delta["mean_consensus_reference_coverage"]
            >= gate["minimum_consensus_reference_coverage"]
        ),
    })
    passed = all(conditions.values())
    decision = (
        "PASS_EFFECT_WITNESS_DUAL_AXIS_REPLICATION"
        if passed else "REJECT_EFFECT_WITNESS_DUAL_AXIS_REPLICATION"
    )
    state = (
        "EFFECT_WITNESS_DUAL_AXIS_REPLICATED_READY_POSTHOC"
        if passed else "EFFECT_WITNESS_DUAL_AXIS_REJECTED_STOP"
    )
    commitment = {
        name: copy.deepcopy(value)
        for name, value in base.items() if name != "artifact_hash"
    }
    commitment.update({
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "relation_stability_metrics": measured,
        "effect_witness_metrics": {
            "effect_lane_accepted_count": effect_accepted,
            "independent_witness_activation_count": effect_witnessed,
            "provider_calls_added": 0,
        },
        "conditions": conditions,
        "decision": decision,
        "candidate_state": state,
        "effect_witness_gate": "PASS" if passed else "REJECT",
        "core_integration_authorized": False,
    })
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _validate_hash(value):
    field = "run_hash" if "run_hash" in value else "artifact_hash"
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError("effect_witness_source_hash_invalid")
