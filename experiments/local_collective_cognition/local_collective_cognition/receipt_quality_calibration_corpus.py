"""Independent receipt-quality calibration corpus for ambiguity coordination."""

from __future__ import annotations

from dataclasses import dataclass

from .ambiguity_coordinator_holdout import CASES as COORDINATOR_V01_CASES
from .ambiguity_hard_null_holdout import CASES as HARD_NULL_V01_CASES
from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, RUBRIC
from .unstated_ambiguity_holdout import CASES as DISCOVERY_V04_CASES, LEAKAGE_TERMS


CORPUS_VERSION = "receipt_quality_calibration_corpus_v0_1"
CORPUS_ID = "local-receipt-quality-calibration-v0-1"
EVIDENCE_REFS = (f"corpus://{CORPUS_ID}",)
BATCH_SIZE = 1


@dataclass(frozen=True)
class ReceiptQualityCase:
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
    ReceiptQualityCase(
        "RQ01", "museum-catalog",
        "A museum maintains 240 physical exhibits and a digital catalog occupying 1.8 terabytes. Report the collection size as one number.",
        "the number of physical exhibits", "the digital storage footprint",
        "counted objects versus storage volume",
        "Should size mean exhibit count or digital storage volume?",
        "FULLY_USABLE_CONTROL",
    ),
    ReceiptQualityCase(
        "RQ02", "conference-program",
        "A conference schedules 36 accepted talks across 6 thematic tracks. Report the conference scale as one integer.",
        "the number of accepted talks", "the number of thematic tracks",
        "program-item count versus organizational-track count",
        "Should scale refer to talks or tracks?",
        "FULLY_USABLE_CONTROL",
    ),
    ReceiptQualityCase(
        "RQ03", "bridge-inspection",
        "A bridge spans 900 metres and is supported by 12 piers. Report its span in metres as one integer.",
        "the year in which the bridge opened", "the end-to-end distance in metres",
        "opening date versus physical distance",
        "Should span mean opening year or distance?",
        "RIVAL_A_OBJECT_FIT",
    ),
    ReceiptQualityCase(
        "RQ04", "investment-fund",
        "An investment fund holds 70 securities with a total market value of 250 million dollars. Report portfolio value in millions of dollars.",
        "the number of securities", "the total market value",
        "holding count versus monetary value",
        "Should value mean holding count or market value?",
        "RIVAL_A_OBJECT_FIT",
    ),
    ReceiptQualityCase(
        "RQ05", "orchard-yield",
        "An orchard harvested 480 crates from 20 hectares. Report yield per hectare as one number.",
        "crates divided by hectares", "the number of orchard workers",
        "production density versus workforce size",
        "Should yield mean crates per hectare or worker count?",
        "RIVAL_B_OBJECT_FIT",
    ),
    ReceiptQualityCase(
        "RQ06", "library-circulation",
        "A library lent 3200 books during 40 open days. Report average daily circulation as one integer.",
        "loans divided by open days", "the library floor area",
        "daily lending rate versus building area",
        "Should circulation mean daily loans or floor area?",
        "RIVAL_B_OBJECT_FIT",
    ),
    ReceiptQualityCase(
        "RQ07", "weather-station",
        "A weather station recorded 18 millimetres of rain over six hours. Report rainfall as one number.",
        "the measured precipitation amount", "the amount of rain that was measured",
        "two phrasings of the same precipitation quantity",
        "Should rainfall mean measured precipitation or measured rain?",
        "RIVALS_STRUCTURALLY_DISTINCT",
    ),
    ReceiptQualityCase(
        "RQ08", "factory-defects",
        "A factory inspected 500 components and found 20 defective units. Report the defect level as one number.",
        "the defective-unit count", "the number of defective components",
        "equivalent names for the same count",
        "Should level mean defective units or defective components?",
        "RIVALS_STRUCTURALLY_DISTINCT",
    ),
    ReceiptQualityCase(
        "RQ09", "reservoir-release",
        "A reservoir released 6000 cubic metres of water over 30 minutes. Report discharge as one number.",
        "the total released volume", "the release rate per minute",
        "the two interpretations differ",
        "Should discharge mean total volume or rate?",
        "CONTRAST_NAMES_DECISIVE_VARIABLE",
    ),
    ReceiptQualityCase(
        "RQ10", "retail-returns",
        "A store sold 800 items and received 32 returns. Report returns as one number.",
        "the returned-item count", "the return percentage",
        "one is one thing and the other is another",
        "Should returns mean count or percentage?",
        "CONTRAST_NAMES_DECISIVE_VARIABLE",
    ),
    ReceiptQualityCase(
        "RQ11", "rail-service",
        "A rail service scheduled 50 trains and 44 arrived on time. Report punctuality as one number.",
        "the on-time train count", "the on-time percentage",
        "absolute count versus normalized rate",
        "What answer would be most useful?",
        "QUESTION_RESOLVES_AMBIGUITY",
    ),
    ReceiptQualityCase(
        "RQ12", "network-latency",
        "A network test sent 200 packets with a mean round-trip time of 35 milliseconds. Report network performance as one number.",
        "the packet count", "the mean round-trip time",
        "traffic volume versus latency",
        "Could you clarify the task?",
        "QUESTION_RESOLVES_AMBIGUITY",
    ),
    ReceiptQualityCase(
        "RQ13", "solar-array",
        "A solar array has 40 panels rated at 300 watts each and produced 9 kilowatt-hours today. Report output as one number.",
        "today's generated energy", "the guaranteed output after a hidden 15 percent loss",
        "observed energy versus assumed derated output",
        "Should output mean observed energy or the hidden-loss estimate?",
        "NO_INVENTED_FACT_OR_SOLUTION_DEPENDENCE",
    ),
    ReceiptQualityCase(
        "RQ14", "shipping-order",
        "An order contains 24 boxes weighing 8 kilograms each. Report shipment weight as one integer.",
        "the stated weight of one box", "the total weight after adding an unstated pallet weight",
        "per-box weight versus an assumed loaded total",
        "Should weight include the pallet that is not described?",
        "NO_INVENTED_FACT_OR_SOLUTION_DEPENDENCE",
    ),
)

CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])
SPEC_COMMITMENT = {
    "corpus_version": CORPUS_VERSION,
    "corpus_id": CORPUS_ID,
    "theory_baseline": "Cognitive Research Architecture v3.7",
    "methodology_kernel": "v1.1",
    "object_before_proxy": {
        "ontology_object": "semantic usability of an ambiguity-discovery receipt",
        "observable_proxy": "six criterion-level model-panel judgments",
        "metrics": [
            "criterion_agreement", "usable_packet_accuracy", "false_usable_rate",
            "uncertain_rate", "provider_cost",
        ],
    },
    "case_count": len(CASES),
    "criterion_count": len(JUDGE_CRITERIA),
    "case_commitment": CASE_COMMITMENT,
    "rubric": RUBRIC,
    "construction_target_counts": {
        target: sum(case.construction_target == target for case in CASES)
        for target in {case.construction_target for case in CASES}
    },
    "excluded_predecessor_benchmarks": [
        "unstated_ambiguity_holdout_v0_4",
        "ambiguity_coordinator_holdout_v0_1",
        "ambiguity_hard_null_holdout_v0_1",
    ],
    "predecessor_labels_available_for_tuning": False,
    "panel_reference_is_candidate_not_ground_truth": True,
    "selection_authority": False,
    "retention_authority": False,
}
CORPUS_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def build_receipt_quality_corpus_artifact():
    validate_receipt_quality_corpus_spec()
    source_commitment_hash = hash_payload({
        "corpus_spec_hash": CORPUS_SPEC["spec_hash"],
        "case_commitment": CASE_COMMITMENT,
    })
    batches, bindings = [], {}
    for index, case in enumerate(CASES, start=1):
        blind_id = "receipt-" + hash_payload([
            CORPUS_VERSION, source_commitment_hash, case.item_id,
        ])[:18]
        public_candidate = {
            "blind_candidate_id": blind_id,
            "contrastive_packet": case.packet(),
        }
        bindings[blind_id] = {
            "item_id": case.item_id,
            "domain": case.domain,
            "construction_target": case.construction_target,
            "case_commitment": case.commitment(),
        }
        batches.append({
            "batch_id": f"receipt-quality-batch-{index:02d}",
            "public_prompt": case.public_prompt,
            "public_candidates": [public_candidate],
        })
    surface_commitment = {
        "surface_version": "receipt_quality_blind_surface_v0_1",
        "source_artifact_hash": source_commitment_hash,
        "batches": batches,
        "bindings": bindings,
        "source_identity_exposed": False,
        "construction_targets_exposed": False,
        "predecessor_labels_exposed": False,
    }
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    trials = [
        {
            "blind_candidate_id": blind_id,
            "item_id": binding["item_id"],
            "construction_target": binding["construction_target"],
            "construction_expectation_is_ground_truth": False,
        }
        for blind_id, binding in sorted(bindings.items())
    ]
    report_commitment = {
        "report_version": "receipt_quality_corpus_private_report_v0_1",
        "corpus_spec_hash": CORPUS_SPEC["spec_hash"],
        "blind_surface_hash": surface["surface_hash"],
        "trials": trials,
        "reference_state": "AWAITING_GPT_GEMINI_ANNOTATIONS",
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
    }
    report = {**report_commitment, "report_hash": hash_payload(report_commitment)}
    commitment = {
        "artifact_version": "receipt_quality_calibration_source_v0_1",
        "corpus_spec": CORPUS_SPEC,
        "blind_surface": surface,
        "report": report,
        "evidence_refs": list(EVIDENCE_REFS),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_receipt_quality_corpus_artifact(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("receipt_quality_corpus_artifact_hash_invalid")
    if artifact != build_receipt_quality_corpus_artifact():
        raise ValueError("receipt_quality_corpus_artifact_semantics_invalid")


def validate_receipt_quality_corpus_spec(*, cases=CASES, spec=CORPUS_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    if spec.get("spec_hash") != hash_payload(commitment) or tuple(cases) != CASES:
        raise ValueError("receipt_quality_corpus_spec_invalid")
    targets = [case.construction_target for case in cases]
    expected_targets = {"FULLY_USABLE_CONTROL", *JUDGE_CRITERIA}
    if (
        len(cases) != 14
        or len({case.item_id for case in cases}) != len(cases)
        or set(targets) != expected_targets
        or targets.count("FULLY_USABLE_CONTROL") != 2
        or any(targets.count(criterion) != 2 for criterion in JUDGE_CRITERIA)
        or any(term in case.public_prompt.lower() for case in cases for term in LEAKAGE_TERMS)
    ):
        raise ValueError("receipt_quality_corpus_surface_invalid")
    predecessors = (*DISCOVERY_V04_CASES, *COORDINATOR_V01_CASES, *HARD_NULL_V01_CASES)
    if (
        {case.item_id for case in cases} & {case.item_id for case in predecessors}
        or {case.public_prompt for case in cases} & {case.prompt for case in predecessors}
    ):
        raise ValueError("receipt_quality_corpus_predecessor_reuse_invalid")
