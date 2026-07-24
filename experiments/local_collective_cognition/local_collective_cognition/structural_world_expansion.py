"""Structure-first problem-emergence smoke runtime v0.26."""

from __future__ import annotations

from collections import Counter
from statistics import mean

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .provider_telemetry import hash_payload
from .structural_world_constraints import (
    CONSTRAINT_VERSION,
    validate_science_institutional_constraints,
)
from .structural_world_holdout import validate_structural_world_holdout


RUNTIME_VERSION = "structural_world_expansion_smoke_v0_26"
TASK_KIND = "STRUCTURAL_WORLD_EXPANSION_SMOKE"
ARM_IDS = ("A0_DIRECT", "A1_ONTOLOGY", "A2_GRAPH", "A3_INTERVENTION")
OBJECT_TYPES = (
    "ACTOR", "PROCESS", "STATE", "RESOURCE", "CONSTRAINT",
    "OBSERVABLE", "EVIDENCE_SOURCE", "POLICY",
)
RELATION_TYPES = (
    "AFFECTS", "CONSTRAINS", "MEASURES", "PRECEDES", "ENABLES",
    "GOVERNS", "DEPENDS_ON", "CONTRADICTS", "ALTERNATIVE_TO",
)
EPISTEMIC_STATUSES = ("OBSERVED", "INFERRED", "HYPOTHETICAL")
COORDINATES = (
    "OBJECT", "PROCESS", "CAUSAL", "MEASUREMENT", "INSTITUTIONAL",
    "TEMPORAL", "EVIDENCE",
)
QUESTION_TYPES = (
    "CAUSAL", "DISCRIMINATIVE", "BOUNDARY", "MEASUREMENT",
    "COUNTERFACTUAL",
)
INTERVENTION_TYPES = (
    "REVERSE_RELATION", "REMOVE_RELATION", "SWITCH_OBJECT",
    "SWITCH_COORDINATE", "SEARCH_COUNTEREXAMPLE",
)


ARM_METHODS = {
    "A0_DIRECT": {
        "name": "direct_problem_expansion",
        "instructions": [
            "Formulate research questions directly from the evidence packet.",
            "Do not emit an object census, relation graph, perspective, or intervention.",
            "Bind every problem to registered objects and evidence spans.",
        ],
    },
    "A1_ONTOLOGY": {
        "name": "multiview_ontology_then_problem",
        "instructions": [
            "First classify relevant registered objects across actor, process, state, resource, constraint, observable, evidence-source, and policy views.",
            "Identify hidden constraints and invariants before formulating problems.",
            "Do not emit a relation graph, perspective, or intervention.",
        ],
    },
    "A2_GRAPH": {
        "name": "ontology_graph_and_situated_perspectives",
        "instructions": [
            "Build an evidence-bound relation graph after the object census.",
            "Generate situated perspectives bound to different graph objects and coordinates.",
            "Use discrepancies between positions to formulate problems.",
            "Do not emit interventions.",
        ],
    },
    "A3_INTERVENTION": {
        "name": "graph_with_reverse_and_coordinate_interventions",
        "instructions": [
            "Build the ontology, relation graph, and situated perspectives.",
            "Apply reverse-relation, relation-removal, object-switch, coordinate-switch, or counterexample-search interventions.",
            "Formulate problems from predicted discrepancies and sensitivity to those interventions.",
        ],
    },
}


