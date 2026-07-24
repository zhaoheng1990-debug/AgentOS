"""Hidden-Harness evaluation and profiles for structure elicitor capability."""

from __future__ import annotations

import re

from .provider_telemetry import hash_payload


CALIBRATION_VERSION = "structure_elicitor_capability_calibration_v0_2"
EVALUATION_SCOPES = {"CALIBRATION_ONLY", "FRESH_HOLDOUT"}
CRITERIA = (
    "GRAMMAR_COMPLETE",
    "NON_RESTATEMENT",
    "RIVAL_STRUCTURE_COVERAGE",
    "DECISIVE_CONTRAST",
    "DISCRIMINATING_QUESTION",
)
_PACKET = re.compile(
    r"^\s*RIVAL_A:\s*(?P<a>.+?)\s*\|\s*RIVAL_B:\s*(?P<b>.+?)\s*\|\s*"
    r"CONTRAST:\s*(?P<contrast>.+?)\s*\|\s*QUESTION:\s*(?P<question>.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)
_TOKENS = re.compile(r"[a-z0-9+]+", re.IGNORECASE)


def parse_packet(text):
    if not isinstance(text, str):
        return None
    match = _PACKET.fullmatch(text.strip())
    if not match:
        return None
    return {key: value.strip() for key, value in match.groupdict().items()}


def evaluate_packet(*, case, packet, model_id, provider_id, task_hash,
                    invocation_receipt, provider_status, provider_failures=(),
                    work_usage=None, telemetry_hashes=(),
                    evaluation_scope="CALIBRATION_ONLY"):
    if evaluation_scope not in EVALUATION_SCOPES:
        raise ValueError("structure_elicitor_evaluation_scope_invalid")
    text = str((packet or {}).get("contrastive_packet", "")).strip()
    segments = parse_packet(text)
    criteria = {key: False for key in CRITERIA}
    if segments:
        coverage = _rival_coverage(case, segments)
        criteria.update({
            "GRAMMAR_COMPLETE": all(segments.values()),
            "NON_RESTATEMENT": _non_restatement(text, case.prompt, case.item_id),
            "RIVAL_STRUCTURE_COVERAGE": coverage,
            "DECISIVE_CONTRAST": (
                _contains_any(segments["contrast"], case.rival_a_terms)
                and _contains_any(segments["contrast"], case.rival_b_terms)
            ),
            "DISCRIMINATING_QUESTION": (
                "?" in segments["question"]
                and _contains_any(segments["question"], case.question_terms)
            ),
        })
    usage = work_usage or invocation_receipt.get("token_usage") or {}
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "evaluation_scope": evaluation_scope,
        "item_id": case.item_id,
        "truth_commitment": case.truth_commitment(),
        "model_id": model_id,
        "provider_id": provider_id,
        "task_hash": task_hash,
        "packet_hash": hash_payload(packet or {}),
        "provider_status": provider_status,
        "provider_failures": list(provider_failures),
        "criteria": criteria,
        "quality_score": sum(criteria.values()) / len(CRITERIA),
        "provider_calls": int(usage.get("provider_calls") or 0),
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "invocation_receipt_hash": invocation_receipt.get("receipt_hash", ""),
        "telemetry_hashes": list(telemetry_hashes),
        "harness_owned": True,
        "provider_self_scored": False,
    }
    return {**commitment, "outcome_hash": hash_payload(commitment)}


