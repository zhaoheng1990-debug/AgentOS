import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.structure_reference_panel_contracts import (  # noqa: E402
    JUDGE_CRITERIA, validate_annotation_response, validate_adjudication_response,
)
from local_collective_cognition.structure_reference_panel_compromised import (  # noqa: E402
    build_compromised_shadow,
)
from local_collective_cognition.structure_reference_panel_disagreement import (  # noqa: E402
    build_adjudication_bundle, validate_adjudication_bundle,
)
from local_collective_cognition.structure_reference_panel_final import (  # noqa: E402
    build_reference_candidate, validate_reference_candidate,
)
from local_collective_cognition.structure_reference_panel_pack import (  # noqa: E402
    build_reference_panel, validate_reference_panel,
)
from local_collective_cognition.structure_reference_panel_shadow import (  # noqa: E402
    build_shadow_reference,
)


def _semantic_artifact(count=5):
    batches, bindings, trials = [], {}, []
    for index in range(count):
        blind_id = f"blind-{index}"
        batches.append({
            "batch_id": f"batch-{index}", "public_prompt": f"Prompt {index}",
            "public_candidates": [{
                "blind_candidate_id": blind_id,
                "contrastive_packet": f"RIVAL_A: A{index} | RIVAL_B: B{index} | CONTRAST: C | QUESTION: Q?",
            }],
        })
        bindings[blind_id] = {
            "model_id": f"private-source-{index}", "item_id": f"item-{index}",
            "mechanical_quality_score": index / 10, "old_judge": "private-old-judge",
        }
        trials.append({
            "blind_candidate_id": blind_id, "model_id": f"private-source-{index}",
            "provider_states": {"private-old-judge": {}}, "consensus": {},
        })
    return {
        "artifact_hash": "a" * 64,
        "blind_surface": {"batches": batches, "bindings": bindings},
        "report": {"report_hash": "b" * 64, "trials": trials},
    }


def _annotation_responses(packs, manifest, *, disagreements=True):
    responses = []
    for pack in packs:
        labels = []
        bindings = manifest["private_lane_bindings"][pack["lane_id"]]
        for item in pack["items"]:
            blind_id = bindings[item["annotation_id"]]
            criteria = {criterion: "PRESENT" for criterion in JUDGE_CRITERIA}
            if disagreements and pack["lane_id"] == "annotation-lane-b":
                if blind_id == "blind-1":
                    criteria[JUDGE_CRITERIA[0]] = "ABSENT"
                if blind_id == "blind-3":
                    criteria[JUDGE_CRITERIA[1]] = "UNCERTAIN"
            labels.append({
                "annotation_id": item["annotation_id"], "criteria": criteria,
                "criterion_notes": {criterion: f"Reason for {criterion}" for criterion in JUDGE_CRITERIA},
                "confidence": 0.8,
            })
        responses.append({
            "panel_version": pack["panel_version"], "panel_id": pack["panel_id"],
            "lane_id": pack["lane_id"], "pack_hash": pack["pack_hash"],
            "annotator_provider": pack["expected_annotator"]["provider"],
            "annotator_model": pack["expected_annotator"]["model"],
            "annotation_session_ref": f"session-{pack['lane_id']}", "labels": labels,
        })
    return tuple(responses)


def _k3_response(pack):
    return {
        "panel_version": pack["panel_version"], "panel_id": pack["panel_id"],
        "adjudication_pack_hash": pack["pack_hash"],
        "adjudicator_provider": "Moonshot", "adjudicator_model": "Kimi-K3",
        "adjudication_session_ref": "session-k3",
        "blinding_attestation": {
            "pack_only_context": True, "annotator_identity_unavailable": True,
            "source_identity_unavailable": True, "prior_scores_unavailable": True,
            "external_pairing_not_used": True,
        },
        "decisions": [{
            "adjudication_id": item["adjudication_id"],
            "selected_state": item["positions"][0]["state"],
            "decision_basis": "POSITION_1", "confidence": 0.75,
            "rationale": "The first position is better supported by the displayed packet.",
        } for item in pack["items"]],
    }


