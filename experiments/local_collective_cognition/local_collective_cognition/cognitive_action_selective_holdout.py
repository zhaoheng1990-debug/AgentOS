"""Fresh unlabeled holdout for object-conditional collaboration v0.18."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


SELECTIVE_CORPUS_VERSION = "cognitive_action_selective_holdout_v0_18"
SELECTIVE_CORPUS_ID = "local-cognitive-action-selective-v0-18"
DESIGN_STRATA = (
    "DIRECT_DEFINITION",
    "COMPOSITIONAL_DETERMINATION",
    "SOFT_AMBIGUITY",
    "OPAQUE_SPECIFICATION",
)


@dataclass(frozen=True)
class SelectiveCase:
    case_id: str
    object_family: str
    design_stratum: str
    public_prompt: str
    candidate_a: str
    candidate_b: str

    def commitment(self):
        return asdict(self)


CASES = (
    SelectiveCase("SC-W01", "TIME_WINDOW", "DIRECT_DEFINITION", "A compliance extract defines end-of-month active accounts as accounts whose status is active at 23:59 on September 30. Choose between accounts active at that instant and accounts active at any time during September.", "accounts active at any time during September", "accounts active at 23:59 on September 30"),
    SelectiveCase("SC-W02", "TIME_WINDOW", "COMPOSITIONAL_DETERMINATION", "A review covers the seven complete calendar days immediately before Monday, August 12. Candidates use August 5 through August 11 or August 6 through August 12.", "August 5 through August 11", "August 6 through August 12"),
    SelectiveCase("SC-W03", "TIME_WINDOW", "SOFT_AMBIGUITY", "A product brief requests weekly active teams but supplies no local definition. Candidates count teams active at least once during the week or teams active on the final day. Choose one only if the displayed context supports it.", "teams active at least once during the week", "teams active on the final day"),
    SelectiveCase("SC-W04", "TIME_WINDOW", "OPAQUE_SPECIFICATION", "An archive request names reporting window WX-14, but the defining calendar is unavailable. Candidates use the last fourteen complete days or the fourteen days ending today. Determine whether either is supported.", "last fourteen complete calendar days", "fourteen days ending today"),
    SelectiveCase("SC-E01", "ELIGIBILITY_SCOPE", "DIRECT_DEFINITION", "A protocol defines the safety population as participants who received at least one study dose. Candidates use all randomized participants or participants receiving at least one dose.", "participants receiving at least one dose", "all randomized participants"),
    SelectiveCase("SC-E02", "ELIGIBILITY_SCOPE", "COMPOSITIONAL_DETERMINATION", "A mailing is limited to members registered before June 1 who had not opted out by June 10. Candidates include all members registered before June 1 or only those also not opted out by June 10.", "members registered before June 1 and not opted out by June 10", "all members registered before June 1"),
    SelectiveCase("SC-E03", "ELIGIBILITY_SCOPE", "SOFT_AMBIGUITY", "A campus report asks for currently participating students without defining current participation. Candidates use students with any activity this term or students enrolled on the reporting date. Choose one only if context supplies a defensible default.", "students with any activity this term", "students enrolled on the reporting date"),
    SelectiveCase("SC-E04", "ELIGIBILITY_SCOPE", "OPAQUE_SPECIFICATION", "A registry requests cohort rule CR-27, but its rulebook is missing. Candidates are records passing filter K4 and records passing filter M9. Determine whether either cohort is supported.", "records passing undocumented filter K4", "records passing undocumented filter M9"),
    SelectiveCase("SC-S01", "EVENT_VERSUS_STATE", "DIRECT_DEFINITION", "A workforce table asks how many employees entered a supervisor role during Q3. Candidates count transitions into supervisor roles during Q3 or employees holding supervisor roles at quarter end.", "employees holding supervisor roles at Q3 end", "transitions into supervisor roles during Q3"),
    SelectiveCase("SC-S02", "EVENT_VERSUS_STATE", "COMPOSITIONAL_DETERMINATION", "The metric counts orders that moved from pending to approved between May 1 and May 31. Candidates count approval transitions in May or orders remaining approved on May 31.", "approval transitions between May 1 and May 31", "orders in approved state on May 31"),
    SelectiveCase("SC-S03", "EVENT_VERSUS_STATE", "SOFT_AMBIGUITY", "An operations note requests recovered jobs but does not say whether recovery means a successful retry event or being in a recovered status at cutoff. Choose one only if a contextual default is justified.", "successful retry events", "jobs marked recovered at cutoff"),
    SelectiveCase("SC-S04", "EVENT_VERSUS_STATE", "OPAQUE_SPECIFICATION", "A legacy dashboard requests lifecycle indicator LI-8 without its state model. Candidates count entry into verification or residence in verification at period end. Determine whether either is supported.", "entries into verification", "items in verification at period end"),
    SelectiveCase("SC-D01", "DENOMINATOR", "DIRECT_DEFINITION", "A reliability measure is defined as failures per 1,000 completed sessions. Candidates divide failures by sessions started or by sessions completed.", "sessions started", "sessions completed"),
    SelectiveCase("SC-D02", "DENOMINATOR", "COMPOSITIONAL_DETERMINATION", "A conversion measure is purchases divided by eligible visits after bot traffic and internal visits are removed. Candidates use all recorded visits or the remaining eligible visits.", "remaining eligible visits after both exclusions", "all recorded visits"),
    SelectiveCase("SC-D03", "DENOMINATOR", "SOFT_AMBIGUITY", "A support review asks for complaints normalized by customer activity but does not define activity. Candidates use complaints per active account or complaints per completed order. Choose one only if context warrants it.", "active accounts", "completed orders"),
    SelectiveCase("SC-D04", "DENOMINATOR", "OPAQUE_SPECIFICATION", "A benchmark requests denominator DN-12, but its specification is unavailable. Candidates use eligible requests or successfully logged requests. Determine whether either is justified.", "eligible requests", "successfully logged requests"),
    SelectiveCase("SC-A01", "ATTRIBUTION_RULE", "DIRECT_DEFINITION", "A campaign report explicitly uses last-touch attribution. Candidates credit the earliest recorded campaign interaction or the final campaign interaction before purchase.", "final campaign interaction before purchase", "earliest recorded campaign interaction"),
    SelectiveCase("SC-A02", "ATTRIBUTION_RULE", "COMPOSITIONAL_DETERMINATION", "Credit goes to the earliest interaction that occurred after qualification and before contract signature. Candidates use the earliest qualifying interaction in that interval or the final interaction before signature.", "earliest qualifying interaction after qualification and before signature", "final interaction before signature"),
    SelectiveCase("SC-A03", "ATTRIBUTION_RULE", "SOFT_AMBIGUITY", "A partnership memo asks for partner-influenced revenue without defining influence. Candidates include deals with any documented partner meeting or only deals sourced from a registered partner lead. Choose one only if context supports a default.", "deals with any documented partner meeting", "deals sourced from a registered partner lead"),
    SelectiveCase("SC-A04", "ATTRIBUTION_RULE", "OPAQUE_SPECIFICATION", "A historical export requests attribution policy AP-19, but the glossary is unavailable. Candidates apply rule U2 or rule V7. Determine whether either policy is supported.", "credit under undocumented rule U2", "credit under undocumented rule V7"),
    SelectiveCase("SC-G01", "AGGREGATION", "DIRECT_DEFINITION", "A latency objective explicitly requests the 95th percentile. Candidates report mean request latency or p95 request latency.", "95th-percentile request latency", "mean request latency"),
    SelectiveCase("SC-G02", "AGGREGATION", "COMPOSITIONAL_DETERMINATION", "A portfolio score is defined as the sum of each asset score times its capital weight. Candidates use an unweighted arithmetic mean or a capital-weighted mean.", "unweighted arithmetic mean", "capital-weighted mean"),
    SelectiveCase("SC-G03", "AGGREGATION", "SOFT_AMBIGUITY", "A quality brief asks for a typical repair duration in a strongly skewed sample but gives no reporting convention. Candidates use the arithmetic mean or the median. Choose one only if a contextual default is defensible.", "arithmetic mean repair duration", "median repair duration"),
    SelectiveCase("SC-G04", "AGGREGATION", "OPAQUE_SPECIFICATION", "A research table requests statistic SX-9 without its codebook. Candidates use a winsorized mean or a geometric mean. Determine whether either is supported.", "winsorized mean", "geometric mean"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])


def build_selective_holdout():
    _validate_cases()
    ordered = sorted(CASES, key=lambda case: hash_payload([SELECTIVE_CORPUS_VERSION, case.case_id]))
    items, bindings = [], {}
    for case in ordered:
        conflict_id = "selective-fresh-" + hash_payload([SELECTIVE_CORPUS_VERSION, CASE_COMMITMENT, case.case_id])[:18]
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
        "surface_version": SELECTIVE_CORPUS_VERSION,
        "items": items,
        "semantic_labels_exposed": False,
        "design_strata_exposed": False,
        "candidate_outputs_exposed": False,
    }
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    commitment = {
        "artifact_version": SELECTIVE_CORPUS_VERSION,
        "corpus_id": SELECTIVE_CORPUS_ID,
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
        "reference_state": "UNLABELED_FROZEN_BEFORE_CANDIDATE_RUN",
        "reference_revision_allowed_after_candidate_run": False,
        "real_world_ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "evidence_refs": [f"corpus://{SELECTIVE_CORPUS_ID}"],
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_selective_holdout(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_selective_holdout():
        raise ValueError("selective_holdout_invalid")


def _validate_cases():
    if len(CASES) != 24 or len({case.case_id for case in CASES}) != 24:
        raise ValueError("selective_cases_invalid")
    family_counts = {
        family: sum(case.object_family == family for case in CASES)
        for family in {case.object_family for case in CASES}
    }
    stratum_counts = {
        stratum: sum(case.design_stratum == stratum for case in CASES)
        for stratum in DESIGN_STRATA
    }
    if len(family_counts) != 6 or set(family_counts.values()) != {4}:
        raise ValueError("selective_family_balance_invalid")
    if set(stratum_counts.values()) != {6}:
        raise ValueError("selective_stratum_balance_invalid")
    for family in family_counts:
        if {case.design_stratum for case in CASES if case.object_family == family} != set(DESIGN_STRATA):
            raise ValueError("selective_cross_balance_invalid")
