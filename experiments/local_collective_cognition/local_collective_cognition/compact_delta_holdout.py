"""Fresh holdout for compact semantic-delta validation v0.42."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "compact_delta_holdout_v0_42"
CORPUS_ID = "local-compact-delta-v0-42"
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
        "CD-WIND", "offshore_wind",
        "Distinguish causes of power-estimate drift.",
        ("power drift", "control policy", "wind shear",
         "turbine vendor", "service lag", "blade age"),
        ("Drift rose after the control policy changed.",
         "Wind shear shifted in affected intervals.",
         "Turbine vendors are balanced across farms.",
         "Service lags are missing for several turbines.",
         "Blade ages differ across sites.",
         "Old-policy replay reduces drift at matched shear.",
         "Vendor-matched turbines preserve the shear effect."),
    ),
    _case(
        "CD-BREW", "fermentation",
        "Distinguish causes of yield-score drift.",
        ("yield drift", "aeration recipe", "sugar profile",
         "vessel vendor", "sampling lag", "culture age"),
        ("Drift rose after the aeration recipe changed.",
         "Sugar profiles shifted in affected batches.",
         "Vessel vendors are balanced across lines.",
         "Sampling lags are missing for several batches.",
         "Culture ages differ across facilities.",
         "Old-recipe replay reduces drift at matched sugar.",
         "Vendor-matched batches preserve the sugar effect."),
    ),
    _case(
        "CD-TRAFFIC", "urban_traffic",
        "Distinguish causes of travel-time drift.",
        ("travel drift", "signal policy", "vehicle mix",
         "camera vendor", "incident lag", "map age"),
        ("Drift rose after the signal policy changed.",
         "Vehicle mix shifted in affected corridors.",
         "Camera vendors are balanced across junctions.",
         "Incident lags are missing for several periods.",
         "Map ages differ across districts.",
         "Old-policy replay reduces drift within vehicle strata.",
         "Vendor-matched corridors preserve the vehicle effect."),
    ),
    _case(
        "CD-MINING", "mineral_processing",
        "Distinguish causes of recovery-estimate drift.",
        ("recovery drift", "flotation recipe", "ore composition",
         "reagent vendor", "assay lag", "sensor age"),
        ("Drift rose after the flotation recipe changed.",
         "Ore composition shifted in affected lots.",
         "Reagent vendors are balanced across plants.",
         "Assay lags are missing for several lots.",
         "Sensor ages differ across plants.",
         "Old-recipe replay reduces drift at matched composition.",
         "Vendor-matched lots preserve the composition effect."),
    ),
    _case(
        "CD-PAPER", "paper_milling",
        "Distinguish causes of strength-estimate drift.",
        ("strength drift", "pressing recipe", "fiber moisture",
         "pulp vendor", "conditioning lag", "gauge age"),
        ("Drift rose after the pressing recipe changed.",
         "Fiber moisture shifted in affected rolls.",
         "Pulp vendors are balanced across mills.",
         "Conditioning lags are missing for several samples.",
         "Gauge ages differ across laboratories.",
         "Old-recipe replay reduces drift at matched moisture.",
         "Vendor-matched rolls preserve the moisture effect."),
    ),
    _case(
        "CD-MARINE", "marine_navigation",
        "Distinguish causes of route-error drift.",
        ("route drift", "guidance policy", "current pattern",
         "receiver vendor", "chart lag", "antenna age"),
        ("Drift rose after the guidance policy changed.",
         "Current patterns shifted in affected routes.",
         "Receiver vendors are balanced across vessels.",
         "Chart lags are missing for several voyages.",
         "Antenna ages differ across fleets.",
         "Old-policy replay reduces drift at matched current.",
         "Vendor-matched routes preserve the current effect."),
    ),
    _case(
        "CD-CHIP", "semiconductor_test",
        "Distinguish causes of defect-score drift.",
        ("defect drift", "test policy", "wafer mix",
         "probe vendor", "review lag", "fixture age"),
        ("Drift rose after the test policy changed.",
         "Wafer mix shifted in affected lots.",
         "Probe vendors are balanced across lines.",
         "Review lags hide several recent failures.",
         "Fixture ages differ across factories.",
         "Old-policy replay reduces drift within wafer strata.",
         "Vendor-matched lots preserve the wafer-mix effect."),
    ),
    _case(
        "CD-GRAIN", "grain_storage",
        "Distinguish causes of spoilage-score drift.",
        ("spoilage drift", "ventilation policy", "humidity pattern",
         "silo vendor", "inspection lag", "sensor age"),
        ("Drift rose after the ventilation policy changed.",
         "Humidity patterns shifted in affected silos.",
         "Silo vendors are balanced across depots.",
         "Inspection lags are missing for several bins.",
         "Sensor ages differ across depots.",
         "Old-policy replay reduces drift at matched humidity.",
         "Vendor-matched silos preserve the humidity effect."),
    ),
)


def build_compact_delta_holdout():
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
            "FRESH_V0_42_FROZEN_BEFORE_COMPACT_DELTA_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_compact_delta_holdout(artifact):
    if artifact != build_compact_delta_holdout():
        raise ValueError("compact_delta_holdout_invalid")


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
