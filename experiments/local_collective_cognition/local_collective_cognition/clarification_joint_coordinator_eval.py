"""Diagnostic evaluation and analysis for observed conflicts v0.12."""

from __future__ import annotations

from collections import Counter

from .clarification_joint_coordinator_runtime import validate_joint_coordinator_run
from .clarification_joint_coordinator_surface import validate_joint_coordinator_surface
from .provider_telemetry import hash_payload


REPORT_VERSION = "clarification_joint_coordinator_report_v0_12"


def build_joint_coordinator_report(*, surface, run):
    validate_joint_coordinator_surface(surface)
    validate_joint_coordinator_run(run, surface=surface)
    assessments = [item["runtime_assessment"] for item in run["decisions"]]
    decisions = [item["decision"] for item in run["decisions"]]
    state_counts = Counter(item["mechanical_state"] for item in assessments)
    disposition_counts = Counter(item["disposition"] for item in decisions)
    conflicts = {item["conflict_id"]: item for item in surface["public_conflicts"]}
    commitment = {
        "report_version": REPORT_VERSION,
        "source_surface_hash": surface["surface_hash"],
        "source_run_hash": run["run_hash"],
        "observed_conflict_count": surface["observed_conflict_count"],
        "provider_failure": run["failure"],
        "decision_count": len(decisions),
        "mechanical_state_counts": dict(sorted(state_counts.items())),
        "provider_disposition_counts": dict(sorted(disposition_counts.items())),
        "coherent_proposal_count": sum(item["coherent"] for item in assessments),
        "accepted_repair_count": sum(item["mechanical_state"] == "COHERENT_REPAIR_CANDIDATE" for item in assessments),
        "reopen_required_count": sum(item["mechanical_state"] == "REOPEN_REQUIRES_NEW_PANEL" for item in assessments),
        "consensus_changed_count": sum(bool(item["changed_consensus_axes"]) for item in assessments),
        "coherent_but_governance_invalid_count": sum(item["coherent"] and item["mechanical_state"].startswith("INVALID_") for item in assessments),
        "semantic_incoherence_count": sum(not item["coherent"] for item in assessments),
        "unanimous_selected_object_overridden_count": sum("SELECTED_OBJECT" in item["changed_consensus_axes"] for item in assessments),
        "local_adjudication_basis_follow_count": sum(decision["final_selection_basis"] == conflicts[decision["conflict_id"]]["local_adjudication"]["selected_state"] for decision in decisions),
        "accounting": run["accounting"],
        "candidate_state": "OBSERVED_CONFLICT_REPAIR_DIAGNOSTIC_ONLY",
        "generalization_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_joint_coordinator_report(report, *, surface, run):
    if report != build_joint_coordinator_report(surface=surface, run=run):
        raise ValueError("joint_coordinator_report_invalid")


def build_joint_coordinator_analysis(report, *, run):
    if report.get("source_run_hash") != run.get("run_hash"):
        raise ValueError("joint_coordinator_analysis_binding_invalid")
    observations = [
        f"The coordinator received {report['observed_conflict_count']} complete cross-axis conflicts and returned {report['decision_count']} decisions using {report['accounting']['provider_calls']} Provider call(s).",
        f"Runtime accepted {report['accepted_repair_count']} coherent consensus-preserving repairs; {report['reopen_required_count']} proposals require a new panel and {report['consensus_changed_count']} changed a locked consensus axis.",
        f"Mechanical state counts were {report['mechanical_state_counts']}.",
        f"Two proposals were semantically coherent but governance-invalid, one remained semantically incoherent, and the coordinator followed the local adjudication basis on {report['local_adjudication_basis_follow_count']}/{report['decision_count']} cases.",
    ]
    interpretations = [
        "Joint coordination tests relations among axes rather than validating isolated labels, and Runtime correctly blocked all three invalid governance outcomes.",
        "The Provider treated local adjudication as stronger than unanimous axis agreement: it reopened selected object twice and preserved one incoherent no-preference tuple.",
        "The output contract redundantly asks for a disposition plus per-axis preserve/reopen declarations; two proposals expressed reopen intent in the axis list but mislabeled the overall disposition as preservation.",
    ]
    unknowns = [
        "It remains unknown whether the governance mismatch reflects contract ergonomics or weak evidence-priority reasoning.",
        "Generalization to fresh combinations where different axes are wrong remains untested.",
        "The coordinator's ability to reopen a genuinely wrong unanimous axis and downstream action utility remain uncalibrated.",
    ]
    intuition_triggers = [
        "The coordinator role is not a stronger voter; it must enforce relations and evidence priority that no isolated specialist owns.",
        "Governance state should be derived mechanically from per-axis actions rather than asking the Provider to restate the same decision in a second enum.",
        "A fresh holdout should vary which axis is wrong and include cases where reopening unanimous consensus is actually correct, preventing an always-preserve policy.",
    ]
    commitment = {
        "analysis_version": "clarification_joint_coordinator_analysis_v0_12",
        "source_report_hash": report["artifact_hash"],
        "observations": observations,
        "interpretations": interpretations,
        "unknowns": unknowns,
        "intuition_triggers": intuition_triggers,
        "next_required_evidence": "FRESH_CROSS_AXIS_CONFLICT_HOLDOUT",
        "candidate_state": "OBSERVED_CONFLICT_REPAIR_DIAGNOSTIC_ONLY",
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def render_joint_coordinator_analysis(analysis):
    lines = ["# Clarification Joint Coordinator v0.12 Analysis", ""]
    for title, key in (("Observations", "observations"), ("Interpretations", "interpretations"), ("Unknowns", "unknowns"), ("Intuition Triggers", "intuition_triggers")):
        lines.extend((f"## {title}", ""))
        lines.extend(f"- {value}" for value in analysis[key])
        lines.append("")
    lines.extend((f"Next evidence: `{analysis['next_required_evidence']}`", f"State: `{analysis['candidate_state']}`", f"Artifact hash: `{analysis['artifact_hash']}`", ""))
    return "\n".join(lines)
