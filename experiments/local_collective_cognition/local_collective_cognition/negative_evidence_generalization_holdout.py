"""Distribution-shifted holdout for negative-evidence role generalization."""

from __future__ import annotations

from dataclasses import dataclass

from .ambiguity_coordinator_holdout import CASES as COORDINATOR_CASES
from .ambiguity_hard_null_holdout import CASES as HARD_NULL_CASES
from .negative_evidence_holdout import CASES as NEGATIVE_EVIDENCE_V01_CASES
from .provider_telemetry import hash_payload
from .receipt_quality_calibration_corpus import CASES as RECEIPT_QUALITY_CASES
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, RUBRIC
from .unstated_ambiguity_holdout import CASES as DISCOVERY_CASES, LEAKAGE_TERMS


CORPUS_VERSION = "negative_evidence_generalization_holdout_v0_2"
CORPUS_ID = "local-negative-evidence-generalization-v0-2"
EVIDENCE_REFS = (f"corpus://{CORPUS_ID}",)
BATCH_SIZE = 2
CATEGORIES = (
    "CLEAN_AMBIGUOUS",
    "EXPLICITLY_DETERMINED",
    "INVENTED_DEPENDENCE",
    "MIXED_DEFECT",
    "ADVERSARIAL_CLEAN",
    "BOUNDARY_COMPOSITION",
)
SURFACE_STYLES = ("CANONICAL", "PROSE", "BULLETS", "QUESTION_FIRST")