def build_profile(*, model_id, provider_id, outcomes):
    outcomes = tuple(outcomes)
    if not outcomes or any(item["model_id"] != model_id for item in outcomes):
        raise ValueError("structure_calibration_profile_outcomes_invalid")
    scopes = {item.get("evaluation_scope", "CALIBRATION_ONLY") for item in outcomes}
    if len(scopes) != 1 or not scopes.issubset(EVALUATION_SCOPES):
        raise ValueError("structure_calibration_profile_scope_invalid")
    criterion_rates = {
        criterion: sum(item["criteria"][criterion] for item in outcomes) / len(outcomes)
        for criterion in CRITERIA
    }
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "model_id": model_id,
        "provider_id": provider_id,
        "independent_trials": len(outcomes),
        "successful_provider_trials": sum(item["provider_status"] == "COMPLETED" for item in outcomes),
        "criterion_rates": criterion_rates,
        "mean_quality_score": sum(item["quality_score"] for item in outcomes) / len(outcomes),
        "perfect_packets": sum(item["quality_score"] == 1.0 for item in outcomes),
        "total_provider_calls": sum(item["provider_calls"] for item in outcomes),
        "total_tokens": sum(item["input_tokens"] + item["output_tokens"] for item in outcomes),
        "outcome_hashes": [item["outcome_hash"] for item in outcomes],
        "scope": scopes.pop(),
        "fresh_holdout_authority": False,
        "retention_authority": False,
    }
    return {**commitment, "profile_hash": hash_payload(commitment)}


def build_calibration_report(*, experiment_id, profiles, strong_model_id, truth_commitment):
    profiles = tuple(profiles)
    strong = next((item for item in profiles if item["model_id"] == strong_model_id), None)
    small = tuple(item for item in profiles if item["model_id"] != strong_model_id)
    if strong is None or not small or len({item["model_id"] for item in profiles}) != len(profiles):
        raise ValueError("structure_calibration_report_profile_surface_invalid")
    ranked = sorted(
        small,
        key=lambda item: (
            item["mean_quality_score"],
            item["successful_provider_trials"],
            -item["total_tokens"],
            item["model_id"],
        ),
        reverse=True,
    )
    selected = ranked[0]
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "experiment_id": experiment_id,
        "truth_commitment": truth_commitment,
        "profiles": list(profiles),
        "strong_model_id": strong_model_id,
        "strong_model_quality_ceiling": strong["mean_quality_score"],
        "selected_small_model_id": selected["model_id"],
        "selected_small_quality": selected["mean_quality_score"],
        "small_to_strong_quality_ratio": (
            selected["mean_quality_score"] / strong["mean_quality_score"]
            if strong["mean_quality_score"] else None
        ),
        "routing_support_mode": "CALIBRATION_TRANSFER_CANDIDATE_EXPLORATORY",
        "same_context_support": False,
        "fresh_holdout_required": True,
        "selection_authority": False,
        "retention_authority": False,
    }
    return {**commitment, "report_hash": hash_payload(commitment)}


def validate_profile(profile):
    committed = {key: value for key, value in profile.items() if key != "profile_hash"}
    if profile.get("profile_hash") != hash_payload(committed):
        raise ValueError("structure_calibration_profile_hash_invalid")


def validate_report(report):
    committed = {key: value for key, value in report.items() if key != "report_hash"}
    if report.get("report_hash") != hash_payload(committed):
        raise ValueError("structure_calibration_report_hash_invalid")
    for profile in report["profiles"]:
        validate_profile(profile)


def _rival_coverage(case, segments):
    direct = (_contains_any(segments["a"], case.rival_a_terms)
              and _contains_any(segments["b"], case.rival_b_terms))
    reverse = (_contains_any(segments["a"], case.rival_b_terms)
               and _contains_any(segments["b"], case.rival_a_terms))
    return direct or reverse


def _contains_any(text, terms):
    normalized = " ".join(str(text).lower().split())
    return any(term.lower() in normalized for term in terms)


def _non_restatement(text, prompt, item_id):
    normalized = " ".join(text.lower().split())
    if normalized in {" ".join(prompt.lower().split()), item_id.lower()}:
        return False
    content = set(_TOKENS.findall(normalized))
    prompt_tokens = set(_TOKENS.findall(prompt.lower()))
    novel = content - prompt_tokens - {"rival", "a", "b", "contrast", "question"}
    return len(content) >= 18 and len(novel) / max(1, len(content)) >= 0.10
