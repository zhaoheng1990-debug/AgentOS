"""Fresh hidden-reference corpus for R4 v0.3G."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ATTRIBUTE_NAMES = (
    "source_identity",
    "lineage_coupling",
    "information_relation",
    "added_uncertainty",
    "target_claim_relation",
)


@dataclass(frozen=True)
class InferenceCase:
    case_id: str
    target_claim: str
    evidence: tuple[tuple[str, str], ...]
    expected_attributes: tuple[tuple[str, str], ...]
    expected_attribute_refs: tuple[tuple[str, tuple[str, ...]], ...]
    expected_relation_state: str
    expected_action: str
    true_missing_attributes: tuple[str, ...] = ()

    def public_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "target_claim": self.target_claim,
            "evidence": [
                {"evidence_ref": ref, "statement": statement}
                for ref, statement in self.evidence
            ],
        }

    def attributes(self) -> dict[str, str]:
        return dict(self.expected_attributes)

    def attribute_refs(self) -> dict[str, tuple[str, ...]]:
        return dict(self.expected_attribute_refs)

    @property
    def evidence_refs(self) -> tuple[str, ...]:
        return tuple(ref for ref, _ in self.evidence)


def _case(
    case_id: str,
    target_claim: str,
    statements: dict[str, str],
    attributes: dict[str, str],
    refs: dict[str, tuple[str, ...]],
    relation: str,
    action: str,
    missing: tuple[str, ...] = (),
) -> InferenceCase:
    return InferenceCase(
        case_id=case_id,
        target_claim=target_claim,
        evidence=tuple(
            (f"evidence://{case_id.lower()}/{key}", value)
            for key, value in statements.items()
        ),
        expected_attributes=tuple((name, attributes[name]) for name in ATTRIBUTE_NAMES),
        expected_attribute_refs=tuple(
            (
                name,
                tuple(
                    f"evidence://{case_id.lower()}/{key}" for key in refs[name]
                ),
            )
            for name in ATTRIBUTE_NAMES
        ),
        expected_relation_state=relation,
        expected_action=action,
        true_missing_attributes=missing,
    )


INFERENCE_CASES = (
    _case(
        "R43G-01",
        "Whether spindle S stayed below 2.0 volts during sample 44.",
        {
            "source": "Both packets encode the same sample 44 from spindle S.",
            "lineage": "Packet B is computed directly from packet A.",
            "transform": "Packet B converts microvolts to volts by the exact factor 1,000,000; the conversion is reversible.",
            "uncertainty": "The conversion adds no measurement uncertainty.",
            "tolerance": "The claim tolerance is 0.01 volts.",
            "target": "Both packets are assessed only for the stated voltage-threshold claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "information_relation": "VERIFIED_GLOBAL_EQUIVALENCE",
            "added_uncertainty": "IMMATERIAL_FOR_CLAIM",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
        {
            "source_identity": ("source",),
            "lineage_coupling": ("lineage",),
            "information_relation": ("transform",),
            "added_uncertainty": ("uncertainty", "tolerance"),
            "target_claim_relation": ("target",),
        },
        "EXACT_DUPLICATE",
        "DEDUPE_AND_COMBINE",
    ),
    _case(
        "R43G-02",
        "Whether spindle T stayed below 2.0 volts during sample 45.",
        {
            "source": "Both packets encode the same sample 45 from spindle T.",
            "lineage": "Packet B is computed directly from packet A.",
            "transform": "Packet B applies the registered voltage calibration to packet A.",
            "uncertainty": "Calibration can shift the reported value by 0.08 volts.",
            "tolerance": "The claim tolerance is 0.01 volts.",
            "target": "Both packets are assessed only for the stated voltage-threshold claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "information_relation": "VERIFIED_CLAIM_EQUIVALENCE",
            "added_uncertainty": "MATERIAL_FOR_CLAIM",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
        {
            "source_identity": ("source",),
            "lineage_coupling": ("lineage",),
            "information_relation": ("transform",),
            "added_uncertainty": ("uncertainty", "tolerance"),
            "target_claim_relation": ("target",),
        },
        "DEPENDENT_DISTINCT",
        "BLOCK",
    ),
    _case(
        "R43G-03",
        "The daily rainfall total at station M on day 17.",
        {
            "source": "Both packets reproduce the same station M day-17 observation.",
            "lineage": "Packet B is a direct transformation of packet A.",
            "transform": "Millimetres are converted to inches with an exact reversible scale factor.",
            "uncertainty": "No uncertainty is added by the unit conversion.",
            "tolerance": "The claim tolerance is 0.001 inches.",
            "target": "Both packets answer the same daily-total claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "information_relation": "VERIFIED_GLOBAL_EQUIVALENCE",
            "added_uncertainty": "IMMATERIAL_FOR_CLAIM",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
        {
            "source_identity": ("source",),
            "lineage_coupling": ("lineage",),
            "information_relation": ("transform",),
            "added_uncertainty": ("uncertainty", "tolerance"),
            "target_claim_relation": ("target",),
        },
        "EXACT_DUPLICATE",
        "DEDUPE_AND_COMBINE",
    ),
    _case(
        "R43G-04",
        "Packet A estimates daily rainfall, while packet B is used to identify the instrument model.",
        {
            "source": "Both packets originate from the same station M day-18 record.",
            "lineage": "Packet B is a direct reversible unit conversion of packet A.",
            "transform": "The conversion preserves the complete numeric observation.",
            "uncertainty": "No uncertainty is added by the conversion.",
            "tolerance": "Each stated use has a 0.001-inch numeric tolerance.",
            "target": "Packet A supports a rainfall-total claim; packet B is being used for a different instrument-identity claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "information_relation": "VERIFIED_GLOBAL_EQUIVALENCE",
            "added_uncertainty": "IMMATERIAL_FOR_CLAIM",
            "target_claim_relation": "DIFFERENT_TARGET_CLAIM",
        },
        {
            "source_identity": ("source",),
            "lineage_coupling": ("lineage",),
            "information_relation": ("transform",),
            "added_uncertainty": ("uncertainty", "tolerance"),
            "target_claim_relation": ("target",),
        },
        "SCOPE_INCOMPATIBLE",
        "BLOCK",
    ),
    _case(
        "R43G-05",
        "The exact byte content of archive object Q.",
        {
            "source": "Both packets represent archive object Q revision 9.",
            "lineage": "Packet B is generated directly from packet A.",
            "transform": "Packet B uses a verified lossless codec and decodes byte-for-byte to packet A.",
            "uncertainty": "No transformation uncertainty applies.",
            "target": "Both packets answer the same exact-content claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "information_relation": "VERIFIED_GLOBAL_EQUIVALENCE",
            "added_uncertainty": "NOT_APPLICABLE",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
        {
            "source_identity": ("source",),
            "lineage_coupling": ("lineage",),
            "information_relation": ("transform",),
            "added_uncertainty": ("uncertainty",),
            "target_claim_relation": ("target",),
        },
        "EXACT_DUPLICATE",
        "DEDUPE_AND_COMBINE",
    ),
    _case(
        "R43G-06",
        "The exact byte content of archive object R.",
        {
            "source": "Both packets originate from archive object R revision 4.",
            "lineage": "Packet B is generated directly from packet A.",
            "transform": "Packet B is a topic summary that omits repeated and low-ranked passages.",
            "uncertainty": "No numeric transformation uncertainty is defined.",
            "target": "Both packets are evaluated against the same exact-content claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "information_relation": "INFORMATION_REDUCING",
            "added_uncertainty": "NOT_APPLICABLE",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
        {
            "source_identity": ("source",),
            "lineage_coupling": ("lineage",),
            "information_relation": ("transform",),
            "added_uncertainty": ("uncertainty",),
            "target_claim_relation": ("target",),
        },
        "DEPENDENT_DISTINCT",
        "BLOCK",
    ),
    _case(
        "R43G-07",
        "Whether the reported effect appears in two independent laboratory runs.",
        {
            "source": "Packet A records laboratory U run 81; packet B records laboratory V run 12.",
            "lineage": "The laboratories used separate instruments, operators, and analysis pipelines.",
            "transform": "Neither packet is a transformation of the other.",
            "uncertainty": "No added transformation uncertainty applies.",
            "target": "Both packets address the same replication claim.",
        },
        {
            "source_identity": "DISTINCT_SOURCE",
            "lineage_coupling": "SEPARATE_PIPELINES",
            "information_relation": "NOT_APPLICABLE",
            "added_uncertainty": "NOT_APPLICABLE",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
        {
            "source_identity": ("source",),
            "lineage_coupling": ("lineage",),
            "information_relation": ("transform",),
            "added_uncertainty": ("uncertainty",),
            "target_claim_relation": ("target",),
        },
        "INDEPENDENT_DISTINCT",
        "COMBINE",
    ),
    _case(
        "R43G-08",
        "Whether the reported effect appears in two collected samples.",
        {
            "source": "Packet A records sample 31; packet B records a distinct sample 32.",
            "lineage": "Both packets were produced by the same extraction batch, instrument run, and normalization pipeline.",
            "transform": "Neither packet is a transformation of the other.",
            "uncertainty": "No added transformation uncertainty applies.",
            "target": "Both packets address the same replication claim.",
        },
        {
            "source_identity": "DISTINCT_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "information_relation": "NOT_APPLICABLE",
            "added_uncertainty": "NOT_APPLICABLE",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
        {
            "source_identity": ("source",),
            "lineage_coupling": ("lineage",),
            "information_relation": ("transform",),
            "added_uncertainty": ("uncertainty",),
            "target_claim_relation": ("target",),
        },
        "DEPENDENT_DISTINCT",
        "BLOCK",
    ),
    _case(
        "R43G-09",
        "The distribution represented by the complete municipal survey.",
        {
            "source": "Packet A contains respondents 1-400; packet B contains respondents 1-120 from that same survey.",
            "lineage": "The subset was copied from the full survey without a separate collection pipeline.",
            "transform": "Packet B is a strict subset rather than a transformation of all records.",
            "uncertainty": "No added transformation uncertainty applies.",
            "target": "Both packets address the same survey-distribution claim.",
        },
        {
            "source_identity": "PARTIAL_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "information_relation": "NOT_APPLICABLE",
            "added_uncertainty": "NOT_APPLICABLE",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
        {
            "source_identity": ("source",),
            "lineage_coupling": ("lineage",),
            "information_relation": ("transform",),
            "added_uncertainty": ("uncertainty",),
            "target_claim_relation": ("target",),
        },
        "PARTIAL_OVERLAP",
        "BLOCK",
    ),
    _case(
        "R43G-10",
        "The distribution represented by two undated survey extracts.",
        {
            "source": "The extracts lack survey IDs, respondent IDs, dates, and row-level hashes, so their source relationship cannot be determined.",
            "lineage": "No collection or derivation lineage is available.",
            "transform": "No transformation record is available.",
            "uncertainty": "Transformation uncertainty cannot be determined.",
            "target": "Both extracts are proposed for the same survey-distribution claim.",
        },
        {
            "source_identity": "UNKNOWN_SOURCE",
            "lineage_coupling": "UNKNOWN_PIPELINE",
            "information_relation": "UNVERIFIED_TRANSFORM",
            "added_uncertainty": "UNKNOWN_UNCERTAINTY",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
        {
            "source_identity": ("source",),
            "lineage_coupling": ("lineage",),
            "information_relation": ("transform",),
            "added_uncertainty": ("uncertainty",),
            "target_claim_relation": ("target",),
        },
        "UNRESOLVED",
        "BLOCK",
        (
            "source_identity",
            "lineage_coupling",
            "information_relation",
            "added_uncertainty",
        ),
    ),
    _case(
        "R43G-11",
        "Whether turbine J exceeded 900 revolutions per minute at tick 204.",
        {
            "source": "Both packets describe turbine J at tick 204.",
            "lineage": "Packet B is computed directly from packet A.",
            "transform": "The documented transform converts revolutions per second to revolutions per minute by multiplying by exactly 60.",
            "uncertainty": "The arithmetic adds no uncertainty.",
            "tolerance": "The threshold claim tolerance is 1 revolution per minute.",
            "target": "Both packets address the same threshold claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "information_relation": "VERIFIED_GLOBAL_EQUIVALENCE",
            "added_uncertainty": "IMMATERIAL_FOR_CLAIM",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
        {
            "source_identity": ("source",),
            "lineage_coupling": ("lineage",),
            "information_relation": ("transform",),
            "added_uncertainty": ("uncertainty", "tolerance"),
            "target_claim_relation": ("target",),
        },
        "EXACT_DUPLICATE",
        "DEDUPE_AND_COMBINE",
    ),
    _case(
        "R43G-12",
        "Whether turbine K exceeded 900 revolutions per minute at tick 205.",
        {
            "source": "Both packets describe turbine K at tick 205.",
            "lineage": "Packet B is computed directly from packet A.",
            "transform": "Packet B is labelled as a speed conversion, but its formula and calibration record are not documented.",
            "uncertainty": "A separate comparison establishes that any arithmetic error is below 1 revolution per minute.",
            "tolerance": "The threshold claim tolerance is 1 revolution per minute.",
            "target": "Both packets address the same threshold claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "information_relation": "UNVERIFIED_TRANSFORM",
            "added_uncertainty": "IMMATERIAL_FOR_CLAIM",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
        {
            "source_identity": ("source",),
            "lineage_coupling": ("lineage",),
            "information_relation": ("transform",),
            "added_uncertainty": ("uncertainty", "tolerance"),
            "target_claim_relation": ("target",),
        },
        "UNRESOLVED",
        "BLOCK",
        ("information_relation",),
    ),
)


PAIR_EXPECTATIONS = (
    ("PAIR_UNCERTAINTY", "R43G-01", "R43G-02", ("added_uncertainty",)),
    ("PAIR_TARGET", "R43G-03", "R43G-04", ("target_claim_relation",)),
    ("PAIR_INFORMATION", "R43G-05", "R43G-06", ("information_relation",)),
    ("PAIR_LINEAGE", "R43G-07", "R43G-08", ("lineage_coupling",)),
    (
        "PAIR_SOURCE_KNOWLEDGE",
        "R43G-09",
        "R43G-10",
        ("source_identity",),
    ),
    ("PAIR_TRANSFORM_WITNESS", "R43G-11", "R43G-12", ("information_relation",)),
)

