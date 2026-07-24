"""Reference-first coherent full-tuple model panel and whole-object adjudication v0.15."""

from __future__ import annotations

from collections import Counter

from .clarification_joint_coordinator_contracts import semantic_tuple_violations
from .clarification_reference_first_holdout import validate_reference_first_holdout
from .clarification_semantic_basis_panel import ALLOWED_STATES, CRITERIA, K3_SPEC, LANE_SPECS, RUBRIC
from .provider_telemetry import hash_payload


PANEL_VERSION = "clarification_reference_first_panel_v0_15"
ADJUDICATION_VERSION = "clarification_reference_first_adjudication_v0_15"


def build_reference_first_panel(*, corpus_artifact):
    validate_reference_first_holdout(corpus_artifact)
    panel_id = "reference-first-panel-" + hash_payload([PANEL_VERSION, corpus_artifact["artifact_hash"]])[:16]
    source_items = [item for batch in corpus_artifact["public_surface"]["batches"] for item in batch["conflicts"]]
    packs, bindings = [], {}
    for lane_id, provider, model in LANE_SPECS:
        items, lane_bindings = [], {}
        for source in source_items:
            annotation_id = "reference-first-annotation-" + hash_payload([PANEL_VERSION, panel_id, lane_id, source["conflict_id"]])[:18]
            items.append({
                "annotation_id": annotation_id,
                "public_prompt": source["public_prompt"],
                "candidate_a": source["candidate_a"],
                "candidate_b": source["candidate_b"],
            })
            lane_bindings[annotation_id] = source["conflict_id"]
        items.sort(key=lambda item: hash_payload([lane_id, item["annotation_id"]]))
        commitment = {
            "panel_version": PANEL_VERSION,
            "panel_id": panel_id,
            "lane_id": lane_id,
            "expected_annotator": {"provider": provider, "model": model},
            "source_identity": "WITHHELD",
            "object_family": "WITHHELD",
            "peer_annotation": "WITHHELD",
            "candidate_coordinator_output": "NOT_YET_CREATED",
            "construction_labels": "DO_NOT_EXIST",
            "prior_scores": "WITHHELD",
            "item_order": "LANE_SPECIFIC_HASH_RANDOMIZED",
            "rubric": RUBRIC,
            "instructions": (
                "Assess each semantic object independently from the displayed prompt and candidates. Return one "
                "complete, globally coherent four-criterion tuple per item. Do not label criteria independently: "
                "hard basis requires selected A/B; PRAGMATIC_DEFAULT requires selected NONE and directional "
                "preference A/B; NO_PREFERENCE requires selected NONE and preference NONE; INCOMPLETE requires an "
                "UNCERTAIN basis. A justified open object may still be COMPLETE. Return JSON only."
            ),
            "items": items,
            "response_contract": annotation_response_contract(),
        }
        packs.append({**commitment, "pack_hash": hash_payload(commitment)})
        bindings[lane_id] = lane_bindings
    manifest_commitment = {
        "panel_version": PANEL_VERSION,
        "panel_id": panel_id,
        "source_corpus_hash": corpus_artifact["artifact_hash"],
        "source_surface_hash": corpus_artifact["public_surface"]["surface_hash"],
        "lane_pack_hashes": {pack["lane_id"]: pack["pack_hash"] for pack in packs},
        "private_lane_bindings": bindings,
        "candidate_count": len(source_items),
        "criterion_count": len(CRITERIA),
        "reference_state": "AWAITING_COHERENT_MODEL_ANNOTATIONS",
        "reference_must_precede_candidate_run": True,
        "semantic_labels_present_in_source": False,
        "ground_truth_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return tuple(packs), {**manifest_commitment, "manifest_hash": hash_payload(manifest_commitment)}


def validate_reference_first_panel(*, packs, manifest, corpus_artifact=None):
    packs = tuple(packs)
    mc = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if manifest.get("manifest_hash") != hash_payload(mc):
        raise ValueError("reference_first_panel_manifest_hash_invalid")
    expected = {(lane, provider, model) for lane, provider, model in LANE_SPECS}
    observed = {(pack.get("lane_id"), pack.get("expected_annotator", {}).get("provider"), pack.get("expected_annotator", {}).get("model")) for pack in packs}
    if len(packs) != len(LANE_SPECS) or observed != expected:
        raise ValueError("reference_first_panel_lanes_invalid")
    for pack in packs:
        pc = {key: value for key, value in pack.items() if key != "pack_hash"}
        ids = {item["annotation_id"] for item in pack.get("items", [])}
        if (
            pack.get("pack_hash") != hash_payload(pc)
            or manifest["lane_pack_hashes"].get(pack["lane_id"]) != pack["pack_hash"]
            or ids != set(manifest["private_lane_bindings"].get(pack["lane_id"], {}))
        ):
            raise ValueError("reference_first_panel_pack_binding_invalid")
    if corpus_artifact is not None and (packs, manifest) != build_reference_first_panel(corpus_artifact=corpus_artifact):
        raise ValueError("reference_first_panel_semantics_invalid")


def annotation_response_contract():
    return {
        "required_top_level": ["panel_version", "panel_id", "lane_id", "pack_hash", "annotator_provider", "annotator_model", "annotation_session_ref", "blinding_attestation", "labels"],
        "required_label_fields": ["annotation_id", "criteria", "criterion_notes", "criterion_confidence", "tuple_rationale"],
        "criteria": list(CRITERIA),
        "allowed_states": {criterion: list(states) for criterion, states in ALLOWED_STATES.items()},
        "required_blinding_attestation": {
            "pack_only_context": True,
            "source_identity_unavailable": True,
            "object_family_unavailable": True,
            "peer_annotation_unavailable": True,
            "candidate_coordinator_output_unavailable": True,
            "construction_labels_do_not_exist": True,
            "prior_scores_unavailable": True,
        },
    }


def validate_reference_first_annotation_response(response, *, pack):
    contract = annotation_response_contract()
    if not isinstance(response, dict) or set(response) != set(contract["required_top_level"]):
        raise ValueError("reference_first_annotation_shape_invalid")
    expected = {
        "panel_version": PANEL_VERSION,
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
        raise ValueError("reference_first_annotation_binding_invalid")
    expected_ids = {item["annotation_id"] for item in pack["items"]}
    labels = response.get("labels")
    if not isinstance(labels, list) or len(labels) != len(expected_ids):
        raise ValueError("reference_first_annotation_count_invalid")
    observed = []
    for label in labels:
        if not isinstance(label, dict) or set(label) != set(contract["required_label_fields"]):
            raise ValueError("reference_first_annotation_item_shape_invalid")
        observed.append(label["annotation_id"])
        _validate_criteria(label["criteria"], error="reference_first_annotation_criteria_invalid")
        if set(label["criterion_notes"]) != set(CRITERIA) or any(not isinstance(value, str) or not value.strip() for value in label["criterion_notes"].values()):
            raise ValueError("reference_first_annotation_notes_invalid")
        if set(label["criterion_confidence"]) != set(CRITERIA) or any(not _valid_confidence(value) for value in label["criterion_confidence"].values()):
            raise ValueError("reference_first_annotation_confidence_invalid")
        if not isinstance(label["tuple_rationale"], str) or not label["tuple_rationale"].strip():
            raise ValueError("reference_first_annotation_rationale_invalid")
        if _tuple_violations(label["criteria"]):
            raise ValueError("reference_first_annotation_tuple_incoherent")
    if len(observed) != len(set(observed)) or set(observed) != expected_ids:
        raise ValueError("reference_first_annotation_id_invalid")


def build_reference_first_adjudication(*, packs, panel_manifest, responses):
    packs, responses = tuple(packs), tuple(responses)
    validate_reference_first_panel(packs=packs, manifest=panel_manifest)
    pack_index = {pack["lane_id"]: pack for pack in packs}
    response_index = {response.get("lane_id"): response for response in responses}
    if len(responses) != len(response_index) or set(response_index) != set(pack_index):
        raise ValueError("reference_first_annotation_lanes_invalid")
    for lane, response in response_index.items():
        validate_reference_first_annotation_response(response, pack=pack_index[lane])
    lane_labels = {
        lane: {panel_manifest["private_lane_bindings"][lane][label["annotation_id"]]: label for label in response["labels"]}
        for lane, response in response_index.items()
    }
    public_items = {
        panel_manifest["private_lane_bindings"][packs[0]["lane_id"]][item["annotation_id"]]: item
        for item in packs[0]["items"]
    }
    agreements, items, bindings = [], [], {}
    lanes = sorted(lane_labels)
    for conflict_id in sorted(public_items):
        labels = {lane: lane_labels[lane][conflict_id] for lane in lanes}
        tuples = {lane: labels[lane]["criteria"] for lane in lanes}
        lane_annotation_ids = {lane: labels[lane]["annotation_id"] for lane in lanes}
        if len({hash_payload(value) for value in tuples.values()}) == 1:
            agreements.append({
                "conflict_id": conflict_id,
                "selected_tuple": tuples[lanes[0]],
                "lane_annotation_ids": lane_annotation_ids,
                "lane_confidence": {lane: labels[lane]["criterion_confidence"] for lane in lanes},
            })
            continue
        adjudication_id = "reference-first-adjudication-" + hash_payload([ADJUDICATION_VERSION, panel_manifest["panel_id"], conflict_id])[:18]
        ordered = sorted(lanes, key=lambda lane: hash_payload([adjudication_id, lane]))
        positions = []
        for index, lane in enumerate(ordered):
            label = labels[lane]
            positions.append({
                "position_id": f"POSITION_{index + 1}",
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
            "position_lanes": {f"POSITION_{index + 1}": lane for index, lane in enumerate(ordered)},
            "lane_annotation_ids": lane_annotation_ids,
        }
    items.sort(key=lambda item: hash_payload([panel_manifest["panel_id"], item["adjudication_id"]]))
    pack_commitment = {
        "panel_version": PANEL_VERSION,
        "adjudication_version": ADJUDICATION_VERSION,
        "panel_id": panel_manifest["panel_id"],
        "expected_adjudicator": {"provider": K3_SPEC[0], "model": K3_SPEC[1]},
        "annotator_identity": "WITHHELD",
        "source_identity": "WITHHELD",
        "object_family": "WITHHELD",
        "candidate_coordinator_output": "NOT_YET_CREATED",
        "construction_labels": "DO_NOT_EXIST",
        "prior_scores": "WITHHELD",
        "instructions": (
            "Adjudicate each disagreement as one complete semantic object. Positions are anonymous coherent tuples. "
            "Return one globally coherent tuple; never select or combine criteria independently. You may select a "
            "displayed full position or independently reassess the whole object. Return JSON only."
        ),
        "items": items,
        "response_contract": adjudication_response_contract(),
    }
    pack = {**pack_commitment, "pack_hash": hash_payload(pack_commitment)}
    manifest_commitment = {
        "panel_version": PANEL_VERSION,
        "adjudication_version": ADJUDICATION_VERSION,
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
        "reference_must_precede_candidate_run": True,
        "ground_truth_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return pack, {**manifest_commitment, "manifest_hash": hash_payload(manifest_commitment)}


def validate_reference_first_adjudication(*, pack, manifest, panel_inputs=None):
    pc = {key: value for key, value in pack.items() if key != "pack_hash"}
    mc = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if (
        pack.get("pack_hash") != hash_payload(pc)
        or manifest.get("manifest_hash") != hash_payload(mc)
        or manifest.get("adjudication_pack_hash") != pack.get("pack_hash")
        or manifest.get("total_object_count") != 24
        or set(manifest.get("private_disagreement_bindings", {})) != {item["adjudication_id"] for item in pack.get("items", [])}
    ):
        raise ValueError("reference_first_adjudication_invalid")
    public = str(pack).casefold()
    if any(value in public for value in ("gpt-5.6", "gemini-3.1", "openai", "google", "annotation-lane")):
        raise ValueError("reference_first_adjudication_identity_leak")
    if panel_inputs is not None:
        expected = build_reference_first_adjudication(**panel_inputs)
        if (pack, manifest) != expected:
            raise ValueError("reference_first_adjudication_semantics_invalid")


def adjudication_response_contract():
    return {
        "required_top_level": ["panel_version", "adjudication_version", "panel_id", "adjudication_pack_hash", "adjudicator_provider", "adjudicator_model", "adjudication_session_ref", "blinding_attestation", "decisions"],
        "required_decision_fields": ["adjudication_id", "criteria", "decision_basis", "confidence", "rationale"],
        "allowed_bases": ["POSITION_1", "POSITION_2", "INDEPENDENT_REASSESSMENT"],
        "required_blinding_attestation": {
            "pack_only_context": True,
            "annotator_identity_unavailable": True,
            "source_identity_unavailable": True,
            "object_family_unavailable": True,
            "candidate_coordinator_output_unavailable": True,
            "construction_labels_do_not_exist": True,
            "prior_scores_unavailable": True,
        },
    }


def validate_reference_first_adjudication_response(response, *, pack):
    contract = adjudication_response_contract()
    if not isinstance(response, dict) or set(response) != set(contract["required_top_level"]):
        raise ValueError("reference_first_adjudication_response_shape_invalid")
    expected = {
        "panel_version": PANEL_VERSION,
        "adjudication_version": ADJUDICATION_VERSION,
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
        raise ValueError("reference_first_adjudication_response_binding_invalid")
    index = {item["adjudication_id"]: item for item in pack["items"]}
    decisions = response.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(index):
        raise ValueError("reference_first_adjudication_decision_count_invalid")
    observed = []
    for decision in decisions:
        if not isinstance(decision, dict) or set(decision) != set(contract["required_decision_fields"]):
            raise ValueError("reference_first_adjudication_decision_shape_invalid")
        adjudication_id = decision["adjudication_id"]
        observed.append(adjudication_id)
        item = index.get(adjudication_id)
        _validate_criteria(decision.get("criteria"), error="reference_first_adjudication_decision_invalid")
        if (
            not item
            or decision.get("decision_basis") not in contract["allowed_bases"]
            or not _valid_confidence(decision.get("confidence"))
            or not isinstance(decision.get("rationale"), str)
            or not decision["rationale"].strip()
        ):
            raise ValueError("reference_first_adjudication_decision_invalid")
        if _tuple_violations(decision["criteria"]):
            raise ValueError("reference_first_adjudication_tuple_incoherent")
        positions = {position["position_id"]: position["criteria"] for position in item["anonymous_full_tuple_positions"]}
        if decision["decision_basis"] in positions and decision["criteria"] != positions[decision["decision_basis"]]:
            raise ValueError("reference_first_adjudication_position_invalid")
    if len(observed) != len(set(observed)) or set(observed) != set(index):
        raise ValueError("reference_first_adjudication_id_invalid")


def build_reference_first_reference(*, adjudication_pack, adjudication_manifest, response=None):
    validate_reference_first_adjudication(pack=adjudication_pack, manifest=adjudication_manifest)
    if adjudication_pack["items"]:
        if response is None:
            raise ValueError("reference_first_adjudication_response_required")
        validate_reference_first_adjudication_response(response, pack=adjudication_pack)
    decisions = {decision["adjudication_id"]: decision for decision in (response or {"decisions": []})["decisions"]}
    labels = []
    for agreement in adjudication_manifest["agreement_records"]:
        labels.append({
            "conflict_id": agreement["conflict_id"],
            "criteria": agreement["selected_tuple"],
            "tuple_source": "GPT_GEMINI_FULL_TUPLE_AGREEMENT",
        })
    for adjudication_id, binding in adjudication_manifest["private_disagreement_bindings"].items():
        labels.append({
            "conflict_id": binding["conflict_id"],
            "criteria": decisions[adjudication_id]["criteria"],
            "tuple_source": "KIMI_K3_FULL_TUPLE_ADJUDICATION",
        })
    labels.sort(key=lambda item: item["conflict_id"])
    if len(labels) != 24 or any(_tuple_violations(label["criteria"]) for label in labels):
        raise ValueError("reference_first_reference_coherence_invalid")
    commitment = {
        "panel_version": PANEL_VERSION,
        "adjudication_version": ADJUDICATION_VERSION,
        "panel_id": adjudication_pack["panel_id"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_response_hash": hash_payload(response) if response is not None else None,
        "labels": labels,
        "object_count": len(labels),
        "label_count": len(labels) * len(CRITERIA),
        "cross_axis_coherence_passed": True,
        "cross_axis_inconsistency_count": 0,
        "candidate_state": "REFERENCE_FIRST_MODEL_PANEL_CANDIDATE",
        "frozen_before_candidate_run": True,
        "ground_truth_claim": False,
        "human_gold_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_reference_first_reference(artifact, *, source_inputs=None):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    labels = artifact.get("labels", [])
    labels_valid = isinstance(labels, list) and len(labels) == 24 and len({label.get("conflict_id") for label in labels if isinstance(label, dict)}) == 24
    if labels_valid:
        for label in labels:
            try:
                _validate_criteria(label.get("criteria"), error="reference_first_reference_invalid")
            except ValueError:
                labels_valid = False
                break
            if _tuple_violations(label["criteria"]):
                labels_valid = False
                break
    if (
        artifact.get("artifact_hash") != hash_payload(commitment)
        or artifact.get("panel_version") != PANEL_VERSION
        or artifact.get("object_count") != 24
        or artifact.get("label_count") != 24 * len(CRITERIA)
        or artifact.get("cross_axis_coherence_passed") is not True
        or artifact.get("cross_axis_inconsistency_count") != 0
        or not labels_valid
        or artifact.get("frozen_before_candidate_run") is not True
        or any(artifact.get(key) is not False for key in ("action_credit_authority", "selection_authority", "retention_authority", "production_authority"))
    ):
        raise ValueError("reference_first_reference_invalid")
    if source_inputs is not None and artifact != build_reference_first_reference(**source_inputs):
        raise ValueError("reference_first_reference_semantics_invalid")


def build_reference_first_agreement_analysis(
    *, corpus_artifact, panel_manifest, responses, adjudication_pack, adjudication_manifest
):
    responses = tuple(responses)
    validate_reference_first_holdout(corpus_artifact)
    response_index = {response["lane_id"]: response for response in responses}
    if len(responses) != len(response_index) or set(response_index) != set(panel_manifest["private_lane_bindings"]):
        raise ValueError("reference_first_analysis_lanes_invalid")
    validate_reference_first_adjudication(pack=adjudication_pack, manifest=adjudication_manifest)
    lane_labels = {
        lane: {panel_manifest["private_lane_bindings"][lane][label["annotation_id"]]: label for label in response["labels"]}
        for lane, response in response_index.items()
    }
    lanes = sorted(lane_labels)
    provenance = corpus_artifact["private_provenance"]["bindings"]
    criterion_agreement = Counter()
    disagreement_axis_count = Counter()
    disagreement_axis_sets = Counter()
    disagreement_families = Counter()
    disagreement_classes = Counter()
    lane_state_counts = {lane: {criterion: Counter() for criterion in CRITERIA} for lane in lanes}
    lane_confidence = {lane: {criterion: [] for criterion in CRITERIA} for lane in lanes}
    rows = []
    for conflict_id in sorted(provenance):
        labels = {lane: lane_labels[lane][conflict_id] for lane in lanes}
        differing = []
        for criterion in CRITERIA:
            states = [labels[lane]["criteria"][criterion] for lane in lanes]
            if len(set(states)) == 1:
                criterion_agreement[criterion] += 1
            else:
                differing.append(criterion)
            for lane in lanes:
                lane_state_counts[lane][criterion][labels[lane]["criteria"][criterion]] += 1
                lane_confidence[lane][criterion].append(labels[lane]["criterion_confidence"][criterion])
        if differing:
            disagreement_axis_count[len(differing)] += 1
            disagreement_axis_sets["+".join(differing)] += 1
            disagreement_families[provenance[conflict_id]["object_family"]] += 1
            basis_states = {labels[lane]["criteria"]["SELECTION_BASIS"] for lane in lanes}
            disagreement_class = (
                "HARD_BASIS_GRANULARITY_ONLY"
                if differing == ["SELECTION_BASIS"] and basis_states == {"LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT"}
                else "MATERIAL_SEMANTIC_COMMITMENT"
            )
            disagreement_classes[disagreement_class] += 1
        else:
            disagreement_class = "FULL_TUPLE_AGREEMENT"
        rows.append({
            "conflict_id": conflict_id,
            "case_id": provenance[conflict_id]["case_id"],
            "object_family": provenance[conflict_id]["object_family"],
            "full_tuple_agreement": not differing,
            "differing_criteria": differing,
            "disagreement_class": disagreement_class,
        })
    tuple_agreement_count = adjudication_manifest["agreement_object_count"]
    tuple_disagreement_count = adjudication_manifest["disagreement_object_count"]
    observations = [
        f"Both annotation lanes returned {len(rows)} schema-valid, globally coherent full tuples.",
        f"Full-tuple agreement is {tuple_agreement_count}/{len(rows)}; {tuple_disagreement_count} objects require whole-object adjudication.",
        "Criterion agreement counts are " + ", ".join(f"{criterion} {criterion_agreement[criterion]}/{len(rows)}" for criterion in CRITERIA) + ".",
        "Disagreement objects by family are " + (", ".join(f"{family} {count}" for family, count in sorted(disagreement_families.items())) or "none") + ".",
        f"Of the {tuple_disagreement_count} object disagreements, {disagreement_classes.get('HARD_BASIS_GRANULARITY_ONLY', 0)} are lexical-versus-compositional hard-basis boundaries and {disagreement_classes.get('MATERIAL_SEMANTIC_COMMITMENT', 0)} change a substantive semantic commitment.",
    ]
    interpretations = [
        "Because each lane is coherent before comparison, every disagreement is semantic rather than a tuple-assembly artifact.",
        "Whole-tuple agreement is the relevant reference-readiness measure; high cell agreement cannot substitute for object-level agreement.",
        "Family concentration can guide later role specialization, but it must not alter this frozen holdout or its adjudication rubric.",
    ]
    unknowns = [
        "Disagreement objects have no reference label until blinded Kimi-K3 whole-object adjudication is returned.",
        "Model-panel output is candidate reference evidence, not human gold or real-world ground truth.",
        "Coordinator performance remains unobserved because candidate execution is still disabled.",
    ]
    intuition_triggers = [
        "If disagreements cluster by object family, cognitive roles may need structure-specific competence rather than generic critic labels.",
        "A reference-first protocol separates evaluator uncertainty from coordinator error instead of charging both to the runtime candidate.",
        "The number of simultaneously differing axes is a direct measure of how strongly semantic commitments are coupled inside an object.",
    ]
    commitment = {
        "analysis_version": "clarification_reference_first_agreement_analysis_v0_15",
        "source_corpus_hash": corpus_artifact["artifact_hash"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "annotation_response_hashes": {lane: hash_payload(response_index[lane]) for lane in lanes},
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "object_count": len(rows),
        "full_tuple_agreement_count": tuple_agreement_count,
        "full_tuple_disagreement_count": tuple_disagreement_count,
        "full_tuple_agreement_rate": tuple_agreement_count / len(rows),
        "criterion_agreement_counts": {criterion: criterion_agreement[criterion] for criterion in CRITERIA},
        "criterion_agreement_rates": {criterion: criterion_agreement[criterion] / len(rows) for criterion in CRITERIA},
        "disagreement_object_counts_by_axis_count": dict(sorted(disagreement_axis_count.items())),
        "disagreement_object_counts_by_axis_set": dict(sorted(disagreement_axis_sets.items())),
        "disagreement_object_counts_by_family": dict(sorted(disagreement_families.items())),
        "disagreement_object_counts_by_class": dict(sorted(disagreement_classes.items())),
        "lane_state_counts": {lane: {criterion: dict(sorted(counter.items())) for criterion, counter in values.items()} for lane, values in lane_state_counts.items()},
        "lane_mean_criterion_confidence": {lane: {criterion: sum(values) / len(values) for criterion, values in criteria.items()} for lane, criteria in lane_confidence.items()},
        "rows": rows,
        "observations": observations,
        "interpretations": interpretations,
        "unknowns": unknowns,
        "intuition_triggers": intuition_triggers,
        "next_required_evidence": "KIMI_K3_WHOLE_OBJECT_ADJUDICATION",
        "candidate_state": "REFERENCE_FIRST_PANEL_DISAGREEMENT_DIAGNOSTIC_ONLY",
        "candidate_run_allowed": False,
        "ground_truth_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_reference_first_agreement_analysis(
    artifact, *, corpus_artifact, panel_manifest, responses, adjudication_pack, adjudication_manifest
):
    expected = build_reference_first_agreement_analysis(
        corpus_artifact=corpus_artifact,
        panel_manifest=panel_manifest,
        responses=responses,
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
    )
    if artifact != expected:
        raise ValueError("reference_first_agreement_analysis_invalid")


def render_reference_first_agreement_analysis(analysis):
    lines = ["# Reference-First Full-Tuple Panel v0.15 Agreement Analysis", ""]
    for title, key in (
        ("Observations", "observations"),
        ("Interpretations", "interpretations"),
        ("Unknowns", "unknowns"),
        ("Intuition Triggers", "intuition_triggers"),
    ):
        lines.extend((f"## {title}", ""))
        lines.extend(f"- {value}" for value in analysis[key])
        lines.append("")
    lines.extend((
        f"Next evidence: `{analysis['next_required_evidence']}`",
        f"State: `{analysis['candidate_state']}`",
        f"Artifact hash: `{analysis['artifact_hash']}`",
        "",
    ))
    return "\n".join(lines)


def build_reference_first_final_analysis(
    *, corpus_artifact, agreement_analysis, adjudication_pack, adjudication_manifest, response, reference
):
    validate_reference_first_holdout(corpus_artifact)
    validate_reference_first_adjudication(pack=adjudication_pack, manifest=adjudication_manifest)
    validate_reference_first_adjudication_response(response, pack=adjudication_pack)
    validate_reference_first_reference(
        reference,
        source_inputs={
            "adjudication_pack": adjudication_pack,
            "adjudication_manifest": adjudication_manifest,
            "response": response,
        },
    )
    agreement_commitment = {key: value for key, value in agreement_analysis.items() if key != "artifact_hash"}
    if (
        agreement_analysis.get("artifact_hash") != hash_payload(agreement_commitment)
        or agreement_analysis.get("adjudication_pack_hash") != adjudication_pack.get("pack_hash")
        or agreement_analysis.get("adjudication_manifest_hash") != adjudication_manifest.get("manifest_hash")
        or reference.get("adjudication_response_hash") != hash_payload(response)
    ):
        raise ValueError("reference_first_final_analysis_lineage_invalid")
    decisions = {decision["adjudication_id"]: decision for decision in response["decisions"]}
    rows = {row["conflict_id"]: row for row in agreement_analysis["rows"]}
    decision_basis_counts = Counter()
    source_lane_counts = Counter()
    adjudication_counts_by_class = Counter()
    hard_basis_outcomes = Counter()
    decision_records = []
    for adjudication_id, binding in adjudication_manifest["private_disagreement_bindings"].items():
        decision = decisions[adjudication_id]
        conflict_id = binding["conflict_id"]
        disagreement_class = rows[conflict_id]["disagreement_class"]
        decision_basis_counts[decision["decision_basis"]] += 1
        adjudication_counts_by_class[disagreement_class] += 1
        if disagreement_class == "HARD_BASIS_GRANULARITY_ONLY":
            hard_basis_outcomes[decision["criteria"]["SELECTION_BASIS"]] += 1
        selected_lane = binding["position_lanes"].get(decision["decision_basis"])
        if selected_lane is not None:
            source_lane_counts[selected_lane] += 1
        decision_records.append({
            "adjudication_id": adjudication_id,
            "conflict_id": conflict_id,
            "case_id": rows[conflict_id]["case_id"],
            "object_family": rows[conflict_id]["object_family"],
            "disagreement_class": disagreement_class,
            "decision_basis": decision["decision_basis"],
            "selected_source_lane": selected_lane or "INDEPENDENT_REASSESSMENT",
            "selected_tuple": decision["criteria"],
            "confidence": decision["confidence"],
        })
    confidences = [decision["confidence"] for decision in response["decisions"]]
    reference_state_counts = {criterion: Counter() for criterion in CRITERIA}
    reference_source_counts = Counter()
    for label in reference["labels"]:
        reference_source_counts[label["tuple_source"]] += 1
        for criterion in CRITERIA:
            reference_state_counts[criterion][label["criteria"][criterion]] += 1
    observations = [
        f"Kimi-K3 returned {len(response['decisions'])} complete adjudication tuples; all pass position binding and global coherence validation.",
        f"The frozen reference contains {reference['object_count']} coherent objects: {reference_source_counts.get('GPT_GEMINI_FULL_TUPLE_AGREEMENT', 0)} from dual-model agreement and {reference_source_counts.get('KIMI_K3_FULL_TUPLE_ADJUDICATION', 0)} from whole-object adjudication.",
        f"Kimi-K3 selected a displayed anonymous full position in {sum(source_lane_counts.values())}/{len(response['decisions'])} disputes; mean confidence is {sum(confidences) / len(confidences):.3f}.",
        f"For the five hard-basis granularity disputes, outcomes are {dict(sorted(hard_basis_outcomes.items()))}.",
    ]
    interpretations = [
        "Whole-object adjudication closes the reference without creating any cross-axis contradiction or criterion-splicing artifact.",
        "The lexical-versus-compositional boundary remains genuinely unstable across otherwise identical semantic commitments, supporting later ontology-factorization analysis.",
        "The four material disputes show that object selection, pragmatic default, and assessment completeness require different coordination moves rather than one generic uncertainty rule.",
    ]
    unknowns = [
        "The frozen reference remains a model-panel candidate rather than human gold or real-world truth.",
        "Kimi-K3 confidence is moderate and has not been calibrated against an independent outcome source.",
        "Local specialist roles and the DeepSeek coordinator have not yet seen this fresh surface, so cognitive gain and cost remain unknown.",
    ]
    intuition_triggers = [
        "Reference formation itself behaves like a small cognitive organization: independent coherent positions first, object-level integration second.",
        "Evidence form and semantic commitment may need separate state dimensions so proof-style disputes do not masquerade as object disputes.",
        "Freezing evaluator uncertainty before candidate execution creates a clean place to measure whether coordination repairs role errors or merely echoes evaluator conventions.",
    ]
    commitment = {
        "analysis_version": "clarification_reference_first_final_analysis_v0_15",
        "source_corpus_hash": corpus_artifact["artifact_hash"],
        "agreement_analysis_hash": agreement_analysis["artifact_hash"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "adjudication_response_hash": hash_payload(response),
        "frozen_reference_hash": reference["artifact_hash"],
        "decision_basis_counts": dict(sorted(decision_basis_counts.items())),
        "selected_source_lane_counts": dict(sorted(source_lane_counts.items())),
        "adjudication_counts_by_class": dict(sorted(adjudication_counts_by_class.items())),
        "hard_basis_granularity_outcomes": dict(sorted(hard_basis_outcomes.items())),
        "mean_adjudication_confidence": sum(confidences) / len(confidences),
        "reference_tuple_source_counts": dict(sorted(reference_source_counts.items())),
        "reference_state_counts": {criterion: dict(sorted(counter.items())) for criterion, counter in reference_state_counts.items()},
        "decision_records": sorted(decision_records, key=lambda item: item["conflict_id"]),
        "observations": observations,
        "interpretations": interpretations,
        "unknowns": unknowns,
        "intuition_triggers": intuition_triggers,
        "next_required_evidence": "LOCAL_SPECIALIST_ROLE_OUTPUTS_ON_FROZEN_SURFACE",
        "candidate_state": "REFERENCE_FIRST_MODEL_PANEL_REFERENCE_FROZEN",
        "local_role_collection_allowed": True,
        "coordinator_run_allowed": False,
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_reference_first_final_analysis(
    artifact, *, corpus_artifact, agreement_analysis, adjudication_pack, adjudication_manifest, response, reference
):
    expected = build_reference_first_final_analysis(
        corpus_artifact=corpus_artifact,
        agreement_analysis=agreement_analysis,
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
        response=response,
        reference=reference,
    )
    if artifact != expected:
        raise ValueError("reference_first_final_analysis_invalid")


def render_reference_first_final_analysis(analysis):
    lines = ["# Reference-First Model Panel v0.15 Final Analysis", ""]
    for title, key in (
        ("Observations", "observations"),
        ("Interpretations", "interpretations"),
        ("Unknowns", "unknowns"),
        ("Intuition Triggers", "intuition_triggers"),
    ):
        lines.extend((f"## {title}", ""))
        lines.extend(f"- {value}" for value in analysis[key])
        lines.append("")
    lines.extend((
        f"Next evidence: `{analysis['next_required_evidence']}`",
        f"State: `{analysis['candidate_state']}`",
        f"Artifact hash: `{analysis['artifact_hash']}`",
        "",
    ))
    return "\n".join(lines)


def _validate_criteria(criteria, *, error):
    if not isinstance(criteria, dict) or set(criteria) != set(CRITERIA) or any(criteria[criterion] not in ALLOWED_STATES[criterion] for criterion in CRITERIA):
        raise ValueError(error)


def _tuple_violations(criteria):
    return semantic_tuple_violations(
        selected=criteria["SELECTED_OBJECT"],
        basis=criteria["SELECTION_BASIS"],
        preference=criteria["PRAGMATIC_PREFERENCE"],
        completeness=criteria["AXIS_ASSESSMENT_COMPLETE"],
    )


def _valid_confidence(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1
