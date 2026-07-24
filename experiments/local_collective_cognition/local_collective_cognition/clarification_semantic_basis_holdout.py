"""Fresh four-class semantic-basis holdout for clarification v0.11."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


CORPUS_VERSION = "clarification_semantic_basis_holdout_v0_11"
CORPUS_ID = "local-clarification-semantic-basis-v0-11"
EVIDENCE_REFS = (f"corpus://{CORPUS_ID}",)
BATCH_SIZE = 2


@dataclass(frozen=True)
class SemanticBasisCase:
    case_id: str
    domain: str
    fact: str
    request: str
    candidate_a: str
    candidate_b: str
    construction_basis: str
    selected_object: str
    pragmatic_preference: str

    def commitment(self):
        return asdict(self)


CASES = (
    SemanticBasisCase("SL01", "cinema", "A cinema sold 184000 tickets to 73000 patrons.", "Report the ticket count as one integer.", "ticket count", "distinct patron count", "LEXICAL_EXACT", "CANDIDATE_A", "CANDIDATE_A"),
    SemanticBasisCase("SL02", "library", "A library recorded 410000 loans to 52000 borrowers.", "Report the distinct borrower count as one integer.", "loan count", "distinct borrower count", "LEXICAL_EXACT", "CANDIDATE_B", "CANDIDATE_B"),
    SemanticBasisCase("SL03", "imaging-center", "An imaging center completed 96000 scans for 38000 patients.", "Report the scan count as one number.", "scan count", "distinct patient count", "LEXICAL_EXACT", "CANDIDATE_A", "CANDIDATE_A"),
    SemanticBasisCase("SL04", "streaming-service", "A streaming service delivered 8.2 million streams for 610000 subscribers.", "Report the distinct subscriber count as one number.", "stream count", "distinct subscriber count", "LEXICAL_EXACT", "CANDIDATE_B", "CANDIDATE_B"),
    SemanticBasisCase("SL05", "laboratory", "A laboratory completed 275000 assays for 88000 specimens.", "Report the assay count as one integer.", "assay count", "distinct specimen count", "LEXICAL_EXACT", "CANDIDATE_A", "CANDIDATE_A"),
    SemanticBasisCase("SL06", "conference", "A conference logged 49000 entries by 12500 attendees.", "Report the distinct attendee count as one integer.", "entry count", "distinct attendee count", "LEXICAL_EXACT", "CANDIDATE_B", "CANDIDATE_B"),
    SemanticBasisCase("SC01", "clinic", "A clinic completed 112000 consultations for 47000 patients.", "How many appointments were completed? Return one integer.", "consultation-event count", "distinct patient count", "COMPOSITIONAL_ENTAILMENT", "CANDIDATE_A", "CANDIDATE_A"),
    SemanticBasisCase("SC02", "subscription-service", "A subscription service sent 6.4 million notices to 340000 subscribers.", "How many people held subscriptions? Return one integer.", "notice count", "distinct subscriber count", "COMPOSITIONAL_ENTAILMENT", "CANDIDATE_B", "CANDIDATE_B"),
    SemanticBasisCase("SC03", "assembly-plant", "An assembly plant produced 830000 units on 48 active lines.", "How many finished products left the lines? Return one integer.", "produced-unit count", "active production-line count", "COMPOSITIONAL_ENTAILMENT", "CANDIDATE_A", "CANDIDATE_A"),
    SemanticBasisCase("SC04", "video-channel", "A video channel recorded 3.9 million views from 560000 viewers.", "How many unique people watched? Return one integer.", "view-event count", "distinct viewer count", "COMPOSITIONAL_ENTAILMENT", "CANDIDATE_B", "CANDIDATE_B"),
    SemanticBasisCase("SC05", "insurer", "An insurer received 146000 claims from 91000 claimants.", "How many insurance cases arrived? Return one integer.", "received-claim count", "distinct claimant count", "COMPOSITIONAL_ENTAILMENT", "CANDIDATE_A", "CANDIDATE_A"),
    SemanticBasisCase("SC06", "employer", "An employer scheduled 730000 shifts across 18500 employees.", "How many staff members were employed? Return one integer.", "scheduled-shift count", "distinct employee count", "COMPOSITIONAL_ENTAILMENT", "CANDIDATE_B", "CANDIDATE_B"),
    SemanticBasisCase("SP01", "field-service", "A field-service platform completed 215000 jobs for 69000 users.", "Report service activity as one number.", "completed-job count", "distinct user count", "PRAGMATIC_DEFAULT", "NONE", "CANDIDATE_A"),
    SemanticBasisCase("SP02", "outreach-program", "An outreach program made 440000 contacts with 128000 customers.", "Report customer reach as one number.", "contact-event count", "distinct customer count", "PRAGMATIC_DEFAULT", "NONE", "CANDIDATE_B"),
    SemanticBasisCase("SP03", "document-service", "A document service processed 720000 forms for 37000 organizations.", "Report processing volume as one number.", "processed-form count", "distinct organization count", "PRAGMATIC_DEFAULT", "NONE", "CANDIDATE_A"),
    SemanticBasisCase("SP04", "community-program", "A community program logged 83000 attendances by 21000 residents.", "Report community participation as one number.", "attendance-event count", "distinct resident count", "PRAGMATIC_DEFAULT", "NONE", "CANDIDATE_B"),
    SemanticBasisCase("SP05", "edge-network", "An edge network served 12 million requests from 470000 clients.", "Report network load as one number.", "request count", "distinct client count", "PRAGMATIC_DEFAULT", "NONE", "CANDIDATE_A"),
    SemanticBasisCase("SP06", "retail-network", "A retail network recorded 1.1 million purchases across 8400 stores.", "Report market coverage as one number.", "purchase-event count", "distinct store count", "PRAGMATIC_DEFAULT", "NONE", "CANDIDATE_B"),
    SemanticBasisCase("SN01", "museum", "A museum issued 92000 admissions to 61000 visitors.", "The brief gives no convention for choosing between the two measures. Return the primary metric as one number.", "admission-event count", "distinct visitor count", "NO_PREFERENCE", "NONE", "NONE"),
    SemanticBasisCase("SN02", "freight-exchange", "A freight exchange matched 310000 loads with 27000 carriers.", "No reporting convention or analytic objective is supplied. Return the primary metric as one number.", "matched-load count", "distinct carrier count", "NO_PREFERENCE", "NONE", "NONE"),
    SemanticBasisCase("SN03", "learning-platform", "A learning platform recorded 680000 lesson completions by 95000 learners.", "The request supplies no basis for preferring either candidate. Return the primary metric as one number.", "lesson-completion count", "distinct learner count", "NO_PREFERENCE", "NONE", "NONE"),
    SemanticBasisCase("SN04", "repair-network", "A repair network closed 155000 work orders for 78000 devices.", "Neither measure is designated as the reporting default. Return the primary metric as one number.", "closed-work-order count", "distinct device count", "NO_PREFERENCE", "NONE", "NONE"),
    SemanticBasisCase("SN05", "licensing-office", "A licensing office processed 204000 filings from 89000 applicants.", "The brief intentionally leaves the choice between the measures open. Return the primary metric as one number.", "processed-filing count", "distinct applicant count", "NO_PREFERENCE", "NONE", "NONE"),
    SemanticBasisCase("SN06", "research-portal", "A research portal served 4.8 million downloads to 230000 accounts.", "No use case, convention, or preference between the measures is provided. Return the primary metric as one number.", "download-event count", "distinct account count", "NO_PREFERENCE", "NONE", "NONE"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])
SPEC_COMMITMENT = {
    "corpus_version": CORPUS_VERSION,
    "corpus_id": CORPUS_ID,
    "ontology_object": "semantic basis of object selection before clarification action",
    "observable_proxy": "fresh four-class selection-basis discrimination",
    "case_count": 24,
    "batch_size": BATCH_SIZE,
    "case_commitment": CASE_COMMITMENT,
    "construction_counts": {"LEXICAL_EXACT": 6, "COMPOSITIONAL_ENTAILMENT": 6, "PRAGMATIC_DEFAULT": 6, "NO_PREFERENCE": 6},
    "fixed_direction_counts": {"CANDIDATE_A": 6, "CANDIDATE_B": 6},
    "pragmatic_direction_counts": {"CANDIDATE_A": 9, "CANDIDATE_B": 9, "NONE": 6},
    "construction_labels_are_pre_panel_diagnostics_only": True,
    "matched_counterpart_visible": False,
    "fresh_from_v0_10": True,
    "evidence_coordinate": "SYNTHETIC_SEMANTIC_TRANSFER_AUDIT",
    "real_world_ground_truth_claim": False,
    "action_credit_authority": False,
    "selection_authority": False,
    "retention_authority": False,
    "production_authority": False,
}
CORPUS_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def build_semantic_basis_holdout_artifact():
    validate_semantic_basis_holdout_spec()
    source_hash = hash_payload({"spec_hash": CORPUS_SPEC["spec_hash"], "case_commitment": CASE_COMMITMENT})
    bindings, batches = {}, []
    ordered = sorted(CASES, key=lambda case: hash_payload([CORPUS_VERSION, case.case_id]))
    for offset in range(0, len(ordered), BATCH_SIZE):
        public_cases = []
        for case in ordered[offset:offset + BATCH_SIZE]:
            blind_id = "semantic-basis-" + hash_payload([CORPUS_VERSION, source_hash, case.case_id])[:18]
            public = {"blind_case_id": blind_id, "public_prompt": f"{case.fact} {case.request}", "candidate_a": case.candidate_a, "candidate_b": case.candidate_b}
            bindings[blind_id] = {
                "case_id": case.case_id,
                "domain": case.domain,
                "construction_basis": case.construction_basis,
                "truth_category": "PROMPT_FIXED" if case.construction_basis in ("LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT") else "OPEN_RIVALS",
                "selected_object": case.selected_object,
                "pragmatic_preference": case.pragmatic_preference,
                "axis_assessment_complete": True,
                "case_commitment": hash_payload(public),
            }
            public_cases.append(public)
        batches.append({"batch_id": f"semantic-basis-batch-{len(batches) + 1:02d}", "public_cases": public_cases})
    surface_commitment = {
        "surface_version": "clarification_semantic_basis_surface_v0_11",
        "source_artifact_hash": source_hash,
        "batches": batches,
        "matched_counterpart_visible": False,
        "oracle_exposed": False,
        "construction_exposed": False,
    }
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    oracle_commitment = {
        "oracle_version": "clarification_semantic_basis_oracle_v0_11",
        "surface_hash": surface["surface_hash"],
        "bindings": bindings,
        "revealed_to_provider": False,
        "construction_labels_are_pre_panel_diagnostics_only": True,
    }
    oracle = {**oracle_commitment, "oracle_hash": hash_payload(oracle_commitment)}
    commitment = {"artifact_version": "clarification_semantic_basis_source_v0_11", "corpus_spec": CORPUS_SPEC, "public_surface": surface, "private_oracle": oracle, "evidence_refs": list(EVIDENCE_REFS)}
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_semantic_basis_holdout_artifact(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_semantic_basis_holdout_artifact():
        raise ValueError("clarification_semantic_basis_artifact_invalid")


def validate_semantic_basis_holdout_spec(*, cases=CASES, spec=CORPUS_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    counts = {basis: sum(case.construction_basis == basis for case in cases) for basis in ("LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT", "PRAGMATIC_DEFAULT", "NO_PREFERENCE")}
    if spec.get("spec_hash") != hash_payload(commitment) or tuple(cases) != CASES or len(cases) != 24 or any(value != 6 for value in counts.values()):
        raise ValueError("clarification_semantic_basis_spec_invalid")
