"""Object-conditional selective collaboration runtime v0.18."""

from __future__ import annotations

from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .cognitive_action_coordinator import BASES, SELECTIONS, tuple_violations
from .cognitive_action_protocol import ActionCost, build_action_receipt, validate_action_receipt
from .cognitive_action_selective_holdout import validate_selective_holdout
from .grammar_backed_role_adapter import validate_grammar_output
from .provider_telemetry import hash_payload


SELECTIVE_RUNTIME_VERSION = "cognitive_action_selective_runtime_v0_18"
SELECTIVE_TASK_KIND = "COGNITIVE_ACTION_SELECTIVE_ESCALATION"
SOURCE_EVALUATION_HASH = "30b724cb6870e20b7974ce9648f48bbfac84e7796866ecafbe5d6e8a59853f2c"
SOURCE_REFERENCE_HASH = "9060ea76277b2f688dad5b6003a9180ec2d88ac7a71e897027520265e54dd68b"
EVIDENCE_STATES = (
    "DIRECTLY_DEFINED",
    "COMPOSITIONALLY_DETERMINED",
    "SOFT_AMBIGUITY",
    "OPAQUE_REFERENCE",
    "CONFLICTED",
    "UNCERTAIN",
)
PROCESS_STATES = ("COMPLETE", "INCOMPLETE")
ADMISSION_CAP = 8


def build_selective_preregistration(*, source_evaluation):
    if (
        source_evaluation.get("artifact_hash") != SOURCE_EVALUATION_HASH
        or source_evaluation.get("reference_hash") != SOURCE_REFERENCE_HASH
        or source_evaluation.get("anti_additive_gate") != "REJECT"
        or source_evaluation.get("candidate_state") != "AXIS_ROUTING_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
    ):
        raise ValueError("selective_source_evaluation_invalid")
    commitment = {
        "preregistration_version": SELECTIVE_RUNTIME_VERSION,
        "source_evaluation_hash": SOURCE_EVALUATION_HASH,
        "source_reference_hash": SOURCE_REFERENCE_HASH,
        "frozen_hypothesis": "collaboration_value_depends_on_object_evidence_state",
        "admission_rule": {
            "evidence_state": "SOFT_AMBIGUITY",
            "selected_object": "NONE",
            "maximum_admissions": ADMISSION_CAP,
            "tie_break": "hash_order",
        },
        "collaboration_scope": {
            "local_role": "PRAGMATIC_DEFAULT_ONLY",
            "provider_role": "FOCUSED_PREFERENCE_ADJUDICATOR",
            "selected_object_mutable": False,
            "basis_critic_present": False,
            "non_admitted_behavior": "PRESERVE_BASELINE",
            "failed_escalation_behavior": "PRESERVE_BASELINE_AND_CHARGE_COST",
        },
        "success_gate": {
            "minimum_admission_precision": 0.75,
            "minimum_soft_ambiguity_recall": 0.60,
            "minimum_preference_case_gain": 2,
            "minimum_basis_case_gain": 0,
            "minimum_selected_object_case_gain": 0,
            "minimum_primary_correct_cell_gain": 2,
            "corrections_must_exceed_harms": True,
            "maximum_routed_to_baseline_token_ratio": 2.5,
            "maximum_tokens_per_net_primary_correct_cell": 12000,
            "required_output_coverage": 1.0,
        },
        "external_reference_available_during_inference": False,
        "reference_revision_allowed_after_candidate_run": False,
        "baseline_promotion_allowed_before_external_panel": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_selective_preregistration(artifact, *, source_evaluation):
    if artifact != build_selective_preregistration(source_evaluation=source_evaluation):
        raise ValueError("selective_preregistration_invalid")


def selective_tuple_schema(conflict_id, evidence_refs):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "conflict_id", "selected_object", "selection_basis", "pragmatic_preference",
            "evidence_state", "assessment_process_state", "action", "rationale",
            "confidence", "evidence_refs",
        ],
        "properties": {
            "conflict_id": {"type": "string", "enum": [conflict_id]},
            "selected_object": {"type": "string", "enum": list(SELECTIONS)},
            "selection_basis": {"type": "string", "enum": list(BASES)},
            "pragmatic_preference": {"type": "string", "enum": list(SELECTIONS)},
            "evidence_state": {"type": "string", "enum": list(EVIDENCE_STATES)},
            "assessment_process_state": {"type": "string", "enum": list(PROCESS_STATES)},
            "action": {"type": "string", "enum": ["ACCEPT", "CLARIFY", "ABSTAIN"]},
            "rationale": {"type": "string", "minLength": 1, "maxLength": 900},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence_refs": {
                "type": "array",
                "minItems": len(evidence_refs),
                "maxItems": len(evidence_refs),
                "items": {"type": "string", "enum": list(evidence_refs)},
            },
        },
    }