def build_structural_world_preregistration(*, constraints, corpus):
    validate_science_institutional_constraints(constraints)
    validate_structural_world_holdout(corpus)
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "science_constraint_hash": constraints["artifact_hash"],
        "science_constraint_version": CONSTRAINT_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "frozen_hypothesis": (
            "Expanding object structure before question generation improves "
            "evidence-bound identification of unresolved relations compared "
            "with direct question generation."
        ),
        "arms": [
            {"arm_id": arm_id, **ARM_METHODS[arm_id]}
            for arm_id in ARM_IDS
        ],
        "primary_metric": "mean_problem_target_f1",
        "secondary_metrics": [
            "primary_object_recall",
            "hidden_constraint_recall",
            "critical_relation_recall",
            "counterevidence_recall",
            "invariant_recall",
            "nonredundant_problem_rate",
            "cross_coordinate_valid_target_rate",
            "tokens_per_valid_cbit_event",
        ],
        "success_gate": {
            "minimum_receipt_coverage_per_arm": 0.9,
            "minimum_best_structural_problem_target_f1": 0.55,
            "minimum_problem_target_f1_gain_over_direct": 0.08,
            "minimum_best_structural_counterevidence_recall": 0.5,
            "maximum_task_calls": 48,
            "maximum_total_tokens": 140000,
        },
        "frozen_before_provider_run": True,
        "private_construction_metadata_available_to_provider": False,
        "prior_v0_25_labels_reused": False,
        "one_provider_call_counts_as_group_cognition": False,
        "recursive_society_tested": False,
        "claim_ceiling": constraints["claim_ceiling"],
        "selection_authority": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_structural_world_preregistration(
    preregistration, *, constraints, corpus
):
    expected = build_structural_world_preregistration(
        constraints=constraints, corpus=corpus
    )
    if preregistration != expected:
        raise ValueError("structural_world_preregistration_invalid")


