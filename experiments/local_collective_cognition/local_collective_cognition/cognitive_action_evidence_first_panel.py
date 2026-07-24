"""Blinded external panel for evidence-first selective challenge v0.22."""

from __future__ import annotations

from .cognitive_action_evidence_first_holdout import (
    validate_evidence_first_holdout,
)
from .cognitive_action_selective_panel import (
    ALLOWED_STATES,
    CRITERIA,
    K3_SPEC,
    selective_tuple_violations,
)
from .cognitive_action_source_ontology_panel import (
    annotation_response_contract,
)
from .provider_telemetry import hash_payload


EVIDENCE_FIRST_PANEL_VERSION = (
    "cognitive_action_evidence_first_external_panel_v0_22"
)
EVIDENCE_FIRST_ADJUDICATION_VERSION = (
    "cognitive_action_evidence_first_external_adjudication_v0_22"
)
LANE_SPECS = (
    ("ANNOTATION_LANE_A", "OpenAI", "GPT-5.6"),
    ("ANNOTATION_LANE_B", "Google", "Gemini-3.1"),
)


def build_evidence_first_external_panel(*, corpus, run):
    validate_evidence_first_holdout(corpus)
    if (
        run.get("run_hash") != hash_payload({
            key: value for key, value in run.items() if key != "run_hash"
        })
        or run.get("source_corpus_hash") != corpus["artifact_hash"]
        or run.get("candidate_outputs_frozen_before_external_reference")
        is not True
    ):
        raise ValueError("evidence_first_panel_run_invalid")
    panel_id = "evidence-first-panel-" + hash_payload([
        EVIDENCE_FIRST_PANEL_VERSION,
        corpus["artifact_hash"],
        run["run_hash"],
    ])[:16]
    packs, bindings = [], {}
    for lane_id, provider, model in LANE_SPECS:
        items, lane_bindings = [], {}
        for source in corpus["public_surface"]["items"]:
            annotation_id = "evidence-first-annotation-" + hash_payload([
                EVIDENCE_FIRST_PANEL_VERSION,
                panel_id,
                lane_id,
                source["conflict_id"],
            ])[:18]
            items.append({
                "annotation_id": annotation_id,
                "public_prompt": source["public_prompt"],
                "candidate_a": source["candidate_a"],
                "candidate_b": source["candidate_b"],
            })
            lane_bindings[annotation_id] = source["conflict_id"]
        items.sort(
            key=lambda item: hash_payload([lane_id, item["annotation_id"]])
        )
        commitment = {
            "panel_version": EVIDENCE_FIRST_PANEL_VERSION,
            "panel_id": panel_id,
            "lane_id": lane_id,
            "expected_annotator": {
                "provider": provider,
                "model": model,
            },
            "source_identity": "WITHHELD",
            "object_family": "WITHHELD",
            "design_stratum": "WITHHELD",
            "candidate_system_outputs": "WITHHELD",
            "challenge_plan": "WITHHELD",
            "witness_receipts": "WITHHELD",
            "prior_scores": "WITHHELD",
            "instructions": (
                "Assess each item independently. Candidate option text is not "
                "definition evidence. Distinguish positive displayed "
                "definition, multi-clause compositional determination, ordinary "
                "soft ambiguity, and a missing named external specification. "
                "Keep semantic selection separate from pragmatic preference. "
                "A justified open or opaque conclusion may be COMPLETE. Return "
                "one coherent five-axis tuple per item."
            ),
            "items": items,
            "response_contract": annotation_response_contract(),
        }
        packs.append({
            **commitment,
            "pack_hash": hash_payload(commitment),
        })
        bindings[lane_id] = lane_bindings
    manifest_commitment = {
        "panel_version": EVIDENCE_FIRST_PANEL_VERSION,
        "panel_id": panel_id,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_surface_hash": corpus["public_surface"]["surface_hash"],
        "frozen_candidate_run_hash": run["run_hash"],
        "candidate_outputs_frozen_before_panel_pack": True,
        "candidate_outputs_exposed_to_annotators": False,
        "challenge_plan_exposed_to_annotators": False,
        "witness_receipts_exposed_to_annotators": False,
        "lane_pack_hashes": {
            pack["lane_id"]: pack["pack_hash"] for pack in packs
        },
        "private_lane_bindings": bindings,
        "candidate_count": corpus["case_count"],
        "criterion_count": len(CRITERIA),
        "current_phase": "AWAITING_GPT_GEMINI_EVIDENCE_FIRST_TUPLES",
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return tuple(packs), {
        **manifest_commitment,
        "manifest_hash": hash_payload(manifest_commitment),
    }


def validate_evidence_first_external_panel(
    *, packs, manifest, source_inputs=None
):
    packs = tuple(packs)
    if manifest.get("manifest_hash") != hash_payload({
        key: value for key, value in manifest.items()
        if key != "manifest_hash"
    }):
        raise ValueError("evidence_first_panel_manifest_hash_invalid")
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
        or manifest.get("challenge_plan_exposed_to_annotators") is not False
        or manifest.get("witness_receipts_exposed_to_annotators") is not False
    ):
        raise ValueError("evidence_first_panel_manifest_invalid")
    lane_ids = []
    for pack in packs:
        ids = {item.get("annotation_id") for item in pack.get("items", [])}
        if (
            pack.get("pack_hash") != hash_payload({
                key: value for key, value in pack.items()
                if key != "pack_hash"
            })
            or len(ids) != manifest["candidate_count"]
            or ids
            != set(manifest["private_lane_bindings"][pack["lane_id"]])
        ):
            raise ValueError("evidence_first_panel_pack_invalid")
        forbidden = (
            "deepseek-r1",
            "baseline_legacy",
            "selective_challenge",
            "support_spans",
            "witness_mode",
        )
        if any(value in str(pack).casefold() for value in forbidden):
            raise ValueError("evidence_first_panel_candidate_leak")
        lane_ids.append(ids)
    if lane_ids[0] & lane_ids[1]:
        raise ValueError("evidence_first_panel_lane_alias_collision")
    if (
        source_inputs is not None
        and (packs, manifest)
        != build_evidence_first_external_panel(**source_inputs)
    ):
        raise ValueError("evidence_first_panel_semantics_invalid")


