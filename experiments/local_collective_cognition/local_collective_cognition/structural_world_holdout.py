"""Fresh synthetic object worlds for structure-first problem emergence v0.26."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "structural_world_expansion_holdout_v0_26"
CORPUS_ID = "local-structural-world-expansion-v0-26"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)


def _case(
    case_id,
    domain,
    research_goal,
    objects,
    spans,
    *,
    primary,
    constraints,
    relations,
    unresolved,
    invariants=(),
    counterevidence=(),
):
    return {
        "case_id": case_id,
        "domain": domain,
        "research_goal": research_goal,
        "objects": objects,
        "spans": spans,
        "primary": primary,
        "constraints": constraints,
        "relations": relations,
        "unresolved": unresolved,
        "invariants": invariants,
        "counterevidence": counterevidence,
    }


CASE_SPECS = (
    _case(
        "SW-ADHESIVE",
        "manufacturing",
        "Identify the next question that can explain variation in bond strength.",
        (
            ("O1", "bond strength"), ("O2", "curing temperature"),
            ("O3", "ambient humidity"), ("O4", "catalyst batch"),
            ("O5", "line speed"), ("O6", "fixed-humidity lab protocol"),
        ),
        (
            ("S1", "The investigation target is the shift-to-shift change in bond strength."),
            ("S2", "Curing temperature increased before bond strength improved on the production line."),
            ("S3", "Ambient humidity rose during the same shift."),
            ("S4", "A new catalyst batch entered service at the start of that shift."),
            ("S5", "Line speed remained fixed across the compared shifts."),
            ("S6", "Under a fixed-humidity lab protocol, increasing temperature did not improve bond strength."),
        ),
        primary=("O1",),
        constraints=("O3", "O4", "O6"),
        relations=(
            ("O2", "PRECEDES", "O1"), ("O3", "PRECEDES", "O1"),
            ("O4", "PRECEDES", "O1"), ("O6", "CONSTRAINS", "O2"),
        ),
        unresolved=(("O2", "O1"), ("O4", "O1")),
        invariants=("O5",),
        counterevidence=("S6",),
    ),
    _case(
        "SW-IDENTITY",
        "data_systems",
        "Identify the next question needed to make repeat-visitor counts interpretable.",
        (
            ("O1", "repeat-visitor count"), ("O2", "browser cookie"),
            ("O3", "verified email"), ("O4", "shared device"),
            ("O5", "identity rule IR-7"), ("O6", "consent reset"),
        ),
        (
            ("S1", "The report requests repeat-visitor count under identity rule IR-7, but the IR-7 catalog entry is unavailable."),
            ("S2", "The current pipeline links visits with a browser cookie."),
            ("S3", "A consent reset deletes the browser cookie for returning visitors."),
            ("S4", "Verified email exists only for a subset of visitors."),
            ("S5", "Shared devices can place several people behind one browser cookie."),
            ("S6", "The raw visit-event count is stable across the compared reports."),
        ),
        primary=("O1", "O5"),
        constraints=("O4", "O5", "O6"),
        relations=(
            ("O2", "MEASURES", "O1"), ("O3", "ALTERNATIVE_TO", "O2"),
            ("O4", "CONSTRAINS", "O2"), ("O6", "AFFECTS", "O2"),
        ),
        unresolved=(("O2", "O1"), ("O3", "O1"), ("O5", "O1")),
        invariants=(),
        counterevidence=("S1",),
    ),
    _case(
        "SW-BIOMARKER",
        "clinical_research",
        "Identify the next study question about the apparent biomarker-response link.",
        (
            ("O1", "response endpoint"), ("O2", "baseline biomarker"),
            ("O3", "assigned dose"), ("O4", "assay lot"),
            ("O5", "enrollment site"), ("O6", "concomitant therapy"),
        ),
        (
            ("S1", "The observed association is between baseline biomarker and the response endpoint."),
            ("S2", "The assigned dose was fixed within each randomized arm."),
            ("S3", "The assay lot changed halfway through enrollment."),
            ("S4", "Enrollment-site composition also changed halfway through enrollment."),
            ("S5", "Concomitant therapy was recorded but not used in the reported stratification."),
            ("S6", "The association weakens when only the first assay lot is examined."),
        ),
        primary=("O1", "O2"),
        constraints=("O4", "O5", "O6"),
        relations=(
            ("O2", "AFFECTS", "O1"), ("O4", "MEASURES", "O2"),
            ("O5", "CONSTRAINS", "O1"), ("O6", "AFFECTS", "O1"),
        ),
        unresolved=(("O2", "O1"), ("O4", "O1")),
        invariants=("O3",),
        counterevidence=("S6",),
    ),
    _case(
        "SW-WETLAND",
        "ecology",
        "Identify the next question that separates competing explanations of seedling survival.",
        (
            ("O1", "seedling survival"), ("O2", "water level"),
            ("O3", "salinity"), ("O4", "grazing exclusion"),
            ("O5", "plot elevation"), ("O6", "census interval"),
        ),
        (
            ("S1", "Seedling survival increased in plots assigned a higher water level."),
            ("S2", "Salinity fell in the same plots after an upstream gate change."),
            ("S3", "Grazing exclusion was applied to every plot before the comparison."),
            ("S4", "Plot elevation differs between the high- and low-water groups."),
            ("S5", "The census interval was identical for every plot."),
            ("S6", "Within the narrow middle-elevation band, the survival difference is small."),
        ),
        primary=("O1",),
        constraints=("O3", "O4", "O5"),
        relations=(
            ("O2", "AFFECTS", "O1"), ("O3", "AFFECTS", "O1"),
            ("O4", "CONSTRAINS", "O1"), ("O5", "CONSTRAINS", "O2"),
        ),
        unresolved=(("O2", "O1"), ("O3", "O1")),
        invariants=("O6",),
        counterevidence=("S6",),
    ),
    _case(
        "SW-COLDCHAIN",
        "supply_chain",
        "Identify the next question needed to diagnose spoilage alerts.",
        (
            ("O1", "spoilage alert"), ("O2", "temperature sensor"),
            ("O3", "route duration"), ("O4", "calibration drift"),
            ("O5", "refrigeration door opening"), ("O6", "manual inspection"),
        ),
        (
            ("S1", "Spoilage alerts increased after a longer delivery route was introduced."),
            ("S2", "The temperature sensor also passed its nominal recalibration date."),
            ("S3", "Door-opening duration increased at two transfer depots."),
            ("S4", "Manual inspection did not find spoilage in several alerted loads."),
            ("S5", "The alert rule consumes the temperature sensor reading."),
            ("S6", "Loads without alerts followed the same route duration on three days."),
        ),
        primary=("O1",),
        constraints=("O4", "O5", "O6"),
        relations=(
            ("O2", "MEASURES", "O1"), ("O3", "PRECEDES", "O1"),
            ("O4", "AFFECTS", "O2"), ("O5", "AFFECTS", "O2"),
        ),
        unresolved=(("O3", "O1"), ("O4", "O1"), ("O5", "O1")),
        invariants=(),
        counterevidence=("S4", "S6"),
    ),
    _case(
        "SW-LATENCY",
        "software_operations",
        "Identify the next question that can localize the tail-latency regression.",
        (
            ("O1", "tail latency"), ("O2", "cache hit rate"),
            ("O3", "service deployment"), ("O4", "traffic mix"),
            ("O5", "clock skew"), ("O6", "trace sampling"),
        ),
        (
            ("S1", "Tail latency rose immediately after a service deployment."),
            ("S2", "Cache hit rate fell during the same interval."),
            ("S3", "The traffic mix shifted toward larger requests one hour earlier."),
            ("S4", "Clock skew was detected in one region."),
            ("S5", "Trace sampling excludes the largest one percent of requests."),
            ("S6", "A rollback restored the old service binary but tail latency remained elevated."),
        ),
        primary=("O1",),
        constraints=("O4", "O5", "O6"),
        relations=(
            ("O3", "PRECEDES", "O1"), ("O2", "AFFECTS", "O1"),
            ("O4", "AFFECTS", "O1"), ("O6", "CONSTRAINS", "O1"),
        ),
        unresolved=(("O2", "O1"), ("O4", "O1")),
        invariants=(),
        counterevidence=("S6",),
    ),
    _case(
        "SW-TUTORING",
        "education",
        "Identify the next question needed to interpret the reported score gain.",
        (
            ("O1", "score gain"), ("O2", "tutoring program"),
            ("O3", "prior score"), ("O4", "test form"),
            ("O5", "attendance"), ("O6", "instructor assignment"),
        ),
        (
            ("S1", "Students offered the tutoring program show a larger score gain."),
            ("S2", "Program enrollment was voluntary rather than randomized."),
            ("S3", "Prior scores were higher among students who enrolled."),
            ("S4", "A new test form was used at two participating schools."),
            ("S5", "Attendance was recorded only for enrolled students."),
            ("S6", "The same instructor assignment policy was used in every school."),
        ),
        primary=("O1", "O2"),
        constraints=("O3", "O4", "O5"),
        relations=(
            ("O2", "AFFECTS", "O1"), ("O3", "CONSTRAINS", "O2"),
            ("O4", "MEASURES", "O1"), ("O5", "MEASURES", "O2"),
        ),
        unresolved=(("O2", "O1"), ("O4", "O1")),
        invariants=("O6",),
        counterevidence=("S2", "S3"),
    ),
    _case(
        "SW-JURISDICTION",
        "regulation",
        "Identify the next question required to determine incident-reporting scope.",
        (
            ("O1", "reportable incident"), ("O2", "branch status"),
            ("O3", "policy manual"), ("O4", "signed addendum"),
            ("O5", "temporary branch"), ("O6", "reporting window"),
        ),
        (
            ("S1", "The policy manual excludes temporary branches from incident reporting."),
            ("S2", "A later signed addendum includes temporary branches."),
            ("S3", "The incident occurred at a temporary branch."),
            ("S4", "The reporting window is identical in the manual and addendum."),
            ("S5", "The branch-status registry labels the site as temporary."),
            ("S6", "No document in the packet states which text controls when they conflict."),
        ),
        primary=("O1", "O5"),
        constraints=("O3", "O4"),
        relations=(
            ("O3", "GOVERNS", "O1"), ("O4", "GOVERNS", "O1"),
            ("O3", "CONTRADICTS", "O4"), ("O2", "MEASURES", "O5"),
        ),
        unresolved=(("O3", "O4"), ("O5", "O1")),
        invariants=("O6",),
        counterevidence=("S1", "S2", "S6"),
    ),
    _case(
        "SW-BATTERY",
        "energy_storage",
        "Identify the next question that distinguishes physical fade from measurement drift.",
        (
            ("O1", "capacity fade"), ("O2", "charge rate"),
            ("O3", "ambient temperature"), ("O4", "cell batch"),
            ("O5", "rest period"), ("O6", "capacity estimator version"),
        ),
        (
            ("S1", "Estimated capacity fade accelerated after charge rate increased."),
            ("S2", "Ambient temperature also rose during those cycles."),
            ("S3", "The tested cells came from a new cell batch."),
            ("S4", "The rest period remained fixed."),
            ("S5", "A new capacity estimator version was deployed before the acceleration appeared."),
            ("S6", "Raw discharge energy did not show the full drop reported by the estimator."),
        ),
        primary=("O1",),
        constraints=("O3", "O4", "O6"),
        relations=(
            ("O2", "PRECEDES", "O1"), ("O3", "AFFECTS", "O1"),
            ("O4", "CONSTRAINS", "O1"), ("O6", "MEASURES", "O1"),
        ),
        unresolved=(("O2", "O1"), ("O6", "O1")),
        invariants=("O5",),
        counterevidence=("S6",),
    ),
    _case(
        "SW-REPLICATION",
        "distributed_systems",
        "Identify the next question that can explain the stale-read increase.",
        (
            ("O1", "stale-read rate"), ("O2", "replication lag"),
            ("O3", "quorum setting"), ("O4", "retry policy"),
            ("O5", "regional outage"), ("O6", "log sampling"),
        ),
        (
            ("S1", "Stale-read rate increased during a regional outage."),
            ("S2", "Replication lag rose in the surviving regions."),
            ("S3", "The quorum setting was unchanged."),
            ("S4", "A retry-policy update was deployed the previous day."),
            ("S5", "Log sampling omits requests that terminate before the first retry."),
            ("S6", "The stale-read increase persists after excluding the outage interval."),
        ),
        primary=("O1",),
        constraints=("O4", "O5", "O6"),
        relations=(
            ("O5", "AFFECTS", "O2"), ("O2", "AFFECTS", "O1"),
            ("O4", "AFFECTS", "O1"), ("O6", "CONSTRAINS", "O1"),
        ),
        unresolved=(("O2", "O1"), ("O4", "O1")),
        invariants=("O3",),
        counterevidence=("S6",),
    ),
    _case(
        "SW-PLACEMENT",
        "labor_policy",
        "Identify the next question needed to estimate the training program's placement effect.",
        (
            ("O1", "job placement"), ("O2", "training program"),
            ("O3", "local labor demand"), ("O4", "eligibility threshold"),
            ("O5", "follow-up attrition"), ("O6", "wage subsidy"),
        ),
        (
            ("S1", "Participants in the training program have higher job placement."),
            ("S2", "Program entry requires a score just above an eligibility threshold."),
            ("S3", "Local labor demand rose more in participating districts."),
            ("S4", "Follow-up attrition is higher in the comparison group."),
            ("S5", "A wage subsidy is available only in some participating districts."),
            ("S6", "Near the eligibility threshold, the placement difference is smaller."),
        ),
        primary=("O1", "O2"),
        constraints=("O3", "O4", "O5", "O6"),
        relations=(
            ("O2", "AFFECTS", "O1"), ("O4", "GOVERNS", "O2"),
            ("O3", "AFFECTS", "O1"), ("O5", "CONSTRAINS", "O1"),
        ),
        unresolved=(("O2", "O1"), ("O3", "O1"), ("O6", "O1")),
        invariants=(),
        counterevidence=("S6",),
    ),
    _case(
        "SW-TRANSIT",
        "astronomy",
        "Identify the next question that can determine whether the transit-depth change is astrophysical.",
        (
            ("O1", "transit depth"), ("O2", "starspot coverage"),
            ("O3", "instrument calibration"), ("O4", "comparison star"),
            ("O5", "observing cadence"), ("O6", "weather exclusion"),
        ),
        (
            ("S1", "Measured transit depth increased in the latest observing run."),
            ("S2", "Starspot coverage was higher in that run."),
            ("S3", "Instrument calibration changed between runs."),
            ("S4", "The comparison star shows a smaller shift in the same direction."),
            ("S5", "Observing cadence was unchanged."),
            ("S6", "Frames failing the weather-exclusion rule were removed in both runs."),
        ),
        primary=("O1",),
        constraints=("O2", "O3", "O4"),
        relations=(
            ("O2", "AFFECTS", "O1"), ("O3", "MEASURES", "O1"),
            ("O4", "MEASURES", "O3"), ("O6", "CONSTRAINS", "O1"),
        ),
        unresolved=(("O2", "O1"), ("O3", "O1")),
        invariants=("O5", "O6"),
        counterevidence=("S4",),
    ),
)


def build_structural_world_holdout():
    public_items = []
    bindings = {}
    for spec in CASE_SPECS:
        item = {
            "case_id": spec["case_id"],
            "domain": spec["domain"],
            "research_goal": spec["research_goal"],
            "object_registry": [
                {"object_id": object_id, "label": label}
                for object_id, label in spec["objects"]
            ],
            "evidence_spans": [
                {
                    "span_id": span_id,
                    "text": text,
                    "text_hash": hash_payload(text),
                }
                for span_id, text in spec["spans"]
            ],
        }
        public_items.append(item)
        bindings[spec["case_id"]] = {
            "public_item_hash": hash_payload(item),
            "primary_object_ids": list(spec["primary"]),
            "hidden_constraint_object_ids": list(spec["constraints"]),
            "critical_relations": [
                {"source_object_id": source, "relation_type": relation,
                 "target_object_id": target}
                for source, relation, target in spec["relations"]
            ],
            "unresolved_targets": [
                {"source_object_id": source, "target_object_id": target}
                for source, target in spec["unresolved"]
            ],
            "invariant_object_ids": list(spec["invariants"]),
            "counterevidence_span_ids": list(spec["counterevidence"]),
        }
    public_items.sort(
        key=lambda item: hash_payload([CORPUS_VERSION, item["case_id"]])
    )
    surface_commitment = {
        "surface_version": CORPUS_VERSION,
        "items": public_items,
        "private_labels_exposed": False,
    }
    surface = {
        **surface_commitment,
        "surface_hash": hash_payload(surface_commitment),
    }
    commitment = {
        "artifact_version": CORPUS_VERSION,
        "corpus_id": CORPUS_ID,
        "case_count": len(CASE_SPECS),
        "domain_count": len({spec["domain"] for spec in CASE_SPECS}),
        "public_surface": surface,
        "private_provenance": {
            "bindings": bindings,
            "truth_coordinate": "SYNTHETIC_CONSTRUCTION_METADATA",
            "available_to_provider": False,
            "external_semantic_labels_present": False,
        },
        "reference_state": "FRESH_SYNTHETIC_HOLDOUT_FROZEN_BEFORE_RUN",
        "prior_v0_25_labels_reused": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "evidence_refs": list(EVIDENCE_REFS),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_structural_world_holdout(artifact):
    commitment = {
        key: value for key, value in artifact.items()
        if key != "artifact_hash"
    }
    if (
        artifact.get("artifact_hash") != hash_payload(commitment)
        or artifact != build_structural_world_holdout()
    ):
        raise ValueError("structural_world_holdout_invalid")
    if artifact["case_count"] != 12 or artifact["domain_count"] != 12:
        raise ValueError("structural_world_holdout_coverage_invalid")
