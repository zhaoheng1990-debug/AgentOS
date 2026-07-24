"""Fresh v0.4 holdout for naive replication and structured defer."""

from __future__ import annotations

from .negative_evidence_generalization_holdout import GeneralizationCase, CASES as V02_CASES
from .negative_evidence_holdout import CASES as V01_CASES
from .negative_evidence_precision_holdout import CASES as V03_CASES
from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, RUBRIC
from .unstated_ambiguity_holdout import LEAKAGE_TERMS


CORPUS_VERSION = "negative_evidence_structured_holdout_v0_4"
CORPUS_ID = "local-negative-evidence-structured-v0-4"
EVIDENCE_REFS = (f"corpus://{CORPUS_ID}",)
BATCH_SIZE = 2
CATEGORIES = (
    "OPEN_COMMON_DEFAULT", "OPEN_BOUNDARY", "OPEN_GRANULARITY",
    "EXPLICIT_OBJECT", "INVALID_OR_EQUIVALENT", "INVENTED_DEPENDENCE",
)
SURFACE_STYLES = ("CANONICAL", "PROSE", "BULLETS", "QUESTION_FIRST")


CASES = (
    GeneralizationCase("SV01", "concert-venue", "A concert venue sold 15000 tickets and admitted 12000 people last month. Report audience as one number.", "the ticket-sale count", "the admitted-person count", "commercial demand versus actual attendance", "Should audience mean tickets sold or people admitted?", "OPEN_COMMON_DEFAULT", "CANONICAL"),
    GeneralizationCase("SV02", "website", "A website recorded 100000 page views across 20000 browsing sessions yesterday. Report engagement as one number.", "the page-view count", "the session count", "content exposures versus browsing episodes", "Should engagement mean page views or sessions?", "OPEN_COMMON_DEFAULT", "PROSE"),
    GeneralizationCase("SV03", "distribution-centre", "A distribution centre received 900 inbound loads and dispatched 700 outbound loads this week. Report centre activity as one integer.", "the inbound-load count", "the outbound-load count", "receiving events versus dispatch events", "Should activity mean inbound or outbound loads?", "OPEN_COMMON_DEFAULT", "BULLETS"),
    GeneralizationCase("SV04", "research-institute", "A research institute received 5000 academic citations and 100 media mentions this year. Report research impact as one integer.", "the academic-citation count", "the media-mention count", "scholarly uptake versus public visibility", "Should research impact mean citations or media mentions?", "OPEN_COMMON_DEFAULT", "QUESTION_FIRST"),
    GeneralizationCase("SV05", "manufacturer", "A manufacturer reports 400 tonnes of direct emissions and 900 tonnes from purchased materials. Report its carbon footprint as one number.", "direct operational emissions", "direct plus purchased-material emissions", "operational boundary versus supply-chain boundary", "Should the footprint include purchased materials?", "OPEN_BOUNDARY", "PROSE"),
    GeneralizationCase("SV06", "health-network", "A health network spent 8 million dollars on inpatient care and 3 million dollars on outpatient care. Report healthcare cost as one number.", "inpatient expenditure only", "inpatient plus outpatient expenditure", "one care setting versus combined care cost", "Should healthcare cost include outpatient as well as inpatient care?", "OPEN_BOUNDARY", "QUESTION_FIRST"),
    GeneralizationCase("SV07", "membership-club", "A club has 8000 paying members and 2000 trial members. Report membership as one integer.", "paying members only", "paying plus trial members", "contracted membership versus extended participation", "Should membership include trial members?", "OPEN_BOUNDARY", "CANONICAL"),
    GeneralizationCase("SV08", "construction-project", "A project has a 1 million dollar capital budget and 200000 dollars for operating expenses. Report project budget as one number.", "capital allocation only", "capital plus operating allocation", "investment boundary versus total funded expenditure", "Should project budget include operating expenses?", "OPEN_BOUNDARY", "BULLETS"),
    GeneralizationCase("SV09", "school-district", "A school district has 600 students distributed across 24 classes. Report class size as one number.", "the total student count", "the average students per class", "system population versus per-class average", "Should class size mean total students or average students per class?", "OPEN_GRANULARITY", "BULLETS"),
    GeneralizationCase("SV10", "call-centre", "A call centre handled 600 calls requiring 1800 agent-minutes yesterday. Report handling volume as one number.", "the call count", "the agent-minute total", "interaction count versus labour time", "Should handling volume mean calls or agent-minutes?", "OPEN_GRANULARITY", "PROSE"),
    GeneralizationCase("SV11", "logistics-hub", "A logistics hub processed 500 pallets containing 10000 parcels today. Report throughput as one integer.", "the pallet count", "the parcel count", "grouped handling units versus individual packages", "Should throughput mean pallets or parcels?", "OPEN_GRANULARITY", "QUESTION_FIRST"),
    GeneralizationCase("SV12", "cinema-chain", "A cinema chain sold 20000 tickets across 500 screenings this weekend. Report cinema activity as one integer.", "the ticket count", "the screening count", "audience transactions versus presentation events", "Should activity mean tickets or screenings?", "OPEN_GRANULARITY", "CANONICAL"),
    GeneralizationCase("SV13", "battery-system", "A battery stores 45 kilowatt-hours out of 60 kilowatt-hours capacity. Report charge level as a percentage.", "the stored kilowatt-hours", "stored energy divided by capacity", "absolute energy versus normalized charge level", "Should charge level mean kilowatt-hours or percentage of capacity?", "EXPLICIT_OBJECT", "CANONICAL"),
    GeneralizationCase("SV14", "employer", "A company employed 1000 people and 100 left during the year. Report employee turnover rate as a percentage.", "the departure count", "departures divided by employee count", "absolute exits versus turnover proportion", "Should turnover rate mean departures or a percentage?", "EXPLICIT_OBJECT", "QUESTION_FIRST"),
    GeneralizationCase("SV15", "device-platform", "A platform has 300000 registered devices, of which 80000 were active in June. Report June active devices as one integer.", "all registered devices", "devices active in June", "registered inventory versus explicitly requested activity window", "Should June active devices mean all registered devices or those active in June?", "EXPLICIT_OBJECT", "PROSE"),
    GeneralizationCase("SV16", "network-link", "A network link transferred 900 gigabytes with average latency of 20 milliseconds. Report data-transfer volume in gigabytes.", "the latency measurement", "the transferred data volume", "response delay versus byte volume", "Should transfer volume mean milliseconds or gigabytes?", "EXPLICIT_OBJECT", "BULLETS"),
    GeneralizationCase("SV17", "weather-station", "A weather station used 12 sensors and measured an average temperature of 18 degrees Celsius. Report average temperature in degrees Celsius.", "the sensor count", "the average temperature", "instrument inventory versus measured temperature", "Should average temperature mean sensors or degrees Celsius?", "INVALID_OR_EQUIVALENT", "BULLETS"),
    GeneralizationCase("SV18", "software-company", "A software company earned 5 million dollars in revenue and 1 million dollars in net profit. Report net profit in dollars.", "the revenue total", "the net-profit total", "top-line income versus explicitly requested residual profit", "Should net profit mean revenue or profit after costs?", "INVALID_OR_EQUIVALENT", "CANONICAL"),
    GeneralizationCase("SV19", "vehicle-registry", "A registry recorded 40000 registered vehicles this year. Report the registered-vehicle count as one integer.", "the number of registered vehicles", "the registered-vehicle total", "two equivalent descriptions of the same count", "Should registered-vehicle count mean vehicles or the vehicle total?", "INVALID_OR_EQUIVALENT", "PROSE"),
    GeneralizationCase("SV20", "quality-line", "A production line inspected 5000 units and found 80 defects. Report defect count as one integer.", "the number of defects", "defects divided by inspected units", "absolute defect events versus defect rate", "Should defect count mean defects or defect percentage?", "INVALID_OR_EQUIVALENT", "QUESTION_FIRST"),
    GeneralizationCase("SV21", "office-building", "An office building used 600 megawatt-hours and has 12000 square metres of floor area. Report energy efficiency as one number.", "the observed energy per square metre", "efficiency after applying an assumed climate baseline", "recorded intensity versus an undocumented normalization", "Should efficiency apply the assumed climate baseline?", "INVENTED_DEPENDENCE", "QUESTION_FIRST"),
    GeneralizationCase("SV22", "fruit-farm", "A farm harvested 900 tonnes from 150 hectares. Report yield as one number.", "the observed tonnes per hectare", "yield after excluding an assumed spoiled quantity", "recorded harvest intensity versus an undocumented exclusion", "Should yield exclude the assumed spoiled crop?", "INVENTED_DEPENDENCE", "BULLETS"),
    GeneralizationCase("SV23", "exporter", "An exporter recorded 2 million euros in sales. Report revenue in euros.", "the recorded euro revenue", "revenue after an assumed currency adjustment", "stated currency total versus an undocumented conversion", "Should revenue include the assumed currency adjustment?", "INVENTED_DEPENDENCE", "PROSE"),
    GeneralizationCase("SV24", "survey", "A survey reports 82 percent satisfaction among all 1000 respondents. Report satisfaction as one number.", "the reported all-respondent percentage", "satisfaction after excluding assumed nonrespondents", "reported sample statistic versus an undocumented exclusion", "Should satisfaction exclude the assumed nonrespondents?", "INVENTED_DEPENDENCE", "CANONICAL"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])
