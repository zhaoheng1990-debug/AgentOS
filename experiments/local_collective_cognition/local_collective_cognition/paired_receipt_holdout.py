"""Fresh holdout for paired common-receipt validation v0.45."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "paired_receipt_holdout_v0_45"
CORPUS_ID = "local-paired-receipt-v0-45"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


def _case(
    case_id, domain, goal, labels, texts, supported,
    informative_null, constraints, counterevidence,
):
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
        "supported": tuple(supported),
        "informative_null": tuple(informative_null),
        "constraints": tuple(constraints),
        "counterevidence": tuple(counterevidence),
    }


CASES = (
    _case(
        "PR-MICROGRID", "microgrid_control",
        "Resolve the source of dispatch-error drift.",
        ("dispatch drift", "controller update", "load volatility",
         "inverter vendor", "meter lag", "battery age"),
        ("Dispatch drift followed the controller update.",
         "Load volatility rose during affected intervals.",
         "Inverter vendors are balanced across feeders.",
         "Meter exports omit several switching events.",
         "Battery ages vary without matching dispatch drift.",
         "Old-controller replay reduces drift at matched load.",
         "Vendor-matched feeders preserve the load effect."),
        (("O2", "O1"), ("O3", "O1")),
        (("O4", "O1"),), ("O5", "O6"), ("S3", "S4", "S5", "S7"),
    ),
    _case(
        "PR-DAIRY", "dairy_processing",
        "Resolve the source of viscosity-estimate drift.",
        ("viscosity drift", "heating recipe", "fat profile",
         "sensor vendor", "sample-order lag", "pump wear"),
        ("Viscosity drift followed the heating-recipe update.",
         "Fat profiles changed only after drift was established.",
         "Sensor vendors are balanced across lines.",
         "Exported samples reverse several collection times.",
         "Pump wear differs without tracking the drift.",
         "Correcting sample order removes residual estimate drift.",
         "Old-recipe replay reduces the remaining drift."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5", "S7"),
    ),
    _case(
        "PR-SEISMIC", "seismic_monitoring",
        "Resolve the source of location-residual drift.",
        ("location drift", "velocity-model update", "noise spectrum",
         "station vendor", "pick lag", "geophone age"),
        ("The velocity model changed before drift appeared.",
         "Model rollback gives mixed residuals.",
         "Noise-spectrum shifts precede every high-drift event.",
         "Station vendors are balanced across arrays.",
         "Pick lag does not align with location residuals.",
         "Aged geophones retain bias at matched noise.",
         "Vendor-matched arrays preserve the noise effect."),
        (("O3", "O1"), ("O6", "O1")),
        (("O4", "O1"),), ("O2", "O5"), ("S1", "S4", "S5", "S7"),
    ),
    _case(
        "PR-RETAIL", "retail_inventory",
        "Resolve the source of stockout-score drift.",
        ("stockout drift", "replenishment update", "demand mix",
         "scanner vendor", "event-order lag", "shelf age"),
        ("Stockout drift followed the replenishment update.",
         "Demand mix changed only after drift was established.",
         "Scanner vendors are balanced across stores.",
         "Inventory exports misorder several receipt events.",
         "Shelf ages differ but do not match affected stores.",
         "Correcting event order removes residual score drift.",
         "Old-policy replay reduces the remaining drift."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5"),
    ),
    _case(
        "PR-WASTEWATER", "wastewater_aeration",
        "Resolve the source of oxygen-demand drift.",
        ("demand drift", "aeration policy", "influent pattern",
         "blower vendor", "lab lag", "diffuser age"),
        ("Aeration policy changed before demand drift.",
         "Policy replay does not explain storm-day residuals.",
         "Influent patterns precede dry-day drift.",
         "Blower vendors are balanced across basins.",
         "Lab reports lag inline sensors by eleven minutes.",
         "Lag correction removes storm-day residual drift.",
         "Diffuser age varies but matched-age basins still drift."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S2", "S4", "S7"),
    ),
    _case(
        "PR-DRONE", "drone_fleet",
        "Resolve the source of navigation-score drift.",
        ("navigation drift", "filter policy", "wind profile",
         "receiver vendor", "maintenance lag", "cable age"),
        ("Navigation drift followed the filter-policy update.",
         "Wind profiles explain only coastal excursions.",
         "Receiver vendors are balanced across fleets.",
         "Maintenance timestamps omit two receiver swaps.",
         "Cable age was proposed but route matching weakens it.",
         "Bench tests show aged cables shift navigation score.",
         "Old-policy replay reduces drift outside wind peaks."),
        (("O2", "O1"), ("O6", "O1")),
        (("O4", "O1"),), ("O3", "O5"), ("S2", "S3", "S4", "S5"),
    ),
    _case(
        "PR-CEMENT", "cement_kiln",
        "Resolve the source of strength-estimate drift.",
        ("strength drift", "burn schedule", "mineral cycle",
         "kiln supplier", "sampling lag", "thermocouple age"),
        ("Strength drift followed the burn-schedule change.",
         "Mineral cycles shifted during affected lots.",
         "Kiln suppliers are mixed across plants.",
         "Old-schedule replay removes drift at matched minerals.",
         "Complete logs show no sampling-lag effect.",
         "Thermocouple ages vary across kilns.",
         "Supplier-matched kilns preserve the mineral response."),
        (("O2", "O1"), ("O3", "O1")),
        (("O5", "O1"),), ("O4", "O6"), ("S3", "S5", "S6", "S7"),
    ),
    _case(
        "PR-BUOY", "ocean_buoy_network",
        "Resolve the source of wave-height drift.",
        ("wave drift", "filter update", "storm burst",
         "modem vendor", "clock skew", "mooring age"),
        ("Filter policy changed, but replay is inconclusive.",
         "Storm bursts precede every high-drift interval.",
         "Modem vendors are balanced across regions.",
         "Clock comparisons show persistent buoy skew.",
         "Mooring ages differ without tracking wave drift.",
         "Correcting clock skew removes residual drift.",
         "Vendor-matched buoys preserve the storm effect."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S1", "S3", "S5", "S7"),
    ),
)


def build_paired_receipt_holdout():
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
            "FRESH_V0_45_FROZEN_BEFORE_PAIRED_RECEIPT_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_paired_receipt_holdout(artifact):
    if artifact != build_paired_receipt_holdout():
        raise ValueError("paired_receipt_holdout_invalid")


def _public_item(value):
    return {
        "case_id": value["case_id"],
        "domain": value["domain"],
        "research_goal": value["research_goal"],
        "focal_object_id": value["primary"][0],
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
