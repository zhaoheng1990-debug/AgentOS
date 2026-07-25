"""Blinded GPT/Gemini typed-evidence panel for Admission V2."""

from __future__ import annotations

from .admission_v2_annotation_rubric import (
    EFFECT_BASIS_CODES,
    LANE_SPECS,
    PANEL_VERSION,
    RUBRIC,
    label_violations,
)
from .admission_v2_calibration import validate_calibration_projection
from .provider_telemetry import hash_payload


def build_external_panel(*, panel, run, score, decision):
    validate_calibration_projection(panel)
    _validate_hash(run, "run_hash")
    _validate_hash(score, "artifact_hash")
    _validate_hash(decision, "artifact_hash")
    if (
        run["source_panel_hash"] != panel["artifact_hash"]
        or score["source_panel_hash"] != panel["artifact_hash"]
        or decision["source_score_hash"] != score["artifact_hash"]
        or decision["decision"] != "REJECT_ADMISSION_V2_CALIBRATION"
    ):
        raise ValueError("admission_v2_external_source_lineage_invalid")
    panel_id = "admission-v2-panel-" + hash_payload([
        PANEL_VERSION,
        panel["artifact_hash"],
        run["run_hash"],
        score["artifact_hash"],
    ])[:18]
    public_units = _public_units(panel)
    packs, lane_bindings = [], {}
    for lane_id, provider, model in LANE_SPECS:
        items, bindings = [], {}
        for unit in public_units:
            annotation_id = "admission-v2-annotation-" + hash_payload([
                PANEL_VERSION,
                panel_id,
                lane_id,
                unit["case_id"],
                unit["span_id"],
            ])[:20]
            items.append({
                "annotation_id": annotation_id,
                "target_object": unit["target_object"],
                "target_span_text": unit["target_span_text"],
                "independent_span_assessment": True,
            })
            bindings[annotation_id] = {
                "case_id": unit["case_id"],
                "span_id": unit["span_id"],
            }
        items.sort(
            key=lambda value: hash_payload([
                lane_id,
                value["annotation_id"],
            ])
        )
        value = {
            "panel_version": PANEL_VERSION,
            "panel_id": panel_id,
            "lane_id": lane_id,
            "expected_annotator": {
                "provider": provider,
                "model": model,
            },
            "source_case_ids": "WITHHELD",
            "source_span_ids": "WITHHELD",
            "benchmark_gold": "WITHHELD",
            "candidate_system_outputs": "WITHHELD",
            "peer_annotation": "WITHHELD",
            "rubric": RUBRIC,
            "instructions": (
                "Assess each target span independently against the supplied "
                "intervention-comparator-outcome object. Do not choose a "
                "minimal evidence set and do not demote valid evidence because "
                "another span may be shorter. Null/no-difference, uncertainty, "
                "significance, and quantitative corroboration can all be "
                "effect-bearing. Return exactly one compatible typed label per "
                "annotation_id."
            ),
            "items": items,
            "response_contract": annotation_response_contract(),
        }
        packs.append({**value, "pack_hash": hash_payload(value)})
        lane_bindings[lane_id] = bindings
    manifest_value = {
        "panel_version": PANEL_VERSION,
        "panel_id": panel_id,
        "source_panel_hash": panel["artifact_hash"],
        "frozen_candidate_run_hash": run["run_hash"],
        "source_score_hash": score["artifact_hash"],
        "source_decision_hash": decision["artifact_hash"],
        "candidate_outputs_frozen_before_panel": True,
        "candidate_outputs_exposed_to_annotators": False,
        "benchmark_gold_exposed_to_annotators": False,
        "lane_pack_hashes": {
            pack["lane_id"]: pack["pack_hash"] for pack in packs
        },
        "private_lane_bindings": lane_bindings,
        "case_count": panel["case_count"],
        "span_count": len(public_units),
        "current_phase": "AWAITING_GPT_GEMINI_TYPED_ANNOTATIONS",
        "v0_75_holdout_reused": False,
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return tuple(packs), {
        **manifest_value,
        "manifest_hash": hash_payload(manifest_value),
    }


def validate_external_panel(*, packs, manifest, source_inputs=None):
    packs = tuple(packs)
    _validate_hash(manifest, "manifest_hash")
    observed = {
        (
            pack.get("lane_id"),
            pack.get("expected_annotator", {}).get("provider"),
            pack.get("expected_annotator", {}).get("model"),
        )
        for pack in packs
    }
    if (
        observed != set(LANE_SPECS)
        or manifest.get("candidate_outputs_exposed_to_annotators") is not False
        or manifest.get("benchmark_gold_exposed_to_annotators") is not False
        or manifest.get("v0_75_holdout_reused") is not False
    ):
        raise ValueError("admission_v2_external_manifest_invalid")
    lane_ids = []
    for pack in packs:
        _validate_hash(pack, "pack_hash")
        ids = {
            item.get("annotation_id") for item in pack.get("items", [])
        }
        if (
            pack["pack_hash"]
            != manifest["lane_pack_hashes"].get(pack["lane_id"])
            or len(ids) != manifest["span_count"]
            or ids
            != set(manifest["private_lane_bindings"][pack["lane_id"]])
        ):
            raise ValueError("admission_v2_external_pack_invalid")
        forbidden = (
            "private_gold",
            "gold_rationale",
            "predicted_label",
            "calibration_candidate_run",
            "deepseek",
        )
        if any(value in str(pack).casefold() for value in forbidden):
            raise ValueError("admission_v2_external_pack_leak")
        lane_ids.append(ids)
    if lane_ids[0] & lane_ids[1]:
        raise ValueError("admission_v2_external_lane_id_collision")
    if source_inputs is not None and (packs, manifest) != (
        build_external_panel(**source_inputs)
    ):
        raise ValueError("admission_v2_external_panel_not_deterministic")


def annotation_response_contract():
    return {
        "required_top_level": [
            "panel_version",
            "panel_id",
            "lane_id",
            "pack_hash",
            "annotator_provider",
            "annotator_model",
            "annotation_session_ref",
            "blinding_attestation",
            "labels",
        ],
        "required_label_fields": [
            "annotation_id",
            "object_relation",
            "evidence_utility",
            "disposition",
            "effect_basis_codes",
            "confidence",
            "rationale",
        ],
        "allowed_effect_basis_codes": list(EFFECT_BASIS_CODES),
        "required_blinding_attestation": {
            "pack_only_context": True,
            "source_case_ids_unavailable": True,
            "source_span_ids_unavailable": True,
            "benchmark_gold_unavailable": True,
            "peer_annotation_unavailable": True,
            "candidate_system_outputs_unavailable": True,
        },
    }


def validate_annotation_response(response, *, pack):
    contract = annotation_response_contract()
    expected = {
        "panel_version": PANEL_VERSION,
        "panel_id": pack["panel_id"],
        "lane_id": pack["lane_id"],
        "pack_hash": pack["pack_hash"],
        "annotator_provider": pack["expected_annotator"]["provider"],
        "annotator_model": pack["expected_annotator"]["model"],
    }
    if (
        not isinstance(response, dict)
        or set(response) != set(contract["required_top_level"])
        or any(response.get(key) != value for key, value in expected.items())
        or response.get("blinding_attestation")
        != contract["required_blinding_attestation"]
        or not isinstance(response.get("annotation_session_ref"), str)
        or not response["annotation_session_ref"].strip()
    ):
        raise ValueError("admission_v2_annotation_response_binding_invalid")
    expected_ids = {
        item["annotation_id"] for item in pack["items"]
    }
    labels = response.get("labels")
    if not isinstance(labels, list) or len(labels) != len(expected_ids):
        raise ValueError("admission_v2_annotation_response_count_invalid")
    observed = []
    for label in labels:
        if (
            not isinstance(label, dict)
            or set(label) != set(contract["required_label_fields"])
        ):
            raise ValueError("admission_v2_annotation_label_shape_invalid")
        observed.append(label["annotation_id"])
        if (
            label_violations(label)
            or not _confidence(label.get("confidence"))
            or not isinstance(label.get("rationale"), str)
            or not label["rationale"].strip()
            or len(label["rationale"]) > 1200
        ):
            raise ValueError("admission_v2_annotation_label_invalid")
    if len(observed) != len(set(observed)) or set(observed) != expected_ids:
        raise ValueError("admission_v2_annotation_ids_invalid")


def _public_units(panel):
    return [
        {
            "case_id": item["case_id"],
            "span_id": span["span_id"],
            "target_object": item["object"],
            "target_span_text": span["text"],
        }
        for item in panel["public_surface"]["items"]
        for span in item["candidate_spans"]
    ]


def _validate_hash(value, field):
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError(f"admission_v2_external_{field}_invalid")


def _confidence(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 <= value <= 1
    )
