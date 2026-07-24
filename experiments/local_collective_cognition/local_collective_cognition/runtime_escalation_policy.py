"""Zero-marginal-token escalation policy derived from a standard receipt."""

from __future__ import annotations

from collections import Counter

from .provider_telemetry import hash_payload


POLICY_VERSION = "runtime_escalation_policy_v0_33"
ROUTE_IDS = (
    "A1_ONTOLOGY",
    "MECHANISM",
    "ADVERSARIAL",
    "COORDINATE_SHIFT",
)
DIAGNOSTIC_FLAGS = (
    "RELATION_COLLAPSE",
    "NARROW_OBJECT_FRAME",
    "THIN_EVIDENCE_BINDING",
    "SPECULATION_DOMINANCE",
)


def derive_escalation_receipt(*, raw_receipt, item):
    """Derive one replayable decision without Provider text or private truth."""
    candidates = (
        raw_receipt.get("problem_candidates", [])
        if isinstance(raw_receipt, dict)
        else []
    )
    candidates = [
        value for value in candidates if isinstance(value, dict)
    ]
    object_ids = {
        value["object_id"] for value in item["object_registry"]
    }
    span_ids = {
        value["span_id"] for value in item["evidence_spans"]
    }
    relations = {
        (value.get("source_object_id"), value.get("target_object_id"))
        for value in candidates
        if value.get("source_object_id") in object_ids
        and value.get("target_object_id") in object_ids
    }
    used_objects = {
        object_id
        for value in candidates
        for object_id in (
            value.get("source_object_id"),
            value.get("target_object_id"),
        )
        if object_id in object_ids
    }
    used_spans = {
        span_id
        for value in candidates
        for span_id in value.get("evidence_span_ids", [])
        if span_id in span_ids
    }
    target_counts = Counter(
        value.get("target_object_id")
        for value in candidates
        if value.get("target_object_id") in object_ids
    )
    speculative_count = sum(
        value.get("lane") == "FRONTIER"
        or value.get("epistemic_basis") == "SPECULATIVE"
        for value in candidates
    )
    candidate_count = len(candidates)
    relation_count = len(relations)
    object_coverage = _ratio(len(used_objects), len(object_ids))
    evidence_coverage = _ratio(len(used_spans), len(span_ids))
    target_concentration = _ratio(
        max(target_counts.values(), default=0),
        candidate_count,
    )
    speculative_fraction = _ratio(
        speculative_count,
        candidate_count,
    )
    flags = []
    if candidate_count == 3 and relation_count < 3:
        flags.append("RELATION_COLLAPSE")
    if object_coverage <= 0.5 and target_concentration >= 2 / 3:
        flags.append("NARROW_OBJECT_FRAME")
    if evidence_coverage < 0.7:
        flags.append("THIN_EVIDENCE_BINDING")
    if speculative_fraction >= 2 / 3 and evidence_coverage < 0.85:
        flags.append("SPECULATION_DOMINANCE")

    if "RELATION_COLLAPSE" in flags or "NARROW_OBJECT_FRAME" in flags:
        route_id = "COORDINATE_SHIFT"
    elif "THIN_EVIDENCE_BINDING" in flags:
        route_id = "ADVERSARIAL"
    elif "SPECULATION_DOMINANCE" in flags:
        route_id = "MECHANISM"
    else:
        route_id = "A1_ONTOLOGY"
    commitment = {
        "policy_version": POLICY_VERSION,
        "case_id": item["case_id"],
        "source_raw_receipt_hash": hash_payload(raw_receipt),
        "private_truth_used": False,
        "provider_generated_trigger_text_used": False,
        "metrics": {
            "candidate_count": candidate_count,
            "unique_relation_count": relation_count,
            "object_coverage": object_coverage,
            "evidence_span_coverage": evidence_coverage,
            "target_concentration": target_concentration,
            "speculative_fraction": speculative_fraction,
        },
        "diagnostic_flags": flags,
        "triggered": bool(flags),
        "route_id": route_id,
        "stop_condition": (
            "Execute at most one specialized worker for this receipt."
        ),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_escalation_receipt(*, receipt, raw_receipt, item):
    expected = derive_escalation_receipt(
        raw_receipt=raw_receipt,
        item=item,
    )
    if receipt != expected:
        raise ValueError("runtime_escalation_receipt_invalid")


def _ratio(numerator, denominator):
    return round(numerator / denominator if denominator else 0.0, 6)
