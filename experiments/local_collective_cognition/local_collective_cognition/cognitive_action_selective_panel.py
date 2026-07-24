"""Blinded external annotation panel for selective collaboration v0.18."""

from __future__ import annotations

from .cognitive_action_selective_holdout import validate_selective_holdout
from .cognitive_action_selective_runtime import (
    BASES,
    EVIDENCE_STATES,
    PROCESS_STATES,
    SELECTIONS,
    validate_selective_baseline,
    validate_selective_run,
)
from .provider_telemetry import hash_payload


SELECTIVE_PANEL_VERSION = "cognitive_action_selective_external_panel_v0_18"
SELECTIVE_ADJUDICATION_VERSION = "cognitive_action_selective_external_adjudication_v0_18"
K3_SPEC = ("Moonshot", "Kimi-K3")
LANE_SPECS = (
    ("ANNOTATION_LANE_A", "OpenAI", "GPT-5.6"),
    ("ANNOTATION_LANE_B", "Google", "Gemini-3.1"),
)
CRITERIA = (
    "SELECTED_OBJECT",
    "SELECTION_BASIS",
    "PRAGMATIC_PREFERENCE",
    "EVIDENCE_STATE",
    "ASSESSMENT_PROCESS_STATE",
)
ALLOWED_STATES = {
    "SELECTED_OBJECT": SELECTIONS,
    "SELECTION_BASIS": BASES,
    "PRAGMATIC_PREFERENCE": SELECTIONS,
    "EVIDENCE_STATE": EVIDENCE_STATES,
    "ASSESSMENT_PROCESS_STATE": PROCESS_STATES,
}


