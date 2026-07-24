"""Fresh holdout for precision-confirmed negative-evidence vetoes."""

from __future__ import annotations

from dataclasses import dataclass

from .negative_evidence_generalization_holdout import CASES as V02_CASES
from .negative_evidence_holdout import CASES as V01_CASES
from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, RUBRIC
from .unstated_ambiguity_holdout import LEAKAGE_TERMS


CORPUS_VERSION = "negative_evidence_precision_holdout_v0_3"
CORPUS_ID = "local-negative-evidence-precision-v0-3"
EVIDENCE_REFS = (f"corpus://{CORPUS_ID}",)
BATCH_SIZE = 2
CATEGORIES = (
    "OPEN_COMMON_DEFAULT",
    "OPEN_MULTI_DIMENSIONAL",
    "OPEN_BOUNDARY",
    "EXPLICITLY_FIXED",
    "INVALID_OR_EQUIVALENT_RIVAL",
    "INVENTED_DEPENDENCE",
)
SURFACE_STYLES = ("CANONICAL", "PROSE", "BULLETS", "QUESTION_FIRST")


@dataclass(frozen=True)
class PrecisionCase:
    item_id: str
    domain: str
    public_prompt: str
    rival_a: str
    rival_b: str
    decisive_contrast: str
    discriminating_question: str
    construction_category: str
    surface_style: str

    def packet(self):
        if self.surface_style == "CANONICAL":
            return (
                f"RIVAL_A: {self.rival_a} | RIVAL_B: {self.rival_b} | "
                f"CONTRAST: {self.decisive_contrast} | "
                f"QUESTION: {self.discriminating_question}"
            )
        if self.surface_style == "PROSE":
            return (
                f"One reading is {self.rival_a}. Another reading is {self.rival_b}. "
                f"They differ by {self.decisive_contrast}. Clarify by asking: "
                f"{self.discriminating_question}"
            )
        if self.surface_style == "BULLETS":
            return (
                f"A) {self.rival_a}\nB) {self.rival_b}\n"
                f"Difference: {self.decisive_contrast}\n"
                f"Clarifier: {self.discriminating_question}"
            )
        return (
            f"CLARIFIER: {self.discriminating_question} | "
            f"FIRST READING: {self.rival_a} | SECOND READING: {self.rival_b} | "
            f"DISTINGUISHER: {self.decisive_contrast}"
        )

    def commitment(self):
        return hash_payload({
            "item_id": self.item_id,
            "domain": self.domain,
            "public_prompt": self.public_prompt,
            "contrastive_packet": self.packet(),
            "construction_category": self.construction_category,
            "surface_style": self.surface_style,
        })


