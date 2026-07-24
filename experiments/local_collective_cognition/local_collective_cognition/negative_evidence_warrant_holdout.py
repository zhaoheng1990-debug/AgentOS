"""Fresh v0.5 holdout for executable Provider-backed veto warrants."""

from __future__ import annotations

from .negative_evidence_generalization_holdout import GeneralizationCase, CASES as V02_CASES
from .negative_evidence_holdout import CASES as V01_CASES
from .negative_evidence_precision_holdout import CASES as V03_CASES
from .negative_evidence_structured_holdout import CASES as V04_CASES
from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, RUBRIC
from .unstated_ambiguity_holdout import LEAKAGE_TERMS


CORPUS_VERSION = "negative_evidence_warrant_holdout_v0_5"
CORPUS_ID = "local-negative-evidence-warrant-v0-5"
EVIDENCE_REFS = (f"corpus://{CORPUS_ID}",)
BATCH_SIZE = 2
CATEGORIES = (
    "OPEN_COMMON_DEFAULT", "OPEN_BOUNDARY", "OPEN_GRANULARITY",
    "EXPLICIT_OBJECT", "INVALID_OR_EQUIVALENT", "INVENTED_DEPENDENCE",
)
SURFACE_STYLES = ("CANONICAL", "PROSE", "BULLETS", "QUESTION_FIRST")


