"""Fresh v0.28 holdout for order/context stability of frontier gray cognition."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "frontier_stability_holdout_v0_28"
CORPUS_ID = "local-frontier-stability-v0-28"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)


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
        "ST-OPTICAL", "industrial_inspection",
        "Choose questions that can reduce uncertainty about defect flags.",
        (("O1", "defect flag"), ("O2", "lens focus"), ("O3", "surface texture"),
         ("O4", "lighting angle"), ("O5", "manual audit")),
        (("S1", "Defect flags rose on rough-textured parts."),
         ("S2", "Lighting angle changed on the same production shift."),
         ("S3", "Lens focus checks remained within tolerance."),
         ("S4", "Manual audit rejects fewer parts than the optical system."),
         ("S5", "Reimaging at the old lighting angle removes many flags.")),
        primary=("O1",), supported=(("O3", "O1"), ("O4", "O1")),
        informative_null=(("O2", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "ST-MARINE", "marine_monitoring",
        "Choose questions that distinguish an algal bloom from sensor artifacts.",
        (("O1", "algal bloom alert"), ("O2", "chlorophyll sensor"), ("O3", "turbidity"),
         ("O4", "tide phase"), ("O5", "laboratory sample")),
        (("S1", "Bloom alerts increased during a period of high turbidity."),
         ("S2", "The chlorophyll sensor was last calibrated before that period."),
         ("S3", "Tide phase alternated across alert and non-alert observations."),
         ("S4", "Laboratory samples confirm elevated algae at two alert sites."),
         ("S5", "Several alerts disappear after turbidity correction.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S5"),
    ),
    _case(
        "ST-CLOUD", "cloud_operations",
        "Choose questions that explain a cloud-cost spike.",
        (("O1", "cloud cost spike"), ("O2", "autoscaling policy"), ("O3", "retry storm"),
         ("O4", "price tier"), ("O5", "telemetry lag")),
        (("S1", "Cloud cost rose after an autoscaling policy update."),
         ("S2", "A retry storm increased request volume in the same window."),
         ("S3", "The price tier was unchanged."),
         ("S4", "Telemetry arrives fifteen minutes late."),
         ("S5", "Replay without retries removes most of the estimated cost increase.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S5"),
    ),
    _case(
        "ST-LEGAL", "document_intelligence",
        "Choose questions that localize clause-extraction errors.",
        (("O1", "clause extraction error"), ("O2", "scan quality"), ("O3", "template version"),
         ("O4", "footnote layout"), ("O5", "reviewer label")),
        (("S1", "Extraction errors cluster in a new template version."),
         ("S2", "The new template places footnotes inside clause boundaries."),
         ("S3", "Scan quality is similar across templates."),
         ("S4", "Reviewer labels disagree most on footnoted clauses."),
         ("S5", "Removing footnotes restores many extracted boundaries.")),
        primary=("O1",), supported=(("O3", "O1"), ("O4", "O1")),
        informative_null=(("O2", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4"),
    ),
    _case(
        "ST-SOIL", "soil_science",
        "Choose questions that clarify a soil-carbon estimate difference.",
        (("O1", "soil carbon estimate"), ("O2", "moisture correction"), ("O3", "sampling depth"),
         ("O4", "field slope"), ("O5", "laboratory calibration")),
        (("S1", "Carbon estimates are higher under a new moisture correction."),
         ("S2", "Sampling depth also increased in the new survey."),
         ("S3", "Field slope is balanced between survey groups."),
         ("S4", "Laboratory calibration is shared across samples."),
         ("S5", "Recomputing at matched depth reduces the estimate difference.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S5"),
    ),
    _case(
        "ST-RAIL", "rail_engineering",
        "Choose questions that explain accelerated wheel wear.",
        (("O1", "wheel wear"), ("O2", "braking profile"), ("O3", "track curvature"),
         ("O4", "load sensor"), ("O5", "maintenance interval")),
        (("S1", "Wheel wear rose after a braking-profile update."),
         ("S2", "The affected service uses tighter track curvature."),
         ("S3", "Load-sensor readings stayed within their prior range."),
         ("S4", "Maintenance interval was extended by one week."),
         ("S5", "Wear remains elevated after matching measured load.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S5"),
    ),
    _case(
        "ST-POLYMER", "materials_processing",
        "Choose questions that distinguish viscosity drift from measurement drift.",
        (("O1", "viscosity drift"), ("O2", "catalyst age"), ("O3", "shear rate"),
         ("O4", "thermometer bias"), ("O5", "solvent lot")),
        (("S1", "Viscosity drift increased with older catalyst."),
         ("S2", "A thermometer offset appeared during those batches."),
         ("S3", "Shear rate was held constant."),
         ("S4", "Solvent lot changed halfway through the run."),
         ("S5", "Correcting temperature removes part of the apparent drift.")),
        primary=("O1",), supported=(("O2", "O1"), ("O4", "O1")),
        informative_null=(("O3", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S5"),
    ),
    _case(
        "ST-CHURN", "customer_analytics",
        "Choose questions that explain churn-score drift.",
        (("O1", "churn score drift"), ("O2", "plan migration"), ("O3", "support tickets"),
         ("O4", "feature version"), ("O5", "label window")),
        (("S1", "Churn scores shifted after a plan migration."),
         ("S2", "The feature version was unchanged."),
         ("S3", "Support-ticket volume increased slightly."),
         ("S4", "The outcome label window was shortened."),
         ("S5", "Restoring the old label window removes much of the drift.")),
        primary=("O1",), supported=(("O2", "O1"), ("O5", "O1")),
        informative_null=(("O3", "O1"),), constraints=("O4",),
        counterevidence=("S2", "S5"),
    ),
    _case(
        "ST-QUEUE", "health_operations",
        "Choose questions that explain an increase in waiting time.",
        (("O1", "waiting time"), ("O2", "triage protocol"), ("O3", "staffing mix"),
         ("O4", "arrival burst"), ("O5", "clock synchronization")),
        (("S1", "Waiting time rose after a triage-protocol revision."),
         ("S2", "The staffing mix shifted toward fewer senior staff."),
         ("S3", "Arrival bursts occurred in both compared periods."),
         ("S4", "Clock synchronization was verified."),
         ("S5", "The increase persists after arrival volume is matched.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O5", "O1"),), constraints=("O4",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "ST-SOLAR", "renewable_energy",
        "Choose questions that explain solar-power forecast errors.",
        (("O1", "forecast error"), ("O2", "cloud camera"), ("O3", "inverter clipping"),
         ("O4", "horizon mask"), ("O5", "reference meter")),
        (("S1", "Forecast errors increased near peak generation."),
         ("S2", "Inverter clipping begins in the same interval."),
         ("S3", "The horizon mask omits a new obstruction."),
         ("S4", "Cloud-camera calibration is unchanged."),
         ("S5", "The reference meter confirms less power than the forecast expects.")),
        primary=("O1",), supported=(("O3", "O1"), ("O4", "O1")),
        informative_null=(("O2", "O1"),), constraints=("O5",),
        counterevidence=("S4",),
    ),
    _case(
        "ST-DELIVERY", "last_mile_logistics",
        "Choose questions that explain missed deliveries.",
        (("O1", "missed delivery"), ("O2", "address parser"), ("O3", "driver route"),
         ("O4", "building access"), ("O5", "status scan")),
        (("S1", "Missed deliveries cluster at buildings with restricted access."),
         ("S2", "The address parser truncates some unit identifiers."),
         ("S3", "Driver routes are unchanged."),
         ("S4", "Status scans are sometimes recorded before access attempts."),
         ("S5", "Manual address correction recovers several deliveries.")),
        primary=("O1",), supported=(("O2", "O1"), ("O4", "O1")),
        informative_null=(("O3", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4"),
    ),
    _case(
        "ST-SPEECH", "speech_recognition",
        "Choose questions that explain transcript-error variation.",
        (("O1", "transcript error"), ("O2", "microphone gain"), ("O3", "accent mix"),
         ("O4", "codec version"), ("O5", "human reference")),
        (("S1", "Transcript errors increased after a codec update."),
         ("S2", "Accent mix shifted in the same evaluation batch."),
         ("S3", "Microphone gain was normalized."),
         ("S4", "Human references disagree on several accented phrases."),
         ("S5", "Re-encoding with the old codec removes some errors.")),
        primary=("O1",), supported=(("O3", "O1"), ("O4", "O1")),
        informative_null=(("O2", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4"),
    ),
)


def build_frontier_stability_holdout():
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
        "replication_ids": ["R1", "R2"],
        "public_surface": {
            **surface_commitment,
            "surface_hash": hash_payload(surface_commitment),
        },
        "private_provenance": {
            "bindings": bindings,
            "truth_coordinate": "SYNTHETIC_OUTCOME_METADATA",
            "available_to_provider": False,
        },
        "reference_state": "FRESH_V0_28_FROZEN_BEFORE_STABILITY_RUN",
        "v0_27_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_frontier_stability_holdout(artifact):
    if artifact != build_frontier_stability_holdout():
        raise ValueError("frontier_stability_holdout_invalid")


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
