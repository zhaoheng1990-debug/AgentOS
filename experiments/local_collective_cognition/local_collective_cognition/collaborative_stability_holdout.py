"""Fresh v0.29 holdout for role-collaborative cognitive stabilization."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "collaborative_stability_holdout_v0_29"
CORPUS_ID = "local-collaborative-stability-v0-29"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


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
        "CL-BATTERY", "battery_diagnostics",
        "Choose questions that explain accelerated capacity loss.",
        (("O1", "capacity loss"), ("O2", "charge ceiling"),
         ("O3", "cell temperature"), ("O4", "impedance estimate"),
         ("O5", "cycle counter")),
        (("S1", "Capacity loss accelerated after the charge ceiling increased."),
         ("S2", "Cell temperature also rose during fast-charge sessions."),
         ("S3", "The impedance estimator version did not change."),
         ("S4", "Cycle counters missed several partial cycles."),
         ("S5", "Matched low-temperature cells lose less capacity at the new ceiling.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "CL-IRRIGATION", "precision_agriculture",
        "Choose questions that explain a field-yield difference.",
        (("O1", "field yield"), ("O2", "irrigation timing"),
         ("O3", "soil salinity"), ("O4", "seed lot"),
         ("O5", "harvest moisture")),
        (("S1", "Lower-yield plots received irrigation later in the day."),
         ("S2", "Those plots also have higher measured soil salinity."),
         ("S3", "The same seed lot was used across all plots."),
         ("S4", "Harvest moisture changes the reported yield conversion."),
         ("S5", "Matched-salinity plots still benefit from earlier irrigation.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "CL-FRAUD", "payment_risk",
        "Choose questions that explain a false-positive increase.",
        (("O1", "false-positive alert"), ("O2", "merchant category"),
         ("O3", "velocity feature"), ("O4", "device score"),
         ("O5", "appeal label")),
        (("S1", "False positives rose for a newly split merchant category."),
         ("S2", "The velocity feature window was shortened in the same release."),
         ("S3", "Device-score calibration remained unchanged."),
         ("S4", "Appeal labels arrive several weeks after transactions."),
         ("S5", "Restoring the old velocity window removes many disputed alerts.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "CL-ASSAY", "protein_assay",
        "Choose questions that explain an assay-signal shift.",
        (("O1", "assay signal"), ("O2", "antibody lot"),
         ("O3", "incubation time"), ("O4", "plate reader"),
         ("O5", "reference standard")),
        (("S1", "Assay signal shifted after an antibody-lot change."),
         ("S2", "Incubation time was extended in the same protocol revision."),
         ("S3", "Plate-reader calibration checks stayed within tolerance."),
         ("S4", "The reference standard degraded slightly during storage."),
         ("S5", "Using the previous antibody lot restores part of the signal.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "CL-WAREHOUSE", "warehouse_operations",
        "Choose questions that explain picking-time inflation.",
        (("O1", "picking time"), ("O2", "slotting map"),
         ("O3", "scanner latency"), ("O4", "picker tenure"),
         ("O5", "order complexity")),
        (("S1", "Picking time rose after a slotting-map revision."),
         ("S2", "Scanner latency increased during the same week."),
         ("S3", "Picker-tenure distribution remained stable."),
         ("S4", "Orders contained more multi-zone combinations."),
         ("S5", "Matched-complexity orders are faster under the old slotting map.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "CL-SEISMIC", "seismic_monitoring",
        "Choose questions that distinguish microseismic activity from artifacts.",
        (("O1", "microseismic alert"), ("O2", "sensor coupling"),
         ("O3", "blasting schedule"), ("O4", "filter version"),
         ("O5", "reference station")),
        (("S1", "Alerts cluster near sensors with recently disturbed coupling."),
         ("S2", "Several clusters follow scheduled blasting windows."),
         ("S3", "The signal-filter version is unchanged."),
         ("S4", "The reference station detects only some alert clusters."),
         ("S5", "Recoupled sensors lose many low-amplitude alerts.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "CL-BIDDING", "advertising_systems",
        "Choose questions that explain a conversion-rate estimate shift.",
        (("O1", "conversion estimate"), ("O2", "bid pacing"),
         ("O3", "attribution window"), ("O4", "creative format"),
         ("O5", "delayed conversion")),
        (("S1", "Conversion estimates shifted after bid pacing became more aggressive."),
         ("S2", "The attribution window was shortened at the same time."),
         ("S3", "Creative-format mix stayed approximately constant."),
         ("S4", "Delayed conversions are missing from the newest cohort."),
         ("S5", "Recomputing with the old window recovers much of the difference.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "CL-WATER", "water_treatment",
        "Choose questions that explain an effluent-turbidity increase.",
        (("O1", "effluent turbidity"), ("O2", "coagulant dose"),
         ("O3", "inlet particle load"), ("O4", "pH probe"),
         ("O5", "settling time")),
        (("S1", "Effluent turbidity rose after the coagulant dose was reduced."),
         ("S2", "Inlet particle load increased during recent rain."),
         ("S3", "The pH probe agrees with a portable reference."),
         ("S4", "Settling time was shortened during peak flow."),
         ("S5", "Matched-load tests improve when the prior coagulant dose is restored.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "CL-SATELLITE", "remote_sensing",
        "Choose questions that explain vegetation-index discontinuities.",
        (("O1", "vegetation index"), ("O2", "atmospheric correction"),
         ("O3", "view angle"), ("O4", "crop rotation"),
         ("O5", "ground reference")),
        (("S1", "Index discontinuities began after an atmospheric-correction update."),
         ("S2", "View angle differs across the joined satellite tracks."),
         ("S3", "Crop rotation did not change at the discontinuity boundary."),
         ("S4", "Ground references cover only the western half of the scene."),
         ("S5", "Applying the old correction reduces the track boundary.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "CL-ASSESSMENT", "education_measurement",
        "Choose questions that explain a score-gap change.",
        (("O1", "score gap"), ("O2", "item format"),
         ("O3", "time limit"), ("O4", "curriculum version"),
         ("O5", "missing response")),
        (("S1", "The score gap changed after more items used a new format."),
         ("S2", "The time limit was shortened in the same administration."),
         ("S3", "Curriculum versions are balanced between compared groups."),
         ("S4", "Missing responses increased near the end of the test."),
         ("S5", "Untimed pilot data reduce the observed score gap.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
)


def build_collaborative_stability_holdout():
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
        "public_surface": {
            **surface_commitment,
            "surface_hash": hash_payload(surface_commitment),
        },
        "private_provenance": {
            "bindings": bindings,
            "truth_coordinate": "SYNTHETIC_OUTCOME_METADATA",
            "available_to_provider": False,
        },
        "reference_state": "FRESH_V0_29_FROZEN_BEFORE_LONG_RUN",
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_collaborative_stability_holdout(artifact):
    if artifact != build_collaborative_stability_holdout():
        raise ValueError("collaborative_stability_holdout_invalid")


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