def structural_world_schema(*, case_id, arm_id, object_ids, span_ids, refs):
    object_array = {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["object_id", "object_type", "anchor_span_ids"],
            "properties": {
                "object_id": {"type": "string", "enum": list(object_ids)},
                "object_type": {"type": "string", "enum": list(OBJECT_TYPES)},
                "anchor_span_ids": {
                    "type": "array", "items": {
                        "type": "string", "enum": list(span_ids)
                    },
                },
            },
        },
    }
    relation_array = {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "relation_id", "source_object_id", "relation_type",
                "target_object_id", "epistemic_status", "evidence_span_ids",
            ],
            "properties": {
                "relation_id": {"type": "string"},
                "source_object_id": {
                    "type": "string", "enum": list(object_ids)
                },
                "relation_type": {
                    "type": "string", "enum": list(RELATION_TYPES)
                },
                "target_object_id": {
                    "type": "string", "enum": list(object_ids)
                },
                "epistemic_status": {
                    "type": "string", "enum": list(EPISTEMIC_STATUSES)
                },
                "evidence_span_ids": {
                    "type": "array", "items": {
                        "type": "string", "enum": list(span_ids)
                    },
                },
            },
        },
    }
    problem_array = {
        "type": "array",
        "minItems": 2,
        "maxItems": 4,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "problem_id", "question", "focal_object_ids",
                "constraint_object_ids", "target_relation", "question_type",
                "coordinate", "falsifier", "required_observation",
                "evidence_span_ids",
            ],
            "properties": {
                "problem_id": {"type": "string"},
                "question": {"type": "string"},
                "focal_object_ids": {"type": "array", "items": {
                    "type": "string", "enum": list(object_ids)
                }},
                "constraint_object_ids": {"type": "array", "items": {
                    "type": "string", "enum": list(object_ids)
                }},
                "target_relation": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["source_object_id", "target_object_id"],
                    "properties": {
                        "source_object_id": {
                            "type": "string", "enum": list(object_ids)
                        },
                        "target_object_id": {
                            "type": "string", "enum": list(object_ids)
                        },
                    },
                },
                "question_type": {
                    "type": "string", "enum": list(QUESTION_TYPES)
                },
                "coordinate": {
                    "type": "string", "enum": list(COORDINATES)
                },
                "falsifier": {"type": "string"},
                "required_observation": {"type": "string"},
                "evidence_span_ids": {"type": "array", "items": {
                    "type": "string", "enum": list(span_ids)
                }},
            },
        },
    }
    properties = {
        "case_id": {"type": "string", "enum": [case_id]},
        "arm_id": {"type": "string", "enum": [arm_id]},
        "object_census": object_array,
        "relation_graph": relation_array,
        "situated_perspectives": {
            "type": "array", "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "perspective_id", "bound_object_id", "coordinate",
                    "observation",
                ],
                "properties": {
                    "perspective_id": {"type": "string"},
                    "bound_object_id": {
                        "type": "string", "enum": list(object_ids)
                    },
                    "coordinate": {
                        "type": "string", "enum": list(COORDINATES)
                    },
                    "observation": {"type": "string"},
                },
            },
        },
        "interventions": {
            "type": "array", "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "intervention_id", "intervention_type",
                    "target_object_ids", "target_relation_ids",
                    "predicted_discrepancy",
                ],
                "properties": {
                    "intervention_id": {"type": "string"},
                    "intervention_type": {
                        "type": "string", "enum": list(INTERVENTION_TYPES)
                    },
                    "target_object_ids": {"type": "array", "items": {
                        "type": "string", "enum": list(object_ids)
                    }},
                    "target_relation_ids": {
                        "type": "array", "items": {"type": "string"}
                    },
                    "predicted_discrepancy": {"type": "string"},
                },
            },
        },
        "identified_constraint_object_ids": {
            "type": "array", "items": {
                "type": "string", "enum": list(object_ids)
            },
        },
        "invariant_object_ids": {
            "type": "array", "items": {
                "type": "string", "enum": list(object_ids)
            },
        },
        "counterevidence_span_ids": {
            "type": "array", "items": {
                "type": "string", "enum": list(span_ids)
            },
        },
        "problem_candidates": problem_array,
        "selected_problem_id": {"type": "string"},
        "synthesis": {"type": "string"},
        "evidence_refs": {
            "type": "array",
            "items": {"type": "string", "enum": list(refs)},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def validate_structural_world_receipt(
    receipt, *, item, arm_id, evidence_refs
):
    top_keys = {
        "case_id", "arm_id", "object_census", "relation_graph",
        "situated_perspectives", "interventions",
        "identified_constraint_object_ids", "invariant_object_ids",
        "counterevidence_span_ids", "problem_candidates",
        "selected_problem_id", "synthesis", "evidence_refs",
    }
    object_ids = {
        value["object_id"] for value in item["object_registry"]
    }
    span_ids = {value["span_id"] for value in item["evidence_spans"]}
    if (
        not isinstance(receipt, dict)
        or set(receipt) != top_keys
        or receipt.get("case_id") != item["case_id"]
        or receipt.get("arm_id") != arm_id
        or receipt.get("evidence_refs") != list(evidence_refs)
        or not str(receipt.get("synthesis", "")).strip()
    ):
        raise ValueError("structural_world_receipt_invalid")
    _validate_id_list(
        receipt["identified_constraint_object_ids"], object_ids, allow_empty=True
    )
    _validate_id_list(
        receipt["invariant_object_ids"], object_ids, allow_empty=True
    )
    _validate_id_list(
        receipt["counterevidence_span_ids"], span_ids, allow_empty=True
    )
    _validate_object_census(receipt["object_census"], object_ids, span_ids)
    relation_ids = _validate_relations(
        receipt["relation_graph"], object_ids, span_ids
    )
    _validate_perspectives(
        receipt["situated_perspectives"], object_ids
    )
    _validate_interventions(
        receipt["interventions"], object_ids, relation_ids
    )
    problem_ids = _validate_problems(
        receipt["problem_candidates"], object_ids, span_ids
    )
    if receipt["selected_problem_id"] not in problem_ids:
        raise ValueError("structural_world_receipt_selected_problem_invalid")
    required_nonempty = {
        "A0_DIRECT": (),
        "A1_ONTOLOGY": ("object_census",),
        "A2_GRAPH": (
            "object_census", "relation_graph", "situated_perspectives"
        ),
        "A3_INTERVENTION": (
            "object_census", "relation_graph", "situated_perspectives",
            "interventions",
        ),
    }[arm_id]
    required_empty = {
        "A0_DIRECT": (
            "object_census", "relation_graph", "situated_perspectives",
            "interventions",
        ),
        "A1_ONTOLOGY": (
            "relation_graph", "situated_perspectives", "interventions"
        ),
        "A2_GRAPH": ("interventions",),
        "A3_INTERVENTION": (),
    }[arm_id]
    if any(not receipt[name] for name in required_nonempty):
        raise ValueError("structural_world_receipt_stage_missing")
    if any(receipt[name] for name in required_empty):
        raise ValueError("structural_world_receipt_stage_leakage")


def run_structural_world_smoke(
    *, constraints, corpus, preregistration, adapter
):
    validate_science_institutional_constraints(constraints)
    validate_structural_world_holdout(corpus)
    validate_structural_world_preregistration(
        preregistration, constraints=constraints, corpus=corpus
    )
    refs = tuple(corpus["evidence_refs"])
    matrix = [
        (arm_id, item)
        for arm_id in ARM_IDS
        for item in corpus["public_surface"]["items"]
    ]
    matrix.sort(
        key=lambda value: hash_payload([
            RUNTIME_VERSION, value[0], value[1]["case_id"]
        ])
    )
    calls, receipts, failures = [], {}, []
    for arm_id, item in matrix:
        task = _task(item, arm_id, refs, adapter)
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(arm_id, item["case_id"], task, envelope)
        calls.append(call)
        if envelope.status != "COMPLETED":
            failures.append({
                "case_id": item["case_id"],
                "arm_id": arm_id,
                "stage": "PROVIDER_INVOCATION",
                "status": envelope.status,
                "invocation_receipt": envelope.invocation_receipt.as_dict(),
            })
            continue
        receipt = envelope.normalized_result
        try:
            validate_structural_world_receipt(
                receipt, item=item, arm_id=arm_id, evidence_refs=refs
            )
        except ValueError as exc:
            failures.append({
                "case_id": item["case_id"],
                "arm_id": arm_id,
                "stage": "RUNTIME_VALIDATION",
                "status": "REJECTED",
                "reason": str(exc),
                "output_hash": hash_payload(receipt),
                "rejected_output": receipt,
            })
            continue
        receipts[f"{arm_id}:{item['case_id']}"] = receipt
    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_constraint_hash": constraints["artifact_hash"],
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "receipts": receipts,
        "failures": failures,
        "private_construction_metadata_available_during_inference": False,
        "provider_has_final_state_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_structural_world_smoke(
    *, constraints, corpus, preregistration, run
):
    validate_science_institutional_constraints(constraints)
    validate_structural_world_holdout(corpus)
    validate_structural_world_preregistration(
        preregistration, constraints=constraints, corpus=corpus
    )
    if (
        run.get("run_hash") != hash_payload({
            key: value for key, value in run.items() if key != "run_hash"
        })
        or run.get("source_corpus_hash") != corpus["artifact_hash"]
    ):
        raise ValueError("structural_world_run_invalid")
    items = {
        item["case_id"]: item for item in corpus["public_surface"]["items"]
    }
    bindings = corpus["private_provenance"]["bindings"]
    calls = {
        (call["arm_id"], call["case_id"]): call
        for call in run["task_calls"]
    }
    rows = []
    for key, receipt in run["receipts"].items():
        arm_id, case_id = key.split(":", 1)
        rows.append(_score_receipt(
            arm_id=arm_id,
            item=items[case_id],
            truth=bindings[case_id],
            receipt=receipt,
            call=calls[(arm_id, case_id)],
        ))
    arm_metrics = {
        arm_id: _aggregate_arm(
            [row for row in rows if row["arm_id"] == arm_id],
            expected_count=corpus["case_count"],
            calls=[
                call for call in run["task_calls"]
                if call["arm_id"] == arm_id
            ],
        )
        for arm_id in ARM_IDS
    }
    structural_arms = ARM_IDS[1:]
    best_arm = max(
        structural_arms,
        key=lambda arm_id: (
            arm_metrics[arm_id]["mean_problem_target_f1"],
            -arm_metrics[arm_id]["tokens_per_valid_cbit_event"],
        ),
    )
    baseline = arm_metrics["A0_DIRECT"]["mean_problem_target_f1"]
    comparison_valid = (
        arm_metrics["A0_DIRECT"]["receipt_coverage"]
        >= preregistration["success_gate"][
            "minimum_receipt_coverage_per_arm"
        ]
        and arm_metrics[best_arm]["receipt_coverage"]
        >= preregistration["success_gate"][
            "minimum_receipt_coverage_per_arm"
        ]
    )
    gain = (
        round(
            arm_metrics[best_arm]["mean_problem_target_f1"] - baseline,
            6,
        )
        if comparison_valid else None
    )
    total_tokens = sum(
        _call_token_count(call) for call in run["task_calls"]
    )
    gate = preregistration["success_gate"]
    conditions = {
        "minimum_receipt_coverage_per_arm": all(
            value["receipt_coverage"]
            >= gate["minimum_receipt_coverage_per_arm"]
            for value in arm_metrics.values()
        ),
        "minimum_best_structural_problem_target_f1": (
            arm_metrics[best_arm]["mean_problem_target_f1"]
            >= gate["minimum_best_structural_problem_target_f1"]
        ),
        "minimum_problem_target_f1_gain_over_direct": (
            gain is not None
            and gain >= gate["minimum_problem_target_f1_gain_over_direct"]
        ),
        "minimum_best_structural_counterevidence_recall": (
            arm_metrics[best_arm]["mean_counterevidence_recall"]
            >= gate["minimum_best_structural_counterevidence_recall"]
        ),
        "maximum_task_calls": (
            len(run["task_calls"]) <= gate["maximum_task_calls"]
        ),
        "maximum_total_tokens": total_tokens <= gate["maximum_total_tokens"],
        "authority_boundary_preserved": all(
            run.get(name) is False
            for name in (
                "provider_has_final_state_authority",
                "selection_authority",
                "retention_authority",
                "production_authority",
            )
        ),
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "rows": sorted(rows, key=lambda row: (row["arm_id"], row["case_id"])),
        "arm_metrics": arm_metrics,
        "best_structural_arm": best_arm,
        "direct_problem_target_f1": baseline,
        "best_structural_problem_target_f1": arm_metrics[
            best_arm
        ]["mean_problem_target_f1"],
        "primary_comparison_valid": comparison_valid,
        "problem_target_f1_gain_over_direct": gain,
        "task_call_count": len(run["task_calls"]),
        "valid_receipt_count": len(run["receipts"]),
        "failure_count": len(run["failures"]),
        "failure_counts": dict(Counter(
            f"{value['arm_id']}:{value['stage']}"
            for value in run["failures"]
        )),
        "total_tokens": total_tokens,
        "gate_conditions": conditions,
        "structure_first_smoke_gate": "PASS" if passed else "REJECT",
        "fresh_replication_authorized": passed,
        "recursive_society_authorized": False,
        "external_panel_required_before_semantic_claim": True,
        "candidate_state": (
            "STRUCTURE_FIRST_SMOKE_PASSED_READY_FRESH_REPLICATION"
            if passed else "STRUCTURE_FIRST_SMOKE_REJECTED_STOP"
        ),
        "claim_scope": preregistration["claim_ceiling"],
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _task(item, arm_id, refs, adapter):
    object_ids = tuple(
        value["object_id"] for value in item["object_registry"]
    )
    span_ids = tuple(
        value["span_id"] for value in item["evidence_spans"]
    )
    method = ARM_METHODS[arm_id]
    return ProviderCognitiveTask(
        task_id=f"{RUNTIME_VERSION}-{arm_id}-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Use only the registered objects and immutable evidence spans. "
            "Follow the supplied method in order, preserve contradictions and "
            "uncertainty, and propose two to four falsifiable research problems. "
            "A relation marked OBSERVED must have supporting span IDs. Do not "
            "treat a simulated or hypothetical consequence as observed evidence."
        ),
        inputs={
            "stage": "STRUCTURE_FIRST_PROBLEM_EMERGENCE",
            "arm_id": arm_id,
            "method_name": method["name"],
            "method_instructions": method["instructions"],
            "public_case": item,
            "authority_boundary": {
                "provider_output_state": "CANDIDATE_RECEIPT",
                "provider_has_final_authority": False,
            },
        },
        allowed_evidence=list(refs),
        expected_schema=structural_world_schema(
            case_id=item["case_id"],
            arm_id=arm_id,
            object_ids=object_ids,
            span_ids=span_ids,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _call(arm_id, case_id, task, envelope):
    commitment = {
        "arm_id": arm_id,
        "case_id": case_id,
        "status": envelope.status,
        "task_contract_hash": task.contract_hash(),
        "task_input_keys": sorted(task.inputs),
        "private_truth_keys_exposed": False,
        "normalized_result_hash": (
            hash_payload(envelope.normalized_result)
            if envelope.status == "COMPLETED" else ""
        ),
        "invocation_receipt": envelope.invocation_receipt.as_dict(),
    }
    return {**commitment, "call_hash": hash_payload(commitment)}


def _validate_id_list(values, allowed, *, allow_empty):
    if (
        not isinstance(values, list)
        or (not allow_empty and not values)
        or len(values) != len(set(values))
        or not set(values).issubset(allowed)
    ):
        raise ValueError("structural_world_receipt_id_list_invalid")


def _validate_object_census(values, object_ids, span_ids):
    if not isinstance(values, list) or len(values) > len(object_ids):
        raise ValueError("structural_world_receipt_object_census_invalid")
    seen = set()
    for value in values:
        if (
            not isinstance(value, dict)
            or set(value) != {
                "object_id", "object_type", "anchor_span_ids"
            }
            or value["object_id"] not in object_ids
            or value["object_id"] in seen
            or value["object_type"] not in OBJECT_TYPES
        ):
            raise ValueError("structural_world_receipt_object_census_invalid")
        _validate_id_list(
            value["anchor_span_ids"], span_ids, allow_empty=False
        )
        seen.add(value["object_id"])


def _validate_relations(values, object_ids, span_ids):
    if not isinstance(values, list) or len(values) > 10:
        raise ValueError("structural_world_receipt_relation_graph_invalid")
    relation_ids = set()
    for value in values:
        if (
            not isinstance(value, dict)
            or set(value) != {
                "relation_id", "source_object_id", "relation_type",
                "target_object_id", "epistemic_status", "evidence_span_ids",
            }
            or not str(value["relation_id"]).strip()
            or value["relation_id"] in relation_ids
            or value["source_object_id"] not in object_ids
            or value["target_object_id"] not in object_ids
            or value["source_object_id"] == value["target_object_id"]
            or value["relation_type"] not in RELATION_TYPES
            or value["epistemic_status"] not in EPISTEMIC_STATUSES
        ):
            raise ValueError("structural_world_receipt_relation_graph_invalid")
        _validate_id_list(
            value["evidence_span_ids"],
            span_ids,
            allow_empty=value["epistemic_status"] == "HYPOTHETICAL",
        )
        relation_ids.add(value["relation_id"])
    return relation_ids


def _validate_perspectives(values, object_ids):
    if not isinstance(values, list) or len(values) > 8:
        raise ValueError("structural_world_receipt_perspective_invalid")
    seen = set()
    for value in values:
        if (
            not isinstance(value, dict)
            or set(value) != {
                "perspective_id", "bound_object_id", "coordinate",
                "observation",
            }
            or not str(value["perspective_id"]).strip()
            or value["perspective_id"] in seen
            or value["bound_object_id"] not in object_ids
            or value["coordinate"] not in COORDINATES
            or not str(value["observation"]).strip()
        ):
            raise ValueError("structural_world_receipt_perspective_invalid")
        seen.add(value["perspective_id"])


def _validate_interventions(values, object_ids, relation_ids):
    if not isinstance(values, list) or len(values) > 8:
        raise ValueError("structural_world_receipt_intervention_invalid")
    seen = set()
    for value in values:
        if (
            not isinstance(value, dict)
            or set(value) != {
                "intervention_id", "intervention_type",
                "target_object_ids", "target_relation_ids",
                "predicted_discrepancy",
            }
            or not str(value["intervention_id"]).strip()
            or value["intervention_id"] in seen
            or value["intervention_type"] not in INTERVENTION_TYPES
            or not str(value["predicted_discrepancy"]).strip()
        ):
            raise ValueError("structural_world_receipt_intervention_invalid")
        _validate_id_list(
            value["target_object_ids"], object_ids, allow_empty=True
        )
        _validate_id_list(
            value["target_relation_ids"], relation_ids, allow_empty=True
        )
        if (
            not value["target_object_ids"]
            and not value["target_relation_ids"]
        ):
            raise ValueError("structural_world_receipt_intervention_unbound")
        seen.add(value["intervention_id"])


def _validate_problems(values, object_ids, span_ids):
    if not isinstance(values, list) or not 2 <= len(values) <= 4:
        raise ValueError("structural_world_receipt_problem_invalid")
    problem_ids = set()
    for value in values:
        target = value.get("target_relation")
        if (
            not isinstance(value, dict)
            or set(value) != {
                "problem_id", "question", "focal_object_ids",
                "constraint_object_ids", "target_relation", "question_type",
                "coordinate", "falsifier", "required_observation",
                "evidence_span_ids",
            }
            or not str(value["problem_id"]).strip()
            or value["problem_id"] in problem_ids
            or not str(value["question"]).strip()
            or not isinstance(target, dict)
            or set(target) != {"source_object_id", "target_object_id"}
            or target["source_object_id"] not in object_ids
            or target["target_object_id"] not in object_ids
            or target["source_object_id"] == target["target_object_id"]
            or value["question_type"] not in QUESTION_TYPES
            or value["coordinate"] not in COORDINATES
            or not str(value["falsifier"]).strip()
            or not str(value["required_observation"]).strip()
        ):
            raise ValueError("structural_world_receipt_problem_invalid")
        _validate_id_list(
            value["focal_object_ids"], object_ids, allow_empty=False
        )
        _validate_id_list(
            value["constraint_object_ids"], object_ids, allow_empty=True
        )
        _validate_id_list(
            value["evidence_span_ids"], span_ids, allow_empty=False
        )
        problem_ids.add(value["problem_id"])
    return problem_ids


def _score_receipt(*, arm_id, item, truth, receipt, call):
    problems = receipt["problem_candidates"]
    expected_targets = {
        (value["source_object_id"], value["target_object_id"])
        for value in truth["unresolved_targets"]
    }
    proposed_targets = [
        (
            value["target_relation"]["source_object_id"],
            value["target_relation"]["target_object_id"],
        )
        for value in problems
    ]
    matching = [value for value in proposed_targets if value in expected_targets]
    precision = len(matching) / len(proposed_targets)
    recall = (
        len(set(matching)) / len(expected_targets)
        if expected_targets else 1.0
    )
    target_f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0.0
    )
    focal_ids = {
        object_id for value in problems
        for object_id in value["focal_object_ids"]
    }
    constraint_ids = {
        *receipt["identified_constraint_object_ids"],
        *(object_id for value in problems
          for object_id in value["constraint_object_ids"]),
    }
    relation_values = {
        (
            value["source_object_id"], value["relation_type"],
            value["target_object_id"],
        )
        for value in receipt["relation_graph"]
    }
    expected_relations = {
        (
            value["source_object_id"], value["relation_type"],
            value["target_object_id"],
        )
        for value in truth["critical_relations"]
    }
    primary_hits = len(focal_ids & set(truth["primary_object_ids"]))
    constraint_hits = len(
        constraint_ids & set(truth["hidden_constraint_object_ids"])
    )
    relation_hits = len(relation_values & expected_relations)
    invariant_hits = len(
        set(receipt["invariant_object_ids"])
        & set(truth["invariant_object_ids"])
    )
    counterevidence_hits = len(
        set(receipt["counterevidence_span_ids"])
        & set(truth["counterevidence_span_ids"])
    )
    signatures = {
        (
            value["target_relation"]["source_object_id"],
            value["target_relation"]["target_object_id"],
            value["question_type"],
            value["coordinate"],
        )
        for value in problems
    }
    valid_coordinates = {
        value["coordinate"] for value in problems
        if (
            value["target_relation"]["source_object_id"],
            value["target_relation"]["target_object_id"],
        ) in expected_targets
    }
    usage = call["invocation_receipt"].get("token_usage") or {}
    input_tokens = int(
        usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    )
    output_tokens = int(
        usage.get("completion_tokens") or usage.get("output_tokens") or 0
    )
    valid_cbit_events = (
        primary_hits + constraint_hits + relation_hits + len(set(matching))
        + invariant_hits + counterevidence_hits
    )
    return {
        "case_id": item["case_id"],
        "arm_id": arm_id,
        "problem_target_precision": round(precision, 6),
        "problem_target_recall": round(recall, 6),
        "problem_target_f1": round(target_f1, 6),
        "primary_object_recall": _recall(
            primary_hits, truth["primary_object_ids"]
        ),
        "hidden_constraint_recall": _recall(
            constraint_hits, truth["hidden_constraint_object_ids"]
        ),
        "critical_relation_recall": _recall(
            relation_hits, truth["critical_relations"]
        ),
        "invariant_recall": _recall(
            invariant_hits, truth["invariant_object_ids"]
        ),
        "counterevidence_recall": _recall(
            counterevidence_hits, truth["counterevidence_span_ids"]
        ),
        "nonredundant_problem_rate": round(
            len(signatures) / len(problems), 6
        ),
        "cross_coordinate_valid_target": len(valid_coordinates) >= 2,
        "valid_cbit_events": valid_cbit_events,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def _aggregate_arm(rows, *, expected_count, calls):
    names = (
        "problem_target_precision", "problem_target_recall",
        "problem_target_f1", "primary_object_recall",
        "hidden_constraint_recall", "critical_relation_recall",
        "invariant_recall", "counterevidence_recall",
        "nonredundant_problem_rate",
    )
    total_tokens = sum(_call_token_count(call) for call in calls)
    valid_cbit_events = sum(row["valid_cbit_events"] for row in rows)
    result = {
        "receipt_count": len(rows),
        "receipt_coverage": round(len(rows) / expected_count, 6),
        **{
            f"mean_{name}": round(
                mean(row[name] for row in rows), 6
            ) if rows else 0.0
            for name in names
        },
        "cross_coordinate_valid_target_rate": round(
            mean(
                1.0 if row["cross_coordinate_valid_target"] else 0.0
                for row in rows
            ), 6
        ) if rows else 0.0,
        "valid_cbit_events": valid_cbit_events,
        "total_tokens": total_tokens,
        "tokens_per_valid_cbit_event": round(
            total_tokens / valid_cbit_events, 6
        ) if valid_cbit_events else float(total_tokens or 0),
    }
    return result


def _recall(hit_count, expected):
    return round(hit_count / len(expected), 6) if expected else 1.0


def _call_token_count(call):
    usage = call["invocation_receipt"].get("token_usage") or {}
    return int(
        usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    ) + int(
        usage.get("completion_tokens") or usage.get("output_tokens") or 0
    )
