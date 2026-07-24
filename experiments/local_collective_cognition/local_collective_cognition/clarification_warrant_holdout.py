"""Fresh explicit-versus-pragmatic holdout for selection warrants v0.10."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


CORPUS_VERSION = "clarification_warrant_holdout_v0_10"
CORPUS_ID = "local-clarification-warrant-v0-10"
EVIDENCE_REFS = (f"corpus://{CORPUS_ID}",)
BATCH_SIZE = 2


@dataclass(frozen=True)
class WarrantCase:
    case_id: str
    domain: str
    fact: str
    request: str
    candidate_a: str
    candidate_b: str
    construction: str
    explicit_selection: str
    pragmatic_preference: str

    def commitment(self):
        return asdict(self)


CASES = (
    WarrantCase("WE01", "email-service", "An email service delivered 14 million messages for 620000 accounts.", "Report the distinct account count as one number.", "delivered-message count", "distinct account count", "EXPLICIT", "CANDIDATE_B", "CANDIDATE_B"),
    WarrantCase("WE02", "ticketing", "A ticketing service recorded 380000 bookings from 170000 customers.", "Report the booking count as one integer.", "booking count", "distinct customer count", "EXPLICIT", "CANDIDATE_A", "CANDIDATE_A"),
    WarrantCase("WE03", "university", "A university received 92000 applications from 68000 applicants.", "Report the distinct applicant count as one number.", "application count", "distinct applicant count", "EXPLICIT", "CANDIDATE_B", "CANDIDATE_B"),
    WarrantCase("WE04", "mapping-api", "A mapping API handled 7.5 million requests from 41000 developer accounts.", "Report the API request count as one number.", "API request count", "distinct developer-account count", "EXPLICIT", "CANDIDATE_A", "CANDIDATE_A"),
    WarrantCase("WE05", "charity", "A charity received 240000 donations from 81000 donors.", "Report the distinct donor count as one integer.", "donation count", "distinct donor count", "EXPLICIT", "CANDIDATE_B", "CANDIDATE_B"),
    WarrantCase("WE06", "quality-control", "A quality-control team completed 560000 inspections across 145000 units.", "Report the inspection-event count as one number.", "inspection-event count", "distinct inspected-unit count", "EXPLICIT", "CANDIDATE_A", "CANDIDATE_A"),
    WarrantCase("WE07", "iot-platform", "An IoT platform processed 11 million signals from 390000 devices.", "Report the distinct device count as one number.", "signal count", "distinct device count", "EXPLICIT", "CANDIDATE_B", "CANDIDATE_B"),
    WarrantCase("WE08", "parcel-hub", "A parcel hub recorded 1.8 million scans for 460000 parcels.", "Report the scan count as one integer.", "scan count", "distinct parcel count", "EXPLICIT", "CANDIDATE_A", "CANDIDATE_A"),
    WarrantCase("WE09", "clinic", "A clinic completed 87000 consultations for 33000 patients.", "Report the distinct patient count as one number.", "consultation count", "distinct patient count", "EXPLICIT", "CANDIDATE_B", "CANDIDATE_B"),
    WarrantCase("WE10", "transit-app", "A transit app logged 5.4 million trips by 740000 riders.", "Report the trip count as one number.", "trip count", "distinct rider count", "EXPLICIT", "CANDIDATE_A", "CANDIDATE_A"),
    WarrantCase("WE11", "audio-platform", "An audio platform logged 3.1 million plays from 280000 listeners.", "Report the distinct listener count as one integer.", "play count", "distinct listener count", "EXPLICIT", "CANDIDATE_B", "CANDIDATE_B"),
    WarrantCase("WE12", "online-retail", "An online retailer processed 640000 orders from 220000 households.", "Report the order count as one number.", "order count", "distinct household count", "EXPLICIT", "CANDIDATE_A", "CANDIDATE_A"),
    WarrantCase("WP01", "biobank", "A biobank processed 71000 samples for 2900 research projects.", "Report biobank workload as one number.", "sample count", "distinct project count", "PRAGMATIC_OPEN", "NONE", "CANDIDATE_A"),
    WarrantCase("WP02", "payment-gateway", "A payment gateway processed 8.8 million transactions for 510000 accounts.", "Report transaction volume as one number.", "transaction count", "distinct account count", "PRAGMATIC_OPEN", "NONE", "CANDIDATE_A"),
    WarrantCase("WP03", "factory", "A factory produced 960000 units across 72 active lines.", "Report factory throughput as one integer.", "unit count", "active production-line count", "PRAGMATIC_OPEN", "NONE", "CANDIDATE_A"),
    WarrantCase("WP04", "support-desk", "A support desk handled 430000 tickets from 118000 customers.", "Report support workload as one number.", "ticket count", "distinct customer count", "PRAGMATIC_OPEN", "NONE", "CANDIDATE_A"),
    WarrantCase("WP05", "data-network", "A data network carried 21 million packets from 830000 devices.", "Report network traffic as one number.", "packet count", "distinct device count", "PRAGMATIC_OPEN", "NONE", "CANDIDATE_A"),
    WarrantCase("WP06", "warehouse", "A warehouse processed 310000 shipments for 9700 client businesses.", "Report warehouse volume as one integer.", "shipment count", "distinct client-business count", "PRAGMATIC_OPEN", "NONE", "CANDIDATE_A"),
    WarrantCase("WP07", "media-campaign", "A media campaign generated 6.7 million impressions among 920000 viewers.", "Report campaign reach as one number.", "impression count", "distinct viewer count", "PRAGMATIC_OPEN", "NONE", "CANDIDATE_B"),
    WarrantCase("WP08", "fitness-club", "A fitness club logged 180000 visits by 26000 members.", "Report the club's membership base as one integer.", "visit count", "distinct member count", "PRAGMATIC_OPEN", "NONE", "CANDIDATE_B"),
    WarrantCase("WP09", "training-program", "A training program recorded 54000 attendances from 12000 participants.", "Report program participation as one number.", "attendance count", "distinct participant count", "PRAGMATIC_OPEN", "NONE", "CANDIDATE_B"),
    WarrantCase("WP10", "inspection-service", "An inspection service completed 89000 inspections across 14000 sites.", "Report service coverage as one integer.", "inspection count", "distinct site count", "PRAGMATIC_OPEN", "NONE", "CANDIDATE_B"),
    WarrantCase("WP11", "seller-marketplace", "A marketplace processed 770000 orders from 46000 active sellers.", "Report the marketplace footprint as one number.", "order count", "distinct active-seller count", "PRAGMATIC_OPEN", "NONE", "CANDIDATE_B"),
    WarrantCase("WP12", "mobile-product", "A mobile product recorded 2.2 million installations across 980000 active devices.", "Report product adoption as one number.", "installation count", "distinct active-device count", "PRAGMATIC_OPEN", "NONE", "CANDIDATE_B"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])
SPEC_COMMITMENT = {
    "corpus_version": CORPUS_VERSION,
    "corpus_id": CORPUS_ID,
    "ontology_object": "separation of explicit selection from pragmatic preference",
    "observable_proxy": "fresh hard-generic versus explicit warrant classification",
    "case_count": 24,
    "batch_size": BATCH_SIZE,
    "case_commitment": CASE_COMMITMENT,
    "construction_counts": {"EXPLICIT": 12, "PRAGMATIC_OPEN": 12},
    "explicit_direction_counts": {"CANDIDATE_A": 6, "CANDIDATE_B": 6},
    "pragmatic_direction_counts": {"CANDIDATE_A": 6, "CANDIDATE_B": 6},
    "matched_counterpart_visible": False,
    "evidence_coordinate": "SYNTHETIC_FORMAL_AUDIT",
    "pragmatic_preference_is_constructed_proxy": True,
    "real_world_ground_truth_claim": False,
    "selection_authority": False,
    "retention_authority": False,
    "production_authority": False,
}
CORPUS_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def build_warrant_holdout_artifact():
    validate_warrant_holdout_spec()
    source_hash = hash_payload({"spec_hash": CORPUS_SPEC["spec_hash"], "case_commitment": CASE_COMMITMENT})
    explicit = [case for case in CASES if case.construction == "EXPLICIT"]
    pragmatic = [case for case in CASES if case.construction == "PRAGMATIC_OPEN"]
    bindings, batches = {}, []
    for index, (fixed_case, open_case) in enumerate(zip(explicit, pragmatic)):
        public_cases = []
        ordered = (fixed_case, open_case) if index % 2 else (open_case, fixed_case)
        for case in ordered:
            blind_id = "warrant-" + hash_payload([CORPUS_VERSION, source_hash, case.case_id])[:18]
            public = {
                "blind_case_id": blind_id,
                "public_prompt": f"{case.fact} {case.request}",
                "candidate_a": case.candidate_a,
                "candidate_b": case.candidate_b,
            }
            bindings[blind_id] = {
                "case_id": case.case_id,
                "domain": case.domain,
                "construction": case.construction,
                "truth_category": "PROMPT_FIXED" if case.construction == "EXPLICIT" else "OPEN_RIVALS",
                "explicit_selection": case.explicit_selection,
                "pragmatic_preference": case.pragmatic_preference,
                "case_commitment": hash_payload(public),
            }
            public_cases.append(public)
        batches.append({"batch_id": f"warrant-batch-{index + 1:02d}", "public_cases": public_cases})
    surface_commitment = {
        "surface_version": "clarification_warrant_surface_v0_10",
        "source_artifact_hash": source_hash,
        "batches": batches,
        "matched_counterpart_visible": False,
        "oracle_exposed": False,
        "construction_exposed": False,
    }
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    oracle_commitment = {
        "oracle_version": "clarification_warrant_oracle_v0_10",
        "surface_hash": surface["surface_hash"],
        "bindings": bindings,
        "revealed_to_provider": False,
        "formal_explicitness_not_real_world_ground_truth": True,
    }
    oracle = {**oracle_commitment, "oracle_hash": hash_payload(oracle_commitment)}
    commitment = {
        "artifact_version": "clarification_warrant_source_v0_10",
        "corpus_spec": CORPUS_SPEC,
        "public_surface": surface,
        "private_oracle": oracle,
        "evidence_refs": list(EVIDENCE_REFS),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_warrant_holdout_artifact(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_warrant_holdout_artifact():
        raise ValueError("clarification_warrant_artifact_invalid")


def validate_warrant_holdout_spec(*, cases=CASES, spec=CORPUS_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    if spec.get("spec_hash") != hash_payload(commitment) or tuple(cases) != CASES or len(cases) != 24:
        raise ValueError("clarification_warrant_spec_invalid")
    if sum(case.construction == "EXPLICIT" for case in cases) != 12 or sum(case.construction == "PRAGMATIC_OPEN" for case in cases) != 12:
        raise ValueError("clarification_warrant_construction_balance_invalid")
