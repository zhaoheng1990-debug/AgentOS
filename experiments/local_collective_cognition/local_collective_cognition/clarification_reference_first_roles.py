"""Deterministic model-role rotation and bounded specialist contracts for v0.15."""

from __future__ import annotations

from collections import Counter

from .clarification_reference_first_holdout import validate_reference_first_holdout
from .clarification_reference_first_panel import validate_reference_first_reference
from .provider_telemetry import hash_payload


ROLE_VERSION = "clarification_reference_first_roles_v0_15"
ROLE_TASK_KIND = "CLARIFICATION_REFERENCE_FIRST_SPECIALIST_ROLE"
MODEL_IDS = ("qwen2.5-1.5b-instruct", "gemma-2-2b-it", "llama-3.2-1b-instruct")
ROLE_IDS = ("OBJECT_GROUNDING", "PRAGMATIC_DEFAULT", "ASSESSMENT_SKEPTIC")
ROLE_BATCH_SIZE = 4

ROLE_DEFINITIONS = {
    "OBJECT_GROUNDING": (
        "Determine only whether candidate A, candidate B, neither, or uncertainty is semantically fixed, and classify "
        "the strongest basis. Distinguish semantic entailment from a merely useful default. Do not decide pragmatic "
        "preference or overall completeness."
    ),
    "PRAGMATIC_DEFAULT": (
        "Determine only which candidate would be the more useful contextual default if clarification is unavailable. "
        "Use NONE when neither has a meaningful advantage and UNCERTAIN only when the comparison itself cannot be made. "
        "Do not claim that preference semantically fixes the object."
    ),
    "ASSESSMENT_SKEPTIC": (
        "Determine only whether the displayed prompt and candidate meanings contain enough information to complete the "
        "semantic assessment. A justified open result can be COMPLETE. Mark INCOMPLETE only when missing information "
        "prevents even deciding whether openness is warranted."
    ),
}


def build_specialist_role_plan(*, corpus_artifact, frozen_reference, frozen_progress):
    validate_reference_first_holdout(corpus_artifact)
    validate_reference_first_reference(frozen_reference)
    _validate_frozen_progress(frozen_progress, corpus_artifact=corpus_artifact, frozen_reference=frozen_reference)
    public = {item["conflict_id"]: item for batch in corpus_artifact["public_surface"]["batches"] for item in batch["conflicts"]}
    provenance = corpus_artifact["private_provenance"]["bindings"]
    ordered_conflicts = sorted(provenance, key=lambda conflict_id: provenance[conflict_id]["case_id"])
    assignments = []
    for case_index, conflict_id in enumerate(ordered_conflicts):
        for model_index, model_id in enumerate(MODEL_IDS):
            role_id = ROLE_IDS[(model_index + case_index) % len(ROLE_IDS)]
            assignments.append({
                "conflict_id": conflict_id,
                "case_id": provenance[conflict_id]["case_id"],
                "object_family": provenance[conflict_id]["object_family"],
                "model_id": model_id,
                "role_id": role_id,
                "public_item_hash": hash_payload(public[conflict_id]),
            })
    batches = []
    for model_id in MODEL_IDS:
        for role_id in ROLE_IDS:
            selected = [item for item in assignments if item["model_id"] == model_id and item["role_id"] == role_id]
            selected.sort(key=lambda item: item["case_id"])
            for offset in range(0, len(selected), ROLE_BATCH_SIZE):
                chunk = selected[offset:offset + ROLE_BATCH_SIZE]
                batch_id = "specialist-" + hash_payload([ROLE_VERSION, model_id, role_id, [item["conflict_id"] for item in chunk]])[:18]
                items = [public[item["conflict_id"]] for item in chunk]
                batches.append({
                    "batch_id": batch_id,
                    "model_id": model_id,
                    "role_id": role_id,
                    "role_definition": ROLE_DEFINITIONS[role_id],
                    "items": items,
                    "item_hash": hash_payload(items),
                })
    batches.sort(key=lambda item: hash_payload([ROLE_VERSION, item["batch_id"]]))
    commitment = {
        "role_version": ROLE_VERSION,
        "source_corpus_hash": corpus_artifact["artifact_hash"],
        "source_surface_hash": corpus_artifact["public_surface"]["surface_hash"],
        "frozen_reference_hash": frozen_reference["artifact_hash"],
        "frozen_progress_hash": frozen_progress["artifact_hash"],
        "model_ids": list(MODEL_IDS),
        "role_ids": list(ROLE_IDS),
        "assignments": assignments,
        "batches": batches,
        "assignment_count": len(assignments),
        "batch_count": len(batches),
        "reference_content_exposed_to_roles": False,
        "reference_hash_exposed_to_roles": False,
        "candidate_coordinator_output": "NOT_YET_CREATED",
        "coordinator_run_allowed": False,
        "role_receipt_state": "AWAITING_LOCAL_SPECIALIST_OUTPUTS",
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "plan_hash": hash_payload(commitment)}


