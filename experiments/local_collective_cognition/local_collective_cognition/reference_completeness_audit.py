"""Provider-backed exhaustive reference audit for synthetic holdouts."""

from __future__ import annotations

from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .frontier_experiment import TASK_KIND
from .lineage_revision_experiment import _call, _provider_failure
from .provider_telemetry import hash_payload


AUDIT_VERSION = "reference_completeness_audit_v0_51"
AUDIT_ROLES = ("REFERENCE_EXTRACTOR", "REFERENCE_SKEPTIC")
REFERENCE_STATES = (
    "SUPPORTED_EFFECT",
    "SUPPORTED_NULL",
    "UNRESOLVED",
)


def reference_audit_schema(*, item, refs):
    object_ids = [
        value["object_id"] for value in item["object_registry"]
        if value["object_id"] != item["focal_object_id"]
    ]
    relation_ids = [
        f"REL-{object_id}-{item['focal_object_id']}"
        for object_id in object_ids
    ]
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "all_focal_relations_assessed": {
            "type": "boolean", "enum": [True],
        },
        "relation_assessments": {
            "type": "array",
            "minItems": len(relation_ids),
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "relation_id",
                    "relation_truth_state",
                    "evidence_span_ids",
                    "rationale",
                ],
                "properties": {
                    "relation_id": {
                        "type": "string", "enum": relation_ids,
                    },
                    "relation_truth_state": {
                        "type": "string",
                        "enum": list(REFERENCE_STATES),
                    },
                    "evidence_span_ids": {
                        "type": "array",
                        "items": {
                            "type": "string", "enum": span_ids,
                        },
                    },
                    "rationale": {"type": "string"},
                },
            },
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


def validate_reference_audit_receipt(*, receipt, item, refs):
    if not isinstance(receipt, dict):
        return ["REFERENCE_AUDIT_NOT_OBJECT"]
    failures = []
    if receipt.get("case_id") != item["case_id"]:
        failures.append("REFERENCE_AUDIT_CASE_MISMATCH")
    if receipt.get("all_focal_relations_assessed") is not True:
        failures.append("REFERENCE_AUDIT_COVERAGE_NOT_CONFIRMED")
    if receipt.get("evidence_refs") != list(refs):
        failures.append("REFERENCE_AUDIT_EVIDENCE_SCOPE_MISMATCH")
    expected_relations = {
        f"REL-{value['object_id']}-{item['focal_object_id']}"
        for value in item["object_registry"]
        if value["object_id"] != item["focal_object_id"]
    }
    values = receipt.get("relation_assessments")
    if not isinstance(values, list):
        return [*failures, "REFERENCE_AUDIT_ASSESSMENTS_NOT_ARRAY"]
    relation_ids = [
        value.get("relation_id")
        for value in values if isinstance(value, dict)
    ]
    if (
        len(values) != len(expected_relations)
        or len(set(relation_ids)) != len(relation_ids)
        or set(relation_ids) != expected_relations
    ):
        failures.append("REFERENCE_AUDIT_RELATION_COVERAGE_INVALID")
    allowed_spans = {
        value["span_id"] for value in item["evidence_spans"]
    }
    for value in values:
        if not isinstance(value, dict):
            failures.append("REFERENCE_AUDIT_ASSESSMENT_NOT_OBJECT")
            continue
        if value.get("relation_truth_state") not in REFERENCE_STATES:
            failures.append("REFERENCE_AUDIT_STATE_INVALID")
        spans = value.get("evidence_span_ids")
        state = value.get("relation_truth_state")
        if (
            not isinstance(spans, list)
            or len(set(spans)) != len(spans)
            or not set(spans).issubset(allowed_spans)
            or state != "UNRESOLVED" and not spans
        ):
            failures.append("REFERENCE_AUDIT_SPAN_BINDING_INVALID")
        if not isinstance(value.get("rationale"), str):
            failures.append("REFERENCE_AUDIT_RATIONALE_INVALID")
    return failures


