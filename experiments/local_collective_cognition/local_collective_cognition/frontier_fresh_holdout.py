"""Fresh v0.27 worlds for gray admission and frontier Cbit evaluation."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "frontier_fresh_holdout_v0_27"
CORPUS_ID = "local-frontier-fresh-v0-27"
PREFLIGHT_VERSION = "frontier_transport_preflight_v0_27"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
PREFLIGHT_REFS = ("benchmark://frontier-transport-preflight-v0-27",)


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
        "FR-PICKING", "warehouse_robotics",
        "Choose a low-cost question that can reduce uncertainty about picking errors.",
        (("O1", "pick error rate"), ("O2", "gripper force"), ("O3", "reflective packaging"),
         ("O4", "camera exposure"), ("O5", "conveyor vibration")),
        (("S1", "Pick errors increased for reflective packages."),
         ("S2", "Camera exposure is fixed across package types."),
         ("S3", "Gripper force was raised before the increase."),
         ("S4", "Conveyor vibration remained within its prior range."),
         ("S5", "Manual review found missed object edges in several error frames.")),
        primary=("O1",), supported=(("O3", "O1"), ("O4", "O1")),
        informative_null=(("O5", "O1"),), constraints=("O2", "O4"),
        counterevidence=("S4", "S5"),
    ),
    _case(
        "FR-WATER", "water_monitoring",
        "Choose the next question that can distinguish contamination from alert drift.",
        (("O1", "contamination alert"), ("O2", "chlorine sensor"), ("O3", "pipe repair"),
         ("O4", "rainfall"), ("O5", "laboratory assay")),
        (("S1", "Contamination alerts rose after a pipe repair."),
         ("S2", "The chlorine sensor was not recalibrated after the repair."),
         ("S3", "Heavy rainfall occurred two days later."),
         ("S4", "The alert rule consumes the chlorine sensor reading."),
         ("S5", "Laboratory assays were negative for three alerted samples.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O2", "O5"),
        counterevidence=("S5",),
    ),
    _case(
        "FR-HEAT", "urban_climate",
        "Choose a question that can explain a nighttime temperature difference.",
        (("O1", "nighttime temperature"), ("O2", "tree canopy"), ("O3", "roof coating"),
         ("O4", "sensor height"), ("O5", "traffic closure")),
        (("S1", "Blocks with less tree canopy show higher nighttime temperature."),
         ("S2", "Reflective roof coating differs between the compared blocks."),
         ("S3", "Sensor height is lower on the warmer blocks."),
         ("S4", "A traffic closure affected both groups equally."),
         ("S5", "The difference narrows when sensors at matched heights are compared.")),
        primary=("O1",), supported=(("O2", "O1"), ("O4", "O1")),
        informative_null=(("O5", "O1"),), constraints=("O3", "O4"),
        counterevidence=("S4", "S5"),
    ),
    _case(
        "FR-CROP", "precision_agriculture",
        "Choose a question that can determine whether a stress map reflects crop state.",
        (("O1", "drone stress map"), ("O2", "leaf reflectance"), ("O3", "irrigation event"),
         ("O4", "cloud shadow"), ("O5", "soil moisture probe")),
        (("S1", "The drone stress map changed after an irrigation event."),
         ("S2", "Cloud shadow crossed part of the field during imaging."),
         ("S3", "Leaf reflectance is the input to the stress map."),
         ("S4", "Soil moisture probes changed only near irrigated rows."),
         ("S5", "The mapped boundary aligns more closely with cloud shadow than with irrigated rows.")),
        primary=("O1",), supported=(("O4", "O1"), ("O3", "O1")),
        informative_null=(("O2", "O1"),), constraints=("O4", "O5"),
        counterevidence=("S5",),
    ),
    _case(
        "FR-FRAUD", "payment_risk",
        "Choose a question that can reduce false fraud alerts.",
        (("O1", "false fraud alert"), ("O2", "device fingerprint"), ("O3", "merchant category"),
         ("O4", "clock drift"), ("O5", "chargeback label")),
        (("S1", "False alerts increased for transactions near midnight."),
         ("S2", "One gateway shows clock drift of several minutes."),
         ("S3", "Device fingerprint rules were unchanged."),
         ("S4", "Merchant-category composition shifted during the same week."),
         ("S5", "Chargeback labels arrive thirty days after the alert decision.")),
        primary=("O1",), supported=(("O4", "O1"), ("O5", "O1")),
        informative_null=(("O3", "O1"),), constraints=("O4", "O5"),
        counterevidence=("S3",),
    ),
    _case(
        "FR-ARCHIVE", "digital_humanities",
        "Choose a question that can localize historical-record linkage errors.",
        (("O1", "record linkage error"), ("O2", "OCR text"), ("O3", "shelf mark"),
         ("O4", "transliteration rule"), ("O5", "page damage")),
        (("S1", "Linkage errors cluster in records containing transliterated names."),
         ("S2", "The OCR system was unchanged."),
         ("S3", "Shelf marks are complete for both linked collections."),
         ("S4", "Page damage removes characters from some names."),
         ("S5", "A newer transliteration rule resolves many reviewed mismatches.")),
        primary=("O1",), supported=(("O4", "O1"), ("O5", "O1")),
        informative_null=(("O3", "O1"),), constraints=("O2", "O5"),
        counterevidence=("S2", "S3"),
    ),
    _case(
        "FR-PACKET", "network_operations",
        "Choose a question that can explain persistent packet loss.",
        (("O1", "packet loss"), ("O2", "queue depth"), ("O3", "route change"),
         ("O4", "sampling interval"), ("O5", "encryption overhead")),
        (("S1", "Packet loss rose after a route change."),
         ("S2", "Queue depth peaks before the recorded loss bursts."),
         ("S3", "The monitoring sampling interval doubled that day."),
         ("S4", "Encryption settings were unchanged."),
         ("S5", "Loss remains elevated after traffic volume is matched.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O5", "O1"),), constraints=("O4",),
        counterevidence=("S4", "S5"),
    ),
    _case(
        "FR-FLOW", "microfluidics",
        "Choose a question that can distinguish physical flow instability from observation artifacts.",
        (("O1", "flow instability"), ("O2", "channel width"), ("O3", "surfactant"),
         ("O4", "pump pulse"), ("O5", "imaging frame rate")),
        (("S1", "Flow instability appears after a pump replacement."),
         ("S2", "The replacement pump has a stronger periodic pulse."),
         ("S3", "Surfactant concentration also changed."),
         ("S4", "Channel width is identical across devices."),
         ("S5", "Changing imaging frame rate shifts the apparent oscillation frequency.")),
        primary=("O1",), supported=(("O4", "O1"), ("O3", "O1")),
        informative_null=(("O2", "O1"),), constraints=("O5",),
        counterevidence=("S4", "S5"),
    ),
    _case(
        "FR-TRANSIT", "public_transport",
        "Choose a question that can explain a route's delay increase.",
        (("O1", "route delay"), ("O2", "station dwell time"), ("O3", "signal priority"),
         ("O4", "passenger load"), ("O5", "GPS smoothing")),
        (("S1", "Route delay increased after a timetable revision."),
         ("S2", "Station dwell time rose at the busiest stops."),
         ("S3", "Signal-priority settings were unchanged."),
         ("S4", "Passenger load increased during the same period."),
         ("S5", "GPS smoothing changes reported delay by less than one minute.")),
        primary=("O1",), supported=(("O2", "O1"), ("O4", "O1")),
        informative_null=(("O5", "O1"),), constraints=("O3",),
        counterevidence=("S3", "S5"),
    ),
    _case(
        "FR-SATELLITE", "earth_observation",
        "Choose a question that can explain a surface-brightness shift.",
        (("O1", "surface brightness"), ("O2", "detector gain"), ("O3", "solar angle"),
         ("O4", "atmospheric aerosol"), ("O5", "reference panel")),
        (("S1", "Measured surface brightness shifted between passes."),
         ("S2", "Detector gain calibration changed between passes."),
         ("S3", "Solar angle differs by less than one degree."),
         ("S4", "Atmospheric aerosol increased on the second pass."),
         ("S5", "The reference panel shows part of the same brightness shift.")),
        primary=("O1",), supported=(("O2", "O1"), ("O4", "O1")),
        informative_null=(("O3", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S5"),
    ),
    _case(
        "FR-FERMENT", "bioprocessing",
        "Choose a question that can explain a fermentation yield drop.",
        (("O1", "fermentation yield"), ("O2", "pH probe"), ("O3", "feed rate"),
         ("O4", "inoculum age"), ("O5", "off-gas sensor")),
        (("S1", "Fermentation yield fell in batches with older inoculum."),
         ("S2", "Feed rate was increased for those batches."),
         ("S3", "The pH probe passed calibration."),
         ("S4", "Off-gas measurements show an earlier metabolic transition."),
         ("S5", "Matched-feed pilot batches still show an inoculum-age difference.")),
        primary=("O1",), supported=(("O4", "O1"), ("O3", "O1")),
        informative_null=(("O2", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S5"),
    ),
    _case(
        "FR-BUILDING", "building_energy",
        "Choose a question that can explain an unexplained energy spike.",
        (("O1", "energy spike"), ("O2", "occupancy schedule"), ("O3", "outdoor temperature"),
         ("O4", "ventilation override"), ("O5", "meter firmware")),
        (("S1", "The energy spike began after a ventilation override."),
         ("S2", "Outdoor temperature was similar to the prior week."),
         ("S3", "Occupancy schedule was unchanged."),
         ("S4", "Meter firmware was updated the previous night."),
         ("S5", "A secondary meter shows a smaller increase than the primary meter.")),
        primary=("O1",), supported=(("O4", "O1"), ("O5", "O1")),
        informative_null=(("O2", "O1"),), constraints=("O3",),
        counterevidence=("S2", "S3", "S5"),
    ),
)


PREFLIGHT_CASES = (
    {
        "case_id": "PF-LIBRARY",
        "domain": "neutral_preflight",
        "research_goal": "Propose two testable questions about scanner count drift.",
        "objects": (("O1", "scanner count"), ("O2", "page size"), ("O3", "duplex mode")),
        "spans": (("S1", "Scanner count changes when duplex mode is enabled."),
                  ("S2", "Page size remains fixed.")),
    },
    {
        "case_id": "PF-IRRIGATION",
        "domain": "neutral_preflight",
        "research_goal": "Propose two testable questions about irrigation timing.",
        "objects": (("O1", "irrigation timing"), ("O2", "soil sensor"), ("O3", "valve delay")),
        "spans": (("S1", "Irrigation starts later after a valve replacement."),
                  ("S2", "The soil sensor threshold is unchanged.")),
    },
)


def build_frontier_preflight():
    commitment = {
        "artifact_version": PREFLIGHT_VERSION,
        "public_surface": {
            "items": [_public_item(value) for value in PREFLIGHT_CASES],
        },
        "case_count": len(PREFLIGHT_CASES),
        "formal_holdout_labels_present": False,
        "semantic_success_claim_allowed": False,
        "evidence_refs": list(PREFLIGHT_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def build_frontier_fresh_holdout():
    items = [_public_item(value) for value in CASES]
    items.sort(key=lambda value: hash_payload([CORPUS_VERSION, value["case_id"]]))
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
        "public_surface": {
            **surface_commitment,
            "surface_hash": hash_payload(surface_commitment),
        },
        "private_provenance": {
            "bindings": bindings,
            "truth_coordinate": "SYNTHETIC_OUTCOME_METADATA",
            "available_to_provider": False,
        },
        "reference_state": "FRESH_V0_27_FROZEN_AFTER_NEUTRAL_PREFLIGHT",
        "v0_26_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_frontier_artifact(artifact, *, preflight=False):
    expected = (
        build_frontier_preflight()
        if preflight else build_frontier_fresh_holdout()
    )
    if artifact != expected:
        raise ValueError("frontier_holdout_artifact_invalid")


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
