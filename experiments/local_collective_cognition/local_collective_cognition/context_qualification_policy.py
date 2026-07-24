"""Context-normalized zero-token qualification policy v0.53."""

from __future__ import annotations

from collections import Counter

from .candidate_pool_arbitration import relation_id
from .null_role_candidate_composition import SCORE_MAP
from .provider_telemetry import hash_payload
from .selective_delta_policy import (
    MINIMUM_COMPOUND_DIAGNOSTICS,
    MINIMUM_SECOND_SCORE,
    MINIMUM_SEMANTIC_SPREAD,
)


POLICY_VERSION = "context_qualification_policy_v0_53"
QUALIFICATION_BASES = (
    "LEGACY_ASYMMETRY",
    "STRUCTURAL_OPPORTUNITY_GAP",
    "BOTH",
    "NONE",
)


def derive_context_qualification(
    *, raw_receipt, item, escalation_receipt
):
    candidates = raw_receipt.get("problem_candidates", [])
    scores = sorted(
        (_semantic_score(value) for value in candidates),
        reverse=True,
    )
    score_spread = scores[0] - scores[-1] if len(scores) == 3 else 0
    second_score = scores[1] if len(scores) == 3 else 0
    diagnostic_count = len(
        escalation_receipt.get("diagnostic_flags", [])
    )
    legacy_asymmetry = bool(
        len(scores) == 3
        and score_spread >= MINIMUM_SEMANTIC_SPREAD
        and (
            second_score >= MINIMUM_SECOND_SCORE
            or diagnostic_count >= MINIMUM_COMPOUND_DIAGNOSTICS
        )
    )
    base_relations = {
        relation_id(value) for value in candidates
    }
    used_spans = {
        span_id
        for value in candidates
        for span_id in value.get("evidence_span_ids", [])
    }
    focal = item["focal_object_id"]
    structural = []
    for opportunity in raw_receipt.get("admission_opportunities", []):
        current = (
            f"{opportunity.get('source_object_id')}->"
            f"{opportunity.get('target_object_id')}"
        )
        novel_spans = sorted(
            set(opportunity.get("evidence_span_ids", [])) - used_spans
        )
        focal_relation = focal in {
            opportunity.get("source_object_id"),
            opportunity.get("target_object_id"),
        }
        if (
            current not in base_relations
            and focal_relation
            and novel_spans
            and _review_ready(opportunity)
        ):
            structural.append({
                "relation_id": current,
                "opportunity_type": opportunity["opportunity_type"],
                "novel_evidence_span_ids": novel_spans,
                "source_evidence_span_ids": list(
                    opportunity["evidence_span_ids"]
                ),
            })
    structural.sort(key=lambda value: hash_payload([
        POLICY_VERSION,
        escalation_receipt["artifact_hash"],
        value["relation_id"],
    ]))
    triggered = escalation_receipt.get("triggered") is True
    structural_gap = bool(triggered and structural)
    qualified = bool(triggered and (legacy_asymmetry or structural_gap))
    if legacy_asymmetry and structural_gap:
        basis = "BOTH"
    elif legacy_asymmetry:
        basis = "LEGACY_ASYMMETRY"
    elif structural_gap:
        basis = "STRUCTURAL_OPPORTUNITY_GAP"
    else:
        basis = "NONE"
    commitment = {
        "policy_version": POLICY_VERSION,
        "case_id": item["case_id"],
        "source_raw_receipt_hash": hash_payload(raw_receipt),
        "source_escalation_receipt_hash": escalation_receipt[
            "artifact_hash"
        ],
        "semantic_scores_descending": scores,
        "semantic_score_spread": score_spread,
        "second_highest_semantic_score": second_score,
        "diagnostic_count": diagnostic_count,
        "legacy_thresholds": {
            "minimum_semantic_spread": MINIMUM_SEMANTIC_SPREAD,
            "minimum_second_score": MINIMUM_SECOND_SCORE,
            "minimum_compound_diagnostics": (
                MINIMUM_COMPOUND_DIAGNOSTICS
            ),
        },
        "legacy_asymmetry_satisfied": legacy_asymmetry,
        "structural_opportunity_gap_satisfied": structural_gap,
        "structural_opportunity_count": len(structural),
        "structural_opportunities": structural,
        "qualification_basis": basis,
        "qualified": qualified,
        "route_id": (
            escalation_receipt["route_id"]
            if qualified else "A1_ONTOLOGY"
        ),
        "private_truth_used": False,
        "provider_generated_qualification_text_used": False,
        "additional_provider_call_used": False,
        "absolute_threshold_retuned_from_v0_41": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def audit_context_qualification_calibration(*, sources):
    source_metrics = {}
    basis = Counter()
    total_old = total_new = total_receipts = 0
    for source_id, corpus, run in sources:
        raw_items = {
            value["case_id"]: value
            for value in corpus["public_surface"]["items"]
        }
        rows = []
        for key, old in sorted(run["qualification_receipts"].items()):
            rep, _, case_id = key.split(":", 2)
            raw = run["raw_receipts"][
                f"{rep}:SHARED_STANDARD:STANDARD_OPPORTUNITY:{case_id}"
            ]
            new = derive_context_qualification(
                raw_receipt=raw,
                item=raw_items[case_id],
                escalation_receipt=run["trigger_receipts"][key],
            )
            rows.append({
                "key": key,
                "old_qualified": old["qualified"],
                "new_qualified": new["qualified"],
                "qualification_basis": new["qualification_basis"],
                "semantic_score_spread": new[
                    "semantic_score_spread"
                ],
                "structural_opportunity_count": new[
                    "structural_opportunity_count"
                ],
            })
            basis[new["qualification_basis"]] += 1
        old_count = sum(value["old_qualified"] for value in rows)
        new_count = sum(value["new_qualified"] for value in rows)
        total_old += old_count
        total_new += new_count
        total_receipts += len(rows)
        source_metrics[source_id] = {
            "source_corpus_hash": corpus["artifact_hash"],
            "source_run_hash": run["run_hash"],
            "receipt_count": len(rows),
            "old_qualified_count": old_count,
            "new_qualified_count": new_count,
            "new_qualification_rate": round(
                new_count / len(rows) if rows else 0.0, 6
            ),
            "rows": rows,
        }
    rates = [
        value["new_qualification_rate"]
        for value in source_metrics.values()
    ]
    commitment = {
        "calibration_version": (
            "context_qualification_unlabeled_calibration_v0_53"
        ),
        "source_policy_version": POLICY_VERSION,
        "source_metrics": source_metrics,
        "source_count": len(source_metrics),
        "total_receipt_count": total_receipts,
        "old_qualified_count": total_old,
        "new_qualified_count": total_new,
        "qualification_basis_distribution": dict(basis),
        "cross_source_rate_range": round(
            max(rates) - min(rates) if rates else 0.0, 6
        ),
        "private_outcomes_accessed": False,
        "posthoc_labels_accessed": False,
        "provider_calls_added": 0,
        "absolute_threshold_retuned_from_v0_41": False,
        "calibration_authority": "PREREGISTRATION_INPUT_ONLY",
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _semantic_score(candidate):
    value = candidate.get("candidate_value", {})
    return sum(
        mapping.get(value.get(axis), min(mapping.values()))
        for axis, mapping in SCORE_MAP.items()
    )


def _review_ready(value):
    if value.get("opportunity_type") == "EFFECT":
        return (
            value.get("relation_truth_state") == "SUPPORTED_EFFECT"
            and value.get("constraint_binding") == "ADEQUATE"
            and value.get("expected_cbit") in {"HIGH", "MEDIUM"}
            and value.get("research_value_disposition")
            in {"PRIORITIZE", "RETAIN"}
        )
    if value.get("opportunity_type") == "INFORMATIVE_NULL":
        return (
            value.get("relation_truth_state")
            in {"SUPPORTED_NULL", "WEAK", "INDIRECT", "CONFLICTED"}
            and value.get("null_information_role")
            == "RULES_OUT_PLAUSIBLE_CAUSE"
            and value.get("constraint_binding") == "ADEQUATE"
            and value.get("expected_cbit") in {"HIGH", "MEDIUM"}
            and value.get("research_value_disposition")
            in {"PRIORITIZE", "RETAIN"}
        )
    return (
        value.get("opportunity_type") == "QUARANTINE_ALTERNATIVE"
        and value.get("constraint_binding") in {"ADEQUATE", "PARTIAL"}
        and value.get("expected_cbit") in {"HIGH", "MEDIUM"}
        and value.get("research_value_disposition")
        in {"PRIORITIZE", "RETAIN"}
    )