def validate_specialist_role_plan(plan, *, corpus_artifact=None, frozen_reference=None, frozen_progress=None):
    commitment = {key: value for key, value in plan.items() if key != "plan_hash"}
    assignment_counts = Counter((item["model_id"], item["role_id"]) for item in plan.get("assignments", []))
    conflict_roles = Counter((item["conflict_id"], item["role_id"]) for item in plan.get("assignments", []))
    conflict_models = Counter((item["conflict_id"], item["model_id"]) for item in plan.get("assignments", []))
    if (
        plan.get("plan_hash") != hash_payload(commitment)
        or plan.get("role_version") != ROLE_VERSION
        or plan.get("assignment_count") != 72
        or plan.get("batch_count") != 18
        or set(assignment_counts) != {(model, role) for model in MODEL_IDS for role in ROLE_IDS}
        or any(count != 8 for count in assignment_counts.values())
        or any(count != 1 for count in conflict_roles.values())
        or any(count != 1 for count in conflict_models.values())
        or len(conflict_roles) != 24 * len(ROLE_IDS)
        or len(conflict_models) != 24 * len(MODEL_IDS)
        or plan.get("reference_content_exposed_to_roles") is not False
        or plan.get("reference_hash_exposed_to_roles") is not False
        or plan.get("coordinator_run_allowed") is not False
    ):
        raise ValueError("specialist_role_plan_invalid")
    supplied = (corpus_artifact, frozen_reference, frozen_progress)
    if any(value is not None for value in supplied):
        if not all(value is not None for value in supplied) or plan != build_specialist_role_plan(
            corpus_artifact=corpus_artifact,
            frozen_reference=frozen_reference,
            frozen_progress=frozen_progress,
        ):
            raise ValueError("specialist_role_plan_semantics_invalid")


