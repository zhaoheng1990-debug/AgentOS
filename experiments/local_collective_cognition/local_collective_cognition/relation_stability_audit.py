"""Outcome-aware decomposition of relation reproducibility."""

from __future__ import annotations

import copy
from collections import Counter
from itertools import combinations

from .provider_telemetry import hash_payload


AUDIT_VERSION = "relation_stability_audit_v0_55"
ARM_IDS = ("A1_BASELINE", "A2_COMPACT_DELTA")


def audit_relation_stability(*, corpus, run, posthoc):
    _validate_hash(corpus, "artifact_hash")
    _validate_hash(run, "run_hash")
    _validate_hash(posthoc, "artifact_hash")
    measured = measure_relation_stability(corpus=corpus, run=run)
    replications = tuple(corpus["replication_ids"])
    surfaces = measured["case_surfaces"]
    summaries = measured["arm_summaries"]
    classifications = Counter(
        value["classification"] for value in posthoc["cells"]
    )
    baseline = summaries["A1_BASELINE"]
    delta = summaries["A2_COMPACT_DELTA"]
    if (
        delta["mean_pairwise_relation_jaccard"]
        < baseline["mean_pairwise_relation_jaccard"]
        and delta["mean_union_reference_coverage"]
        >= baseline["mean_union_reference_coverage"]
        and delta["unsupported_relation_occurrence_rate"]
        <= baseline["unsupported_relation_occurrence_rate"]
        and classifications["HARMFUL_ACCEPTED"] == 0
    ):
        diagnosis = "PRODUCTIVE_REFERENCE_VALID_DIVERSITY"
    elif (
        delta["unsupported_relation_occurrence_rate"]
        > baseline["unsupported_relation_occurrence_rate"]
    ):
        diagnosis = "UNSUPPORTED_RELATION_DRIFT"
    else:
        diagnosis = "MIXED_STABILITY_DIVERSITY_SIGNAL"
    commitment = {
        "audit_version": AUDIT_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_posthoc_hash": posthoc["artifact_hash"],
        "replication_ids": list(replications),
        "arm_summaries": summaries,
        "case_surfaces": surfaces,
        "posthoc_classification_distribution": dict(classifications),
        "diagnosis": diagnosis,
        "jaccard_is_sufficient_as_solo_hard_gate": False,
        "recommended_gate_family": {
            "unsupported_relation_occurrence_rate": "MAXIMIZE_PRECISION",
            "union_reference_coverage": "PRESERVE_OR_IMPROVE",
            "consensus_reference_coverage": "MINIMUM_STABLE_CORE",
            "realized_harmful_acceptance_count": "ZERO",
            "pairwise_relation_jaccard": "DIAGNOSTIC_NOT_SOLO_GATE",
        },
        "provider_calls_added": 0,
        "private_synthetic_reference_used_posthoc": True,
        "formal_v0_54_decision_unchanged": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def measure_relation_stability(*, corpus, run):
    replications = tuple(corpus["replication_ids"])
    reference = _reference_relations(corpus)
    surfaces = {}
    summaries = {}
    for arm_id in ARM_IDS:
        cells = []
        for item in corpus["public_surface"]["items"]:
            case_id = item["case_id"]
            relations = {
                rep: _projection_relations(
                    run["final_projections"].get(
                        f"{rep}:{arm_id}:{case_id}"
                    )
                )
                for rep in replications
            }
            cells.append(_case_audit(
                case_id=case_id,
                relations=relations,
                reference=reference[case_id],
                replications=replications,
            ))
        surfaces[arm_id] = cells
        summaries[arm_id] = _summarize(cells)
    return {
        "arm_summaries": summaries,
        "case_surfaces": surfaces,
    }


def _reference_relations(corpus):
    items = {
        value["case_id"]: value
        for value in corpus["public_surface"]["items"]
    }
    result = {}
    for case_id, binding in corpus["private_provenance"][
        "bindings"
    ].items():
        states = {}
        for value in binding["supported_targets"]:
            states[_pair(value)] = "SUPPORTED_EFFECT"
        for value in binding["informative_null_targets"]:
            states[_pair(value)] = "SUPPORTED_NULL"
        focal = set(binding["primary_object_ids"])
        for source in items[case_id]["object_registry"]:
            source_id = source["object_id"]
            for target_id in focal:
                pair = (source_id, target_id)
                if source_id != target_id and pair not in states:
                    states[pair] = "UNRESOLVED"
        result[case_id] = states
    return result


def _projection_relations(projection):
    if projection is None:
        return set()
    return {
        (
            value["normalized_candidate"]["source_object_id"],
            value["normalized_candidate"]["target_object_id"],
        )
        for value in projection["candidate_components"]
        if value["disposition"] != "QUARANTINED_COMPONENT"
    }


def _case_audit(*, case_id, relations, reference, replications):
    reference_set = set(reference)
    union = set().union(*(relations[rep] for rep in replications))
    intersection = set.intersection(
        *(relations[rep] for rep in replications)
    )
    pairs = []
    for left, right in combinations(replications, 2):
        left_set = relations[left]
        right_set = relations[right]
        combined = left_set | right_set
        difference = left_set ^ right_set
        pairs.append({
            "left_replication_id": left,
            "right_replication_id": right,
            "jaccard": round(
                len(left_set & right_set) / len(combined)
                if combined else 1.0,
                6,
            ),
            "reference_valid_symmetric_difference_count": len(
                difference & reference_set
            ),
            "unsupported_symmetric_difference_count": len(
                difference - reference_set
            ),
        })
    occurrences = [
        relation
        for rep in replications
        for relation in relations[rep]
    ]
    unsupported = [
        relation for relation in occurrences
        if relation not in reference_set
    ]
    return {
        "case_id": case_id,
        "reference_relation_count": len(reference_set),
        "reference_state_distribution": dict(Counter(
            reference.values()
        )),
        "relations_by_replication": {
            rep: [_relation_value(value, reference) for value in sorted(
                relations[rep]
            )]
            for rep in replications
        },
        "pairwise": pairs,
        "union_relation_count": len(union),
        "union_reference_coverage": round(
            len(union & reference_set) / len(reference_set)
            if reference_set else 1.0,
            6,
        ),
        "consensus_reference_coverage": round(
            len(intersection & reference_set) / len(reference_set)
            if reference_set else 1.0,
            6,
        ),
        "reference_valid_diversity_count": len(
            (union - intersection) & reference_set
        ),
        "unsupported_union_count": len(union - reference_set),
        "relation_occurrence_count": len(occurrences),
        "unsupported_occurrence_count": len(unsupported),
    }


def _summarize(cells):
    pairwise = [
        pair for cell in cells for pair in cell["pairwise"]
    ]
    occurrences = sum(
        value["relation_occurrence_count"] for value in cells
    )
    unsupported = sum(
        value["unsupported_occurrence_count"] for value in cells
    )
    return {
        "case_count": len(cells),
        "pair_count": len(pairwise),
        "mean_pairwise_relation_jaccard": _mean(
            value["jaccard"] for value in pairwise
        ),
        "mean_union_reference_coverage": _mean(
            value["union_reference_coverage"] for value in cells
        ),
        "mean_consensus_reference_coverage": _mean(
            value["consensus_reference_coverage"] for value in cells
        ),
        "reference_valid_diversity_count": sum(
            value["reference_valid_diversity_count"] for value in cells
        ),
        "unsupported_union_count": sum(
            value["unsupported_union_count"] for value in cells
        ),
        "relation_occurrence_count": occurrences,
        "unsupported_relation_occurrence_count": unsupported,
        "unsupported_relation_occurrence_rate": round(
            unsupported / occurrences if occurrences else 0.0,
            6,
        ),
        "reference_valid_pairwise_difference_count": sum(
            value["reference_valid_symmetric_difference_count"]
            for value in pairwise
        ),
        "unsupported_pairwise_difference_count": sum(
            value["unsupported_symmetric_difference_count"]
            for value in pairwise
        ),
    }


def _relation_value(relation, reference):
    return {
        "source_object_id": relation[0],
        "target_object_id": relation[1],
        "reference_state": reference.get(relation, "UNSUPPORTED"),
    }


def _pair(value):
    return value["source_object_id"], value["target_object_id"]


def _mean(values):
    values = list(values)
    return round(sum(values) / len(values) if values else 0.0, 6)


def _validate_hash(value, field):
    commitment = {
        key: copy.deepcopy(item)
        for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError("relation_stability_source_hash_invalid")
