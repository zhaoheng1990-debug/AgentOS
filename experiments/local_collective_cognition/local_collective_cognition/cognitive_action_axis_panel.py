"""Candidate-blind external model panel for axis routing v0.17."""

from __future__ import annotations

from .clarification_joint_coordinator_contracts import semantic_tuple_violations
from .clarification_semantic_basis_panel import ALLOWED_STATES, CRITERIA, K3_SPEC, LANE_SPECS, RUBRIC
from .cognitive_action_axis_holdout import validate_axis_routing_holdout
from .cognitive_action_axis_routing import validate_axis_routing_run
from .provider_telemetry import hash_payload


AXIS_PANEL_VERSION = "cognitive_action_axis_external_panel_v0_17"
AXIS_ADJUDICATION_VERSION = "cognitive_action_axis_external_adjudication_v0_17"


def build_axis_external_panel(*, corpus, run):
    validate_axis_routing_holdout(corpus)
    validate_axis_routing_run(corpus=corpus, run=run)
    if run.get("candidate_outputs_frozen_before_external_reference") is not True:
        raise ValueError("axis_panel_candidate_freeze_invalid")
    panel_id = "axis-routing-panel-" + hash_payload([AXIS_PANEL_VERSION, corpus["artifact_hash"], run["run_hash"]])[:16]
    packs, bindings = [], {}
    for lane_id, provider, model in LANE_SPECS:
        items, lane_bindings = [], {}
        for source in corpus["public_surface"]["items"]:
            annotation_id = "axis-routing-annotation-" + hash_payload([AXIS_PANEL_VERSION, panel_id, lane_id, source["conflict_id"]])[:18]
            items.append({
                "annotation_id": annotation_id,
                "public_prompt": source["public_prompt"],
                "candidate_a": source["candidate_a"],
                "candidate_b": source["candidate_b"],
            })
            lane_bindings[annotation_id] = source["conflict_id"]
        items.sort(key=lambda item: hash_payload([AXIS_PANEL_VERSION, lane_id, item["annotation_id"]]))
        commitment = {
            "panel_version": AXIS_PANEL_VERSION,
            "panel_id": panel_id,
            "lane_id": lane_id,
            "expected_annotator": {"provider": provider, "model": model},
            "source_identity": "WITHHELD",
            "object_family": "WITHHELD",
            "peer_annotation": "WITHHELD",
            "candidate_system_outputs": "WITHHELD",
            "construction_labels": "DO_NOT_EXIST",
            "prior_scores": "WITHHELD",
            "item_order": "LANE_SPECIFIC_HASH_RANDOMIZED",
            "rubric": RUBRIC,
            "basis_definitions": {
                "LEXICAL_EXACT": "The prompt directly names or explicitly defines the selected candidate.",
                "COMPOSITIONAL_ENTAILMENT": "The candidate follows from combining prompt constraints without an exact definition.",
                "PRAGMATIC_DEFAULT": "No candidate is entailed, but ordinary context favors one; selected object must be NONE.",
                "NO_PREFERENCE": "No candidate is entailed or contextually favored; selected object and preference must be NONE.",
                "UNCERTAIN": "The displayed surface is internally conflicting or too incomplete to classify.",
            },
            "instructions": (
                "Assess every object independently using only the displayed prompt and candidates. Return one globally coherent "
                "four-criterion tuple per item. Keep semantic entailment separate from contextual preference. A justified open "
                "object can be COMPLETE. Do not infer hidden construction classes or compare objects. Return one JSON object only."
            ),
            "items": items,
            "response_contract": annotation_response_contract(),
        }
        packs.append({**commitment, "pack_hash": hash_payload(commitment)})
        bindings[lane_id] = lane_bindings
    manifest_commitment = {
        "panel_version": AXIS_PANEL_VERSION,
        "panel_id": panel_id,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_surface_hash": corpus["public_surface"]["surface_hash"],
        "frozen_candidate_run_hash": run["run_hash"],
        "candidate_outputs_frozen_before_panel_pack": True,
        "candidate_outputs_exposed_to_annotators": False,
        "lane_pack_hashes": {pack["lane_id"]: pack["pack_hash"] for pack in packs},
        "private_lane_bindings": bindings,
        "candidate_count": len(corpus["public_surface"]["items"]),
        "criterion_count": len(CRITERIA),
        "current_phase": "AWAITING_GPT_GEMINI_COHERENT_FULL_TUPLES",
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return tuple(packs), {**manifest_commitment, "manifest_hash": hash_payload(manifest_commitment)}


def validate_axis_external_panel(*, packs, manifest, corpus=None, run=None):
    packs = tuple(packs)
    commitment = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    expected_lanes = {(lane, provider, model) for lane, provider, model in LANE_SPECS}
    observed_lanes = {
        (pack.get("lane_id"), pack.get("expected_annotator", {}).get("provider"), pack.get("expected_annotator", {}).get("model"))
        for pack in packs
    }
    if (
        manifest.get("manifest_hash") != hash_payload(commitment)
        or manifest.get("panel_version") != AXIS_PANEL_VERSION
        or len(packs) != len(LANE_SPECS)
        or observed_lanes != expected_lanes
        or manifest.get("candidate_outputs_exposed_to_annotators") is not False
        or manifest.get("reference_revision_allowed") is not False
    ):
        raise ValueError("axis_external_panel_manifest_invalid")
    ids_by_lane = []
    for pack in packs:
        pack_commitment = {key: value for key, value in pack.items() if key != "pack_hash"}
        ids = {item.get("annotation_id") for item in pack.get("items", [])}
        if (
            pack.get("pack_hash") != hash_payload(pack_commitment)
            or pack.get("panel_id") != manifest["panel_id"]
            or manifest["lane_pack_hashes"].get(pack["lane_id"]) != pack["pack_hash"]
            or len(ids) != manifest["candidate_count"]
            or ids != set(manifest["private_lane_bindings"].get(pack["lane_id"], {}))
        ):
            raise ValueError("axis_external_panel_pack_invalid")
        public = str(pack).casefold()
        forbidden = ("deepseek-r1", "qwen2.5", "gemma-2", "llama-3.2", "axis_routing_run", "selected_bijective_routing")
        if any(value in public for value in forbidden):
            raise ValueError("axis_external_panel_candidate_leak")
        ids_by_lane.append(ids)
    if len(ids_by_lane) == 2 and ids_by_lane[0] & ids_by_lane[1]:
        raise ValueError("axis_external_panel_lane_alias_collision")
    if any(value is not None for value in (corpus, run)):
        if corpus is None or run is None or (packs, manifest) != build_axis_external_panel(corpus=corpus, run=run):
            raise ValueError("axis_external_panel_semantics_invalid")


def annotation_response_contract():
    return {
        "required_top_level": [
            "panel_version", "panel_id", "lane_id", "pack_hash", "annotator_provider",
            "annotator_model", "annotation_session_ref", "blinding_attestation", "labels",
        ],
        "required_label_fields": [
            "annotation_id", "criteria", "criterion_notes", "criterion_confidence", "tuple_rationale",
        ],
        "criteria": list(CRITERIA),
        "allowed_states": {criterion: list(states) for criterion, states in ALLOWED_STATES.items()},
        "required_blinding_attestation": {
            "pack_only_context": True,
            "source_identity_unavailable": True,
            "object_family_unavailable": True,
            "peer_annotation_unavailable": True,
            "candidate_system_outputs_unavailable": True,
            "construction_labels_do_not_exist": True,
            "prior_scores_unavailable": True,
        },
    }


def validate_axis_annotation_response(response, *, pack):
    contract = annotation_response_contract()
    if not isinstance(response, dict) or set(response) != set(contract["required_top_level"]):
        raise ValueError("axis_annotation_response_shape_invalid")
    expected = {
        "panel_version": AXIS_PANEL_VERSION,
        "panel_id": pack["panel_id"],
        "lane_id": pack["lane_id"],
        "pack_hash": pack["pack_hash"],
        "annotator_provider": pack["expected_annotator"]["provider"],
        "annotator_model": pack["expected_annotator"]["model"],
    }
    if (
        any(response.get(key) != value for key, value in expected.items())
        or response.get("blinding_attestation") != contract["required_blinding_attestation"]
        or not isinstance(response.get("annotation_session_ref"), str)
        or not response["annotation_session_ref"].strip()
    ):
        raise ValueError("axis_annotation_response_binding_invalid")
    expected_ids = {item["annotation_id"] for item in pack["items"]}
    labels = response.get("labels")
    if not isinstance(labels, list) or len(labels) != len(expected_ids):
        raise ValueError("axis_annotation_response_count_invalid")
    observed = []
    for label in labels:
        if not isinstance(label, dict) or set(label) != set(contract["required_label_fields"]):
            raise ValueError("axis_annotation_label_shape_invalid")
        observed.append(label.get("annotation_id"))
        criteria = label.get("criteria")
        if (
            not isinstance(criteria, dict)
            or set(criteria) != set(CRITERIA)
            or any(criteria[criterion] not in ALLOWED_STATES[criterion] for criterion in CRITERIA)
        ):
            raise ValueError("axis_annotation_criteria_invalid")
        if semantic_tuple_violations(
            selected=criteria["SELECTED_OBJECT"],
            basis=criteria["SELECTION_BASIS"],
            preference=criteria["PRAGMATIC_PREFERENCE"],
            completeness=criteria["AXIS_ASSESSMENT_COMPLETE"],
        ):
            raise ValueError("axis_annotation_tuple_incoherent")
        notes, confidence = label.get("criterion_notes"), label.get("criterion_confidence")
        if (
            not isinstance(notes, dict)
            or set(notes) != set(CRITERIA)
            or any(not isinstance(value, str) or not value.strip() or len(value) > 800 for value in notes.values())
        ):
            raise ValueError("axis_annotation_notes_invalid")
        if (
            not isinstance(confidence, dict)
            or set(confidence) != set(CRITERIA)
            or any(not _valid_confidence(value) for value in confidence.values())
        ):
            raise ValueError("axis_annotation_confidence_invalid")
        rationale = label.get("tuple_rationale")
        if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 1200:
            raise ValueError("axis_annotation_rationale_invalid")
    if len(observed) != len(set(observed)) or set(observed) != expected_ids:
        raise ValueError("axis_annotation_ids_invalid")


def build_axis_external_adjudication(*, packs, panel_manifest, responses, corpus):
    packs, responses = tuple(packs), tuple(responses)
    validate_axis_external_panel(packs=packs, manifest=panel_manifest)
    validate_axis_routing_holdout(corpus)
    pack_index = {pack["lane_id"]: pack for pack in packs}
    response_index = {response.get("lane_id"): response for response in responses}
    if len(response_index) != len(responses) or set(response_index) != set(pack_index):
        raise ValueError("axis_annotation_lanes_invalid")
    for lane, response in response_index.items():
        validate_axis_annotation_response(response, pack=pack_index[lane])
    lane_labels = {
        lane: {
            panel_manifest["private_lane_bindings"][lane][label["annotation_id"]]: label
            for label in response_index[lane]["labels"]
        }
        for lane in response_index
    }
    public_items = {item["conflict_id"]: item for item in corpus["public_surface"]["items"]}
    lanes = sorted(lane_labels)
    agreements, items, bindings = [], [], {}
    for conflict_id in sorted(public_items):
        labels = {lane: lane_labels[lane][conflict_id] for lane in lanes}
        tuples = {lane: labels[lane]["criteria"] for lane in lanes}
        annotation_ids = {lane: labels[lane]["annotation_id"] for lane in lanes}
        if len({hash_payload(value) for value in tuples.values()}) == 1:
            agreements.append({
                "conflict_id": conflict_id,
                "selected_tuple": tuples[lanes[0]],
                "lane_annotation_ids": annotation_ids,
                "lane_confidence": {lane: labels[lane]["criterion_confidence"] for lane in lanes},
            })
            continue
        adjudication_id = "axis-routing-adjudication-" + hash_payload([
            AXIS_ADJUDICATION_VERSION, panel_manifest["panel_id"], conflict_id
        ])[:18]
        ordered_lanes = sorted(lanes, key=lambda lane: hash_payload([adjudication_id, lane]))
        positions = []
        for index, lane in enumerate(ordered_lanes, start=1):
            label = labels[lane]
            positions.append({
                "position_id": f"POSITION_{index}",
                "criteria": label["criteria"],
                "criterion_notes": label["criterion_notes"],
                "criterion_confidence": label["criterion_confidence"],
                "tuple_rationale": label["tuple_rationale"],
            })
        source = public_items[conflict_id]
        items.append({
            "adjudication_id": adjudication_id,
            "public_prompt": source["public_prompt"],
            "candidate_a": source["candidate_a"],
            "candidate_b": source["candidate_b"],
            "anonymous_full_tuple_positions": positions,
        })
        bindings[adjudication_id] = {
            "conflict_id": conflict_id,
            "position_lanes": {f"POSITION_{index}": lane for index, lane in enumerate(ordered_lanes, start=1)},
            "lane_annotation_ids": annotation_ids,
        }
    items.sort(key=lambda item: hash_payload([panel_manifest["panel_id"], item["adjudication_id"]]))
    pack_commitment = {
        "panel_version": AXIS_PANEL_VERSION,
        "adjudication_version": AXIS_ADJUDICATION_VERSION,
        "panel_id": panel_manifest["panel_id"],
        "expected_adjudicator": {"provider": K3_SPEC[0], "model": K3_SPEC[1]},
        "annotator_identity": "WITHHELD",
        "source_identity": "WITHHELD",
        "object_family": "WITHHELD",
        "candidate_system_outputs": "WITHHELD",
        "construction_labels": "DO_NOT_EXIST",
        "prior_scores": "WITHHELD",
        "instructions": (
            "Adjudicate each disagreement as one complete semantic object. The displayed positions are anonymous coherent "
            "full tuples from independent annotators. Never vote or combine criteria independently. Select one displayed "
            "full position or independently reassess the entire object. Return one JSON object only."
        ),
        "items": items,
        "response_contract": adjudication_response_contract(),
    }
    pack = {**pack_commitment, "pack_hash": hash_payload(pack_commitment)}
    manifest_commitment = {
        "panel_version": AXIS_PANEL_VERSION,
        "adjudication_version": AXIS_ADJUDICATION_VERSION,
        "panel_id": panel_manifest["panel_id"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "annotation_response_hashes": {lane: hash_payload(response_index[lane]) for lane in sorted(response_index)},
        "adjudication_pack_hash": pack["pack_hash"],
        "agreement_records": agreements,
        "private_disagreement_bindings": bindings,
        "agreement_object_count": len(agreements),
        "disagreement_object_count": len(items),
        "total_object_count": len(agreements) + len(items),
        "reference_state": "AWAITING_KIMI_K3_FULL_TUPLE_ADJUDICATION" if items else "REFERENCE_READY_FROM_FULL_TUPLE_AGREEMENT",
        "candidate_outputs_exposed_to_adjudicator": False,
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return pack, {**manifest_commitment, "manifest_hash": hash_payload(manifest_commitment)}


def validate_axis_external_adjudication(*, pack, manifest, source_inputs=None):
    pack_commitment = {key: value for key, value in pack.items() if key != "pack_hash"}
    manifest_commitment = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    ids = {item.get("adjudication_id") for item in pack.get("items", [])}
    if (
        pack.get("pack_hash") != hash_payload(pack_commitment)
        or manifest.get("manifest_hash") != hash_payload(manifest_commitment)
        or pack.get("adjudication_version") != AXIS_ADJUDICATION_VERSION
        or manifest.get("adjudication_pack_hash") != pack.get("pack_hash")
        or manifest.get("total_object_count") != 24
        or manifest.get("agreement_object_count") + manifest.get("disagreement_object_count") != 24
        or ids != set(manifest.get("private_disagreement_bindings", {}))
        or manifest.get("candidate_outputs_exposed_to_adjudicator") is not False
        or manifest.get("reference_revision_allowed") is not False
    ):
        raise ValueError("axis_external_adjudication_invalid")
    public = str(pack).casefold()
    forbidden = ("gpt-5.6", "gemini-3.1", "openai", "google", "annotation-lane", "deepseek-r1", "qwen2.5", "gemma-2", "llama-3.2")
    if any(value in public for value in forbidden):
        raise ValueError("axis_external_adjudication_identity_leak")
    for item in pack.get("items", []):
        positions = item.get("anonymous_full_tuple_positions")
        if not isinstance(positions, list) or len(positions) != 2 or {value.get("position_id") for value in positions} != {"POSITION_1", "POSITION_2"}:
            raise ValueError("axis_external_adjudication_positions_invalid")
    if source_inputs is not None and (pack, manifest) != build_axis_external_adjudication(**source_inputs):
        raise ValueError("axis_external_adjudication_semantics_invalid")


def adjudication_response_contract():
    return {
        "required_top_level": [
            "panel_version", "adjudication_version", "panel_id", "adjudication_pack_hash",
            "adjudicator_provider", "adjudicator_model", "adjudication_session_ref",
            "blinding_attestation", "decisions",
        ],
        "required_decision_fields": ["adjudication_id", "criteria", "decision_basis", "confidence", "rationale"],
        "allowed_bases": ["POSITION_1", "POSITION_2", "INDEPENDENT_REASSESSMENT"],
        "required_blinding_attestation": {
            "pack_only_context": True,
            "annotator_identity_unavailable": True,
            "source_identity_unavailable": True,
            "object_family_unavailable": True,
            "candidate_system_outputs_unavailable": True,
            "construction_labels_do_not_exist": True,
            "prior_scores_unavailable": True,
        },
    }


def validate_axis_adjudication_response(response, *, pack):
    contract = adjudication_response_contract()
    if not isinstance(response, dict) or set(response) != set(contract["required_top_level"]):
        raise ValueError("axis_adjudication_response_shape_invalid")
    expected = {
        "panel_version": AXIS_PANEL_VERSION,
        "adjudication_version": AXIS_ADJUDICATION_VERSION,
        "panel_id": pack["panel_id"],
        "adjudication_pack_hash": pack["pack_hash"],
        "adjudicator_provider": K3_SPEC[0],
        "adjudicator_model": K3_SPEC[1],
    }
    if (
        any(response.get(key) != value for key, value in expected.items())
        or response.get("blinding_attestation") != contract["required_blinding_attestation"]
        or not isinstance(response.get("adjudication_session_ref"), str)
        or not response["adjudication_session_ref"].strip()
    ):
        raise ValueError("axis_adjudication_response_binding_invalid")
    item_index = {item["adjudication_id"]: item for item in pack["items"]}
    decisions = response.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(item_index):
        raise ValueError("axis_adjudication_response_count_invalid")
    observed = []
    for decision in decisions:
        if not isinstance(decision, dict) or set(decision) != set(contract["required_decision_fields"]):
            raise ValueError("axis_adjudication_decision_shape_invalid")
        adjudication_id = decision.get("adjudication_id")
        observed.append(adjudication_id)
        item = item_index.get(adjudication_id)
        criteria = decision.get("criteria")
        if (
            not item
            or not isinstance(criteria, dict)
            or set(criteria) != set(CRITERIA)
            or any(criteria[criterion] not in ALLOWED_STATES[criterion] for criterion in CRITERIA)
        ):
            raise ValueError("axis_adjudication_decision_invalid")
        if semantic_tuple_violations(
            selected=criteria["SELECTED_OBJECT"], basis=criteria["SELECTION_BASIS"],
            preference=criteria["PRAGMATIC_PREFERENCE"], completeness=criteria["AXIS_ASSESSMENT_COMPLETE"],
        ):
            raise ValueError("axis_adjudication_tuple_incoherent")
        if decision.get("decision_basis") not in contract["allowed_bases"] or not _valid_confidence(decision.get("confidence")):
            raise ValueError("axis_adjudication_decision_invalid")
        if not isinstance(decision.get("rationale"), str) or not decision["rationale"].strip() or len(decision["rationale"]) > 1200:
            raise ValueError("axis_adjudication_decision_invalid")
        positions = {position["position_id"]: position["criteria"] for position in item["anonymous_full_tuple_positions"]}
        if decision["decision_basis"] in positions and criteria != positions[decision["decision_basis"]]:
            raise ValueError("axis_adjudication_position_binding_invalid")
    if len(observed) != len(set(observed)) or set(observed) != set(item_index):
        raise ValueError("axis_adjudication_ids_invalid")


def _valid_confidence(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1
