"""Fresh public micro-worlds and private v0.3B relation references."""

from __future__ import annotations

from dataclasses import dataclass


STATE_TO_ACTION = {
    "INDEPENDENT_DISTINCT": "COMBINE",
    "EXACT_DUPLICATE": "DEDUPE_AND_COMBINE",
    "DEPENDENT_DISTINCT": "BLOCK",
    "PARTIAL_OVERLAP": "BLOCK",
    "SCOPE_INCOMPATIBLE": "BLOCK",
    "UNRESOLVED": "BLOCK",
}


@dataclass(frozen=True)
class SemanticCase:
    case_id: str
    target_scope: str
    left_packet_id: str
    left_descriptor: str
    left_evidence_ref: str
    right_packet_id: str
    right_descriptor: str
    right_evidence_ref: str
    private_relation_state: str

    @property
    def evidence_refs(self) -> tuple[str, str]:
        return (self.left_evidence_ref, self.right_evidence_ref)

    @property
    def private_action(self) -> str:
        return STATE_TO_ACTION[self.private_relation_state]

    def public_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "target_scope": self.target_scope,
            "left_packet": {
                "packet_id": self.left_packet_id,
                "descriptor": self.left_descriptor,
                "evidence_ref": self.left_evidence_ref,
            },
            "right_packet": {
                "packet_id": self.right_packet_id,
                "descriptor": self.right_descriptor,
                "evidence_ref": self.right_evidence_ref,
            },
        }


