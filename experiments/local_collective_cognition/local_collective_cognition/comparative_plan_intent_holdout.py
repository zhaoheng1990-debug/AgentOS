"""Fresh v0.31 holdout for single-call comparative plan intent."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "comparative_plan_intent_holdout_v0_31"
CORPUS_ID = "local-comparative-plan-intent-v0-31"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


def _case(
    case_id, domain, goal, objects, spans, *,
    primary, supported, informative_null, constraints, counterevidence,
):
    return {
        "case_id": case_id, "domain": domain, "research_goal": goal,
        "objects": objects, "spans": spans, "primary": primary,
        "supported": supported, "informative_null": informative_null,
        "constraints": constraints, "counterevidence": counterevidence,
    }


CASES = (
    _case(
        "PI-COOLING", "data_center_control",
        "Choose questions that explain a cooling-power increase.",
        (("O1", "cooling power"), ("O2", "airflow setpoint"),
         ("O3", "rack inlet temperature"), ("O4", "humidity sensor"),
         ("O5", "workload meter")),
        (("S1", "Cooling power rose after the airflow setpoint changed."),
         ("S2", "Rack inlet temperatures became more uneven."),
         ("S3", "Humidity-sensor calibration is unchanged."),
         ("S4", "The workload meter undercounts burst jobs."),
         ("S5", "Matched-load replay at the old setpoint lowers cooling power.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "PI-CATALYST", "chemical_processing",
        "Choose questions that explain a reaction-selectivity decline.",
        (("O1", "reaction selectivity"), ("O2", "catalyst age"),
         ("O3", "feed impurity"), ("O4", "pressure gauge"),
         ("O5", "product assay")),
        (("S1", "Selectivity declines with older catalyst batches."),
         ("S2", "Feed impurity increased during the same campaign."),
         ("S3", "The pressure gauge agrees with a reference."),
         ("S4", "Product assays are sampled after a long transfer delay."),
         ("S5", "Fresh catalyst improves selectivity at matched impurity.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "PI-ROBOT", "robotic_fulfillment",
        "Choose questions that explain grasp-failure variation.",
        (("O1", "grasp failure"), ("O2", "gripper force"),
         ("O3", "package reflectivity"), ("O4", "arm firmware"),
         ("O5", "operator override")),
        (("S1", "Failures rose after gripper-force tuning."),
         ("S2", "Reflective packages fail more often."),
         ("S3", "Arm firmware is unchanged."),
         ("S4", "Operator overrides hide some failed attempts."),
         ("S5", "Old force settings recover several reflective packages.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "PI-CLAIMS", "insurance_analytics",
        "Choose questions that explain a claim-severity estimate shift.",
        (("O1", "severity estimate"), ("O2", "repair index"),
         ("O3", "claim mix"), ("O4", "region code"),
         ("O5", "settlement delay")),
        (("S1", "Severity estimates changed after the repair index update."),
         ("S2", "The claim mix shifted toward more complex repairs."),
         ("S3", "Region-code distribution remained stable."),
         ("S4", "Recent claims have not reached final settlement."),
         ("S5", "Using the old index reduces the estimate shift.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "PI-ACOUSTIC", "ecological_monitoring",
        "Choose questions that explain a species-call detection change.",
        (("O1", "call detection"), ("O2", "noise filter"),
         ("O3", "rain intensity"), ("O4", "microphone model"),
         ("O5", "manual annotation")),
        (("S1", "Detections changed after a noise-filter update."),
         ("S2", "Rain intensity was higher in the affected recordings."),
         ("S3", "Microphone models are balanced across sites."),
         ("S4", "Manual annotators disagree on faint calls."),
         ("S5", "Old-filter replay recovers many calls in rainy segments.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "PI-GRID", "power_grid_operations",
        "Choose questions that explain frequency-alarm inflation.",
        (("O1", "frequency alarm"), ("O2", "droop setting"),
         ("O3", "solar ramp"), ("O4", "meter firmware"),
         ("O5", "dispatch timestamp")),
        (("S1", "Alarms rose after a droop-setting revision."),
         ("S2", "Solar ramps became steeper during the same period."),
         ("S3", "Meter firmware is unchanged."),
         ("S4", "Dispatch timestamps lag some control actions."),
         ("S5", "Matched-ramp simulations reduce alarms under the old droop setting.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "PI-ADHERENCE", "medication_monitoring",
        "Choose questions that explain adherence-score drift.",
        (("O1", "adherence score"), ("O2", "reminder schedule"),
         ("O3", "refill delay"), ("O4", "device version"),
         ("O5", "self-report")),
        (("S1", "Scores shifted after the reminder schedule changed."),
         ("S2", "Refill delays increased in the same cohort."),
         ("S3", "Device-version mix remained stable."),
         ("S4", "Self-reports overstate several verified doses."),
         ("S5", "Restoring the old reminder schedule improves verified adherence.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "PI-SEARCH", "search_ranking",
        "Choose questions that explain relevance-score drift.",
        (("O1", "relevance score"), ("O2", "query rewrite"),
         ("O3", "document freshness"), ("O4", "language detector"),
         ("O5", "click label")),
        (("S1", "Scores drifted after a query-rewrite update."),
         ("S2", "The document set contains more stale pages."),
         ("S3", "Language-detector calibration is unchanged."),
         ("S4", "Click labels are position biased."),
         ("S5", "Old-rewrite replay reduces drift on freshness-matched pages.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
)


def build_comparative_plan_intent_holdout():
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
        "surface_version": CORPUS_VERSION, "items": items,
        "private_outcomes_exposed": False,
    }
    commitment = {
        "artifact_version": CORPUS_VERSION, "corpus_id": CORPUS_ID,
        "case_count": len(CASES),
        "domain_count": len({value["domain"] for value in CASES}),
        "replication_ids": list(REPLICATION_IDS),
        "public_surface": {
            **surface, "surface_hash": hash_payload(surface)
        },
        "private_provenance": {
            "bindings": bindings,
            "truth_coordinate": "SYNTHETIC_OUTCOME_METADATA",
            "available_to_provider": False,
        },
        "reference_state": "FRESH_V0_31_FROZEN_BEFORE_PLAN_INTENT_RUN",
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False, "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_comparative_plan_intent_holdout(artifact):
    if artifact != build_comparative_plan_intent_holdout():
        raise ValueError("comparative_plan_intent_holdout_invalid")


def _public_item(value):
    return {
        "case_id": value["case_id"], "domain": value["domain"],
        "research_goal": value["research_goal"],
        "object_registry": [
            {"object_id": object_id, "label": label}
            for object_id, label in value["objects"]
        ],
        "evidence_spans": [
            {"span_id": span_id, "text": text,
             "text_hash": hash_payload(text)}
            for span_id, text in value["spans"]
        ],
    }
