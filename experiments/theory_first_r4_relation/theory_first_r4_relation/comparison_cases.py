"""Fresh matched legacy/factorized corpus for R4 v0.3J."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SHARED_ATTRIBUTES = (
    "source_identity",
    "lineage_coupling",
    "added_uncertainty",
    "target_claim_relation",
)
LEGACY_ATTRIBUTES = (*SHARED_ATTRIBUTES[:2], "information_relation", *SHARED_ATTRIBUTES[2:])
FACTORIZED_ATTRIBUTES = (
    *SHARED_ATTRIBUTES[:2],
    "transform_status",
    "information_effect",
    *SHARED_ATTRIBUTES[2:],
)
LEGACY_PROJECTION = {
    ("VERIFIED_TRANSFORM", "GLOBAL_EQUIVALENT"): "VERIFIED_GLOBAL_EQUIVALENCE",
    ("VERIFIED_TRANSFORM", "CLAIM_EQUIVALENT"): "VERIFIED_CLAIM_EQUIVALENCE",
    ("VERIFIED_TRANSFORM", "INFORMATION_REDUCING"): "INFORMATION_REDUCING",
    ("VERIFIED_TRANSFORM", "INFORMATION_AUGMENTING"): "INFORMATION_AUGMENTING",
    ("NO_TRANSFORM", "NOT_APPLICABLE"): "NOT_APPLICABLE",
    ("ASSERTED_UNVERIFIED_TRANSFORM", "UNKNOWN_EFFECT"): "UNVERIFIED_TRANSFORM",
    ("UNKNOWN_TRANSFORM_APPLICABILITY", "UNKNOWN_EFFECT"): "UNVERIFIED_TRANSFORM",
}
LEGACY_INVERSE = {
    value: frozenset(pair for pair, projected in LEGACY_PROJECTION.items() if projected == value)
    for value in set(LEGACY_PROJECTION.values())
}
REVALIDATION_BY_STATUS = {
    "VERIFIED_TRANSFORM": "NO_TRANSFORM_STATUS_REVALIDATION",
    "NO_TRANSFORM": "NO_TRANSFORM_RELATION_ESTABLISHED",
    "ASSERTED_UNVERIFIED_TRANSFORM": "VERIFY_ASSERTED_TRANSFORM",
    "UNKNOWN_TRANSFORM_APPLICABILITY": "DISCOVER_TRANSFORM_APPLICABILITY",
}


@dataclass(frozen=True)
class ComparisonCase:
    case_id: str
    target_claim: str
    evidence: tuple[tuple[str, str], ...]
    factorized: tuple[tuple[str, str], ...]

    def public_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "target_claim": self.target_claim,
            "evidence": [
                {"evidence_ref": ref, "statement": statement}
                for ref, statement in self.evidence
            ],
        }

    def factorized_dict(self) -> dict[str, str]:
        return dict(self.factorized)

    def legacy_dict(self) -> dict[str, str]:
        values = self.factorized_dict()
        return {
            "source_identity": values["source_identity"],
            "lineage_coupling": values["lineage_coupling"],
            "information_relation": LEGACY_PROJECTION[
                (values["transform_status"], values["information_effect"])
            ],
            "added_uncertainty": values["added_uncertainty"],
            "target_claim_relation": values["target_claim_relation"],
        }

    @property
    def refs(self) -> tuple[str, ...]:
        return tuple(ref for ref, _ in self.evidence)

    def expected_refs(self, arm: str) -> dict[str, tuple[str, ...]]:
        prefix = f"evidence://{self.case_id.lower()}/"
        common = {
            "source_identity": (prefix + "source",),
            "lineage_coupling": (prefix + "lineage",),
            "added_uncertainty": (
                (prefix + "uncertainty", prefix + "tolerance")
                if self.factorized_dict()["added_uncertainty"]
                in {"IMMATERIAL_FOR_CLAIM", "MATERIAL_FOR_CLAIM"}
                else (prefix + "uncertainty",)
            ),
            "target_claim_relation": (prefix + "target",),
        }
        if arm == "legacy":
            return common | {
                "information_relation": (prefix + "status", prefix + "effect")
            }
        return common | {
            "transform_status": (prefix + "status",),
            "information_effect": (prefix + "effect",),
        }

    @property
    def revalidation(self) -> str:
        return REVALIDATION_BY_STATUS[self.factorized_dict()["transform_status"]]


def _case(
    case_id: str,
    claim: str,
    statements: dict[str, str],
    factorized: dict[str, str],
) -> ComparisonCase:
    return ComparisonCase(
        case_id,
        claim,
        tuple(
            (f"evidence://{case_id.lower()}/{key}", value)
            for key, value in statements.items()
        ),
        tuple((name, factorized[name]) for name in FACTORIZED_ATTRIBUTES),
    )


COMPARISON_CASES = (
    _case(
        "R43J-01",
        "Whether lens A moved less than 4.0 micrometres during exposure 18.",
        {"source": "Both packets encode lens A exposure 18.", "lineage": "Packet B is computed directly from packet A.", "status": "The conversion from nanometres to micrometres is documented and verified over the full numeric domain.", "effect": "The reversible scale conversion preserves every numeric value.", "uncertainty": "The arithmetic adds no uncertainty.", "tolerance": "The claim tolerance is 0.01 micrometres.", "target": "Both packets address the same movement-threshold claim."},
        {"source_identity": "SAME_SOURCE", "lineage_coupling": "SAME_PIPELINE", "transform_status": "VERIFIED_TRANSFORM", "information_effect": "GLOBAL_EQUIVALENT", "added_uncertainty": "IMMATERIAL_FOR_CLAIM", "target_claim_relation": "SAME_TARGET_CLAIM"},
    ),
    _case(
        "R43J-02",
        "Whether any participant in cohort Q was younger than 18.",
        {"source": "Both packets derive from the same cohort Q roster.", "lineage": "Packet B is a redacted rendering of packet A.", "status": "The redaction procedure and retained age field are explicitly documented and verified.", "effect": "Names are removed, but every age value needed for the stated threshold claim is preserved.", "uncertainty": "The redaction adds no uncertainty to age values.", "tolerance": "The claim requires exact integer ages.", "target": "Both packets address only the same under-18 claim."},
        {"source_identity": "SAME_SOURCE", "lineage_coupling": "SAME_PIPELINE", "transform_status": "VERIFIED_TRANSFORM", "information_effect": "CLAIM_EQUIVALENT", "added_uncertainty": "IMMATERIAL_FOR_CLAIM", "target_claim_relation": "SAME_TARGET_CLAIM"},
    ),
    _case(
        "R43J-03",
        "Whether reactor C exceeded 71.0 degrees during interval 9.",
        {"source": "Both packets represent reactor C interval 9.", "lineage": "Packet B applies a verified calibration to packet A.", "status": "The calibration transform is documented and verified for this temperature claim.", "effect": "It preserves the temperature quantity relevant to the stated threshold.", "uncertainty": "Calibration can shift the result by 1.2 degrees.", "tolerance": "The claim tolerance is 0.2 degrees.", "target": "Both packets address the same threshold claim."},
        {"source_identity": "SAME_SOURCE", "lineage_coupling": "SAME_PIPELINE", "transform_status": "VERIFIED_TRANSFORM", "information_effect": "CLAIM_EQUIVALENT", "added_uncertainty": "MATERIAL_FOR_CLAIM", "target_claim_relation": "SAME_TARGET_CLAIM"},
    ),
    _case(
        "R43J-04",
        "The complete sequence of access events in audit stream D.",
        {"source": "Both packets originate from audit stream D.", "lineage": "Packet B is produced from packet A by an audited aggregation job.", "status": "The aggregation transform is documented and verified.", "effect": "Packet B retains daily counts but removes event order and individual records.", "uncertainty": "No numeric transformation uncertainty is defined.", "target": "Both packets are evaluated against the complete-sequence claim."},
        {"source_identity": "SAME_SOURCE", "lineage_coupling": "SAME_PIPELINE", "transform_status": "VERIFIED_TRANSFORM", "information_effect": "INFORMATION_REDUCING", "added_uncertainty": "NOT_APPLICABLE", "target_claim_relation": "SAME_TARGET_CLAIM"},
    ),
    _case(
        "R43J-05",
        "The distribution represented by the full soil survey.",
        {"source": "Packet A contains plots 1-300; packet B contains plots 1-75 from the same survey.", "lineage": "The subset is extracted through the same survey pipeline.", "status": "The subset extraction procedure is documented and verified.", "effect": "The extraction removes 225 plot records.", "uncertainty": "No added transformation uncertainty applies.", "target": "Both packets address the same full-survey distribution claim."},
        {"source_identity": "PARTIAL_SOURCE", "lineage_coupling": "SAME_PIPELINE", "transform_status": "VERIFIED_TRANSFORM", "information_effect": "INFORMATION_REDUCING", "added_uncertainty": "NOT_APPLICABLE", "target_claim_relation": "SAME_TARGET_CLAIM"},
    ),
    _case(
        "R43J-06",
        "The raw spectral observations recorded for compound E.",
        {"source": "Both packets derive from the same compound E spectra.", "lineage": "Packet B is calculated from packet A by the registered scoring pipeline.", "status": "The scoring transform is documented and verified.", "effect": "Packet B adds a model-derived anomaly score not present as a raw observation.", "uncertainty": "No scalar transformation uncertainty is defined.", "target": "Both packets are evaluated against the raw-observation claim."},
        {"source_identity": "SAME_SOURCE", "lineage_coupling": "SAME_PIPELINE", "transform_status": "VERIFIED_TRANSFORM", "information_effect": "INFORMATION_AUGMENTING", "added_uncertainty": "NOT_APPLICABLE", "target_claim_relation": "SAME_TARGET_CLAIM"},
    ),
    _case(
        "R43J-07",
        "Whether two independent observers recorded the same eclipse feature.",
        {"source": "Packet A is observer L's record; packet B is observer M's distinct record.", "lineage": "They used separate instruments, clocks, and reduction pipelines.", "status": "Neither packet is a transformation of the other.", "effect": "No transformation information effect applies.", "uncertainty": "No added transformation uncertainty applies.", "target": "Both packets address the same replication claim."},
        {"source_identity": "DISTINCT_SOURCE", "lineage_coupling": "SEPARATE_PIPELINES", "transform_status": "NO_TRANSFORM", "information_effect": "NOT_APPLICABLE", "added_uncertainty": "NOT_APPLICABLE", "target_claim_relation": "SAME_TARGET_CLAIM"},
    ),
    _case(
        "R43J-08",
        "Whether two wafers show the same defect signature.",
        {"source": "Packet A records wafer 41; packet B records distinct wafer 42.", "lineage": "Both were processed in the same imaging batch and normalization pipeline.", "status": "Neither packet is a transformation of the other.", "effect": "No transformation information effect applies.", "uncertainty": "No added transformation uncertainty applies.", "target": "Both packets address the same defect-signature claim."},
        {"source_identity": "DISTINCT_SOURCE", "lineage_coupling": "SAME_PIPELINE", "transform_status": "NO_TRANSFORM", "information_effect": "NOT_APPLICABLE", "added_uncertainty": "NOT_APPLICABLE", "target_claim_relation": "SAME_TARGET_CLAIM"},
    ),
    _case(
        "R43J-09",
        "Whether normalized table F preserves the original measurement threshold.",
        {"source": "Both packets are asserted to concern table F.", "lineage": "Packet B is claimed to be generated from packet A.", "status": "A normalization transform is asserted, but its formula and verification record are missing.", "effect": "Its information-preservation effect cannot be established.", "uncertainty": "Added uncertainty is unknown.", "target": "Both packets are proposed for the same threshold claim."},
        {"source_identity": "SAME_SOURCE", "lineage_coupling": "SAME_PIPELINE", "transform_status": "ASSERTED_UNVERIFIED_TRANSFORM", "information_effect": "UNKNOWN_EFFECT", "added_uncertainty": "UNKNOWN_UNCERTAINTY", "target_claim_relation": "SAME_TARGET_CLAIM"},
    ),
    _case(
        "R43J-10",
        "Whether two unlabeled exports describe the same inventory quantity.",
        {"source": "The exports share a project folder but lack object IDs and lineage hashes.", "lineage": "No derivation or independence record is available.", "status": "It is unknown whether either export is a transformation of the other.", "effect": "No information effect can be determined until transform applicability is known.", "uncertainty": "Added uncertainty is unknown.", "target": "Both exports are proposed for the same inventory claim."},
        {"source_identity": "UNKNOWN_SOURCE", "lineage_coupling": "UNKNOWN_PIPELINE", "transform_status": "UNKNOWN_TRANSFORM_APPLICABILITY", "information_effect": "UNKNOWN_EFFECT", "added_uncertainty": "UNKNOWN_UNCERTAINTY", "target_claim_relation": "SAME_TARGET_CLAIM"},
    ),
    _case(
        "R43J-11",
        "Packet A supports location while packet B is used to infer device identity.",
        {"source": "Both packets encode the same beacon event.", "lineage": "Packet B is a verified coordinate conversion of packet A.", "status": "The reversible coordinate transform is documented over the full domain.", "effect": "All coordinate information is preserved.", "uncertainty": "Conversion uncertainty is below the stated numeric tolerances.", "tolerance": "Each numeric use has a frozen 0.1 metre tolerance.", "target": "The packets are used for different claims: location versus device identity."},
        {"source_identity": "SAME_SOURCE", "lineage_coupling": "SAME_PIPELINE", "transform_status": "VERIFIED_TRANSFORM", "information_effect": "GLOBAL_EQUIVALENT", "added_uncertainty": "IMMATERIAL_FOR_CLAIM", "target_claim_relation": "DIFFERENT_TARGET_CLAIM"},
    ),
    _case(
        "R43J-12",
        "Whether two passages from dossier G provide the same factual support.",
        {"source": "Both packets cite dossier G but refer to different passages.", "lineage": "Neither passage is derived from the other.", "status": "No transformation relation is established between the passages.", "effect": "No transformation information effect applies.", "uncertainty": "No added transformation uncertainty applies.", "target": "Both passages are proposed for the same factual claim."},
        {"source_identity": "SAME_SOURCE", "lineage_coupling": "NOT_APPLICABLE", "transform_status": "NO_TRANSFORM", "information_effect": "NOT_APPLICABLE", "added_uncertainty": "NOT_APPLICABLE", "target_claim_relation": "SAME_TARGET_CLAIM"},
    ),
)


FORWARD_ORDER = tuple(case.case_id for case in COMPARISON_CASES)
REVERSE_ORDER = tuple(reversed(FORWARD_ORDER))