def build_selective_external_panel(*, corpus, baseline_run, selective_run):
    validate_selective_holdout(corpus)
    validate_selective_baseline(corpus=corpus, baseline_run=baseline_run)
    validate_selective_run(corpus=corpus, baseline_run=baseline_run, run=selective_run)
    panel_id = "selective-panel-" + hash_payload([
        SELECTIVE_PANEL_VERSION, corpus["artifact_hash"], selective_run["run_hash"]
    ])[:16]
    packs, bindings = [], {}
    for lane_id, provider, model in LANE_SPECS:
        items, lane_bindings = [], {}
        for source in corpus["public_surface"]["items"]:
            annotation_id = "selective-annotation-" + hash_payload([
                SELECTIVE_PANEL_VERSION, panel_id, lane_id, source["conflict_id"]
            ])[:18]
            items.append({
                "annotation_id": annotation_id,
                "public_prompt": source["public_prompt"],
                "candidate_a": source["candidate_a"],
                "candidate_b": source["candidate_b"],
            })
            lane_bindings[annotation_id] = source["conflict_id"]
        items.sort(key=lambda item: hash_payload([SELECTIVE_PANEL_VERSION, lane_id, item["annotation_id"]]))
        commitment = {
            "panel_version": SELECTIVE_PANEL_VERSION,
            "panel_id": panel_id,
            "lane_id": lane_id,
            "expected_annotator": {"provider": provider, "model": model},
            "source_identity": "WITHHELD",
            "object_family": "WITHHELD",
            "design_stratum": "WITHHELD",
            "candidate_system_outputs": "WITHHELD",
            "prior_scores": "WITHHELD",
            "criterion_definitions": {
                "SELECTED_OBJECT": "Which candidate, if any, is semantically fixed by the displayed prompt.",
                "SELECTION_BASIS": "Why selection is fixed or remains open.",
                "PRAGMATIC_PREFERENCE": "Which candidate ordinary context favors when neither is entailed.",
                "EVIDENCE_STATE": "Whether evidence directly defines, compositionally determines, softly underdetermines, opaquely references, conflicts, or remains uncertain.",
                "ASSESSMENT_PROCESS_STATE": "Whether the assessment process itself completed; a justified open or opaque conclusion can be COMPLETE.",
            },
            "instructions": (
                "Assess each object independently from the displayed prompt and candidates. Keep semantic selection, pragmatic "
                "preference, evidence state, and process completion separate. OPAQUE_REFERENCE means a missing named rule or "
                "codebook blocks resolution; it is not SOFT_AMBIGUITY. A justified open result may be COMPLETE. Return one JSON object only."
            ),
            "items": items,
            "response_contract": annotation_response_contract(),
        }
        packs.append({**commitment, "pack_hash": hash_payload(commitment)})
        bindings[lane_id] = lane_bindings
    manifest_commitment = {
        "panel_version": SELECTIVE_PANEL_VERSION,
        "panel_id": panel_id,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_surface_hash": corpus["public_surface"]["surface_hash"],
        "frozen_baseline_run_hash": baseline_run["run_hash"],
        "frozen_selective_run_hash": selective_run["run_hash"],
        "candidate_outputs_frozen_before_panel_pack": True,
        "candidate_outputs_exposed_to_annotators": False,
        "lane_pack_hashes": {pack["lane_id"]: pack["pack_hash"] for pack in packs},
        "private_lane_bindings": bindings,
        "candidate_count": corpus["case_count"],
        "criterion_count": len(CRITERIA),
        "current_phase": "AWAITING_GPT_GEMINI_COHERENT_TUPLES",
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return tuple(packs), {**manifest_commitment, "manifest_hash": hash_payload(manifest_commitment)}


def validate_selective_external_panel(*, packs, manifest, source_inputs=None):
    packs = tuple(packs)
    commitment = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    observed = {
        (pack.get("lane_id"), pack.get("expected_annotator", {}).get("provider"), pack.get("expected_annotator", {}).get("model"))
        for pack in packs
    }
    if (
        manifest.get("manifest_hash") != hash_payload(commitment)
        or manifest.get("panel_version") != SELECTIVE_PANEL_VERSION
        or observed != set(LANE_SPECS)
        or manifest.get("candidate_outputs_exposed_to_annotators") is not False
        or manifest.get("reference_revision_allowed") is not False
    ):
        raise ValueError("selective_panel_manifest_invalid")
    lane_ids = []
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
            raise ValueError("selective_panel_pack_invalid")
        public = str(pack).casefold()
        forbidden = ("deepseek-r1", "qwen2.5", "gemma-2", "llama-3.2", "design_stratum_counts", "selective_run")
        if any(value in public for value in forbidden):
            raise ValueError("selective_panel_candidate_leak")
        lane_ids.append(ids)
    if lane_ids[0] & lane_ids[1]:
        raise ValueError("selective_panel_lane_alias_collision")
    if source_inputs is not None and (packs, manifest) != build_selective_external_panel(**source_inputs):
        raise ValueError("selective_panel_semantics_invalid")


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
            "design_stratum_unavailable": True,
            "peer_annotation_unavailable": True,
            "candidate_system_outputs_unavailable": True,
            "prior_scores_unavailable": True,
        },
    }