def validate_evidence_first_annotation_response(response, *, pack):
    contract = annotation_response_contract()
    expected = {
        "panel_version": EVIDENCE_FIRST_PANEL_VERSION,
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
        or not str(response.get("annotation_session_ref", "")).strip()
    ):
        raise ValueError("evidence_first_annotation_binding_invalid")
    ids = {item["annotation_id"] for item in pack["items"]}
    labels = response.get("labels")
    if not isinstance(labels, list) or len(labels) != len(ids):
        raise ValueError("evidence_first_annotation_count_invalid")
    observed = []
    for label in labels:
        if (
            not isinstance(label, dict)
            or set(label) != set(contract["required_label_fields"])
        ):
            raise ValueError("evidence_first_annotation_shape_invalid")
        observed.append(label.get("annotation_id"))
        criteria = label.get("criteria")
        notes = label.get("criterion_notes")
        confidence = label.get("criterion_confidence")
        if (
            label.get("annotation_id") not in ids
            or not isinstance(criteria, dict)
            or set(criteria) != set(CRITERIA)
            or any(
                criteria[key] not in ALLOWED_STATES[key]
                for key in CRITERIA
            )
            or selective_tuple_violations(criteria)
            or not isinstance(notes, dict)
            or set(notes) != set(CRITERIA)
            or any(not str(value).strip() for value in notes.values())
            or not isinstance(confidence, dict)
            or set(confidence) != set(CRITERIA)
            or any(not _confidence(value) for value in confidence.values())
            or not str(label.get("tuple_rationale", "")).strip()
        ):
            raise ValueError("evidence_first_annotation_label_invalid")
    if len(observed) != len(set(observed)) or set(observed) != ids:
        raise ValueError("evidence_first_annotation_ids_invalid")


