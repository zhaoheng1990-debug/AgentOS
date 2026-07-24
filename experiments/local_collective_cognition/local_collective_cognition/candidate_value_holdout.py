"""Fresh hard/null holdout for candidate-value composition v0.37."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "candidate_value_holdout_v0_37"
CORPUS_ID = "local-candidate-value-v0-37"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


def _case(case_id, domain, goal, labels, texts):
    return {
        "case_id": case_id,
        "domain": domain,
        "research_goal": goal,
        "objects": tuple(
            (f"O{index}", label)
            for index, label in enumerate(labels, 1)
        ),
        "spans": tuple(
            (f"S{index}", text)
            for index, text in enumerate(texts, 1)
        ),
        "primary": ("O1",),
        "supported": (("O2", "O1"), ("O3", "O1")),
        "informative_null": (("O4", "O1"),),
        "constraints": ("O5", "O6"),
        "counterevidence": ("S3", "S4", "S5", "S7"),
    }


CASES = (
    _case(
        "CV-WATER", "water_treatment",
        "Distinguish causes of filtration-efficiency drift.",
        ("efficiency drift", "coagulant protocol", "source turbidity",
         "membrane vendor", "backwash lag", "sensor age"),
        ("Drift rose after the coagulant protocol changed.",
         "Source turbidity increased during affected runs.",
         "Membrane vendors are balanced across treatment lines.",
         "Backwash lags are missing for several cycles.",
         "Sensor ages differ across facilities.",
         "Old-protocol replay reduces drift at matched turbidity.",
         "Vendor-matched lines preserve the turbidity effect."),
    ),
    _case(
        "CV-BATTERY", "battery_testing",
        "Distinguish causes of capacity-estimate drift.",
        ("capacity drift", "charge protocol", "cell temperature",
         "separator maker", "rest duration", "cycle maturity"),
        ("Drift rose after the charge protocol changed.",
         "Cell temperature increased in affected tests.",
         "Separator makers are balanced across cell lots.",
         "Rest durations are missing for several cycles.",
         "Newest cells have immature cycle labels.",
         "Old-protocol replay reduces drift at matched temperature.",
         "Maker-matched cells preserve the temperature effect."),
    ),
    _case(
        "CV-HOSPITAL", "hospital_operations",
        "Distinguish causes of discharge-time prediction drift.",
        ("prediction drift", "coding rule", "patient mix",
         "record vendor", "consult lag", "outcome maturity"),
        ("Drift rose after coding rules changed.",
         "Patient mix shifted toward complex admissions.",
         "Record vendors are balanced across wards.",
         "Consult lags are absent from several records.",
         "Recent admissions have immature outcome labels.",
         "Old-rule replay reduces drift within patient strata.",
         "Vendor-matched wards preserve the patient-mix effect."),
    ),
    _case(
        "CV-SAT", "satellite_imaging",
        "Distinguish causes of reflectance-estimate drift.",
        ("reflectance drift", "correction model", "aerosol load",
         "detector maker", "view-angle lag", "calibration age"),
        ("Drift rose after the correction model changed.",
         "Aerosol load increased in affected scenes.",
         "Detector makers are balanced across acquisitions.",
         "View-angle metadata is missing for several scenes.",
         "Calibration ages differ across instruments.",
         "Old-model replay reduces drift at matched aerosol load.",
         "Maker-matched scenes preserve the aerosol effect."),
    ),
    _case(
        "CV-CEMENT", "cement_production",
        "Distinguish causes of strength-estimate drift.",
        ("strength drift", "kiln recipe", "clinker composition",
         "mill supplier", "curing delay", "assay age"),
        ("Drift rose after the kiln recipe changed.",
         "Clinker composition shifted in affected batches.",
         "Mill suppliers are balanced across production lines.",
         "Curing delays are missing for several samples.",
         "Assay ages differ across laboratories.",
         "Old-recipe replay reduces drift at matched composition.",
         "Supplier-matched lines preserve the composition effect."),
    ),
    _case(
        "CV-FRAUD", "payment_fraud",
        "Distinguish causes of fraud-score drift.",
        ("score drift", "feature window", "merchant mix",
         "gateway vendor", "chargeback lag", "label maturity"),
        ("Drift rose after feature windows changed.",
         "Merchant mix shifted toward new marketplaces.",
         "Gateway vendors are balanced across transactions.",
         "Chargeback lags hide several recent fraud events.",
         "Newest transactions have immature labels.",
         "Old-window replay reduces drift within merchant strata.",
         "Vendor-matched traffic preserves the merchant-mix effect."),
    ),
    _case(
        "CV-CROP", "crop_monitoring",
        "Distinguish causes of yield-estimate drift.",
        ("yield drift", "growth model", "soil moisture",
         "drone maker", "survey lag", "harvest maturity"),
        ("Drift rose after the growth model changed.",
         "Soil moisture differed in affected fields.",
         "Drone makers are balanced across farms.",
         "Survey lags are missing for several plots.",
         "Recent plots have immature harvest labels.",
         "Old-model replay reduces drift at matched moisture.",
         "Maker-matched farms preserve the moisture effect."),
    ),
    _case(
        "CV-ROBOT", "warehouse_robotics",
        "Distinguish causes of navigation-error drift.",
        ("error drift", "planner policy", "aisle congestion",
         "lidar vendor", "map-update lag", "maintenance age"),
        ("Drift rose after the planner policy changed.",
         "Aisle congestion increased during affected shifts.",
         "Lidar vendors are balanced across robots.",
         "Map-update lags are missing for several routes.",
         "Maintenance ages differ across fleets.",
         "Old-policy replay reduces drift at matched congestion.",
         "Vendor-matched robots preserve the congestion effect."),
    ),
)


def build_candidate_value_holdout():
    items = [_public_item(value) for value in CASES]
    items.sort(key=lambda value: hash_payload(
        [CORPUS_VERSION, value["case_id"]]
    ))
    bindings = {
        value["case_id"]: {
            "public_item_hash": hash_payload(_public_item(value)),
            "primary_object_ids": list(value["primary"]),
            "supported_targets": [
                {"source_object_id": source, "target_object_id": target}
                for source, target in value["supported"]
            ],
            "informative_null_targets": [
                {"source_object_id": source, "target_object_id": target}
                for source, target in value["informative_null"]
            ],
            "hidden_constraint_object_ids": list(value["constraints"]),
            "counterevidence_span_ids": list(value["counterevidence"]),
        }
        for value in CASES
    }
    surface = {
        "surface_version": CORPUS_VERSION,
        "items": items,
        "private_outcomes_exposed": False,
    }
    commitment = {
        "artifact_version": CORPUS_VERSION,
        "corpus_id": CORPUS_ID,
        "case_count": len(CASES),
        "domain_count": len({value["domain"] for value in CASES}),
        "replication_ids": list(REPLICATION_IDS),
        "public_surface": {
            **surface,
            "surface_hash": hash_payload(surface),
        },
        "private_provenance": {
            "bindings": bindings,
            "truth_coordinate": "SYNTHETIC_OUTCOME_METADATA",
            "available_to_provider": False,
        },
        "reference_state": (
            "FRESH_V0_37_FROZEN_BEFORE_CANDIDATE_VALUE_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_candidate_value_holdout(artifact):
    if artifact != build_candidate_value_holdout():
        raise ValueError("candidate_value_holdout_invalid")


def _public_item(value):
    return {
        "case_id": value["case_id"],
        "domain": value["domain"],
        "research_goal": value["research_goal"],
        "object_registry": [
            {"object_id": object_id, "label": label}
            for object_id, label in value["objects"]
        ],
        "evidence_spans": [
            {
                "span_id": span_id,
                "text": text,
                "text_hash": hash_payload(text),
            }
            for span_id, text in value["spans"]
        ],
    }
