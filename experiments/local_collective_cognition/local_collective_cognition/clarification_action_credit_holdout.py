"""Fresh v0.7 validation corpus for transferred clarification action credit."""

from __future__ import annotations

from .clarification_regret_holdout import BATCH_SIZE, CLARIFICATION_COST, CORRECT_UTILITY, WRONG_UTILITY, RegretCase
from .provider_telemetry import hash_payload


CORPUS_VERSION = "clarification_action_credit_holdout_v0_7"
CORPUS_ID = "local-clarification-action-credit-v0-7"
EVIDENCE_REFS = (f"corpus://{CORPUS_ID}",)
CATEGORIES = ("OPEN", "EXPLICIT", "EQUIVALENT", "FABRICATED")


CASES = (
    RegretCase("CV01", "car-rental", "A car-rental service logged 36000 rentals made by 19000 customers in August. Report demand as one number.", "rental transaction count", "distinct customer count", "rental events versus people renting", "Should demand mean rentals or customers?", "OPEN", "ANSWER_A"),
    RegretCase("CV02", "news-site", "A news site recorded 2.8 million article views from 470000 readers. Give reach as one number.", "article-view count", "distinct reader count", "content exposures versus people reached", "Should reach mean views or readers?", "OPEN", "ANSWER_B"),
    RegretCase("CV03", "fitness-chain", "A fitness chain recorded 210000 visits by 44000 members this quarter. Return participation as one integer.", "visit count", "distinct member count", "attendance events versus participating members", "Should participation mean visits or members?", "OPEN", "ANSWER_A"),
    RegretCase("CV04", "courier", "A courier completed 480000 deliveries for 160000 customers. Report service volume as one number.", "delivery count", "customer count", "service events versus recipients served", "Should service volume mean deliveries or customers?", "OPEN", "ANSWER_B"),
    RegretCase("CV05", "webinar-platform", "A webinar platform logged 95000 viewing sessions from 38000 participants. Give engagement as one integer.", "viewing-session count", "participant count", "viewing events versus people engaged", "Should engagement mean sessions or participants?", "OPEN", "ANSWER_A"),
    RegretCase("CV06", "mobile-network", "A mobile network carried 7 million calls for 1.2 million subscribers yesterday. Report activity as one number.", "call count", "subscriber count", "communication events versus accounts involved", "Should activity mean calls or subscribers?", "OPEN", "ANSWER_B"),
    RegretCase("CV07", "food-marketplace", "A food marketplace processed 330000 orders from 18000 restaurants. Return marketplace volume as one integer.", "order count", "restaurant count", "transactions versus participating vendors", "Should volume mean orders or restaurants?", "OPEN", "ANSWER_A"),
    RegretCase("CV08", "bank", "A bank processed 9 million transfers for 640000 customers. Report transaction activity as one number.", "transfer count", "customer count", "financial events versus customers transacting", "Should activity mean transfers or customers?", "OPEN", "ANSWER_B"),
    RegretCase("CV09", "subscription-service", "A service has 74000 accounts, of which 51000 paid in June. Report June paying accounts as one integer.", "accounts that paid in June", "all registered accounts", "requested payment status and window versus total registrations", "Should paying accounts include every registered account?", "EXPLICIT", "ANSWER_A"),
    RegretCase("CV10", "rail-operator", "A rail operator scheduled 6200 services and ran 5800. Report all scheduled services as one integer.", "services actually run", "all scheduled services", "operations completed versus explicitly requested schedule", "Should scheduled services mean run services or all scheduled?", "EXPLICIT", "ANSWER_B"),
    RegretCase("CV11", "battery-fleet", "A battery fleet stores 720 megawatt-hours against 900 megawatt-hours of capacity. Report charge level as a percentage.", "stored energy divided by capacity", "stored megawatt-hours", "requested normalized level versus absolute energy", "Should charge level mean percentage or stored energy?", "EXPLICIT", "ANSWER_A"),
    RegretCase("CV12", "insurer", "An insurer received 14000 claims and approved 9200. Report total claims received as one integer.", "approved claim count", "all claims received", "approval outcome versus explicitly requested intake", "Should received claims mean approved or all received?", "EXPLICIT", "ANSWER_B"),
    RegretCase("CV13", "aquarium", "An aquarium admitted 18000 visitors in March. Report March visitor count.", "number of March visitors", "March visitor total", "equivalent descriptions of one count", "Should visitor count mean visitors or the visitor total?", "EQUIVALENT", "BOTH"),
    RegretCase("CV14", "wind-farm", "A wind farm generated 42 gigawatt-hours. Give total generated electricity in gigawatt-hours.", "generated electricity total", "total electricity generated", "equivalent descriptions of one quantity", "Should generation mean generated electricity or total generation?", "EQUIVALENT", "BOTH"),
    RegretCase("CV15", "hotel", "A hotel sold 7600 room nights in April. Return April room-night sales.", "room nights sold in April", "April sold room-night total", "equivalent labels for one sales count", "Should room-night sales mean sold nights or the sales total?", "EQUIVALENT", "BOTH"),
    RegretCase("CV16", "factory", "A factory operates 85 production lines. Report its production-line count.", "number of production lines", "production-line total", "equivalent descriptions of one inventory", "Should line count mean lines or the line total?", "EQUIVALENT", "BOTH"),
    RegretCase("CV17", "ticket-platform", "A ticket platform recorded 1.4 million dollars in sales. Report recorded ticket revenue.", "recorded sales total", "sales after an assumed reseller adjustment", "observed revenue versus an undocumented adjustment", "Should revenue apply the assumed reseller adjustment?", "FABRICATED", "ANSWER_A"),
    RegretCase("CV18", "dairy", "A dairy produced 820 tonnes from 410 cows. Report output per cow using the stated values.", "output after an assumed quality deduction", "recorded tonnes divided by cow count", "undocumented deduction versus stated calculation", "Should output apply the assumed quality deduction?", "FABRICATED", "ANSWER_B"),
    RegretCase("CV19", "telecom-provider", "A telecom provider recorded 96.4 percent network availability. Return the recorded availability.", "recorded availability percentage", "availability after an assumed maintenance exclusion", "observed statistic versus an undocumented exclusion", "Should availability exclude assumed maintenance?", "FABRICATED", "ANSWER_A"),
    RegretCase("CV20", "recycler", "A recycler processed 12000 tonnes this year. Report measured material processed.", "tonnes after an assumed contamination correction", "recorded processed tonnes", "undocumented correction versus measured throughput", "Should processed material apply the assumed correction?", "FABRICATED", "ANSWER_B"),
)


CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])
SPEC_COMMITMENT = {
    "corpus_version": CORPUS_VERSION, "corpus_id": CORPUS_ID,
    "ontology_object": "transfer of outcome-calibrated ASK versus DIRECT action credit",
    "observable_proxy": "fresh validation utility under a frozen calibration ledger",
    "case_count": 20, "batch_size": BATCH_SIZE, "case_commitment": CASE_COMMITMENT,
    "category_counts": {category: sum(case.category == category for case in CASES) for category in CATEGORIES},
    "utility_contract": {"correct": CORRECT_UTILITY, "wrong": WRONG_UTILITY, "clarification_cost": CLARIFICATION_COST},
    "evidence_coordinate": "SYNTHETIC_FORMAL_AUDIT", "real_world_ground_truth_claim": False,
    "selection_authority": False, "retention_authority": False, "production_authority": False,
}
CORPUS_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def build_action_credit_validation_artifact():
    validate_action_credit_validation_spec()
    source_hash = hash_payload({"spec_hash": CORPUS_SPEC["spec_hash"], "case_commitment": CASE_COMMITMENT})
    bindings, public_cases = {}, []
    for case in CASES:
        blind_id = "credit-" + hash_payload([CORPUS_VERSION, source_hash, case.item_id])[:18]
        public_cases.append({"blind_case_id": blind_id, "public_prompt": case.prompt, "contrastive_packet": case.packet()})
        valid = ["ANSWER_A", "ANSWER_B"] if case.intended_answer == "BOTH" else [case.intended_answer]
        bindings[blind_id] = {"item_id": case.item_id, "domain": case.domain, "category": case.category, "intended_answer": case.intended_answer, "valid_direct_actions": valid, "operational_oracle_action": "ASK" if case.category == "OPEN" else valid[0], "case_commitment": case.commitment()}
    batches = [{"batch_id": f"action-credit-batch-{offset // BATCH_SIZE + 1:02d}", "public_cases": public_cases[offset:offset + BATCH_SIZE]} for offset in range(0, 20, BATCH_SIZE)]
    surface_commitment = {"surface_version": "clarification_action_credit_surface_v0_7", "source_artifact_hash": source_hash, "batches": batches, "oracle_exposed": False, "category_exposed": False}
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    oracle_commitment = {"oracle_version": "clarification_action_credit_oracle_v0_7", "surface_hash": surface["surface_hash"], "bindings": bindings, "revealed_to_provider": False, "formal_not_real_world_ground_truth": True}
    oracle = {**oracle_commitment, "oracle_hash": hash_payload(oracle_commitment)}
    commitment = {"artifact_version": "clarification_action_credit_source_v0_7", "corpus_spec": CORPUS_SPEC, "public_surface": surface, "private_oracle": oracle, "evidence_refs": list(EVIDENCE_REFS)}
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_action_credit_validation_artifact(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_action_credit_validation_artifact():
        raise ValueError("clarification_action_credit_artifact_invalid")


def validate_action_credit_validation_spec(*, cases=CASES, spec=CORPUS_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    if spec.get("spec_hash") != hash_payload(commitment) or tuple(cases) != CASES or len(cases) != 20 or len({case.item_id for case in cases}) != 20 or sum(case.category == "OPEN" for case in cases) != 8 or any(sum(case.category == category for case in cases) != 4 for category in CATEGORIES[1:]):
        raise ValueError("clarification_action_credit_spec_invalid")