SPEC_COMMITMENT = {
    "corpus_version": CORPUS_VERSION, "corpus_id": CORPUS_ID,
    "ontology_object": "replication of three-role veto and structured semantic defer",
    "observable_proxy": "four frozen arm decisions against a later model-panel reference",
    "case_count": 24, "batch_size": BATCH_SIZE, "criterion_count": len(JUDGE_CRITERIA),
    "case_commitment": CASE_COMMITMENT, "rubric": RUBRIC,
    "category_counts": {category: sum(case.construction_category == category for case in CASES) for category in CATEGORIES},
    "surface_style_counts": {style: sum(case.surface_style == style for case in CASES) for style in SURFACE_STYLES},
    "predecessor_diagnostics_used_for_architecture": True,
    "predecessor_prompts_or_labels_exposed_to_candidates": False,
    "current_reference_labels_available_to_candidates": False,
    "construction_categories_are_ground_truth": False,
    "panel_reference_is_candidate_not_ground_truth": True,
    "selection_authority": False, "retention_authority": False, "production_authority": False,
}
CORPUS_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def build_structured_corpus_artifact():
    validate_structured_corpus_spec()
    source_hash = hash_payload({"corpus_spec_hash": CORPUS_SPEC["spec_hash"], "case_commitment": CASE_COMMITMENT})
    bindings, candidates = {}, []
    for case in CASES:
        blind_id = "structured-" + hash_payload([CORPUS_VERSION, source_hash, case.item_id])[:18]
        bindings[blind_id] = {
            "item_id": case.item_id, "domain": case.domain,
            "construction_category": case.construction_category,
            "surface_style": case.surface_style, "case_commitment": case.commitment(),
        }
        candidates.append({"blind_candidate_id": blind_id, "public_prompt": case.public_prompt, "contrastive_packet": case.packet()})
    batches = [
        {"batch_id": f"negative-structured-batch-{offset // BATCH_SIZE + 1:02d}", "public_candidates": candidates[offset:offset + BATCH_SIZE]}
        for offset in range(0, 24, BATCH_SIZE)
    ]
    surface_commitment = {
        "surface_version": "negative_evidence_structured_surface_v0_4",
        "source_artifact_hash": source_hash, "batches": batches, "bindings": bindings,
        "source_identity_exposed": False, "construction_categories_exposed": False,
        "predecessor_labels_exposed": False,
    }
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    report_commitment = {
        "report_version": "negative_evidence_structured_private_report_v0_4",
        "corpus_spec_hash": CORPUS_SPEC["spec_hash"], "blind_surface_hash": surface["surface_hash"],
        "trials": [
            {"blind_candidate_id": key, "item_id": value["item_id"], "construction_category": value["construction_category"], "surface_style": value["surface_style"], "construction_expectation_is_ground_truth": False}
            for key, value in sorted(bindings.items())
        ],
        "reference_state": "AWAITING_GPT_GEMINI_ANNOTATIONS", "ground_truth_claim": False,
        "selection_authority": False, "retention_authority": False,
    }
    report = {**report_commitment, "report_hash": hash_payload(report_commitment)}
    commitment = {
        "artifact_version": "negative_evidence_structured_source_v0_4",
        "corpus_spec": CORPUS_SPEC, "blind_surface": surface, "report": report,
        "evidence_refs": list(EVIDENCE_REFS),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_structured_corpus_artifact(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("negative_structured_corpus_hash_invalid")
    if artifact != build_structured_corpus_artifact():
        raise ValueError("negative_structured_corpus_semantics_invalid")


def validate_structured_corpus_spec(*, cases=CASES, spec=CORPUS_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    if (
        spec.get("spec_hash") != hash_payload(commitment) or tuple(cases) != CASES
        or len(cases) != 24 or len({case.item_id for case in cases}) != 24
        or any(sum(case.construction_category == category for case in cases) != 4 for category in CATEGORIES)
        or any(sum(case.surface_style == style for case in cases) != 6 for style in SURFACE_STYLES)
        or any(term in case.public_prompt.lower() for case in cases for term in LEAKAGE_TERMS)
    ):
        raise ValueError("negative_structured_corpus_surface_invalid")
    prior_prompts = {case.public_prompt for case in (*V01_CASES, *V02_CASES, *V03_CASES)}
    if {case.public_prompt for case in cases} & prior_prompts:
        raise ValueError("negative_structured_predecessor_reuse_invalid")
