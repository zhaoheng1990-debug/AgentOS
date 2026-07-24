"""Fresh holdout for the v0.20 source-recognition and gate-policy factorial."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


FACTORIAL_CORPUS_VERSION = "cognitive_action_evidence_factorial_holdout_v0_20"
FACTORIAL_CORPUS_ID = "local-cognitive-action-evidence-factorial-v0-20"
DESIGN_STRATA = (
    "DIRECT_DEFINITION",
    "COMPOSITIONAL_DETERMINATION",
    "SOFT_AMBIGUITY",
    "OPAQUE_SPECIFICATION",
)


@dataclass(frozen=True)
class FactorialCase:
    case_id: str
    object_family: str
    design_stratum: str
    public_prompt: str
    candidate_a: str
    candidate_b: str

    def commitment(self):
        return asdict(self)


CASES = (
    FactorialCase("EF-OI01", "OBSERVATION_INTERVAL", "DIRECT_DEFINITION", "A safety manual defines the night observation window as 22:00 through 05:59 local time. Candidates use that interval or 20:00 through 03:59.", "22:00 through 05:59", "20:00 through 03:59"),
    FactorialCase("EF-OI02", "OBSERVATION_INTERVAL", "COMPOSITIONAL_DETERMINATION", "A review covers the three complete Monday-to-Sunday weeks immediately before a reporting Monday. Candidates use the 21 days ending on the preceding Sunday or the 21 days ending on the reporting Monday.", "21 days ending on the preceding Sunday", "21 days ending on the reporting Monday"),
    FactorialCase("EF-OI03", "OBSERVATION_INTERVAL", "SOFT_AMBIGUITY", "A planning note requests near-term incidents but does not define near-term. Candidates use incidents in the next 14 calendar days or incidents through the end of next month. Select only if the context supports a default.", "next 14 calendar days", "through the end of next month"),
    FactorialCase("EF-OI04", "OBSERVATION_INTERVAL", "OPAQUE_SPECIFICATION", "A compliance export requests interval token QT-9, but the interval dictionary is unavailable. Candidates use the previous nine complete weeks or the current week plus eight preceding weeks.", "previous nine complete weeks", "current week plus eight preceding weeks"),
    FactorialCase("EF-MS01", "MEMBERSHIP_SCOPE", "DIRECT_DEFINITION", "A program defines qualifying workshops as sessions with an instructor and at least 20 attendees. Candidates include every scheduled session or only sessions meeting both conditions.", "sessions with an instructor and at least 20 attendees", "every scheduled session"),
    FactorialCase("EF-MS02", "MEMBERSHIP_SCOPE", "COMPOSITIONAL_DETERMINATION", "The cohort includes accounts approved after June 1 that have not been revoked by the July 15 cutoff. Candidates include all accounts approved after June 1 or only accounts satisfying both conditions.", "approved after June 1 and not revoked by July 15", "all accounts approved after June 1"),
    FactorialCase("EF-MS03", "MEMBERSHIP_SCOPE", "SOFT_AMBIGUITY", "A portfolio review asks for high-activity repositories without an operational threshold. Candidates use the top decile by commits or repositories with at least 50 commits. Select only with a defensible contextual default.", "top decile by commits", "at least 50 commits"),
    FactorialCase("EF-MS04", "MEMBERSHIP_SCOPE", "OPAQUE_SPECIFICATION", "A registry requests cohort profile CP-73, but its handbook entry is missing. Candidates apply membership rule R4 or membership rule T7.", "records passing undocumented rule R4", "records passing undocumented rule T7"),
    FactorialCase("EF-ES01", "EVENT_VERSUS_STATE", "DIRECT_DEFINITION", "A reliability metric defines recovered sessions as sessions transitioning from degraded to normal during the hour. Candidates count those transitions or sessions normal at the hour end.", "degraded-to-normal transitions during the hour", "sessions normal at the hour end"),
    FactorialCase("EF-ES02", "EVENT_VERSUS_STATE", "COMPOSITIONAL_DETERMINATION", "The audit counts tickets that entered hold and later left hold during the quarter. Candidates count hold-exit transitions or tickets outside hold at quarter end.", "hold-exit transitions during the quarter", "tickets outside hold at quarter end"),
    FactorialCase("EF-ES03", "EVENT_VERSUS_STATE", "SOFT_AMBIGUITY", "A subscriber report asks for returned subscribers without specifying whether return means a resubscription event or active status at cutoff. Select only if one reading has a supported default.", "resubscription events during the period", "subscribers active again at cutoff"),
    FactorialCase("EF-ES04", "EVENT_VERSUS_STATE", "OPAQUE_SPECIFICATION", "A dashboard requests lifecycle flag LF-27 without the state-machine definition. Candidates count entry into recovery or residence in recovery at period end.", "entries into recovery", "items in recovery at period end"),
    FactorialCase("EF-XB01", "EXPOSURE_BASE", "DIRECT_DEFINITION", "A reliability standard defines incident frequency as incidents per 1,000 operating machine-hours. Candidates divide by installed machine-hours or operating machine-hours.", "installed machine-hours", "operating machine-hours"),
    FactorialCase("EF-XB02", "EXPOSURE_BASE", "COMPOSITIONAL_DETERMINATION", "The exposure base excludes scheduled downtime and diagnostic test cycles. Candidates use all logged hours or hours remaining after both exclusions.", "all logged hours", "hours after scheduled downtime and test-cycle exclusions"),
    FactorialCase("EF-XB03", "EXPOSURE_BASE", "SOFT_AMBIGUITY", "A productivity ratio is requested per unit of capacity, but capacity is not operationally defined. Candidates use rated equipment capacity or actually staffed capacity. Select only if context warrants a default.", "rated equipment capacity", "actually staffed capacity"),
    FactorialCase("EF-XB04", "EXPOSURE_BASE", "OPAQUE_SPECIFICATION", "A performance sheet names exposure-base code EB-12, but its specification is unavailable. Candidates use commissioned units or units active during the period.", "commissioned units", "units active during the period"),
    FactorialCase("EF-CA01", "CREDIT_ASSIGNMENT", "DIRECT_DEFINITION", "A sales policy defines lead credit as the last verified campaign touch before qualification. Candidates credit that touch or the first campaign touch after qualification.", "last verified campaign touch before qualification", "first campaign touch after qualification"),
    FactorialCase("EF-CA02", "CREDIT_ASSIGNMENT", "COMPOSITIONAL_DETERMINATION", "Credit goes to the earliest eligible event after consent but before the first purchase. Candidates use the earliest event in that interval or the latest event before consent.", "earliest eligible event after consent and before purchase", "latest event before consent"),
    FactorialCase("EF-CA03", "CREDIT_ASSIGNMENT", "SOFT_AMBIGUITY", "A renewal report asks for partner-influenced renewals but gives no definition of influence. Candidates include any recorded partner interaction or only a formal partner referral. Select only with a supported default.", "any recorded partner interaction", "formal partner referral"),
    FactorialCase("EF-CA04", "CREDIT_ASSIGNMENT", "OPAQUE_SPECIFICATION", "An attribution file requests profile AP-64 without its rulebook. Candidates assign credit by undocumented rule C3 or undocumented rule D9.", "credit under undocumented rule C3", "credit under undocumented rule D9"),
    FactorialCase("EF-SO01", "SUMMARY_OPERATOR", "DIRECT_DEFINITION", "A latency report explicitly requests the 90th percentile duration. Candidates report the arithmetic mean or the 90th percentile.", "arithmetic mean duration", "90th percentile duration"),
    FactorialCase("EF-SO02", "SUMMARY_OPERATOR", "COMPOSITIONAL_DETERMINATION", "A category index is the sum of each category value multiplied by its revenue share. Candidates use an unweighted mean or a revenue-weighted mean.", "unweighted category mean", "revenue-weighted category mean"),
    FactorialCase("EF-SO03", "SUMMARY_OPERATOR", "SOFT_AMBIGUITY", "A logistics brief asks for typical delivery delay without a distribution description or reporting convention. Candidates use the arithmetic mean or median. Select only if a default is defensible.", "arithmetic mean delivery delay", "median delivery delay"),
    FactorialCase("EF-SO04", "SUMMARY_OPERATOR", "OPAQUE_SPECIFICATION", "A research table requests summary operator SX-11, but the operator catalog is missing. Candidates use a geometric mean or a winsorized median.", "geometric mean", "winsorized median"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])


def build_factorial_holdout():
    _validate_cases()
    ordered = sorted(
        CASES,
        key=lambda case: hash_payload([FACTORIAL_CORPUS_VERSION, case.case_id]),
    )
    items, bindings = [], {}
    for case in ordered:
        conflict_id = "evidence-factorial-" + hash_payload([
            FACTORIAL_CORPUS_VERSION,
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
            "public_item_hash": hash_payload(item),
        }
    surface_commitment = {
        "surface_version": FACTORIAL_CORPUS_VERSION,
        "items": items,
        "semantic_labels_exposed": False,
        "design_strata_exposed": False,
        "candidate_outputs_exposed": False,
    }
    surface = {
        **surface_commitment,
        "surface_hash": hash_payload(surface_commitment),
    }
    commitment = {
        "artifact_version": FACTORIAL_CORPUS_VERSION,
        "corpus_id": FACTORIAL_CORPUS_ID,
        "case_commitment": CASE_COMMITMENT,
        "case_count": len(CASES),
        "family_counts": {
            family: sum(case.object_family == family for case in CASES)
            for family in sorted({case.object_family for case in CASES})
        },
        "design_stratum_counts": {
            stratum: sum(case.design_stratum == stratum for case in CASES)
            for stratum in DESIGN_STRATA
        },
        "public_surface": surface,
        "private_provenance": {
            "bindings": bindings,
            "design_strata_committed_but_not_reference_truth": True,
            "semantic_labels_present": False,
        },
        "reference_state": "UNLABELED_FROZEN_BEFORE_FACTORIAL_RUN",
        "v0_19_labels_available_during_inference": False,
        "calibration_labels_reused_as_validation": False,
        "reference_revision_allowed_after_candidate_run": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "evidence_refs": [f"corpus://{FACTORIAL_CORPUS_ID}"],
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_factorial_holdout(artifact):
    commitment = {
        key: value for key, value in artifact.items() if key != "artifact_hash"
    }
    if (
        artifact.get("artifact_hash") != hash_payload(commitment)
        or artifact != build_factorial_holdout()
    ):
        raise ValueError("evidence_factorial_holdout_invalid")


def _validate_cases():
    if len(CASES) != 24 or len({case.case_id for case in CASES}) != 24:
        raise ValueError("evidence_factorial_cases_invalid")
    for family in {case.object_family for case in CASES}:
        observed = {
            case.design_stratum
            for case in CASES
            if case.object_family == family
        }
        if observed != set(DESIGN_STRATA):
            raise ValueError("evidence_factorial_cross_balance_invalid")