def validate_selective_tuple(payload, *, conflict_id, evidence_refs):
    required = set(selective_tuple_schema(conflict_id, evidence_refs)["required"])
    if (
        not isinstance(payload, dict)
        or set(payload) != required
        or payload.get("conflict_id") != conflict_id
        or payload.get("evidence_refs") != list(evidence_refs)
    ):
        raise ValueError("selective_tuple_shape_invalid")
    if (
        payload["selected_object"] not in SELECTIONS
        or payload["selection_basis"] not in BASES
        or payload["pragmatic_preference"] not in SELECTIONS
        or payload["evidence_state"] not in EVIDENCE_STATES
        or payload["assessment_process_state"] not in PROCESS_STATES
    ):
        raise ValueError("selective_tuple_value_invalid")
    if (
        not isinstance(payload["confidence"], (int, float))
        or isinstance(payload["confidence"], bool)
        or not 0 <= payload["confidence"] <= 1
        or not isinstance(payload["rationale"], str)
        or not payload["rationale"].strip()
    ):
        raise ValueError("selective_tuple_metadata_invalid")
    compatibility = {
        "DIRECTLY_DEFINED": ("LEXICAL_EXACT",),
        "COMPOSITIONALLY_DETERMINED": ("COMPOSITIONAL_ENTAILMENT",),
        "SOFT_AMBIGUITY": ("PRAGMATIC_DEFAULT", "NO_PREFERENCE"),
        "OPAQUE_REFERENCE": ("NO_PREFERENCE",),
        "CONFLICTED": ("UNCERTAIN",),
        "UNCERTAIN": ("UNCERTAIN",),
    }
    if payload["selection_basis"] not in compatibility[payload["evidence_state"]]:
        raise ValueError("selective_evidence_basis_incoherent")
    if tuple_violations({
        **payload,
        "assessment_completeness": payload["assessment_process_state"],
    }):
        raise ValueError("selective_tuple_incoherent")


def run_selective_baseline(*, corpus, preregistration, adapter):
    validate_selective_holdout(corpus)
    if preregistration.get("preregistration_version") != SELECTIVE_RUNTIME_VERSION:
        raise ValueError("selective_preregistration_missing")
    outputs, failures = [], []
    evidence_refs = tuple(corpus["evidence_refs"])
    for item in corpus["public_surface"]["items"]:
        task = _baseline_task(item=item, evidence_refs=evidence_refs, adapter=adapter)
        envelope = ProviderTaskRouter([adapter]).route(task)
        invocation = envelope.invocation_receipt.as_dict()
        if envelope.status != "COMPLETED":
            failures.append(_failure("BASELINE", item["conflict_id"], envelope, invocation))
            continue
        try:
            validate_selective_tuple(
                envelope.normalized_result,
                conflict_id=item["conflict_id"],
                evidence_refs=evidence_refs,
            )
        except ValueError as exc:
            failures.append({
                "stage": "BASELINE",
                "conflict_id": item["conflict_id"],
                "status": "SEMANTIC_VALIDATION_FAILED",
                "validation_errors": [str(exc)],
                "payload": envelope.normalized_result,
                "invocation_receipt": invocation,
            })
            continue
        payload = envelope.normalized_result
        usage = invocation.get("token_usage") or {}
        receipt = build_action_receipt(
            action_id="action-" + hash_payload([SELECTIVE_RUNTIME_VERSION, "baseline", item["conflict_id"]])[:18],
            action_type="SYNTHESIZE",
            object_ref="object://" + item["conflict_id"],
            actor_role="COORDINATOR",
            actor_instance=f"{adapter.profile.model_id}:SINGLE_MODEL_BASELINE",
            method=SELECTIVE_RUNTIME_VERSION,
            result_state="CANDIDATE",
            result={key: payload[key] for key in (
                "selected_object", "selection_basis", "pragmatic_preference",
                "evidence_state", "assessment_process_state", "action",
            )},
            evidence_refs=evidence_refs,
            support=(payload["rationale"],),
            uncertainty=round(1 - payload["confidence"], 6),
            recommended_next_actions=("CLARIFY",) if payload["action"] == "CLARIFY" else ("ABSTAIN",) if payload["action"] == "ABSTAIN" else ("FALSIFY",),
            cost=_usage_cost(usage),
        )
        commitment = {
            "stage": "BASELINE",
            "conflict_id": item["conflict_id"],
            "payload": payload,
            "action_receipt": receipt,
            "invocation_receipt": invocation,
            "task_contract_hash": task.contract_hash(),
            "reference_available": False,
        }
        outputs.append({**commitment, "output_hash": hash_payload(commitment)})
    run_commitment = {
        "runtime_version": SELECTIVE_RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "outputs": outputs,
        "failures": failures,
        "external_reference_available": False,
        "candidate_outputs_frozen_before_external_reference": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**run_commitment, "run_hash": hash_payload(run_commitment)}


