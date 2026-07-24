"""Fresh holdout for split negative-evidence receipt auditing."""

from __future__ import annotations

from dataclasses import dataclass

from .ambiguity_coordinator_holdout import CASES as COORDINATOR_CASES
from .ambiguity_hard_null_holdout import CASES as HARD_NULL_CASES
from .provider_telemetry import hash_payload
from .receipt_quality_calibration_corpus import CASES as RECEIPT_QUALITY_CASES
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, RUBRIC
from .unstated_ambiguity_holdout import CASES as DISCOVERY_CASES, LEAKAGE_TERMS


CORPUS_VERSION = "negative_evidence_holdout_v0_1"
CORPUS_ID = "local-negative-evidence-holdout-v0-1"
EVIDENCE_REFS = (f"corpus://{CORPUS_ID}",)
BATCH_SIZE = 2
CONSTRUCTION_TARGETS = (
    "FULLY_USABLE_CONTROL",
    "FALSE_AMBIGUITY_CONTROL",
    "INVENTED_DEPENDENCE_CONTROL",
)


@dataclass(frozen=True)
class NegativeEvidenceCase:
    item_id: str
    domain: str
    public_prompt: str
    rival_a: str
    rival_b: str
    decisive_contrast: str
    discriminating_question: str
    construction_target: str

    def packet(self):
        return (
            f"RIVAL_A: {self.rival_a} | RIVAL_B: {self.rival_b} | "
            f"CONTRAST: {self.decisive_contrast} | "
            f"QUESTION: {self.discriminating_question}"
        )

    def commitment(self):
        return hash_payload({
            "item_id": self.item_id,
            "domain": self.domain,
            "public_prompt": self.public_prompt,
            "contrastive_packet": self.packet(),
            "construction_target": self.construction_target,
        })