CASES = (
    SemanticCase(
        "R43B-01",
        "Whether pump M is currently in cavitation state C.",
        "L01",
        "A pressure sensor measures inlet pressure. Its noise source, clock, "
        "calibration chain, and samples are independent of the acoustic sensor "
        "after conditioning on the pump state.",
        "descriptor://R43B-01/pressure",
        "R01",
        "An acoustic sensor measures blade-frequency energy. It uses a separate "
        "clock, calibration chain, and sample path, with independent noise after "
        "conditioning on the same pump state.",
        "descriptor://R43B-01/acoustic",
        "INDEPENDENT_DISTINCT",
    ),
    SemanticCase(
        "R43B-02",
        "Whether treatment T changes biomarker B in population P.",
        "L02",
        "One laboratory analyzes a randomized cohort drawn from sites A and B. "
        "No subject, specimen, operator, assay lot, or preprocessing artifact is "
        "shared with the second cohort.",
        "descriptor://R43B-02/cohort-ab",
        "R02",
        "A different laboratory analyzes an independently randomized cohort from "
        "sites C and D. The two cohorts and measurement pipelines are disjoint "
        "after conditioning on treatment assignment and biomarker state.",
        "descriptor://R43B-02/cohort-cd",
        "INDEPENDENT_DISTINCT",
    ),
    SemanticCase(
        "R43B-03",
        "Whether alloy batch Q exceeded impurity threshold I.",
        "L03",
        "The packet cites raw assay file assay-Q-17.csv with checksum 91af. It "
        "reports the impurity result from that file.",
        "descriptor://R43B-03/assay-primary",
        "R03",
        "The packet cites backup/renamed-Q.csv with checksum 91af. The archive "
        "manifest states it is a byte-for-byte mirror of assay-Q-17.csv.",
        "descriptor://R43B-03/assay-mirror",
        "EXACT_DUPLICATE",
    ),
    SemanticCase(
        "R43B-04",
        "Whether witness W observed event E.",
        "L04",
        "A memo quotes transcript lines 44-61 from recording REC-204 and treats "
        "them as the witness account.",
        "descriptor://R43B-04/memo",
        "R04",
        "A review note reproduces the same transcript lines 44-61 from recording "
        "REC-204. It adds no second interview or observation.",
        "descriptor://R43B-04/review-note",
        "EXACT_DUPLICATE",
    ),
    SemanticCase(
        "R43B-05",
        "Whether service S breached latency objective L.",
        "L05",
        "The packet reports the mean latency computed from request rows in log "
        "partition shard-8 during minute 32.",
        "descriptor://R43B-05/mean",
        "R05",
        "The packet reports the count above 400 ms computed from the same request "
        "rows in shard-8 during minute 32. It is a different statistic derived "
        "from the same observations.",
        "descriptor://R43B-05/threshold-count",
        "DEPENDENT_DISTINCT",
    ),
    SemanticCase(
        "R43B-06",
        "Whether image set V contains defect D.",
        "L06",
        "Classifier A was trained on bootstrap sample BS-9 and uses shared feature "
        "extractor FE-2 before its own output head.",
        "descriptor://R43B-06/model-a",
        "R06",
        "Classifier B was trained on the same bootstrap sample BS-9 and uses the "
        "same feature extractor FE-2, but has a separately fitted output head.",
        "descriptor://R43B-06/model-b",
        "DEPENDENT_DISTINCT",
    ),
    SemanticCase(
        "R43B-07",
        "Whether users in region R prefer interface N.",
        "L07",
        "Survey packet A summarizes respondents U001-U100.",
        "descriptor://R43B-07/survey-a",
        "R07",
        "Survey packet B summarizes respondents U041-U140. Sixty respondents are "
        "also present in packet A, while forty are new.",
        "descriptor://R43B-07/survey-b",
        "PARTIAL_OVERLAP",
    ),
    SemanticCase(
        "R43B-08",
        "Whether intervention J reduces outcome O.",
        "L08",
        "The packet reports trial TR-77 as a standalone randomized study.",
        "descriptor://R43B-08/trial",
        "R08",
        "The packet reports a three-trial pooled estimate containing TR-77, "
        "TR-81, and TR-95. Only one component is shared with the first packet.",
        "descriptor://R43B-08/meta-analysis",
        "PARTIAL_OVERLAP",
    ),
    SemanticCase(
        "R43B-09",
        "Whether dosage rule D is effective for children aged 6-11.",
        "L09",
        "The packet studies adults aged 35-60 and explicitly excludes minors.",
        "descriptor://R43B-09/adult-study",
        "R09",
        "The packet studies children aged 6-11 under the target dosage rule.",
        "descriptor://R43B-09/child-study",
        "SCOPE_INCOMPATIBLE",
    ),
    SemanticCase(
        "R43B-10",
        "Whether the 2025 revised manufacturing process meets yield target Y.",
        "L10",
        "The packet measures the superseded 2022 process before the reactor and "
        "feedstock changes introduced in 2025.",
        "descriptor://R43B-10/legacy-process",
        "R10",
        "The packet measures the revised 2025 process under the target reactor "
        "and feedstock configuration.",
        "descriptor://R43B-10/current-process",
        "SCOPE_INCOMPATIBLE",
    ),
    SemanticCase(
        "R43B-11",
        "Whether exposure X is associated with outcome Y.",
        "L11",
        "Report A says its records came from a regional registry but suppresses "
        "registry name, subject IDs, dates, and sampling log.",
        "descriptor://R43B-11/report-a",
        "R11",
        "Report B also says regional registry data were used. Its registry name, "
        "subject IDs, dates, and sampling log are likewise unavailable, so shared "
        "records cannot be confirmed or excluded.",
        "descriptor://R43B-11/report-b",
        "UNRESOLVED",
    ),
    SemanticCase(
        "R43B-12",
        "Whether policy K changed migration rate M.",
        "L12",
        "Packet A summarizes an unnamed administrative extract. The extraction "
        "window and row identifiers are missing.",
        "descriptor://R43B-12/extract-a",
        "R12",
        "Packet B summarizes another unnamed administrative extract. Available "
        "metadata do not establish whether its rows are disjoint, identical, or "
        "partially overlapping with packet A.",
        "descriptor://R43B-12/extract-b",
        "UNRESOLVED",
    ),
)