def build_admission_plan(*, corpus, preregistration, baseline_run):
    validate_selective_baseline(corpus=corpus, baseline_run=baseline_run)
    if preregistration.get("artifact_hash") != baseline_run.get("source_preregistration_hash"):
        raise ValueError("selective_admission_preregistration_mismatch")
    eligible = [
        output["conflict_id"]
        for output in baseline_run["outputs"]
        if output["payload"]["evidence_state"] == "SOFT_AMBIGUITY"
        and output["payload"]["selected_object"] == "NONE"
    ]
    ranked = sorted(eligible, key=lambda conflict_id: hash_payload([SELECTIVE_RUNTIME_VERSION, "admit", conflict_id]))
    admitted = ranked[:ADMISSION_CAP]
    commitment = {
        "plan_version": SELECTIVE_RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_baseline_run_hash": baseline_run["run_hash"],
        "eligible_conflict_ids": ranked,
        "admitted_conflict_ids": admitted,
        "admission_cap": ADMISSION_CAP,
        "cap_applied": len(ranked) > ADMISSION_CAP,
        "admission_rule_executed_mechanically": True,
        "semantic_admission_source": "BASELINE_PROVIDER_EVIDENCE_STATE",
        "reference_available": False,
    }
    return {**commitment, "plan_hash": hash_payload(commitment)}


