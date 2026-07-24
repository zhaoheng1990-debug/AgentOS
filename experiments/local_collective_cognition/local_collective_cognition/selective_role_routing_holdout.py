"""Fresh v0.30 holdout for provider-backed selective role routing."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "selective_role_routing_holdout_v0_30"
CORPUS_ID = "local-selective-role-routing-v0-30"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")
SHADOW_AUDIT_REPLICATION_ID = "R3"


def _case(
    case_id, domain, goal, objects, spans, *,
    primary, supported, informative_null, constraints, counterevidence,
):
    return {
        "case_id": case_id,
        "domain": domain,
        "research_goal": goal,
        "objects": objects,
        "spans": spans,
        "primary": primary,
        "supported": supported,
        "informative_null": informative_null,
        "constraints": constraints,
        "counterevidence": counterevidence,
    }


CASES = (
    _case(
        "RT-THERMAL", "building_sensing",
        "Choose questions that explain an occupancy-count drift.",
        (("O1", "occupancy count"), ("O2", "thermal threshold"),
         ("O3", "ventilation plume"), ("O4", "camera angle"),
         ("O5", "door counter")),
        (("S1", "Occupancy counts rose after the thermal threshold changed."),
         ("S2", "A new ventilation plume crosses the detection region."),
         ("S3", "Camera angle remained fixed."),
         ("S4", "Door-counter records miss some side entrances."),
         ("S5", "Old-threshold replay removes many extra detections.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "RT-FERMENT", "bioprocess_control",
        "Choose questions that explain a fermentation-yield decline.",
        (("O1", "fermentation yield"), ("O2", "feed rate"),
         ("O3", "dissolved oxygen"), ("O4", "inoculum age"),
         ("O5", "offline assay")),
        (("S1", "Yield declined after the feed-rate schedule changed."),
         ("S2", "Dissolved oxygen reaches a lower minimum in the same batches."),
         ("S3", "Inoculum age is balanced across high- and low-yield batches."),
         ("S4", "Offline assays are sampled two hours after the online estimate."),
         ("S5", "Matched-oxygen runs recover yield under the earlier feed schedule.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "RT-PACKET", "network_reliability",
        "Choose questions that explain an increase in packet loss.",
        (("O1", "packet loss"), ("O2", "queue policy"),
         ("O3", "link saturation"), ("O4", "firmware build"),
         ("O5", "sampling interval")),
        (("S1", "Packet loss rose after the queue policy was revised."),
         ("S2", "Link saturation now lasts longer during traffic peaks."),
         ("S3", "Firmware build is unchanged across compared routers."),
         ("S4", "Monitoring samples once per minute and misses short bursts."),
         ("S5", "Replay under the old queue policy reduces loss at matched load.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "RT-CREDIT", "credit_modeling",
        "Choose questions that explain default-score calibration drift.",
        (("O1", "default score"), ("O2", "income normalization"),
         ("O3", "repayment window"), ("O4", "region code"),
         ("O5", "maturity label")),
        (("S1", "Scores drifted after income normalization changed."),
         ("S2", "The repayment observation window was shortened."),
         ("S3", "Region-code proportions stayed stable."),
         ("S4", "Maturity labels are unavailable for the newest loans."),
         ("S5", "Using the old window and normalization reduces calibration error.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "RT-MICROSCOPY", "cell_imaging",
        "Choose questions that explain a cell-count discrepancy.",
        (("O1", "cell count"), ("O2", "segmentation threshold"),
         ("O3", "cell overlap"), ("O4", "objective lens"),
         ("O5", "manual reference")),
        (("S1", "Automated counts changed after a segmentation-threshold update."),
         ("S2", "Cell overlap is higher in the affected wells."),
         ("S3", "The same objective lens was used throughout."),
         ("S4", "Manual references disagree in dense regions."),
         ("S5", "Separating overlapping cells recovers much of the count difference.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "RT-TURBINE", "wind_maintenance",
        "Choose questions that explain a vibration-alarm increase.",
        (("O1", "vibration alarm"), ("O2", "blade pitch"),
         ("O3", "bearing temperature"), ("O4", "wind direction"),
         ("O5", "maintenance log")),
        (("S1", "Vibration alarms increased after blade-pitch recalibration."),
         ("S2", "Bearing temperature also trends upward before alarms."),
         ("S3", "Wind-direction distribution is unchanged."),
         ("S4", "Maintenance logs omit one temporary sensor replacement."),
         ("S5", "Pitch correction reduces alarms at matched wind speed.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "RT-INVENTORY", "retail_operations",
        "Choose questions that explain inventory-record mismatches.",
        (("O1", "inventory mismatch"), ("O2", "return workflow"),
         ("O3", "shelf scan"), ("O4", "product category"),
         ("O5", "cycle count")),
        (("S1", "Mismatches rose after the return workflow changed."),
         ("S2", "Shelf scans now occur less frequently."),
         ("S3", "Product-category mix is stable."),
         ("S4", "Cycle counts happen after overnight replenishment."),
         ("S5", "Replaying returned items through the old workflow removes many mismatches.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "RT-NUTRIENT", "wastewater_control",
        "Choose questions that explain reduced nutrient removal.",
        (("O1", "nutrient removal"), ("O2", "aeration cycle"),
         ("O3", "carbon feed"), ("O4", "temperature probe"),
         ("O5", "laboratory sample")),
        (("S1", "Removal declined after the aeration cycle was shortened."),
         ("S2", "Carbon feed concentration also decreased."),
         ("S3", "The temperature probe agrees with a reference thermometer."),
         ("S4", "Laboratory samples are collected only once per shift."),
         ("S5", "Restoring carbon feed improves removal under the shorter cycle.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "RT-TRANSLATE", "machine_translation",
        "Choose questions that explain terminology-error variation.",
        (("O1", "terminology error"), ("O2", "glossary version"),
         ("O3", "document domain"), ("O4", "decoder setting"),
         ("O5", "reviewer reference")),
        (("S1", "Terminology errors rose after a glossary-version change."),
         ("S2", "The evaluation set contains more legal-domain documents."),
         ("S3", "Decoder settings are unchanged."),
         ("S4", "Reviewer references disagree on several technical terms."),
         ("S5", "Restoring the prior glossary fixes many repeated terms.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "RT-TRAFFIC", "urban_mobility",
        "Choose questions that explain a congestion-index jump.",
        (("O1", "congestion index"), ("O2", "signal timing"),
         ("O3", "road closure"), ("O4", "weather station"),
         ("O5", "probe coverage")),
        (("S1", "The index jumped after signal timing changed."),
         ("S2", "A nearby road closure redirected traffic into the corridor."),
         ("S3", "Weather-station readings show typical conditions."),
         ("S4", "Probe coverage fell in low-speed side streets."),
         ("S5", "Matched-coverage replay still shows the timing-change effect.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
)


def build_selective_role_routing_holdout():
    items = [_public_item(value) for value in CASES]
    items.sort(key=lambda value: hash_payload([
        CORPUS_VERSION, value["case_id"]
    ]))
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
    surface_commitment = {
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
        "shadow_audit_replication_id": SHADOW_AUDIT_REPLICATION_ID,
        "public_surface": {
            **surface_commitment,
            "surface_hash": hash_payload(surface_commitment),
        },
        "private_provenance": {
            "bindings": bindings,
            "truth_coordinate": "SYNTHETIC_OUTCOME_METADATA",
            "available_to_provider": False,
        },
        "reference_state": "FRESH_V0_30_FROZEN_BEFORE_ROUTING_RUN",
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_selective_role_routing_holdout(artifact):
    if artifact != build_selective_role_routing_holdout():
        raise ValueError("selective_role_routing_holdout_invalid")


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
