"""Fresh formal holdout with a private intent oracle and fixed action costs."""

from __future__ import annotations

from dataclasses import dataclass

from .provider_telemetry import hash_payload


CORPUS_VERSION = "clarification_regret_holdout_v0_6"
CORPUS_ID = "local-clarification-regret-v0-6"
EVIDENCE_REFS = (f"corpus://{CORPUS_ID}",)
BATCH_SIZE = 2
CLARIFICATION_COST = 0.25
CORRECT_UTILITY = 1.0
WRONG_UTILITY = 0.0
CATEGORIES = ("OPEN", "EXPLICIT", "EQUIVALENT", "FABRICATED")


@dataclass(frozen=True)
class RegretCase:
    item_id: str
    domain: str
    prompt: str
    rival_a: str
    rival_b: str
    difference: str
    question: str
    category: str
    intended_answer: str

    def packet(self):
        return f"A) {self.rival_a}\nB) {self.rival_b}\nDifference: {self.difference}\nClarifier: {self.question}"

    def commitment(self):
        return hash_payload(self.__dict__)


CASES = (
    RegretCase("CR01", "bike-share", "A bike-share system recorded 180000 trips made by 52000 riders in May. Report usage as one number.", "trip count", "distinct rider count", "rental events versus people using the service", "Should usage mean trips or distinct riders?", "OPEN", "ANSWER_A"),
    RegretCase("CR02", "clinic", "A clinic scheduled 9000 appointments for 6200 patients this quarter. Report demand as one number.", "appointment count", "distinct patient count", "service bookings versus people seeking care", "Should demand mean appointments or patients?", "OPEN", "ANSWER_B"),
    RegretCase("CR03", "messaging-app", "A messaging app carried 4 million messages from 130000 active users yesterday. Report activity as one integer.", "message count", "active-user count", "communication events versus participating accounts", "Should activity mean messages or active users?", "OPEN", "ANSWER_A"),
    RegretCase("CR04", "shipping-port", "A port handled 70000 containers weighing 1.6 million tonnes. Give cargo volume as one number.", "container count", "cargo weight in tonnes", "handling units versus physical mass", "Should cargo volume mean containers or tonnes?", "OPEN", "ANSWER_B"),
    RegretCase("CR05", "podcast-network", "A podcast network logged 900000 downloads from 240000 devices. Return audience as one number.", "download count", "distinct device count", "content retrievals versus approximate listeners", "Should audience mean downloads or devices?", "OPEN", "ANSWER_A"),
    RegretCase("CR06", "conference", "A conference accepted 5000 registrations and admitted 4200 attendees. Report participation as one integer.", "registration count", "admitted attendee count", "expressed intent versus physical attendance", "Should participation mean registrations or admitted attendees?", "OPEN", "ANSWER_B"),
    RegretCase("CR07", "power-grid", "A power grid recorded 320 incidents causing 18000 outage-minutes. Give disruption as one number.", "incident count", "total outage-minutes", "event frequency versus duration burden", "Should disruption mean incidents or outage-minutes?", "OPEN", "ANSWER_A"),
    RegretCase("CR08", "job-board", "A job board listed 85000 postings from 12000 employers. Report market activity as one integer.", "posting count", "employer count", "opportunities advertised versus organizations hiring", "Should activity mean postings or employers?", "OPEN", "ANSWER_B"),
    RegretCase("CR09", "retailer", "A retailer processed 80000 purchases made by 31000 unique buyers. Report unique buyers as one integer.", "unique buyer count", "purchase transaction count", "explicitly requested people versus transactions", "Should unique buyers mean buyers or purchases?", "EXPLICIT", "ANSWER_A"),
    RegretCase("CR10", "exporter", "An exporter shipped 9000 units and received 600 returned units. Report gross shipments as one integer.", "net shipped units after returns", "gross shipped units", "net flow versus explicitly requested gross flow", "Should gross shipments subtract returns?", "EXPLICIT", "ANSWER_B"),
    RegretCase("CR11", "factory", "A factory inspected 20000 parts and found 500 defects. Report the defect rate as a percentage.", "defects divided by inspected parts", "absolute defect count", "requested proportion versus event count", "Should defect rate mean percentage or defect count?", "EXPLICIT", "ANSWER_A"),
    RegretCase("CR12", "call-centre", "A call centre scheduled 14000 callbacks and completed 11000 in July. Report all scheduled callbacks as one integer.", "callbacks completed in July", "all scheduled callbacks", "completed work versus explicitly requested schedule", "Should scheduled callbacks mean completed or all scheduled?", "EXPLICIT", "ANSWER_B"),
    RegretCase("CR13", "stadium", "A stadium admitted 42000 spectators. Report the spectator count as one integer.", "number of spectators admitted", "total admitted spectators", "equivalent descriptions of the same count", "Should spectator count mean spectators or the spectator total?", "EQUIVALENT", "BOTH"),
    RegretCase("CR14", "reservoir", "A reservoir contains 18 million cubic metres of water. Give stored water volume in cubic metres.", "stored water in cubic metres", "cubic metres of stored water", "equivalent descriptions of one volume", "Should stored volume mean water stored or stored water?", "EQUIVALENT", "BOTH"),
    RegretCase("CR15", "university", "A university enrolled 26000 students this year. Return total enrolment as one integer.", "total enrolled students", "the student enrolment total", "equivalent labels for one population", "Should enrolment mean enrolled students or the enrolment total?", "EQUIVALENT", "BOTH"),
    RegretCase("CR16", "data-centre", "A data centre operates 2400 servers. Report its server count as one integer.", "number of operating servers", "operating-server total", "equivalent descriptions of the same inventory", "Should server count mean servers or the server total?", "EQUIVALENT", "BOTH"),
    RegretCase("CR17", "donation-platform", "A donation platform received 3 million dollars this month. Report recorded donations in dollars.", "recorded donation total", "donations after an assumed fraud adjustment", "observed receipts versus an undocumented adjustment", "Should recorded donations apply the assumed fraud adjustment?", "FABRICATED", "ANSWER_A"),
    RegretCase("CR18", "orchard", "An orchard harvested 1400 tonnes from 200 hectares. Report yield after the documented division by hectares.", "yield after an assumed spoilage deduction", "recorded tonnes divided by hectares", "undocumented exclusion versus the stated calculation", "Should yield deduct assumed spoilage?", "FABRICATED", "ANSWER_B"),
    RegretCase("CR19", "warehouse", "A warehouse counted 7600 units at month end. Give the recorded inventory count.", "recorded unit count", "inventory after an assumed obsolescence write-off", "observed count versus an undocumented write-off", "Should inventory apply the assumed write-off?", "FABRICATED", "ANSWER_A"),
    RegretCase("CR20", "weather-service", "A weather service measured 640 millimetres of rain this year. Report the measured rainfall.", "rainfall after an assumed gauge correction", "recorded rainfall measurement", "undocumented correction versus the observed value", "Should rainfall apply the assumed gauge correction?", "FABRICATED", "ANSWER_B"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])
