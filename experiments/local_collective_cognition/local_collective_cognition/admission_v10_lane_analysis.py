"""Selective external lane analysis for v0.85."""

from __future__ import annotations

from .admission_v10_external_panel import (
    validate_annotation_response,
    validate_external_panel,
)
from .provider_telemetry import hash_payload


LABEL_FIELDS = (
    "object_relation",
    "evidence_utility",
    "disposition",
    "effect_basis_codes",
)


def build_lane_analysis(
    *,
    packs,
    panel_manifest,
    responses,
    evaluation,
):
    packs, responses = tuple(packs), tuple(responses)
    validate_external_panel(packs=packs, manifest=panel_manifest)
    pack_index = {pack["lane_id"]: pack for pack in packs}
    response_index = {
        response["lane_id"]: response for response in responses
    }
    if set(pack_index) != set(response_index):
        raise ValueError("admission_v10_lane_analysis_lane_mismatch")
    for lane_id, response in response_index.items():
        validate_annotation_response(response, pack=pack_index[lane_id])
    _validate_hash(evaluation, "artifact_hash")
    lane_labels = _labels_by_unit(
        panel_manifest=panel_manifest,
        responses=response_index,
    )
    lanes = sorted(lane_labels)
    unit_keys = sorted(set.intersection(*(
        set(labels) for labels in lane_labels.values()
    )))
    agreements, disagreements = [], []
    for unit_key in unit_keys:
        labels = {lane: lane_labels[lane][unit_key] for lane in lanes}
        semantic = {
            lane: _semantic_label(labels[lane]) for lane in lanes
        }
        if len({hash_payload(value) for value in semantic.values()}) == 1:
            agreements.append({
                "unit_key": unit_key,
                "typed_label": semantic[lanes[0]],
                "lane_confidence": {
                    lane: labels[lane]["confidence"] for lane in lanes
                },
            })
        else:
            disagreements.append({
                "unit_key": unit_key,
                "anonymous_semantic_positions": [
                    semantic[lane] for lane in sorted(
                        lanes,
                        key=lambda value: hash_payload([unit_key, value]),
                    )
                ],
                "decision_relevance": "UNCHANGED_CONTROL_ONLY",
            })
    agreement_index = {
        value["unit_key"]: value for value in agreements
    }
    mutation_records = []
    for mutation in evaluation["relation_mutations"]:
        unit_key = f"{mutation['case_id']}::{mutation['span_id']}"
        agreement = agreement_index.get(unit_key)
        reference = (
            agreement["typed_label"]["disposition"] if agreement else None
        )
        if reference == mutation["before"] and reference != mutation["after"]:
            outcome = "HARMED"
        elif reference == mutation["after"] and reference != mutation["before"]:
            outcome = "CORRECTED"
        else:
            outcome = "PENDING_OR_OTHER"
        mutation_records.append({
            "case_id": mutation["case_id"],
            "span_id": mutation["span_id"],
            "before": mutation["before"],
            "after": mutation["after"],
            "external_lane_disposition": reference,
            "paired_outcome": outcome,
        })
    corrected = sum(
        value["paired_outcome"] == "CORRECTED"
        for value in mutation_records
    )
    harmed = sum(
        value["paired_outcome"] == "HARMED"
        for value in mutation_records
    )
    unresolved = len(mutation_records) - corrected - harmed
    value = {
        "analysis_version": "admission_v10_lane_analysis_v0_85",
        "panel_id": panel_manifest["panel_id"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "source_evaluation_hash": evaluation["artifact_hash"],
        "annotation_response_hashes": {
            lane: hash_payload(response)
            for lane, response in sorted(response_index.items())
        },
        "agreement_count": len(agreements),
        "disagreement_count": len(disagreements),
        "total_span_count": len(unit_keys),
        "agreement_records": agreements,
        "unresolved_control_records": disagreements,
        "mutation_records": mutation_records,
        "mutation_outcome_counts": {
            "CORRECTED": corrected,
            "HARMED": harmed,
            "UNRESOLVED": unresolved,
        },
        "all_mutations_resolved_by_lane_agreement": unresolved == 0,
        "control_adjudication_required_for_mechanism_decision": False,
        "mechanism_decision": (
            "REJECT_A19_ALL_MUTATIONS_EXTERNALLY_HARMFUL"
            if corrected == 0 and harmed > 0 and unresolved == 0
            else "DEFER_A19_MUTATION_DECISION"
        ),
        "full_reference_claim": False,
        "external_acceptance_eligible": False,
        "candidate_acceptance_authorized": False,
        "runtime_tuning_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def _labels_by_unit(*, panel_manifest, responses):
    result = {}
    for lane, response in responses.items():
        bindings = panel_manifest["private_lane_bindings"][lane]
        result[lane] = {
            _unit_key(bindings[label["annotation_id"]]): label
            for label in response["labels"]
        }
    return result


def _semantic_label(value):
    return {field: value[field] for field in LABEL_FIELDS}


def _unit_key(binding):
    return f"{binding['case_id']}::{binding['span_id']}"


def _validate_hash(value, field):
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError(f"admission_v10_lane_analysis_{field}_invalid")
