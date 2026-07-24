"""Identity-blind semantic reference panel for fresh joint coordination v0.13."""

from __future__ import annotations

from .clarification_joint_holdout import validate_joint_holdout_artifact
from .clarification_joint_coordinator_contracts import semantic_tuple_violations
from .clarification_semantic_basis_panel import ALLOWED_STATES, CRITERIA, RUBRIC
from .provider_telemetry import hash_payload


PANEL_VERSION = "clarification_joint_fresh_panel_v0_13"
ADJUDICATION_VERSION = "clarification_joint_fresh_adjudication_v0_13"
LANE_SPECS = (("annotation-lane-a", "OpenAI", "GPT-5.6"), ("annotation-lane-b", "Google", "Gemini-3.1"))
K3_SPEC = ("Moonshot", "Kimi-K3")


def build_joint_fresh_panel(*, corpus_artifact):
    validate_joint_holdout_artifact(corpus_artifact)
    source_hash = corpus_artifact["artifact_hash"]
    panel_id = "joint-fresh-panel-" + hash_payload([PANEL_VERSION, source_hash])[:16]
    source_items = [item for batch in corpus_artifact["public_surface"]["batches"] for item in batch["conflicts"]]
    packs, bindings = [], {}
    for lane_id, provider, model in LANE_SPECS:
        items, lane_bindings = [], {}
        for source in source_items:
            annotation_id = "joint-fresh-annotation-" + hash_payload([PANEL_VERSION, source_hash, lane_id, source["conflict_id"]])[:18]
            items.append({"annotation_id": annotation_id, "public_prompt": source["public_prompt"], "candidate_a": source["candidate_a"], "candidate_b": source["candidate_b"]})
            lane_bindings[annotation_id] = source["conflict_id"]
        items.sort(key=lambda item: hash_payload([lane_id, item["annotation_id"]]))
        commitment = {
            "panel_version": PANEL_VERSION, "panel_id": panel_id, "lane_id": lane_id,
            "expected_annotator": {"provider": provider, "model": model},
            "source_identity": "WITHHELD", "construction_labels": "WITHHELD", "locked_consensus_axes": "WITHHELD",
            "local_basis_outcome": "WITHHELD", "deepseek_outputs": "WITHHELD", "prior_scores": "WITHHELD",
            "item_order": "LANE_SPECIFIC_HASH_RANDOMIZED", "rubric": RUBRIC,
            "instructions": (
                "Assess every item independently using only the displayed prompt and candidates. Return the semantic "
                "tuple, not a governance action. Semantic entailment, pragmatic preference, and assessment completeness "
                "are separate axes. A justified NONE can be complete; use INCOMPLETE only when the displayed information "
                "is insufficient even to decide whether NONE is warranted. Return JSON only."
            ),
            "items": items, "response_contract": annotation_response_contract(),
        }
        packs.append({**commitment, "pack_hash": hash_payload(commitment)}); bindings[lane_id] = lane_bindings
    manifest_commitment = {
        "panel_version": PANEL_VERSION, "panel_id": panel_id, "source_corpus_hash": source_hash,
        "source_surface_hash": corpus_artifact["public_surface"]["surface_hash"], "rubric_hash": hash_payload(RUBRIC),
        "lane_pack_hashes": {pack["lane_id"]: pack["pack_hash"] for pack in packs}, "private_lane_bindings": bindings,
        "candidate_count": len(source_items), "criterion_count": len(CRITERIA), "reference_state": "AWAITING_MODEL_ANNOTATIONS",
        "construction_labels_are_reference": False, "ground_truth_claim": False, "action_credit_authority": False,
        "selection_authority": False, "retention_authority": False,
    }
    manifest = {**manifest_commitment, "manifest_hash": hash_payload(manifest_commitment)}
    return tuple(packs), manifest