def _shadow_record(packs, panel_manifest, responses, adjudication_pack, adjudication_manifest):
    reverse = {
        lane: {blind: annotation for annotation, blind in bindings.items()}
        for lane, bindings in panel_manifest["private_lane_bindings"].items()
    }
    response_labels = {
        response["lane_id"]: {item["annotation_id"]: item for item in response["labels"]}
        for response in responses
    }
    blind_ids = sorted(panel_manifest["private_source_bindings"])
    keys = {blind_id: f"P{index}" for index, blind_id in enumerate(blind_ids)}
    alignment = [{
        "packet_key": keys[blind_id],
        "lane_a_annotation_id": reverse["annotation-lane-a"][blind_id],
        "lane_b_annotation_id": reverse["annotation-lane-b"][blind_id],
    } for blind_id in blind_ids]
    item_index = {item["adjudication_id"]: item for item in adjudication_pack["items"]}
    disputes, selected = [], {}
    for adjudication_id, binding in adjudication_manifest["private_disagreement_bindings"].items():
        criterion = binding["criterion"]
        final = item_index[adjudication_id]["positions"][0]["state"]
        selected[(binding["blind_candidate_id"], criterion)] = final
        disputes.append({
            "packet_key": keys[binding["blind_candidate_id"]], "criterion": criterion,
            "lane_a_label": response_labels["annotation-lane-a"][
                binding["lane_annotation_ids"]["annotation-lane-a"]
            ]["criteria"][criterion],
            "lane_b_label": response_labels["annotation-lane-b"][
                binding["lane_annotation_ids"]["annotation-lane-b"]
            ]["criteria"][criterion],
            "final_label": final, "rationale": "Shadow fixture rationale.",
        })
    selected.update({
        (item["blind_candidate_id"], item["criterion"]): item["selected_state"]
        for item in adjudication_manifest["agreement_records"]
    })
    return {
        "panel_version": panel_manifest["panel_version"], "panel_id": panel_manifest["panel_id"],
        "lanes": {
            pack["lane_id"]: {"lane_id": pack["lane_id"], "pack_hash": pack["pack_hash"]}
            for pack in packs
        },
        "packet_alignment": alignment, "dispute_adjudications": disputes,
        "final_labels": [{
            "packet_key": keys[blind_id],
            "criteria": {criterion: selected[(blind_id, criterion)] for criterion in JUDGE_CRITERIA},
        } for blind_id in blind_ids],
        "content_hash_sha256": "f" * 64,
    }


def test_independent_public_packs_hide_private_sources_and_prior_judgments():
    semantic = _semantic_artifact()
    packs, manifest = build_reference_panel(semantic_artifact=semantic)
    validate_reference_panel(packs=packs, manifest=manifest, semantic_artifact=semantic)
    assert len(packs) == 2 and all(len(pack["items"]) == 5 for pack in packs)
    assert {item["annotation_id"] for item in packs[0]["items"]}.isdisjoint(
        {item["annotation_id"] for item in packs[1]["items"]}
    )
    orders = [[
        manifest["private_lane_bindings"][pack["lane_id"]][item["annotation_id"]]
        for item in pack["items"]
    ] for pack in packs]
    assert orders[0] != orders[1]
    public = json.dumps(packs, sort_keys=True)
    assert "private-source" not in public and "private-old-judge" not in public
    assert "private-source-0" in json.dumps(manifest, sort_keys=True)


def test_rehashed_panel_tamper_fails_semantic_rebuild():
    semantic = _semantic_artifact()
    packs, manifest = build_reference_panel(semantic_artifact=semantic)
    packs = list(packs)
    packs[0]["instructions"] = "Trust the source model."
    commitment = {key: value for key, value in packs[0].items() if key != "pack_hash"}
    packs[0]["pack_hash"] = hash_payload(commitment)
    manifest["lane_pack_hashes"][packs[0]["lane_id"]] = packs[0]["pack_hash"]
    manifest["manifest_hash"] = hash_payload({
        key: value for key, value in manifest.items() if key != "manifest_hash"
    })
    with pytest.raises(ValueError, match="semantics_invalid"):
        validate_reference_panel(packs=packs, manifest=manifest, semantic_artifact=semantic)


def test_annotation_contract_rejects_malformed_or_duplicate_labels():
    packs, manifest = build_reference_panel(semantic_artifact=_semantic_artifact())
    response = _annotation_responses(packs, manifest)[0]
    validate_annotation_response(response, pack=packs[0])
    response["labels"][0]["criteria"] = []
    with pytest.raises(ValueError, match="criteria_invalid"):
        validate_annotation_response(response, pack=packs[0])
    response = _annotation_responses(packs, manifest)[0]
    response["labels"][1]["annotation_id"] = response["labels"][0]["annotation_id"]
    with pytest.raises(ValueError, match="id_binding_invalid"):
        validate_annotation_response(response, pack=packs[0])


