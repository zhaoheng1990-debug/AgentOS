"""Fresh matched-pair holdout for clarification representation v0.8."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


CORPUS_VERSION = "clarification_contrastive_holdout_v0_8"
CORPUS_ID = "local-clarification-contrastive-v0-8"
EVIDENCE_REFS = (f"corpus://{CORPUS_ID}",)


@dataclass(frozen=True)
class ContrastivePair:
    pair_id: str
    domain: str
    fact: str
    open_request: str
    fixed_request: str
    candidate_a: str
    candidate_b: str
    fixed_answer: str
    fixed_first: bool

    def commitment(self):
        return asdict(self)


PAIRS = (
    ContrastivePair("RP01", "library", "A library logged 120000 checkouts by 35000 members this year.", "Report library usage as one number.", "Report the distinct member count as one number.", "checkout count", "distinct member count", "ANSWER_B", False),
    ContrastivePair("RP02", "charging-network", "A charging network recorded 48000 charging sessions from 9000 vehicles.", "Report network activity as one number.", "Report the charging-session count as one number.", "charging-session count", "distinct vehicle count", "ANSWER_A", True),
    ContrastivePair("RP03", "clinic", "A clinic completed 76000 appointments for 28000 patients.", "Report clinic volume as one integer.", "Report the distinct patient count as one integer.", "appointment count", "distinct patient count", "ANSWER_B", False),
    ContrastivePair("RP04", "streaming-service", "A streaming service logged 3.2 million plays from 410000 accounts.", "Report service engagement as one number.", "Report the play count as one number.", "play count", "distinct account count", "ANSWER_A", True),
    ContrastivePair("RP05", "bike-share", "A bike-share system recorded 670000 trips by 92000 riders.", "Report system participation as one number.", "Report the distinct rider count as one number.", "trip count", "distinct rider count", "ANSWER_B", False),
    ContrastivePair("RP06", "payment-network", "A payment network processed 8.4 million payments for 630000 merchants.", "Report network throughput as one number.", "Report the payment count as one number.", "payment count", "distinct merchant count", "ANSWER_A", True),
    ContrastivePair("RP07", "museum", "A museum recorded 240000 visits by 110000 visitors.", "Report museum demand as one integer.", "Report the distinct visitor count as one integer.", "visit count", "distinct visitor count", "ANSWER_B", False),
    ContrastivePair("RP08", "support-center", "A support center handled 310000 tickets from 87000 customers.", "Report support workload as one number.", "Report the ticket count as one number.", "ticket count", "distinct customer count", "ANSWER_A", True),
    ContrastivePair("RP09", "online-course", "An online course logged 560000 lesson views from 74000 learners.", "Report course activity as one number.", "Report the distinct learner count as one number.", "lesson-view count", "distinct learner count", "ANSWER_B", False),
    ContrastivePair("RP10", "parcel-locker", "A parcel-locker network processed 190000 pickups by 52000 recipients.", "Report locker utilization as one integer.", "Report the pickup count as one integer.", "pickup count", "distinct recipient count", "ANSWER_A", True),
    ContrastivePair("RP11", "grocery-platform", "A grocery platform fulfilled 440000 orders for 130000 households.", "Report platform scale as one number.", "Report the distinct household count as one number.", "order count", "distinct household count", "ANSWER_B", False),
    ContrastivePair("RP12", "transit-card", "A transit-card system recorded 6.1 million taps from 780000 cards.", "Report transit activity as one number.", "Report the tap count as one number.", "tap count", "distinct card count", "ANSWER_A", True),
)


PAIR_COMMITMENT = hash_payload([pair.commitment() for pair in PAIRS])
SPEC_COMMITMENT = {
    "corpus_version": CORPUS_VERSION,
    "corpus_id": CORPUS_ID,
    "ontology_object": "separability of prompt-fixed and genuinely open requested objects",
    "observable_proxy": "matched-pair structural classification on minimal request edits",
    "pair_count": 12,
    "case_count": 24,
    "pair_commitment": PAIR_COMMITMENT,
    "category_counts": {"OPEN_RIVALS": 12, "PROMPT_FIXED": 12},
    "fixed_answer_counts": {"ANSWER_A": 6, "ANSWER_B": 6},
    "fixed_position_counts": {"FIRST": 6, "SECOND": 6},
    "evidence_coordinate": "SYNTHETIC_FORMAL_AUDIT",
    "real_world_ground_truth_claim": False,
    "selection_authority": False,
    "retention_authority": False,
    "production_authority": False,
}
CORPUS_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def build_contrastive_holdout_artifact():
    validate_contrastive_holdout_spec()
    source_hash = hash_payload({"spec_hash": CORPUS_SPEC["spec_hash"], "pair_commitment": PAIR_COMMITMENT})
    bindings = {}
    batches = []
    for pair in PAIRS:
        pair_token = "pair-" + hash_payload([CORPUS_VERSION, source_hash, pair.pair_id])[:16]
        open_case = _case(pair, source_hash, pair_token, "OPEN_RIVALS", "NEITHER", pair.open_request)
        fixed_case = _case(pair, source_hash, pair_token, "PROMPT_FIXED", pair.fixed_answer, pair.fixed_request)
        ordered = [fixed_case, open_case] if pair.fixed_first else [open_case, fixed_case]
        public_cases = []
        for private, public in ordered:
            bindings[public["blind_case_id"]] = private
            public_cases.append(public)
        batches.append({"batch_id": f"contrastive-{pair_token}", "pair_token": pair_token, "public_cases": public_cases})
    surface_commitment = {
        "surface_version": "clarification_contrastive_surface_v0_8",
        "source_artifact_hash": source_hash,
        "batches": batches,
        "oracle_exposed": False,
        "category_exposed": False,
    }
    surface = {**surface_commitment, "surface_hash": hash_payload(surface_commitment)}
    oracle_commitment = {
        "oracle_version": "clarification_contrastive_oracle_v0_8",
        "surface_hash": surface["surface_hash"],
        "bindings": bindings,
        "revealed_to_provider": False,
        "formal_not_real_world_ground_truth": True,
    }
    oracle = {**oracle_commitment, "oracle_hash": hash_payload(oracle_commitment)}
    commitment = {
        "artifact_version": "clarification_contrastive_source_v0_8",
        "corpus_spec": CORPUS_SPEC,
        "public_surface": surface,
        "private_oracle": oracle,
        "evidence_refs": list(EVIDENCE_REFS),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _case(pair, source_hash, pair_token, category, selected, request):
    blind_id = "repr-" + hash_payload([CORPUS_VERSION, source_hash, pair.pair_id, category])[:18]
    prompt = f"{pair.fact} {request}"
    public = {
        "blind_case_id": blind_id,
        "pair_token": pair_token,
        "public_prompt": prompt,
        "candidate_a": pair.candidate_a,
        "candidate_b": pair.candidate_b,
    }
    private = {
        "pair_id": pair.pair_id,
        "pair_token": pair_token,
        "domain": pair.domain,
        "category": category,
        "selected_candidate": selected,
        "fixed_answer": pair.fixed_answer,
        "case_commitment": hash_payload(public),
    }
    return private, public


def validate_contrastive_holdout_artifact(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_contrastive_holdout_artifact():
        raise ValueError("clarification_contrastive_artifact_invalid")


def validate_contrastive_holdout_spec(*, pairs=PAIRS, spec=CORPUS_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    if spec.get("spec_hash") != hash_payload(commitment) or tuple(pairs) != PAIRS or len(pairs) != 12:
        raise ValueError("clarification_contrastive_spec_invalid")
    if sum(pair.fixed_answer == "ANSWER_A" for pair in pairs) != 6 or sum(pair.fixed_first for pair in pairs) != 6:
        raise ValueError("clarification_contrastive_balance_invalid")
