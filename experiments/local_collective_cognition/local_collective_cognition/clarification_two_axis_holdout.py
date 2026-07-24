"""Fresh paired and shuffled holdout for two-axis clarification receipts."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


CORPUS_VERSION = "clarification_two_axis_holdout_v0_9"
CORPUS_ID = "local-clarification-two-axis-v0-9"
EVIDENCE_REFS = (f"corpus://{CORPUS_ID}",)
LAYOUTS = ("PAIRED", "SHUFFLED")


@dataclass(frozen=True)
class TwoAxisPair:
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
    TwoAxisPair("TA01", "podcast-network", "A podcast network logged 2.6 million downloads from 310000 listeners.", "Report network reach as one number.", "Report the distinct listener count as one number.", "download count", "distinct listener count", "ANSWER_B", False),
    TwoAxisPair("TA02", "theater-chain", "A theater chain sold 420000 tickets to 180000 patrons.", "Report theater demand as one integer.", "Report the ticket count as one integer.", "ticket count", "distinct patron count", "ANSWER_A", True),
    TwoAxisPair("TA03", "research-lab", "A research lab processed 68000 samples for 2400 studies.", "Report laboratory workload as one number.", "Report the distinct study count as one number.", "sample count", "distinct study count", "ANSWER_B", False),
    TwoAxisPair("TA04", "weather-api", "A weather API handled 9.1 million requests from 47000 developer accounts.", "Report API activity as one number.", "Report the request count as one number.", "request count", "distinct developer-account count", "ANSWER_A", True),
    TwoAxisPair("TA05", "laundry-service", "A laundry service completed 86000 loads for 26000 customers.", "Report service volume as one integer.", "Report the distinct customer count as one integer.", "laundry-load count", "distinct customer count", "ANSWER_B", False),
    TwoAxisPair("TA06", "toll-network", "A toll network recorded 4.8 million crossings by 920000 vehicles.", "Report network traffic as one number.", "Report the crossing count as one number.", "crossing count", "distinct vehicle count", "ANSWER_A", True),
    TwoAxisPair("TA07", "pharmacy", "A pharmacy dispensed 350000 prescriptions for 125000 patients.", "Report pharmacy activity as one integer.", "Report the distinct patient count as one integer.", "prescription count", "distinct patient count", "ANSWER_B", False),
    TwoAxisPair("TA08", "conference", "A conference recorded 29000 session attendances from 6400 delegates.", "Report conference participation as one number.", "Report the session-attendance count as one number.", "session-attendance count", "distinct delegate count", "ANSWER_A", True),
    TwoAxisPair("TA09", "recruiting-platform", "A recruiting platform received 510000 applications from 210000 candidates.", "Report platform scale as one number.", "Report the distinct candidate count as one number.", "application count", "distinct candidate count", "ANSWER_B", False),
    TwoAxisPair("TA10", "factory-inspection", "A factory recorded 730000 inspections across 190000 units.", "Report inspection activity as one integer.", "Report the inspection count as one integer.", "inspection count", "distinct unit count", "ANSWER_A", True),
    TwoAxisPair("TA11", "email-service", "An email service delivered 18 million messages for 760000 accounts.", "Report service usage as one number.", "Report the distinct account count as one number.", "delivered-message count", "distinct account count", "ANSWER_B", False),
    TwoAxisPair("TA12", "warehouse", "A warehouse processed 270000 shipments for 8400 client businesses.", "Report warehouse throughput as one integer.", "Report the shipment count as one integer.", "shipment count", "distinct client-business count", "ANSWER_A", True),
)


PAIR_COMMITMENT = hash_payload([pair.commitment() for pair in PAIRS])
SPEC_COMMITMENT = {
    "corpus_version": CORPUS_VERSION,
    "corpus_id": CORPUS_ID,
    "ontology_object": "orthogonality of task-object selection and assessor resolution status",
    "observable_proxy": "fresh two-axis accuracy with and without matched-pair visibility",
    "pair_count": 12,
    "case_count": 24,
    "pair_commitment": PAIR_COMMITMENT,
    "category_counts": {"OPEN_RIVALS": 12, "PROMPT_FIXED": 12},
    "fixed_answer_counts": {"ANSWER_A": 6, "ANSWER_B": 6},
    "fixed_position_counts": {"FIRST": 6, "SECOND": 6},
    "layouts": list(LAYOUTS),
    "evidence_coordinate": "SYNTHETIC_FORMAL_AUDIT",
    "real_world_ground_truth_claim": False,
    "selection_authority": False,
    "retention_authority": False,
    "production_authority": False,
}
CORPUS_SPEC = {**SPEC_COMMITMENT, "spec_hash": hash_payload(SPEC_COMMITMENT)}


def build_two_axis_holdout_artifact():
    validate_two_axis_holdout_spec()
    source_hash = hash_payload({"spec_hash": CORPUS_SPEC["spec_hash"], "pair_commitment": PAIR_COMMITMENT})
    bindings = {}
    cases_by_pair = []
    for pair in PAIRS:
        pair_token = "pair-" + hash_payload([CORPUS_VERSION, source_hash, pair.pair_id])[:16]
        open_case = _case(pair, source_hash, pair_token, "OPEN_RIVALS", "NONE", pair.open_request)
        fixed_case = _case(pair, source_hash, pair_token, "PROMPT_FIXED", pair.fixed_answer, pair.fixed_request)
        for private, public in (open_case, fixed_case):
            bindings[public["blind_case_id"]] = private
        cases_by_pair.append((open_case[1], fixed_case[1], pair.fixed_first))

    paired_batches = []
    for open_case, fixed_case, fixed_first in cases_by_pair:
        ordered = [fixed_case, open_case] if fixed_first else [open_case, fixed_case]
        paired_batches.append({"batch_id": f"paired-{open_case['pair_token']}", "public_cases": ordered})

    shuffled_batches = []
    for index, (open_case, _, _) in enumerate(cases_by_pair):
        fixed_case = cases_by_pair[(index + 1) % len(cases_by_pair)][1]
        ordered = [fixed_case, open_case] if index % 2 else [open_case, fixed_case]
        shuffled_batches.append({"batch_id": f"shuffled-{index + 1:02d}", "public_cases": ordered})

    surfaces = {
        "PAIRED": _surface("PAIRED", source_hash, paired_batches, matched_counterpart_visible=True),
        "SHUFFLED": _surface("SHUFFLED", source_hash, shuffled_batches, matched_counterpart_visible=False),
    }
    oracle_commitment = {
        "oracle_version": "clarification_two_axis_oracle_v0_9",
        "surface_hashes": {layout: surface["surface_hash"] for layout, surface in surfaces.items()},
        "bindings": bindings,
        "revealed_to_provider": False,
        "formal_not_real_world_ground_truth": True,
    }
    oracle = {**oracle_commitment, "oracle_hash": hash_payload(oracle_commitment)}
    commitment = {
        "artifact_version": "clarification_two_axis_source_v0_9",
        "corpus_spec": CORPUS_SPEC,
        "public_surfaces": surfaces,
        "private_oracle": oracle,
        "evidence_refs": list(EVIDENCE_REFS),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _case(pair, source_hash, pair_token, category, selection, request):
    blind_id = "axis-" + hash_payload([CORPUS_VERSION, source_hash, pair.pair_id, category])[:18]
    public = {
        "blind_case_id": blind_id,
        "pair_token": pair_token,
        "public_prompt": f"{pair.fact} {request}",
        "candidate_a": pair.candidate_a,
        "candidate_b": pair.candidate_b,
    }
    private = {
        "pair_id": pair.pair_id,
        "pair_token": pair_token,
        "domain": pair.domain,
        "category": category,
        "object_selection": selection,
        "case_commitment": hash_payload(public),
    }
    return private, public


def _surface(layout, source_hash, batches, *, matched_counterpart_visible):
    commitment = {
        "surface_version": f"clarification_two_axis_{layout.lower()}_surface_v0_9",
        "layout": layout,
        "source_artifact_hash": source_hash,
        "batches": batches,
        "matched_counterpart_visible": matched_counterpart_visible,
        "oracle_exposed": False,
        "category_exposed": False,
    }
    return {**commitment, "surface_hash": hash_payload(commitment)}


def validate_two_axis_holdout_artifact(artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_two_axis_holdout_artifact():
        raise ValueError("clarification_two_axis_artifact_invalid")


def validate_two_axis_holdout_spec(*, pairs=PAIRS, spec=CORPUS_SPEC):
    commitment = {key: value for key, value in spec.items() if key != "spec_hash"}
    if spec.get("spec_hash") != hash_payload(commitment) or tuple(pairs) != PAIRS or len(pairs) != 12:
        raise ValueError("clarification_two_axis_spec_invalid")
    if sum(pair.fixed_answer == "ANSWER_A" for pair in pairs) != 6 or sum(pair.fixed_first for pair in pairs) != 6:
        raise ValueError("clarification_two_axis_balance_invalid")
