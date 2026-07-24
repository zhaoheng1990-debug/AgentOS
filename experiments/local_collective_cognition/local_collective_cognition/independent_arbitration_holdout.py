"""Fresh hard/null holdout for independent candidate arbitration v0.36."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "independent_arbitration_holdout_v0_36"
CORPUS_ID = "local-independent-arbitration-v0-36"
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
        "AR-AIR", "air_quality",
        "Distinguish causes of particulate-estimate drift.",
        ("estimate drift", "humidity correction", "traffic mix",
         "sensor maker", "filter age", "reference lag"),
        ("Drift rose after humidity correction changed.",
         "Traffic mix shifted toward heavy vehicles.",
         "Sensor makers are balanced across sites.",
         "Filter ages are missing for several stations.",
         "Reference measurements lag peak pollution windows.",
         "Old-correction replay reduces drift at matched traffic mix.",
         "Maker-matched sites preserve the traffic-mix effect."),
    ),
    _case(
        "AR-PROTEIN", "protein_assay",
        "Distinguish causes of binding-affinity drift.",
        ("affinity drift", "buffer protocol", "protein lot",
         "plate supplier", "incubation delay", "calibration age"),
        ("Drift rose after the buffer protocol changed.",
         "Protein lots differ in the affected assays.",
         "Plate suppliers are balanced across runs.",
         "Incubation delays are missing for several wells.",
         "Calibration ages differ across instruments.",
         "Old-protocol replay reduces drift within protein lots.",
         "Supplier-matched assays preserve the lot effect."),
    ),
    _case(
        "AR-FLEET", "fleet_maintenance",
        "Distinguish causes of fuel-efficiency drift.",
        ("efficiency drift", "control firmware", "route load",
         "vehicle maker", "tire pressure", "service age"),
        ("Drift rose after control firmware changed.",
         "Route loads increased in affected vehicles.",
         "Vehicle makers are balanced across samples.",
         "Tire pressure is absent from several trips.",
         "Service ages differ across depots.",
         "Old-firmware replay reduces drift at matched route load.",
         "Maker-matched vehicles preserve the load effect."),
    ),
    _case(
        "AR-SIGNAL", "radio_network",
        "Distinguish causes of signal-quality drift.",
        ("quality drift", "handover policy", "user density",
         "radio vendor", "antenna tilt", "clock offset"),
        ("Drift rose after handover policy changed.",
         "User density increased in affected cells.",
         "Radio vendors are balanced across cells.",
         "Antenna tilt is missing for several sectors.",
         "Clock offsets differ during incident windows.",
         "Old-policy replay reduces drift at matched density.",
         "Vendor-matched cells preserve the density effect."),
    ),
    _case(
        "AR-GLASS", "glass_manufacturing",
        "Distinguish causes of thickness-variation drift.",
        ("thickness drift", "furnace recipe", "cullet fraction",
         "roller supplier", "annealing delay", "gauge age"),
        ("Drift rose after the furnace recipe changed.",
         "Cullet fraction increased in affected batches.",
         "Roller suppliers are balanced across lines.",
         "Annealing delays are missing for several runs.",
         "Gauge ages differ across production lines.",
         "Old-recipe replay reduces drift at matched cullet fraction.",
         "Supplier-matched lines preserve the cullet effect."),
    ),
    _case(
        "AR-SEARCH", "search_ranking",
        "Distinguish causes of ranking-quality drift.",
        ("quality drift", "ranking objective", "query mix",
         "index vendor", "feedback delay", "judgment age"),
        ("Drift rose after the ranking objective changed.",
         "Query mix shifted toward navigational requests.",
         "Index vendors are balanced across traffic slices.",
         "Feedback delays hide several recent sessions.",
         "Judgment ages differ across query classes.",
         "Old-objective replay reduces drift within query classes.",
         "Vendor-matched slices preserve the query-mix effect."),
    ),
    _case(
        "AR-POWER", "power_grid",
        "Distinguish causes of demand-forecast drift.",
        ("forecast drift", "weather transform", "load composition",
         "meter vendor", "outage overlap", "label delay"),
        ("Drift rose after the weather transform changed.",
         "Load composition shifted in affected feeders.",
         "Meter vendors are balanced across feeders.",
         "Outage overlap is missing from several intervals.",
         "Final demand labels lag recent peaks.",
         "Old-transform replay reduces drift at matched composition.",
         "Vendor-matched feeders preserve the composition effect."),
    ),
    _case(
        "AR-COLD", "cold_chain",
        "Distinguish causes of temperature-excursion drift.",
        ("excursion drift", "defrost schedule", "cargo mix",
         "logger vendor", "door-open lag", "sensor age"),
        ("Drift rose after defrost scheduling changed.",
         "Cargo mix shifted in affected shipments.",
         "Logger vendors are balanced across shipments.",
         "Door-open lags are missing for several stops.",
         "Sensor ages differ across distribution centers.",
         "Old-schedule replay reduces drift at matched cargo mix.",
         "Vendor-matched shipments preserve the cargo-mix effect."),
    ),
)


def build_independent_arbitration_holdout():
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
            "FRESH_V0_36_FROZEN_BEFORE_INDEPENDENT_ARBITRATION_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_independent_arbitration_holdout(artifact):
    if artifact != build_independent_arbitration_holdout():
        raise ValueError("independent_arbitration_holdout_invalid")


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
