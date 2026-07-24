"""Fresh balanced cross-axis conflict holdout v0.13."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


CORPUS_VERSION = "clarification_joint_holdout_v0_13"
CORPUS_ID = "local-clarification-joint-v0-13"
EVIDENCE_REFS = (f"corpus://{CORPUS_ID}",)
BATCH_SIZE = 4


@dataclass(frozen=True)
class JointCase:
    case_id: str
    target_axis: str
    target_action: str
    public_prompt: str
    candidate_a: str
    candidate_b: str
    locked_selected: str
    locked_preference: str
    locked_completeness: str
    local_basis: str
    truth_selected: str
    truth_basis: str
    truth_preference: str
    truth_completeness: str

    def commitment(self):
        return asdict(self)


CASES = (
    JointCase("JB01", "SELECTION_BASIS", "REVISE", "A field platform completed 240000 jobs for 71000 users. Report operational activity as one number.", "completed-job count", "distinct user count", "NONE", "CANDIDATE_A", "COMPLETE", "COMPOSITIONAL_ENTAILMENT", "NONE", "PRAGMATIC_DEFAULT", "CANDIDATE_A", "COMPLETE"),
    JointCase("JB02", "SELECTION_BASIS", "REVISE", "A media service logged 5.2 million views from 640000 viewers. Report audience reach as one number.", "view-event count", "distinct viewer count", "NONE", "CANDIDATE_B", "COMPLETE", "NO_PREFERENCE", "NONE", "PRAGMATIC_DEFAULT", "CANDIDATE_B", "COMPLETE"),
    JointCase("JB03", "SELECTION_BASIS", "REVISE", "A document gateway processed 810000 forms for 46000 organizations. Report processing volume as one number.", "processed-form count", "distinct organization count", "NONE", "CANDIDATE_A", "COMPLETE", "COMPOSITIONAL_ENTAILMENT", "NONE", "PRAGMATIC_DEFAULT", "CANDIDATE_A", "COMPLETE"),
    JointCase("JB04", "SELECTION_BASIS", "PRESERVE", "A cinema sold 192000 tickets to 76000 patrons. Report the ticket count as one integer.", "ticket count", "distinct patron count", "CANDIDATE_A", "CANDIDATE_A", "COMPLETE", "LEXICAL_EXACT", "CANDIDATE_A", "LEXICAL_EXACT", "CANDIDATE_A", "COMPLETE"),
    JointCase("JB05", "SELECTION_BASIS", "PRESERVE", "A membership service sent 3.4 million notices to 280000 members. How many unique people were members? Return one integer.", "notice count", "distinct member count", "CANDIDATE_B", "CANDIDATE_B", "COMPLETE", "COMPOSITIONAL_ENTAILMENT", "CANDIDATE_B", "COMPOSITIONAL_ENTAILMENT", "CANDIDATE_B", "COMPLETE"),
    JointCase("JB06", "SELECTION_BASIS", "PRESERVE", "A portal served 920000 downloads to 150000 accounts. The brief explicitly supplies no rule or preference between the two measures.", "download-event count", "distinct account count", "NONE", "NONE", "COMPLETE", "NO_PREFERENCE", "NONE", "NO_PREFERENCE", "NONE", "COMPLETE"),
    JointCase("JS01", "SELECTED_OBJECT", "REOPEN", "A retailer processed 530000 orders from 190000 households. Report the order count as one integer.", "order count", "distinct household count", "NONE", "CANDIDATE_A", "COMPLETE", "LEXICAL_EXACT", "CANDIDATE_A", "LEXICAL_EXACT", "CANDIDATE_A", "COMPLETE"),
    JointCase("JS02", "SELECTED_OBJECT", "REOPEN", "A charity received 175000 gifts from 62000 donors. Report the distinct donor count as one integer.", "gift count", "distinct donor count", "NONE", "CANDIDATE_B", "COMPLETE", "LEXICAL_EXACT", "CANDIDATE_B", "LEXICAL_EXACT", "CANDIDATE_B", "COMPLETE"),
    JointCase("JS03", "SELECTED_OBJECT", "REOPEN", "A conference recorded 68000 entries by 18000 attendees. How many unique people attended? Return one integer.", "entry-event count", "distinct attendee count", "CANDIDATE_A", "CANDIDATE_B", "COMPLETE", "COMPOSITIONAL_ENTAILMENT", "CANDIDATE_B", "COMPOSITIONAL_ENTAILMENT", "CANDIDATE_B", "COMPLETE"),
    JointCase("JS04", "SELECTED_OBJECT", "PRESERVE", "A laboratory completed 315000 assays for 102000 specimens. Report the assay count as one integer.", "assay count", "distinct specimen count", "CANDIDATE_A", "CANDIDATE_A", "COMPLETE", "LEXICAL_EXACT", "CANDIDATE_A", "LEXICAL_EXACT", "CANDIDATE_A", "COMPLETE"),
    JointCase("JS05", "SELECTED_OBJECT", "PRESERVE", "A video channel recorded 4.6 million plays from 710000 viewers. How many unique people watched? Return one integer.", "play-event count", "distinct viewer count", "CANDIDATE_B", "CANDIDATE_B", "COMPLETE", "COMPOSITIONAL_ENTAILMENT", "CANDIDATE_B", "COMPOSITIONAL_ENTAILMENT", "CANDIDATE_B", "COMPLETE"),
    JointCase("JS06", "SELECTED_OBJECT", "PRESERVE", "A network served 9.7 million requests from 390000 clients. Report service load as one number.", "request count", "distinct client count", "NONE", "CANDIDATE_A", "COMPLETE", "PRAGMATIC_DEFAULT", "NONE", "PRAGMATIC_DEFAULT", "CANDIDATE_A", "COMPLETE"),
    JointCase("JP01", "PRAGMATIC_PREFERENCE", "REOPEN", "A support platform closed 360000 tickets for 98000 customers. Report support workload as one number.", "closed-ticket count", "distinct customer count", "NONE", "NONE", "COMPLETE", "PRAGMATIC_DEFAULT", "NONE", "PRAGMATIC_DEFAULT", "CANDIDATE_A", "COMPLETE"),
    JointCase("JP02", "PRAGMATIC_PREFERENCE", "REOPEN", "An outreach service made 410000 contacts with 126000 customers. Report customer reach as one number.", "contact-event count", "distinct customer count", "NONE", "NONE", "COMPLETE", "PRAGMATIC_DEFAULT", "NONE", "PRAGMATIC_DEFAULT", "CANDIDATE_B", "COMPLETE"),
    JointCase("JP03", "PRAGMATIC_PREFERENCE", "REOPEN", "A marketplace processed 840000 purchases across 53000 active sellers. Report the active marketplace footprint as one number.", "purchase-event count", "distinct active-seller count", "NONE", "CANDIDATE_A", "COMPLETE", "PRAGMATIC_DEFAULT", "NONE", "PRAGMATIC_DEFAULT", "CANDIDATE_B", "COMPLETE"),
    JointCase("JP04", "PRAGMATIC_PREFERENCE", "PRESERVE", "A freight hub handled 620000 shipments for 13000 clients. Report freight volume as one number.", "shipment count", "distinct client count", "NONE", "CANDIDATE_A", "COMPLETE", "PRAGMATIC_DEFAULT", "NONE", "PRAGMATIC_DEFAULT", "CANDIDATE_A", "COMPLETE"),
    JointCase("JP05", "PRAGMATIC_PREFERENCE", "PRESERVE", "A learning program logged 97000 attendances by 26000 learners. Report learner participation as one number.", "attendance-event count", "distinct learner count", "NONE", "CANDIDATE_B", "COMPLETE", "PRAGMATIC_DEFAULT", "NONE", "PRAGMATIC_DEFAULT", "CANDIDATE_B", "COMPLETE"),
    JointCase("JP06", "PRAGMATIC_PREFERENCE", "PRESERVE", "A repair network closed 141000 work orders for 69000 devices. The request explicitly gives no preference between the measures.", "closed-work-order count", "distinct device count", "NONE", "NONE", "COMPLETE", "NO_PREFERENCE", "NONE", "NO_PREFERENCE", "NONE", "COMPLETE"),
    JointCase("JC01", "AXIS_ASSESSMENT_COMPLETE", "REOPEN", "A museum issued 88000 admissions to 59000 visitors. The brief explicitly leaves both measures open and gives neither a preference.", "admission-event count", "distinct visitor count", "NONE", "NONE", "INCOMPLETE", "NO_PREFERENCE", "NONE", "NO_PREFERENCE", "NONE", "COMPLETE"),
    JointCase("JC02", "AXIS_ASSESSMENT_COMPLETE", "REOPEN", "A scanner completed 122000 scans for 47000 patients. Report the scan count as one integer.", "scan count", "distinct patient count", "CANDIDATE_A", "CANDIDATE_A", "INCOMPLETE", "LEXICAL_EXACT", "CANDIDATE_A", "LEXICAL_EXACT", "CANDIDATE_A", "COMPLETE"),
    JointCase("JC03", "AXIS_ASSESSMENT_COMPLETE", "REOPEN", "A community program logged 76000 attendances by 22000 residents. Report community participation as one number.", "attendance-event count", "distinct resident count", "NONE", "CANDIDATE_B", "UNCERTAIN", "PRAGMATIC_DEFAULT", "NONE", "PRAGMATIC_DEFAULT", "CANDIDATE_B", "COMPLETE"),
    JointCase("JC04", "AXIS_ASSESSMENT_COMPLETE", "PRESERVE", "A report lists 420000 observations and 170000 records but does not define candidate measure Q or candidate measure R. Choose the requested measure.", "candidate measure Q", "candidate measure R", "UNCERTAIN", "UNCERTAIN", "INCOMPLETE", "UNCERTAIN", "UNCERTAIN", "UNCERTAIN", "UNCERTAIN", "INCOMPLETE"),
    JointCase("JC05", "AXIS_ASSESSMENT_COMPLETE", "PRESERVE", "A licensing office processed 196000 filings from 84000 applicants. The brief explicitly gives no rule or preference between the measures.", "processed-filing count", "distinct applicant count", "NONE", "NONE", "COMPLETE", "NO_PREFERENCE", "NONE", "NO_PREFERENCE", "NONE", "COMPLETE"),
    JointCase("JC06", "AXIS_ASSESSMENT_COMPLETE", "PRESERVE", "A library recorded 380000 loans to 49000 borrowers. Report the distinct borrower count as one integer.", "loan count", "distinct borrower count", "CANDIDATE_B", "CANDIDATE_B", "COMPLETE", "LEXICAL_EXACT", "CANDIDATE_B", "LEXICAL_EXACT", "CANDIDATE_B", "COMPLETE"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])
SPEC_COMMITMENT = {
    "corpus_version": CORPUS_VERSION, "corpus_id": CORPUS_ID,
    "ontology_object": "joint semantic tuple coordination with evidence-priority reopening",
    "case_count": 24, "batch_size": BATCH_SIZE, "case_commitment": CASE_COMMITMENT,
    "target_axis_counts": {axis: 6 for axis in ("SELECTION_BASIS", "SELECTED_OBJECT", "PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE")},
    "target_action_counts_per_axis": {"PRESERVE": 3, "REOPEN_OR_REVISE": 3},
    "construction_labels_are_pre_panel_diagnostics_only": True,
    "matched_counterpart_visible": False, "fresh_from_v0_12": True,
    "real_world_ground_truth_claim": False, "action_credit_authority": False,
    "selection_authority": False, "retention_authority": False, "production_authority": False,
}
CORPUS_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def build_joint_holdout_artifact():
    validate_joint_holdout_spec()
    source_hash = hash_payload({"spec_hash": CORPUS_SPEC["spec_hash"], "case_commitment": CASE_COMMITMENT})
    ordered = sorted(CASES, key=lambda case: hash_payload([CORPUS_VERSION, case.case_id]))
    bindings, batches = {}, []
    for offset in range(0, len(ordered), BATCH_SIZE):
        items = []
        for case in ordered[offset:offset + BATCH_SIZE]:
            blind_id = "joint-fresh-" + hash_payload([CORPUS_VERSION, source_hash, case.case_id])[:18]
            public = {
                "conflict_id": blind_id, "public_prompt": case.public_prompt,
                "candidate_a": case.candidate_a, "candidate_b": case.candidate_b,
                "locked_consensus_axes": {"SELECTED_OBJECT": case.locked_selected, "PRAGMATIC_PREFERENCE": case.locked_preference, "AXIS_ASSESSMENT_COMPLETE": case.locked_completeness},
                "consensus_support": {"independent_positions": 2, "agreement": "UNANIMOUS"},
                "local_basis_outcome": {"selection_basis": case.local_basis, "independent_positions": 1},
            }
            truth = {"SELECTED_OBJECT": case.truth_selected, "SELECTION_BASIS": case.truth_basis, "PRAGMATIC_PREFERENCE": case.truth_preference, "AXIS_ASSESSMENT_COMPLETE": case.truth_completeness}
            bindings[blind_id] = {"case_id": case.case_id, "target_axis": case.target_axis, "target_action": case.target_action, "construction_truth": truth, "case_commitment": hash_payload(public)}
            items.append(public)
        batches.append({"batch_id": f"joint-fresh-batch-{len(batches) + 1:02d}", "conflicts": items})
    surface_commitment = {"surface_version": "clarification_joint_surface_v0_13", "source_hash": source_hash, "batches": batches, "construction_exposed": False, "oracle_exposed": False}
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    oracle_commitment = {"oracle_version": "clarification_joint_oracle_v0_13", "surface_hash": surface["surface_hash"], "bindings": bindings, "construction_labels_are_pre_panel_diagnostics_only": True}
    oracle = {**oracle_commitment, "oracle_hash": hash_payload(oracle_commitment)}
    commitment = {"artifact_version": "clarification_joint_source_v0_13", "corpus_spec": CORPUS_SPEC, "public_surface": surface, "private_oracle": oracle, "evidence_refs": list(EVIDENCE_REFS)}
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_joint_holdout_artifact(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_joint_holdout_artifact():
        raise ValueError("clarification_joint_holdout_artifact_invalid")


def validate_joint_holdout_spec(*, cases=CASES, spec=CORPUS_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    axes = ("SELECTION_BASIS", "SELECTED_OBJECT", "PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE")
    if spec.get("spec_hash") != hash_payload(commitment) or tuple(cases) != CASES or len(cases) != 24 or any(sum(case.target_axis == axis for case in cases) != 6 for axis in axes):
        raise ValueError("clarification_joint_holdout_spec_invalid")
    for axis in axes:
        group = [case for case in cases if case.target_axis == axis]
        preserve = sum(case.target_action == "PRESERVE" for case in group)
        if preserve != 3:
            raise ValueError("clarification_joint_holdout_action_balance_invalid")
