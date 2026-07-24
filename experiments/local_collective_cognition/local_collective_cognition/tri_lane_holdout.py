"""Fresh holdout for three-lane replacement safety v0.44."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "tri_lane_holdout_v0_44"
CORPUS_ID = "local-tri-lane-v0-44"
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
        "TL-VOLCANO", "volcano_monitoring",
        "Resolve the source of eruption-alert drift.",
        ("alert drift", "baseline correction", "plume moisture",
         "station vendor", "packet lag", "antenna age"),
        ("Alert drift followed the baseline correction update.",
         "Plume moisture rose during the affected windows.",
         "Station vendors are balanced around the caldera.",
         "Packet logs omit two high-activity intervals.",
         "Antenna ages vary without matching alert drift.",
         "Old-correction replay reduces drift at matched moisture.",
         "Vendor-matched stations preserve the moisture effect."),
        (("O2", "O1"), ("O3", "O1")),
        (("O4", "O1"),), ("O5", "O6"), ("S3", "S4", "S5", "S7"),
    ),
    _case(
        "TL-WAREHOUSE", "warehouse_picking",
        "Resolve the source of pick-time forecast drift.",
        ("pick-time drift", "routing update", "aisle congestion",
         "robot vendor", "scan-order lag", "wheel wear"),
        ("Forecast drift followed the routing update.",
         "Aisle congestion changed only on night shifts.",
         "Robot vendors are balanced across zones.",
         "Exported scans reverse several pick timestamps.",
         "Wheel wear differs without tracking the drift.",
         "Correcting scan order removes residual forecast drift.",
         "Old-routing replay reduces the remaining error."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5", "S7"),
    ),
    _case(
        "TL-CARBON", "carbon_capture",
        "Resolve the source of capture-rate drift.",
        ("capture drift", "solvent schedule", "flue composition",
         "packing supplier", "lab lag", "column age"),
        ("The solvent schedule changed before drift appeared.",
         "Schedule reversion alone gives mixed results.",
         "Flue composition shifts precede every high-drift run.",
         "Packing suppliers are balanced across columns.",
         "Lab reporting lag does not align with process residuals.",
         "Aged columns retain lower capture at matched composition.",
         "Supplier-matched columns preserve the composition effect."),
        (("O3", "O1"), ("O6", "O1")),
        (("O4", "O1"),), ("O2", "O5"), ("S1", "S4", "S5", "S7"),
    ),
    _case(
        "TL-SEQUENCING", "genome_sequencing",
        "Resolve the source of variant-score drift.",
        ("variant drift", "basecaller update", "GC profile",
         "flowcell vendor", "demultiplex lag", "laser age"),
        ("Variant drift followed the basecaller update.",
         "GC profiles shifted only after drift was established.",
         "Flowcell vendors are balanced across runs.",
         "Demultiplex exports misorder several read batches.",
         "Laser ages differ but do not match affected runs.",
         "Correcting batch order removes residual score drift.",
         "Old-basecaller replay reduces the remaining drift."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5"),
    ),
    _case(
        "TL-SOLAR", "solar_farm",
        "Resolve the source of yield-forecast drift.",
        ("yield drift", "curtailment policy", "soiling pattern",
         "inverter vendor", "irradiance lag", "panel age"),
        ("Curtailment policy changed before forecast drift.",
         "Policy replay does not explain cloudy-day residuals.",
         "Soiling patterns precede clear-day drift.",
         "Inverter vendors are balanced across blocks.",
         "Irradiance feeds lag local sensors by nine minutes.",
         "Lag correction removes cloudy-day residual drift.",
         "Panel age varies but matched-age blocks still drift."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S2", "S4", "S7"),
    ),
    _case(
        "TL-AVIATION", "aviation_maintenance",
        "Resolve the source of fault-score drift.",
        ("fault drift", "threshold policy", "mission profile",
         "sensor vendor", "maintenance lag", "harness age"),
        ("Fault drift followed the threshold policy update.",
         "Mission profiles explain only short-haul excursions.",
         "Sensor vendors are balanced across fleets.",
         "Maintenance timestamps omit two component swaps.",
         "Harness age was proposed but fleet matching weakens it.",
         "Bench tests show aged harnesses shift the fault score.",
         "Old-policy replay reduces drift outside mission peaks."),
        (("O2", "O1"), ("O6", "O1")),
        (("O4", "O1"),), ("O3", "O5"), ("S2", "S3", "S4", "S5"),
    ),
    _case(
        "TL-HATCHERY", "fish_hatchery",
        "Resolve the source of growth-estimate drift.",
        ("growth drift", "feed schedule", "oxygen cycle",
         "tank supplier", "sampling lag", "probe age"),
        ("Growth drift followed the feed schedule change.",
         "Oxygen cycles shifted during affected cohorts.",
         "Tank suppliers are mixed across cohorts.",
         "Old-schedule replay removes drift at matched oxygen.",
         "Complete sampling logs show no sampling-lag effect.",
         "Probe ages vary across tanks.",
         "Supplier-matched tanks preserve the oxygen response."),
        (("O2", "O1"), ("O3", "O1")),
        (("O5", "O1"),), ("O4", "O6"), ("S3", "S5", "S6", "S7"),
    ),
    _case(
        "TL-SETTLEMENT", "financial_settlement",
        "Resolve the source of settlement-delay drift.",
        ("delay drift", "netting policy", "message burst",
         "gateway vendor", "clock skew", "hardware age"),
        ("Netting policy changed, but replay is inconclusive.",
         "Message bursts precede every high-delay interval.",
         "Gateway vendors are balanced across venues.",
         "Clock comparisons show persistent regional skew.",
         "Hardware ages differ without tracking delay drift.",
         "Correcting clock skew removes residual delay.",
         "Vendor-matched gateways preserve the burst effect."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S1", "S3", "S5", "S7"),
    ),
)


def build_tri_lane_holdout():
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
            "FRESH_V0_44_FROZEN_BEFORE_TRI_LANE_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_tri_lane_holdout(artifact):
    if artifact != build_tri_lane_holdout():
        raise ValueError("tri_lane_holdout_invalid")


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
