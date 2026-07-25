"""Fresh responsibility-decomposition corpus for R4 v0.3K."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .comparison_cases import REVALIDATION_BY_STATUS


PROVENANCE_ATTRIBUTES = (
    "source_identity",
    "lineage_coupling",
    "transform_status",
)
EFFECT_ATTRIBUTES = (
    "information_effect",
    "added_uncertainty",
    "target_claim_relation",
)
WIDE_ATTRIBUTES = PROVENANCE_ATTRIBUTES + EFFECT_ATTRIBUTES


@dataclass(frozen=True)
class RoleCase:
    case_id: str
    category: str
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

    @property
    def refs(self) -> tuple[str, ...]:
        return tuple(ref for ref, _ in self.evidence)

    def expected_refs(
        self, attributes: tuple[str, ...] = WIDE_ATTRIBUTES
    ) -> dict[str, tuple[str, ...]]:
        prefix = f"evidence://{self.case_id.lower()}/"
        uncertainty = self.factorized_dict()["added_uncertainty"]
        all_refs = {
            "source_identity": (prefix + "source",),
            "lineage_coupling": (prefix + "lineage",),
            "transform_status": (prefix + "status",),
            "information_effect": (prefix + "effect",),
            "added_uncertainty": (
                (prefix + "uncertainty", prefix + "tolerance")
                if uncertainty in {"IMMATERIAL_FOR_CLAIM", "MATERIAL_FOR_CLAIM"}
                else (prefix + "uncertainty",)
            ),
            "target_claim_relation": (prefix + "target",),
        }
        return {name: all_refs[name] for name in attributes}

    @property
    def revalidation(self) -> str:
        return REVALIDATION_BY_STATUS[
            self.factorized_dict()["transform_status"]
        ]


def _case(
    case_id: str,
    category: str,
    claim: str,
    statements: dict[str, str],
    factorized: dict[str, str],
) -> RoleCase:
    return RoleCase(
        case_id=case_id,
        category=category,
        target_claim=claim,
        evidence=tuple(
            (f"evidence://{case_id.lower()}/{key}", value)
            for key, value in statements.items()
        ),
        factorized=tuple((name, factorized[name]) for name in WIDE_ATTRIBUTES),
    )


ROLE_CASES = (
    _case(
        "R43K-01",
        "provenance_edge",
        "Whether station H reported pressure above 8.4 bar in cycle 22.",
        {
            "source": "Both packets encode station H cycle 22 from the same acquisition record.",
            "lineage": "Packet B is produced from packet A by the registered pressure normalization pipeline.",
            "status": "The normalization transform is documented and verified for the stated pressure claim.",
            "effect": "The transform preserves every value needed for the 8.4 bar threshold claim.",
            "uncertainty": "The transform adds at most 0.02 bar uncertainty.",
            "tolerance": "The frozen claim tolerance is 0.10 bar.",
            "target": "Both packets address the same pressure-threshold claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "transform_status": "VERIFIED_TRANSFORM",
            "information_effect": "CLAIM_EQUIVALENT",
            "added_uncertainty": "IMMATERIAL_FOR_CLAIM",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-02",
        "provenance_edge",
        "Whether two entries in archive J support the same authorization claim.",
        {
            "source": "Both packets are entries from archive J, but they are different signed records.",
            "lineage": "Neither signed record is derived from the other, so a transformation pipeline between them is not applicable.",
            "status": "The records are explicitly separate observations, not transformations of one another.",
            "effect": "Because no transform links the records, a transform effect is inapplicable.",
            "uncertainty": "No transformation uncertainty applies.",
            "target": "Both records are proposed as support for the same authorization claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "NOT_APPLICABLE",
            "transform_status": "NO_TRANSFORM",
            "information_effect": "NOT_APPLICABLE",
            "added_uncertainty": "NOT_APPLICABLE",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-03",
        "provenance_edge",
        "Whether two specimens exhibit the same fluorescence peak.",
        {
            "source": "Packet A records specimen K17 and packet B records distinct specimen K18.",
            "lineage": "Both specimens were processed by the same scanner and reduction pipeline.",
            "status": "Neither specimen record is a transformation of the other.",
            "effect": "There is no transform-derived information effect between the specimen records.",
            "uncertainty": "No transformation uncertainty applies.",
            "target": "Both packets address the same fluorescence-peak claim.",
        },
        {
            "source_identity": "DISTINCT_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "transform_status": "NO_TRANSFORM",
            "information_effect": "NOT_APPLICABLE",
            "added_uncertainty": "NOT_APPLICABLE",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-04",
        "provenance_edge",
        "The distribution represented by the complete coastal transect survey.",
        {
            "source": "Packet A contains all 240 transect observations; packet B contains 60 observations from the same survey.",
            "lineage": "Packet B is extracted through the same registered survey pipeline.",
            "status": "The subset extraction transform is documented and verified.",
            "effect": "The extraction removes 180 observations from the full survey.",
            "uncertainty": "The subset operation has no defined scalar conversion-error term.",
            "target": "Both packets are evaluated against the complete-survey distribution claim.",
        },
        {
            "source_identity": "PARTIAL_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "transform_status": "VERIFIED_TRANSFORM",
            "information_effect": "INFORMATION_REDUCING",
            "added_uncertainty": "NOT_APPLICABLE",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-05",
        "effect_scope_edge",
        "The exact torque series recorded by motor L during trial 7.",
        {
            "source": "Both packets encode the same motor L trial 7 torque series.",
            "lineage": "Packet B is a reversible unit conversion of packet A.",
            "status": "The conversion is documented and verified over the full numeric domain.",
            "effect": "The reversible conversion preserves every torque value and ordering.",
            "uncertainty": "The conversion adds no measurable uncertainty.",
            "tolerance": "The claim tolerance is 0.01 newton-metre.",
            "target": "Both packets address the same exact-series claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "transform_status": "VERIFIED_TRANSFORM",
            "information_effect": "GLOBAL_EQUIVALENT",
            "added_uncertainty": "IMMATERIAL_FOR_CLAIM",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-06",
        "effect_scope_edge",
        "Whether chamber M stayed below 42.0 degrees during test 3.",
        {
            "source": "Both packets encode chamber M test 3 from the same sensor trace.",
            "lineage": "Packet B applies the verified field calibration to packet A.",
            "status": "The calibration transform is documented and verified for the threshold claim.",
            "effect": "The calibrated values preserve the temperature quantity used by the claim.",
            "uncertainty": "Calibration can move a value by 0.8 degrees.",
            "tolerance": "The frozen threshold tolerance is 0.2 degrees.",
            "target": "Both packets address the same temperature-threshold claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "transform_status": "VERIFIED_TRANSFORM",
            "information_effect": "CLAIM_EQUIVALENT",
            "added_uncertainty": "MATERIAL_FOR_CLAIM",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-07",
        "effect_scope_edge",
        "The complete sequence of packet-loss events on link N.",
        {
            "source": "Both packets originate from the same link N event stream.",
            "lineage": "Packet B is generated from packet A by the audited hourly aggregation job.",
            "status": "Audit records verify the declared hourly aggregation procedure.",
            "effect": "Packet B keeps hourly counts but removes event order and individual timestamps.",
            "uncertainty": "No scalar transformation uncertainty applies.",
            "target": "Both packets are evaluated against the complete-event-sequence claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "transform_status": "VERIFIED_TRANSFORM",
            "information_effect": "INFORMATION_REDUCING",
            "added_uncertainty": "NOT_APPLICABLE",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-08",
        "effect_scope_edge",
        "The raw vibration observations collected from turbine P.",
        {
            "source": "Both packets derive from the same turbine P vibration trace.",
            "lineage": "Packet B is produced from packet A by the registered diagnostic pipeline.",
            "status": "The diagnostic transform is documented and verified.",
            "effect": "Packet B adds a model-derived bearing-risk score absent from the raw trace.",
            "uncertainty": "The diagnostic output has no defined scalar conversion-error term.",
            "target": "Each packet is being assessed for the identical raw-vibration claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "transform_status": "VERIFIED_TRANSFORM",
            "information_effect": "INFORMATION_AUGMENTING",
            "added_uncertainty": "NOT_APPLICABLE",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-09",
        "cross_role_interaction",
        "Packet A supports route position while packet B is used to infer driver identity.",
        {
            "source": "Both packets encode the same vehicle Q location event.",
            "lineage": "Packet B comes from packet A through the validated coordinate-conversion pipeline.",
            "status": "Verification covers reversibility across the coordinate transform's entire domain.",
            "effect": "All coordinate information is preserved by the transform.",
            "uncertainty": "Conversion uncertainty is below the numeric tolerance.",
            "tolerance": "The frozen location tolerance is 0.5 metre.",
            "target": "The packets are used for different claims: route position versus driver identity.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "transform_status": "VERIFIED_TRANSFORM",
            "information_effect": "GLOBAL_EQUIVALENT",
            "added_uncertainty": "IMMATERIAL_FOR_CLAIM",
            "target_claim_relation": "DIFFERENT_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-10",
        "cross_role_interaction",
        "Whether two independent telescopes detected the same transient.",
        {
            "source": "Packet A is telescope R's observation and packet B is telescope S's distinct observation.",
            "lineage": "The telescopes use separate instruments, clocks, and reduction pipelines.",
            "status": "Neither observation is a transformation of the other.",
            "effect": "Transform-related information change is inapplicable to the independent observations.",
            "uncertainty": "No transformation uncertainty applies.",
            "target": "Both packets address the same transient-detection claim.",
        },
        {
            "source_identity": "DISTINCT_SOURCE",
            "lineage_coupling": "SEPARATE_PIPELINES",
            "transform_status": "NO_TRANSFORM",
            "information_effect": "NOT_APPLICABLE",
            "added_uncertainty": "NOT_APPLICABLE",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-11",
        "cross_role_interaction",
        "Whether normalized ledger T preserves the original balance threshold.",
        {
            "source": "Both packets are asserted to describe ledger T.",
            "lineage": "Packet B is claimed to be generated from packet A in the same export pipeline.",
            "status": "The export claims normalization, yet supplies neither the formula nor a validation artifact.",
            "effect": "The record does not establish what information the claimed normalization preserves.",
            "uncertainty": "The export provides no basis for estimating transformation uncertainty.",
            "target": "Both packets are proposed for the same balance-threshold claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "transform_status": "ASSERTED_UNVERIFIED_TRANSFORM",
            "information_effect": "UNKNOWN_EFFECT",
            "added_uncertainty": "UNKNOWN_UNCERTAINTY",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-12",
        "cross_role_interaction",
        "Whether two unlabeled extracts support the same material-composition claim.",
        {
            "source": "The extracts share a project folder but have no source object identifiers.",
            "lineage": "No derivation, shared-pipeline, or independence record is available.",
            "status": "It is unknown whether either extract is a transformation of the other.",
            "effect": "The information effect is unknown until transformation applicability is established.",
            "uncertainty": "No evidence determines the uncertainty introduced by a possible transform.",
            "target": "The available records do not establish whether the extracts address the same claim.",
        },
        {
            "source_identity": "UNKNOWN_SOURCE",
            "lineage_coupling": "UNKNOWN_PIPELINE",
            "transform_status": "UNKNOWN_TRANSFORM_APPLICABILITY",
            "information_effect": "UNKNOWN_EFFECT",
            "added_uncertainty": "UNKNOWN_UNCERTAINTY",
            "target_claim_relation": "UNKNOWN_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-13",
        "null_unknown",
        "Whether two devices recorded the same acoustic anomaly.",
        {
            "source": "Packet A records device U1 and packet B records distinct device U2.",
            "lineage": "Both records passed through the same acoustic processing pipeline.",
            "status": "Neither device record is a transformation of the other.",
            "effect": "No transform-mediated information change exists between the device records.",
            "uncertainty": "No transformation uncertainty applies.",
            "target": "Both packets address the same acoustic-anomaly claim.",
        },
        {
            "source_identity": "DISTINCT_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "transform_status": "NO_TRANSFORM",
            "information_effect": "NOT_APPLICABLE",
            "added_uncertainty": "NOT_APPLICABLE",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-14",
        "null_unknown",
        "Packet A supports shipment time while packet B supports container ownership.",
        {
            "source": "Both packets are separate entries from the same port manifest V.",
            "lineage": "Neither entry is derived from the other, so a transformation pipeline is not applicable.",
            "status": "The entries are not transformations of one another.",
            "effect": "A transformation effect is inapplicable because the entries are not derivations.",
            "uncertainty": "No transformation uncertainty applies.",
            "target": "The entries are used for different claims: shipment time versus container ownership.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "NOT_APPLICABLE",
            "transform_status": "NO_TRANSFORM",
            "information_effect": "NOT_APPLICABLE",
            "added_uncertainty": "NOT_APPLICABLE",
            "target_claim_relation": "DIFFERENT_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-15",
        "null_unknown",
        "Whether compressed map W preserves the original boundary classification.",
        {
            "source": "Both packets are asserted to encode map W.",
            "lineage": "Packet B is claimed to come from packet A through the same map pipeline.",
            "status": "A compression transform is asserted but no verification artifact is available.",
            "effect": "Whether classification-relevant information is preserved is unknown.",
            "uncertainty": "The claimed compression has no supported uncertainty estimate.",
            "target": "Both packets are proposed for the same boundary-classification claim.",
        },
        {
            "source_identity": "SAME_SOURCE",
            "lineage_coupling": "SAME_PIPELINE",
            "transform_status": "ASSERTED_UNVERIFIED_TRANSFORM",
            "information_effect": "UNKNOWN_EFFECT",
            "added_uncertainty": "UNKNOWN_UNCERTAINTY",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
    ),
    _case(
        "R43K-16",
        "null_unknown",
        "Whether two orphaned exports describe the same reserve quantity.",
        {
            "source": "The exports have no source identifiers or object hashes.",
            "lineage": "No pipeline, derivation, or independence record survives.",
            "status": "It is unknown whether a transformation relation exists between them.",
            "effect": "The information effect cannot be determined without transformation applicability.",
            "uncertainty": "The orphaned records contain no transformation-uncertainty evidence.",
            "target": "Both exports are proposed for the same reserve-quantity claim.",
        },
        {
            "source_identity": "UNKNOWN_SOURCE",
            "lineage_coupling": "UNKNOWN_PIPELINE",
            "transform_status": "UNKNOWN_TRANSFORM_APPLICABILITY",
            "information_effect": "UNKNOWN_EFFECT",
            "added_uncertainty": "UNKNOWN_UNCERTAINTY",
            "target_claim_relation": "SAME_TARGET_CLAIM",
        },
    ),
)


FORWARD_ORDER = tuple(case.case_id for case in ROLE_CASES)
REVERSE_ORDER = tuple(reversed(FORWARD_ORDER))
