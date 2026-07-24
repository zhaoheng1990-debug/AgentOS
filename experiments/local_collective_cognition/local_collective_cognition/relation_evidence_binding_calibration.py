"""Two-stage relation-evidence binding calibration v0.62."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .frontier_experiment import TASK_KIND
from .portfolio_critic_fresh_holdout import (
    validate_portfolio_critic_fresh_holdout_v0_61_1,
)
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "relation_evidence_binding_calibration_v0_62"
BINDING_ROLES = ("EVIDENCE_BINDER", "BINDING_SKEPTIC")
STATE_ROLES = ("STATE_ASSESSOR", "STATE_SKEPTIC")
REFERENCE_STATES = (
    "SUPPORTED_EFFECT",
    "SUPPORTED_NULL",
    "UNRESOLVED",
)
BINDING_FIELDS = (
    "source_object_binding",
    "target_outcome_binding",
    "evidence_design",
    "binding_state",
    "evidence_span_ids",
)


def build_binding_preregistration(
    *,
    corpus,
    failed_reference,
    source_closure,
    runtime_version=RUNTIME_VERSION,
    coarse_identity_consensus=False,
    provider_binding_state_authority=True,
):
    validate_portfolio_critic_fresh_holdout_v0_61_1(corpus)
    for value in (failed_reference, source_closure):
        _validate_hash(value)
    if (
        failed_reference.get("reference_complete") is not False
        or len(failed_reference.get("reference_mismatches", [])) != 2
        or source_closure.get("decision")
        != "REJECT_FRESH_PORTFOLIO_REFERENCE_GATE"
        or source_closure.get(
            "object_evidence_binding_calibration_required"
        ) is not True
    ):
        raise ValueError("binding_calibration_source_invalid")
    binding_receipts = corpus["case_count"] * len(BINDING_ROLES)
    state_receipts = corpus["case_count"] * len(STATE_ROLES)
    commitment = {
        "preregistration_version": runtime_version,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_failed_reference_hash": failed_reference["artifact_hash"],
        "source_closure_hash": source_closure["artifact_hash"],
        "binding_roles": list(BINDING_ROLES),
        "state_roles": list(STATE_ROLES),
        "required_binding_receipt_count": binding_receipts,
        "required_binding_relation_consensus_count": (
            corpus["case_count"] * 5
        ),
        "maximum_binding_conflict_count": 0,
        "required_state_receipt_count": state_receipts,
        "maximum_state_contract_failure_count": 0,
        "maximum_state_reference_mismatch_count": 0,
        "maximum_state_cross_role_disagreement_count": 0,
        "required_recovered_coordinate": {
            "case_id": "PC-TRAFFIC",
            "relation_id": "REL-O3-O1",
            "required_state": "SUPPORTED_EFFECT",
        },
        "maximum_provider_calls": binding_receipts + state_receipts,
        "hard_token_ceiling": 200000,
        "binding_roles_forbidden_from_truth_state": True,
        "binding_consensus_mode": (
            "COARSE_BOUND_IDENTITY"
            if coarse_identity_consensus else "EXACT_BINDING_SUBTYPE"
        ),
        "provider_binding_state_authority": (
            provider_binding_state_authority
        ),
        "state_roles_require_binding_consensus": True,
        "formal_scope": "REVEALED_MECHANISM_CALIBRATION_ONLY",
        "fresh_generalization_claim_allowed": False,
        "core_integration_authorized": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def binding_schema(*, item, role, refs):
    relation_ids = _relation_ids(item)
    object_ids = [
        value["object_id"] for value in item["object_registry"]
    ]
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    relation = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "relation_id",
            "source_object_id",
            "target_object_id",
            "evidence_span_ids",
            "source_object_binding",
            "target_outcome_binding",
            "evidence_design",
            "binding_state",
            "rationale",
        ],
        "properties": {
            "relation_id": {"type": "string", "enum": relation_ids},
            "source_object_id": {
                "type": "string", "enum": object_ids,
            },
            "target_object_id": {
                "type": "string", "enum": [item["focal_object_id"]],
            },
            "evidence_span_ids": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {"type": "string", "enum": span_ids},
            },
            "source_object_binding": {
                "type": "string",
                "enum": ["EXACT_EXPLICIT", "COREFERENCE", "UNBOUND"],
            },
            "target_outcome_binding": {
                "type": "string",
                "enum": ["EXACT_EXPLICIT", "COREFERENCE", "UNBOUND"],
            },
            "evidence_design": {
                "type": "string",
                "enum": [
                    "INTERVENTION_OR_ROLLBACK",
                    "MATCHED_NULL_COMPARISON",
                    "UNTESTED_DIFFERENCE",
                    "OTHER",
                ],
            },
            "binding_state": {
                "type": "string", "enum": ["BOUND", "UNBOUND"],
            },
            "rationale": {"type": "string"},
        },
    }
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "binding_role": {"type": "string", "enum": [role]},
        "source_item_hash": {
            "type": "string", "enum": [hash_payload(item)],
        },
        "all_relations_assessed": {"type": "boolean", "enum": [True]},
        "relation_bindings": {
            "type": "array",
            "minItems": len(relation_ids),
            "maxItems": len(relation_ids),
            "items": relation,
        },
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


def validate_binding_receipt(
    *,
    receipt,
    item,
    role,
    refs,
    provider_binding_state_authority=True,
):
    failures = []
    if receipt.get("case_id") != item["case_id"]:
        failures.append("BINDING_CASE_MISMATCH")
    if receipt.get("binding_role") != role:
        failures.append("BINDING_ROLE_MISMATCH")
    if receipt.get("source_item_hash") != hash_payload(item):
        failures.append("BINDING_ITEM_HASH_MISMATCH")
    if receipt.get("all_relations_assessed") is not True:
        failures.append("BINDING_COVERAGE_NOT_CONFIRMED")
    if receipt.get("evidence_refs") != list(refs):
        failures.append("BINDING_EVIDENCE_SCOPE_MISMATCH")
    if "relation_truth_state" in str(receipt):
        failures.append("BINDING_TRUTH_STATE_FORBIDDEN")
    values = receipt.get("relation_bindings")
    if not isinstance(values, list):
        return [*failures, "BINDINGS_NOT_ARRAY"]
    expected = set(_relation_ids(item))
    observed = {
        value.get("relation_id")
        for value in values if isinstance(value, dict)
    }
    if len(values) != len(expected) or observed != expected:
        failures.append("BINDING_RELATION_COVERAGE_INVALID")
    allowed_spans = {
        value["span_id"] for value in item["evidence_spans"]
    }
    for value in values:
        if not isinstance(value, dict):
            failures.append("BINDING_RELATION_NOT_OBJECT")
            continue
        relation_id = value.get("relation_id", "")
        expected_source = (
            relation_id.split("-")[1]
            if relation_id.startswith("REL-") else None
        )
        if value.get("source_object_id") != expected_source:
            failures.append("BINDING_SOURCE_RELATION_MISMATCH")
        if value.get("target_object_id") != item["focal_object_id"]:
            failures.append("BINDING_TARGET_RELATION_MISMATCH")
        spans = value.get("evidence_span_ids")
        if (
            not isinstance(spans, list)
            or not spans
            or len(spans) != len(set(spans))
            or not set(spans).issubset(allowed_spans)
        ):
            failures.append("BINDING_SPAN_INVALID")
        source_bound = (
            value.get("source_object_binding") != "UNBOUND"
        )
        target_bound = (
            value.get("target_outcome_binding") != "UNBOUND"
        )
        expected_state = "BOUND" if source_bound and target_bound else "UNBOUND"
        if (
            provider_binding_state_authority
            and value.get("binding_state") != expected_state
        ):
            failures.append("BINDING_STATE_INCONSISTENT")
    return failures


def run_binding_panel(*, corpus, preregistration, adapter):
    validate_portfolio_critic_fresh_holdout_v0_61_1(corpus)
    _validate_hash(preregistration)
    refs = tuple(corpus["evidence_refs"])
    calls = []
    receipts = {}
    failures = []
    for role in BINDING_ROLES:
        for item in corpus["public_surface"]["items"]:
            task = _binding_task(
                item=item,
                role=role,
                refs=refs,
                adapter=adapter,
                runtime_version=preregistration[
                    "preregistration_version"
                ],
                provider_binding_state_authority=preregistration[
                    "provider_binding_state_authority"
                ],
            )
            envelope = ProviderTaskRouter([adapter]).route(task)
            call = _call(role=role, item=item, task=task, envelope=envelope)
            calls.append(call)
            if envelope.status != "COMPLETED":
                failures.append({**call, "failure": envelope.error})
                continue
            receipt = envelope.normalized_result
            contract_failures = validate_binding_receipt(
                receipt=receipt,
                item=item,
                role=role,
                refs=refs,
                provider_binding_state_authority=preregistration[
                    "provider_binding_state_authority"
                ],
            )
            if contract_failures:
                failures.append({
                    **call,
                    "contract_failures": contract_failures,
                })
                continue
            receipts[f"{role}:{item['case_id']}"] = receipt
    consensus_receipts = {}
    conflicts = []
    subtype_divergences = []
    consensus_count = 0
    for item in corpus["public_surface"]["items"]:
        case_id = item["case_id"]
        left = receipts.get(f"{BINDING_ROLES[0]}:{case_id}")
        right = receipts.get(f"{BINDING_ROLES[1]}:{case_id}")
        if left is None or right is None:
            continue
        left_map = {
            value["relation_id"]: value
            for value in left["relation_bindings"]
        }
        right_map = {
            value["relation_id"]: value
            for value in right["relation_bindings"]
        }
        bindings = []
        for relation_id in _relation_ids(item):
            first = left_map[relation_id]
            second = right_map[relation_id]
            coarse = (
                preregistration["binding_consensus_mode"]
                == "COARSE_BOUND_IDENTITY"
            )
            if coarse:
                agreed = (
                    (
                        first["source_object_binding"] != "UNBOUND"
                    )
                    == (
                        second["source_object_binding"] != "UNBOUND"
                    )
                    and (
                        first["target_outcome_binding"] != "UNBOUND"
                    )
                    == (
                        second["target_outcome_binding"] != "UNBOUND"
                    )
                    and first["evidence_design"]
                    == second["evidence_design"]
                    and first["evidence_span_ids"]
                    == second["evidence_span_ids"]
                )
                if agreed and (
                    first["source_object_binding"]
                    != second["source_object_binding"]
                    or first["target_outcome_binding"]
                    != second["target_outcome_binding"]
                    or first["binding_state"]
                    != second["binding_state"]
                ):
                    subtype_divergences.append({
                        "case_id": case_id,
                        "relation_id": relation_id,
                        "left": {
                            field: first[field]
                            for field in (
                                "source_object_binding",
                                "target_outcome_binding",
                                "binding_state",
                            )
                        },
                        "right": {
                            field: second[field]
                            for field in (
                                "source_object_binding",
                                "target_outcome_binding",
                                "binding_state",
                            )
                        },
                    })
            else:
                agreed = all(
                    first[field] == second[field]
                    for field in BINDING_FIELDS
                )
            if not agreed:
                conflicts.append({
                    "case_id": case_id,
                    "relation_id": relation_id,
                    "left": {
                        field: first[field] for field in BINDING_FIELDS
                    },
                    "right": {
                        field: second[field] for field in BINDING_FIELDS
                    },
                })
                continue
            consensus_count += 1
            source_binding = _coarse_binding(
                first["source_object_binding"],
                second["source_object_binding"],
            )
            target_binding = _coarse_binding(
                first["target_outcome_binding"],
                second["target_outcome_binding"],
            )
            bindings.append({
                "relation_id": first["relation_id"],
                "source_object_id": first["source_object_id"],
                "target_object_id": first["target_object_id"],
                "source_object_binding": source_binding,
                "target_outcome_binding": target_binding,
                "evidence_design": first["evidence_design"],
                "binding_state": (
                    "BOUND"
                    if (
                        source_binding != "UNBOUND"
                        and target_binding != "UNBOUND"
                    )
                    else "UNBOUND"
                ),
                "evidence_span_ids": first["evidence_span_ids"],
            })
        commitment = {
            "consensus_version": preregistration[
                "preregistration_version"
            ],
            "case_id": case_id,
            "source_item_hash": hash_payload(item),
            "source_role_receipt_hashes": {
                BINDING_ROLES[0]: hash_payload(left),
                BINDING_ROLES[1]: hash_payload(right),
            },
            "relation_bindings": bindings,
            "relation_consensus_count": len(bindings),
            "binding_ready": len(bindings) == len(_relation_ids(item)),
            "truth_state_authority": False,
        }
        consensus_receipts[case_id] = {
            **commitment,
            "artifact_hash": hash_payload(commitment),
        }
    ready = (
        len(receipts) == preregistration["required_binding_receipt_count"]
        and consensus_count
        == preregistration["required_binding_relation_consensus_count"]
        and len(conflicts)
        <= preregistration["maximum_binding_conflict_count"]
        and not failures
    )
    commitment = {
        "runtime_version": preregistration["preregistration_version"],
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "raw_receipts": receipts,
        "contract_failures": failures,
        "consensus_receipts": consensus_receipts,
        "binding_relation_consensus_count": consensus_count,
        "binding_conflicts": conflicts,
        "binding_subtype_divergences": subtype_divergences,
        "binding_ready_for_state_assessment": ready,
        "private_truth_exposed": False,
        "truth_state_assessed": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def state_schema(*, item, role, binding_receipt, refs):
    relation_ids = _relation_ids(item)
    span_ids = {
        value["span_id"] for value in item["evidence_spans"]
    }
    assessment = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "relation_id",
            "relation_truth_state",
            "evidence_span_ids",
            "rationale",
        ],
        "properties": {
            "relation_id": {"type": "string", "enum": relation_ids},
            "relation_truth_state": {
                "type": "string", "enum": list(REFERENCE_STATES),
            },
            "evidence_span_ids": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {"type": "string", "enum": sorted(span_ids)},
            },
            "rationale": {"type": "string"},
        },
    }
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "state_role": {"type": "string", "enum": [role]},
        "source_binding_consensus_hash": {
            "type": "string",
            "enum": [binding_receipt["artifact_hash"]],
        },
        "all_relations_assessed": {"type": "boolean", "enum": [True]},
        "relation_assessments": {
            "type": "array",
            "minItems": len(relation_ids),
            "maxItems": len(relation_ids),
            "items": assessment,
        },
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


def validate_state_receipt(
    *, receipt, item, role, binding_receipt, refs
):
    failures = []
    if receipt.get("case_id") != item["case_id"]:
        failures.append("STATE_CASE_MISMATCH")
    if receipt.get("state_role") != role:
        failures.append("STATE_ROLE_MISMATCH")
    if (
        receipt.get("source_binding_consensus_hash")
        != binding_receipt["artifact_hash"]
    ):
        failures.append("STATE_BINDING_HASH_MISMATCH")
    if receipt.get("all_relations_assessed") is not True:
        failures.append("STATE_COVERAGE_NOT_CONFIRMED")
    if receipt.get("evidence_refs") != list(refs):
        failures.append("STATE_EVIDENCE_SCOPE_MISMATCH")
    values = receipt.get("relation_assessments")
    if not isinstance(values, list):
        return [*failures, "STATE_ASSESSMENTS_NOT_ARRAY"]
    expected = set(_relation_ids(item))
    observed = {
        value.get("relation_id")
        for value in values if isinstance(value, dict)
    }
    if len(values) != len(expected) or observed != expected:
        failures.append("STATE_RELATION_COVERAGE_INVALID")
    binding_map = {
        value["relation_id"]: value
        for value in binding_receipt["relation_bindings"]
    }
    for value in values:
        if not isinstance(value, dict):
            failures.append("STATE_ASSESSMENT_NOT_OBJECT")
            continue
        relation_id = value.get("relation_id")
        if relation_id not in binding_map:
            failures.append("STATE_RELATION_NOT_BOUND")
            continue
        spans = value.get("evidence_span_ids")
        allowed = set(binding_map[relation_id]["evidence_span_ids"])
        if (
            not isinstance(spans, list)
            or not spans
            or not set(spans).issubset(allowed)
        ):
            failures.append("STATE_SPAN_NOT_BOUND")
    return failures


def run_state_panel(*, corpus, preregistration, binding_run, adapter):
    validate_portfolio_critic_fresh_holdout_v0_61_1(corpus)
    _validate_hash(preregistration)
    _validate_hash(binding_run)
    if binding_run.get("binding_ready_for_state_assessment") is not True:
        raise ValueError("binding_panel_not_ready")
    refs = tuple(corpus["evidence_refs"])
    calls = []
    receipts = {}
    failures = []
    for role in STATE_ROLES:
        for item in corpus["public_surface"]["items"]:
            binding = binding_run["consensus_receipts"][item["case_id"]]
            task = _state_task(
                item=item,
                role=role,
                binding_receipt=binding,
                refs=refs,
                adapter=adapter,
                runtime_version=preregistration[
                    "preregistration_version"
                ],
            )
            envelope = ProviderTaskRouter([adapter]).route(task)
            call = _call(role=role, item=item, task=task, envelope=envelope)
            calls.append(call)
            if envelope.status != "COMPLETED":
                failures.append({**call, "failure": envelope.error})
                continue
            receipt = envelope.normalized_result
            contract_failures = validate_state_receipt(
                receipt=receipt,
                item=item,
                role=role,
                binding_receipt=binding,
                refs=refs,
            )
            if contract_failures:
                failures.append({
                    **call,
                    "contract_failures": contract_failures,
                })
                continue
            receipts[f"{role}:{item['case_id']}"] = receipt
    commitment = {
        "runtime_version": preregistration["preregistration_version"],
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_binding_run_hash": binding_run["run_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "raw_receipts": receipts,
        "contract_failures": failures,
        "private_truth_exposed": False,
        "binding_consensus_required": True,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_state_panel(
    *, corpus, preregistration, binding_run, state_run
):
    validate_portfolio_critic_fresh_holdout_v0_61_1(corpus)
    for value in (preregistration, binding_run, state_run):
        _validate_hash(value)
    expected = _expected_states(corpus)
    role_states = {}
    mismatches = []
    for key, receipt in state_run["raw_receipts"].items():
        role, case_id = key.split(":", 1)
        states = {
            value["relation_id"]: value["relation_truth_state"]
            for value in receipt["relation_assessments"]
        }
        role_states[key] = states
        for relation_id, expected_state in expected[case_id].items():
            observed = states.get(relation_id)
            if observed != expected_state:
                mismatches.append({
                    "role": role,
                    "case_id": case_id,
                    "relation_id": relation_id,
                    "expected_state": expected_state,
                    "observed_state": observed,
                })
    disagreements = []
    for case_id, expected_relations in expected.items():
        left = role_states.get(f"{STATE_ROLES[0]}:{case_id}", {})
        right = role_states.get(f"{STATE_ROLES[1]}:{case_id}", {})
        for relation_id in expected_relations:
            if left.get(relation_id) != right.get(relation_id):
                disagreements.append({
                    "case_id": case_id,
                    "relation_id": relation_id,
                    "assessor_state": left.get(relation_id),
                    "skeptic_state": right.get(relation_id),
                })
    coordinate = preregistration["required_recovered_coordinate"]
    recovered = all(
        role_states.get(
            f"{role}:{coordinate['case_id']}", {}
        ).get(coordinate["relation_id"]) == coordinate["required_state"]
        for role in STATE_ROLES
    )
    calls = [
        *binding_run["task_calls"],
        *state_run["task_calls"],
    ]
    tokens = sum(
        value["token_usage"]["total_tokens"] for value in calls
    )
    conditions = {
        "required_binding_receipt_count": (
            len(binding_run["raw_receipts"])
            == preregistration["required_binding_receipt_count"]
        ),
        "required_binding_relation_consensus_count": (
            binding_run["binding_relation_consensus_count"]
            == preregistration[
                "required_binding_relation_consensus_count"
            ]
        ),
        "maximum_binding_conflict_count": (
            len(binding_run["binding_conflicts"])
            <= preregistration["maximum_binding_conflict_count"]
        ),
        "required_state_receipt_count": (
            len(state_run["raw_receipts"])
            == preregistration["required_state_receipt_count"]
        ),
        "maximum_state_contract_failure_count": (
            len(state_run["contract_failures"])
            <= preregistration["maximum_state_contract_failure_count"]
        ),
        "maximum_state_reference_mismatch_count": (
            len(mismatches)
            <= preregistration["maximum_state_reference_mismatch_count"]
        ),
        "maximum_state_cross_role_disagreement_count": (
            len(disagreements)
            <= preregistration[
                "maximum_state_cross_role_disagreement_count"
            ]
        ),
        "required_recovered_coordinate": recovered,
        "maximum_provider_calls": (
            len(calls) <= preregistration["maximum_provider_calls"]
        ),
        "hard_token_ceiling": (
            tokens <= preregistration["hard_token_ceiling"]
        ),
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": preregistration["preregistration_version"],
        "source_binding_run_hash": binding_run["run_hash"],
        "source_state_run_hash": state_run["run_hash"],
        "binding_receipt_count": len(binding_run["raw_receipts"]),
        "binding_relation_consensus_count": binding_run[
            "binding_relation_consensus_count"
        ],
        "binding_conflict_count": len(binding_run["binding_conflicts"]),
        "state_receipt_count": len(state_run["raw_receipts"]),
        "state_reference_mismatches": mismatches,
        "state_cross_role_disagreements": disagreements,
        "required_coordinate_recovered": recovered,
        "provider_call_count": len(calls),
        "physical_total_tokens": tokens,
        "conditions": conditions,
        "decision": (
            "PASS_RELATION_EVIDENCE_BINDING_CALIBRATION"
            if passed else "REJECT_RELATION_EVIDENCE_BINDING_CALIBRATION"
        ),
        "candidate_state": (
            "BINDING_ARCHITECTURE_READY_FOR_FRESH_HOLDOUT"
            if passed else "BINDING_ARCHITECTURE_REJECTED_STOP"
        ),
        "fresh_generalization_claim": False,
        "core_integration_authorized": False,
        "promotion_allowed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _binding_task(
    *,
    item,
    role,
    refs,
    adapter,
    runtime_version=RUNTIME_VERSION,
    provider_binding_state_authority=True,
):
    role_prompt = {
        "EVIDENCE_BINDER": (
            "Bind each focal relation to the evidence that explicitly names "
            "or corefers to its source object and focal outcome."
        ),
        "BINDING_SKEPTIC": (
            "Independently challenge object and outcome identity before "
            "binding each focal relation to evidence."
        ),
    }[role]
    return ProviderCognitiveTask(
        task_id=f"{runtime_version}-{role}-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            f"{role_prompt} Assess all five non-focal relations exactly "
            "once. This stage must not classify EFFECT, NULL, or UNRESOLVED. "
            "INTERVENTION_OR_ROLLBACK means the source object was changed or "
            "controlled and an outcome response was measured; "
            "MATCHED_NULL_COMPARISON means a matched test found no outcome "
            "difference; UNTESTED_DIFFERENCE means the source differs but "
            "has not been causally or comparatively tested."
            + (
                " Runtime, not the Provider, derives binding_state from "
                "whether source_object_binding and target_outcome_binding "
                "are UNBOUND; the binding_state output is compatibility "
                "telemetry only."
                if not provider_binding_state_authority else ""
            )
        ),
        inputs={
            "binding_role": role,
            "public_item": item,
            "private_truth_available": False,
            "truth_state_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=binding_schema(
            item=item, role=role, refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _state_task(
    *,
    item,
    role,
    binding_receipt,
    refs,
    adapter,
    runtime_version=RUNTIME_VERSION,
):
    role_prompt = {
        "STATE_ASSESSOR": (
            "Classify the truth state of each bound focal relation."
        ),
        "STATE_SKEPTIC": (
            "Independently challenge overclaim and underclaim, then classify "
            "each bound focal relation."
        ),
    }[role]
    return ProviderCognitiveTask(
        task_id=f"{runtime_version}-{role}-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            f"{role_prompt} Use SUPPORTED_EFFECT only when a BOUND "
            "intervention or rollback changed the focal outcome, "
            "SUPPORTED_NULL only when a BOUND matched comparison found no "
            "focal-outcome difference, and UNRESOLVED for untested "
            "differences, OTHER designs, or UNBOUND relations. Use only "
            "the evidence spans admitted by the binding consensus."
        ),
        inputs={
            "state_role": role,
            "public_item": item,
            "binding_consensus_receipt": binding_receipt,
            "private_truth_available": False,
        },
        allowed_evidence=list(refs),
        expected_schema=state_schema(
            item=item,
            role=role,
            binding_receipt=binding_receipt,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _call(*, role, item, task, envelope):
    return {
        "role": role,
        "case_id": item["case_id"],
        "status": envelope.status,
        "token_usage": dict(envelope.invocation_receipt.token_usage),
        "task_id": task.task_id,
    }


def _relation_ids(item):
    return [
        f"REL-{value['object_id']}-{item['focal_object_id']}"
        for value in item["object_registry"]
        if value["object_id"] != item["focal_object_id"]
    ]


def _expected_states(corpus):
    result = {}
    for item in corpus["public_surface"]["items"]:
        case_id = item["case_id"]
        binding = corpus["private_provenance"]["bindings"][case_id]
        supported = {
            value["source_object_id"]
            for value in binding["supported_targets"]
        }
        nulls = {
            value["source_object_id"]
            for value in binding["informative_null_targets"]
        }
        result[case_id] = {}
        for relation_id in _relation_ids(item):
            source = relation_id.split("-")[1]
            result[case_id][relation_id] = (
                "SUPPORTED_EFFECT" if source in supported
                else "SUPPORTED_NULL" if source in nulls
                else "UNRESOLVED"
            )
    return result


def _coarse_binding(left, right):
    if left == "UNBOUND" or right == "UNBOUND":
        return "UNBOUND"
    if left == "COREFERENCE" or right == "COREFERENCE":
        return "COREFERENCE"
    return "EXACT_EXPLICIT"


def _validate_hash(value):
    field = "run_hash" if "run_hash" in value else "artifact_hash"
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError("relation_evidence_binding_source_hash_invalid")
