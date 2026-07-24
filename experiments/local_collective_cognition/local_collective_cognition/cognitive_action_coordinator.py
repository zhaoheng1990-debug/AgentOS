"""Blinded DeepSeek baseline and role-informed coordinator arms v0.16."""

from __future__ import annotations

from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .cognitive_action_fresh_holdout import validate_fresh_action_holdout
from .cognitive_action_protocol import ActionCost, build_action_receipt, validate_action_receipt
from .provider_telemetry import hash_payload


COORDINATOR_VERSION = "cognitive_action_coordinator_v0_16"
COORDINATOR_TASK_KIND = "COGNITIVE_ACTION_BLIND_SYNTHESIS"
ARMS = ("SINGLE_MODEL_BASELINE", "ROLE_INFORMED_COORDINATOR")
SELECTIONS = ("CANDIDATE_A", "CANDIDATE_B", "NONE", "UNCERTAIN")
BASES = ("LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT", "PRAGMATIC_DEFAULT", "NO_PREFERENCE", "UNCERTAIN")
COMPLETENESS = ("COMPLETE", "INCOMPLETE", "UNCERTAIN")
ACTIONS = ("ACCEPT", "CLARIFY", "ABSTAIN")


def coordinator_schema(conflict_id, evidence_refs):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["conflict_id", "selected_object", "selection_basis", "pragmatic_preference", "assessment_completeness", "action", "rationale", "confidence", "evidence_refs"],
        "properties": {
            "conflict_id": {"type": "string", "enum": [conflict_id]},
            "selected_object": {"type": "string", "enum": list(SELECTIONS)},
            "selection_basis": {"type": "string", "enum": list(BASES)},
            "pragmatic_preference": {"type": "string", "enum": list(SELECTIONS)},
            "assessment_completeness": {"type": "string", "enum": list(COMPLETENESS)},
            "action": {"type": "string", "enum": list(ACTIONS)},
            "rationale": {"type": "string", "minLength": 1, "maxLength": 800},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence_refs": {"type": "array", "minItems": len(evidence_refs), "maxItems": len(evidence_refs), "items": {"type": "string", "enum": list(evidence_refs)}},
        },
    }


def validate_coordinator_payload(payload, *, conflict_id, evidence_refs):
    required = set(coordinator_schema(conflict_id, evidence_refs)["required"])
    if not isinstance(payload, dict) or set(payload) != required or payload.get("conflict_id") != conflict_id or payload.get("evidence_refs") != list(evidence_refs):
        raise ValueError("cognitive_action_coordinator_payload_invalid")
    if payload["selected_object"] not in SELECTIONS or payload["selection_basis"] not in BASES or payload["pragmatic_preference"] not in SELECTIONS or payload["assessment_completeness"] not in COMPLETENESS or payload["action"] not in ACTIONS:
        raise ValueError("cognitive_action_coordinator_value_invalid")
    if not isinstance(payload["confidence"], (int, float)) or isinstance(payload["confidence"], bool) or not 0 <= payload["confidence"] <= 1 or not isinstance(payload["rationale"], str) or not payload["rationale"].strip():
        raise ValueError("cognitive_action_coordinator_metadata_invalid")
    violations = tuple_violations(payload)
    if violations:
        raise ValueError("cognitive_action_coordinator_tuple_incoherent:" + ",".join(violations))


def tuple_violations(payload):
    selected, basis = payload["selected_object"], payload["selection_basis"]
    preference, completeness = payload["pragmatic_preference"], payload["assessment_completeness"]
    violations = []
    if basis in ("LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT") and selected not in ("CANDIDATE_A", "CANDIDATE_B"):
        violations.append("HARD_BASIS_WITHOUT_OBJECT")
    if basis == "PRAGMATIC_DEFAULT" and (selected != "NONE" or preference not in ("CANDIDATE_A", "CANDIDATE_B")):
        violations.append("PRAGMATIC_BASIS_MISMATCH")
    if basis == "NO_PREFERENCE" and (selected != "NONE" or preference != "NONE"):
        violations.append("NO_PREFERENCE_MISMATCH")
    if basis == "UNCERTAIN" and selected != "UNCERTAIN":
        violations.append("UNCERTAIN_BASIS_MISMATCH")
    if completeness == "INCOMPLETE" and payload["action"] == "ACCEPT":
        violations.append("INCOMPLETE_ACCEPTED")
    return violations


