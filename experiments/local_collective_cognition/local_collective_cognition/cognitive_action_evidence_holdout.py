"""Fresh holdout for contrastive evidence-state calibration v0.19."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


EVIDENCE_CORPUS_VERSION = "cognitive_action_evidence_holdout_v0_19"
EVIDENCE_CORPUS_ID = "local-cognitive-action-evidence-v0-19"
DESIGN_STRATA = (
    "DIRECT_DEFINITION",
    "COMPOSITIONAL_DETERMINATION",
    "SOFT_AMBIGUITY",
    "OPAQUE_SPECIFICATION",
)


@dataclass(frozen=True)
class EvidenceCase:
    case_id: str
    object_family: str
    design_stratum: str
    public_prompt: str
    candidate_a: str
    candidate_b: str

    def commitment(self):
        return asdict(self)


CASES = (
    EvidenceCase("EC-W01", "TIME_WINDOW", "DIRECT_DEFINITION", "A billing policy defines the October service period as 00:00 October 1 through 23:59 October 31. Candidates use that calendar interval or the 31 days ending October 31.", "October 1 through October 31", "31 days ending October 31"),
    EvidenceCase("EC-W02", "TIME_WINDOW", "COMPOSITIONAL_DETERMINATION", "A review covers the five complete business days immediately before Monday, November 18. Candidates use November 11 through November 15 or November 12 through November 18.", "November 11 through November 15", "November 12 through November 18"),
    EvidenceCase("EC-W03", "TIME_WINDOW", "SOFT_AMBIGUITY", "A usage memo requests recently active users without defining recent. Candidates use activity in the trailing seven days or activity in the current calendar week. Choose only if context supports a default.", "activity in the trailing seven days", "activity in the current calendar week"),
    EvidenceCase("EC-W04", "TIME_WINDOW", "OPAQUE_SPECIFICATION", "An export requests period key PK-22, but its calendar table is unavailable. Candidates use the previous 22 complete days or 22 days ending today. Determine whether either is supported.", "previous 22 complete days", "22 days ending today"),
    EvidenceCase("EC-E01", "ELIGIBILITY_SCOPE", "DIRECT_DEFINITION", "An audit defines reportable invoices as approved invoices above $1,000. Candidates include all approved invoices or only approved invoices above $1,000.", "approved invoices above $1,000", "all approved invoices"),
    EvidenceCase("EC-E02", "ELIGIBILITY_SCOPE", "COMPOSITIONAL_DETERMINATION", "Access requires an account active by March 1 and no overdue balance on March 5. Candidates include every account active by March 1 or only accounts satisfying both conditions.", "accounts active by March 1 with no overdue balance on March 5", "all accounts active by March 1"),
    EvidenceCase("EC-E03", "ELIGIBILITY_SCOPE", "SOFT_AMBIGUITY", "A procurement dashboard asks for engaged suppliers without defining engagement. Candidates include suppliers submitting any bid this year or suppliers awarded a contract this year. Choose only with a defensible default.", "suppliers submitting any bid this year", "suppliers awarded a contract this year"),
    EvidenceCase("EC-E04", "ELIGIBILITY_SCOPE", "OPAQUE_SPECIFICATION", "A ledger requests eligibility profile EP-31, but the policy appendix is missing. Candidates apply rule H6 or rule J8. Determine whether either profile is supported.", "records passing undocumented rule H6", "records passing undocumented rule J8"),
    EvidenceCase("EC-S01", "EVENT_VERSUS_STATE", "DIRECT_DEFINITION", "A metric defines newly activated devices as devices transitioning from inactive to active during the month. Candidates count those transitions or devices active at month end.", "inactive-to-active transitions during the month", "devices active at month end"),
    EvidenceCase("EC-S02", "EVENT_VERSUS_STATE", "COMPOSITIONAL_DETERMINATION", "The count includes cases closed, then reopened, between January 1 and January 31. Candidates count reopen transitions in January or cases in reopened status on January 31.", "reopen transitions during January", "cases in reopened status on January 31"),
    EvidenceCase("EC-S03", "EVENT_VERSUS_STATE", "SOFT_AMBIGUITY", "A retention note asks for churned customers without saying whether churn is a cancellation event or a cancelled state at cutoff. Choose only if a contextual default is justified.", "cancellation events during the period", "customers in cancelled state at cutoff"),
    EvidenceCase("EC-S04", "EVENT_VERSUS_STATE", "OPAQUE_SPECIFICATION", "A legacy report requests state marker SM-16 without its lifecycle model. Candidates count entry into escalation or residence in escalation at period end. Determine whether either is supported.", "entries into escalation", "items in escalation at period end"),
    EvidenceCase("EC-D01", "DENOMINATOR", "DIRECT_DEFINITION", "A delivery defect rate is explicitly defects per 10,000 orders confirmed delivered. Candidates divide by orders shipped or orders confirmed delivered.", "orders shipped", "orders confirmed delivered"),
    EvidenceCase("EC-D02", "DENOMINATOR", "COMPOSITIONAL_DETERMINATION", "A net error rate excludes test runs and duplicate runs from the exposure count. Candidates divide errors by all runs or by runs remaining after both exclusions.", "all recorded runs", "runs remaining after test and duplicate exclusions"),
    EvidenceCase("EC-D03", "DENOMINATOR", "SOFT_AMBIGUITY", "An incident metric asks for incidents normalized by workload without defining workload. Candidates use staffed hours or completed jobs. Choose only if context warrants a default.", "staffed hours", "completed jobs"),
    EvidenceCase("EC-D04", "DENOMINATOR", "OPAQUE_SPECIFICATION", "A scorecard names denominator code DC-44, but its specification is unavailable. Candidates use attempted transactions or validated transactions. Determine whether either is justified.", "attempted transactions", "validated transactions"),
    EvidenceCase("EC-A01", "ATTRIBUTION_RULE", "DIRECT_DEFINITION", "A report defines source credit as the first registered referral before signup. Candidates credit that first referral or the final interaction before signup.", "first registered referral before signup", "final interaction before signup"),
    EvidenceCase("EC-A02", "ATTRIBUTION_RULE", "COMPOSITIONAL_DETERMINATION", "Credit goes to the latest interaction after approval but before deployment. Candidates use the latest qualifying interaction in that interval or the earliest interaction after approval.", "latest qualifying interaction after approval and before deployment", "earliest interaction after approval"),
    EvidenceCase("EC-A03", "ATTRIBUTION_RULE", "SOFT_AMBIGUITY", "A maintenance report asks for community-contributed fixes without defining contribution. Candidates include issues with any community comment or fixes containing an accepted community patch. Choose only with a supported default.", "issues with any community comment", "fixes containing an accepted community patch"),
    EvidenceCase("EC-A04", "ATTRIBUTION_RULE", "OPAQUE_SPECIFICATION", "An archive requests attribution method AM-28 without its glossary. Candidates apply method P5 or method Q2. Determine whether either can be selected.", "credit under undocumented method P5", "credit under undocumented method Q2"),
    EvidenceCase("EC-G01", "AGGREGATION", "DIRECT_DEFINITION", "A cycle-time table explicitly requests the median duration. Candidates report arithmetic mean duration or median duration.", "arithmetic mean duration", "median duration"),
    EvidenceCase("EC-G02", "AGGREGATION", "COMPOSITIONAL_DETERMINATION", "A regional index is the sum of each region's score multiplied by its population share. Candidates use an unweighted mean or a population-weighted mean.", "unweighted regional mean", "population-weighted regional mean"),
    EvidenceCase("EC-G03", "AGGREGATION", "SOFT_AMBIGUITY", "A service brief asks for representative resolution time without a distribution description or reporting convention. Candidates use the arithmetic mean or median. Choose only if a default is defensible.", "arithmetic mean resolution time", "median resolution time"),
    EvidenceCase("EC-G04", "AGGREGATION", "OPAQUE_SPECIFICATION", "A study requests summary code ZS-4 without its codebook. Candidates use a harmonic mean or a trimmed median. Determine whether either is supported.", "harmonic mean", "trimmed median"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])


def build_evidence_holdout():
    _validate_cases()
    ordered = sorted(CASES, key=lambda case: hash_payload([EVIDENCE_CORPUS_VERSION, case.case_id]))
    items, bindings = [], {}
    for case in ordered:
        conflict_id = "evidence-fresh-" + hash_payload([EVIDENCE_CORPUS_VERSION, CASE_COMMITMENT, case.case_id])[:18]
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
        "surface_version": EVIDENCE_CORPUS_VERSION,
        "items": items,
        "semantic_labels_exposed": False,
        "design_strata_exposed": False,
        "candidate_outputs_exposed": False,
    }
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    commitment = {
        "artifact_version": EVIDENCE_CORPUS_VERSION,
        "corpus_id": EVIDENCE_CORPUS_ID,
        "case_commitment": CASE_COMMITMENT,
        "case_count": len(CASES),
        "family_counts": {family: sum(case.object_family == family for case in CASES) for family in sorted({case.object_family for case in CASES})},
        "design_stratum_counts": {stratum: sum(case.design_stratum == stratum for case in CASES) for stratum in DESIGN_STRATA},
        "public_surface": surface,
        "private_provenance": {
            "bindings": bindings,
            "design_strata_committed_but_not_reference_truth": True,
            "semantic_labels_present": False,
        },
        "reference_state": "UNLABELED_FROZEN_BEFORE_CANDIDATE_RUN",
        "calibration_labels_reused_as_validation": False,
        "reference_revision_allowed_after_candidate_run": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "evidence_refs": [f"corpus://{EVIDENCE_CORPUS_ID}"],
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_evidence_holdout(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_evidence_holdout():
        raise ValueError("evidence_holdout_invalid")


def _validate_cases():
    if len(CASES) != 24 or len({case.case_id for case in CASES}) != 24:
        raise ValueError("evidence_cases_invalid")
    for family in {case.object_family for case in CASES}:
        if {case.design_stratum for case in CASES if case.object_family == family} != set(DESIGN_STRATA):
            raise ValueError("evidence_cross_balance_invalid")
