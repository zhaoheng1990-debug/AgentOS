"""Fresh unlabeled holdout for axis-specific credibility routing v0.17."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


AXIS_CORPUS_VERSION = "cognitive_action_axis_holdout_v0_17"
AXIS_CORPUS_ID = "local-cognitive-action-axis-v0-17"


@dataclass(frozen=True)
class AxisRoutingCase:
    case_id: str
    object_family: str
    public_prompt: str
    candidate_a: str
    candidate_b: str

    def commitment(self):
        return asdict(self)


CASES = (
    AxisRoutingCase("AR-W01", "TIME_WINDOW", "A finance note asks for customers active on the final day of April. Choose between customers with an active status at April 30 and customers active at any point during April.", "customers active at April 30", "customers active at any time during April"),
    AxisRoutingCase("AR-W02", "TIME_WINDOW", "A service review requests tickets opened in the trailing 30 days ending July 15. Candidates count tickets opened from June 16 through July 15, or tickets still open on July 15.", "tickets still open on July 15", "tickets opened from June 16 through July 15"),
    AxisRoutingCase("AR-W03", "TIME_WINDOW", "A dashboard requests monthly engagement but gives no definition. Candidates are users active at least once in the month and users active on the last day of the month. Choose one or leave the object open.", "users active at least once in the month", "users active on the month's final day"),
    AxisRoutingCase("AR-W04", "TIME_WINDOW", "A legacy extract requests window code TW-8, but the data dictionary is unavailable. Candidates use the previous eight complete weeks or the eight weeks ending today. Determine whether the object can be selected.", "previous eight complete calendar weeks", "eight weeks ending today"),
    AxisRoutingCase("AR-E01", "ELIGIBILITY_SCOPE", "A trial summary asks for response rate among participants who received at least one dose. Candidates use dosed participants or everyone randomized as the denominator.", "all randomized participants", "participants receiving at least one dose"),
    AxisRoutingCase("AR-E02", "ELIGIBILITY_SCOPE", "A school report asks for attendance among enrolled students during the term. Candidates include students enrolled for any part of the term or only students enrolled on census day; no local convention is supplied.", "students enrolled for any part of the term", "students enrolled on census day"),
    AxisRoutingCase("AR-E03", "ELIGIBILITY_SCOPE", "A warranty metric explicitly excludes products outside the coverage period. Candidates count all returned products or only returned products whose warranty was active when the fault occurred.", "all returned products", "returned products covered when the fault occurred"),
    AxisRoutingCase("AR-E04", "ELIGIBILITY_SCOPE", "A registry requests eligibility class EC-4, but the defining rule is missing. Candidates are records passing filter A17 and records passing filter B09. Determine whether either candidate is supported.", "records passing undocumented filter A17", "records passing undocumented filter B09"),
    AxisRoutingCase("AR-S01", "EVENT_VERSUS_STATE", "A staffing report asks how many employees became managers in Q2. Candidates count promotion events into manager roles during Q2 or employees holding manager roles at quarter end.", "employees holding manager roles at Q2 end", "promotion events into manager roles during Q2"),
    AxisRoutingCase("AR-S02", "EVENT_VERSUS_STATE", "A payments review requests subscriptions that failed renewal in May. Candidates count renewal attempts ending in failure during May or subscriptions in a delinquent state on May 31.", "failed renewal attempts during May", "delinquent subscriptions at May 31"),
    AxisRoutingCase("AR-S03", "EVENT_VERSUS_STATE", "An operations memo asks for reopened cases but does not say whether it means reopen transitions or cases currently in reopened status. Choose one candidate or leave the object open.", "transitions from closed to reopened", "cases currently marked reopened"),
    AxisRoutingCase("AR-S04", "EVENT_VERSUS_STATE", "A process report requests lifecycle marker LM-3 without the state model. Candidates count entry into review or residence in review at period end. Determine whether selection is possible.", "entries into review", "items in review at period end"),
    AxisRoutingCase("AR-D01", "DENOMINATOR", "A logistics score asks for damaged parcels per 10,000 delivered parcels. Candidates divide by parcels shipped or parcels confirmed delivered.", "parcels shipped", "parcels confirmed delivered"),
    AxisRoutingCase("AR-D02", "DENOMINATOR", "A staffing metric asks for incidents per staffed hour. Candidates divide incident count by scheduled labor hours or by hours with staff actually present.", "scheduled labor hours", "hours with staff actually present"),
    AxisRoutingCase("AR-D03", "DENOMINATOR", "A growth review asks for complaints normalized for business scale, without defining scale. Candidates use complaints per paying account or complaints per transaction. Choose one or leave the denominator open.", "paying accounts", "transactions"),
    AxisRoutingCase("AR-D04", "DENOMINATOR", "A benchmark requests rate denominator DQ-6, but its specification is absent. Candidates use eligible sessions or successfully logged sessions. Determine whether either denominator is justified.", "eligible sessions", "successfully logged sessions"),
    AxisRoutingCase("AR-A01", "ATTRIBUTION_RULE", "A sales report asks for first-touch-attributed bookings. Candidates assign a booking to the earliest recorded campaign touch or to the final touch before booking.", "final campaign touch before booking", "earliest recorded campaign touch"),
    AxisRoutingCase("AR-A02", "ATTRIBUTION_RULE", "A partnership review asks for partner-assisted deals but does not define assistance. Candidates include any deal with a partner meeting or only deals where the partner supplied the registered lead.", "deals with any partner meeting", "deals whose registered lead came from a partner"),
    AxisRoutingCase("AR-A03", "ATTRIBUTION_RULE", "A support analysis defines self-service deflection as a help-center visit followed by no support contact within 48 hours. Candidates count those visits or all visits without a same-session support contact.", "help-center visits with no support contact within 48 hours", "help-center visits with no same-session support contact"),
    AxisRoutingCase("AR-A04", "ATTRIBUTION_RULE", "A historical report requests attribution rule AT-11, but the glossary is unavailable. Candidates are conversion credit under rule R3 and credit under rule R8. Determine whether the requested object can be resolved.", "conversion credit under undocumented rule R3", "conversion credit under undocumented rule R8"),
    AxisRoutingCase("AR-G01", "AGGREGATION", "A latency objective explicitly requests the 99th percentile. Candidates are mean request latency and p99 request latency.", "mean request latency", "99th-percentile request latency"),
    AxisRoutingCase("AR-G02", "AGGREGATION", "A compensation report asks for mean base salary, defined as total base salary divided by employee count. Candidates are that arithmetic mean and the median employee salary.", "median employee salary", "total base salary divided by employee count"),
    AxisRoutingCase("AR-G03", "AGGREGATION", "A quality memo asks for a typical defect count but provides no convention for a strongly skewed distribution. Candidates are arithmetic mean defects and median defects. Choose one or leave the statistic open.", "arithmetic mean defect count", "median defect count"),
    AxisRoutingCase("AR-G04", "AGGREGATION", "A research table requests summary statistic ST-5 without its codebook. Candidates are a trimmed mean and an interquartile midpoint. Determine whether either statistic can be selected.", "trimmed mean", "interquartile midpoint"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])


def build_axis_routing_holdout():
    _validate_cases()
    ordered = sorted(CASES, key=lambda case: hash_payload([AXIS_CORPUS_VERSION, case.case_id]))
    items, bindings = [], {}
    for case in ordered:
        conflict_id = "axis-fresh-" + hash_payload([AXIS_CORPUS_VERSION, CASE_COMMITMENT, case.case_id])[:18]
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
        "surface_version": AXIS_CORPUS_VERSION,
        "items": items,
        "semantic_labels_exposed": False,
        "candidate_outputs_exposed": False,
    }
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    commitment = {
        "artifact_version": AXIS_CORPUS_VERSION,
        "corpus_id": AXIS_CORPUS_ID,
        "case_commitment": CASE_COMMITMENT,
        "case_count": len(CASES),
        "family_counts": {
            family: sum(case.object_family == family for case in CASES)
            for family in sorted({case.object_family for case in CASES})
        },
        "public_surface": surface,
        "private_provenance": {
            "bindings": bindings,
            "semantic_labels_present": False,
            "construction_truth_present": False,
        },
        "reference_state": "UNLABELED_FROZEN_BEFORE_CANDIDATE_RUN",
        "calibration_cases_reused": False,
        "reference_revision_allowed_after_candidate_run": False,
        "real_world_ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "evidence_refs": [f"corpus://{AXIS_CORPUS_ID}"],
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_axis_routing_holdout(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_axis_routing_holdout():
        raise ValueError("axis_routing_holdout_invalid")


def _validate_cases():
    if len(CASES) != 24 or len({case.case_id for case in CASES}) != 24 or len({case.public_prompt for case in CASES}) != 24:
        raise ValueError("axis_routing_cases_invalid")
    counts = {
        family: sum(case.object_family == family for case in CASES)
        for family in {case.object_family for case in CASES}
    }
    if len(counts) != 6 or set(counts.values()) != {4}:
        raise ValueError("axis_routing_family_balance_invalid")