@dataclass(frozen=True)
class GeneralizationCase:
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
    GeneralizationCase(
        "NG01", "diagnostic-laboratory",
        "A diagnostic laboratory completed 640 assays arranged in 80 processing batches yesterday. Report laboratory throughput as one integer.",
        "the number of assays completed", "the number of processing batches",
        "individual tests versus grouped processing runs",
        "Should throughput refer to assays or processing batches?",
        "CLEAN_AMBIGUOUS", "PROSE",
    ),
    GeneralizationCase(
        "NG02", "news-platform",
        "A news platform recorded 2 million article views from 300000 distinct readers yesterday. Give daily reach as one number.",
        "the article-view count", "the distinct-reader count",
        "content exposures versus unique audience",
        "Should reach mean total views or distinct readers?",
        "CLEAN_AMBIGUOUS", "BULLETS",
    ),
    GeneralizationCase(
        "NG03", "cargo-harbour",
        "A cargo harbour handled 420 vessel calls and 1.8 million tonnes of freight last quarter. State harbour activity as one number.",
        "the vessel-call count", "the freight tonnage",
        "transport events versus cargo mass",
        "Should activity be measured by vessel calls or freight tonnage?",
        "CLEAN_AMBIGUOUS", "QUESTION_FIRST",
    ),
    GeneralizationCase(
        "NG04", "training-programme",
        "A professional training programme registered 900 enrolments across 45 courses this year. Report programme size as one integer.",
        "the enrolment count", "the course count",
        "participant volume versus curriculum breadth",
        "Should programme size mean enrolments or courses?",
        "CLEAN_AMBIGUOUS", "CANONICAL",
    ),
    GeneralizationCase(
        "NG05", "industrial-centrifuge",
        "An industrial centrifuge has 18 sample slots and operates at 12000 revolutions per minute. Report operating speed in revolutions per minute.",
        "the number of sample slots", "the operating rotation speed",
        "container capacity versus rotational rate",
        "Does operating speed mean slot count or revolutions per minute?",
        "EXPLICITLY_DETERMINED", "BULLETS",
    ),
    GeneralizationCase(
        "NG06", "digital-archive",
        "A digital archive contains 8 million documents and occupies 240 terabytes. Report storage volume in terabytes.",
        "the document count", "the occupied digital storage",
        "record count versus storage volume",
        "Should storage volume mean documents or terabytes occupied?",
        "EXPLICITLY_DETERMINED", "PROSE",
    ),
    GeneralizationCase(
        "NG07", "clinical-trial",
        "A clinical trial enrolled 500 participants, of whom 86 percent followed the medication schedule. Report adherence as a percentage.",
        "the participant count", "the adherence percentage",
        "cohort size versus behavioural proportion",
        "Should adherence mean participant count or the percentage following the schedule?",
        "EXPLICITLY_DETERMINED", "QUESTION_FIRST",
    ),
    GeneralizationCase(
        "NG08", "fibre-link",
        "A fibre link provides 100 gigabits per second of bandwidth with 4 milliseconds of latency. Report bandwidth in gigabits per second.",
        "the measured latency", "the data-transfer bandwidth",
        "response delay versus transfer capacity",
        "Should bandwidth mean milliseconds of latency or gigabits per second?",
        "EXPLICITLY_DETERMINED", "CANONICAL",
    ),
    GeneralizationCase(
        "NG09", "regional-airline",
        "A regional airline scheduled 300 flights and 270 arrived on time last month. Report punctuality as one number.",
        "the observed on-time proportion", "the proportion after excluding an assumed set of weather delays",
        "recorded performance versus an undocumented exclusion",
        "Should punctuality exclude the assumed weather-delayed flights?",
        "INVENTED_DEPENDENCE", "QUESTION_FIRST",
    ),
    GeneralizationCase(
        "NG10", "grain-farm",
        "A grain farm harvested 720 tonnes from 120 hectares. Report crop yield as one number.",
        "the observed tonnes per hectare", "yield after applying an unstated moisture correction",
        "recorded field yield versus an undocumented adjustment",
        "Should yield use the unreported moisture correction?",
        "INVENTED_DEPENDENCE", "PROSE",
    ),
    GeneralizationCase(
        "NG11", "hosting-service",
        "A hosting service was available for 718 of 720 measured hours. Report availability as one number.",
        "the observed available-hour proportion", "availability after removing an unreported maintenance window",
        "measured availability versus an undocumented time exclusion",
        "Should availability omit the assumed maintenance window?",
        "INVENTED_DEPENDENCE", "BULLETS",
    ),
    GeneralizationCase(
        "NG12", "assembly-line",
        "An assembly line produced 2400 units and recorded 90 rejected units this week. Report output as one number.",
        "the recorded produced-unit count", "output after adding an assumed quantity of reworked units",
        "recorded production versus an undocumented addition",
        "Should output include the assumed reworked units?",
        "INVENTED_DEPENDENCE", "CANONICAL",
    ),
    GeneralizationCase(
        "NG13", "municipal-census",
        "A municipal census counted 84000 residents and 31000 households. Report the counted population as one integer.",
        "the household count", "the resident count plus an assumed unregistered population",
        "household units versus an undocumented expansion of the explicit resident count",
        "Should counted population include the assumed unregistered residents?",
        "MIXED_DEFECT", "PROSE",
    ),
    GeneralizationCase(
        "NG14", "cold-storage",
        "A cold-storage room contains 600 crates and its thermometer reads minus 18 degrees Celsius. Report the thermometer reading in degrees Celsius.",
        "the crate count", "temperature after applying an unstated calibration offset",
        "inventory count versus an undocumented correction to the requested reading",
        "Should the thermometer reading include the assumed calibration offset?",
        "MIXED_DEFECT", "QUESTION_FIRST",
    ),
    GeneralizationCase(
        "NG15", "supplier-invoice",
        "A supplier invoice lists 50 components at 40 dollars each and states a total of 2000 dollars. Report the stated invoice total in dollars.",
        "the component count", "the total after adding an unstated local tax",
        "item count versus an undocumented addition to the explicit total",
        "Should the stated invoice total include the assumed tax?",
        "MIXED_DEFECT", "BULLETS",
    ),
    GeneralizationCase(
        "NG16", "network-monitor",
        "A network monitor reports median end-to-end latency of 48 milliseconds across 10000 requests. Report measured median latency in milliseconds.",
        "the request count", "latency after subtracting an assumed monitoring overhead",
        "traffic count versus an undocumented adjustment to the explicit measurement",
        "Should measured latency subtract the assumed monitoring overhead?",
        "MIXED_DEFECT", "CANONICAL",
    ),
    GeneralizationCase(
        "NG17", "online-retailer",
        "An online retailer booked 5 million dollars in sales and issued 400000 dollars in refunds. Report revenue as one number.",
        "gross sales before refunds", "net revenue after the stated refunds",
        "gross versus net treatment of a disclosed amount",
        "Should revenue be gross sales or sales net of the stated refunds?",
        "ADVERSARIAL_CLEAN", "BULLETS",
    ),
    GeneralizationCase(
        "NG18", "wind-farm",
        "A wind farm has 60 turbines, of which 54 were operational yesterday. Report available capacity as one integer.",
        "the installed turbine count", "the stated operational turbine count",
        "installed fleet versus currently available fleet",
        "Should available capacity mean all installed turbines or the 54 stated as operational?",
        "ADVERSARIAL_CLEAN", "QUESTION_FIRST",
    ),
    GeneralizationCase(
        "NG19", "courier-network",
        "A courier network scheduled 1200 deliveries and completed 1080 of them yesterday. Report delivery volume as one integer.",
        "the scheduled-delivery count", "the completed-delivery count",
        "planned workload versus realised completions",
        "Should delivery volume mean scheduled or completed deliveries?",
        "ADVERSARIAL_CLEAN", "PROSE",
    ),
    GeneralizationCase(
        "NG20", "electric-vehicle",
        "An electric vehicle battery has 82 kilowatt-hours nominal capacity and reserves 7 kilowatt-hours that drivers cannot use. Report battery capacity as one number.",
        "the stated nominal capacity", "the usable capacity after the stated reserve",
        "nameplate storage versus driver-accessible storage using disclosed values",
        "Should battery capacity mean nominal or usable capacity after the stated reserve?",
        "ADVERSARIAL_CLEAN", "CANONICAL",
    ),
    GeneralizationCase(
        "NG21", "hospital-ward",
        "A hospital ward has 80 staffed beds and 68 are occupied. Report occupancy as one number.",
        "the occupied-bed count", "the occupied share of staffed beds",
        "absolute census versus normalized occupancy rate",
        "Should occupancy mean occupied beds or occupancy percentage?",
        "BOUNDARY_COMPOSITION", "QUESTION_FIRST",
    ),
    GeneralizationCase(
        "NG22", "corporate-emissions",
        "A company reports 900 tonnes of direct emissions and 600 tonnes from purchased electricity. Report emissions as one number.",
        "direct operational emissions only", "direct emissions plus purchased-electricity emissions",
        "narrow operational boundary versus combined reporting boundary",
        "Should emissions include purchased electricity or only direct operations?",
        "BOUNDARY_COMPOSITION", "BULLETS",
    ),
    GeneralizationCase(
        "NG23", "software-team",
        "A software team completed 40 work items worth 130 story points this sprint. Report team velocity as one number.",
        "the completed-item count", "the completed story-point total",
        "unit count versus effort-weighted completion",
        "Should velocity mean completed items or story points?",
        "BOUNDARY_COMPOSITION", "PROSE",
    ),
    GeneralizationCase(
        "NG24", "warehouse-inventory",
        "A warehouse holds 5000 units valued at 2 million dollars. Report inventory as one number.",
        "the physical unit count", "the monetary inventory value",
        "stock quantity versus financial valuation",
        "Should inventory mean units on hand or their monetary value?",
        "BOUNDARY_COMPOSITION", "CANONICAL",
    ),
)

CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])
SPEC_COMMITMENT = {
    "corpus_version": CORPUS_VERSION,
    "corpus_id": CORPUS_ID,
    "theory_baseline": "Cognitive Research Architecture v3.7",
    "methodology_kernel": "v1.1",
    "ontology_object": "generalization of role-structured negative-evidence correction",
    "observable_proxy": "four-arm packet decisions against a later model-panel reference",
    "case_count": len(CASES),
    "batch_size": BATCH_SIZE,
    "criterion_count": len(JUDGE_CRITERIA),
    "case_commitment": CASE_COMMITMENT,
    "rubric": RUBRIC,
    "category_counts": {
        category: sum(case.construction_category == category for case in CASES)
        for category in CATEGORIES
    },
    "surface_style_counts": {
        style: sum(case.surface_style == style for case in CASES)
        for style in SURFACE_STYLES
    },
    "predecessor_prompts_or_labels_available_to_candidates": False,
    "construction_categories_are_ground_truth": False,
    "panel_reference_is_candidate_not_ground_truth": True,
    "selection_authority": False,
    "retention_authority": False,
    "production_authority": False,
}
CORPUS_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def build_generalization_corpus_artifact():
    validate_generalization_corpus_spec()
    source_hash = hash_payload({
        "corpus_spec_hash": CORPUS_SPEC["spec_hash"],
        "case_commitment": CASE_COMMITMENT,
    })
    bindings, candidates = {}, []
    for case in CASES:
        blind_id = "generalization-" + hash_payload([
            CORPUS_VERSION, source_hash, case.item_id,
        ])[:18]
        bindings[blind_id] = {
            "item_id": case.item_id,
            "domain": case.domain,
            "construction_category": case.construction_category,
            "surface_style": case.surface_style,
            "case_commitment": case.commitment(),
        }
        candidates.append({
            "blind_candidate_id": blind_id,
            "public_prompt": case.public_prompt,
            "contrastive_packet": case.packet(),
        })
    batches = [
        {
            "batch_id": f"negative-generalization-batch-{offset // BATCH_SIZE + 1:02d}",
            "public_candidates": candidates[offset:offset + BATCH_SIZE],
        }
        for offset in range(0, len(candidates), BATCH_SIZE)
    ]
    surface_commitment = {
        "surface_version": "negative_evidence_generalization_surface_v0_2",
        "source_artifact_hash": source_hash,
        "batches": batches,
        "bindings": bindings,
        "source_identity_exposed": False,
        "construction_categories_exposed": False,
        "predecessor_labels_exposed": False,
    }
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    report_commitment = {
        "report_version": "negative_evidence_generalization_private_report_v0_2",
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
        "artifact_version": "negative_evidence_generalization_source_v0_2",
        "corpus_spec": CORPUS_SPEC,
        "blind_surface": surface,
        "report": report,
        "evidence_refs": list(EVIDENCE_REFS),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_generalization_corpus_artifact(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("negative_generalization_corpus_hash_invalid")
    if artifact != build_generalization_corpus_artifact():
        raise ValueError("negative_generalization_corpus_semantics_invalid")


def validate_generalization_corpus_spec(*, cases=CASES, spec=CORPUS_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    if (
        spec.get("spec_hash") != hash_payload(commitment)
        or tuple(cases) != CASES
        or len(cases) != 24
        or len({case.item_id for case in cases}) != len(cases)
        or any(
            sum(case.construction_category == category for case in cases) != 4
            for category in CATEGORIES
        )
        or any(
            sum(case.surface_style == style for case in cases) != 6
            for style in SURFACE_STYLES
        )
        or any(term in case.public_prompt.lower() for case in cases for term in LEAKAGE_TERMS)
    ):
        raise ValueError("negative_generalization_corpus_surface_invalid")
    predecessors = (
        *DISCOVERY_CASES, *COORDINATOR_CASES, *HARD_NULL_CASES,
        *RECEIPT_QUALITY_CASES, *NEGATIVE_EVIDENCE_V01_CASES,
    )
    prior_prompts = {
        getattr(case, "public_prompt", getattr(case, "prompt", ""))
        for case in predecessors
    }
    if {case.public_prompt for case in cases} & prior_prompts:
        raise ValueError("negative_generalization_predecessor_reuse_invalid")