def specialist_role_schema(*, role_id, batch_id, conflict_ids):
    if role_id not in ROLE_IDS:
        raise ValueError("specialist_role_unknown")
    return {
        "type": "object",
        "required": ["role_version", "role_id", "batch_id", "decisions", "evidence_refs"],
        "additionalProperties": False,
        "properties": {
            "role_version": {"type": "string", "enum": [ROLE_VERSION]},
            "role_id": {"type": "string", "enum": [role_id]},
            "batch_id": {"type": "string", "enum": [batch_id]},
            "decisions": {"type": "array", "minItems": len(conflict_ids), "items": {"type": "object"}},
            "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        },
        "decision_contract": role_decision_contract(role_id),
        "required_conflict_ids": list(conflict_ids),
    }


def role_decision_contract(role_id):
    if role_id == "OBJECT_GROUNDING":
        return {
            "required": ["conflict_id", "selected_object", "selection_basis", "support", "counterevidence", "confidence"],
            "selected_object": ["CANDIDATE_A", "CANDIDATE_B", "NONE", "UNCERTAIN"],
            "selection_basis": ["LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT", "PRAGMATIC_DEFAULT", "NO_PREFERENCE", "UNCERTAIN"],
        }
    if role_id == "PRAGMATIC_DEFAULT":
        return {
            "required": ["conflict_id", "pragmatic_preference", "default_advantage", "counterpressure", "confidence"],
            "pragmatic_preference": ["CANDIDATE_A", "CANDIDATE_B", "NONE", "UNCERTAIN"],
        }
    if role_id == "ASSESSMENT_SKEPTIC":
        return {
            "required": ["conflict_id", "assessment_completeness", "missing_information", "rationale", "confidence"],
            "assessment_completeness": ["COMPLETE", "INCOMPLETE", "UNCERTAIN"],
        }
    raise ValueError("specialist_role_unknown")


def validate_specialist_role_payload(payload, *, batch, evidence_refs):
    if not isinstance(payload, dict) or set(payload) != {"role_version", "role_id", "batch_id", "decisions", "evidence_refs"}:
        raise ValueError("specialist_role_payload_shape_invalid")
    if payload["role_version"] != ROLE_VERSION or payload["role_id"] != batch["role_id"] or payload["batch_id"] != batch["batch_id"]:
        raise ValueError("specialist_role_payload_binding_invalid")
    if payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("specialist_role_evidence_refs_invalid")
    decisions = payload["decisions"]
    expected_ids = {item["conflict_id"] for item in batch["items"]}
    if not isinstance(decisions, list) or len(decisions) != len(expected_ids):
        raise ValueError("specialist_role_decision_count_invalid")
    observed = []
    contract = role_decision_contract(batch["role_id"])
    for decision in decisions:
        if not isinstance(decision, dict) or set(decision) != set(contract["required"]):
            raise ValueError("specialist_role_decision_shape_invalid")
        observed.append(decision["conflict_id"])
        confidence = decision["confidence"]
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            raise ValueError("specialist_role_confidence_invalid")
        _validate_role_decision(decision, role_id=batch["role_id"], contract=contract)
    if len(observed) != len(set(observed)) or set(observed) != expected_ids:
        raise ValueError("specialist_role_decision_ids_invalid")


def _validate_role_decision(decision, *, role_id, contract):
    if role_id == "OBJECT_GROUNDING":
        selected, basis = decision["selected_object"], decision["selection_basis"]
        if selected not in contract["selected_object"] or basis not in contract["selection_basis"]:
            raise ValueError("specialist_object_value_invalid")
        coherent = (
            basis in ("LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT") and selected in ("CANDIDATE_A", "CANDIDATE_B")
            or basis in ("PRAGMATIC_DEFAULT", "NO_PREFERENCE") and selected == "NONE"
            or basis == "UNCERTAIN" and selected == "UNCERTAIN"
        )
        if not coherent:
            raise ValueError("specialist_object_pair_incoherent")
        text_fields = ("support", "counterevidence")
    elif role_id == "PRAGMATIC_DEFAULT":
        if decision["pragmatic_preference"] not in contract["pragmatic_preference"]:
            raise ValueError("specialist_preference_value_invalid")
        text_fields = ("default_advantage", "counterpressure")
    else:
        if decision["assessment_completeness"] not in contract["assessment_completeness"]:
            raise ValueError("specialist_completeness_value_invalid")
        if not isinstance(decision["missing_information"], list) or any(not isinstance(value, str) for value in decision["missing_information"]):
            raise ValueError("specialist_missing_information_invalid")
        text_fields = ("rationale",)
    if any(not isinstance(decision[field], str) or not decision[field].strip() for field in text_fields):
        raise ValueError("specialist_role_rationale_invalid")


def _validate_frozen_progress(progress, *, corpus_artifact, frozen_reference):
    commitment = {key: value for key, value in progress.items() if key != "artifact_hash"}
    if (
        progress.get("artifact_hash") != hash_payload(commitment)
        or progress.get("source_corpus_hash") != corpus_artifact.get("artifact_hash")
        or progress.get("frozen_reference_hash") != frozen_reference.get("artifact_hash")
        or progress.get("current_phase") != "REFERENCE_FROZEN_AWAITING_LOCAL_ROLE_OUTPUTS"
        or progress.get("local_role_collection_allowed") is not True
        or progress.get("coordinator_run_allowed") is not False
        or progress.get("reference_revision_allowed") is not False
    ):
        raise ValueError("specialist_role_frozen_progress_invalid")