SPEC_COMMITMENT = {
    "corpus_version": CORPUS_VERSION,
    "corpus_id": CORPUS_ID,
    "ontology_object": "counterfactual utility of clarification before object commitment",
    "observable_proxy": "action utility under a private intent oracle",
    "metric": "mean utility, decision regret, wrong answers, unnecessary questions, missed clarification, and provider cost",
    "case_count": len(CASES),
    "batch_size": BATCH_SIZE,
    "case_commitment": CASE_COMMITMENT,
    "category_counts": {category: sum(case.category == category for case in CASES) for category in CATEGORIES},
    "utility_contract": {"correct": CORRECT_UTILITY, "wrong": WRONG_UTILITY, "clarification_cost": CLARIFICATION_COST},
    "evidence_coordinate": "SYNTHETIC_FORMAL_AUDIT",
    "real_world_ground_truth_claim": False,
    "selection_authority": False,
    "retention_authority": False,
    "production_authority": False,
}
CORPUS_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def build_clarification_regret_artifact():
    validate_clarification_regret_spec()
    source_hash = hash_payload({"spec_hash": CORPUS_SPEC["spec_hash"], "case_commitment": CASE_COMMITMENT})
    bindings, public_cases = {}, []
    for case in CASES:
        blind_id = "clarify-" + hash_payload([CORPUS_VERSION, source_hash, case.item_id])[:18]
        public_cases.append({
            "blind_case_id": blind_id,
            "public_prompt": case.prompt,
            "contrastive_packet": case.packet(),
        })
        valid = ["ANSWER_A", "ANSWER_B"] if case.intended_answer == "BOTH" else [case.intended_answer]
        bindings[blind_id] = {
            "item_id": case.item_id,
            "domain": case.domain,
            "category": case.category,
            "intended_answer": case.intended_answer,
            "valid_direct_actions": valid,
            "operational_oracle_action": "ASK" if case.category == "OPEN" else valid[0],
            "case_commitment": case.commitment(),
        }
    batches = [
        {"batch_id": f"clarification-regret-batch-{offset // BATCH_SIZE + 1:02d}", "public_cases": public_cases[offset:offset + BATCH_SIZE]}
        for offset in range(0, len(public_cases), BATCH_SIZE)
    ]
    surface_commitment = {
        "surface_version": "clarification_regret_surface_v0_6",
        "source_artifact_hash": source_hash,
        "batches": batches,
        "oracle_exposed": False,
        "category_exposed": False,
    }
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    oracle_commitment = {
        "oracle_version": "clarification_regret_oracle_v0_6",
        "surface_hash": surface["surface_hash"],
        "bindings": bindings,
        "revealed_to_provider": False,
        "formal_not_real_world_ground_truth": True,
    }
    oracle = {**oracle_commitment, "oracle_hash": hash_payload(oracle_commitment)}
    commitment = {
        "artifact_version": "clarification_regret_source_v0_6",
        "corpus_spec": CORPUS_SPEC,
        "public_surface": surface,
        "private_oracle": oracle,
        "evidence_refs": list(EVIDENCE_REFS),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_clarification_regret_artifact(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_clarification_regret_artifact():
        raise ValueError("clarification_regret_artifact_invalid")


def validate_clarification_regret_spec(*, cases=CASES, spec=CORPUS_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    if (
        spec.get("spec_hash") != hash_payload(commitment)
        or tuple(cases) != CASES
        or len(cases) != 20
        or len({case.item_id for case in cases}) != 20
        or sum(case.category == "OPEN" for case in cases) != 8
        or any(sum(case.category == category for case in cases) != 4 for category in CATEGORIES[1:])
        or sum(case.category == "OPEN" and case.intended_answer == "ANSWER_A" for case in cases) != 4
        or sum(case.category == "OPEN" and case.intended_answer == "ANSWER_B" for case in cases) != 4
        or any(case.category not in CATEGORIES or case.intended_answer not in {"ANSWER_A", "ANSWER_B", "BOTH"} for case in cases)
    ):
        raise ValueError("clarification_regret_spec_invalid")
