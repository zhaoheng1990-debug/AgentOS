"""Fresh holdout for selective single-delta counterproposals v0.41."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "selective_delta_holdout_v0_41"
CORPUS_ID = "local-selective-delta-v0-41"
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
        "SD-ORCHARD", "precision_orchard",
        "Distinguish causes of yield-estimate drift.",
        ("yield drift", "irrigation policy", "soil moisture",
         "drone vendor", "harvest lag", "tree age"),
        ("Drift rose after the irrigation policy changed.",
         "Soil moisture shifted in affected blocks.",
         "Drone vendors are balanced across orchards.",
         "Harvest lags are missing for several blocks.",
         "Tree ages differ across farms.",
         "Old-policy replay reduces drift at matched moisture.",
         "Vendor-matched blocks preserve the moisture effect."),
    ),
    _case(
        "SD-RAIL", "rail_operations",
        "Distinguish causes of delay-score drift.",
        ("delay drift", "dispatch rule", "freight mix",
         "signal vendor", "incident lag", "track age"),
        ("Drift rose after the dispatch rule changed.",
         "Freight mix shifted in affected corridors.",
         "Signal vendors are balanced across corridors.",
         "Incident lags are missing for several journeys.",
         "Track ages differ across regions.",
         "Old-rule replay reduces drift within freight strata.",
         "Vendor-matched corridors preserve the freight effect."),
    ),
    _case(
        "SD-BATTERY", "battery_storage",
        "Distinguish causes of health-estimate drift.",
        ("health drift", "charge policy", "temperature profile",
         "cell vendor", "inspection lag", "pack age"),
        ("Drift rose after the charge policy changed.",
         "Temperature profiles shifted in affected packs.",
         "Cell vendors are balanced across sites.",
         "Inspection lags are missing for several packs.",
         "Pack ages differ across installations.",
         "Old-policy replay reduces drift at matched temperature.",
         "Vendor-matched packs preserve the temperature effect."),
    ),
    _case(
        "SD-SATELLITE", "satellite_imaging",
        "Distinguish causes of cloud-score drift.",
        ("cloud drift", "correction model", "viewing angle",
         "sensor vendor", "review lag", "calibration age"),
        ("Drift rose after the correction model changed.",
         "Viewing angles shifted in affected scenes.",
         "Sensor vendors are balanced across satellites.",
         "Review lags hide several recent scenes.",
         "Calibration ages differ across instruments.",
         "Old-model replay reduces drift at matched angle.",
         "Vendor-matched scenes preserve the angle effect."),
    ),
    _case(
        "SD-FOUNDRY", "metal_foundry",
        "Distinguish causes of porosity-estimate drift.",
        ("porosity drift", "pouring recipe", "melt composition",
         "mold vendor", "cooling lag", "scanner age"),
        ("Drift rose after the pouring recipe changed.",
         "Melt composition shifted in affected casts.",
         "Mold vendors are balanced across lines.",
         "Cooling lags are missing for several casts.",
         "Scanner ages differ across laboratories.",
         "Old-recipe replay reduces drift at matched composition.",
         "Vendor-matched lines preserve the composition effect."),
    ),
    _case(
        "SD-WATER", "water_distribution",
        "Distinguish causes of leakage-score drift.",
        ("leakage drift", "pressure policy", "demand pattern",
         "meter vendor", "repair lag", "pipe age"),
        ("Drift rose after the pressure policy changed.",
         "Demand patterns shifted in affected districts.",
         "Meter vendors are balanced across districts.",
         "Repair lags are missing for several incidents.",
         "Pipe ages differ across networks.",
         "Old-policy replay reduces drift at matched demand.",
         "Vendor-matched districts preserve the demand effect."),
    ),
    _case(
        "SD-ROBOT", "warehouse_robotics",
        "Distinguish causes of route-time drift.",
        ("route drift", "planner policy", "order mix",
         "robot vendor", "queue lag", "map age"),
        ("Drift rose after the planner policy changed.",
         "Order mix shifted toward multi-zone picks.",
         "Robot vendors are balanced across warehouses.",
         "Queue lags are missing for several shifts.",
         "Map ages differ across sites.",
         "Old-policy replay reduces drift within order strata.",
         "Vendor-matched sites preserve the order-mix effect."),
    ),
    _case(
        "SD-FOREST", "forest_monitoring",
        "Distinguish causes of biomass-estimate drift.",
        ("biomass drift", "canopy model", "rainfall pattern",
         "lidar vendor", "survey lag", "plot age"),
        ("Drift rose after the canopy model changed.",
         "Rainfall patterns shifted in affected regions.",
         "Lidar vendors are balanced across surveys.",
         "Survey lags are missing for several plots.",
         "Plot ages differ across regions.",
         "Old-model replay reduces drift at matched rainfall.",
         "Vendor-matched plots preserve the rainfall effect."),
    ),
)


def build_selective_delta_holdout():
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
            "FRESH_V0_41_FROZEN_BEFORE_SELECTIVE_DELTA_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_selective_delta_holdout(artifact):
    if artifact != build_selective_delta_holdout():
        raise ValueError("selective_delta_holdout_invalid")


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
