"""Fresh holdout for the v0.21 decomposed source-ontology ablation."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


ONTOLOGY_CORPUS_VERSION = "cognitive_action_source_ontology_holdout_v0_21"
ONTOLOGY_CORPUS_ID = "local-cognitive-action-source-ontology-v0-21"
DESIGN_STRATA = (
    "POSITIVE_DEFINITION",
    "COMPOSITIONAL_DERIVATION",
    "OPEN_SURFACE",
    "MISSING_SPECIFICATION",
)


@dataclass(frozen=True)
class OntologyCase:
    case_id: str
    object_family: str
    design_stratum: str
    public_prompt: str
    candidate_a: str
    candidate_b: str

    def commitment(self):
        return asdict(self)


CASES = (
    OntologyCase("SO-RT01", "REFERENCE_TIME", "POSITIVE_DEFINITION", "The incident protocol defines the reference day as the calendar day in UTC on which triage begins. Candidates use the UTC triage-start day or the reporter's local submission day.", "UTC calendar day when triage begins", "reporter's local calendar day when submitted"),
    OntologyCase("SO-RT02", "REFERENCE_TIME", "COMPOSITIONAL_DERIVATION", "The snapshot is taken two complete business days after approval, excluding the approval day and weekends. Approval occurred on Thursday. Candidates use Monday or Tuesday.", "Monday", "Tuesday"),
    OntologyCase("SO-RT03", "REFERENCE_TIME", "OPEN_SURFACE", "A dashboard asks for recently stabilized services without defining recently. Candidates use stabilization within 7 days or within 30 days. Select only if the request supports a default.", "within 7 days", "within 30 days"),
    OntologyCase("SO-RT04", "REFERENCE_TIME", "MISSING_SPECIFICATION", "A filing requests reference calendar RC-41, but the calendar table is not supplied. Candidates anchor dates to fiscal weeks or ISO weeks.", "fiscal-week calendar", "ISO-week calendar"),
    OntologyCase("SO-EP01", "ELIGIBILITY_PREDICATE", "POSITIVE_DEFINITION", "The policy defines an eligible mentor as an active employee with at least two completed mentoring cycles. Candidates require both conditions or active employment alone.", "active with at least two completed cycles", "active employment alone"),
    OntologyCase("SO-EP02", "ELIGIBILITY_PREDICATE", "COMPOSITIONAL_DERIVATION", "Participants qualify when they enrolled before the cutoff and had not withdrawn by the review date. Candidates include all pre-cutoff enrollments or only records satisfying both clauses.", "enrolled before cutoff and not withdrawn", "all pre-cutoff enrollments"),
    OntologyCase("SO-EP03", "ELIGIBILITY_PREDICATE", "OPEN_SURFACE", "A review requests mature projects but provides no maturity rule. Candidates use at least two releases or at least one year of activity. Select only if a contextual default is supported.", "at least two releases", "at least one year of activity"),
    OntologyCase("SO-EP04", "ELIGIBILITY_PREDICATE", "MISSING_SPECIFICATION", "An intake form requires eligibility profile EL-8, but the profile definition is unavailable. Candidates apply threshold set P or threshold set Q.", "undocumented threshold set P", "undocumented threshold set Q"),
    OntologyCase("SO-CO01", "CHANGE_OPERATOR", "POSITIVE_DEFINITION", "The monitoring guide defines a recovery as the first transition from unavailable to available after an alert. Candidates count that transition or every available sample after the alert.", "first unavailable-to-available transition", "every available sample after the alert"),
    OntologyCase("SO-CO02", "CHANGE_OPERATOR", "COMPOSITIONAL_DERIVATION", "Count records whose status moved from queued to running and later from running to complete in the same batch. Candidates count completed two-step paths or all records currently complete.", "queued-to-running-to-complete paths", "all records currently complete"),
    OntologyCase("SO-CO03", "CHANGE_OPERATOR", "OPEN_SURFACE", "A report asks for reactivated users without saying whether reactivation is an event or an end-state. Candidates count a new login after dormancy or users active at cutoff. Select only with a supported default.", "new login after dormancy", "active at the cutoff"),
    OntologyCase("SO-CO04", "CHANGE_OPERATOR", "MISSING_SPECIFICATION", "A workflow export uses transition class TC-6 without the transition catalog. Candidates count entry into review or exit from review.", "entries into review", "exits from review"),
    OntologyCase("SO-DS01", "DENOMINATOR_SCOPE", "POSITIVE_DEFINITION", "The quality standard defines the defect rate denominator as inspected units that completed final testing. Candidates use all manufactured units or completed final-test units.", "all manufactured units", "units completing final testing"),
    OntologyCase("SO-DS02", "DENOMINATOR_SCOPE", "COMPOSITIONAL_DERIVATION", "The denominator includes staffed hours, then removes training time and approved leave. Candidates use all staffed hours or hours remaining after both removals.", "all staffed hours", "staffed hours minus training and approved leave"),
    OntologyCase("SO-DS03", "DENOMINATOR_SCOPE", "OPEN_SURFACE", "A utilization measure is requested per available seat, but available is not operationalized. Candidates use licensed seats or seats enabled that month. Select only if context supplies a default.", "licensed seats", "seats enabled that month"),
    OntologyCase("SO-DS04", "DENOMINATOR_SCOPE", "MISSING_SPECIFICATION", "A scorecard names denominator recipe DR-22, but the recipe registry is absent. Candidates use registered devices or devices reporting that week.", "registered devices", "devices reporting that week"),
    OntologyCase("SO-AW01", "ATTRIBUTION_WINDOW", "POSITIVE_DEFINITION", "The campaign rule defines credited contact as the earliest verified touch in the 14 days before signup. Candidates use that touch or the latest touch after signup.", "earliest verified touch in the 14 days before signup", "latest touch after signup"),
    OntologyCase("SO-AW02", "ATTRIBUTION_WINDOW", "COMPOSITIONAL_DERIVATION", "Credit the last eligible referral after consent and no later than three days before purchase. Candidates use the last referral in that interval or the first referral before consent.", "last eligible referral after consent and at least three days before purchase", "first referral before consent"),
    OntologyCase("SO-AW03", "ATTRIBUTION_WINDOW", "OPEN_SURFACE", "A brief asks which channel initiated a relationship but gives no attribution convention. Candidates use first recorded contact or first converted contact. Select only if a convention is supported.", "first recorded contact", "first converted contact"),
    OntologyCase("SO-AW04", "ATTRIBUTION_WINDOW", "MISSING_SPECIFICATION", "An attribution job requests window profile WP-5 without its rule sheet. Candidates use a 7-day lookback or a 28-day lookback.", "7-day lookback", "28-day lookback"),
    OntologyCase("SO-AR01", "AGGREGATION_RULE", "POSITIVE_DEFINITION", "The service objective defines monthly latency as the median of daily 95th-percentile values. Candidates use that median or the mean of daily means.", "median of daily 95th-percentile values", "mean of daily means"),
    OntologyCase("SO-AR02", "AGGREGATION_RULE", "COMPOSITIONAL_DERIVATION", "Each regional value is multiplied by its active-user share and the products are summed. Candidates use an unweighted regional mean or an active-user-weighted mean.", "unweighted regional mean", "active-user-weighted mean"),
    OntologyCase("SO-AR03", "AGGREGATION_RULE", "OPEN_SURFACE", "A summary requests a representative queue delay without a distribution or reporting convention. Candidates use the mean or median. Select only if a default is defensible.", "mean queue delay", "median queue delay"),
    OntologyCase("SO-AR04", "AGGREGATION_RULE", "MISSING_SPECIFICATION", "A workbook requests aggregation operator AO-17, but the operator registry is unavailable. Candidates use a trimmed mean or a geometric mean.", "trimmed mean", "geometric mean"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])


def build_source_ontology_holdout():
    _validate_cases()
    ordered = sorted(
        CASES,
        key=lambda case: hash_payload([
            ONTOLOGY_CORPUS_VERSION,
            case.case_id,
        ]),
    )
    items, bindings = [], {}
    for case in ordered:
        conflict_id = "source-ontology-" + hash_payload([
            ONTOLOGY_CORPUS_VERSION,
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
        "surface_version": ONTOLOGY_CORPUS_VERSION,
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
        "artifact_version": ONTOLOGY_CORPUS_VERSION,
        "corpus_id": ONTOLOGY_CORPUS_ID,
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
        "reference_state": "UNLABELED_FROZEN_BEFORE_SOURCE_ONTOLOGY_RUN",
        "v0_20_reference_available_during_inference": False,
        "v0_20_labels_used_as_validation": False,
        "reference_revision_allowed_after_candidate_run": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "evidence_refs": [f"corpus://{ONTOLOGY_CORPUS_ID}"],
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_source_ontology_holdout(artifact):
    commitment = {
        key: value for key, value in artifact.items()
        if key != "artifact_hash"
    }
    if (
        artifact.get("artifact_hash") != hash_payload(commitment)
        or artifact != build_source_ontology_holdout()
    ):
        raise ValueError("source_ontology_holdout_invalid")


def _validate_cases():
    if len(CASES) != 24 or len({case.case_id for case in CASES}) != 24:
        raise ValueError("source_ontology_cases_invalid")
    for family in {case.object_family for case in CASES}:
        observed = {
            case.design_stratum
            for case in CASES
            if case.object_family == family
        }
        if observed != set(DESIGN_STRATA):
            raise ValueError("source_ontology_cross_balance_invalid")