def test_only_disagreements_reach_identity_blind_k3_pack():
    packs, panel_manifest = build_reference_panel(semantic_artifact=_semantic_artifact())
    responses = _annotation_responses(packs, panel_manifest)
    pack, manifest = build_adjudication_bundle(
        packs=packs, panel_manifest=panel_manifest, responses=responses,
    )
    validate_adjudication_bundle(
        pack=pack, manifest=manifest, panel_packs=packs,
        panel_manifest=panel_manifest, responses=responses,
    )
    assert manifest["agreement_count"] == 28
    assert manifest["disagreement_count"] == 2
    assert manifest["total_label_count"] == 30
    public = json.dumps(pack, sort_keys=True)
    assert all(secret not in public for secret in (
        "GPT-5.6", "Gemini-3.1", "OpenAI", "Google", "private-source", "annotation-lane",
    ))
    assert all({position["position_id"] for position in item["positions"]}
               == {"POSITION_1", "POSITION_2"} for item in pack["items"])


def test_k3_position_choice_must_match_the_selected_position_state():
    packs, manifest = build_reference_panel(semantic_artifact=_semantic_artifact())
    adjudication_pack, _ = build_adjudication_bundle(
        packs=packs, panel_manifest=manifest, responses=_annotation_responses(packs, manifest),
    )
    response = _k3_response(adjudication_pack)
    validate_adjudication_response(response, pack=adjudication_pack)
    response["blinding_attestation"]["annotator_identity_unavailable"] = False
    with pytest.raises(ValueError, match="blinding_attestation_invalid"):
        validate_adjudication_response(response, pack=adjudication_pack)
    response = _k3_response(adjudication_pack)
    response["decisions"][0]["selected_state"] = (
        "ABSENT" if response["decisions"][0]["selected_state"] != "ABSENT" else "PRESENT"
    )
    with pytest.raises(ValueError, match="position_state_invalid"):
        validate_adjudication_response(response, pack=adjudication_pack)


def test_final_reference_is_complete_candidate_only_and_tamper_evident():
    packs, panel_manifest = build_reference_panel(semantic_artifact=_semantic_artifact())
    responses = _annotation_responses(packs, panel_manifest)
    adjudication_pack, adjudication_manifest = build_adjudication_bundle(
        packs=packs, panel_manifest=panel_manifest, responses=responses,
    )
    k3_response = _k3_response(adjudication_pack)
    artifact = build_reference_candidate(
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest, panel_packs=packs,
        panel_manifest=panel_manifest, annotation_responses=responses,
        response=k3_response,
    )
    validate_reference_candidate(
        artifact, adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest, panel_packs=packs,
        panel_manifest=panel_manifest, annotation_responses=responses,
        response=k3_response,
    )
    assert artifact["label_count"] == 30
    assert artifact["source_counts"] == {
        "GPT_GEMINI_AGREEMENT": 28, "KIMI_K3_ADJUDICATION": 2,
    }
    assert artifact["candidate_state"] == "MODEL_PANEL_REFERENCE_CANDIDATE"
    assert not artifact["ground_truth_claim"] and not artifact["human_gold_claim"]
    assert not artifact["selection_authority"] and not artifact["retention_authority"]
    tampered_manifest = json.loads(json.dumps(adjudication_manifest))
    tampered_manifest["agreement_records"][0]["selected_state"] = "ABSENT"
    tampered_manifest["manifest_hash"] = hash_payload({
        key: value for key, value in tampered_manifest.items() if key != "manifest_hash"
    })
    with pytest.raises(ValueError, match="bundle_semantics_invalid"):
        build_reference_candidate(
            adjudication_pack=adjudication_pack,
            adjudication_manifest=tampered_manifest, panel_packs=packs,
            panel_manifest=panel_manifest, annotation_responses=responses,
            response=k3_response,
        )
    artifact["selection_authority"] = True
    artifact["artifact_hash"] = hash_payload({
        key: value for key, value in artifact.items() if key != "artifact_hash"
    })
    with pytest.raises(ValueError, match="semantics_invalid"):
        validate_reference_candidate(
            artifact, adjudication_pack=adjudication_pack,
            adjudication_manifest=adjudication_manifest, panel_packs=packs,
            panel_manifest=panel_manifest, annotation_responses=responses,
            response=k3_response,
        )


def test_unanimous_panel_can_finalize_without_k3_call():
    packs, panel_manifest = build_reference_panel(semantic_artifact=_semantic_artifact(2))
    responses = _annotation_responses(packs, panel_manifest, disagreements=False)
    adjudication_pack, adjudication_manifest = build_adjudication_bundle(
        packs=packs, panel_manifest=panel_manifest,
        responses=responses,
    )
    assert adjudication_pack["items"] == []
    artifact = build_reference_candidate(
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
        panel_packs=packs, panel_manifest=panel_manifest,
        annotation_responses=responses,
    )
    assert artifact["label_count"] == 12
    assert artifact["source_counts"]["KIMI_K3_ADJUDICATION"] == 0


