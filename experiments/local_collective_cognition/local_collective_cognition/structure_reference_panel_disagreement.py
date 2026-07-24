"""Extract GPT/Gemini disagreements into an identity-blind Kimi K3 pack."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structure_reference_panel_contracts import (
    ADJUDICATION_VERSION, JUDGE_CRITERIA, K3_SPEC, PANEL_VERSION,
    adjudication_response_contract, validate_annotation_response,
)
from .structure_reference_panel_pack import validate_reference_panel
from .structure_semantic_judge_contracts import RUBRIC


def build_adjudication_bundle(*, packs, panel_manifest, responses):
    packs = tuple(packs)
    responses = tuple(responses)
    validate_reference_panel(packs=packs, manifest=panel_manifest)
    pack_index = {pack["lane_id"]: pack for pack in packs}
    response_index = {response.get("lane_id"): response for response in responses}
    if set(response_index) != set(pack_index) or len(responses) != len(pack_index):
        raise ValueError("reference_annotation_lane_responses_invalid")
    for lane_id, response in response_index.items():
        validate_annotation_response(response, pack=pack_index[lane_id])
    labels = {lane: _label_index(response) for lane, response in response_index.items()}
    lanes = sorted(pack_index)
    public_items, agreements, private_bindings = [], [], {}
    first_bindings = panel_manifest["private_lane_bindings"][lanes[0]]
    for annotation_id, blind_id in sorted(first_bindings.items(), key=lambda item: item[1]):
        lane_ids = {lane: _annotation_for(panel_manifest, lane, blind_id) for lane in lanes}
        source_item = _public_item(pack_index[lanes[0]], annotation_id)
        for criterion in JUDGE_CRITERIA:
            states = {lane: labels[lane][lane_ids[lane]]["criteria"][criterion] for lane in lanes}
            notes = {lane: labels[lane][lane_ids[lane]]["criterion_notes"][criterion] for lane in lanes}
            confidences = {lane: labels[lane][lane_ids[lane]]["confidence"] for lane in lanes}
            if len(set(states.values())) == 1:
                agreements.append({
                    "blind_candidate_id": blind_id, "criterion": criterion,
                    "selected_state": next(iter(states.values())),
                    "lane_annotation_ids": lane_ids, "lane_confidences": confidences,
                })
                continue
            adjudication_id = "adjudication-" + hash_payload([
                ADJUDICATION_VERSION, panel_manifest["panel_id"], blind_id, criterion,
            ])[:18]
            ordered = sorted(lanes, key=lambda lane: hash_payload([adjudication_id, lane]))
            positions = [{
                "position_id": f"POSITION_{index + 1}", "state": states[lane],
                "criterion_note": notes[lane],
            } for index, lane in enumerate(ordered)]
            public_items.append({
                "adjudication_id": adjudication_id,
                "public_prompt": source_item["public_prompt"],
                "contrastive_packet": source_item["contrastive_packet"],
                "criterion": criterion, "criterion_definition": RUBRIC[criterion],
                "positions": positions,
            })
            private_bindings[adjudication_id] = {
                "blind_candidate_id": blind_id, "criterion": criterion,
                "position_lanes": {
                    f"POSITION_{index + 1}": lane for index, lane in enumerate(ordered)
                },
                "lane_annotation_ids": lane_ids,
            }
    public_items.sort(key=lambda item: hash_payload([panel_manifest["panel_id"], item["adjudication_id"]]))
    pack_commitment = {
        "panel_version": PANEL_VERSION, "adjudication_version": ADJUDICATION_VERSION,
        "panel_id": panel_manifest["panel_id"],
        "expected_adjudicator": {"provider": K3_SPEC[0], "model": K3_SPEC[1]},
        "annotator_identity": "WITHHELD", "source_identity": "WITHHELD",
        "instructions": (
            "Adjudicate only the displayed criterion from the prompt and packet. Positions are anonymous. "
            "Select a position when justified, independently reassess when both are weak, and preserve "
            "UNCERTAIN with UNRESOLVED when evidence cannot decide. Do not claim ground-truth authority."
        ),
        "items": public_items, "response_contract": adjudication_response_contract(),
    }
    pack = {**pack_commitment, "pack_hash": hash_payload(pack_commitment)}
    manifest_commitment = {
        "panel_version": PANEL_VERSION, "adjudication_version": ADJUDICATION_VERSION,
        "panel_id": panel_manifest["panel_id"], "panel_manifest_hash": panel_manifest["manifest_hash"],
        "annotation_response_hashes": {
            lane: hash_payload(response_index[lane]) for lane in lanes
        },
        "adjudication_pack_hash": pack["pack_hash"], "agreement_records": agreements,
        "private_disagreement_bindings": private_bindings,
        "agreement_count": len(agreements), "disagreement_count": len(public_items),
        "total_label_count": len(agreements) + len(public_items),
        "reference_state": "AWAITING_KIMI_K3_ADJUDICATION" if public_items else "PANEL_AGREEMENT_COMPLETE",
        "ground_truth_claim": False, "retention_authority": False,
    }
    manifest = {**manifest_commitment, "manifest_hash": hash_payload(manifest_commitment)}
    return pack, manifest


def validate_adjudication_bundle(*, pack, manifest, panel_packs=None,
                                 panel_manifest=None, responses=None):
    pack_commitment = {key: value for key, value in pack.items() if key != "pack_hash"}
    manifest_commitment = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if pack.get("pack_hash") != hash_payload(pack_commitment):
        raise ValueError("reference_adjudication_pack_hash_invalid")
    if manifest.get("manifest_hash") != hash_payload(manifest_commitment):
        raise ValueError("reference_adjudication_manifest_hash_invalid")
    if (manifest.get("adjudication_pack_hash") != pack["pack_hash"]
            or set(manifest["private_disagreement_bindings"])
            != {item["adjudication_id"] for item in pack["items"]}
            or manifest["agreement_count"] != len(manifest["agreement_records"])
            or manifest["disagreement_count"] != len(pack["items"])
            or manifest["total_label_count"] != (
                manifest["agreement_count"] + manifest["disagreement_count"]
            )
            or manifest["total_label_count"] != len(JUDGE_CRITERIA) * len({
                item["blind_candidate_id"] for item in manifest["agreement_records"]
            } | {
                item["blind_candidate_id"]
                for item in manifest["private_disagreement_bindings"].values()
            })):
        raise ValueError("reference_adjudication_bundle_binding_invalid")
    supplied = (panel_packs, panel_manifest, responses)
    if any(item is not None for item in supplied):
        if not all(item is not None for item in supplied):
            raise ValueError("reference_adjudication_rebuild_inputs_incomplete")
        expected = build_adjudication_bundle(
            packs=panel_packs, panel_manifest=panel_manifest, responses=responses,
        )
        if (pack, manifest) != expected:
            raise ValueError("reference_adjudication_bundle_semantics_invalid")


def _label_index(response):
    return {label["annotation_id"]: label for label in response["labels"]}


def _annotation_for(manifest, lane, blind_id):
    matches = [key for key, value in manifest["private_lane_bindings"][lane].items() if value == blind_id]
    if len(matches) != 1:
        raise ValueError("reference_annotation_reverse_binding_invalid")
    return matches[0]


def _public_item(pack, annotation_id):
    return next(item for item in pack["items"] if item["annotation_id"] == annotation_id)
