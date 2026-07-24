"""Fresh holdout for review-ready routing validation v0.48."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "review_ready_holdout_v0_48"
CORPUS_ID = "local-review-ready-v0-48"
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
        "RR-BREWERY", "brewery_fermentation",
        "Resolve the source of fermentation-yield drift.",
        ("yield drift", "fermentation schedule", "yeast exposure",
         "vessel vendor", "metrology lag", "agitator age"),
        ("Yield drift followed the fermentation-schedule update.",
         "Yeast exposure peaks precede warm-route drift.",
         "Vessel vendors are balanced across breweries.",
         "Sampling logs omit two synchronization resets.",
         "Agitator age differs without matching drift.",
         "Old-policy replay removes matched-temperature drift.",
         "Vendor-matched breweries preserve the yeast effect."),
        (("O2", "O1"), ("O3", "O1")),
        (("O4", "O1"),), ("O5", "O6"), ("S3", "S4", "S5", "S7"),
    ),
    _case(
        "RR-COATING", "battery_coating",
        "Resolve the source of coating-thickness drift.",
        ("thickness drift", "coating recipe", "slurry mix",
         "gauge supplier", "inspection lag", "die wear"),
        ("Drift followed the coating-recipe revision.",
         "Slurry mix changed after the first drift interval.",
         "Gauge suppliers are balanced across lines.",
         "Sample exports reverse several coating times.",
         "Die wear varies without tracking drift.",
         "Correcting sample order removes residual drift.",
         "Old-recipe replay reduces the remaining drift."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5", "S7"),
    ),
    _case(
        "RR-TRAFFIC", "traffic_signal_control",
        "Resolve the source of queue-time drift.",
        ("queue drift", "signal policy", "event demand",
         "detector vendor", "phase lag", "controller age"),
        ("The signal policy changed before drift.",
         "Policy replay gives mixed queue residuals.",
         "Event demand precedes every high-drift junction.",
         "Detector vendors are balanced across corridors.",
         "Phase lag does not align with queue drift.",
         "Older controllers retain bias at matched event demand.",
         "Vendor-matched junctions preserve the demand effect."),
        (("O3", "O1"), ("O6", "O1")),
        (("O4", "O1"),), ("O2", "O5"), ("S1", "S4", "S5", "S7"),
    ),
    _case(
        "RR-ASSAY", "protein_assay",
        "Resolve the source of binding-score drift.",
        ("binding drift", "assay update", "sample mix",
         "reagent vendor", "plate-order lag", "kit age"),
        ("Drift followed the assay update.",
         "Sample mix changed after drift was established.",
         "Reagent vendors are balanced across batches.",
         "Plate exports misorder several measurement steps.",
         "Kit ages differ but do not match affected plates.",
         "Correcting event order removes residual drift.",
         "Old-assay replay reduces the remaining drift."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5"),
    ),
    _case(
        "RR-BAGGAGE", "airport_baggage",
        "Resolve the source of transfer-time drift.",
        ("transfer drift", "routing policy", "connection pattern",
         "scanner vendor", "handoff lag", "belt age"),
        ("Routing policy changed before transfer drift.",
         "Policy replay does not explain tight-connection residuals.",
         "Connection patterns precede normal-connection drift.",
         "Scanner vendors are balanced across terminals.",
         "Handoff reports lag inline scanners by eight minutes.",
         "Handoff correction removes tight-connection residual drift.",
         "Belt age varies but matched-age terminals still drift."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S2", "S4", "S7"),
    ),
    _case(
        "RR-GREENHOUSE", "greenhouse_climate",
        "Resolve the source of humidity-score drift.",
        ("humidity drift", "ventilation policy", "solar exposure",
         "sensor vendor", "maintenance lag", "fan age"),
        ("Drift followed the ventilation-policy update.",
         "Solar exposure explains only midday errors.",
         "Sensor vendors are balanced across greenhouse blocks.",
         "Maintenance logs omit two sensor replacements.",
         "Fan age was proposed but block matching weakens it.",
         "Bench tests show aged fans shift humidity score.",
         "Old-policy replay reduces drift outside midday periods."),
        (("O2", "O1"), ("O6", "O1")),
        (("O4", "O1"),), ("O3", "O5"), ("S2", "S3", "S4", "S5"),
    ),
    _case(
        "RR-ETCH", "semiconductor_etch",
        "Resolve the source of etch-depth drift.",
        ("depth drift", "plasma schedule", "wafer cycle",
         "chamber supplier", "metrology lag", "electrode age"),
        ("Drift followed the plasma-schedule change.",
         "Wafer cycles shifted during affected lots.",
         "Chamber suppliers are mixed across fabs.",
         "Old-schedule replay removes drift at matched wafer.",
         "Complete logs show no metrology-lag effect.",
         "Electrode ages vary across chambers.",
         "Supplier-matched fabs preserve the wafer response."),
        (("O2", "O1"), ("O3", "O1")),
        (("O5", "O1"),), ("O4", "O6"), ("S3", "S5", "S6", "S7"),
    ),
    _case(
        "RR-PRICING", "freight_pricing",
        "Resolve the source of quote-estimate drift.",
        ("quote drift", "pricing update", "route regime",
         "data vendor", "currency skew", "contract age"),
        ("Pricing policy changed, but replay is inconclusive.",
         "Route regimes precede every high-drift interval.",
         "Data vendors are balanced across markets.",
         "Currency comparisons show persistent quote skew.",
         "Contract ages differ without tracking quote drift.",
         "Correcting currency skew removes residual drift.",
         "Vendor-matched markets preserve the route effect."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S1", "S3", "S5", "S7"),
    ),
)


def build_review_ready_holdout():
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
            "FRESH_V0_48_FROZEN_BEFORE_REVIEW_READY_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_review_ready_holdout(artifact):
    if artifact != build_review_ready_holdout():
        raise ValueError("review_ready_holdout_invalid")


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