def build_evidence_first_external_adjudication(
    *, packs, panel_manifest, responses, corpus
):
    packs, responses = tuple(packs), tuple(responses)
    validate_evidence_first_external_panel(
        packs=packs,
        manifest=panel_manifest,
    )
    validate_evidence_first_holdout(corpus)
    pack_index = {pack["lane_id"]: pack for pack in packs}
    response_index = {
        response.get("lane_id"): response for response in responses
    }
    if set(response_index) != set(pack_index):
        raise ValueError("evidence_first_annotation_lanes_invalid")
    for lane, response in response_index.items():
        validate_evidence_first_annotation_response(
            response,
            pack=pack_index[lane],
        )
    labels = {
        lane: {
            panel_manifest["private_lane_bindings"][lane][
                label["annotation_id"]
            ]: label
            for label in response["labels"]
        }
        for lane, response in response_index.items()
    }
    public = {
        item["conflict_id"]: item
        for item in corpus["public_surface"]["items"]
    }
    lanes = sorted(labels)
    agreements, items, bindings = [], [], {}
    for conflict_id in sorted(public):
        current = {lane: labels[lane][conflict_id] for lane in lanes}
        tuples = {lane: current[lane]["criteria"] for lane in lanes}
        annotation_ids = {
            lane: current[lane]["annotation_id"] for lane in lanes
        }
        if len({hash_payload(value) for value in tuples.values()}) == 1:
            agreements.append({
                "conflict_id": conflict_id,
                "selected_tuple": tuples[lanes[0]],
                "lane_annotation_ids": annotation_ids,
                "lane_confidence": {
                    lane: current[lane]["criterion_confidence"]
                    for lane in lanes
                },
            })
            continue
        adjudication_id = "evidence-first-adjudication-" + hash_payload([
            EVIDENCE_FIRST_ADJUDICATION_VERSION,
            panel_manifest["panel_id"],
            conflict_id,
        ])[:18]
        ordered = sorted(
            lanes,
            key=lambda lane: hash_payload([adjudication_id, lane]),
        )
        positions = [{
            "position_id": f"POSITION_{index}",
            "criteria": current[lane]["criteria"],
            "criterion_notes": current[lane]["criterion_notes"],
            "criterion_confidence": current[lane]["criterion_confidence"],
            "tuple_rationale": current[lane]["tuple_rationale"],
        } for index, lane in enumerate(ordered, start=1)]
        source = public[conflict_id]
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
                for index, lane in enumerate(ordered, start=1)
            },
            "lane_annotation_ids": annotation_ids,
        }
    items.sort(key=lambda item: hash_payload([
        panel_manifest["panel_id"],
        item["adjudication_id"],
    ]))
    pack_commitment = {
        "panel_version": EVIDENCE_FIRST_PANEL_VERSION,
        "adjudication_version": EVIDENCE_FIRST_ADJUDICATION_VERSION,
        "panel_id": panel_manifest["panel_id"],
        "expected_adjudicator": {
            "provider": K3_SPEC[0],
            "model": K3_SPEC[1],
        },
        "annotator_identity": "WITHHELD",
        "source_identity": "WITHHELD",
        "object_family": "WITHHELD",
        "design_stratum": "WITHHELD",
        "candidate_system_outputs": "WITHHELD",
        "challenge_plan": "WITHHELD",
        "witness_receipts": "WITHHELD",
        "prior_scores": "WITHHELD",
        "instructions": (
            "Adjudicate each disagreement as one complete five-axis tuple. "
            "Distinguish positive definition, compositional determination, "
            "ordinary soft ambiguity, and missing named specification. "
            "Candidate option text is not evidence. A justified opaque "
            "conclusion may be COMPLETE with selected object NONE. Select one "
            "anonymous position or independently reassess the whole tuple."
        ),
        "items": items,
        "response_contract": {
            "required_top_level": [
                "panel_version", "adjudication_version", "panel_id",
                "adjudication_pack_hash", "adjudicator_provider",
                "adjudicator_model", "adjudication_session_ref",
                "blinding_attestation", "decisions",
            ],
            "required_decision_fields": [
                "adjudication_id", "criteria", "decision_basis",
                "confidence", "rationale",
            ],
            "allowed_bases": [
                "POSITION_1", "POSITION_2", "INDEPENDENT_REASSESSMENT",
            ],
            "required_blinding_attestation": {
                "pack_only_context": True,
                "annotator_identity_unavailable": True,
                "source_identity_unavailable": True,
                "object_family_unavailable": True,
                "design_stratum_unavailable": True,
                "candidate_system_outputs_unavailable": True,
                "prior_scores_unavailable": True,
            },
        },
    }
    pack = {**pack_commitment, "pack_hash": hash_payload(pack_commitment)}
    manifest_commitment = {
        "panel_version": EVIDENCE_FIRST_PANEL_VERSION,
        "adjudication_version": EVIDENCE_FIRST_ADJUDICATION_VERSION,
        "panel_id": panel_manifest["panel_id"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "annotation_response_hashes": {
            lane: hash_payload(response_index[lane])
            for lane in sorted(response_index)
        },
        "adjudication_pack_hash": pack["pack_hash"],
        "agreement_records": agreements,
        "private_disagreement_bindings": bindings,
        "agreement_object_count": len(agreements),
        "disagreement_object_count": len(items),
        "total_object_count": len(agreements) + len(items),
        "reference_state": (
            "AWAITING_KIMI_K3_EVIDENCE_FIRST_FULL_TUPLE_ADJUDICATION"
            if items else "REFERENCE_READY_FROM_FULL_TUPLE_AGREEMENT"
        ),
        "candidate_outputs_exposed_to_adjudicator": False,
        "challenge_plan_exposed_to_adjudicator": False,
        "witness_receipts_exposed_to_adjudicator": False,
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return pack, {
        **manifest_commitment,
        "manifest_hash": hash_payload(manifest_commitment),
    }


def validate_evidence_first_external_adjudication(
    *, pack, manifest, source_inputs=None
):
    ids = {item.get("adjudication_id") for item in pack.get("items", [])}
    if (
        pack.get("pack_hash") != hash_payload({
            key: value for key, value in pack.items() if key != "pack_hash"
        })
        or manifest.get("manifest_hash") != hash_payload({
            key: value for key, value in manifest.items()
            if key != "manifest_hash"
        })
        or manifest.get("adjudication_pack_hash") != pack.get("pack_hash")
        or manifest.get("total_object_count") != 16
        or ids != set(manifest.get("private_disagreement_bindings", {}))
        or manifest.get("candidate_outputs_exposed_to_adjudicator")
        is not False
    ):
        raise ValueError("evidence_first_adjudication_invalid")
    forbidden = (
        "gpt-5.6", "gemini-3.1", "openai", "google", "deepseek-r1",
        "support_spans", "witness_mode", "selective_challenge",
    )
    if any(value in str(pack).casefold() for value in forbidden):
        raise ValueError("evidence_first_adjudication_identity_leak")
    if any(
        {
            position["position_id"]
            for position in item["anonymous_full_tuple_positions"]
        } != {"POSITION_1", "POSITION_2"}
        for item in pack["items"]
    ):
        raise ValueError("evidence_first_adjudication_positions_invalid")
    if (
        source_inputs is not None
        and (pack, manifest)
        != build_evidence_first_external_adjudication(**source_inputs)
    ):
        raise ValueError("evidence_first_adjudication_semantics_invalid")


def validate_evidence_first_adjudication_response(response, *, pack):
    contract = pack["response_contract"]
    expected = {
        "panel_version": EVIDENCE_FIRST_PANEL_VERSION,
        "adjudication_version": EVIDENCE_FIRST_ADJUDICATION_VERSION,
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
        or not str(response.get("adjudication_session_ref", "")).strip()
    ):
        raise ValueError("evidence_first_adjudication_binding_invalid")
    item_index = {
        item["adjudication_id"]: item for item in pack["items"]
    }
    decisions = response.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(item_index):
        raise ValueError("evidence_first_adjudication_count_invalid")
    observed = []
    for decision in decisions:
        if (
            not isinstance(decision, dict)
            or set(decision) != set(contract["required_decision_fields"])
        ):
            raise ValueError("evidence_first_adjudication_shape_invalid")
        adjudication_id = decision.get("adjudication_id")
        observed.append(adjudication_id)
        criteria = decision.get("criteria")
        item = item_index.get(adjudication_id)
        if (
            item is None
            or not isinstance(criteria, dict)
            or set(criteria) != set(CRITERIA)
            or any(
                criteria[key] not in ALLOWED_STATES[key]
                for key in CRITERIA
            )
            or selective_tuple_violations(criteria)
            or decision.get("decision_basis")
            not in contract["allowed_bases"]
            or not _confidence(decision.get("confidence"))
            or not str(decision.get("rationale", "")).strip()
            or len(decision["rationale"]) > 1200
        ):
            raise ValueError("evidence_first_adjudication_decision_invalid")
        positions = {
            position["position_id"]: position["criteria"]
            for position in item["anonymous_full_tuple_positions"]
        }
        if (
            decision["decision_basis"] in positions
            and criteria != positions[decision["decision_basis"]]
        ):
            raise ValueError(
                "evidence_first_adjudication_position_binding_invalid"
            )
    if len(observed) != len(set(observed)) or set(observed) != set(item_index):
        raise ValueError("evidence_first_adjudication_ids_invalid")


def _confidence(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 <= value <= 1
    )
