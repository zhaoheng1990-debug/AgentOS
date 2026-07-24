"""Fresh unlabeled holdout for routed cognitive actions v0.16."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


FRESH_CORPUS_VERSION = "cognitive_action_fresh_holdout_v0_16"
FRESH_CORPUS_ID = "local-cognitive-action-fresh-v0-16"


@dataclass(frozen=True)
class FreshActionCase:
    case_id: str
    object_family: str
    public_prompt: str
    candidate_a: str
    candidate_b: str

    def commitment(self):
        return asdict(self)


CASES = (
    FreshActionCase("AF-A01", "AGGREGATION_STATISTIC", "A commerce review asks for average order value, defined as total recognized order revenue divided by completed orders. Choose the matching candidate.", "recognized order revenue divided by completed orders", "median completed-order value"),
    FreshActionCase("AF-A02", "AGGREGATION_STATISTIC", "An incident review asks for typical restoration time but gives no convention for skewed durations. Candidates are arithmetic mean restoration time and median restoration time. Choose one or leave the object open.", "arithmetic mean restoration time", "median restoration time"),
    FreshActionCase("AF-A03", "AGGREGATION_STATISTIC", "A reliability target specifies p95 request latency. Available measures are mean request latency and the 95th percentile of request latency. Choose the requested measure.", "mean request latency", "95th-percentile request latency"),
    FreshActionCase("AF-A04", "AGGREGATION_STATISTIC", "A weekly dashboard asks for average daily active users across seven calendar days. Candidates are the sum of each day's active-user count divided by seven, and distinct users active at least once during the week. Choose the requested measure.", "sum of daily active-user counts divided by seven", "distinct weekly active users"),
    FreshActionCase("AF-T01", "ATTRIBUTION_SCOPE", "A campaign report asks for last-click-attributed revenue. Candidates are revenue assigned to the final campaign touch before purchase and revenue assigned to any campaign appearing in the journey. Choose the requested measure.", "revenue assigned to the final campaign touch", "revenue assigned to any journey campaign"),
    FreshActionCase("AF-T02", "ATTRIBUTION_SCOPE", "A board note asks for marketing-influenced pipeline but supplies no attribution window or influence rule. Candidates count opportunities with any logged marketing touch, or only opportunities whose first touch was marketing. Choose one or leave the object open.", "opportunities with any marketing touch", "opportunities whose first touch was marketing"),
    FreshActionCase("AF-T03", "ATTRIBUTION_SCOPE", "A partner report asks for deals directly sourced by partners. Candidates are deals whose recorded originating source is a partner and deals with any partner interaction before close. Choose the requested measure.", "deals with a partner as recorded originating source", "deals with any pre-close partner interaction"),
    FreshActionCase("AF-T04", "ATTRIBUTION_SCOPE", "A legacy report requests attribution metric M7. The glossary entry and attribution rule are unavailable. Candidates are pipeline under rule X2 and pipeline under rule Y4. Determine whether the object can be assessed.", "pipeline under undocumented rule X2", "pipeline under undocumented rule Y4"),
    FreshActionCase("AF-U01", "OBSERVATION_UNIT", "A public-health brief asks how many people received at least one message. Candidates are delivered-message events and distinct recipients with a delivery. Choose the requested measure.", "delivered-message event count", "distinct recipients with at least one delivery"),
    FreshActionCase("AF-U02", "OBSERVATION_UNIT", "A housing service asks for households served. Available measures are distinct household identifiers receiving service and distinct individual clients receiving service. Choose the requested measure.", "distinct served household identifiers", "distinct served individual clients"),
    FreshActionCase("AF-U03", "OBSERVATION_UNIT", "An operations note asks for affected accounts. Candidates are incident-event count and distinct accounts associated with at least one incident. Choose the requested measure.", "incident-event count", "distinct accounts with at least one incident"),
    FreshActionCase("AF-U04", "OBSERVATION_UNIT", "A survey export asks for respondent units under coding scheme R. The codebook is missing. Candidates are unique record keys and unique household keys. Determine whether selection is possible.", "unique record keys", "unique household keys"),
    FreshActionCase("AF-S01", "STATE_TRANSITION", "A subscription report asks for accounts newly activated during June. Candidates are accounts whose activation transition occurred in June and accounts still active at June month end. Choose the requested measure.", "accounts activated during June", "accounts active at June month end"),
    FreshActionCase("AF-S02", "STATE_TRANSITION", "A workflow report asks for cases completed during the week. Candidates are cases entering the workflow during the week and cases reaching the completed state during the week. Choose the requested measure.", "cases entering the workflow during the week", "cases reaching completed state during the week"),
    FreshActionCase("AF-S03", "STATE_TRANSITION", "A product review asks for churn as one account count but does not state whether churn means cancellation requests or completed service termination. Choose one candidate or leave the object open.", "accounts submitting cancellation requests", "accounts whose service termination completed"),
    FreshActionCase("AF-S04", "STATE_TRANSITION", "A process audit asks for transition class Z9, but the state-machine documentation is unavailable. Candidates count transitions P-to-Q and transitions Q-to-R. Determine whether the requested object can be assessed.", "undocumented transitions P-to-Q", "undocumented transitions Q-to-R"),
    FreshActionCase("AF-N01", "NORMALIZATION_BASE", "A factory report asks for electricity used per finished unit. Candidates are kilowatt-hours divided by finished units and kilowatt-hours divided by machine operating hours. Choose the requested measure.", "kilowatt-hours divided by finished units", "kilowatt-hours divided by machine operating hours"),
    FreshActionCase("AF-N02", "NORMALIZATION_BASE", "A fleet dashboard asks for incidents per 1,000 device-days. Candidates divide incidents by active device-days and divide incidents by installed devices at period end. Choose the requested measure.", "incidents divided by active device-days", "incidents divided by installed devices at period end"),
    FreshActionCase("AF-N03", "NORMALIZATION_BASE", "An executive asks for support load normalized for scale but does not identify whether scale means customers or staffed hours. Candidates are tickets per active customer and tickets per staffed support hour. Choose one or leave the object open.", "tickets per active customer", "tickets per staffed support hour"),
    FreshActionCase("AF-N04", "NORMALIZATION_BASE", "A benchmark requests normalized score K, but its denominator definition is missing. Candidates divide the numerator by eligible sites or by reporting sites. Determine whether selection is possible.", "numerator divided by eligible sites", "numerator divided by reporting sites"),
    FreshActionCase("AF-R01", "RISK_POPULATION", "A clinical dashboard asks for mortality among admitted patients. Candidates use deaths divided by admitted patients and deaths divided by all site visitors. Choose the requested measure.", "deaths divided by admitted patients", "deaths divided by all site visitors"),
    FreshActionCase("AF-R02", "RISK_POPULATION", "A safety report asks for adverse-event rate among treated participants. Candidates divide adverse-event participants by treated participants and divide adverse-event reports by all enrolled participants. Choose the requested measure.", "participants with an adverse event divided by treated participants", "adverse-event reports divided by all enrolled participants"),
    FreshActionCase("AF-R03", "RISK_POPULATION", "A policy note asks for default risk but supplies no horizon, event definition, or eligible population. Candidates are defaults among originated loans and delinquent accounts among currently open accounts. Choose one or leave the object open.", "defaults divided by originated loans", "delinquent open accounts divided by open accounts"),
    FreshActionCase("AF-R04", "RISK_POPULATION", "A registry requests risk set D3, but the eligibility specification is unavailable. Candidates are all registered subjects and subjects passing filter F. Determine whether the population can be selected.", "all registered subjects", "subjects passing undocumented filter F"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])


def build_fresh_action_holdout():
    _validate_cases()
    ordered = sorted(CASES, key=lambda case: hash_payload([FRESH_CORPUS_VERSION, case.case_id]))
    items, bindings = [], {}
    for case in ordered:
        conflict_id = "action-fresh-" + hash_payload([FRESH_CORPUS_VERSION, CASE_COMMITMENT, case.case_id])[:18]
        item = {"conflict_id": conflict_id, "public_prompt": case.public_prompt, "candidate_a": case.candidate_a, "candidate_b": case.candidate_b}
        items.append(item)
        bindings[conflict_id] = {"case_id": case.case_id, "object_family": case.object_family, "public_item_hash": hash_payload(item)}
    surface_commitment = {"surface_version": FRESH_CORPUS_VERSION, "items": items, "semantic_labels_exposed": False, "candidate_outputs_exposed": False}
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    commitment = {
        "artifact_version": FRESH_CORPUS_VERSION,
        "corpus_id": FRESH_CORPUS_ID,
        "case_commitment": CASE_COMMITMENT,
        "case_count": len(CASES),
        "family_counts": {family: sum(case.object_family == family for case in CASES) for family in sorted({case.object_family for case in CASES})},
        "public_surface": surface,
        "private_provenance": {"bindings": bindings, "semantic_labels_present": False, "construction_truth_present": False},
        "reference_state": "UNLABELED_FROZEN_BEFORE_CANDIDATE_RUN",
        "blind_candidate_run_allowed": True,
        "reference_revision_allowed_after_candidate_run": False,
        "real_world_ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "evidence_refs": [f"corpus://{FRESH_CORPUS_ID}"],
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_fresh_action_holdout(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_fresh_action_holdout():
        raise ValueError("fresh_action_holdout_invalid")


def _validate_cases():
    if len(CASES) != 24 or len({case.case_id for case in CASES}) != 24 or len({case.public_prompt for case in CASES}) != 24:
        raise ValueError("fresh_action_cases_invalid")
    counts = {family: sum(case.object_family == family for case in CASES) for family in {case.object_family for case in CASES}}
    if len(counts) != 6 or set(counts.values()) != {4}:
        raise ValueError("fresh_action_family_balance_invalid")

