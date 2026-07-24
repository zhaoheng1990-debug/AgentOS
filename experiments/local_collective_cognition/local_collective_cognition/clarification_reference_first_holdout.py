"""Fresh unlabeled semantic-object holdout for reference-first coordination v0.15."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


CORPUS_VERSION = "clarification_reference_first_holdout_v0_15"
CORPUS_ID = "local-clarification-reference-first-v0-15"
BATCH_SIZE = 4


@dataclass(frozen=True)
class ReferenceFirstCase:
    case_id: str
    object_family: str
    public_prompt: str
    candidate_a: str
    candidate_b: str

    def commitment(self):
        return asdict(self)


CASES = (
    ReferenceFirstCase("RF-T01", "TEMPORAL_SCOPE", "A product dashboard asks for monthly active accounts for July. The source table contains accounts with at least one July login and all accounts registered by July 31. Choose the requested measure.", "accounts with at least one July login", "all accounts registered by July 31"),
    ReferenceFirstCase("RF-T02", "TEMPORAL_SCOPE", "An operations review asks for cumulative installations through the end of Q2. The ledger separately reports installations made during Q2 and installations made since launch through Q2. Choose the requested measure.", "installations made during Q2", "installations since launch through Q2"),
    ReferenceFirstCase("RF-T03", "TEMPORAL_SCOPE", "A service desk report asks for the current unresolved backlog at Friday midnight. Available measures are tickets still unresolved at that snapshot and tickets resolved during the preceding week. Choose the requested measure.", "tickets unresolved at Friday midnight", "tickets resolved during the week"),
    ReferenceFirstCase("RF-T04", "TEMPORAL_SCOPE", "A quarterly brief asks for service demand. The data offers requests received during the quarter and the cumulative number of client organizations ever registered. No further definition is supplied. Choose one measure or leave the object open.", "requests received during the quarter", "all client organizations ever registered"),
    ReferenceFirstCase("RF-G01", "GROSS_NET", "A finance note asks for net collected revenue after refunds. The ledger provides customer charges before refunds and customer charges minus completed refunds. Choose the requested measure.", "customer charges before refunds", "customer charges minus completed refunds"),
    ReferenceFirstCase("RF-G02", "GROSS_NET", "A commerce report requests gross merchandise value before cancellations. Available measures are submitted order value before cancellations and settled paid value after cancellations. Choose the requested measure.", "submitted order value before cancellations", "settled paid value after cancellations"),
    ReferenceFirstCase("RF-G03", "GROSS_NET", "A board slide asks for sales performance as one monetary measure. The system offers booked contract value and cash collected, but the slide gives no accounting or operating convention. Choose one measure or leave the object open.", "booked contract value", "cash collected"),
    ReferenceFirstCase("RF-G04", "GROSS_NET", "A report asks for recognized revenue under the applicable accounting policy, but the policy and recognition conditions are not provided. Candidate measures are invoiced amount and amount earned after performance obligations. Determine whether the requested object can be selected.", "invoiced amount", "amount earned after performance obligations"),
    ReferenceFirstCase("RF-R01", "RATE_DENOMINATOR", "An experiment report asks for purchase conversion rate per session. The warehouse offers purchases divided by sessions and distinct purchasers divided by distinct visitors. Choose the requested measure.", "purchases divided by sessions", "distinct purchasers divided by distinct visitors"),
    ReferenceFirstCase("RF-R02", "RATE_DENOMINATOR", "A retention dashboard asks for customer retention rate, but no cohort, starting population, or time window is supplied. Candidates use retained starting customers divided by starting customers, or current active customers divided by all registered customers. Determine whether selection is possible.", "retained starting customers divided by starting customers", "current active customers divided by all registered customers"),
    ReferenceFirstCase("RF-R03", "RATE_DENOMINATOR", "A quality report requests the defective-unit rate among inspected units. Available measures are defective units divided by inspected units and recorded defect observations divided by inspection events. Choose the requested measure.", "defective units divided by inspected units", "defect observations divided by inspection events"),
    ReferenceFirstCase("RF-R04", "RATE_DENOMINATOR", "An executive asks for utilization without naming the resource or population. Candidates are used capacity-hours divided by available capacity-hours and active users divided by licensed seats. Determine whether the requested measure can be selected.", "used capacity-hours divided by available capacity-hours", "active users divided by licensed seats"),
    ReferenceFirstCase("RF-E01", "ENTITY_EVENT", "A messaging report asks for messages delivered. The delivery log contains successful delivery events and distinct recipients with at least one successful delivery. Choose the requested measure.", "successful delivery-event count", "distinct recipient count"),
    ReferenceFirstCase("RF-E02", "ENTITY_EVENT", "A campaign report asks how many people were reached. Available measures are total impression events and distinct people receiving at least one impression. Choose the requested measure.", "impression-event count", "distinct person count"),
    ReferenceFirstCase("RF-E03", "ENTITY_EVENT", "A product brief asks for engagement as one number. The system offers engagement-action events and distinct accounts performing an engagement action. No reporting convention is stated. Choose one measure or leave the object open.", "engagement-action event count", "distinct engaged-account count"),
    ReferenceFirstCase("RF-E04", "ENTITY_EVENT", "A case-management report asks for completed-case throughput during May. Available measures are cases completed during May and distinct clients associated with those cases. Choose the requested measure.", "cases completed during May", "distinct client count"),
    ReferenceFirstCase("RF-S01", "STOCK_FLOW", "A warehouse report asks for open inventory at midnight. The system provides items on hand at midnight and items shipped during that calendar day. Choose the requested measure.", "items on hand at midnight", "items shipped during the day"),
    ReferenceFirstCase("RF-S02", "STOCK_FLOW", "A hospital operations report requests monthly discharge flow. Candidate measures are patient discharges during the month and occupied beds at month end. Choose the requested measure.", "patient discharges during the month", "occupied beds at month end"),
    ReferenceFirstCase("RF-S03", "STOCK_FLOW", "A legal team asks for workload as one number. The case system offers matters opened during the period and unresolved matters at period end, with no stated planning convention. Choose one measure or leave the object open.", "matters opened during the period", "unresolved matters at period end"),
    ReferenceFirstCase("RF-S04", "STOCK_FLOW", "A device report asks for the installed base at quarter end. Available measures are active deployed devices at the quarter-end snapshot and devices shipped during the quarter. Choose the requested measure.", "active deployed devices at quarter end", "devices shipped during the quarter"),
    ReferenceFirstCase("RF-P01", "POPULATION_SCOPE", "A compliance report asks for the eligible account population under a rule requiring identity verification and age of at least 18. Candidates are all registered accounts and verified adult accounts. Choose the requested measure.", "all registered accounts", "verified adult accounts"),
    ReferenceFirstCase("RF-P02", "POPULATION_SCOPE", "A public-service report asks for the number of people served. Available measures are service encounters and distinct recipients receiving at least one service. Choose the requested measure.", "service-encounter count", "distinct recipient count"),
    ReferenceFirstCase("RF-P03", "POPULATION_SCOPE", "A rollout report asks for site coverage as a proportion of eligible sites. Candidate measures are eligible sites reached divided by eligible sites and visit events divided by visited sites. Choose the requested measure.", "eligible sites reached divided by eligible sites", "visit events divided by visited sites"),
    ReferenceFirstCase("RF-P04", "POPULATION_SCOPE", "A feature report asks for organizational adoption. The warehouse offers activated organizations divided by eligible organizations and total feature-use events. No alternative definition is stated. Choose the requested measure.", "activated organizations divided by eligible organizations", "total feature-use events"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])
SPEC_COMMITMENT = {
    "corpus_version": CORPUS_VERSION,
    "corpus_id": CORPUS_ID,
    "ontology_object": "reference-first full-tuple semantic coordination across multiple object families",
    "case_count": len(CASES),
    "batch_size": BATCH_SIZE,
    "case_commitment": CASE_COMMITMENT,
    "object_family_counts": {family: 4 for family in ("TEMPORAL_SCOPE", "GROSS_NET", "RATE_DENOMINATOR", "ENTITY_EVENT", "STOCK_FLOW", "POPULATION_SCOPE")},
    "semantic_labels_present": False,
    "construction_truth_present": False,
    "candidate_run_allowed_before_reference_freeze": False,
    "real_world_ground_truth_claim": False,
    "action_credit_authority": False,
    "selection_authority": False,
    "retention_authority": False,
    "production_authority": False,
}
CORPUS_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def build_reference_first_holdout():
    validate_reference_first_spec()
    source_hash = hash_payload({"spec_hash": CORPUS_SPEC["spec_hash"], "case_commitment": CASE_COMMITMENT})
    ordered = sorted(CASES, key=lambda case: hash_payload([CORPUS_VERSION, case.case_id]))
    bindings, batches = {}, []
    for offset in range(0, len(ordered), BATCH_SIZE):
        conflicts = []
        for case in ordered[offset:offset + BATCH_SIZE]:
            conflict_id = "reference-first-" + hash_payload([CORPUS_VERSION, source_hash, case.case_id])[:18]
            public = {
                "conflict_id": conflict_id,
                "public_prompt": case.public_prompt,
                "candidate_a": case.candidate_a,
                "candidate_b": case.candidate_b,
            }
            bindings[conflict_id] = {
                "case_id": case.case_id,
                "object_family": case.object_family,
                "public_item_hash": hash_payload(public),
            }
            conflicts.append(public)
        batches.append({"batch_id": f"reference-first-batch-{len(batches) + 1:02d}", "conflicts": conflicts})
    surface_commitment = {
        "surface_version": "clarification_reference_first_surface_v0_15",
        "source_hash": source_hash,
        "batches": batches,
        "semantic_labels_exposed": False,
        "candidate_outputs_exposed": False,
    }
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    provenance_commitment = {
        "provenance_version": "clarification_reference_first_provenance_v0_15",
        "surface_hash": surface["surface_hash"],
        "bindings": bindings,
        "semantic_labels_present": False,
        "construction_truth_present": False,
    }
    provenance = {**provenance_commitment, "provenance_hash": hash_payload(provenance_commitment)}
    commitment = {
        "artifact_version": "clarification_reference_first_source_v0_15",
        "corpus_spec": CORPUS_SPEC,
        "public_surface": surface,
        "private_provenance": provenance,
        "reference_state": "UNLABELED_AWAITING_FULL_TUPLE_PANEL",
        "candidate_run_allowed": False,
        "evidence_refs": [f"corpus://{CORPUS_ID}"],
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_reference_first_holdout(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_reference_first_holdout():
        raise ValueError("reference_first_holdout_invalid")


def validate_reference_first_spec(*, cases=CASES, spec=CORPUS_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    if spec.get("spec_hash") != hash_payload(commitment) or tuple(cases) != CASES or len(cases) != 24:
        raise ValueError("reference_first_spec_invalid")
    observed = {family: sum(case.object_family == family for case in cases) for family in spec["object_family_counts"]}
    if observed != spec["object_family_counts"] or len({case.public_prompt for case in cases}) != len(cases):
        raise ValueError("reference_first_family_balance_invalid")