def run_reference_completeness_audit(*, corpus, adapter):
    refs = tuple(corpus["evidence_refs"])
    matrix = [
        (role, item)
        for role in AUDIT_ROLES
        for item in corpus["public_surface"]["items"]
    ]
    matrix.sort(key=lambda value: hash_payload([
        AUDIT_VERSION, value[0], value[1]["case_id"]
    ]))
    calls, receipts, failures, valid_keys = [], {}, [], []
    for role, item in matrix:
        task = _audit_task(
            item=item, role=role, refs=refs, adapter=adapter
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=role,
            arm_id="REFERENCE_AUDIT",
            case_id=item["case_id"],
            stage=role,
            route_id=role,
            task=task,
            envelope=envelope,
        )
        calls.append(call)
        key = f"{role}:{item['case_id']}"
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
            continue
        receipt = envelope.normalized_result
        receipt_failures = validate_reference_audit_receipt(
            receipt=receipt, item=item, refs=refs
        )
        receipts[key] = receipt
        if receipt_failures:
            failures.append({
                "role": role,
                "case_id": item["case_id"],
                "stage": "REFERENCE_AUDIT_CONTRACT",
                "failures": receipt_failures,
                "raw_receipt_hash": hash_payload(receipt),
            })
            continue
        valid_keys.append(key)
    expected = _expected_reference(corpus)
    mismatches = []
    role_states = {}
    for key in valid_keys:
        role, case_id = key.split(":", 1)
        states = {
            value["relation_id"]: value["relation_truth_state"]
            for value in receipts[key]["relation_assessments"]
        }
        role_states[key] = states
        for relation_id, state in expected[case_id].items():
            if states.get(relation_id) != state:
                mismatches.append({
                    "role": role,
                    "case_id": case_id,
                    "relation_id": relation_id,
                    "expected_state": state,
                    "observed_state": states.get(relation_id),
                })
    disagreements = []
    for item in corpus["public_surface"]["items"]:
        case_id = item["case_id"]
        left = role_states.get(f"{AUDIT_ROLES[0]}:{case_id}", {})
        right = role_states.get(f"{AUDIT_ROLES[1]}:{case_id}", {})
        for relation_id in sorted(expected[case_id]):
            if left.get(relation_id) != right.get(relation_id):
                disagreements.append({
                    "case_id": case_id,
                    "relation_id": relation_id,
                    "extractor_state": left.get(relation_id),
                    "skeptic_state": right.get(relation_id),
                })
    required = corpus["case_count"] * len(AUDIT_ROLES)
    complete = bool(
        len(valid_keys) == required
        and not failures
        and not mismatches
        and not disagreements
    )
    distribution = Counter(
        state
        for states in role_states.values()
        for state in states.values()
    )
    commitment = {
        "audit_version": AUDIT_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "audit_roles": list(AUDIT_ROLES),
        "task_calls": calls,
        "raw_receipts": receipts,
        "valid_keys": valid_keys,
        "contract_failures": failures,
        "reference_mismatches": mismatches,
        "cross_role_disagreements": disagreements,
        "state_distribution": dict(distribution),
        "required_receipt_count": required,
        "valid_receipt_count": len(valid_keys),
        "reference_complete": complete,
        "private_reference_available_to_provider": False,
        "private_reference_compared_after_provider_calls": True,
        "reference_authority": (
            "INTERNAL_PROVIDER_AUDITED_SYNTHETIC_ONLY"
        ),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_reference_completeness_audit(*, audit, corpus):
    commitment = {
        key: value for key, value in audit.items()
        if key != "artifact_hash"
    }
    if (
        audit.get("artifact_hash") != hash_payload(commitment)
        or audit.get("source_corpus_hash") != corpus["artifact_hash"]
    ):
        raise ValueError("reference_completeness_audit_invalid")


def _expected_reference(corpus):
    expected = {}
    for item in corpus["public_surface"]["items"]:
        case_id = item["case_id"]
        truth = corpus["private_provenance"]["bindings"][case_id]
        supported = {
            (
                value["source_object_id"],
                value["target_object_id"],
            )
            for value in truth["supported_targets"]
        }
        nulls = {
            (
                value["source_object_id"],
                value["target_object_id"],
            )
            for value in truth["informative_null_targets"]
        }
        expected[case_id] = {}
        for value in item["object_registry"]:
            source = value["object_id"]
            target = item["focal_object_id"]
            if source == target:
                continue
            pair = (source, target)
            state = (
                "SUPPORTED_EFFECT" if pair in supported
                else "SUPPORTED_NULL" if pair in nulls
                else "UNRESOLVED"
            )
            expected[case_id][f"REL-{source}-{target}"] = state
    return expected


def _audit_task(*, item, role, refs, adapter):
    role_prompt = {
        "REFERENCE_EXTRACTOR": (
            "Extract the evidence-supported truth state of every relation "
            "from each non-focal object to the focal object."
        ),
        "REFERENCE_SKEPTIC": (
            "Independently challenge overclaim and underclaim, then assign "
            "the evidence-supported truth state of every relation from each "
            "non-focal object to the focal object."
        ),
    }[role]
    return ProviderCognitiveTask(
        task_id=f"{AUDIT_VERSION}-{role}-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            f"{role_prompt} Assess all relations exactly once. Use "
            "SUPPORTED_EFFECT only for evidence that positively supports "
            "the relation, SUPPORTED_NULL only for evidence that rules the "
            "relation out, and UNRESOLVED when neither is established. "
            "Do not infer truth from mere temporal order, imbalance, or an "
            "untested proposal. Bind supporting spans; unresolved relations "
            "may cite the span that exposes the gap."
        ),
        inputs={
            "stage": "REFERENCE_COMPLETENESS_AUDIT",
            "audit_role": role,
            "public_case": item,
            "private_reference_available": False,
            "provider_output_state": "DIAGNOSTIC_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=reference_audit_schema(item=item, refs=refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
