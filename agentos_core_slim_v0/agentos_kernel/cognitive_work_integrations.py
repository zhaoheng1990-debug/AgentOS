"""Focused Kernel adapters from cognitive-work control into existing gates."""

from __future__ import annotations

from typing import Any

from .cognitive_work_models import CognitiveWorkControlDecision, validate_control_binding


def apply_anti_additive_work_control(
    *,
    candidate: Any,
    control: CognitiveWorkControlDecision | None,
    state: str,
    reason: str,
) -> tuple[str, str]:
    if control is None:
        return state, reason
    validate_control_binding(control, project_scope=candidate.project_scope)
    if control.evidence_ref not in candidate.evidence_refs:
        raise ValueError("anti_additive_cognitive_work_evidence_not_bound")
    if state == "ALLOW_BOUNDED_CHANGE" and not control.allow_organization_expansion and candidate.change_kind != "OBJECT":
        return (
            "BLOCK_PATCH_ACCUMULATION",
            "cognitive_work_marginal_gain_does_not_authorize_same_level_expansion",
        )
    return state, reason


def validate_policy_work_control(control, *, project_scope: str, context_key: str) -> None:
    if control is not None:
        validate_control_binding(control, project_scope=project_scope, context_key=context_key)


def policy_work_failure(control, policy_id: str) -> str:
    if control is not None and not control.allow_organization_expansion and policy_id != "SOLO":
        return "cognitive_work_expansion_not_authorized"
    return ""


def work_control_evidence_refs(control) -> tuple[str, ...]:
    return (control.evidence_ref,) if control is not None else ()