def run_local_preference_roles(*, corpus, admission_plan, adapter):
    validate_selective_holdout(corpus)
    public = {item["conflict_id"]: item for item in corpus["public_surface"]["items"]}
    outputs, failures = [], []
    for conflict_id in admission_plan["admitted_conflict_ids"]:
        try:
            output = adapter.invoke(
                role_id="PRAGMATIC_DEFAULT",
                item=public[conflict_id],
                evidence_refs=tuple(corpus["evidence_refs"]),
            )
            validate_grammar_output(output, item=public[conflict_id])
            outputs.append(output)
        except Exception as exc:
            failures.append({
                "stage": "LOCAL_PRAGMATIC_ROLE",
                "conflict_id": conflict_id,
                "status": "FAILED",
                "error_type": type(exc).__name__,
            })
    commitment = {
        "runtime_version": SELECTIVE_RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_admission_plan_hash": admission_plan["plan_hash"],
        "outputs": outputs,
        "failures": failures,
        "requested_count": len(admission_plan["admitted_conflict_ids"]),
        "reference_available": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def run_selective_adjudication(*, corpus, preregistration, baseline_run, admission_plan, local_role_run, adapter):
    validate_selective_holdout(corpus)
    validate_selective_baseline(corpus=corpus, baseline_run=baseline_run)
    public = {item["conflict_id"]: item for item in corpus["public_surface"]["items"]}
    baseline = {output["conflict_id"]: output for output in baseline_run["outputs"]}
    roles = {
        output["object_ref"].removeprefix("object://"): output["action_receipt"]
        for output in local_role_run["outputs"]
    }
    adjudications, failures, routed = [], [], []
    admitted = set(admission_plan["admitted_conflict_ids"])
    evidence_refs = tuple(corpus["evidence_refs"])
    for conflict_id, baseline_output in baseline.items():
        if conflict_id not in admitted:
            routed.append(_preserved_output(baseline_output, reason="NOT_ADMITTED"))
            continue
        role_receipt = roles.get(conflict_id)
        if role_receipt is None:
            failures.append({"stage": "LOCAL_ROLE_MISSING", "conflict_id": conflict_id, "status": "FAILED"})
            routed.append(_preserved_output(baseline_output, reason="LOCAL_ROLE_FAILED"))
            continue
        task = _preference_task(
            item=public[conflict_id],
            baseline_output=baseline_output,
            role_receipt=role_receipt,
            evidence_refs=evidence_refs,
            adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        invocation = envelope.invocation_receipt.as_dict()
        if envelope.status != "COMPLETED":
            failures.append(_failure("PREFERENCE_ADJUDICATION", conflict_id, envelope, invocation))
            routed.append(_preserved_output(baseline_output, reason="ADJUDICATOR_FAILED"))
            continue
        payload = envelope.normalized_result
        try:
            _validate_preference_payload(payload, conflict_id=conflict_id, evidence_refs=evidence_refs)
        except ValueError as exc:
            failures.append({
                "stage": "PREFERENCE_ADJUDICATION",
                "conflict_id": conflict_id,
                "status": "SEMANTIC_VALIDATION_FAILED",
                "validation_errors": [str(exc)],
                "payload": payload,
                "invocation_receipt": invocation,
            })
            routed.append(_preserved_output(baseline_output, reason="ADJUDICATOR_INVALID"))
            continue
        usage = invocation.get("token_usage") or {}
        receipt = build_action_receipt(
            action_id="action-" + hash_payload([SELECTIVE_RUNTIME_VERSION, "adjudicate", conflict_id])[:18],
            action_type="ADJUDICATE",
            object_ref="object://" + conflict_id,
            actor_role="ADJUDICATOR",
            actor_instance=f"{adapter.profile.model_id}:FOCUSED_PREFERENCE",
            method=SELECTIVE_RUNTIME_VERSION,
            result_state="CANDIDATE",
            result={"pragmatic_preference": payload["pragmatic_preference"]},
            input_claim_refs=(baseline_output["action_receipt"]["receipt_hash"], role_receipt["receipt_hash"]),
            evidence_refs=evidence_refs,
            support=(payload["rationale"],),
            uncertainty=round(1 - payload["confidence"], 6),
            recommended_next_actions=("CLARIFY",) if payload["pragmatic_preference"] == "UNCERTAIN" else ("FALSIFY",),
            cost=_usage_cost(usage),
        )
        adjudication_commitment = {
            "stage": "PREFERENCE_ADJUDICATION",
            "conflict_id": conflict_id,
            "payload": payload,
            "action_receipt": receipt,
            "invocation_receipt": invocation,
            "task_contract_hash": task.contract_hash(),
            "reference_available": False,
        }
        adjudication = {**adjudication_commitment, "output_hash": hash_payload(adjudication_commitment)}
        adjudications.append(adjudication)
        routed.append(_fused_output(baseline_output=baseline_output, adjudication=adjudication))
    commitment = {
        "runtime_version": SELECTIVE_RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_baseline_run_hash": baseline_run["run_hash"],
        "source_admission_plan_hash": admission_plan["plan_hash"],
        "source_local_role_run_hash": local_role_run["run_hash"],
        "adjudications": adjudications,
        "routed_outputs": routed,
        "failures": failures,
        "selected_object_mutable": False,
        "basis_critic_present": False,
        "fallback_preserves_baseline": True,
        "external_reference_available": False,
        "candidate_outputs_frozen_before_external_reference": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    run = {**commitment, "run_hash": hash_payload(commitment)}
    validate_selective_run(corpus=corpus, baseline_run=baseline_run, run=run)
    return run


def analyze_selective_run(*, corpus, baseline_run, admission_plan, local_role_run, run):
    validate_selective_run(corpus=corpus, baseline_run=baseline_run, run=run)
    baseline_success_cost = _sum_receipt_cost(output["action_receipt"] for output in baseline_run["outputs"])
    baseline_failure_cost = _failed_cost(baseline_run["failures"])
    baseline_cost = Counter(baseline_success_cost)
    baseline_cost.update(baseline_failure_cost)
    local_cost = _sum_receipt_cost(output["action_receipt"] for output in local_role_run["outputs"])
    adjudicator_cost = _sum_receipt_cost(output["action_receipt"] for output in run["adjudications"])
    failure_cost = _failed_cost(run["failures"])
    selective_extra = Counter(local_cost)
    selective_extra.update(adjudicator_cost)
    selective_extra.update(failure_cost)
    total = Counter(baseline_cost)
    total.update(selective_extra)
    baseline_tokens = baseline_cost["input_tokens"] + baseline_cost["output_tokens"]
    total_tokens = total["input_tokens"] + total["output_tokens"]
    routed = {output["conflict_id"]: output for output in run["routed_outputs"]}
    baseline = {output["conflict_id"]: output for output in baseline_run["outputs"]}
    commitment = {
        "analysis_version": SELECTIVE_RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "baseline_coverage": round(len(baseline) / corpus["case_count"], 6),
        "routed_coverage": round(len(routed) / len(baseline), 6) if baseline else 0,
        "eligible_count": len(admission_plan["eligible_conflict_ids"]),
        "admitted_count": len(admission_plan["admitted_conflict_ids"]),
        "successful_adjudication_count": len(run["adjudications"]),
        "fallback_count": sum(output["route_state"] != "ADJUDICATED" for output in run["routed_outputs"]),
        "selected_object_preservation_count": sum(
            routed[conflict_id]["payload"]["selected_object"] == output["payload"]["selected_object"]
            for conflict_id, output in baseline.items()
        ),
        "baseline_success_accounting": dict(baseline_success_cost),
        "baseline_failed_invocation_accounting": dict(baseline_failure_cost),
        "baseline_accounting": dict(baseline_cost),
        "local_role_accounting": dict(local_cost),
        "adjudicator_accounting": dict(adjudicator_cost),
        "failed_invocation_accounting": dict(failure_cost),
        "selective_extra_accounting": dict(selective_extra),
        "routed_path_accounting": dict(total),
        "baseline_total_tokens": baseline_tokens,
        "routed_path_total_tokens": total_tokens,
        "routed_to_baseline_token_ratio": round(total_tokens / baseline_tokens, 6) if baseline_tokens else None,
        "semantic_accuracy_available": False,
        "external_panel_required": True,
        "collective_gain_claim_allowed": False,
        "candidate_state": "SELECTIVE_ESCALATION_FROZEN_AWAITING_EXTERNAL_PANEL",
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_selective_baseline(*, corpus, baseline_run):
    commitment = {key: value for key, value in baseline_run.items() if key != "run_hash"}
    if (
        baseline_run.get("run_hash") != hash_payload(commitment)
        or baseline_run.get("source_corpus_hash") != corpus.get("artifact_hash")
    ):
        raise ValueError("selective_baseline_invalid")
    seen = set()
    for output in baseline_run["outputs"]:
        output_commitment = {key: value for key, value in output.items() if key != "output_hash"}
        if output.get("output_hash") != hash_payload(output_commitment):
            raise ValueError("selective_baseline_output_hash_invalid")
        validate_action_receipt(output["action_receipt"])
        validate_selective_tuple(
            output["payload"],
            conflict_id=output["conflict_id"],
            evidence_refs=tuple(corpus["evidence_refs"]),
        )
        if output["conflict_id"] in seen:
            raise ValueError("selective_baseline_duplicate")
        seen.add(output["conflict_id"])
    if len(baseline_run["outputs"]) + len(baseline_run["failures"]) != corpus["case_count"]:
        raise ValueError("selective_baseline_coverage_invalid")


def validate_selective_run(*, corpus, baseline_run, run):
    commitment = {key: value for key, value in run.items() if key != "run_hash"}
    if (
        run.get("run_hash") != hash_payload(commitment)
        or run.get("source_corpus_hash") != corpus.get("artifact_hash")
        or run.get("source_baseline_run_hash") != baseline_run.get("run_hash")
        or run.get("selected_object_mutable") is not False
        or run.get("basis_critic_present") is not False
        or run.get("fallback_preserves_baseline") is not True
    ):
        raise ValueError("selective_run_invalid")
    baseline = {output["conflict_id"]: output["payload"] for output in baseline_run["outputs"]}
    routed = {}
    for output in run["routed_outputs"]:
        commitment = {key: value for key, value in output.items() if key != "output_hash"}
        if output.get("output_hash") != hash_payload(commitment):
            raise ValueError("selective_routed_output_hash_invalid")
        conflict_id = output["conflict_id"]
        if conflict_id in routed or conflict_id not in baseline:
            raise ValueError("selective_routed_output_binding_invalid")
        routed[conflict_id] = output
        if output["payload"]["selected_object"] != baseline[conflict_id]["selected_object"]:
            raise ValueError("selective_selected_object_mutated")
        if output["route_state"] != "ADJUDICATED" and output["payload"] != baseline[conflict_id]:
            raise ValueError("selective_fallback_changed_baseline")
    if set(routed) != set(baseline):
        raise ValueError("selective_routed_coverage_invalid")


def _baseline_task(*, item, evidence_refs, adapter):
    objective = (
        "Assess the displayed object as a semantic tuple and separately classify its evidence state. "
        "DIRECTLY_DEFINED means exact wording fixes A or B; COMPOSITIONALLY_DETERMINED means combined constraints fix A or B; "
        "SOFT_AMBIGUITY means neither is entailed but ordinary context may favor one; OPAQUE_REFERENCE means a missing codebook "
        "or definition blocks selection; CONFLICTED means displayed evidence clashes; UNCERTAIN is residual uncertainty. "
        "A justified open conclusion can have assessment_process_state COMPLETE. Use INCOMPLETE only when your assessment itself "
        "could not be completed. Keep semantic selection separate from pragmatic preference."
    )
    return ProviderCognitiveTask(
        task_id=f"{SELECTIVE_RUNTIME_VERSION}-baseline-{item['conflict_id']}",
        task_kind=SELECTIVE_TASK_KIND,
        objective=objective,
        inputs={"arm": "SINGLE_MODEL_BASELINE", "public_object": item, "external_reference": "WITHHELD"},
        allowed_evidence=list(evidence_refs),
        expected_schema=selective_tuple_schema(item["conflict_id"], evidence_refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="retain_failure_without_local_semantic_substitution",
    )


def _preference_schema(conflict_id, evidence_refs):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["conflict_id", "pragmatic_preference", "rationale", "confidence", "evidence_refs"],
        "properties": {
            "conflict_id": {"type": "string", "enum": [conflict_id]},
            "pragmatic_preference": {"type": "string", "enum": ["CANDIDATE_A", "CANDIDATE_B", "NONE", "UNCERTAIN"]},
            "rationale": {"type": "string", "minLength": 1, "maxLength": 700},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence_refs": {
                "type": "array",
                "minItems": len(evidence_refs),
                "maxItems": len(evidence_refs),
                "items": {"type": "string", "enum": list(evidence_refs)},
            },
        },
    }


def _preference_task(*, item, baseline_output, role_receipt, evidence_refs, adapter):
    objective = (
        "The baseline has already classified this object as semantically open and selected NONE. "
        "Adjudicate only whether ordinary context pragmatically favors candidate A, candidate B, neither, or remains uncertain. "
        "Do not change the selected object or introduce hidden definitions. Treat the local role receipt as fallible evidence."
    )
    return ProviderCognitiveTask(
        task_id=f"{SELECTIVE_RUNTIME_VERSION}-preference-{item['conflict_id']}",
        task_kind=SELECTIVE_TASK_KIND,
        objective=objective,
        inputs={
            "public_object": item,
            "frozen_selected_object": baseline_output["payload"]["selected_object"],
            "baseline_preference": baseline_output["payload"]["pragmatic_preference"],
            "local_preference_receipt": {
                "result": role_receipt["result"],
                "uncertainty": role_receipt["uncertainty"],
                "receipt_hash": role_receipt["receipt_hash"],
            },
            "external_reference": "WITHHELD",
        },
        allowed_evidence=list(evidence_refs),
        expected_schema=_preference_schema(item["conflict_id"], evidence_refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_frozen_baseline_and_charge_failed_work",
    )


def _validate_preference_payload(payload, *, conflict_id, evidence_refs):
    required = set(_preference_schema(conflict_id, evidence_refs)["required"])
    if (
        not isinstance(payload, dict)
        or set(payload) != required
        or payload.get("conflict_id") != conflict_id
        or payload.get("pragmatic_preference") not in SELECTIONS
        or payload.get("evidence_refs") != list(evidence_refs)
        or not isinstance(payload.get("confidence"), (int, float))
        or isinstance(payload.get("confidence"), bool)
        or not 0 <= payload["confidence"] <= 1
        or not isinstance(payload.get("rationale"), str)
        or not payload["rationale"].strip()
    ):
        raise ValueError("selective_preference_payload_invalid")


def _preserved_output(baseline_output, *, reason):
    commitment = {
        "conflict_id": baseline_output["conflict_id"],
        "route_state": "BASELINE_PRESERVED",
        "route_reason": reason,
        "payload": baseline_output["payload"],
        "baseline_output_hash": baseline_output["output_hash"],
        "adjudication_output_hash": "",
    }
    return {**commitment, "output_hash": hash_payload(commitment)}


def _fused_output(*, baseline_output, adjudication):
    payload = dict(baseline_output["payload"])
    preference = adjudication["payload"]["pragmatic_preference"]
    payload["pragmatic_preference"] = preference
    payload["selection_basis"] = (
        "PRAGMATIC_DEFAULT"
        if preference in ("CANDIDATE_A", "CANDIDATE_B")
        else "NO_PREFERENCE"
        if preference == "NONE"
        else "UNCERTAIN"
    )
    if preference == "UNCERTAIN":
        payload["selected_object"] = "UNCERTAIN"
        # This path would violate the immutable selected-object boundary.
        return _preserved_output(baseline_output, reason="ADJUDICATOR_UNCERTAIN")
    payload["rationale"] = adjudication["payload"]["rationale"]
    payload["confidence"] = adjudication["payload"]["confidence"]
    commitment = {
        "conflict_id": baseline_output["conflict_id"],
        "route_state": "ADJUDICATED",
        "route_reason": "SOFT_AMBIGUITY_ADMITTED",
        "payload": payload,
        "baseline_output_hash": baseline_output["output_hash"],
        "adjudication_output_hash": adjudication["output_hash"],
    }
    return {**commitment, "output_hash": hash_payload(commitment)}


def _failure(stage, conflict_id, envelope, invocation):
    return {
        "stage": stage,
        "conflict_id": conflict_id,
        "status": envelope.status,
        "validation_errors": list(envelope.validation_errors),
        "invocation_receipt": invocation,
    }


def _usage_cost(usage):
    return ActionCost(
        provider_calls=max(1, int(usage.get("provider_calls") or 1)),
        input_tokens=int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        latency_ms=int(usage.get("latency_ms") or 0),
    )


def _sum_receipt_cost(receipts):
    total = Counter()
    for receipt in receipts:
        total.update(receipt["cost"])
    return total


def _failed_cost(failures):
    total, seen = Counter(), set()
    for failure in failures:
        receipt = failure.get("invocation_receipt") or {}
        receipt_hash = receipt.get("receipt_hash")
        if not receipt_hash or receipt_hash in seen:
            continue
        seen.add(receipt_hash)
        usage = receipt.get("token_usage") or {}
        total.update({
            "provider_calls": int(usage.get("provider_calls") or 1),
            "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
            "latency_ms": int(usage.get("latency_ms") or 0),
        })
    return total