def validate_joint_fresh_panel(*, packs, manifest, corpus_artifact=None):
    packs = tuple(packs); commitment = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if manifest.get("manifest_hash") != hash_payload(commitment):
        raise ValueError("joint_fresh_panel_manifest_hash_invalid")
    expected = {(lane, provider, model) for lane, provider, model in LANE_SPECS}
    observed = {(pack.get("lane_id"), pack.get("expected_annotator", {}).get("provider"), pack.get("expected_annotator", {}).get("model")) for pack in packs}
    if len(packs) != 2 or observed != expected:
        raise ValueError("joint_fresh_panel_lane_invalid")
    for pack in packs:
        pack_commitment = {key: value for key, value in pack.items() if key != "pack_hash"}
        ids = {item["annotation_id"] for item in pack["items"]}
        if pack.get("pack_hash") != hash_payload(pack_commitment) or manifest["lane_pack_hashes"].get(pack["lane_id"]) != pack["pack_hash"] or ids != set(manifest["private_lane_bindings"][pack["lane_id"]]):
            raise ValueError("joint_fresh_panel_pack_binding_invalid")
    if corpus_artifact is not None and (packs, manifest) != build_joint_fresh_panel(corpus_artifact=corpus_artifact):
        raise ValueError("joint_fresh_panel_semantics_invalid")


def annotation_response_contract():
    return {"required_top_level": ["panel_version", "panel_id", "lane_id", "pack_hash", "annotator_provider", "annotator_model", "annotation_session_ref", "labels"], "required_label_fields": ["annotation_id", "criteria", "criterion_notes", "criterion_confidence"], "criteria": list(CRITERIA), "allowed_states": {criterion: list(states) for criterion, states in ALLOWED_STATES.items()}, "instruction": "Return one JSON object only and provide every criterion for every annotation_id."}


def validate_joint_fresh_annotation_response(response, *, pack):
    contract = annotation_response_contract()
    if not isinstance(response, dict) or set(response) != set(contract["required_top_level"]):
        raise ValueError("joint_fresh_annotation_shape_invalid")
    expected = {"panel_version": PANEL_VERSION, "panel_id": pack["panel_id"], "lane_id": pack["lane_id"], "pack_hash": pack["pack_hash"], "annotator_provider": pack["expected_annotator"]["provider"], "annotator_model": pack["expected_annotator"]["model"]}
    if any(response.get(key) != value for key, value in expected.items()) or not isinstance(response.get("annotation_session_ref"), str) or not response["annotation_session_ref"].strip():
        raise ValueError("joint_fresh_annotation_binding_invalid")
    labels = response["labels"]; expected_ids = {item["annotation_id"] for item in pack["items"]}
    if not isinstance(labels, list) or len(labels) != len(expected_ids):
        raise ValueError("joint_fresh_annotation_count_invalid")
    observed = []
    for label in labels:
        if not isinstance(label, dict) or set(label) != set(contract["required_label_fields"]):
            raise ValueError("joint_fresh_annotation_item_shape_invalid")
        observed.append(label["annotation_id"])
        if set(label["criteria"]) != set(CRITERIA) or any(label["criteria"][criterion] not in ALLOWED_STATES[criterion] for criterion in CRITERIA):
            raise ValueError("joint_fresh_annotation_criteria_invalid")
        if set(label["criterion_notes"]) != set(CRITERIA) or any(not isinstance(value, str) or not value.strip() for value in label["criterion_notes"].values()):
            raise ValueError("joint_fresh_annotation_notes_invalid")
        if set(label["criterion_confidence"]) != set(CRITERIA) or any(not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1 for value in label["criterion_confidence"].values()):
            raise ValueError("joint_fresh_annotation_confidence_invalid")
    if len(observed) != len(set(observed)) or set(observed) != expected_ids:
        raise ValueError("joint_fresh_annotation_id_invalid")


