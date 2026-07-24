"""Kernel-style deterministic consensus over independent semantic judges."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structure_semantic_judge_blinding import validate_blind_surface
from .structure_semantic_judge_contracts import JUDGE_CRITERIA
from .structure_semantic_judge_receipts import validate_judge_run


CONSENSUS_VERSION = "structure_packet_semantic_consensus_v0_1"
MIN_EXACT_AGREEMENT = 0.75
MAX_DIRECT_CONFLICT = 0.10


def build_semantic_report(*, experiment_id, fresh_artifact, surface, judge_runs):
    validate_blind_surface(surface)
    judge_runs = tuple(judge_runs)
    if len(judge_runs) != 2:
        raise ValueError("semantic_consensus_requires_two_judges")
    for run in judge_runs:
        validate_judge_run(run, surface=surface)
    if (len({run["judge_provider_id"] for run in judge_runs}) != 2
            or len({run["judge_model_id"] for run in judge_runs}) != 2):
        raise ValueError("semantic_consensus_judges_not_independent")
    indexes = tuple(_assessment_index(run) for run in judge_runs)
    trials, exact, compared, direct_conflicts = [], 0, 0, 0
    for blind_id, binding in sorted(surface["bindings"].items()):
        provider_states = {
            run["judge_model_id"]: indexes[index].get(blind_id, {}).get("criteria", {})
            for index, run in enumerate(judge_runs)
        }
        consensus = {}
        for criterion in JUDGE_CRITERIA:
            states = [provider_states[run["judge_model_id"]].get(criterion) for run in judge_runs]
            if any(state is None for state in states):
                consensus[criterion] = "UNRESOLVED"
                continue
            compared += 1
            if states[0] == states[1]:
                exact += 1
                consensus[criterion] = states[0]
            elif set(states) == {"PRESENT", "ABSENT"}:
                direct_conflicts += 1
                consensus[criterion] = "CONFLICT"
            else:
                consensus[criterion] = "UNCERTAIN"
        trials.append({
            "blind_candidate_id": blind_id,
            **binding,
            "provider_states": provider_states,
            "consensus": consensus,
            "strict_semantic_score": sum(
                state == "PRESENT" for state in consensus.values()
            ) / len(JUDGE_CRITERIA),
        })
    model_profiles = _model_profiles(fresh_artifact, trials, surface["excluded_trials"])
    agreement = exact / compared if compared else 0.0
    conflict_rate = direct_conflicts / compared if compared else 0.0
    all_batches = all(run["successful_batches"] == len(surface["batches"]) for run in judge_runs)
    calibration_ready = all_batches and agreement >= MIN_EXACT_AGREEMENT and conflict_rate <= MAX_DIRECT_CONFLICT
    source_report = fresh_artifact["report"]
    profiles = {item["model_id"]: item for item in model_profiles}
    selected = source_report["selected_small_model_id"]
    comparator = source_report["comparator_small_model_id"]
    strong = source_report["strong_model_id"]
    commitment = {
        "consensus_version": CONSENSUS_VERSION,
        "experiment_id": experiment_id,
        "source_artifact_hash": fresh_artifact["artifact_hash"],
        "source_report_hash": source_report["report_hash"],
        "blind_surface_hash": surface["surface_hash"],
        "judge_run_hashes": [run["judge_run_hash"] for run in judge_runs],
        "judge_models": [run["judge_model_id"] for run in judge_runs],
        "trials": trials,
        "excluded_trials": list(surface["excluded_trials"]),
        "model_profiles": model_profiles,
        "exact_criterion_agreement": agreement,
        "direct_conflict_rate": conflict_rate,
        "compared_criteria": compared,
        "all_judge_batches_complete": all_batches,
        "semantic_route_replicated": (
            profiles[selected]["effective_semantic_score"]
            >= profiles[comparator]["effective_semantic_score"]
        ),
        "selected_to_strong_semantic_ratio": (
            profiles[selected]["effective_semantic_score"]
            / profiles[strong]["effective_semantic_score"]
            if profiles[strong]["effective_semantic_score"] else None
        ),
        "candidate_state": (
            "SEMANTIC_SCALE_CALIBRATION_CANDIDATE"
            if calibration_ready else "SEMANTIC_JUDGE_DISAGREEMENT_REQUIRES_AUDIT"
        ),
        "selection_authority": False,
        "retention_authority": False,
        "human_audit_required": True,
        "total_provider_calls": sum(run["total_provider_calls"] for run in judge_runs),
        "total_tokens": sum(
            run["total_input_tokens"] + run["total_output_tokens"] for run in judge_runs
        ),
    }
    return {**commitment, "report_hash": hash_payload(commitment)}


def validate_semantic_report(report, *, fresh_artifact, surface, judge_runs):
    committed = {key: value for key, value in report.items() if key != "report_hash"}
    if report.get("report_hash") != hash_payload(committed):
        raise ValueError("semantic_consensus_report_hash_invalid")
    expected = build_semantic_report(
        experiment_id=report["experiment_id"], fresh_artifact=fresh_artifact,
        surface=surface, judge_runs=judge_runs,
    )
    if _normalized_report(report) != _normalized_report(expected):
        raise ValueError("semantic_consensus_report_invalid")


def _assessment_index(run):
    return {
        item["blind_candidate_id"]: item
        for judgment in run["judgments"] for item in judgment["payload"]["assessments"]
    }


def _normalized_report(report):
    normalized = {key: value for key, value in report.items() if key != "report_hash"}
    normalized["trials"] = sorted(normalized["trials"], key=lambda item: item["blind_candidate_id"])
    normalized["model_profiles"] = sorted(
        normalized["model_profiles"], key=lambda item: item["model_id"]
    )
    return normalized


def _model_profiles(fresh_artifact, trials, excluded):
    profiles = []
    source_profiles = {item["model_id"]: item for item in fresh_artifact["report"]["profiles"]}
    for model_id, source in source_profiles.items():
        available = [item for item in trials if item["model_id"] == model_id]
        missing = sum(item["model_id"] == model_id for item in excluded)
        total = len(available) + missing
        strict_sum = sum(item["strict_semantic_score"] for item in available)
        profiles.append({
            "model_id": model_id,
            "source_mechanical_score": source["mean_quality_score"],
            "semantically_assessed_trials": len(available),
            "unavailable_trials": missing,
            "available_packet_semantic_score": strict_sum / len(available) if available else 0.0,
            "effective_semantic_score": strict_sum / total if total else 0.0,
            "semantic_minus_mechanical": (
                strict_sum / total - source["mean_quality_score"] if total else 0.0
            ),
        })
    return profiles