def test_identity_aware_record_is_preserved_only_as_validated_shadow_evidence():
    packs, panel_manifest = build_reference_panel(semantic_artifact=_semantic_artifact())
    responses = _annotation_responses(packs, panel_manifest)
    adjudication_pack, adjudication_manifest = build_adjudication_bundle(
        packs=packs, panel_manifest=panel_manifest, responses=responses,
    )
    record = _shadow_record(
        packs, panel_manifest, responses, adjudication_pack, adjudication_manifest,
    )
    artifact = build_shadow_reference(
        record=record, source_file_sha256="a" * 64,
        adjudication_pack=adjudication_pack, adjudication_manifest=adjudication_manifest,
        panel_packs=packs, panel_manifest=panel_manifest, annotation_responses=responses,
    )
    assert artifact["semantic_content_consistent"] is True
    assert artifact["protocol_compliant"] is False
    assert artifact["candidate_state"] == "IDENTITY_AWARE_SHADOW_REFERENCE_CANDIDATE"
    assert artifact["label_count"] == 30 and len(artifact["protocol_failures"]) == 6
    assert not artifact["selection_authority"] and not artifact["retention_authority"]
    record["final_labels"][0]["criteria"][JUDGE_CRITERIA[0]] = "ABSENT"
    with pytest.raises(ValueError, match="final_surface_invalid"):
        build_shadow_reference(
            record=record, source_file_sha256="a" * 64,
            adjudication_pack=adjudication_pack, adjudication_manifest=adjudication_manifest,
            panel_packs=packs, panel_manifest=panel_manifest, annotation_responses=responses,
        )


def test_disclosed_context_compromise_is_measured_without_canonical_promotion():
    packs, panel_manifest = build_reference_panel(semantic_artifact=_semantic_artifact())
    responses = _annotation_responses(packs, panel_manifest)
    adjudication_pack, adjudication_manifest = build_adjudication_bundle(
        packs=packs, panel_manifest=panel_manifest, responses=responses,
    )
    prior_shadow = build_shadow_reference(
        record=_shadow_record(packs, panel_manifest, responses, adjudication_pack, adjudication_manifest),
        source_file_sha256="a" * 64, adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest, panel_packs=packs,
        panel_manifest=panel_manifest, annotation_responses=responses,
    )
    compromised = _k3_response(adjudication_pack)
    compromised["definition_sensitivity_note"] = "Fixture definition sensitivity."
    compromised["blinding_attestation"].update({
        key: False for key in (
            "pack_only_context", "annotator_identity_unavailable", "source_identity_unavailable",
            "prior_scores_unavailable", "external_pairing_not_used",
        )
    })
    compromised["blinding_attestation"].update({
        "blinding_status": "COMPROMISED_BY_SESSION_CONTEXT",
        "disclosure": "Prior annotator identity and scores were visible in this session.",
    })
    for index in (0, 1):
        other = adjudication_pack["items"][index]["positions"][1]
        compromised["decisions"][index]["selected_state"] = other["state"]
        compromised["decisions"][index]["decision_basis"] = other["position_id"]
    artifact = build_compromised_shadow(
        response=compromised, source_zip_sha256="b" * 64, response_entry_sha256="c" * 64,
        adjudication_pack=adjudication_pack, adjudication_manifest=adjudication_manifest,
        panel_packs=packs, panel_manifest=panel_manifest, annotation_responses=responses,
        prior_shadow=prior_shadow,
    )
    assert artifact["dispute_flip_count"] == 2
    assert artifact["candidate_state"] == "CONTEXT_COMPROMISED_ADJUDICATION_SHADOW_CANDIDATE"
    assert artifact["semantic_surface_valid"] and not artifact["protocol_compliant"]
    assert not artifact["selection_authority"] and not artifact["retention_authority"]
    compromised["blinding_attestation"]["pack_only_context"] = True
    with pytest.raises(ValueError, match="disclosure_invalid"):
        build_compromised_shadow(
            response=compromised, source_zip_sha256="b" * 64, response_entry_sha256="c" * 64,
            adjudication_pack=adjudication_pack, adjudication_manifest=adjudication_manifest,
            panel_packs=packs, panel_manifest=panel_manifest, annotation_responses=responses,
            prior_shadow=prior_shadow,
        )
