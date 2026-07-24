"""Fresh hard/null holdout for truth/value separation v0.39."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "truth_value_holdout_v0_39"
CORPUS_ID = "local-truth-value-v0-39"
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
        "TV-REACTOR", "chemical_reactor",
        "Distinguish causes of conversion-estimate drift.",
        ("conversion drift", "feed protocol", "catalyst age",
         "vessel vendor", "sampling lag", "sensor age"),
        ("Drift rose after the feed protocol changed.",
         "Catalyst age increased in affected batches.",
         "Vessel vendors are balanced across batches.",
         "Sampling lags are missing for several runs.",
         "Sensor ages differ across production lines.",
         "Old-protocol replay reduces drift at matched catalyst age.",
         "Vendor-matched batches preserve the catalyst-age effect."),
    ),
    _case(
        "TV-ECG", "cardiac_monitoring",
        "Distinguish causes of rhythm-score drift.",
        ("score drift", "filter protocol", "patient activity",
         "electrode vendor", "annotation lag", "device age"),
        ("Drift rose after the filter protocol changed.",
         "Patient activity increased in affected recordings.",
         "Electrode vendors are balanced across recordings.",
         "Annotation lags are missing for several segments.",
         "Device ages differ across clinics.",
         "Old-filter replay reduces drift at matched activity.",
         "Vendor-matched recordings preserve the activity effect."),
    ),
    _case(
        "TV-PORT", "port_operations",
        "Distinguish causes of unloading-time prediction drift.",
        ("prediction drift", "berth rule", "cargo mix",
         "crane vendor", "queue lag", "label maturity"),
        ("Drift rose after berth rules changed.",
         "Cargo mix shifted toward oversized loads.",
         "Crane vendors are balanced across terminals.",
         "Queue lags are missing for several vessel calls.",
         "Recent calls have immature completion labels.",
         "Old-rule replay reduces drift within cargo strata.",
         "Vendor-matched terminals preserve the cargo-mix effect."),
    ),
    _case(
        "TV-SNOW", "snow_hydrology",
        "Distinguish causes of melt-estimate drift.",
        ("melt drift", "albedo model", "air temperature",
         "camera maker", "survey lag", "calibration age"),
        ("Drift rose after the albedo model changed.",
         "Air temperature shifted during affected periods.",
         "Camera makers are balanced across sites.",
         "Survey lags are missing for several transects.",
         "Calibration ages differ across instruments.",
         "Old-model replay reduces drift at matched temperature.",
         "Maker-matched sites preserve the temperature effect."),
    ),
    _case(
        "TV-MORTGAGE", "mortgage_risk",
        "Distinguish causes of delinquency-score drift.",
        ("score drift", "history window", "borrower mix",
         "servicer vendor", "payment lag", "label maturity"),
        ("Drift rose after history windows changed.",
         "Borrower mix shifted toward variable-income applicants.",
         "Servicer vendors are balanced across samples.",
         "Payment lags hide several recent delinquencies.",
         "Newest loans have immature labels.",
         "Old-window replay reduces drift within borrower strata.",
         "Vendor-matched loans preserve the borrower-mix effect."),
    ),
    _case(
        "TV-SOLAR", "solar_farm",
        "Distinguish causes of yield-estimate drift.",
        ("yield drift", "inverter policy", "irradiance pattern",
         "panel vendor", "cleaning lag", "meter age"),
        ("Drift rose after the inverter policy changed.",
         "Irradiance patterns shifted in affected intervals.",
         "Panel vendors are balanced across arrays.",
         "Cleaning lags are missing for several rows.",
         "Meter ages differ across sites.",
         "Old-policy replay reduces drift at matched irradiance.",
         "Vendor-matched arrays preserve the irradiance effect."),
    ),
    _case(
        "TV-TEXTILE", "textile_manufacturing",
        "Distinguish causes of tensile-strength drift.",
        ("strength drift", "weaving recipe", "fiber moisture",
         "loom vendor", "conditioning lag", "gauge age"),
        ("Drift rose after the weaving recipe changed.",
         "Fiber moisture shifted in affected lots.",
         "Loom vendors are balanced across production lines.",
         "Conditioning lags are missing for several samples.",
         "Gauge ages differ across laboratories.",
         "Old-recipe replay reduces drift at matched moisture.",
         "Vendor-matched lines preserve the moisture effect."),
    ),
    _case(
        "TV-TRANSLATE", "machine_translation",
        "Distinguish causes of translation-quality drift.",
        ("quality drift", "decoding policy", "document mix",
         "tokenizer vendor", "review lag", "label age"),
        ("Drift rose after the decoding policy changed.",
         "Document mix shifted toward legal text.",
         "Tokenizer vendors are balanced across samples.",
         "Review lags hide several recent documents.",
         "Label ages differ across domains.",
         "Old-policy replay reduces drift within document strata.",
         "Vendor-matched samples preserve the document-mix effect."),
    ),
)


def build_truth_value_holdout():
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
            "FRESH_V0_39_FROZEN_BEFORE_TRUTH_VALUE_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_truth_value_holdout(artifact):
    if artifact != build_truth_value_holdout():
        raise ValueError("truth_value_holdout_invalid")


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
