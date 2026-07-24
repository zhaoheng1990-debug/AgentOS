"""Fresh structural smoke holdout for the candidate-blind funnel v0.24."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


FUNNEL_CORPUS_VERSION = (
    "cognitive_action_candidate_blind_funnel_holdout_v0_24"
)
FUNNEL_CORPUS_ID = "local-cognitive-action-candidate-blind-funnel-v0-24"
SOURCE_STATUSES = ("AVAILABLE", "MISSING", "UNSPECIFIED", "CONFLICTED")


@dataclass(frozen=True)
class CandidateBlindFunnelCase:
    case_id: str
    object_family: str
    source_status: str
    public_prompt: str
    candidate_a: str
    candidate_b: str

    def commitment(self):
        return asdict(self)


CASES = (
    CandidateBlindFunnelCase("CF-RP01", "REFERENCE_POPULATION", "AVAILABLE", "The roster rule defines the reference population as accounts active on both the first and last day of the quarter. Candidates use accounts active on any day or accounts active on both boundary days.", "accounts active on any day", "accounts active on both boundary days"),
    CandidateBlindFunnelCase("CF-RP02", "REFERENCE_POPULATION", "UNSPECIFIED", "The report requests core customers but provides no behavioral or percentile threshold. Candidates use at least five purchases or the top revenue decile.", "at least five purchases", "top revenue decile"),
    CandidateBlindFunnelCase("CF-ET01", "EVENT_TIME_WINDOW", "AVAILABLE", "The observation window opens two hours after an event is accepted and closes six hours after acceptance. Candidates use acceptance through hour six or hour two through hour six.", "acceptance through hour six", "hour two through hour six"),
    CandidateBlindFunnelCase("CF-ET02", "EVENT_TIME_WINDOW", "MISSING", "The export requests time profile TP-64, but the profile registry is unavailable. Candidates use receipt time or processing-completion time.", "receipt time", "processing-completion time"),
    CandidateBlindFunnelCase("CF-FD01", "FEATURE_DERIVATION", "CONFLICTED", "The main specification says to center each value by subtracting the cohort median, while the signed appendix says to subtract the cohort mean. Candidates use median centering or mean centering.", "median centering", "mean centering"),
    CandidateBlindFunnelCase("CF-FD02", "FEATURE_DERIVATION", "MISSING", "The pipeline invokes feature transform FT-73, but its formula catalog is absent. Candidates use log-one-plus scaling or square-root scaling.", "log-one-plus scaling", "square-root scaling"),
    CandidateBlindFunnelCase("CF-PS01", "POLICY_SCOPE", "UNSPECIFIED", "The review covers material markets but gives no materiality rule. Candidates include markets above five percent of revenue or every regulated market.", "markets above five percent of revenue", "every regulated market"),
    CandidateBlindFunnelCase("CF-PS02", "POLICY_SCOPE", "CONFLICTED", "The scope memo says pilot sites are excluded, while a later signed addendum says pilot sites are included. Candidates exclude pilot sites or include pilot sites.", "exclude pilot sites", "include pilot sites"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])


def build_candidate_blind_funnel_holdout():
    _validate_cases()
    ordered = sorted(
        CASES,
        key=lambda case: hash_payload([
            FUNNEL_CORPUS_VERSION,
            case.case_id,
        ]),
    )
    items, bindings = [], {}
    for case in ordered:
        conflict_id = "candidate-blind-funnel-" + hash_payload([
            FUNNEL_CORPUS_VERSION,
            CASE_COMMITMENT,
            case.case_id,
        ])[:18]
        item = {
            "conflict_id": conflict_id,
            "public_prompt": case.public_prompt,
            "candidate_a": case.candidate_a,
            "candidate_b": case.candidate_b,
        }
        items.append(item)
        bindings[conflict_id] = {
            "case_id": case.case_id,
            "object_family": case.object_family,
            "source_status": case.source_status,
            "public_item_hash": hash_payload(item),
        }
    surface_commitment = {
        "surface_version": FUNNEL_CORPUS_VERSION,
        "items": items,
        "source_statuses_exposed": False,
        "candidate_outputs_exposed": False,
    }
    surface = {
        **surface_commitment,
        "surface_hash": hash_payload(surface_commitment),
    }
    commitment = {
        "artifact_version": FUNNEL_CORPUS_VERSION,
        "corpus_id": FUNNEL_CORPUS_ID,
        "case_commitment": CASE_COMMITMENT,
        "case_count": len(CASES),
        "family_counts": {
            family: sum(case.object_family == family for case in CASES)
            for family in sorted({case.object_family for case in CASES})
        },
        "source_status_counts": {
            status: sum(case.source_status == status for case in CASES)
            for status in SOURCE_STATUSES
        },
        "public_surface": surface,
        "private_provenance": {
            "bindings": bindings,
            "source_statuses_are_synthetic_construction_metadata": True,
            "external_semantic_labels_present": False,
        },
        "reference_state": (
            "SYNTHETIC_STRUCTURAL_SMOKE_FROZEN_BEFORE_FUNNEL_RUN"
        ),
        "v0_23_receipts_available_during_inference": False,
        "reference_revision_allowed_after_candidate_run": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "evidence_refs": [f"corpus://{FUNNEL_CORPUS_ID}"],
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_candidate_blind_funnel_holdout(artifact):
    commitment = {
        key: value for key, value in artifact.items()
        if key != "artifact_hash"
    }
    if (
        artifact.get("artifact_hash") != hash_payload(commitment)
        or artifact != build_candidate_blind_funnel_holdout()
    ):
        raise ValueError("candidate_blind_funnel_holdout_invalid")


def evidence_text(item):
    marker = " Candidates "
    prompt = item["public_prompt"]
    return prompt.split(marker, 1)[0] if marker in prompt else prompt


def _validate_cases():
    if len(CASES) != 8 or len({case.case_id for case in CASES}) != 8:
        raise ValueError("candidate_blind_funnel_cases_invalid")
    if {case.source_status for case in CASES} != set(SOURCE_STATUSES):
        raise ValueError("candidate_blind_funnel_status_coverage_invalid")
    if any(
        sum(case.source_status == status for case in CASES) != 2
        for status in SOURCE_STATUSES
    ):
        raise ValueError("candidate_blind_funnel_status_balance_invalid")