def build_joint_fresh_adjudication(*, packs, panel_manifest, responses):
    packs, responses = tuple(packs), tuple(responses); validate_joint_fresh_panel(packs=packs, manifest=panel_manifest)
    pack_index = {pack["lane_id"]: pack for pack in packs}; response_index = {response.get("lane_id"): response for response in responses}
    if set(response_index) != set(pack_index) or len(responses) != 2:
        raise ValueError("joint_fresh_annotation_lanes_invalid")
    for lane, response in response_index.items():
        validate_joint_fresh_annotation_response(response, pack=pack_index[lane])
    labels = {lane: {label["annotation_id"]: label for label in response["labels"]} for lane, response in response_index.items()}; lanes = sorted(pack_index)
    agreements, items, bindings = [], [], {}
    for first_id, conflict_id in sorted(panel_manifest["private_lane_bindings"][lanes[0]].items(), key=lambda item: item[1]):
        lane_ids = {lane: _annotation_for(panel_manifest, lane, conflict_id) for lane in lanes}; source = _public_item(pack_index[lanes[0]], first_id)
        for criterion in CRITERIA:
            states = {lane: labels[lane][lane_ids[lane]]["criteria"][criterion] for lane in lanes}
            notes = {lane: labels[lane][lane_ids[lane]]["criterion_notes"][criterion] for lane in lanes}
            confidence = {lane: labels[lane][lane_ids[lane]]["criterion_confidence"][criterion] for lane in lanes}
            if len(set(states.values())) == 1:
                agreements.append({"conflict_id": conflict_id, "criterion": criterion, "selected_state": next(iter(states.values())), "lane_annotation_ids": lane_ids, "lane_confidence": confidence}); continue
            adjudication_id = "joint-fresh-adjudication-" + hash_payload([ADJUDICATION_VERSION, panel_manifest["panel_id"], conflict_id, criterion])[:18]
            ordered = sorted(lanes, key=lambda lane: hash_payload([adjudication_id, lane])); positions = [{"position_id": f"POSITION_{index + 1}", "state": states[lane], "criterion_note": notes[lane], "confidence": confidence[lane]} for index, lane in enumerate(ordered)]
            items.append({"adjudication_id": adjudication_id, "public_prompt": source["public_prompt"], "candidate_a": source["candidate_a"], "candidate_b": source["candidate_b"], "criterion": criterion, "criterion_definition": RUBRIC[criterion], "positions": positions})
            bindings[adjudication_id] = {"conflict_id": conflict_id, "criterion": criterion, "position_lanes": {f"POSITION_{index + 1}": lane for index, lane in enumerate(ordered)}, "lane_annotation_ids": lane_ids}
    items.sort(key=lambda item: hash_payload([panel_manifest["panel_id"], item["adjudication_id"]]))
    pack_commitment = {"panel_version": PANEL_VERSION, "adjudication_version": ADJUDICATION_VERSION, "panel_id": panel_manifest["panel_id"], "expected_adjudicator": {"provider": K3_SPEC[0], "model": K3_SPEC[1]}, "annotator_identity": "WITHHELD", "source_identity": "WITHHELD", "construction_labels": "WITHHELD", "locked_consensus_axes": "WITHHELD", "local_basis_outcome": "WITHHELD", "deepseek_outputs": "WITHHELD", "prior_scores": "WITHHELD", "instructions": "Adjudicate only the displayed semantic criterion. Positions are anonymous. Preserve NONE and UNCERTAIN when justified. Return JSON only.", "items": items, "response_contract": adjudication_response_contract()}
    pack = {**pack_commitment, "pack_hash": hash_payload(pack_commitment)}
    manifest_commitment = {"panel_version": PANEL_VERSION, "adjudication_version": ADJUDICATION_VERSION, "panel_id": panel_manifest["panel_id"], "panel_manifest_hash": panel_manifest["manifest_hash"], "annotation_response_hashes": {lane: hash_payload(response_index[lane]) for lane in lanes}, "adjudication_pack_hash": pack["pack_hash"], "agreement_records": agreements, "private_disagreement_bindings": bindings, "agreement_count": len(agreements), "disagreement_count": len(items), "total_label_count": len(agreements) + len(items), "reference_state": "AWAITING_KIMI_K3_ADJUDICATION" if items else "PANEL_AGREEMENT_COMPLETE", "ground_truth_claim": False, "action_credit_authority": False, "selection_authority": False, "retention_authority": False}
    manifest = {**manifest_commitment, "manifest_hash": hash_payload(manifest_commitment)}
    return pack, manifest


