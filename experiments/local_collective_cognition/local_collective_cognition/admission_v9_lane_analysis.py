"""Paired lane-agreement analysis for ternary boundary review v0.84."""

from __future__ import annotations

from collections import Counter

from .admission_v9_external_adjudication import validate_adjudication
from .admission_v9_external_panel import (
    validate_annotation_response,
    validate_external_panel,
)
from .provider_telemetry import hash_payload


def build_lane_agreement_analysis(
    *,
    packs,
    panel_manifest,
    responses,
    adjudication_pack,
    adjudication_manifest,
    evaluation,
):
    packs, responses = tuple(packs), tuple(responses)
    validate_external_panel(packs=packs, manifest=panel_manifest)
    pack_index = {pack["lane_id"]: pack for pack in packs}
    response_index = {
        response["lane_id"]: response for response in responses
    }
    if set(pack_index) != set(response_index):
        raise ValueError("admission_v9_lane_analysis_lane_mismatch")
    for lane_id, response in response_index.items():
        validate_annotation_response(response, pack=pack_index[lane_id])
    validate_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
    )
    _validate_hash(evaluation, "artifact_hash")
    agreements = {
        record["unit_key"]: record
        for record in adjudication_manifest["agreement_records"]
    }
    mutation_records = []
    outcomes = Counter()
    for mutation in evaluation["boundary_mutations"]:
        unit_key = f"{mutation['case_id']}::{mutation['span_id']}"
        agreement = agreements.get(unit_key)
        if agreement is None:
            outcome = "PENDING_ADJUDICATION"
            reference_disposition = None
        else:
            reference_disposition = agreement["typed_label"]["disposition"]
            if (
                reference_disposition == mutation["after"]
                and reference_disposition != mutation["before"]
            ):
                outcome = "CORRECTED"
            elif (
                reference_disposition == mutation["before"]
                and reference_disposition != mutation["after"]
            ):
                outcome = "HARMED"
            else:
                outcome = "OTHER"
        outcomes[outcome] += 1
        mutation_records.append({
            "case_id": mutation["case_id"],
            "span_id": mutation["span_id"],
            "before": mutation["before"],
            "after": mutation["after"],
            "reference_disposition": reference_disposition,
            "paired_outcome": outcome,
            "reference_basis": (
                "INDEPENDENT_LANE_AGREEMENT" if agreement else None
            ),
        })
    all_resolved = (
        len(mutation_records) > 0
        and outcomes["PENDING_ADJUDICATION"] == 0
    )
    decisive_reject = (
        all_resolved
        and outcomes["CORRECTED"] == 0
        and outcomes["HARMED"] > 0
    )
    lane_dispositions = {
        lane: dict(sorted(Counter(
            label["disposition"] for label in response["labels"]
        ).items()))
        for lane, response in sorted(response_index.items())
    }
    value = {
        "analysis_version": "admission_v9_lane_agreement_v0_84",
        "panel_id": panel_manifest["panel_id"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "source_evaluation_hash": evaluation["artifact_hash"],
        "annotation_response_hashes": {
            lane: hash_payload(response)
            for lane, response in sorted(response_index.items())
        },
        "agreement_count": adjudication_manifest["agreement_count"],
        "disagreement_count": adjudication_manifest["disagreement_count"],
        "total_span_count": adjudication_manifest["total_span_count"],
        "semantic_agreement_rate": (
            adjudication_manifest["agreement_count"]
            / adjudication_manifest["total_span_count"]
        ),
        "lane_disposition_counts": lane_dispositions,
        "mutation_records": mutation_records,
        "mutation_outcome_counts": dict(sorted(outcomes.items())),
        "all_mutations_resolved_by_lane_agreement": all_resolved,
        "candidate_acceptance_authorized": False,
        "mutation_semantic_decision": (
            "REJECT_A18_ALL_MUTATIONS_EXTERNALLY_HARMFUL"
            if decisive_reject
            else "DEFER_MUTATION_DECISION"
        ),
        "full_reference_state": adjudication_manifest["reference_state"],
        "ground_truth_claim": False,
        "runtime_tuning_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def _validate_hash(value, field):
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError(f"admission_v9_lane_analysis_{field}_invalid")
