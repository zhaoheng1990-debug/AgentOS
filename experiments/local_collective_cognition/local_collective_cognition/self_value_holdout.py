"""Fresh hard/null holdout for self-valued composition v0.38."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "self_value_holdout_v0_38"
CORPUS_ID = "local-self-value-v0-38"
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
        "SV-TURBINE", "wind_turbine",
        "Distinguish causes of power-estimate drift.",
        ("power drift", "control curve", "air density",
         "blade supplier", "yaw lag", "sensor age"),
        ("Drift rose after the control curve changed.",
         "Air density shifted during affected periods.",
         "Blade suppliers are balanced across turbines.",
         "Yaw lags are missing for several intervals.",
         "Sensor ages differ across wind farms.",
         "Old-curve replay reduces drift at matched density.",
         "Supplier-matched turbines preserve the density effect."),
    ),
    _case(
        "SV-LAB", "clinical_laboratory",
        "Distinguish causes of assay-result drift.",
        ("result drift", "reagent protocol", "sample composition",
         "analyzer vendor", "processing lag", "control age"),
        ("Drift rose after the reagent protocol changed.",
         "Sample composition shifted in affected batches.",
         "Analyzer vendors are balanced across laboratories.",
         "Processing lags are missing for several samples.",
         "Control ages differ across instruments.",
         "Old-protocol replay reduces drift within sample strata.",
         "Vendor-matched assays preserve the composition effect."),
    ),
    _case(
        "SV-LOGISTICS", "parcel_logistics",
        "Distinguish causes of delivery-time prediction drift.",
        ("prediction drift", "routing rule", "parcel mix",
         "scanner vendor", "handoff lag", "label maturity"),
        ("Drift rose after routing rules changed.",
         "Parcel mix shifted toward oversized shipments.",
         "Scanner vendors are balanced across depots.",
         "Handoff lags are missing for several routes.",
         "Recent deliveries have immature outcome labels.",
         "Old-rule replay reduces drift within parcel strata.",
         "Vendor-matched depots preserve the parcel-mix effect."),
    ),
    _case(
        "SV-OCEAN", "ocean_monitoring",
        "Distinguish causes of salinity-estimate drift.",
        ("salinity drift", "correction model", "water temperature",
         "float maker", "depth lag", "calibration age"),
        ("Drift rose after the correction model changed.",
         "Water temperature shifted in affected profiles.",
         "Float makers are balanced across regions.",
         "Depth lags are missing for several profiles.",
         "Calibration ages differ across floats.",
         "Old-model replay reduces drift at matched temperature.",
         "Maker-matched profiles preserve the temperature effect."),
    ),
    _case(
        "SV-INSURE", "insurance_pricing",
        "Distinguish causes of loss-score drift.",
        ("score drift", "exposure window", "policy mix",
         "data vendor", "claim lag", "label maturity"),
        ("Drift rose after exposure windows changed.",
         "Policy mix shifted toward new products.",
         "Data vendors are balanced across portfolios.",
         "Claim lags hide several recent losses.",
         "Newest policies have immature labels.",
         "Old-window replay reduces drift within policy strata.",
         "Vendor-matched portfolios preserve the policy-mix effect."),
    ),
    _case(
        "SV-GRID", "microgrid_control",
        "Distinguish causes of load-balance drift.",
        ("balance drift", "dispatch policy", "storage state",
         "inverter vendor", "telemetry lag", "forecast age"),
        ("Drift rose after the dispatch policy changed.",
         "Storage state shifted during affected intervals.",
         "Inverter vendors are balanced across sites.",
         "Telemetry lags are missing for several intervals.",
         "Forecast ages differ across controllers.",
         "Old-policy replay reduces drift at matched storage state.",
         "Vendor-matched sites preserve the storage-state effect."),
    ),
    _case(
        "SV-PRINT", "additive_manufacturing",
        "Distinguish causes of dimensional-error drift.",
        ("error drift", "scan strategy", "powder condition",
         "laser vendor", "cooling lag", "calibration age"),
        ("Drift rose after the scan strategy changed.",
         "Powder condition shifted in affected builds.",
         "Laser vendors are balanced across machines.",
         "Cooling lags are missing for several parts.",
         "Calibration ages differ across machines.",
         "Old-strategy replay reduces drift at matched powder state.",
         "Vendor-matched builds preserve the powder effect."),
    ),
    _case(
        "SV-VOICE", "speech_recognition",
        "Distinguish causes of recognition-error drift.",
        ("error drift", "decoding objective", "speaker mix",
         "microphone vendor", "transcript lag", "label age"),
        ("Drift rose after the decoding objective changed.",
         "Speaker mix shifted toward accented speech.",
         "Microphone vendors are balanced across samples.",
         "Transcript lags hide several recent sessions.",
         "Label ages differ across speaker groups.",
         "Old-objective replay reduces drift within speaker strata.",
         "Vendor-matched samples preserve the speaker-mix effect."),
    ),
)


def build_self_value_holdout():
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
            "FRESH_V0_38_FROZEN_BEFORE_SELF_VALUE_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_self_value_holdout(artifact):
    if artifact != build_self_value_holdout():
        raise ValueError("self_value_holdout_invalid")


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