def run_blind_coordinator_arms(*, corpus, role_run, role_analysis, adapter):
    validate_fresh_action_holdout(corpus)
    if not role_analysis.get("coordinator_run_allowed"):
        raise ValueError("cognitive_action_coordinator_gate_closed")
    receipts = _index_role_receipts(role_run)
    arm_outputs, failures = [], []
    for item in corpus["public_surface"]["items"]:
        conflict_id = item["conflict_id"]
        order = ARMS if int(hash_payload([COORDINATOR_VERSION, conflict_id])[:2], 16) % 2 == 0 else tuple(reversed(ARMS))
        for arm in order:
            task = _task(item=item, arm=arm, role_receipts=receipts[conflict_id], evidence_refs=tuple(corpus["evidence_refs"]), adapter=adapter)
            envelope = ProviderTaskRouter([adapter]).route(task)
            invocation = envelope.invocation_receipt.as_dict()
            if envelope.status != "COMPLETED":
                failures.append({"arm": arm, "conflict_id": conflict_id, "status": envelope.status, "validation_errors": list(envelope.validation_errors), "invocation_receipt": invocation})
                continue
            try:
                validate_coordinator_payload(envelope.normalized_result, conflict_id=conflict_id, evidence_refs=tuple(corpus["evidence_refs"]))
            except ValueError as exc:
                failures.append({"arm": arm, "conflict_id": conflict_id, "status": "SEMANTIC_VALIDATION_FAILED", "validation_errors": [str(exc)], "payload": envelope.normalized_result, "invocation_receipt": invocation})
                continue
            usage = invocation.get("token_usage") or {}
            payload = envelope.normalized_result
            action_receipt = build_action_receipt(
                action_id="action-" + hash_payload([COORDINATOR_VERSION, arm, conflict_id])[:18],
                action_type="SYNTHESIZE", object_ref="object://" + conflict_id,
                actor_role="COORDINATOR", actor_instance=f"{adapter.profile.model_id}:{arm}",
                method=COORDINATOR_VERSION, result_state="CANDIDATE",
                result={key: payload[key] for key in ("selected_object", "selection_basis", "pragmatic_preference", "assessment_completeness", "action")},
                input_claim_refs=tuple(receipt["receipt_hash"] for receipt in receipts[conflict_id]) if arm == "ROLE_INFORMED_COORDINATOR" else (),
                evidence_refs=tuple(corpus["evidence_refs"]), support=(payload["rationale"],),
                uncertainty=round(1 - payload["confidence"], 6),
                recommended_next_actions=("CLARIFY",) if payload["action"] == "CLARIFY" else ("ABSTAIN",) if payload["action"] == "ABSTAIN" else ("FALSIFY",),
                cost=ActionCost(provider_calls=max(1, int(usage.get("provider_calls") or 1)), input_tokens=int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0), output_tokens=int(usage.get("completion_tokens") or usage.get("output_tokens") or 0), latency_ms=int(usage.get("latency_ms") or 0)),
            )
            output_commitment = {"arm": arm, "conflict_id": conflict_id, "payload": payload, "action_receipt": action_receipt, "invocation_receipt": invocation, "task_contract_hash": task.contract_hash(), "reference_available": False}
            arm_outputs.append({**output_commitment, "output_hash": hash_payload(output_commitment)})
    commitment = {
        "runtime_version": COORDINATOR_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_role_run_hash": role_run["run_hash"],
        "source_role_analysis_hash": role_analysis["artifact_hash"],
        "arm_outputs": arm_outputs,
        "failures": failures,
        "arm_order_counterbalanced": True,
        "external_reference_available": False,
        "candidate_outputs_frozen_before_external_reference": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_blind_coordinator_arms(*, corpus, role_run, role_analysis, run):
    validate_blind_coordinator_run(corpus=corpus, role_run=role_run, role_analysis=role_analysis, run=run)
    by_arm = {arm: {} for arm in ARMS}
    accounting = {arm: Counter() for arm in ARMS}
    action_counts = {arm: Counter() for arm in ARMS}
    for output in run["arm_outputs"]:
        arm, conflict_id = output["arm"], output["conflict_id"]
        by_arm[arm][conflict_id] = output["payload"]
        action_counts[arm][output["payload"]["action"]] += 1
        for key, value in output["action_receipt"]["cost"].items():
            accounting[arm][key] += value
    common = set(by_arm[ARMS[0]]) & set(by_arm[ARMS[1]])
    tuple_fields = ("selected_object", "selection_basis", "pragmatic_preference", "assessment_completeness")
    disagreements = [conflict_id for conflict_id in sorted(common) if any(by_arm[ARMS[0]][conflict_id][field] != by_arm[ARMS[1]][conflict_id][field] for field in tuple_fields)]
    axis_disagreements = {
        field: sum(by_arm[ARMS[0]][conflict_id][field] != by_arm[ARMS[1]][conflict_id][field] for conflict_id in common)
        for field in (*tuple_fields, "action")
    }
    role_receipts = _index_role_receipts(role_run)
    role_results = {conflict_id: {receipt["actor_role"]: receipt["result"] for receipt in receipts} for conflict_id, receipts in role_receipts.items()}
    role_agreement = {}
    for arm in ARMS:
        role_agreement[arm] = {
            "object_plus_basis": sum(
                (payload["selected_object"], payload["selection_basis"]) == (
                    role_results[conflict_id]["OBJECT_GROUNDING"]["selected_object"],
                    role_results[conflict_id]["OBJECT_GROUNDING"]["selection_basis"],
                ) for conflict_id, payload in by_arm[arm].items()
            ),
            "pragmatic_preference": sum(
                payload["pragmatic_preference"] == role_results[conflict_id]["PRAGMATIC_DEFAULT"]["pragmatic_preference"]
                for conflict_id, payload in by_arm[arm].items()
            ),
            "assessment_completeness": sum(
                payload["assessment_completeness"] == role_results[conflict_id]["ASSESSMENT_SKEPTIC"]["assessment_completeness"]
                for conflict_id, payload in by_arm[arm].items()
            ),
        }
    field_distributions = {
        arm: {field: dict(Counter(payload[field] for payload in by_arm[arm].values())) for field in (*tuple_fields, "action")}
        for arm in ARMS
    }
    baseline_cost = accounting["SINGLE_MODEL_BASELINE"]
    coordinator_cost = accounting["ROLE_INFORMED_COORDINATOR"]
    cost_ratios = {
        key: round(coordinator_cost[key] / baseline_cost[key], 6) if baseline_cost[key] else None
        for key in ("input_tokens", "output_tokens", "latency_ms")
    }
    commitment = {
        "analysis_version": COORDINATOR_VERSION,
        "source_run_hash": run["run_hash"],
        "arm_coverage": {arm: round(len(by_arm[arm]) / corpus["case_count"], 6) for arm in ARMS},
        "common_case_count": len(common),
        "full_tuple_disagreement_count": len(disagreements),
        "full_tuple_disagreement_ids": disagreements,
        "axis_disagreement_counts": axis_disagreements,
        "field_distributions": field_distributions,
        "role_receipt_agreement_counts": role_agreement,
        "action_distributions": {arm: dict(action_counts[arm]) for arm in ARMS},
        "accounting": {arm: dict(accounting[arm]) for arm in ARMS},
        "coordinator_to_baseline_cost_ratios": cost_ratios,
        "all_accepted_outputs_mechanically_coherent": True,
        "action_semantics_evidence_state": "CONSTRUCTION_FAILURE_ACTION_PRECONDITIONS_UNDERSPECIFIED",
        "action_distribution_interpretation_allowed": False,
        "semantic_accuracy_available": False,
        "collective_gain_claim_allowed": False,
        "external_panel_required": True,
        "candidate_state": "BLIND_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL",
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_blind_coordinator_run(*, corpus, role_run, role_analysis, run):
    commitment = {key: value for key, value in run.items() if key != "run_hash"}
    if run.get("run_hash") != hash_payload(commitment) or run.get("source_corpus_hash") != corpus.get("artifact_hash") or run.get("source_role_run_hash") != role_run.get("run_hash") or run.get("source_role_analysis_hash") != role_analysis.get("artifact_hash") or run.get("external_reference_available") is not False:
        raise ValueError("cognitive_action_coordinator_run_invalid")
    seen = set()
    for output in run["arm_outputs"]:
        output_commitment = {key: value for key, value in output.items() if key != "output_hash"}
        if output.get("output_hash") != hash_payload(output_commitment):
            raise ValueError("cognitive_action_coordinator_output_hash_invalid")
        validate_action_receipt(output["action_receipt"])
        validate_coordinator_payload(output["payload"], conflict_id=output["conflict_id"], evidence_refs=tuple(corpus["evidence_refs"]))
        key = (output["arm"], output["conflict_id"])
        if key in seen:
            raise ValueError("cognitive_action_coordinator_duplicate_output")
        seen.add(key)
    if len(run["arm_outputs"]) + len(run["failures"]) != corpus["case_count"] * len(ARMS):
        raise ValueError("cognitive_action_coordinator_coverage_invalid")


def _index_role_receipts(role_run):
    index = {}
    for output in role_run["outputs"]:
        conflict_id = output["object_ref"].removeprefix("object://")
        index.setdefault(conflict_id, []).append(output["action_receipt"])
    for conflict_id, receipts in index.items():
        receipts.sort(key=lambda receipt: receipt["actor_role"])
        if len(receipts) != 3:
            raise ValueError(f"cognitive_action_role_receipts_incomplete:{conflict_id}")
    return index


def _task(*, item, arm, role_receipts, evidence_refs, adapter):
    role_input = [
        {"role": receipt["actor_role"], "model": receipt["actor_instance"], "result": receipt["result"], "uncertainty": receipt["uncertainty"], "receipt_hash": receipt["receipt_hash"]}
        for receipt in role_receipts
    ] if arm == "ROLE_INFORMED_COORDINATOR" else "WITHHELD_FOR_SINGLE_MODEL_BASELINE"
    objective = (
        "Return one coherent full semantic tuple for the public object. Distinguish semantic selection from pragmatic preference. "
        "A hard lexical or compositional basis requires selected A or B. PRAGMATIC_DEFAULT requires selected NONE and directional preference A or B. "
        "NO_PREFERENCE requires selected NONE and preference NONE. A justified open result may be COMPLETE. Use INCOMPLETE only when missing material prevents even deciding whether openness is warranted. "
        + ("Treat local role receipts as fallible evidence: resolve conflicts and preserve uncertainty rather than voting." if arm == "ROLE_INFORMED_COORDINATOR" else "Reason directly from the public object without local role receipts.")
    )
    return ProviderCognitiveTask(
        task_id=f"{COORDINATOR_VERSION}-{arm.lower()}-{item['conflict_id']}",
        task_kind=COORDINATOR_TASK_KIND,
        objective=objective,
        inputs={"arm": arm, "public_object": item, "local_role_receipts": role_input, "external_reference": "WITHHELD"},
        allowed_evidence=list(evidence_refs),
        expected_schema=coordinator_schema(item["conflict_id"], evidence_refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="retain_failed_arm_without_local_semantic_substitution",
    )
