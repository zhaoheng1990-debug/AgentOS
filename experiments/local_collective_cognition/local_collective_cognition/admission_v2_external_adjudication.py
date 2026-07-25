"""Anonymous Kimi adjudication and typed reference for Admission V2."""

from __future__ import annotations

from .admission_v2_annotation_rubric import (
    ADJUDICATION_VERSION,
    K3_SPEC,
    PANEL_VERSION,
    REFERENCE_VERSION,
    RUBRIC,
    label_violations,
)
from .admission_v2_external_panel import (
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


def build_adjudication(*, packs, panel_manifest, responses):
    packs, responses = tuple(packs), tuple(responses)
    validate_external_panel(packs=packs, manifest=panel_manifest)
    pack_index = {pack["lane_id"]: pack for pack in packs}
    response_index = {
        response.get("lane_id"): response for response in responses
    }
    if (
        len(response_index) != len(responses)
        or set(response_index) != set(pack_index)
    ):
        raise ValueError("admission_v2_annotation_lanes_invalid")
    for lane_id, response in response_index.items():
        validate_annotation_response(
            response,
            pack=pack_index[lane_id],
        )
    lane_labels = _labels_by_unit(
        panel_manifest=panel_manifest,
        responses=response_index,
    )
    public_units = _public_units(packs, panel_manifest)
    lanes = sorted(lane_labels)
    agreements, disagreements, bindings = [], [], {}
    for unit_key in sorted(public_units):
        labels = {
            lane: lane_labels[lane][unit_key] for lane in lanes
        }
        semantic = {
            lane: _semantic_label(labels[lane]) for lane in lanes
        }
        annotation_ids = {
            lane: labels[lane]["annotation_id"] for lane in lanes
        }
        if len({hash_payload(value) for value in semantic.values()}) == 1:
            agreements.append({
                "unit_key": unit_key,
                "typed_label": semantic[lanes[0]],
                "lane_annotation_ids": annotation_ids,
                "lane_confidence": {
                    lane: labels[lane]["confidence"] for lane in lanes
                },
            })
            continue
        adjudication_id = "admission-v2-adjudication-" + hash_payload([
            ADJUDICATION_VERSION,
            panel_manifest["panel_id"],
            unit_key,
        ])[:20]
        ordered = sorted(
            lanes,
            key=lambda lane: hash_payload([adjudication_id, lane]),
        )
        positions = []
        for index, lane in enumerate(ordered, start=1):
            label = labels[lane]
            positions.append({
                "position_id": f"POSITION_{index}",
                **_semantic_label(label),
                "confidence": label["confidence"],
                "rationale": label["rationale"],
            })
        unit = public_units[unit_key]
        disagreements.append({
            "adjudication_id": adjudication_id,
            "target_object": unit["target_object"],
            "target_span_text": unit["target_span_text"],
            "independent_span_assessment": True,
            "anonymous_positions": positions,
        })
        bindings[adjudication_id] = {
            "unit_key": unit_key,
            "position_lanes": {
                f"POSITION_{index}": lane
                for index, lane in enumerate(ordered, start=1)
            },
            "lane_annotation_ids": annotation_ids,
        }
    disagreements.sort(
        key=lambda value: hash_payload([
            panel_manifest["panel_id"],
            value["adjudication_id"],
        ])
    )
    pack_value = {
        "panel_version": PANEL_VERSION,
        "adjudication_version": ADJUDICATION_VERSION,
        "panel_id": panel_manifest["panel_id"],
        "expected_adjudicator": {
            "provider": K3_SPEC[0],
            "model": K3_SPEC[1],
        },
        "annotator_identity": "WITHHELD",
        "benchmark_gold": "WITHHELD",
        "candidate_system_outputs": "WITHHELD",
        "rubric": RUBRIC,
        "instructions": (
            "Adjudicate each target span independently. Select an anonymous "
            "position only if its complete typed label is correct; otherwise "
            "use INDEPENDENT_REASSESSMENT. Null/no-difference, uncertainty, "
            "significance, and quantitative corroboration may be "
            "effect-bearing. Do not infer a final outcome label."
        ),
        "items": disagreements,
        "response_contract": adjudication_response_contract(),
    }
    pack = {**pack_value, "pack_hash": hash_payload(pack_value)}
    manifest_value = {
        "panel_version": PANEL_VERSION,
        "adjudication_version": ADJUDICATION_VERSION,
        "panel_id": panel_manifest["panel_id"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "annotation_response_hashes": {
            lane: hash_payload(response_index[lane])
            for lane in sorted(response_index)
        },
        "adjudication_pack_hash": pack["pack_hash"],
        "agreement_records": agreements,
        "private_disagreement_bindings": bindings,
        "agreement_count": len(agreements),
        "disagreement_count": len(disagreements),
        "total_span_count": (
            len(agreements) + len(disagreements)
        ),
        "reference_state": (
            "AWAITING_KIMI_K3_TYPED_ADJUDICATION"
            if disagreements
            else "REFERENCE_READY_FROM_LANE_AGREEMENT"
        ),
        "annotator_identity_exposed_to_adjudicator": False,
        "benchmark_gold_exposed_to_adjudicator": False,
        "candidate_outputs_exposed_to_adjudicator": False,
        "ground_truth_claim": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return pack, {
        **manifest_value,
        "manifest_hash": hash_payload(manifest_value),
    }


def validate_adjudication(*, pack, manifest, source_inputs=None):
    _validate_hash(pack, "pack_hash")
    _validate_hash(manifest, "manifest_hash")
    ids = {
        item.get("adjudication_id") for item in pack.get("items", [])
    }
    if (
        manifest.get("adjudication_pack_hash") != pack.get("pack_hash")
        or ids
        != set(manifest.get("private_disagreement_bindings", {}))
        or manifest["agreement_count"] + manifest["disagreement_count"]
        != manifest["total_span_count"]
        or manifest.get("annotator_identity_exposed_to_adjudicator")
        is not False
        or manifest.get("benchmark_gold_exposed_to_adjudicator") is not False
        or manifest.get("candidate_outputs_exposed_to_adjudicator") is not False
    ):
        raise ValueError("admission_v2_adjudication_invalid")
    forbidden = (
        "gpt-5.6",
        "gemini-3.1",
        "openai",
        "google",
        "deepseek",
    )
    if any(value in str(pack).casefold() for value in forbidden):
        raise ValueError("admission_v2_adjudication_identity_leak")
    for item in pack["items"]:
        if {
            position["position_id"]
            for position in item["anonymous_positions"]
        } != {"POSITION_1", "POSITION_2"}:
            raise ValueError("admission_v2_adjudication_positions_invalid")
    if source_inputs is not None and (pack, manifest) != (
        build_adjudication(**source_inputs)
    ):
        raise ValueError("admission_v2_adjudication_not_deterministic")


def adjudication_response_contract():
    return {
        "required_top_level": [
            "panel_version",
            "adjudication_version",
            "panel_id",
            "adjudication_pack_hash",
            "adjudicator_provider",
            "adjudicator_model",
            "adjudication_session_ref",
            "blinding_attestation",
            "decisions",
        ],
        "required_decision_fields": [
            "adjudication_id",
            *LABEL_FIELDS,
            "decision_basis",
            "confidence",
            "rationale",
        ],
        "allowed_decision_bases": [
            "POSITION_1",
            "POSITION_2",
            "INDEPENDENT_REASSESSMENT",
        ],
        "required_blinding_attestation": {
            "pack_only_context": True,
            "annotator_identity_unavailable": True,
            "benchmark_gold_unavailable": True,
            "candidate_system_outputs_unavailable": True,
        },
    }


def validate_adjudication_response(response, *, pack):
    contract = adjudication_response_contract()
    expected = {
        "panel_version": PANEL_VERSION,
        "adjudication_version": ADJUDICATION_VERSION,
        "panel_id": pack["panel_id"],
        "adjudication_pack_hash": pack["pack_hash"],
        "adjudicator_provider": K3_SPEC[0],
        "adjudicator_model": K3_SPEC[1],
    }
    if (
        not isinstance(response, dict)
        or set(response) != set(contract["required_top_level"])
        or any(response.get(key) != value for key, value in expected.items())
        or response.get("blinding_attestation")
        != contract["required_blinding_attestation"]
        or not isinstance(response.get("adjudication_session_ref"), str)
        or not response["adjudication_session_ref"].strip()
    ):
        raise ValueError("admission_v2_adjudication_response_binding_invalid")
    item_index = {
        item["adjudication_id"]: item for item in pack["items"]
    }
    decisions = response.get("decisions")
    if (
        not isinstance(decisions, list)
        or len(decisions) != len(item_index)
    ):
        raise ValueError("admission_v2_adjudication_response_count_invalid")
    observed = []
    for decision in decisions:
        if (
            not isinstance(decision, dict)
            or set(decision) != set(contract["required_decision_fields"])
        ):
            raise ValueError("admission_v2_adjudication_decision_shape_invalid")
        adjudication_id = decision["adjudication_id"]
        observed.append(adjudication_id)
        item = item_index.get(adjudication_id)
        if (
            item is None
            or label_violations(decision)
            or decision.get("decision_basis")
            not in contract["allowed_decision_bases"]
            or not _confidence(decision.get("confidence"))
            or not isinstance(decision.get("rationale"), str)
            or not decision["rationale"].strip()
            or len(decision["rationale"]) > 1200
        ):
            raise ValueError("admission_v2_adjudication_decision_invalid")
        positions = {
            position["position_id"]: _semantic_label(position)
            for position in item["anonymous_positions"]
        }
        basis = decision["decision_basis"]
        if basis in positions and _semantic_label(decision) != positions[basis]:
            raise ValueError("admission_v2_adjudication_position_mismatch")
    if len(observed) != len(set(observed)) or set(observed) != set(item_index):
        raise ValueError("admission_v2_adjudication_ids_invalid")


def build_typed_reference(
    *,
    panel_manifest,
    adjudication_pack,
    adjudication_manifest,
    adjudication_response=None,
):
    validate_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
    )
    if adjudication_pack["items"]:
        if adjudication_response is None:
            raise ValueError("admission_v2_adjudication_response_required")
        validate_adjudication_response(
            adjudication_response,
            pack=adjudication_pack,
        )
    decisions = {
        value["adjudication_id"]: value
        for value in (
            adjudication_response or {"decisions": []}
        )["decisions"]
    }
    labels = []
    lane_bindings = panel_manifest["private_lane_bindings"]
    canonical_lane = sorted(lane_bindings)[0]
    for agreement in adjudication_manifest["agreement_records"]:
        binding = _unit_binding(
            lane_bindings,
            canonical_lane,
            agreement["lane_annotation_ids"][canonical_lane],
        )
        labels.append({
            **binding,
            **agreement["typed_label"],
            "reference_basis": "INDEPENDENT_LANE_AGREEMENT",
        })
    for adjudication_id, binding in adjudication_manifest[
        "private_disagreement_bindings"
    ].items():
        decision = decisions[adjudication_id]
        unit = _unit_binding(
            lane_bindings,
            canonical_lane,
            binding["lane_annotation_ids"][canonical_lane],
        )
        labels.append({
            **unit,
            **_semantic_label(decision),
            "reference_basis": "KIMI_K3_ADJUDICATION",
        })
    labels.sort(key=lambda value: (value["case_id"], value["span_id"]))
    value = {
        "reference_version": REFERENCE_VERSION,
        "panel_id": panel_manifest["panel_id"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "adjudication_manifest_hash": (
            adjudication_manifest["manifest_hash"]
        ),
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_response_hash": (
            hash_payload(adjudication_response)
            if adjudication_response is not None
            else None
        ),
        "labels": labels,
        "label_count": len(labels),
        "reference_status": "EXTERNAL_TYPED_REFERENCE_CANDIDATE",
        "ground_truth_claim": False,
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


def _public_units(packs, manifest):
    lane = packs[0]["lane_id"]
    bindings = manifest["private_lane_bindings"][lane]
    return {
        _unit_key(bindings[item["annotation_id"]]): {
            "target_object": item["target_object"],
            "target_span_text": item["target_span_text"],
        }
        for item in packs[0]["items"]
    }


def _semantic_label(value):
    return {field: value[field] for field in LABEL_FIELDS}


def _unit_key(binding):
    return f"{binding['case_id']}::{binding['span_id']}"


def _unit_binding(lane_bindings, lane, annotation_id):
    return lane_bindings[lane][annotation_id]


def _validate_hash(value, field):
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError(f"admission_v2_{field}_invalid")


def _confidence(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 <= value <= 1
    )