def validate_joint_fresh_adjudication(*, pack, manifest, panel_packs=None, panel_manifest=None, responses=None):
    pc = {key: value for key, value in pack.items() if key != "pack_hash"}; mc = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if pack.get("pack_hash") != hash_payload(pc) or manifest.get("manifest_hash") != hash_payload(mc) or manifest.get("adjudication_pack_hash") != pack.get("pack_hash") or manifest.get("total_label_count") != 24 * len(CRITERIA) or set(manifest.get("private_disagreement_bindings", {})) != {item["adjudication_id"] for item in pack.get("items", [])}:
        raise ValueError("joint_fresh_adjudication_invalid")
    supplied = (panel_packs, panel_manifest, responses)
    if any(value is not None for value in supplied):
        if not all(value is not None for value in supplied) or (pack, manifest) != build_joint_fresh_adjudication(packs=panel_packs, panel_manifest=panel_manifest, responses=responses):
            raise ValueError("joint_fresh_adjudication_semantics_invalid")


def adjudication_response_contract():
    return {"required_top_level": ["panel_version", "panel_id", "adjudication_pack_hash", "adjudicator_provider", "adjudicator_model", "adjudication_session_ref", "blinding_attestation", "decisions"], "required_decision_fields": ["adjudication_id", "selected_state", "decision_basis", "confidence", "rationale"], "allowed_bases": ["POSITION_1", "POSITION_2", "INDEPENDENT_REASSESSMENT", "UNRESOLVED"], "required_blinding_attestation": {"pack_only_context": True, "annotator_identity_unavailable": True, "source_identity_unavailable": True, "construction_labels_unavailable": True, "locked_consensus_axes_unavailable": True, "local_basis_outcome_unavailable": True, "deepseek_outputs_unavailable": True, "prior_scores_unavailable": True, "external_pairing_not_used": True}}


def validate_joint_fresh_adjudication_response(response, *, pack):
    contract = adjudication_response_contract()
    if not isinstance(response, dict) or set(response) != set(contract["required_top_level"]):
        raise ValueError("joint_fresh_adjudication_response_shape_invalid")
    expected = {"panel_version": PANEL_VERSION, "panel_id": pack["panel_id"], "adjudication_pack_hash": pack["pack_hash"], "adjudicator_provider": K3_SPEC[0], "adjudicator_model": K3_SPEC[1]}
    if any(response.get(key) != value for key, value in expected.items()) or response.get("blinding_attestation") != contract["required_blinding_attestation"] or not isinstance(response.get("adjudication_session_ref"), str) or not response["adjudication_session_ref"].strip():
        raise ValueError("joint_fresh_adjudication_response_binding_invalid")
    index = {item["adjudication_id"]: item for item in pack["items"]}; decisions = response["decisions"]
    if not isinstance(decisions, list) or len(decisions) != len(index):
        raise ValueError("joint_fresh_adjudication_decision_count_invalid")
    observed = []
    for decision in decisions:
        if not isinstance(decision, dict) or set(decision) != set(contract["required_decision_fields"]):
            raise ValueError("joint_fresh_adjudication_decision_shape_invalid")
        item = index.get(decision["adjudication_id"]); observed.append(decision["adjudication_id"])
        if not item or decision["selected_state"] not in ALLOWED_STATES[item["criterion"]] or decision["decision_basis"] not in contract["allowed_bases"] or not isinstance(decision["rationale"], str) or not decision["rationale"].strip() or not isinstance(decision["confidence"], (int, float)) or isinstance(decision["confidence"], bool) or not 0 <= decision["confidence"] <= 1:
            raise ValueError("joint_fresh_adjudication_decision_invalid")
        positions = {position["position_id"]: position["state"] for position in item["positions"]}
        if decision["decision_basis"] in positions and decision["selected_state"] != positions[decision["decision_basis"]]:
            raise ValueError("joint_fresh_adjudication_position_invalid")
        if decision["decision_basis"] == "UNRESOLVED" and decision["selected_state"] != "UNCERTAIN":
            raise ValueError("joint_fresh_adjudication_unresolved_invalid")
    if len(observed) != len(set(observed)) or set(observed) != set(index):
        raise ValueError("joint_fresh_adjudication_id_invalid")