CASES = (
    GeneralizationCase("WV01", "streaming-service", "A streaming service logged 420000 song plays from 115000 unique listeners in April. Report reach as one number.", "the song-play count", "the unique-listener count", "content consumption events versus distinct people reached", "Should reach mean plays or unique listeners?", "OPEN_COMMON_DEFAULT", "CANONICAL"),
    GeneralizationCase("WV02", "museum", "A museum recorded 78000 admissions made by 46000 distinct visitors last year. Give museum participation as one integer.", "the admission-event count", "the distinct-visitor count", "entries through the doors versus people participating", "Should participation mean admissions or distinct visitors?", "OPEN_COMMON_DEFAULT", "PROSE"),
    GeneralizationCase("WV03", "help-desk", "A help desk opened 41000 tickets and resolved 37000 tickets this quarter. Return service activity as one integer.", "the opened-ticket count", "the resolved-ticket count", "incoming demand versus completed service work", "Should service activity mean tickets opened or resolved?", "OPEN_COMMON_DEFAULT", "BULLETS"),
    GeneralizationCase("WV04", "rail-terminal", "A rail terminal received 3200 trains and dispatched 2900 trains during June. What single number should represent terminal traffic?", "the arriving-train count", "the departing-train count", "inbound movements versus outbound movements", "Should traffic mean arriving or departing trains?", "OPEN_COMMON_DEFAULT", "QUESTION_FIRST"),
    GeneralizationCase("WV05", "university", "A university spent 60 million dollars on teaching and 20 million dollars on research. Report academic spending as one number.", "teaching expenditure only", "teaching plus research expenditure", "instructional boundary versus combined academic mission", "Should academic spending include research expenditure?", "OPEN_BOUNDARY", "PROSE"),
    GeneralizationCase("WV06", "warehouse", "A warehouse holds 8000 company-owned units and 2000 consigned units for suppliers. What single integer should be reported as stock?", "company-owned inventory only", "owned plus consigned inventory", "ownership boundary versus all physically held goods", "Should stock include consigned units?", "OPEN_BOUNDARY", "QUESTION_FIRST"),
    GeneralizationCase("WV07", "transit-agency", "A transit agency operates 600 buses and keeps 80 additional buses in reserve. Report fleet size as one integer.", "buses in active operation", "active plus reserve buses", "operating fleet versus total controlled fleet", "Should fleet size include reserve buses?", "OPEN_BOUNDARY", "CANONICAL"),
    GeneralizationCase("WV08", "software-service", "A software service has 12000 paying accounts and 3000 free accounts. Return customer base as one number.", "paying accounts only", "paying plus free accounts", "commercial customers versus all registered accounts", "Should customer base include free accounts?", "OPEN_BOUNDARY", "BULLETS"),
    GeneralizationCase("WV09", "brewery", "A brewery completed 240 batches that produced 1.4 million bottles. Report production output as one integer.", "the batch count", "the bottle count", "production runs versus finished units", "Should output mean batches or bottles?", "OPEN_GRANULARITY", "BULLETS"),
    GeneralizationCase("WV10", "library-network", "A library network recorded 310000 loans made by 82000 borrowers. Give library use as one number.", "the loan-transaction count", "the distinct-borrower count", "usage events versus participating users", "Should library use mean loans or borrowers?", "OPEN_GRANULARITY", "PROSE"),
    GeneralizationCase("WV11", "cloud-cluster", "A cloud cluster contains 900 servers equipped with 5400 accelerators. What single integer should represent compute inventory?", "the server count", "the accelerator count", "host machines versus computing devices", "Should compute inventory mean servers or accelerators?", "OPEN_GRANULARITY", "QUESTION_FIRST"),
    GeneralizationCase("WV12", "parcel-carrier", "A parcel carrier sorted 65000 transport bags containing 1.9 million parcels. Report sorting volume as one integer.", "the transport-bag count", "the individual-parcel count", "grouped handling units versus enclosed packages", "Should sorting volume mean bags or parcels?", "OPEN_GRANULARITY", "CANONICAL"),
    GeneralizationCase("WV13", "solar-farm", "A solar farm generated 36 megawatt-hours and used 4 megawatt-hours onsite. Report exported energy in megawatt-hours.", "total generated energy", "generated energy minus onsite use", "gross generation versus explicitly requested export", "Should exported energy mean gross generation or net export?", "EXPLICIT_OBJECT", "CANONICAL"),
    GeneralizationCase("WV14", "online-store", "An online store had 250000 visits and 50000 purchases. Give the purchase conversion rate as a percentage.", "the purchase count", "purchases divided by visits", "absolute transactions versus the requested conversion proportion", "Should conversion rate mean purchases or purchase percentage?", "EXPLICIT_OBJECT", "QUESTION_FIRST"),
    GeneralizationCase("WV15", "hospital", "A hospital scheduled 10000 appointments and completed 7400 of them in the second quarter. Report second-quarter completed appointments as one integer.", "all scheduled appointments", "appointments completed in the second quarter", "scheduled demand versus the named completion status and window", "Should completed appointments include every scheduled appointment?", "EXPLICIT_OBJECT", "PROSE"),
    GeneralizationCase("WV16", "bond-issuer", "A bond has 100 million dollars in principal and pays 6 million dollars in annual interest. Return the annual interest payment in dollars.", "the principal amount", "the annual interest amount", "capital outstanding versus the requested cash payment", "Should annual interest payment mean principal or interest paid?", "EXPLICIT_OBJECT", "BULLETS"),
    GeneralizationCase("WV17", "water-plant", "A water plant runs 40 pumps and processed 1.8 million cubic metres this month. Report water volume in cubic metres.", "the pump count", "the processed-water volume", "equipment inventory versus the requested physical volume", "Should water volume mean pumps or cubic metres processed?", "INVALID_OR_EQUIVALENT", "BULLETS"),
    GeneralizationCase("WV18", "publisher", "A publisher released 120 titles and printed 2 million copies. Give copies printed as one integer.", "the title count", "the printed-copy count", "distinct works versus the explicitly requested unit count", "Should copies printed mean titles or physical copies?", "INVALID_OR_EQUIVALENT", "CANONICAL"),
    GeneralizationCase("WV19", "airport", "An airport handled 350000 passengers in May. Return the May passenger count as one integer.", "the number of May passengers", "the May passenger total", "two equivalent descriptions of one count", "Should passenger count mean passengers or the passenger total?", "INVALID_OR_EQUIVALENT", "PROSE"),
    GeneralizationCase("WV20", "repair-centre", "A repair centre completed 1200 repairs and received 90 returns. What is the return count as one integer?", "the number of returned items", "returns divided by completed repairs", "absolute return events versus a rate not requested", "Should return count mean returns or return percentage?", "INVALID_OR_EQUIVALENT", "QUESTION_FIRST"),
    GeneralizationCase("WV21", "medical-clinic", "A clinic recorded 700 visits during one week. Report patient load as one number.", "the observed visit count", "a patient count after removing assumed repeat visits", "recorded service events versus an undocumented deduplication", "Should patient load remove assumed repeat visits?", "INVENTED_DEPENDENCE", "QUESTION_FIRST"),
    GeneralizationCase("WV22", "grain-farm", "A farm harvested 3000 tonnes from 600 hectares. Report crop yield as one number.", "the observed tonnes per hectare", "yield after an assumed moisture correction", "recorded production intensity versus an undocumented adjustment", "Should crop yield apply the assumed moisture correction?", "INVENTED_DEPENDENCE", "BULLETS"),
    GeneralizationCase("WV23", "charity", "A charity received 2 million dollars in donations. Give donation income in dollars.", "the recorded donation total", "donations after subtracting assumed processing fees", "stated receipts versus an undocumented fee deduction", "Should donation income subtract assumed processing fees?", "INVENTED_DEPENDENCE", "PROSE"),
    GeneralizationCase("WV24", "sensor-network", "A sensor network reported 99.2 percent uptime over 30 days. Report uptime as one percentage.", "the reported 30-day uptime", "uptime after excluding an assumed maintenance interval", "reported availability versus an undocumented exclusion", "Should uptime exclude the assumed maintenance interval?", "INVENTED_DEPENDENCE", "CANONICAL"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])
