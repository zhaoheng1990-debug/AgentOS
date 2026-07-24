"""Fresh holdout for independent truth state and prospective null role."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "null_role_holdout_v0_40"
CORPUS_ID = "local-null-information-role-v0-40"
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
        "NR-AQUA", "aquaculture",
        "Distinguish causes of growth-estimate drift.",
        ("growth drift", "feeding schedule", "water temperature",
         "sensor vendor", "sampling lag", "stock age"),
        ("Drift rose after the feeding schedule changed.",
         "Water temperature shifted in affected tanks.",
         "Sensor vendors are balanced across tanks.",
         "Sampling lags are missing for several cohorts.",
         "Stock ages differ across farms.",
         "Old-schedule replay reduces drift at matched temperature.",
         "Vendor-matched tanks preserve the temperature effect."),
    ),
    _case(
        "NR-AIRCRAFT", "aircraft_maintenance",
        "Distinguish causes of maintenance-risk drift.",
        ("risk drift", "inspection protocol", "flight-cycle mix",
         "parts vendor", "log lag", "airframe age"),
        ("Drift rose after the inspection protocol changed.",
         "Flight-cycle mix shifted in affected fleets.",
         "Parts vendors are balanced across fleets.",
         "Log lags are missing for several inspections.",
         "Airframe ages differ across operators.",
         "Old-protocol replay reduces drift within cycle strata.",
         "Vendor-matched fleets preserve the cycle-mix effect."),
    ),
    _case(
        "NR-SEISMIC", "seismic_monitoring",
        "Distinguish causes of event-location drift.",
        ("location drift", "travel-time model", "station geometry",
         "receiver vendor", "catalog lag", "clock age"),
        ("Drift rose after the travel-time model changed.",
         "Station geometry shifted in affected regions.",
         "Receiver vendors are balanced across arrays.",
         "Catalog lags are missing for several events.",
         "Clock ages differ across stations.",
         "Old-model replay reduces drift at matched geometry.",
         "Vendor-matched arrays preserve the geometry effect."),
    ),
    _case(
        "NR-RETAIL", "retail_forecasting",
        "Distinguish causes of demand-score drift.",
        ("demand drift", "promotion policy", "store mix",
         "scanner vendor", "return lag", "label maturity"),
        ("Drift rose after the promotion policy changed.",
         "Store mix shifted toward urban outlets.",
         "Scanner vendors are balanced across stores.",
         "Return lags hide several recent transactions.",
         "Newest weeks have immature labels.",
         "Old-policy replay reduces drift within store strata.",
         "Vendor-matched stores preserve the store-mix effect."),
    ),
    _case(
        "NR-STEEL", "steel_processing",
        "Distinguish causes of hardness-estimate drift.",
        ("hardness drift", "cooling recipe", "alloy composition",
         "furnace vendor", "conditioning lag", "gauge age"),
        ("Drift rose after the cooling recipe changed.",
         "Alloy composition shifted in affected lots.",
         "Furnace vendors are balanced across lines.",
         "Conditioning lags are missing for several samples.",
         "Gauge ages differ across laboratories.",
         "Old-recipe replay reduces drift at matched composition.",
         "Vendor-matched lines preserve the alloy effect."),
    ),
    _case(
        "NR-EDU", "adaptive_learning",
        "Distinguish causes of mastery-score drift.",
        ("mastery drift", "sequencing policy", "learner mix",
         "content vendor", "grading lag", "cohort age"),
        ("Drift rose after the sequencing policy changed.",
         "Learner mix shifted toward novice cohorts.",
         "Content vendors are balanced across courses.",
         "Grading lags hide several recent attempts.",
         "Cohort ages differ across schools.",
         "Old-policy replay reduces drift within learner strata.",
         "Vendor-matched courses preserve the learner-mix effect."),
    ),
    _case(
        "NR-HEAT", "district_heating",
        "Distinguish causes of load-estimate drift.",
        ("load drift", "dispatch rule", "weather pattern",
         "meter vendor", "billing lag", "sensor age"),
        ("Drift rose after the dispatch rule changed.",
         "Weather patterns shifted in affected districts.",
         "Meter vendors are balanced across districts.",
         "Billing lags are missing for several buildings.",
         "Sensor ages differ across substations.",
         "Old-rule replay reduces drift at matched weather.",
         "Vendor-matched districts preserve the weather effect."),
    ),
    _case(
        "NR-VISION", "industrial_vision",
        "Distinguish causes of inspection-error drift.",
        ("error drift", "threshold policy", "defect mix",
         "camera vendor", "review lag", "lens age"),
        ("Drift rose after the threshold policy changed.",
         "Defect mix shifted toward surface cracks.",
         "Camera vendors are balanced across lines.",
         "Review lags hide several recent inspections.",
         "Lens ages differ across factories.",
         "Old-policy replay reduces drift within defect strata.",
         "Vendor-matched lines preserve the defect-mix effect."),
    ),
)


def build_null_role_holdout():
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
            **surface, "surface_hash": hash_payload(surface),
        },
        "private_provenance": {
            "bindings": bindings,
            "truth_coordinate": "SYNTHETIC_OUTCOME_METADATA",
            "available_to_provider": False,
        },
        "reference_state": (
            "FRESH_V0_40_FROZEN_BEFORE_NULL_ROLE_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_null_role_holdout(artifact):
    if artifact != build_null_role_holdout():
        raise ValueError("null_role_holdout_invalid")


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
