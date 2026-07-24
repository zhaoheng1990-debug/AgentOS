"""Validate and preserve identity-aware adjudication as non-authoritative shadow evidence."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structure_reference_panel_contracts import JUDGE_CRITERIA, JUDGE_STATES
from .structure_reference_panel_disagreement import validate_adjudication_bundle


PROTOCOL_FAILURES = (
    "ADJUDICATION_PACK_HASH_MISSING",
    "ADJUDICATION_IDS_MISSING",
    "DECISION_CONFIDENCE_MISSING",
    "BLINDING_ATTESTATION_MISSING",
    "ANNOTATOR_IDENTITIES_EXPOSED",
    "EXTERNAL_CONTENT_PAIRING_USED",
)


def build_shadow_reference(*, record, source_file_sha256, adjudication_pack,
                           adjudication_manifest, panel_packs, panel_manifest,
                           annotation_responses):
    validate_adjudication_bundle(
        pack=adjudication_pack, manifest=adjudication_manifest,
        panel_packs=panel_packs, panel_manifest=panel_manifest,
        responses=annotation_responses,
    )
    _validate_record_header(record, panel_manifest, panel_packs)
    labels = {
        response["lane_id"]: {item["annotation_id"]: item for item in response["labels"]}
        for response in annotation_responses
    }
    packet_bindings = _packet_bindings(record, panel_manifest)
    item_index = {item["adjudication_id"]: item for item in adjudication_pack["items"]}
    expected = {
        (binding["blind_candidate_id"], binding["criterion"]): (adjudication_id, binding)
        for adjudication_id, binding in adjudication_manifest["private_disagreement_bindings"].items()
    }
    decisions = []
    for dispute in record["dispute_adjudications"]:
        blind_id = packet_bindings[dispute["packet_key"]]["blind_candidate_id"]
        key = (blind_id, dispute["criterion"])
        if key not in expected:
            raise ValueError("shadow_adjudication_unexpected_dispute")
        adjudication_id, binding = expected[key]
        states = {
            lane: labels[lane][binding["lane_annotation_ids"][lane]]["criteria"][dispute["criterion"]]
            for lane in labels
        }
        if (dispute["lane_a_label"] != states["annotation-lane-a"]
                or dispute["lane_b_label"] != states["annotation-lane-b"]
                or dispute["final_label"] not in JUDGE_STATES):
            raise ValueError("shadow_adjudication_source_label_invalid")
        positions = {item["state"]: item["position_id"] for item in item_index[adjudication_id]["positions"]}
        if dispute["final_label"] not in positions:
            raise ValueError("shadow_adjudication_final_label_invalid")
        decisions.append({
            "adjudication_id": adjudication_id, "blind_candidate_id": blind_id,
            "criterion": dispute["criterion"], "selected_state": dispute["final_label"],
            "matching_position": positions[dispute["final_label"]],
            "rationale": dispute["rationale"], "confidence": None,
        })
    if {(item["blind_candidate_id"], item["criterion"]) for item in decisions} != set(expected):
        raise ValueError("shadow_adjudication_dispute_surface_incomplete")
    cells = _merged_cells(adjudication_manifest, decisions)
    _validate_final_labels(record, packet_bindings, cells)
    criteria_by_candidate = [{
        "blind_candidate_id": blind_id,
        "criteria": {criterion: cells[(blind_id, criterion)] for criterion in JUDGE_CRITERIA},
    } for blind_id in sorted({key[0] for key in cells})]
    declared_commitment = {key: value for key, value in record.items() if key != "content_hash_sha256"}
    commitment = {
        "panel_id": panel_manifest["panel_id"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "source_file_sha256": source_file_sha256,
        "source_declared_content_hash": record.get("content_hash_sha256", ""),
        "source_canonical_content_hash": hash_payload(declared_commitment),
        "source_declared_hash_verified": (
            record.get("content_hash_sha256") == hash_payload(declared_commitment)
        ),
        "agreement_count": adjudication_manifest["agreement_count"],
        "disagreement_count": len(decisions), "label_count": len(cells),
        "shadow_decisions": sorted(decisions, key=lambda item: item["adjudication_id"]),
        "labels": criteria_by_candidate,
        "semantic_content_consistent": True, "protocol_compliant": False,
        "protocol_failures": list(PROTOCOL_FAILURES),
        "candidate_state": "IDENTITY_AWARE_SHADOW_REFERENCE_CANDIDATE",
        "ground_truth_claim": False, "human_gold_claim": False,
        "selection_authority": False, "retention_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_shadow_reference(artifact, **build_inputs):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("shadow_reference_artifact_hash_invalid")
    if artifact != build_shadow_reference(**build_inputs):
        raise ValueError("shadow_reference_artifact_semantics_invalid")


def _validate_record_header(record, manifest, packs):
    if (record.get("panel_id") != manifest["panel_id"]
            or record.get("panel_version") != manifest["panel_version"]):
        raise ValueError("shadow_adjudication_panel_binding_invalid")
    expected = {pack["lane_id"]: pack["pack_hash"] for pack in packs}
    observed = {lane["lane_id"]: lane["pack_hash"] for lane in record.get("lanes", {}).values()}
    if observed != expected:
        raise ValueError("shadow_adjudication_lane_binding_invalid")


def _packet_bindings(record, manifest):
    result = {}
    for item in record.get("packet_alignment", []):
        a_id, b_id = item["lane_a_annotation_id"], item["lane_b_annotation_id"]
        a = manifest["private_lane_bindings"]["annotation-lane-a"].get(a_id)
        b = manifest["private_lane_bindings"]["annotation-lane-b"].get(b_id)
        if not a or a != b or item["packet_key"] in result:
            raise ValueError("shadow_adjudication_packet_alignment_invalid")
        result[item["packet_key"]] = {"blind_candidate_id": a}
    if set(item["blind_candidate_id"] for item in result.values()) != set(manifest["private_source_bindings"]):
        raise ValueError("shadow_adjudication_packet_surface_incomplete")
    return result


def _merged_cells(manifest, decisions):
    cells = {
        (item["blind_candidate_id"], item["criterion"]): item["selected_state"]
        for item in manifest["agreement_records"]
    }
    cells.update({(item["blind_candidate_id"], item["criterion"]): item["selected_state"] for item in decisions})
    return cells


def _validate_final_labels(record, packet_bindings, cells):
    observed = {}
    observed_candidates = []
    for item in record.get("final_labels", []):
        blind_id = packet_bindings[item["packet_key"]]["blind_candidate_id"]
        observed_candidates.append(blind_id)
        if set(item["criteria"]) != set(JUDGE_CRITERIA):
            raise ValueError("shadow_adjudication_final_criteria_invalid")
        observed.update({(blind_id, criterion): state for criterion, state in item["criteria"].items()})
    if len(observed_candidates) != len(set(observed_candidates)) or observed != cells:
        raise ValueError("shadow_adjudication_final_surface_invalid")