SPEC_COMMITMENT = {
    "corpus_version": CORPUS_VERSION,
    "corpus_id": CORPUS_ID,
    "ontology_object": "execution-worthy negative evidence for Runtime-owned veto",
    "observable_proxy": "equal-cost naive and warranted veto decisions against a later model-panel reference",
    "case_count": 24,
    "batch_size": BATCH_SIZE,
    "criterion_count": len(JUDGE_CRITERIA),
    "case_commitment": CASE_COMMITMENT,
    "rubric": RUBRIC,
    "category_counts": {category: sum(case.construction_category == category for case in CASES) for category in CATEGORIES},
    "surface_style_counts": {style: sum(case.surface_style == style for case in CASES) for style in SURFACE_STYLES},
    "predecessor_diagnostics_used_for_architecture": True,
    "predecessor_prompts_or_labels_exposed_to_candidates": False,
    "current_reference_labels_available_to_candidates": False,
    "construction_categories_are_ground_truth": False,
    "panel_reference_is_candidate_not_ground_truth": True,
    "selection_authority": False,
    "retention_authority": False,
    "production_authority": False,
}
CORPUS_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def build_warrant_corpus_artifact():
    validate_warrant_corpus_spec()
    source_hash = hash_payload({"corpus_spec_hash": CORPUS_SPEC["spec_hash"], "case_commitment": CASE_COMMITMENT})
    bindings, candidates = {}, []
    for case in CASES:
        blind_id = "warrant-" + hash_payload([CORPUS_VERSION, source_hash, case.item_id])[:18]
        bindings[blind_id] = {
            "item_id": case.item_id,
            "domain": case.domain,
            "construction_category": case.construction_category,
            "surface_style": case.surface_style,
            "case_commitment": case.commitment(),
        }
        candidates.append({"blind_candidate_id": blind_id, "public_prompt": case.public_prompt, "contrastive_packet": case.packet()})
    batches = [
        {"batch_id": f"negative-warrant-batch-{offset // BATCH_SIZE + 1:02d}", "public_candidates": candidates[offset:offset + BATCH_SIZE]}
        for offset in range(0, len(candidates), BATCH_SIZE)
    ]
    surface_commitment = {
        "surface_version": "negative_evidence_warrant_surface_v0_5",
        "source_artifact_hash": source_hash,
        "batches": batches,
        "bindings": bindings,
        "source_identity_exposed": False,
        "construction_categories_exposed": False,
        "predecessor_labels_exposed": False,
    }
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    report_commitment = {
        "report_version": "negative_evidence_warrant_private_report_v0_5",
        "corpus_spec_hash": CORPUS_SPEC["spec_hash"],
        "blind_surface_hash": surface["surface_hash"],
        "trials": [
            {"blind_candidate_id": key, "item_id": value["item_id"], "construction_category": value["construction_category"], "surface_style": value["surface_style"], "construction_expectation_is_ground_truth": False}
            for key, value in sorted(bindings.items())
        ],
        "reference_state": "AWAITING_GPT_GEMINI_ANNOTATIONS",
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
    }
    report = {**report_commitment, "report_hash": hash_payload(report_commitment)}
    commitment = {
        "artifact_version": "negative_evidence_warrant_source_v0_5",
        "corpus_spec": CORPUS_SPEC,
        "blind_surface": surface,
        "report": report,
        "evidence_refs": list(EVIDENCE_REFS),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_warrant_corpus_artifact(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("negative_warrant_corpus_hash_invalid")
    if artifact != build_warrant_corpus_artifact():
        raise ValueError("negative_warrant_corpus_semantics_invalid")


def validate_warrant_corpus_spec(*, cases=CASES, spec=CORPUS_SPEC):
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
        raise ValueError("negative_warrant_corpus_surface_invalid")
    prior_prompts = {case.public_prompt for case in (*V01_CASES, *V02_CASES, *V03_CASES, *V04_CASES)}
    if {case.public_prompt for case in cases} & prior_prompts:
        raise ValueError("negative_warrant_predecessor_reuse_invalid")
