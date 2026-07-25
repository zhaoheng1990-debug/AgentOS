"""Fresh hard synthetic relation corpus for R4 v0.3E."""

from __future__ import annotations

from dataclasses import dataclass

from .semantic_cases import STATE_TO_ACTION


@dataclass(frozen=True)
class HardRelationCase:
    case_id: str
    domain: str
    target_scope: str
    left_packet_id: str
    left_descriptor: str
    left_evidence_ref: str
    right_packet_id: str
    right_descriptor: str
    right_evidence_ref: str
    private_relation_state: str
    private_adjudication_basis: str
    private_ruled_out_neighbor: str | None
    private_compatible_states: tuple[str, ...] = ()

    @property
    def evidence_refs(self) -> tuple[str, str]:
        return (self.left_evidence_ref, self.right_evidence_ref)

    @property
    def private_action(self) -> str:
        return STATE_TO_ACTION[self.private_relation_state]

    def public_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "domain": self.domain,
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


HARD_CASES = (
    HardRelationCase(
        "R43E-01",
        "astronomy",
        "Whether transient source Z emitted during interval N.",
        "OPT-31",
        "A Chilean optical telescope recorded photons in interval N. Its "
        "detector, acquisition host, clock, and calibration files were used "
        "only by that observatory.",
        "descriptor://R43E-01/optical",
        "RAD-88",
        "An Australian radio array recorded a pulse in interval N. It used its "
        "own antennas, acquisition hosts, clock, and calibrator observations; "
        "no optical files entered its processing.",
        "descriptor://R43E-01/radio",
        "INDEPENDENT_DISTINCT",
        "The observation units and complete acquisition lineages are separate.",
        "DEPENDENT_DISTINCT",
    ),
    HardRelationCase(
        "R43E-02",
        "manufacturing",
        "Whether heat treatment H raised hardness in alloy lot L.",
        "MET-12",
        "Lab North measured coupons L-N01 through L-N12 with tester TN. The "
        "coupons, operator, calibration block, and result files stayed at Lab "
        "North.",
        "descriptor://R43E-02/north",
        "MET-29",
        "Lab South measured coupons L-S01 through L-S12 with tester TS. Its "
        "operator, calibration block, and files were not used at Lab North.",
        "descriptor://R43E-02/south",
        "INDEPENDENT_DISTINCT",
        "The two packet lineages share only the target lot and use separate "
        "coupons and measurement chains.",
        "DEPENDENT_DISTINCT",
    ),
    HardRelationCase(
        "R43E-03",
        "agronomy",
        "Whether seed treatment Q changes germination rate.",
        "AGR-41",
        "Station A randomized seeds from lot Q-A across trays A01-A20 and "
        "counted sprouts with camera CA. Its trays, seed lot, camera, and "
        "annotation files remained at Station A.",
        "descriptor://R43E-03/station-a",
        "AGR-73",
        "Station B randomized seeds from lot Q-B across trays B01-B20 and "
        "counted sprouts with camera CB. No trays, seeds, images, or annotators "
        "were used by both stations.",
        "descriptor://R43E-03/station-b",
        "INDEPENDENT_DISTINCT",
        "Distinct seed lots, trays, imaging, and annotation paths support "
        "separate observations of the target effect.",
        "DEPENDENT_DISTINCT",
    ),
    HardRelationCase(
        "R43E-04",
        "legal records",
        "What statement appears in filing F at paragraph 27.",
        "LAW-06",
        "The packet quotes paragraph 27 from filing object F-2026-114 whose "
        "repository digest is 4d91.",
        "descriptor://R43E-04/filing",
        "LAW-22",
        "The packet quotes paragraph 27 from a renamed archive object with "
        "repository digest 4d91; the archive map points that object to "
        "F-2026-114.",
        "descriptor://R43E-04/archive",
        "EXACT_DUPLICATE",
        "Both packets point to one immutable filing object and paragraph.",
        "DEPENDENT_DISTINCT",
    ),
    HardRelationCase(
        "R43E-05",
        "genomics",
        "Which bases occur in sequencing read R.",
        "GEN-17",
        "The packet reads record R from run file lane7.fastq, content digest "
        "8bc2.",
        "descriptor://R43E-05/fastq",
        "GEN-44",
        "The packet reads record R from lane7-copy.fastq.gz after decompression; "
        "the resulting content digest is 8bc2.",
        "descriptor://R43E-05/compressed",
        "EXACT_DUPLICATE",
        "Compression and renaming preserve one underlying read record.",
        "DEPENDENT_DISTINCT",
    ),
    HardRelationCase(
        "R43E-06",
        "spacecraft telemetry",
        "What temperature was reported by probe P at frame 781.",
        "TEL-09",
        "The packet reports the raw sensor code in telemetry frame 781 from "
        "probe P.",
        "descriptor://R43E-06/raw",
        "TEL-64",
        "The packet converts the sensor code from telemetry frame 781 into "
        "degrees Celsius using calibration table C4; it cites no other frame.",
        "descriptor://R43E-06/converted",
        "EXACT_DUPLICATE",
        "Both values are representations of the one sensor observation in frame "
        "781.",
        "DEPENDENT_DISTINCT",
    ),
    HardRelationCase(
        "R43E-07",
        "financial reporting",
        "Whether company C improved operating performance in quarter Q.",
        "FIN-18",
        "The packet calculates revenue growth from ledger rows Q-001 through "
        "Q-940 after the quarter close.",
        "descriptor://R43E-07/growth",
        "FIN-52",
        "The packet calculates operating margin from the full set of ledger rows "
        "Q-001 through Q-940 after the same close.",
        "descriptor://R43E-07/margin",
        "DEPENDENT_DISTINCT",
        "Different quantities inherit the complete same ledger population and "
        "close process.",
        "EXACT_DUPLICATE",
    ),
    HardRelationCase(
        "R43E-08",
        "ecology",
        "Whether restoration changed the condition of wetland W.",
        "ECO-25",
        "The packet computes species richness from quadrat records W01 through "
        "W80 collected in the spring survey.",
        "descriptor://R43E-08/richness",
        "ECO-61",
        "The packet computes total dry biomass from every one of quadrat records "
        "W01 through W80 from that survey.",
        "descriptor://R43E-08/biomass",
        "DEPENDENT_DISTINCT",
        "Distinct ecological quantities use the complete same observation units.",
        "EXACT_DUPLICATE",
    ),
    HardRelationCase(
        "R43E-09",
        "education analytics",
        "Whether course design D affected student outcomes.",
        "EDU-33",
        "The packet estimates the final-score mean from student rows S001 "
        "through S240.",
        "descriptor://R43E-09/score",
        "EDU-70",
        "The packet estimates withdrawal frequency from the complete set of "
        "student rows S001 through S240.",
        "descriptor://R43E-09/withdrawal",
        "DEPENDENT_DISTINCT",
        "Different outcomes are functions of one complete student cohort.",
        "EXACT_DUPLICATE",
    ),
    HardRelationCase(
        "R43E-10",
        "patent analytics",
        "Whether portfolio P covers technology family T.",
        "PAT-11",
        "The packet summarizes patent records P001 through P080.",
        "descriptor://R43E-10/set-a",
        "PAT-48",
        "The packet summarizes patent records P061 through P120.",
        "descriptor://R43E-10/set-b",
        "PARTIAL_OVERLAP",
        "Records P061-P080 occur in both packets, while each packet also has "
        "records absent from the other.",
        "DEPENDENT_DISTINCT",
    ),
    HardRelationCase(
        "R43E-11",
        "clinical operations",
        "Whether clinic K met its specimen turnaround target.",
        "CLI-14",
        "The packet uses specimen IDs K1001 through K1060.",
        "descriptor://R43E-11/early",
        "CLI-57",
        "The packet uses specimen IDs K1046 through K1105.",
        "descriptor://R43E-11/late",
        "PARTIAL_OVERLAP",
        "Fifteen specimen IDs occur in both sets and forty-five in each set occur "
        "only once.",
        "DEPENDENT_DISTINCT",
    ),
    HardRelationCase(
        "R43E-12",
        "remote sensing",
        "Whether flood extent increased within basin B.",
        "SAT-20",
        "The packet aggregates map tiles B-01 through B-54.",
        "descriptor://R43E-12/west",
        "SAT-69",
        "The packet aggregates map tiles B-45 through B-96.",
        "descriptor://R43E-12/east",
        "PARTIAL_OVERLAP",
        "Tiles B-45-B-54 are present in both aggregates and both also contain "
        "unique tiles.",
        "DEPENDENT_DISTINCT",
    ),
    HardRelationCase(
        "R43E-13",
        "battery testing",
        "Whether cell chemistry C meets the target at 20 degrees Celsius.",
        "BAT-07",
        "The packet measures chemistry C during a chamber run held at minus 20 "
        "degrees Celsius.",
        "descriptor://R43E-13/cold",
        "BAT-38",
        "The packet measures chemistry C during a chamber run held at 20 degrees "
        "Celsius.",
        "descriptor://R43E-13/target",
        "SCOPE_INCOMPATIBLE",
        "The cold-chamber observation is outside the target temperature.",
        "DEPENDENT_DISTINCT",
    ),
    HardRelationCase(
        "R43E-14",
        "software reliability",
        "Whether release 5.2 satisfies the crash-rate objective.",
        "SRE-16",
        "The packet reports crash sessions from release 4.8 before the memory "
        "allocator replacement.",
        "descriptor://R43E-14/legacy",
        "SRE-63",
        "The packet reports crash sessions from release 5.2 after the allocator "
        "replacement.",
        "descriptor://R43E-14/current",
        "SCOPE_INCOMPATIBLE",
        "Release 4.8 is not the target configuration and precedes a material "
        "implementation change.",
        "DEPENDENT_DISTINCT",
    ),
    HardRelationCase(
        "R43E-15",
        "regulatory policy",
        "Whether rule J changed reporting behavior among firms registered in the "
        "European Union.",
        "REG-28",
        "The packet studies firms registered only in Canada under Canadian "
        "reporting rules.",
        "descriptor://R43E-15/canada",
        "REG-81",
        "The packet studies firms registered in the European Union under rule J.",
        "descriptor://R43E-15/eu",
        "SCOPE_INCOMPATIBLE",
        "The Canadian firm population and reporting regime fall outside the "
        "target jurisdiction.",
        "DEPENDENT_DISTINCT",
    ),
    HardRelationCase(
        "R43E-16",
        "museum provenance",
        "Whether object O was present in collection C before 1950.",
        "MUS-19",
        "The packet cites an inventory extract labeled North Store. The catalog "
        "number, scan identifier, page range, and transcription lineage are not "
        "provided.",
        "descriptor://R43E-16/north",
        "MUS-74",
        "The packet cites an inventory extract labeled Reserve. Its catalog "
        "number, scan identifier, page range, and transcription lineage are "
        "also not provided.",
        "descriptor://R43E-16/reserve",
        "UNRESOLVED",
        "The public metadata cannot establish whether the extracts use the same "
        "inventory entries, intersecting entries, or separate entries.",
        None,
        ("EXACT_DUPLICATE", "PARTIAL_OVERLAP", "INDEPENDENT_DISTINCT"),
    ),
    HardRelationCase(
        "R43E-17",
        "industrial sensing",
        "Whether line X experienced excessive vibration during shift S.",
        "SNS-23",
        "The packet summarizes an export named shift-summary-1. Device IDs, "
        "sampling times, and aggregation windows are absent.",
        "descriptor://R43E-17/export-1",
        "SNS-58",
        "The packet summarizes an export named shift-summary-2. It also omits "
        "device IDs, sampling times, and aggregation windows.",
        "descriptor://R43E-17/export-2",
        "UNRESOLVED",
        "The exports may use the same readings, intersecting windows, or separate "
        "devices and times.",
        None,
        ("EXACT_DUPLICATE", "PARTIAL_OVERLAP", "INDEPENDENT_DISTINCT"),
    ),
    HardRelationCase(
        "R43E-18",
        "literature synthesis",
        "Whether intervention V changes outcome Y.",
        "LIT-35",
        "The packet summarizes three unnamed studies but gives no authors, "
        "registry identifiers, sample sizes, or study dates.",
        "descriptor://R43E-18/summary-a",
        "LIT-92",
        "The packet summarizes two unnamed studies and likewise omits authors, "
        "registry identifiers, sample sizes, and study dates.",
        "descriptor://R43E-18/summary-b",
        "UNRESOLVED",
        "The metadata cannot establish whether the study sets are separate, "
        "identical in part, or derived from the same registrations.",
        None,
        ("DEPENDENT_DISTINCT", "PARTIAL_OVERLAP", "INDEPENDENT_DISTINCT"),
    ),
)

