"""Runtime gate policies for the v0.20 evidence factorial."""

from __future__ import annotations

from .cognitive_action_evidence_calibrator import (
    DEFINITION_SOURCES,
    SOURCE_TO_STATE,
    normalize_source_receipt,
    source_schema,
)
from .cognitive_action_selective_runtime import (
    PROCESS_STATES,
    SELECTIONS,
    validate_selective_tuple,
)


LEGACY_GATE = "LEGACY_GATE_V0_19"
REPAIRED_GATE = "REPAIRED_GATE_V0_20"
GATE_POLICIES = (LEGACY_GATE, REPAIRED_GATE)


def apply_gate_policy(policy, receipt, *, conflict_id, evidence_refs):
    if policy == LEGACY_GATE:
        payload = normalize_source_receipt(
            receipt,
            conflict_id=conflict_id,
            evidence_refs=evidence_refs,
        )
        return {
            "payload": payload,
            "gate_transforms": [],
            "gate_policy": LEGACY_GATE,
        }
    if policy == REPAIRED_GATE:
        return normalize_repaired_gate(
            receipt,
            conflict_id=conflict_id,
            evidence_refs=evidence_refs,
        )
    raise ValueError("evidence_gate_policy_unknown")


def normalize_repaired_gate(receipt, *, conflict_id, evidence_refs):
    _validate_source_receipt_shape(
        receipt,
        conflict_id=conflict_id,
        evidence_refs=evidence_refs,
    )
    source = receipt["definition_source"]
    selected = receipt["selected_object"]
    preference = receipt["pragmatic_preference"]
    transforms = []
    decisive = (
        "EXPLICIT_REQUEST_DEFINITION",
        "ESTABLISHED_UNAMBIGUOUS_TERM",
        "COMPOSED_CONSTRAINTS",
    )
    if source in decisive and selected not in ("CANDIDATE_A", "CANDIDATE_B"):
        raise ValueError("evidence_decisive_source_without_selection")
    if source == "UNDERSPECIFIED_SURFACE":
        if selected != "NONE":
            raise ValueError("evidence_soft_source_selected_object")
        if preference == "UNCERTAIN":
            preference = "NONE"
            transforms.append("UNSUPPORTED_PREFERENCE_TO_NONE")
    if source == "MISSING_EXTERNAL_SPECIFICATION":
        if selected != "NONE":
            raise ValueError("evidence_opaque_source_selected_object")
        if preference == "UNCERTAIN":
            preference = "NONE"
            transforms.append("UNSUPPORTED_PREFERENCE_TO_NONE")
        elif preference != "NONE":
            raise ValueError("evidence_opaque_source_pragmatic_preference")
    if source in ("CONFLICTING_SURFACE", "UNRESOLVED") and (
        selected != "UNCERTAIN" or preference != "UNCERTAIN"
    ):
        raise ValueError("evidence_uncertain_source_mismatch")

    state = SOURCE_TO_STATE[source]
    if state == "DIRECTLY_DEFINED":
        basis = "LEXICAL_EXACT"
    elif state == "COMPOSITIONALLY_DETERMINED":
        basis = "COMPOSITIONAL_ENTAILMENT"
    elif state == "SOFT_AMBIGUITY":
        basis = (
            "PRAGMATIC_DEFAULT"
            if preference in ("CANDIDATE_A", "CANDIDATE_B")
            else "NO_PREFERENCE"
        )
    elif state == "OPAQUE_REFERENCE":
        basis = "NO_PREFERENCE"
    else:
        basis = "UNCERTAIN"

    process = receipt["assessment_process_state"]
    if source in ("UNDERSPECIFIED_SURFACE", "MISSING_EXTERNAL_SPECIFICATION"):
        if process != "COMPLETE":
            transforms.append("RECOGNIZED_OPEN_STATE_TO_COMPLETE_ASSESSMENT")
        process = "COMPLETE"
    action = (
        "ACCEPT"
        if selected in ("CANDIDATE_A", "CANDIDATE_B")
        else "CLARIFY"
        if selected == "NONE"
        else "ABSTAIN"
    )
    payload = {
        "conflict_id": conflict_id,
        "selected_object": selected,
        "selection_basis": basis,
        "pragmatic_preference": preference,
        "evidence_state": state,
        "assessment_process_state": process,
        "action": action,
        "rationale": receipt["rationale"],
        "confidence": receipt["confidence"],
        "evidence_refs": list(evidence_refs),
    }
    validate_selective_tuple(
        payload,
        conflict_id=conflict_id,
        evidence_refs=evidence_refs,
    )
    return {
        "payload": payload,
        "gate_transforms": transforms,
        "gate_policy": REPAIRED_GATE,
    }


def _validate_source_receipt_shape(receipt, *, conflict_id, evidence_refs):
    required = set(source_schema(conflict_id, evidence_refs)["required"])
    if (
        not isinstance(receipt, dict)
        or set(receipt) != required
        or receipt.get("conflict_id") != conflict_id
        or receipt.get("definition_source") not in DEFINITION_SOURCES
        or receipt.get("selected_object") not in SELECTIONS
        or receipt.get("pragmatic_preference") not in SELECTIONS
        or receipt.get("assessment_process_state") not in PROCESS_STATES
        or receipt.get("evidence_refs") != list(evidence_refs)
        or not isinstance(receipt.get("support_quote"), str)
        or not receipt["support_quote"].strip()
        or not isinstance(receipt.get("rationale"), str)
        or not receipt["rationale"].strip()
        or not isinstance(receipt.get("confidence"), (int, float))
        or isinstance(receipt.get("confidence"), bool)
        or not 0 <= receipt["confidence"] <= 1
    ):
        raise ValueError("evidence_source_receipt_invalid")
