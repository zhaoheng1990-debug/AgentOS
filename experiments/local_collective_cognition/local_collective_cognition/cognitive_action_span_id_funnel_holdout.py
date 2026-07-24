"""Fresh structural smoke holdout for the immutable span-ID funnel v0.25."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .provider_telemetry import hash_payload


SPAN_ID_CORPUS_VERSION = "cognitive_action_span_id_funnel_holdout_v0_25"
SPAN_ID_CORPUS_ID = "local-cognitive-action-span-id-funnel-v0-25"
SOURCE_STATUSES = ("AVAILABLE", "MISSING", "UNSPECIFIED", "CONFLICTED")


@dataclass(frozen=True)
class SpanIdFunnelCase:
    case_id: str
    object_family: str
    source_status: str
    public_prompt: str
    candidate_a: str
    candidate_b: str

    def commitment(self):
        return asdict(self)


CASES = (
    SpanIdFunnelCase(
        "SI-RL01",
        "RECORD_LINKAGE",
        "AVAILABLE",
        "The linkage guide defines a record key as normalized email combined with tenant identifier. Candidates use normalized email alone or normalized email plus tenant identifier.",
        "normalized email alone",
        "normalized email plus tenant identifier",
    ),
    SpanIdFunnelCase(
        "SI-RL02",
        "RECORD_LINKAGE",
        "UNSPECIFIED",
        "The analysis asks for repeat visitors but supplies no identity-resolution rule. Candidates use browser cookie or verified email.",
        "browser cookie",
        "verified email",
    ),
    SpanIdFunnelCase(
        "SI-MW01",
        "MEASUREMENT_WINDOW",
        "AVAILABLE",
        "Begin observation after two consecutive clean cycles; stop immediately before the next reset. Candidates use first clean cycle through reset or after second clean cycle until before reset.",
        "first clean cycle through reset",
        "after second clean cycle until before reset",
    ),
    SpanIdFunnelCase(
        "SI-MW02",
        "MEASUREMENT_WINDOW",
        "MISSING",
        "The export requests window schedule WS-91, but its schedule catalog is unavailable. Candidates use receipt-day boundaries or processing-day boundaries.",
        "receipt-day boundaries",
        "processing-day boundaries",
    ),
    SpanIdFunnelCase(
        "SI-AT01",
        "ATTRIBUTE_TRANSFORM",
        "CONFLICTED",
        "The main specification says cap values at the 95th percentile; the signed appendix says cap values at the 99th percentile. Candidates use 95th-percentile capping or 99th-percentile capping.",
        "95th-percentile capping",
        "99th-percentile capping",
    ),
    SpanIdFunnelCase(
        "SI-AT02",
        "ATTRIBUTE_TRANSFORM",
        "MISSING",
        "The feature pipeline invokes transform AX-44, but its formula table is absent. Candidates use logarithmic scaling or rank normalization.",
        "logarithmic scaling",
        "rank normalization",
    ),
    SpanIdFunnelCase(
        "SI-JS01",
        "JURISDICTION_SCOPE",
        "UNSPECIFIED",
        "The review covers priority jurisdictions but provides no priority rule. Candidates include jurisdictions above three percent revenue or every jurisdiction with local regulation.",
        "jurisdictions above three percent revenue",
        "every jurisdiction with local regulation",
    ),
    SpanIdFunnelCase(
        "SI-JS02",
        "JURISDICTION_SCOPE",
        "CONFLICTED",
        "The policy manual excludes temporary branches; the later signed addendum includes temporary branches. Candidates exclude temporary branches or include temporary branches.",
        "exclude temporary branches",
        "include temporary branches",
    ),
)

CASE_COMMITMENT = hash_payload([case.commitment() for case in CASES])


def build_span_id_funnel_holdout():
    _validate_cases()
    ordered = sorted(
        CASES,
        key=lambda case: hash_payload([SPAN_ID_CORPUS_VERSION, case.case_id]),
    )
    items, bindings = [], {}
    for case in ordered:
        conflict_id = "span-id-funnel-" + hash_payload([
            SPAN_ID_CORPUS_VERSION,
            CASE_COMMITMENT,
            case.case_id,
        ])[:18]
        item = {
            "conflict_id": conflict_id,
            "public_prompt": case.public_prompt,
            "candidate_a": case.candidate_a,
            "candidate_b": case.candidate_b,
        }
        items.append(item)
        bindings[conflict_id] = {
            "case_id": case.case_id,
            "object_family": case.object_family,
            "source_status": case.source_status,
            "public_item_hash": hash_payload(item),
        }
    surface_commitment = {
        "surface_version": SPAN_ID_CORPUS_VERSION,
        "items": items,
        "source_statuses_exposed": False,
        "candidate_outputs_exposed": False,
    }
    surface = {
        **surface_commitment,
        "surface_hash": hash_payload(surface_commitment),
    }
    commitment = {
        "artifact_version": SPAN_ID_CORPUS_VERSION,
        "corpus_id": SPAN_ID_CORPUS_ID,
        "case_commitment": CASE_COMMITMENT,
        "case_count": len(CASES),
        "family_counts": {
            family: sum(case.object_family == family for case in CASES)
            for family in sorted({case.object_family for case in CASES})
        },
        "source_status_counts": {
            status: sum(case.source_status == status for case in CASES)
            for status in SOURCE_STATUSES
        },
        "public_surface": surface,
        "private_provenance": {
            "bindings": bindings,
            "source_statuses_are_synthetic_construction_metadata": True,
            "external_semantic_labels_present": False,
        },
        "reference_state": "SYNTHETIC_STRUCTURAL_SMOKE_FROZEN_BEFORE_RUN",
        "v0_24_receipts_available_during_inference": False,
        "reference_revision_allowed_after_candidate_run": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "evidence_refs": [f"corpus://{SPAN_ID_CORPUS_ID}"],
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_span_id_funnel_holdout(artifact):
    commitment = {
        key: value for key, value in artifact.items()
        if key != "artifact_hash"
    }
    if (
        artifact.get("artifact_hash") != hash_payload(commitment)
        or artifact != build_span_id_funnel_holdout()
    ):
        raise ValueError("span_id_funnel_holdout_invalid")


def evidence_text(item):
    marker = " Candidates "
    prompt = item["public_prompt"]
    return prompt.split(marker, 1)[0] if marker in prompt else prompt


def _validate_cases():
    if len(CASES) != 8 or len({case.case_id for case in CASES}) != 8:
        raise ValueError("span_id_funnel_cases_invalid")
    if {case.source_status for case in CASES} != set(SOURCE_STATUSES):
        raise ValueError("span_id_funnel_status_coverage_invalid")
    if any(
        sum(case.source_status == status for case in CASES) != 2
        for status in SOURCE_STATUSES
    ):
        raise ValueError("span_id_funnel_status_balance_invalid")
