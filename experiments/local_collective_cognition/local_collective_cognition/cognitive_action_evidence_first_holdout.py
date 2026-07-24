"""Fresh mechanism holdout for evidence-first selective challenge v0.22."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


EVIDENCE_FIRST_CORPUS_VERSION = "cognitive_action_evidence_first_holdout_v0_22"
EVIDENCE_FIRST_CORPUS_ID = "local-cognitive-action-evidence-first-v0-22"
DESIGN_STRATA = (
    "POSITIVE_DEFINITION",
    "COMPOSITIONAL_DERIVATION",
    "OPEN_SURFACE",
    "MISSING_SPECIFICATION",
)


@dataclass(frozen=True)
class EvidenceFirstCase:
    case_id: str
    object_family: str
    design_stratum: str
    public_prompt: str
    candidate_a: str
    candidate_b: str

    def commitment(self):
        return asdict(self)


CASES = (
    EvidenceFirstCase("EW-TA01", "TIME_ANCHOR", "POSITIVE_DEFINITION", "The protocol defines the audit date as the UTC date on which verification finishes. Candidates use the UTC verification-finish date or the submitter's local filing date.", "UTC date when verification finishes", "submitter's local filing date"),
    EvidenceFirstCase("EW-TA02", "TIME_ANCHOR", "COMPOSITIONAL_DERIVATION", "The checkpoint occurs three complete business days after a Tuesday approval, excluding the approval day and a Wednesday holiday. Candidates use Friday or Monday.", "Friday", "Monday"),
    EvidenceFirstCase("EW-TA03", "TIME_ANCHOR", "OPEN_SURFACE", "A notice asks for newly stable systems but gives no time threshold. Candidates use stable for 48 hours or stable for 14 days. Select only if context supports a default.", "stable for 48 hours", "stable for 14 days"),
    EvidenceFirstCase("EW-TA04", "TIME_ANCHOR", "MISSING_SPECIFICATION", "A report requests date profile DP-31, but its calendar definition is unavailable. Candidates use calendar-month boundaries or retail-period boundaries.", "calendar-month boundaries", "retail-period boundaries"),
    EvidenceFirstCase("EW-MR01", "MEMBERSHIP_RULE", "POSITIVE_DEFINITION", "The charter defines voting members as enrolled participants who completed orientation. Candidates include enrolled participants or only enrolled participants who completed orientation.", "all enrolled participants", "enrolled participants who completed orientation"),
    EvidenceFirstCase("EW-MR02", "MEMBERSHIP_RULE", "COMPOSITIONAL_DERIVATION", "Records qualify when consent was granted before export and had not been revoked by export time. Candidates include all consented records or records satisfying both conditions.", "all records ever consented", "consented before export and not revoked"),
    EvidenceFirstCase("EW-MR03", "MEMBERSHIP_RULE", "OPEN_SURFACE", "A review asks for established suppliers without an operational rule. Candidates use at least three fulfilled orders or at least two years since registration. Select only with a supported default.", "at least three fulfilled orders", "at least two years since registration"),
    EvidenceFirstCase("EW-MR04", "MEMBERSHIP_RULE", "MISSING_SPECIFICATION", "An export requires membership profile MP-19, but the profile handbook is absent. Candidates apply undocumented rule H or undocumented rule J.", "undocumented rule H", "undocumented rule J"),
    EvidenceFirstCase("EW-TE01", "TRANSITION_EVENT", "POSITIVE_DEFINITION", "The runbook defines restoration as the first transition from failed to healthy after intervention. Candidates count that transition or all healthy samples after intervention.", "first failed-to-healthy transition", "all healthy samples after intervention"),
    EvidenceFirstCase("EW-TE02", "TRANSITION_EVENT", "COMPOSITIONAL_DERIVATION", "Count jobs that moved from waiting to executing and then from executing to archived in the same run. Candidates count those two-step paths or all jobs currently archived.", "waiting-to-executing-to-archived paths", "all jobs currently archived"),
    EvidenceFirstCase("EW-TE03", "TRANSITION_EVENT", "OPEN_SURFACE", "A dashboard asks for resumed subscriptions without defining whether resume is an event or an end-state. Candidates count restart events or subscriptions active at cutoff. Select only with a supported default.", "restart events", "active at cutoff"),
    EvidenceFirstCase("EW-TE04", "TRANSITION_EVENT", "MISSING_SPECIFICATION", "A state export requests transition code TR-14 without its state-machine catalog. Candidates count entry into suspended or exit from suspended.", "entries into suspended", "exits from suspended"),
    EvidenceFirstCase("EW-AG01", "AGGREGATION_RULE", "POSITIVE_DEFINITION", "The scorecard defines weekly response time as the maximum of the seven daily medians. Candidates use the maximum of daily medians or the median of daily maxima.", "maximum of the seven daily medians", "median of the seven daily maxima"),
    EvidenceFirstCase("EW-AG02", "AGGREGATION_RULE", "COMPOSITIONAL_DERIVATION", "Each segment score is multiplied by its transaction share and the products are summed. Candidates use an unweighted segment mean or a transaction-weighted mean.", "unweighted segment mean", "transaction-weighted mean"),
    EvidenceFirstCase("EW-AG03", "AGGREGATION_RULE", "OPEN_SURFACE", "A brief asks for a representative processing delay without a distribution or reporting convention. Candidates use the mean or median. Select only if a default is defensible.", "mean processing delay", "median processing delay"),
    EvidenceFirstCase("EW-AG04", "AGGREGATION_RULE", "MISSING_SPECIFICATION", "A worksheet requests aggregation recipe AR-29, but the recipe catalog is missing. Candidates use a harmonic mean or a 10% trimmed mean.", "harmonic mean", "10% trimmed mean"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])


def build_evidence_first_holdout():
    _validate_cases()
    ordered = sorted(
        CASES,
        key=lambda case: hash_payload([
            EVIDENCE_FIRST_CORPUS_VERSION,
            case.case_id,
        ]),
    )
    items, bindings = [], {}
    for case in ordered:
        conflict_id = "evidence-first-" + hash_payload([
            EVIDENCE_FIRST_CORPUS_VERSION,
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
        "surface_version": EVIDENCE_FIRST_CORPUS_VERSION,
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
        "artifact_version": EVIDENCE_FIRST_CORPUS_VERSION,
        "corpus_id": EVIDENCE_FIRST_CORPUS_ID,
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
        "reference_state": "UNLABELED_FROZEN_BEFORE_EVIDENCE_FIRST_RUN",
        "v0_21_reference_available_during_inference": False,
        "reference_revision_allowed_after_candidate_run": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "evidence_refs": [f"corpus://{EVIDENCE_FIRST_CORPUS_ID}"],
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_evidence_first_holdout(artifact):
    commitment = {
        key: value for key, value in artifact.items()
        if key != "artifact_hash"
    }
    if (
        artifact.get("artifact_hash") != hash_payload(commitment)
        or artifact != build_evidence_first_holdout()
    ):
        raise ValueError("evidence_first_holdout_invalid")


def evidence_text(item):
    marker = " Candidates "
    prompt = item["public_prompt"]
    return prompt.split(marker, 1)[0] if marker in prompt else prompt


def _validate_cases():
    if len(CASES) != 16 or len({case.case_id for case in CASES}) != 16:
        raise ValueError("evidence_first_cases_invalid")
    for family in {case.object_family for case in CASES}:
        if {
            case.design_stratum
            for case in CASES
            if case.object_family == family
        } != set(DESIGN_STRATA):
            raise ValueError("evidence_first_cross_balance_invalid")