CASES = (
    PrecisionCase("PV01", "museum", "A museum recorded 12000 admissions from 9500 unique visitors last month. Report attendance as one number.", "the admission count", "the unique-visitor count", "visits versus distinct people", "Should attendance mean admissions or unique visitors?", "OPEN_COMMON_DEFAULT", "CANONICAL"),
    PrecisionCase("PV02", "mobile-app", "A mobile application logged 80000 sessions from 30000 active users yesterday. Report daily usage as one number.", "the session count", "the active-user count", "interaction episodes versus distinct users", "Should daily usage mean sessions or active users?", "OPEN_COMMON_DEFAULT", "PROSE"),
    PrecisionCase("PV03", "urban-transit", "A transit system carried 150000 passenger journeys made by 90000 individual riders on Monday. Report ridership as one number.", "the passenger-journey count", "the distinct-rider count", "travel events versus people", "Should ridership mean journeys or distinct riders?", "OPEN_COMMON_DEFAULT", "BULLETS"),
    PrecisionCase("PV04", "research-office", "A research office reported 320 journal papers and 45 granted patents this year. Report research output as one integer.", "the publication count", "the granted-patent count", "scholarly dissemination versus protected inventions", "Should research output mean papers or granted patents?", "OPEN_COMMON_DEFAULT", "QUESTION_FIRST"),
    PrecisionCase("PV05", "medical-clinic", "A clinic handled 700 appointments involving 520 patients this week. Report clinic workload as one integer.", "the appointment count", "the patient count", "service encounters versus distinct people", "Should workload mean appointments or patients?", "OPEN_MULTI_DIMENSIONAL", "PROSE"),
    PrecisionCase("PV06", "customer-support", "A support centre closed 400 tickets containing 1100 customer messages yesterday. Report support volume as one integer.", "the closed-ticket count", "the customer-message count", "resolved cases versus communication events", "Should support volume mean tickets or messages?", "OPEN_MULTI_DIMENSIONAL", "QUESTION_FIRST"),
    PrecisionCase("PV07", "public-library", "A library issued 50000 loans to 18000 borrowers last quarter. Report circulation as one number.", "the loan count", "the borrower count", "borrowed items versus participating patrons", "Should circulation mean loans or borrowers?", "OPEN_MULTI_DIMENSIONAL", "CANONICAL"),
    PrecisionCase("PV08", "manufacturing-plant", "A plant operates 10 production lines capable of making 40000 units per day. Report plant capacity as one number.", "the production-line count", "the daily unit throughput", "installed process lines versus output rate", "Should capacity mean lines or units per day?", "OPEN_MULTI_DIMENSIONAL", "BULLETS"),
    PrecisionCase("PV09", "university-campus", "A campus used 8 megalitres of municipal water and 2 megalitres of collected rainwater last month. Report water use as one number.", "municipal water only", "municipal plus collected rainwater", "purchased supply versus total consumed water", "Should water use include collected rainwater?", "OPEN_BOUNDARY", "BULLETS"),
    PrecisionCase("PV10", "technology-company", "A company has 600 employees and 140 long-term contractors. Report workforce size as one integer.", "employees only", "employees plus long-term contractors", "payroll headcount versus extended workforce", "Should workforce size include long-term contractors?", "OPEN_BOUNDARY", "CANONICAL"),
    PrecisionCase("PV11", "food-factory", "A factory consumed 900 megawatt-hours of electricity and 300 megawatt-hours of natural-gas energy this month. Report energy use as one number.", "electricity consumption only", "electricity plus gas energy", "single-carrier versus total operational energy", "Should energy use include natural gas as well as electricity?", "OPEN_BOUNDARY", "QUESTION_FIRST"),
    PrecisionCase("PV12", "subscription-service", "A service has 200000 registered accounts and 85000 accounts active this month. Report customer count as one integer.", "all registered accounts", "monthly active accounts", "registered base versus active customer boundary", "Should customer count mean registered or monthly active accounts?", "OPEN_BOUNDARY", "PROSE"),
    PrecisionCase("PV13", "data-centre", "A data centre runs 2400 servers and consumed 1800 megawatt-hours last month. Report energy consumption in megawatt-hours.", "the server count", "the measured energy consumption", "equipment inventory versus energy quantity", "Should energy consumption mean servers or megawatt-hours?", "EXPLICITLY_FIXED", "QUESTION_FIRST"),
    PrecisionCase("PV14", "hotel", "A hotel has 300 available rooms and 225 were occupied last night. Report occupancy as a percentage.", "the occupied-room count", "the occupied share of available rooms", "absolute rooms versus normalized rate", "Should occupancy be a room count or a percentage?", "EXPLICITLY_FIXED", "PROSE"),
    PrecisionCase("PV15", "freight-train", "A freight train travelled 600 kilometres in 8 hours at an average speed of 75 kilometres per hour. Report average speed in kilometres per hour.", "the route distance", "the stated average speed", "distance travelled versus movement rate", "Should average speed mean kilometres travelled or kilometres per hour?", "EXPLICITLY_FIXED", "BULLETS"),
    PrecisionCase("PV16", "advertising-campaign", "An advertising campaign delivered 2 million impressions and generated 40000 purchases. Report conversion rate as a percentage.", "the impression count", "purchases divided by impressions", "exposure volume versus conversion proportion", "Should conversion rate mean impressions or purchase percentage?", "EXPLICITLY_FIXED", "CANONICAL"),
    PrecisionCase("PV17", "web-service", "A web service handled 50000 requests with a mean response time of 180 milliseconds. Report mean response time in milliseconds.", "the request count", "the mean response time", "traffic volume versus latency", "Should mean response time mean request count or milliseconds?", "INVALID_OR_EQUIVALENT_RIVAL", "CANONICAL"),
    PrecisionCase("PV18", "charity", "A charity received 3 million dollars from 12000 donors. Report total donations in dollars.", "the donor count", "the donated monetary total", "people contributing versus money received", "Should total donations mean donors or dollars received?", "INVALID_OR_EQUIVALENT_RIVAL", "QUESTION_FIRST"),
    PrecisionCase("PV19", "retail-chain", "A retail chain booked 9 million dollars of gross sales before 600000 dollars of refunds. Report gross revenue before refunds.", "gross sales before refunds", "gross revenue before refunds", "two equivalent names for the same stated boundary", "Should gross revenue mean gross sales or revenue before refunds?", "INVALID_OR_EQUIVALENT_RIVAL", "PROSE"),
    PrecisionCase("PV20", "online-community", "An online community has 400000 accounts, including 70000 users active this week. Report weekly active users as one integer.", "all registered accounts", "users active this week", "registered base versus explicitly requested activity window", "Should weekly active users mean all accounts or users active this week?", "INVALID_OR_EQUIVALENT_RIVAL", "BULLETS"),
    PrecisionCase("PV21", "secondary-school", "A school enrolled 800 students and 720 completed the academic year. Report completion rate as one number.", "the observed completion proportion", "completion after excluding an assumed group of transfer students", "recorded completion versus an undocumented exclusion", "Should completion exclude the assumed transfer students?", "INVENTED_DEPENDENCE", "BULLETS"),
    PrecisionCase("PV22", "solar-farm", "A solar farm generated 1200 megawatt-hours last month. Report electricity output as one number.", "the recorded generation", "generation after adding assumed curtailed output", "metered electricity versus an undocumented addition", "Should output include the assumed curtailed electricity?", "INVENTED_DEPENDENCE", "PROSE"),
    PrecisionCase("PV23", "grocery-store", "A grocery store recorded 500000 dollars of sales and 350000 dollars of stated product cost. Report gross margin as one number.", "the margin from the stated sales and product cost", "margin after subtracting an assumed local levy", "disclosed commercial margin versus an undocumented deduction", "Should gross margin subtract the assumed local levy?", "INVENTED_DEPENDENCE", "CANONICAL"),
    PrecisionCase("PV24", "hospital-emergency", "A hospital reports a median waiting time of 42 minutes across all emergency visits last week. Report median waiting time as one number.", "the reported median across all visits", "the median after excluding an assumed priority group", "reported all-visit statistic versus an undocumented exclusion", "Should waiting time exclude the assumed priority patients?", "INVENTED_DEPENDENCE", "QUESTION_FIRST"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])
