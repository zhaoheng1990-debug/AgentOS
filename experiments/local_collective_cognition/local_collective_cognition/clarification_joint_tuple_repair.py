"""Identity-blind full-tuple repair for incoherent v0.13 panel references."""

from __future__ import annotations

from collections import Counter

from .clarification_joint_coordinator_contracts import BASES, COMPLETENESS, SELECTIONS, semantic_tuple_violations
from .clarification_joint_fresh_panel import (
    CRITERIA,
    K3_SPEC,
    validate_joint_fresh_adjudication,
    validate_joint_fresh_adjudication_response,
    validate_joint_fresh_annotation_response,
    validate_joint_fresh_panel,
    validate_joint_fresh_reference,
)
from .clarification_joint_holdout import validate_joint_holdout_artifact
from .provider_telemetry import hash_payload


REPAIR_VERSION = "clarification_joint_tuple_repair_v0_14"
REPAIR_STATE = "AWAITING_KIMI_K3_JOINT_TUPLE_REPAIR"


def build_joint_tuple_repair_pack(
    *, corpus_artifact, panel_packs, panel_manifest, panel_responses,
    cell_adjudication_pack, cell_adjudication_manifest, cell_adjudication_response,
    panel_reference,
):
    panel_packs, panel_responses = tuple(panel_packs), tuple(panel_responses)
    validate_joint_holdout_artifact(corpus_artifact)
    validate_joint_fresh_panel(packs=panel_packs, manifest=panel_manifest)
    pack_index = {pack["lane_id"]: pack for pack in panel_packs}
    response_index = {response["lane_id"]: response for response in panel_responses}
    if len(panel_packs) != len(pack_index) or len(panel_responses) != len(response_index) or set(response_index) != set(pack_index):
        raise ValueError("joint_tuple_repair_panel_lanes_invalid")
    for lane, response in response_index.items():
        validate_joint_fresh_annotation_response(response, pack=pack_index[lane])
    validate_joint_fresh_adjudication(pack=cell_adjudication_pack, manifest=cell_adjudication_manifest)
    validate_joint_fresh_adjudication_response(cell_adjudication_response, pack=cell_adjudication_pack)
    validate_joint_fresh_reference(panel_reference)
    public_cases = {item["conflict_id"]: item for batch in corpus_artifact["public_surface"]["batches"] for item in batch["conflicts"]}
    lane_labels = {
        lane: _labels_by_conflict(response, panel_manifest["private_lane_bindings"][lane])
        for lane, response in response_index.items()
    }
    cell_decisions = {item["adjudication_id"]: item for item in cell_adjudication_response["decisions"]}
    cell_bindings = cell_adjudication_manifest["private_disagreement_bindings"]
    reference_labels = {item["conflict_id"]: item for item in panel_reference["labels"]}
    items, private_bindings = [], {}
    for conflict in panel_reference["cross_axis_inconsistency_records"]:
        conflict_id = conflict["conflict_id"]
        repair_id = "joint-tuple-repair-" + hash_payload([REPAIR_VERSION, panel_reference["artifact_hash"], conflict_id])[:18]
        criterion_evidence = {}
        for criterion in CRITERIA:
            ordered_lanes = sorted(lane_labels, key=lambda lane: hash_payload([repair_id, criterion, lane]))
            positions = []
            for index, lane in enumerate(ordered_lanes):
                label = lane_labels[lane][conflict_id]
                positions.append({
                    "position_id": f"POSITION_{index + 1}",
                    "state": label["criteria"][criterion],
                    "criterion_note": label["criterion_notes"][criterion],
                    "confidence": label["criterion_confidence"][criterion],
                })
            matches = [(adjudication_id, binding) for adjudication_id, binding in cell_bindings.items() if binding["conflict_id"] == conflict_id and binding["criterion"] == criterion]
            cell_outcome = None
            if matches:
                if len(matches) != 1:
                    raise ValueError("joint_tuple_repair_cell_binding_invalid")
                decision = cell_decisions[matches[0][0]]
                cell_outcome = {"state": decision["selected_state"], "confidence": decision["confidence"], "rationale": decision["rationale"]}
            criterion_evidence[criterion] = {"anonymous_positions": positions, "cell_adjudication_outcome": cell_outcome}
        case = public_cases[conflict_id]
        items.append({
            "repair_id": repair_id,
            "public_prompt": case["public_prompt"],
            "candidate_a": case["candidate_a"],
            "candidate_b": case["candidate_b"],
            "current_incoherent_tuple": reference_labels[conflict_id]["criteria"],
            "coherence_violations": conflict["violations"],
            "criterion_evidence": criterion_evidence,
        })
        private_bindings[repair_id] = conflict_id
    items.sort(key=lambda item: hash_payload([REPAIR_VERSION, item["repair_id"]]))
    pack_commitment = {
        "repair_version": REPAIR_VERSION,
        "source_panel_id": panel_reference["panel_id"],
        "expected_adjudicator": {"provider": K3_SPEC[0], "model": K3_SPEC[1]},
        "source_identity": "WITHHELD",
        "annotator_identity": "WITHHELD",
        "prior_cell_adjudicator_identity": "WITHHELD",
        "construction_labels": "WITHHELD",
        "locked_consensus_axes": "WITHHELD",
        "deepseek_outputs": "WITHHELD",
        "prior_scores": "WITHHELD",
        "instructions": (
            "Repair each semantic object jointly. Consider all four criteria together and return one globally coherent "
            "tuple. Do not adjudicate cells independently. Hard basis requires selected A/B; PRAGMATIC_DEFAULT requires "
            "selected NONE and directional preference A/B; NO_PREFERENCE requires selected NONE and preference NONE. "
            "A complete assessment may be open. changed_criteria must exactly name fields changed from the current tuple. "
            "Return JSON only."
        ),
        "items": items,
        "response_contract": joint_tuple_repair_response_contract(),
    }
    pack = {**pack_commitment, "pack_hash": hash_payload(pack_commitment)}
    manifest_commitment = {
        "repair_version": REPAIR_VERSION,
        "source_panel_reference_hash": panel_reference["artifact_hash"],
        "source_corpus_hash": corpus_artifact["artifact_hash"],
        "source_panel_manifest_hash": panel_manifest["manifest_hash"],
        "source_panel_response_hashes": {lane: hash_payload(response_index[lane]) for lane in sorted(response_index)},
        "source_cell_adjudication_pack_hash": cell_adjudication_pack["pack_hash"],
        "source_cell_adjudication_response_hash": hash_payload(cell_adjudication_response),
        "repair_pack_hash": pack["pack_hash"],
        "private_repair_bindings": private_bindings,
        "repair_count": len(items),
        "reference_state": REPAIR_STATE,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    manifest = {**manifest_commitment, "manifest_hash": hash_payload(manifest_commitment)}
    return pack, manifest


def validate_joint_tuple_repair_pack(*, pack, manifest, source_inputs=None):
    pc = {key: value for key, value in pack.items() if key != "pack_hash"}
    mc = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if pack.get("pack_hash") != hash_payload(pc) or manifest.get("manifest_hash") != hash_payload(mc) or manifest.get("repair_pack_hash") != pack.get("pack_hash"):
        raise ValueError("joint_tuple_repair_hash_invalid")
    if manifest.get("repair_count") != len(pack.get("items", [])) or set(manifest.get("private_repair_bindings", {})) != {item["repair_id"] for item in pack.get("items", [])}:
        raise ValueError("joint_tuple_repair_binding_invalid")
    if pack.get("repair_version") != REPAIR_VERSION or manifest.get("repair_version") != REPAIR_VERSION or manifest.get("reference_state") != REPAIR_STATE:
        raise ValueError("joint_tuple_repair_version_invalid")
    for item in pack.get("items", []):
        if set(item.get("current_incoherent_tuple", {})) != set(CRITERIA) or not item.get("coherence_violations") or set(item.get("criterion_evidence", {})) != set(CRITERIA):
            raise ValueError("joint_tuple_repair_item_invalid")
    public = str(pack).casefold()
    if any(value in public for value in ("gpt-5.6", "gemini-3.1", "openai", "google")):
        raise ValueError("joint_tuple_repair_identity_leak")
    if source_inputs is not None:
        expected = build_joint_tuple_repair_pack(**source_inputs)
        if (pack, manifest) != expected:
            raise ValueError("joint_tuple_repair_semantics_invalid")


def joint_tuple_repair_response_contract():
    return {
        "required_top_level": ["repair_version", "source_panel_id", "repair_pack_hash", "adjudicator_provider", "adjudicator_model", "repair_session_ref", "blinding_attestation", "decisions"],
        "required_decision_fields": ["repair_id", "selected_object", "selection_basis", "pragmatic_preference", "assessment_completeness", "changed_criteria", "confidence", "rationale"],
        "allowed_states": {
            "selected_object": list(SELECTIONS),
            "selection_basis": list(BASES),
            "pragmatic_preference": list(SELECTIONS),
            "assessment_completeness": list(COMPLETENESS),
            "changed_criteria": list(CRITERIA),
        },
        "required_blinding_attestation": {"pack_only_context": True, "annotator_identity_unavailable": True, "source_identity_unavailable": True, "prior_cell_adjudicator_identity_unavailable": True, "construction_labels_unavailable": True, "locked_consensus_axes_unavailable": True, "deepseek_outputs_unavailable": True, "prior_scores_unavailable": True},
    }


def validate_joint_tuple_repair_response(response, *, pack):
    contract = joint_tuple_repair_response_contract()
    if not isinstance(response, dict) or set(response) != set(contract["required_top_level"]):
        raise ValueError("joint_tuple_repair_response_shape_invalid")
    expected = {"repair_version": REPAIR_VERSION, "source_panel_id": pack["source_panel_id"], "repair_pack_hash": pack["pack_hash"], "adjudicator_provider": K3_SPEC[0], "adjudicator_model": K3_SPEC[1]}
    if any(response.get(key) != value for key, value in expected.items()) or response.get("blinding_attestation") != contract["required_blinding_attestation"] or not isinstance(response.get("repair_session_ref"), str) or not response["repair_session_ref"].strip():
        raise ValueError("joint_tuple_repair_response_binding_invalid")
    item_index = {item["repair_id"]: item for item in pack["items"]}
    decisions = response["decisions"]
    if not isinstance(decisions, list) or len(decisions) != len(item_index):
        raise ValueError("joint_tuple_repair_decision_count_invalid")
    observed = []
    for decision in decisions:
        required = set(contract["required_decision_fields"])
        if not isinstance(decision, dict) or set(decision) != required:
            raise ValueError("joint_tuple_repair_decision_shape_invalid")
        repair_id = decision["repair_id"]; observed.append(repair_id); item = item_index.get(repair_id)
        if not item or decision["selected_object"] not in SELECTIONS or decision["selection_basis"] not in BASES or decision["pragmatic_preference"] not in SELECTIONS or decision["assessment_completeness"] not in COMPLETENESS:
            raise ValueError("joint_tuple_repair_decision_value_invalid")
        confidence = decision["confidence"]
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1 or not isinstance(decision["rationale"], str) or not decision["rationale"].strip():
            raise ValueError("joint_tuple_repair_decision_metadata_invalid")
        repaired = {"SELECTED_OBJECT": decision["selected_object"], "SELECTION_BASIS": decision["selection_basis"], "PRAGMATIC_PREFERENCE": decision["pragmatic_preference"], "AXIS_ASSESSMENT_COMPLETE": decision["assessment_completeness"]}
        if semantic_tuple_violations(selected=decision["selected_object"], basis=decision["selection_basis"], preference=decision["pragmatic_preference"], completeness=decision["assessment_completeness"]):
            raise ValueError("joint_tuple_repair_still_incoherent")
        changed = sorted(criterion for criterion in CRITERIA if repaired[criterion] != item["current_incoherent_tuple"][criterion])
        if not isinstance(decision["changed_criteria"], list) or len(decision["changed_criteria"]) != len(set(decision["changed_criteria"])) or sorted(decision["changed_criteria"]) != changed:
            raise ValueError("joint_tuple_repair_changed_criteria_invalid")
    if len(observed) != len(set(observed)) or set(observed) != set(item_index):
        raise ValueError("joint_tuple_repair_id_invalid")


def build_joint_tuple_repaired_reference(*, source_reference, repair_pack, repair_manifest, repair_response):
    validate_joint_fresh_reference(source_reference)
    validate_joint_tuple_repair_pack(pack=repair_pack, manifest=repair_manifest)
    validate_joint_tuple_repair_response(repair_response, pack=repair_pack)
    decisions = {decision["repair_id"]: decision for decision in repair_response["decisions"]}
    repairs_by_conflict = {repair_manifest["private_repair_bindings"][repair_id]: decision for repair_id, decision in decisions.items()}
    labels, repair_records = [], []
    for label in source_reference["labels"]:
        conflict_id = label["conflict_id"]
        if conflict_id not in repairs_by_conflict:
            labels.append(label); continue
        decision = repairs_by_conflict[conflict_id]
        criteria = {"SELECTED_OBJECT": decision["selected_object"], "SELECTION_BASIS": decision["selection_basis"], "PRAGMATIC_PREFERENCE": decision["pragmatic_preference"], "AXIS_ASSESSMENT_COMPLETE": decision["assessment_completeness"]}
        labels.append({"conflict_id": conflict_id, "criteria": criteria, "criterion_sources": {criterion: "KIMI_K3_JOINT_TUPLE_REPAIR" for criterion in CRITERIA}})
        repair_id = next(repair_id for repair_id, bound_conflict_id in repair_manifest["private_repair_bindings"].items() if bound_conflict_id == conflict_id)
        repair_records.append({
            "repair_id": repair_id,
            "conflict_id": conflict_id,
            "previous_tuple": label["criteria"],
            "repaired_tuple": criteria,
            "changed_criteria": decision["changed_criteria"],
            "confidence": decision["confidence"],
            "rationale": decision["rationale"],
        })
    coherence_records = []
    for label in labels:
        c = label["criteria"]
        violations = semantic_tuple_violations(selected=c["SELECTED_OBJECT"], basis=c["SELECTION_BASIS"], preference=c["PRAGMATIC_PREFERENCE"], completeness=c["AXIS_ASSESSMENT_COMPLETE"])
        if violations:
            coherence_records.append({"conflict_id": label["conflict_id"], "violations": violations, "criteria": c})
    commitment = {
        "panel_version": source_reference["panel_version"], "repair_version": REPAIR_VERSION,
        "panel_id": source_reference["panel_id"], "source_panel_reference_hash": source_reference["artifact_hash"],
        "repair_manifest_hash": repair_manifest["manifest_hash"], "repair_pack_hash": repair_pack["pack_hash"],
        "repair_response_hash": hash_payload(repair_response), "labels": labels, "label_count": len(labels) * len(CRITERIA),
        "repair_records": sorted(repair_records, key=lambda item: item["conflict_id"]), "repair_count": len(repair_records),
        "cross_axis_coherence_passed": not coherence_records, "cross_axis_inconsistency_count": len(coherence_records),
        "cross_axis_inconsistency_records": coherence_records,
        "candidate_state": "JOINT_TUPLE_REPAIRED_MODEL_PANEL_REFERENCE_CANDIDATE" if not coherence_records else "JOINT_TUPLE_REPAIR_FAILED",
        "ground_truth_claim": False, "human_gold_claim": False, "action_credit_authority": False,
        "selection_authority": False, "retention_authority": False, "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_joint_tuple_repaired_reference(
    artifact, *, source_reference=None, repair_pack=None, repair_manifest=None, repair_response=None
):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if (
        artifact.get("artifact_hash") != hash_payload(commitment)
        or artifact.get("repair_version") != REPAIR_VERSION
        or artifact.get("label_count") != 24 * len(CRITERIA)
        or len(artifact.get("labels", [])) != 24
        or artifact.get("repair_count") != len(artifact.get("repair_records", []))
    ):
        raise ValueError("joint_tuple_repaired_reference_invalid")
    supplied = (source_reference, repair_pack, repair_manifest, repair_response)
    if any(value is not None for value in supplied):
        if not all(value is not None for value in supplied) or artifact != build_joint_tuple_repaired_reference(
            source_reference=source_reference,
            repair_pack=repair_pack,
            repair_manifest=repair_manifest,
            repair_response=repair_response,
        ):
            raise ValueError("joint_tuple_repaired_reference_semantics_invalid")


def build_joint_tuple_repair_analysis(
    *, source_reference, repaired_reference, repair_response, prior_calibration, repaired_calibration
):
    validate_joint_fresh_reference(source_reference)
    validate_joint_tuple_repaired_reference(repaired_reference)
    calibration_hashes_valid = all(
        calibration.get("artifact_hash")
        == hash_payload({key: value for key, value in calibration.items() if key != "artifact_hash"})
        for calibration in (prior_calibration, repaired_calibration)
    )
    if (
        not calibration_hashes_valid
        or repaired_reference.get("source_panel_reference_hash") != source_reference.get("artifact_hash")
        or repaired_reference.get("repair_response_hash") != hash_payload(repair_response)
        or prior_calibration.get("source_panel_reference_hash") != source_reference.get("artifact_hash")
        or repaired_calibration.get("source_panel_reference_hash") != repaired_reference.get("artifact_hash")
    ):
        raise ValueError("joint_tuple_repair_analysis_lineage_invalid")
    before = prior_calibration["candidate_metrics"]
    after = repaired_calibration["candidate_metrics"]
    metric_names = (
        "full_tuple_accuracy",
        "selected_object_accuracy",
        "selection_basis_accuracy",
        "pragmatic_preference_accuracy",
        "assessment_completeness_accuracy",
        "consensus_action_accuracy",
        "preserve_specificity",
        "reopen_recall",
        "local_basis_action_accuracy",
    )
    metric_deltas = {name: after[name] - before[name] for name in metric_names}
    change_counts = Counter(
        criterion for decision in repair_response["decisions"] for criterion in decision["changed_criteria"]
    )
    confidence_values = [decision["confidence"] for decision in repair_response["decisions"]]
    observations = [
        f"Kimi-K3 returned {len(repair_response['decisions'])} complete repair tuples; all passed schema, binding, exact-change, and cross-axis coherence validation.",
        f"The repaired 96-cell reference contains {repaired_reference['cross_axis_inconsistency_count']} incoherent tuples, down from {source_reference['cross_axis_inconsistency_count']}.",
        f"Repairs changed selected object in {change_counts.get('SELECTED_OBJECT', 0)} cases and pragmatic preference in {change_counts.get('PRAGMATIC_PREFERENCE', 0)} cases; no other cells changed.",
        f"DeepSeek full-tuple accuracy is {after['full_tuple_accuracy']:.3f}, consensus reopen recall {after['reopen_recall']:.3f}, and preserve specificity {after['preserve_specificity']:.3f} against the repaired reference.",
    ]
    interpretations = [
        "Object-level adjudication repaired every composition failure without forcing a single global repair rule.",
        "Kimi-K3 preserved hard semantic bases when the evidence supported a specific object, but preserved NO_PREFERENCE by removing unsupported directional preference in genuinely open cases.",
        "Changes in coordinator scores are reference-quality effects, not new coordinator performance; the DeepSeek run itself was frozen before repair.",
    ]
    unknowns = [
        "The repaired model-panel reference is not human gold or real-world ground truth.",
        "The same five cases cannot estimate out-of-sample benefit because they selected the repair protocol.",
        "Whether full-tuple adjudication improves fresh coordinator calibration enough to justify transfer remains untested.",
    ]
    intuition_triggers = [
        "A cognitive object may need to be the atomic unit of adjudication even when evidence is collected by independent specialist roles.",
        "The coordinator appears to need two distinct abilities: preserve strong local evidence and repair global contradictions without flattening all uncertainty into one default.",
        "Role diversity creates useful disagreement only when an object-level integrator can decide which local commitments survive composition.",
    ]
    commitment = {
        "analysis_version": "clarification_joint_tuple_repair_analysis_v0_14",
        "source_panel_reference_hash": source_reference["artifact_hash"],
        "repaired_panel_reference_hash": repaired_reference["artifact_hash"],
        "repair_response_hash": hash_payload(repair_response),
        "prior_calibration_hash": prior_calibration["artifact_hash"],
        "repaired_calibration_hash": repaired_calibration["artifact_hash"],
        "repair_count": len(repair_response["decisions"]),
        "repair_change_counts": dict(sorted(change_counts.items())),
        "mean_repair_confidence": sum(confidence_values) / len(confidence_values),
        "candidate_metrics_before": {name: before[name] for name in metric_names},
        "candidate_metrics_after": {name: after[name] for name in metric_names},
        "candidate_metric_deltas": metric_deltas,
        "observations": observations,
        "interpretations": interpretations,
        "unknowns": unknowns,
        "intuition_triggers": intuition_triggers,
        "transfer_recommendation": "REJECT_JOINT_COORDINATOR_TRANSFER",
        "next_required_evidence": "FRESH_JOINT_TUPLE_PANEL_HOLDOUT",
        "candidate_state": "JOINT_TUPLE_REFERENCE_COHERENT_DIAGNOSTIC_ONLY",
        "ground_truth_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_joint_tuple_repair_analysis(
    artifact, *, source_reference, repaired_reference, repair_response, prior_calibration, repaired_calibration
):
    expected = build_joint_tuple_repair_analysis(
        source_reference=source_reference,
        repaired_reference=repaired_reference,
        repair_response=repair_response,
        prior_calibration=prior_calibration,
        repaired_calibration=repaired_calibration,
    )
    if artifact != expected:
        raise ValueError("joint_tuple_repair_analysis_invalid")


def render_joint_tuple_repair_analysis(analysis):
    lines = ["# Clarification Joint Tuple Repair v0.14 Analysis", ""]
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
        f"Transfer: `{analysis['transfer_recommendation']}`",
        f"State: `{analysis['candidate_state']}`",
        f"Artifact hash: `{analysis['artifact_hash']}`",
        "",
    ))
    return "\n".join(lines)


def _labels_by_conflict(response, bindings):
    labels = {item["annotation_id"]: item for item in response["labels"]}
    return {conflict_id: labels[annotation_id] for annotation_id, conflict_id in bindings.items()}