CASES = (
    NegativeEvidenceCase(
        "NE01", "community-clinic",
        "A community clinic recorded 420 appointments involving 310 unique patients yesterday. Report daily service volume as one integer.",
        "the appointment count", "the unique-patient count",
        "service events versus distinct people served",
        "Should service volume mean appointments or unique patients?",
        "FULLY_USABLE_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE02", "cloud-service",
        "A cloud service handled 2.4 million API requests from 180000 active clients yesterday. Report daily usage as one number.",
        "the API-request count", "the active-client count",
        "interaction volume versus participating-client volume",
        "Should usage mean requests or active clients?",
        "FULLY_USABLE_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE03", "transit-hub",
        "A transit hub logged 26000 passenger entries and 1100 train arrivals yesterday. Report daily throughput as one integer.",
        "the passenger-entry count", "the train-arrival count",
        "people moved versus vehicle movements",
        "Should throughput refer to passenger entries or train arrivals?",
        "FULLY_USABLE_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE04", "university-research",
        "A university produced 600 research papers and received 75 patents last year. Report annual research output as one integer.",
        "the paper count", "the patent count",
        "scholarly publications versus protected inventions",
        "Should research output mean papers or patents?",
        "FULLY_USABLE_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE05", "streaming-platform",
        "A streaming platform recorded 1.8 million viewing hours from 420000 viewers yesterday. Report daily engagement as one number.",
        "the viewing-hour total", "the viewer count",
        "time consumed versus audience reach",
        "Should engagement mean viewing hours or viewers?",
        "FULLY_USABLE_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE06", "recycling-centre",
        "A recycling centre processed 900 tonnes of material through 36000 customer drop-offs last year. Report annual activity as one number.",
        "the processed mass", "the customer drop-off count",
        "material volume versus service-event volume",
        "Should activity mean tonnes processed or customer drop-offs?",
        "FULLY_USABLE_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE07", "laboratory-incubator",
        "A laboratory incubator held 24 samples at an operating temperature of 37 degrees Celsius. Report its operating temperature in degrees Celsius.",
        "the sample count", "the operating temperature",
        "contained-object count versus thermal setting",
        "Should operating temperature mean sample count or degrees Celsius?",
        "FALSE_AMBIGUITY_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE08", "airport-runway",
        "An airport has two runways; the longest is 3200 metres. Report the longest runway length in metres.",
        "the number of runways", "the longest runway length",
        "infrastructure count versus physical distance",
        "Should longest runway length mean runway count or distance in metres?",
        "FALSE_AMBIGUITY_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE09", "battery-pack",
        "A battery pack stores 75 kilowatt-hours and can deliver 180 kilowatts at peak. Report storage capacity in kilowatt-hours.",
        "the peak power output", "the stored energy capacity",
        "instantaneous power versus stored energy",
        "Should storage capacity mean peak kilowatts or kilowatt-hours stored?",
        "FALSE_AMBIGUITY_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE10", "web-service",
        "A website served 4 million requests with a median latency of 120 milliseconds. Report median latency in milliseconds.",
        "the request count", "the median response latency",
        "traffic volume versus response time",
        "Should median latency mean request count or response time?",
        "FALSE_AMBIGUITY_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE11", "school-attendance",
        "A school enrolled 1000 students and recorded an attendance rate of 92 percent. Report attendance rate as a percentage.",
        "the enrolled-student count", "the attendance percentage",
        "population size versus attendance proportion",
        "Should attendance rate mean student count or percentage?",
        "FALSE_AMBIGUITY_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE12", "water-treatment",
        "A water-treatment plant uses five pumps and has a rated daily output of 40 megalitres. Report rated daily output in megalitres.",
        "the pump count", "the rated daily water output",
        "equipment count versus treated-water volume",
        "Should rated daily output mean pump count or megalitres of water?",
        "FALSE_AMBIGUITY_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE13", "theatre-attendance",
        "A theatre sold 1200 tickets and counted 900 people entering for a performance. Report turnout as one integer.",
        "the observed entry count", "the entry count after adding an assumed 8 percent gate undercount",
        "observed attendance versus an undocumented correction",
        "Should turnout include the assumed gate undercount?",
        "INVENTED_DEPENDENCE_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE14", "dairy-farm",
        "A dairy farm collected 3000 litres of milk from 120 cows yesterday. Report daily productivity as one number.",
        "litres collected per cow", "litres per cow after subtracting an unstated spoilage allowance",
        "observed per-animal yield versus an undocumented adjustment",
        "Should productivity subtract the unreported spoilage allowance?",
        "INVENTED_DEPENDENCE_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE15", "software-project",
        "A software project opened 240 issues and closed 180 issues this quarter. Report progress as one number.",
        "the observed issue-closure rate", "the closure rate after assuming 20 open issues are duplicates",
        "recorded closure versus an undocumented duplicate correction",
        "Should progress exclude the assumed duplicate issues?",
        "INVENTED_DEPENDENCE_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE16", "parcel-delivery",
        "A delivery service dispatched 800 parcels and recorded 760 deliveries yesterday. Report reliability as one number.",
        "the recorded delivery proportion", "a corrected proportion after adding 15 assumed unscanned deliveries",
        "observed completion versus an undocumented scan correction",
        "Should reliability include the assumed unscanned deliveries?",
        "INVENTED_DEPENDENCE_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE17", "solar-site",
        "A solar site recorded 15 megawatt-hours at its inverters and 12 megawatt-hours at the grid meter yesterday. Report output as one number.",
        "the grid-delivered energy", "weather-normalized energy using an unstated 0.9 factor",
        "metered delivery versus an undocumented normalization",
        "Should output use the unreported weather-normalization factor?",
        "INVENTED_DEPENDENCE_CONTROL",
    ),
    NegativeEvidenceCase(
        "NE18", "hospital-flow",
        "A hospital recorded 500 admissions and 430 discharges last month. Report patient flow as one integer.",
        "the recorded admission count", "admissions plus 40 undocumented transfer arrivals",
        "recorded arrivals versus an undocumented boundary expansion",
        "Should patient flow include the unreported transfer arrivals?",
        "INVENTED_DEPENDENCE_CONTROL",
    ),
)

CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])
SPEC_COMMITMENT = {
    "corpus_version": CORPUS_VERSION,
    "corpus_id": CORPUS_ID,
    "theory_baseline": "Cognitive Research Architecture v3.7",
    "methodology_kernel": "v1.1",
    "ontology_object": "negative semantic evidence that blocks receipt usability",
    "observable_proxy": "model-panel packet states and specialist veto receipts",
    "case_count": len(CASES),
    "batch_size": BATCH_SIZE,
    "criterion_count": len(JUDGE_CRITERIA),
    "case_commitment": CASE_COMMITMENT,
    "rubric": RUBRIC,
    "construction_target_counts": {
        target: sum(case.construction_target == target for case in CASES)
        for target in CONSTRUCTION_TARGETS
    },
    "predecessor_prompts_or_labels_available_to_candidate": False,
    "construction_targets_are_ground_truth": False,
    "panel_reference_is_candidate_not_ground_truth": True,
    "selection_authority": False,
    "retention_authority": False,
}
CORPUS_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def build_negative_evidence_corpus_artifact():
    validate_negative_evidence_corpus_spec()
    source_hash = hash_payload({
        "corpus_spec_hash": CORPUS_SPEC["spec_hash"],
        "case_commitment": CASE_COMMITMENT,
    })
    bindings, candidates = {}, []
    for case in CASES:
        blind_id = "negative-evidence-" + hash_payload([
            CORPUS_VERSION, source_hash, case.item_id,
        ])[:18]
        bindings[blind_id] = {
            "item_id": case.item_id,
            "domain": case.domain,
            "construction_target": case.construction_target,
            "case_commitment": case.commitment(),
        }
        candidates.append((case, {
            "blind_candidate_id": blind_id,
            "contrastive_packet": case.packet(),
        }))
    batches = []
    for offset in range(0, len(candidates), BATCH_SIZE):
        group = candidates[offset:offset + BATCH_SIZE]
        batches.append({
            "batch_id": f"negative-evidence-batch-{offset // BATCH_SIZE + 1:02d}",
            "public_candidates": [
                {**candidate, "public_prompt": case.public_prompt}
                for case, candidate in group
            ],
        })
    surface_commitment = {
        "surface_version": "negative_evidence_blind_surface_v0_1",
        "source_artifact_hash": source_hash,
        "batches": batches,
        "bindings": bindings,
        "source_identity_exposed": False,
        "construction_targets_exposed": False,
        "predecessor_labels_exposed": False,
    }
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    report_commitment = {
        "report_version": "negative_evidence_private_report_v0_1",
        "corpus_spec_hash": CORPUS_SPEC["spec_hash"],
        "blind_surface_hash": surface["surface_hash"],
        "trials": [
            {
                "blind_candidate_id": blind_id,
                "item_id": binding["item_id"],
                "construction_target": binding["construction_target"],
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
        "artifact_version": "negative_evidence_holdout_source_v0_1",
        "corpus_spec": CORPUS_SPEC,
        "blind_surface": surface,
        "report": report,
        "evidence_refs": list(EVIDENCE_REFS),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_negative_evidence_corpus_artifact(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("negative_evidence_corpus_artifact_hash_invalid")
    if artifact != build_negative_evidence_corpus_artifact():
        raise ValueError("negative_evidence_corpus_artifact_semantics_invalid")


def validate_negative_evidence_corpus_spec(*, cases=CASES, spec=CORPUS_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    targets = [case.construction_target for case in cases]
    if (
        spec.get("spec_hash") != hash_payload(commitment)
        or tuple(cases) != CASES
        or len(cases) != 18
        or len({case.item_id for case in cases}) != len(cases)
        or any(targets.count(target) != 6 for target in CONSTRUCTION_TARGETS)
        or any(term in case.public_prompt.lower() for case in cases for term in LEAKAGE_TERMS)
    ):
        raise ValueError("negative_evidence_corpus_surface_invalid")
    predecessors = (
        *DISCOVERY_CASES, *COORDINATOR_CASES, *HARD_NULL_CASES,
    )
    prior_prompts = {case.prompt for case in predecessors}
    prior_prompts.update(case.public_prompt for case in RECEIPT_QUALITY_CASES)
    if {case.public_prompt for case in cases} & prior_prompts:
        raise ValueError("negative_evidence_corpus_predecessor_reuse_invalid")