def validate_selective_annotation_response(response, *, pack):
    contract = annotation_response_contract()
    if not isinstance(response, dict) or set(response) != set(contract["required_top_level"]):
        raise ValueError("selective_annotation_response_shape_invalid")
    expected = {
        "panel_version": SELECTIVE_PANEL_VERSION,
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
        raise ValueError("selective_annotation_response_binding_invalid")
    expected_ids = {item["annotation_id"] for item in pack["items"]}
    labels = response.get("labels")
    if not isinstance(labels, list) or len(labels) != len(expected_ids):
        raise ValueError("selective_annotation_response_count_invalid")
    observed = []
    for label in labels:
        if not isinstance(label, dict) or set(label) != set(contract["required_label_fields"]):
            raise ValueError("selective_annotation_label_shape_invalid")
        observed.append(label.get("annotation_id"))
        criteria = label.get("criteria")
        if (
            not isinstance(criteria, dict)
            or set(criteria) != set(CRITERIA)
            or any(criteria[criterion] not in ALLOWED_STATES[criterion] for criterion in CRITERIA)
            or selective_tuple_violations(criteria)
        ):
            raise ValueError("selective_annotation_tuple_invalid")
        notes = label.get("criterion_notes")
        confidence = label.get("criterion_confidence")
        if (
            not isinstance(notes, dict)
            or set(notes) != set(CRITERIA)
            or any(not isinstance(value, str) or not value.strip() or len(value) > 800 for value in notes.values())
            or not isinstance(confidence, dict)
            or set(confidence) != set(CRITERIA)
            or any(not _valid_confidence(value) for value in confidence.values())
        ):
            raise ValueError("selective_annotation_support_invalid")
        rationale = label.get("tuple_rationale")
        if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 1200:
            raise ValueError("selective_annotation_rationale_invalid")
    if len(observed) != len(set(observed)) or set(observed) != expected_ids:
        raise ValueError("selective_annotation_ids_invalid")


def build_selective_external_adjudication(*, packs, panel_manifest, responses, corpus):
    packs, responses = tuple(packs), tuple(responses)
    validate_selective_external_panel(packs=packs, manifest=panel_manifest)
    validate_selective_holdout(corpus)
    pack_index = {pack["lane_id"]: pack for pack in packs}
    response_index = {response.get("lane_id"): response for response in responses}
    if len(response_index) != len(responses) or set(response_index) != set(pack_index):
        raise ValueError("selective_annotation_lanes_invalid")
    for lane, response in response_index.items():
        validate_selective_annotation_response(response, pack=pack_index[lane])
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
                "lane_confidence": {
                    lane: labels[lane]["criterion_confidence"] for lane in lanes
                },
            })
            continue
        adjudication_id = "selective-adjudication-" + hash_payload([
            SELECTIVE_ADJUDICATION_VERSION, panel_manifest["panel_id"], conflict_id
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
            "position_lanes": {
                f"POSITION_{index}": lane
                for index, lane in enumerate(ordered_lanes, start=1)
            },
            "lane_annotation_ids": annotation_ids,
        }
    items.sort(key=lambda item: hash_payload([panel_manifest["panel_id"], item["adjudication_id"]]))
    pack_commitment = {
        "panel_version": SELECTIVE_PANEL_VERSION,
        "adjudication_version": SELECTIVE_ADJUDICATION_VERSION,
        "panel_id": panel_manifest["panel_id"],
        "expected_adjudicator": {"provider": K3_SPEC[0], "model": K3_SPEC[1]},
        "annotator_identity": "WITHHELD",
        "source_identity": "WITHHELD",
        "object_family": "WITHHELD",
        "design_stratum": "WITHHELD",
        "candidate_system_outputs": "WITHHELD",
        "prior_scores": "WITHHELD",
        "instructions": (
            "Adjudicate each disagreement as one complete five-criterion semantic object. The positions are anonymous coherent "
            "tuples from independent annotators. Do not vote or combine criteria independently. Distinguish an opaque but "
            "completed open assessment from an assessment process that truly failed to complete. Select one displayed full "
            "position or independently reassess the entire tuple. Return one JSON object only."
        ),
        "items": items,
        "response_contract": adjudication_response_contract(),
    }
    pack = {**pack_commitment, "pack_hash": hash_payload(pack_commitment)}
    manifest_commitment = {
        "panel_version": SELECTIVE_PANEL_VERSION,
        "adjudication_version": SELECTIVE_ADJUDICATION_VERSION,
        "panel_id": panel_manifest["panel_id"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "annotation_response_hashes": {
            lane: hash_payload(response_index[lane]) for lane in sorted(response_index)
        },
        "adjudication_pack_hash": pack["pack_hash"],
        "agreement_records": agreements,
        "private_disagreement_bindings": bindings,
        "agreement_object_count": len(agreements),
        "disagreement_object_count": len(items),
        "total_object_count": len(agreements) + len(items),
        "reference_state": (
            "AWAITING_KIMI_K3_SELECTIVE_FULL_TUPLE_ADJUDICATION"
            if items else "REFERENCE_READY_FROM_FULL_TUPLE_AGREEMENT"
        ),
        "candidate_outputs_exposed_to_adjudicator": False,
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return pack, {**manifest_commitment, "manifest_hash": hash_payload(manifest_commitment)}


def validate_selective_external_adjudication(*, pack, manifest, source_inputs=None):
    pack_commitment = {key: value for key, value in pack.items() if key != "pack_hash"}
    manifest_commitment = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    ids = {item.get("adjudication_id") for item in pack.get("items", [])}
    if (
        pack.get("pack_hash") != hash_payload(pack_commitment)
        or manifest.get("manifest_hash") != hash_payload(manifest_commitment)
        or pack.get("adjudication_version") != SELECTIVE_ADJUDICATION_VERSION
        or manifest.get("adjudication_pack_hash") != pack.get("pack_hash")
        or manifest.get("total_object_count") != 24
        or manifest.get("agreement_object_count") + manifest.get("disagreement_object_count") != 24
        or ids != set(manifest.get("private_disagreement_bindings", {}))
        or manifest.get("candidate_outputs_exposed_to_adjudicator") is not False
        or manifest.get("reference_revision_allowed") is not False
    ):
        raise ValueError("selective_external_adjudication_invalid")
    public = str(pack).casefold()
    forbidden = (
        "gpt-5.6", "gemini-3.1", "openai", "google", "annotation_lane",
        "deepseek-r1", "qwen2.5", "gemma-2", "llama-3.2",
    )
    if any(value in public for value in forbidden):
        raise ValueError("selective_external_adjudication_identity_leak")
    for item in pack.get("items", []):
        positions = item.get("anonymous_full_tuple_positions")
        if (
            not isinstance(positions, list)
            or len(positions) != 2
            or {value.get("position_id") for value in positions} != {"POSITION_1", "POSITION_2"}
        ):
            raise ValueError("selective_external_adjudication_positions_invalid")
    if source_inputs is not None and (pack, manifest) != build_selective_external_adjudication(**source_inputs):
        raise ValueError("selective_external_adjudication_semantics_invalid")


def adjudication_response_contract():
    return {
        "required_top_level": [
            "panel_version", "adjudication_version", "panel_id", "adjudication_pack_hash",
            "adjudicator_provider", "adjudicator_model", "adjudication_session_ref",
            "blinding_attestation", "decisions",
        ],
        "required_decision_fields": [
            "adjudication_id", "criteria", "decision_basis", "confidence", "rationale",
        ],
        "allowed_bases": ["POSITION_1", "POSITION_2", "INDEPENDENT_REASSESSMENT"],
        "required_blinding_attestation": {
            "pack_only_context": True,
            "annotator_identity_unavailable": True,
            "source_identity_unavailable": True,
            "object_family_unavailable": True,
            "design_stratum_unavailable": True,
            "candidate_system_outputs_unavailable": True,
            "prior_scores_unavailable": True,
        },
    }


def validate_selective_adjudication_response(response, *, pack):
    contract = adjudication_response_contract()
    if not isinstance(response, dict) or set(response) != set(contract["required_top_level"]):
        raise ValueError("selective_adjudication_response_shape_invalid")
    expected = {
        "panel_version": SELECTIVE_PANEL_VERSION,
        "adjudication_version": SELECTIVE_ADJUDICATION_VERSION,
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
        raise ValueError("selective_adjudication_response_binding_invalid")
    item_index = {item["adjudication_id"]: item for item in pack["items"]}
    decisions = response.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(item_index):
        raise ValueError("selective_adjudication_response_count_invalid")
    observed = []
    for decision in decisions:
        if not isinstance(decision, dict) or set(decision) != set(contract["required_decision_fields"]):
            raise ValueError("selective_adjudication_decision_shape_invalid")
        adjudication_id = decision.get("adjudication_id")
        observed.append(adjudication_id)
        item = item_index.get(adjudication_id)
        criteria = decision.get("criteria")
        if (
            not item
            or not isinstance(criteria, dict)
            or set(criteria) != set(CRITERIA)
            or any(criteria[criterion] not in ALLOWED_STATES[criterion] for criterion in CRITERIA)
            or selective_tuple_violations(criteria)
            or decision.get("decision_basis") not in contract["allowed_bases"]
            or not _valid_confidence(decision.get("confidence"))
            or not isinstance(decision.get("rationale"), str)
            or not decision["rationale"].strip()
            or len(decision["rationale"]) > 1200
        ):
            raise ValueError("selective_adjudication_decision_invalid")
        positions = {
            position["position_id"]: position["criteria"]
            for position in item["anonymous_full_tuple_positions"]
        }
        if decision["decision_basis"] in positions and criteria != positions[decision["decision_basis"]]:
            raise ValueError("selective_adjudication_position_binding_invalid")
    if len(observed) != len(set(observed)) or set(observed) != set(item_index):
        raise ValueError("selective_adjudication_ids_invalid")


def selective_tuple_violations(criteria):
    selected = criteria["SELECTED_OBJECT"]
    basis = criteria["SELECTION_BASIS"]
    preference = criteria["PRAGMATIC_PREFERENCE"]
    evidence = criteria["EVIDENCE_STATE"]
    process = criteria["ASSESSMENT_PROCESS_STATE"]
    violations = []
    if basis == "LEXICAL_EXACT" and (
        selected not in ("CANDIDATE_A", "CANDIDATE_B") or evidence != "DIRECTLY_DEFINED"
    ):
        violations.append("LEXICAL_DIRECT_MISMATCH")
    if basis == "COMPOSITIONAL_ENTAILMENT" and (
        selected not in ("CANDIDATE_A", "CANDIDATE_B")
        or evidence != "COMPOSITIONALLY_DETERMINED"
    ):
        violations.append("COMPOSITIONAL_EVIDENCE_MISMATCH")
    if basis == "PRAGMATIC_DEFAULT" and (
        selected != "NONE"
        or preference not in ("CANDIDATE_A", "CANDIDATE_B")
        or evidence != "SOFT_AMBIGUITY"
    ):
        violations.append("PRAGMATIC_SOFT_MISMATCH")
    if basis == "NO_PREFERENCE" and (
        selected != "NONE"
        or preference != "NONE"
        or evidence not in ("SOFT_AMBIGUITY", "OPAQUE_REFERENCE")
    ):
        violations.append("NO_PREFERENCE_MISMATCH")
    if basis == "UNCERTAIN" and (
        selected != "UNCERTAIN"
        or preference != "UNCERTAIN"
        or evidence not in ("OPAQUE_REFERENCE", "CONFLICTED", "UNCERTAIN")
    ):
        violations.append("UNCERTAIN_MISMATCH")
    expected_basis = {
        "DIRECTLY_DEFINED": ("LEXICAL_EXACT",),
        "COMPOSITIONALLY_DETERMINED": ("COMPOSITIONAL_ENTAILMENT",),
        "SOFT_AMBIGUITY": ("PRAGMATIC_DEFAULT", "NO_PREFERENCE"),
        "OPAQUE_REFERENCE": ("NO_PREFERENCE", "UNCERTAIN"),
        "CONFLICTED": ("UNCERTAIN",),
        "UNCERTAIN": ("UNCERTAIN",),
    }
    if basis not in expected_basis[evidence]:
        violations.append("EVIDENCE_BASIS_MISMATCH")
    if process == "INCOMPLETE" and evidence not in ("OPAQUE_REFERENCE", "CONFLICTED", "UNCERTAIN"):
        violations.append("INCOMPLETE_WITH_DECISIVE_EVIDENCE")
    return tuple(violations)


def _valid_confidence(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1