def build_joint_fresh_reference(*, adjudication_pack, adjudication_manifest, response=None):
    validate_joint_fresh_adjudication(pack=adjudication_pack, manifest=adjudication_manifest)
    if adjudication_pack["items"]:
        if response is None: raise ValueError("joint_fresh_adjudication_response_required")
        validate_joint_fresh_adjudication_response(response, pack=adjudication_pack)
    decisions = {item["adjudication_id"]: item for item in (response or {"decisions": []})["decisions"]}; cells = {}
    for item in adjudication_manifest["agreement_records"]: cells[(item["conflict_id"], item["criterion"])] = {"state": item["selected_state"], "source": "GPT_GEMINI_AGREEMENT"}
    for adjudication_id, binding in adjudication_manifest["private_disagreement_bindings"].items(): cells[(binding["conflict_id"], binding["criterion"])] = {"state": decisions[adjudication_id]["selected_state"], "source": "KIMI_K3_ADJUDICATION"}
    conflict_ids = sorted({key[0] for key in cells}); labels = [{"conflict_id": conflict_id, "criteria": {criterion: cells[(conflict_id, criterion)]["state"] for criterion in CRITERIA}, "criterion_sources": {criterion: cells[(conflict_id, criterion)]["source"] for criterion in CRITERIA}} for conflict_id in conflict_ids]
    if len(labels) != 24 or len(cells) != 96: raise ValueError("joint_fresh_reference_coverage_invalid")
    coherence_records = _coherence_records(labels)
    commitment = {"panel_version": PANEL_VERSION, "panel_id": adjudication_pack["panel_id"], "adjudication_manifest_hash": adjudication_manifest["manifest_hash"], "adjudication_pack_hash": adjudication_pack["pack_hash"], "adjudication_response_hash": hash_payload(response) if response is not None else None, "labels": labels, "label_count": len(cells), "cross_axis_coherence_passed": not coherence_records, "cross_axis_inconsistency_count": len(coherence_records), "cross_axis_inconsistency_records": coherence_records, "candidate_state": "JOINT_FRESH_MODEL_PANEL_REFERENCE_CANDIDATE" if not coherence_records else "JOINT_FRESH_MODEL_PANEL_REFERENCE_COHERENCE_FAILED", "ground_truth_claim": False, "human_gold_claim": False, "action_credit_authority": False, "selection_authority": False, "retention_authority": False}
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_joint_fresh_reference(artifact, *, adjudication_pack=None, adjudication_manifest=None, response=None):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact.get("panel_version") != PANEL_VERSION or artifact.get("label_count") != 96 or len(artifact.get("labels", [])) != 24:
        raise ValueError("joint_fresh_reference_invalid")
    supplied = (adjudication_pack, adjudication_manifest)
    if any(value is not None for value in supplied):
        if not all(value is not None for value in supplied) or artifact != build_joint_fresh_reference(adjudication_pack=adjudication_pack, adjudication_manifest=adjudication_manifest, response=response):
            raise ValueError("joint_fresh_reference_semantics_invalid")


def _annotation_for(manifest, lane, conflict_id):
    matches = [annotation_id for annotation_id, value in manifest["private_lane_bindings"][lane].items() if value == conflict_id]
    if len(matches) != 1: raise ValueError("joint_fresh_annotation_reverse_binding_invalid")
    return matches[0]


def _public_item(pack, annotation_id):
    return next(item for item in pack["items"] if item["annotation_id"] == annotation_id)


def _coherence_records(labels):
    records = []
    for label in labels:
        c = label["criteria"]
        violations = semantic_tuple_violations(selected=c["SELECTED_OBJECT"], basis=c["SELECTION_BASIS"], preference=c["PRAGMATIC_PREFERENCE"], completeness=c["AXIS_ASSESSMENT_COMPLETE"])
        if violations:
            records.append({"conflict_id": label["conflict_id"], "violations": violations, "criteria": c})
    return records