SPEC_COMMITMENT = {
    "corpus_version": CORPUS_VERSION,
    "corpus_id": CORPUS_ID,
    "ontology_object": "precision of independently confirmed live-ambiguity vetoes",
    "observable_proxy": "four frozen arm decisions against a later model-panel reference",
    "case_count": len(CASES),
    "batch_size": BATCH_SIZE,
    "criterion_count": len(JUDGE_CRITERIA),
    "case_commitment": CASE_COMMITMENT,
    "rubric": RUBRIC,
    "category_counts": {category: sum(case.construction_category == category for case in CASES) for category in CATEGORIES},
    "surface_style_counts": {style: sum(case.surface_style == style for case in CASES) for style in SURFACE_STYLES},
    "predecessor_v0_2_diagnostics_used_for_architecture": True,
    "predecessor_prompts_or_labels_exposed_to_candidates": False,
    "current_reference_labels_available_to_candidates": False,
    "construction_categories_are_ground_truth": False,
    "panel_reference_is_candidate_not_ground_truth": True,
    "selection_authority": False,
    "retention_authority": False,
    "production_authority": False,
}
CORPUS_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def build_precision_corpus_artifact():
    validate_precision_corpus_spec()
    source_hash = hash_payload({"corpus_spec_hash": CORPUS_SPEC["spec_hash"], "case_commitment": CASE_COMMITMENT})
    bindings, candidates = {}, []
    for case in CASES:
        blind_id = "precision-" + hash_payload([CORPUS_VERSION, source_hash, case.item_id])[:18]
        bindings[blind_id] = {
            "item_id": case.item_id,
            "domain": case.domain,
            "construction_category": case.construction_category,
            "surface_style": case.surface_style,
            "case_commitment": case.commitment(),
        }
        candidates.append({"blind_candidate_id": blind_id, "public_prompt": case.public_prompt, "contrastive_packet": case.packet()})
    batches = [
        {"batch_id": f"negative-precision-batch-{offset // BATCH_SIZE + 1:02d}", "public_candidates": candidates[offset:offset + BATCH_SIZE]}
        for offset in range(0, len(candidates), BATCH_SIZE)
    ]
    surface_commitment = {
        "surface_version": "negative_evidence_precision_surface_v0_3",
        "source_artifact_hash": source_hash,
        "batches": batches,
        "bindings": bindings,
        "source_identity_exposed": False,
        "construction_categories_exposed": False,
        "predecessor_labels_exposed": False,
    }
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    report_commitment = {
        "report_version": "negative_evidence_precision_private_report_v0_3",
        "corpus_spec_hash": CORPUS_SPEC["spec_hash"],
        "blind_surface_hash": surface["surface_hash"],
        "trials": [
            {
                "blind_candidate_id": blind_id,
                "item_id": binding["item_id"],
                "construction_category": binding["construction_category"],
                "surface_style": binding["surface_style"],
                "construction_expectation_is_ground_truth": False,
            }
            for blind_id, binding in sorted(bindings.items())
        ],
        "reference_state": "AWAITING_GPT_GEMINI_ANNOTATIONS",
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
    }
    report = {**report_commitment, "report_hash": hash_payload(report_commitment)}
    commitment = {
        "artifact_version": "negative_evidence_precision_source_v0_3",
        "corpus_spec": CORPUS_SPEC,
        "blind_surface": surface,
        "report": report,
        "evidence_refs": list(EVIDENCE_REFS),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_precision_corpus_artifact(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("negative_precision_corpus_hash_invalid")
    if artifact != build_precision_corpus_artifact():
        raise ValueError("negative_precision_corpus_semantics_invalid")


def validate_precision_corpus_spec(*, cases=CASES, spec=CORPUS_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    if (
        spec.get("spec_hash") != hash_payload(commitment)
        or tuple(cases) != CASES
        or len(cases) != 24
        or len({case.item_id for case in cases}) != 24
        or any(sum(case.construction_category == category for case in cases) != 4 for category in CATEGORIES)
        or any(sum(case.surface_style == style for case in cases) != 6 for style in SURFACE_STYLES)
        or any(term in case.public_prompt.lower() for case in cases for term in LEAKAGE_TERMS)
    ):
        raise ValueError("negative_precision_corpus_surface_invalid")
    prior_prompts = {case.public_prompt for case in (*V01_CASES, *V02_CASES)}
    if {case.public_prompt for case in cases} & prior_prompts:
        raise ValueError("negative_precision_predecessor_reuse_invalid")
