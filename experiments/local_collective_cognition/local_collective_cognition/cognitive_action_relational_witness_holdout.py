"""Fresh holdout for relational evidence witnesses v0.23."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


RELATIONAL_CORPUS_VERSION = (
    "cognitive_action_relational_witness_holdout_v0_23"
)
RELATIONAL_CORPUS_ID = "local-cognitive-action-relational-witness-v0-23"
DESIGN_STRATA = (
    "POSITIVE_DEFINITION",
    "COMPOSITIONAL_DERIVATION",
    "OPEN_SURFACE",
    "MISSING_SPECIFICATION",
)


@dataclass(frozen=True)
class RelationalWitnessCase:
    case_id: str
    object_family: str
    design_stratum: str
    public_prompt: str
    candidate_a: str
    candidate_b: str

    def commitment(self):
        return asdict(self)


CASES = (
    RelationalWitnessCase("RW-UA01", "UNIT_OF_ANALYSIS", "POSITIVE_DEFINITION", "The incident policy defines one analysis unit as a customer-visible outage within one region, merging alerts separated by less than thirty minutes. Candidates use each alert or each merged regional outage.", "each individual alert", "each merged regional outage"),
    RelationalWitnessCase("RW-UA02", "UNIT_OF_ANALYSIS", "COMPOSITIONAL_DERIVATION", "Create one cohort for every product and country combination that has at least twenty qualifying accounts. Candidates use product-only cohorts or product-country cohorts.", "one cohort per product", "one cohort per product-country pair"),
    RelationalWitnessCase("RW-UA03", "UNIT_OF_ANALYSIS", "OPEN_SURFACE", "The review asks for meaningful workspaces but supplies no activity threshold. Candidates use at least three active seats or at least ten edited documents. Select only with a supported default.", "at least three active seats", "at least ten edited documents"),
    RelationalWitnessCase("RW-UA04", "UNIT_OF_ANALYSIS", "MISSING_SPECIFICATION", "The analysis requests grain profile UG-42, but the data dictionary containing that profile is unavailable. Candidates use account-day rows or session rows.", "account-day rows", "session rows"),
    RelationalWitnessCase("RW-ET01", "ELIGIBILITY_TRIGGER", "POSITIVE_DEFINITION", "The rebate rule defines eligibility as an invoice paid within ten days with no chargeback during the following thirty days. Candidates require timely payment alone or both stated conditions.", "invoice paid within ten days", "timely payment and no chargeback for thirty days"),
    RelationalWitnessCase("RW-ET02", "ELIGIBILITY_TRIGGER", "COMPOSITIONAL_DERIVATION", "Escalate when three consecutive measurements exceed the limit and the latest measurement occurs after the warning notice. Candidates trigger on any exceedance or only after the full sequence.", "any single exceedance", "three consecutive exceedances with the latest after warning"),
    RelationalWitnessCase("RW-ET03", "ELIGIBILITY_TRIGGER", "OPEN_SURFACE", "The queue prioritizes high-intent leads without defining intent. Candidates require two pricing-page visits or a submitted demo request. Select only if ordinary context supports a default.", "two pricing-page visits", "a submitted demo request"),
    RelationalWitnessCase("RW-ET04", "ELIGIBILITY_TRIGGER", "MISSING_SPECIFICATION", "The alert export invokes trigger policy EP-17, but the policy registry is absent. Candidates trigger on the first anomaly or the third consecutive anomaly.", "first anomaly", "third consecutive anomaly"),
    RelationalWitnessCase("RW-VS01", "VERSION_SELECTOR", "POSITIVE_DEFINITION", "The audit guide defines the effective contract as the latest version approved before the transaction timestamp. Candidates use the latest currently approved version or the latest version approved before the transaction.", "latest currently approved version", "latest version approved before the transaction"),
    RelationalWitnessCase("RW-VS02", "VERSION_SELECTOR", "COMPOSITIONAL_DERIVATION", "Version 4 was approved on Thursday after the Wednesday freeze; version 3 was approved on Tuesday, and the export uses the newest version approved by the freeze. Candidates use version 3 or version 4.", "version 3", "version 4"),
    RelationalWitnessCase("RW-VS03", "VERSION_SELECTOR", "OPEN_SURFACE", "A report requests the current policy without an as-of convention. Candidates use the policy current when data was collected or the policy current when the report is produced. Select only with a supported default.", "policy at data collection", "policy at report production"),
    RelationalWitnessCase("RW-VS04", "VERSION_SELECTOR", "MISSING_SPECIFICATION", "The import requests schema alias SV-88, but the alias catalog is missing. Candidates decode records with schema version 2 or schema version 3.", "schema version 2", "schema version 3"),
    RelationalWitnessCase("RW-NR01", "NORMALIZATION_RULE", "POSITIVE_DEFINITION", "The capacity handbook defines normalized load as request count divided by provisioned processor cores. Candidates divide by processor cores or by active service instances.", "requests per provisioned processor core", "requests per active service instance"),
    RelationalWitnessCase("RW-NR02", "NORMALIZATION_RULE", "COMPOSITIONAL_DERIVATION", "For each observation, subtract the control mean and then divide the difference by the control standard deviation. Candidates use a control ratio or a control-based z score.", "observation divided by control mean", "control-based z score"),
    RelationalWitnessCase("RW-NR03", "NORMALIZATION_RULE", "OPEN_SURFACE", "The comparison asks to normalize for organization size but gives no size variable or formula. Candidates divide by employee count or by log annual revenue. Select only with a supported default.", "per employee", "per log annual revenue"),
    RelationalWitnessCase("RW-NR04", "NORMALIZATION_RULE", "MISSING_SPECIFICATION", "The pipeline requires normalizer NX-12, but its formula sheet cannot be found. Candidates use min-max scaling or a winsorized z score.", "min-max scaling", "winsorized z score"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])


def build_relational_witness_holdout():
    _validate_cases()
    ordered = sorted(
        CASES,
        key=lambda case: hash_payload([
            RELATIONAL_CORPUS_VERSION,
            case.case_id,
        ]),
    )
    items, bindings = [], {}
    for case in ordered:
        conflict_id = "relational-witness-" + hash_payload([
            RELATIONAL_CORPUS_VERSION,
            CASE_COMMITMENT,
            case.case_id,
        ])[:18]
        item = {
            "conflict_id": conflict_id,
            "public_prompt": case.public_prompt,
            "candidate_a": case.candidate_a,
            "candidate_b": case.candidate_b,
        }
        items.append(item)
        bindings[conflict_id] = {
            "case_id": case.case_id,
            "object_family": case.object_family,
            "public_item_hash": hash_payload(item),
        }
    surface_commitment = {
        "surface_version": RELATIONAL_CORPUS_VERSION,
        "items": items,
        "semantic_labels_exposed": False,
        "design_strata_exposed": False,
        "candidate_outputs_exposed": False,
    }
    surface = {
        **surface_commitment,
        "surface_hash": hash_payload(surface_commitment),
    }
    commitment = {
        "artifact_version": RELATIONAL_CORPUS_VERSION,
        "corpus_id": RELATIONAL_CORPUS_ID,
        "case_commitment": CASE_COMMITMENT,
        "case_count": len(CASES),
        "family_counts": {
            family: sum(case.object_family == family for case in CASES)
            for family in sorted({case.object_family for case in CASES})
        },
        "design_stratum_counts": {
            stratum: sum(case.design_stratum == stratum for case in CASES)
            for stratum in DESIGN_STRATA
        },
        "public_surface": surface,
        "private_provenance": {
            "bindings": bindings,
            "design_strata_committed_but_not_reference_truth": True,
            "semantic_labels_present": False,
        },
        "reference_state": (
            "UNLABELED_FROZEN_BEFORE_RELATIONAL_WITNESS_RUN"
        ),
        "v0_22_reference_available_during_inference": False,
        "reference_revision_allowed_after_candidate_run": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "evidence_refs": [f"corpus://{RELATIONAL_CORPUS_ID}"],
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_relational_witness_holdout(artifact):
    commitment = {
        key: value for key, value in artifact.items()
        if key != "artifact_hash"
    }
    if (
        artifact.get("artifact_hash") != hash_payload(commitment)
        or artifact != build_relational_witness_holdout()
    ):
        raise ValueError("relational_witness_holdout_invalid")


def evidence_text(item):
    marker = " Candidates "
    prompt = item["public_prompt"]
    return prompt.split(marker, 1)[0] if marker in prompt else prompt


def _validate_cases():
    if len(CASES) != 16 or len({case.case_id for case in CASES}) != 16:
        raise ValueError("relational_witness_cases_invalid")
    for family in {case.object_family for case in CASES}:
        if {
            case.design_stratum
            for case in CASES
            if case.object_family == family
        } != set(DESIGN_STRATA):
            raise ValueError("relational_witness_cross_balance_invalid")
