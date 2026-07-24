"""Frozen axis-specific credibility routing experiment v0.17."""

from __future__ import annotations

from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .clarification_reference_first_roles import MODEL_IDS, ROLE_IDS
from .cognitive_action_axis_holdout import validate_axis_routing_holdout
from .cognitive_action_coordinator import (
    BASES,
    COMPLETENESS,
    SELECTIONS,
    coordinator_schema,
    validate_coordinator_payload,
)
from .cognitive_action_protocol import ActionCost, build_action_receipt, validate_action_receipt
from .grammar_backed_role_adapter import validate_grammar_output
from .provider_telemetry import hash_payload


AXIS_ROUTING_VERSION = "cognitive_action_axis_routing_v0_17"
AXIS_TASK_KIND = "COGNITIVE_ACTION_AXIS_ROUTING"
SOURCE_EVALUATION_HASH = "6fa8212586a802e43fe33786ec41d5d0f0634e1b8f57db98a27c6bdfa42e0496"
SOURCE_REFERENCE_HASH = "91b293376f111a5dff1fb09a4bb42025c1f4466754ec9c05168ba4fb1735bbfc"
TUPLE_ARMS = ("SINGLE_MODEL_BASELINE", "ROLE_INFORMED_COORDINATOR")
PRIMARY_AXES = ("selected_object", "selection_basis", "pragmatic_preference")


def build_axis_routing_preregistration(*, source_evaluation):
    if (
        source_evaluation.get("artifact_hash") != SOURCE_EVALUATION_HASH
        or source_evaluation.get("reference_hash") != SOURCE_REFERENCE_HASH
        or source_evaluation.get("collective_gain_status") != "MIXED_NO_NET_CELL_GAIN"
        or source_evaluation.get("anti_additive_gate") != "REJECT"
    ):
        raise ValueError("axis_routing_source_evaluation_invalid")
    baseline = source_evaluation["arm_metrics"]["SINGLE_MODEL_BASELINE"]["axis_correct"]
    coordinator = source_evaluation["arm_metrics"]["ROLE_INFORMED_COORDINATOR"]["axis_correct"]
    commitment = {
        "preregistration_version": AXIS_ROUTING_VERSION,
        "source_evaluation_hash": SOURCE_EVALUATION_HASH,
        "source_reference_hash": SOURCE_REFERENCE_HASH,
        "calibration_evidence_only": True,
        "source_axis_correct": {
            "SINGLE_MODEL_BASELINE": baseline,
            "ROLE_INFORMED_COORDINATOR": coordinator,
        },
        "frozen_axis_sources": {
            "selected_object": "SINGLE_MODEL_BASELINE",
            "selection_basis": "CONTRASTIVE_BASIS_CRITIC",
            "pragmatic_preference": "ROLE_INFORMED_COORDINATOR",
            "assessment_completeness": "LOCAL_ASSESSMENT_SKEPTIC_DESCRIPTIVE_ONLY",
        },
        "primary_axes": list(PRIMARY_AXES),
        "completeness_in_promotion_gate": False,
        "success_gate": {
            "minimum_primary_correct_cell_gain_over_baseline": 3,
            "maximum_selected_object_case_loss": 1,
            "minimum_preference_case_gain": 4,
            "minimum_basis_case_gain": 0,
            "corrections_must_exceed_harms": True,
            "maximum_tokens_per_net_primary_correct_cell": 40000,
        },
        "fresh_case_prompts_editable_after_hash_freeze": False,
        "reference_available_during_inference": False,
        "baseline_promotion_allowed_before_external_panel": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_axis_routing_preregistration(artifact, *, source_evaluation):
    expected = build_axis_routing_preregistration(source_evaluation=source_evaluation)
    if artifact != expected:
        raise ValueError("axis_routing_preregistration_invalid")


def build_axis_role_plan(*, corpus, preregistration, calibration_analysis):
    validate_axis_routing_holdout(corpus)
    if preregistration.get("preregistration_version") != AXIS_ROUTING_VERSION:
        raise ValueError("axis_routing_preregistration_missing")
    if not calibration_analysis.get("fresh_blind_collection_allowed"):
        raise ValueError("axis_routing_calibration_gate_closed")
    routing = calibration_analysis["selected_bijective_routing"]
    if set(routing) != set(ROLE_IDS) or set(routing.values()) != set(MODEL_IDS):
        raise ValueError("axis_routing_role_assignment_invalid")
    assignments = [
        {
            "conflict_id": item["conflict_id"],
            "role_id": role,
            "model_id": routing[role],
            "public_item_hash": hash_payload(item),
        }
        for item in corpus["public_surface"]["items"]
        for role in ROLE_IDS
    ]
    commitment = {
        "plan_version": AXIS_ROUTING_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_calibration_hash": calibration_analysis["artifact_hash"],
        "routing": routing,
        "assignments": assignments,
        "assignment_count": len(assignments),
        "routing_frozen_before_inference": True,
        "reference_available": False,
    }
    return {**commitment, "plan_hash": hash_payload(commitment)}


def run_axis_roles(*, corpus, plan, adapters):
    validate_axis_routing_holdout(corpus)
    adapter_index = {adapter.model_id: adapter for adapter in adapters}
    if set(adapter_index) != set(MODEL_IDS):
        raise ValueError("axis_routing_adapters_invalid")
    public = {item["conflict_id"]: item for item in corpus["public_surface"]["items"]}
    outputs, failures = [], []
    for assignment in plan["assignments"]:
        item = public[assignment["conflict_id"]]
        try:
            output = adapter_index[assignment["model_id"]].invoke(
                role_id=assignment["role_id"],
                item=item,
                evidence_refs=tuple(corpus["evidence_refs"]),
            )
            validate_grammar_output(output, item=item)
            outputs.append(output)
        except Exception as exc:
            failures.append({**assignment, "error_type": type(exc).__name__, "error": str(exc)})
    commitment = {
        "runtime_version": AXIS_ROUTING_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_plan_hash": plan["plan_hash"],
        "outputs": outputs,
        "failures": failures,
        "reference_available_during_inference": False,
        "candidate_outputs_frozen_before_external_reference": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_axis_roles(*, corpus, plan, run):
    validate_axis_role_run(corpus=corpus, plan=plan, run=run)
    role_counts, model_counts, accounting = Counter(), Counter(), Counter()
    for output in run["outputs"]:
        role_counts[output["role_id"]] += 1
        model_counts[output["model_id"]] += 1
        accounting.update(output["action_receipt"]["cost"])
    coverage = round(len(run["outputs"]) / plan["assignment_count"], 6)
    inference_allowed = coverage >= 0.95 and all(role_counts[role] >= 22 for role in ROLE_IDS)
    commitment = {
        "analysis_version": AXIS_ROUTING_VERSION,
        "source_run_hash": run["run_hash"],
        "strict_receipt_coverage": coverage,
        "role_counts": dict(role_counts),
        "model_counts": dict(model_counts),
        "accounting": dict(accounting),
        "tuple_inference_allowed": inference_allowed,
        "semantic_accuracy_available": False,
        "candidate_state": "AXIS_ROLE_RECEIPTS_FROZEN" if inference_allowed else "AXIS_ROLE_COLLECTION_INCOMPLETE",
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_axis_role_run(*, corpus, plan, run):
    commitment = {key: value for key, value in run.items() if key != "run_hash"}
    if (
        run.get("run_hash") != hash_payload(commitment)
        or run.get("source_corpus_hash") != corpus.get("artifact_hash")
        or run.get("source_plan_hash") != plan.get("plan_hash")
        or run.get("reference_available_during_inference") is not False
        or len(run.get("outputs", [])) + len(run.get("failures", [])) != plan.get("assignment_count")
    ):
        raise ValueError("axis_routing_role_run_invalid")
    observed = set()
    for output in run["outputs"]:
        validate_grammar_output(output)
        key = (output["object_ref"], output["role_id"])
        if key in observed:
            raise ValueError("axis_routing_role_run_duplicate")
        observed.add(key)


def run_axis_routing_arms(*, corpus, preregistration, role_run, role_analysis, adapter):
    validate_axis_routing_holdout(corpus)
    if preregistration.get("preregistration_version") != AXIS_ROUTING_VERSION:
        raise ValueError("axis_routing_preregistration_missing")
    if not role_analysis.get("tuple_inference_allowed"):
        raise ValueError("axis_routing_role_gate_closed")
    role_receipts = _index_role_receipts(role_run)
    tuple_outputs, basis_outputs, routed_outputs, failures = [], [], [], []
    for item in corpus["public_surface"]["items"]:
        conflict_id = item["conflict_id"]
        by_arm = {}
        order = TUPLE_ARMS if int(hash_payload([AXIS_ROUTING_VERSION, conflict_id])[:2], 16) % 2 == 0 else tuple(reversed(TUPLE_ARMS))
        for arm in order:
            outcome = _invoke_tuple(
                item=item,
                arm=arm,
                role_receipts=role_receipts[conflict_id],
                evidence_refs=tuple(corpus["evidence_refs"]),
                adapter=adapter,
            )
            if outcome.get("failure"):
                failures.append(outcome["failure"])
            else:
                tuple_outputs.append(outcome["output"])
                by_arm[arm] = outcome["output"]
        if set(by_arm) != set(TUPLE_ARMS):
            continue
        baseline = by_arm["SINGLE_MODEL_BASELINE"]
        coordinator = by_arm["ROLE_INFORMED_COORDINATOR"]
        basis_output = _resolve_basis(
            item=item,
            baseline_output=baseline,
            coordinator_output=coordinator,
            evidence_refs=tuple(corpus["evidence_refs"]),
            adapter=adapter,
        )
        if basis_output.get("failure"):
            failures.append(basis_output["failure"])
            continue
        basis_outputs.append(basis_output["output"])
        routed_outputs.append(
            _fuse_axes(
                item=item,
                baseline_output=baseline,
                coordinator_output=coordinator,
                basis_output=basis_output["output"],
                role_receipts=role_receipts[conflict_id],
                evidence_refs=tuple(corpus["evidence_refs"]),
                adapter=adapter,
            )
        )
    commitment = {
        "runtime_version": AXIS_ROUTING_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_role_run_hash": role_run["run_hash"],
        "source_role_analysis_hash": role_analysis["artifact_hash"],
        "tuple_outputs": tuple_outputs,
        "basis_outputs": basis_outputs,
        "routed_outputs": routed_outputs,
        "failures": failures,
        "tuple_arm_order_counterbalanced": True,
        "external_reference_available": False,
        "candidate_outputs_frozen_before_external_reference": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def recover_axis_routing_failures(*, corpus, preregistration, role_run, role_analysis, run, adapter):
    """Retry each structurally missing coordinator object once without changing its contract."""
    validate_axis_routing_holdout(corpus)
    validate_axis_routing_run(corpus=corpus, run=run)
    if preregistration.get("artifact_hash") != run.get("source_preregistration_hash"):
        raise ValueError("axis_routing_recovery_preregistration_mismatch")
    public = {item["conflict_id"]: item for item in corpus["public_surface"]["items"]}
    role_receipts = _index_role_receipts(role_run)
    tuple_outputs = list(run["tuple_outputs"])
    basis_outputs = list(run["basis_outputs"])
    routed_outputs = list(run["routed_outputs"])
    residual_failures, recovery_history = [], []
    tuple_index = {(output["arm"], output["conflict_id"]): output for output in tuple_outputs}
    for failure in run["failures"]:
        conflict_id, stage = failure.get("conflict_id"), failure.get("stage")
        if stage != "ROLE_INFORMED_COORDINATOR" or conflict_id not in public or ("SINGLE_MODEL_BASELINE", conflict_id) not in tuple_index:
            residual_failures.append(failure)
            continue
        outcome = _invoke_tuple(
            item=public[conflict_id],
            arm=stage,
            role_receipts=role_receipts[conflict_id],
            evidence_refs=tuple(corpus["evidence_refs"]),
            adapter=adapter,
        )
        history = {"original_failure": failure, "recovery_attempt_count": 1}
        if outcome.get("failure"):
            residual_failures.append(outcome["failure"])
            recovery_history.append({**history, "recovery_state": "FAILED", "recovery_failure": outcome["failure"]})
            continue
        coordinator = outcome["output"]
        baseline = tuple_index[("SINGLE_MODEL_BASELINE", conflict_id)]
        basis = _resolve_basis(
            item=public[conflict_id],
            baseline_output=baseline,
            coordinator_output=coordinator,
            evidence_refs=tuple(corpus["evidence_refs"]),
            adapter=adapter,
        )
        if basis.get("failure"):
            residual_failures.append(basis["failure"])
            recovery_history.append({**history, "recovery_state": "FAILED", "recovery_failure": basis["failure"]})
            continue
        routed = _fuse_axes(
            item=public[conflict_id],
            baseline_output=baseline,
            coordinator_output=coordinator,
            basis_output=basis["output"],
            role_receipts=role_receipts[conflict_id],
            evidence_refs=tuple(corpus["evidence_refs"]),
            adapter=adapter,
        )
        tuple_outputs.append(coordinator)
        basis_outputs.append(basis["output"])
        routed_outputs.append(routed)
        recovery_history.append({
            **history,
            "recovery_state": "RECOVERED_WITH_UNCHANGED_TASK_CONTRACT",
            "recovered_tuple_output_hash": coordinator["output_hash"],
            "recovered_basis_output_hash": basis["output"]["output_hash"],
            "recovered_routed_output_hash": routed["output_hash"],
        })
    commitment = {
        key: value for key, value in run.items()
        if key not in {"run_hash", "tuple_outputs", "basis_outputs", "routed_outputs", "failures", "recovery_history"}
    }
    commitment.update({
        "tuple_outputs": tuple_outputs,
        "basis_outputs": basis_outputs,
        "routed_outputs": routed_outputs,
        "failures": residual_failures,
        "recovery_history": recovery_history,
    })
    recovered = {**commitment, "run_hash": hash_payload(commitment)}
    validate_axis_routing_run(corpus=corpus, run=recovered)
    return recovered


def analyze_axis_routing_run(*, corpus, role_analysis, run):
    validate_axis_routing_run(corpus=corpus, run=run)
    tuple_index = {arm: {} for arm in TUPLE_ARMS}
    accounting = {arm: Counter() for arm in (*TUPLE_ARMS, "CONTRASTIVE_BASIS_CRITIC")}
    for output in run["tuple_outputs"]:
        tuple_index[output["arm"]][output["conflict_id"]] = output["payload"]
        accounting[output["arm"]].update(output["action_receipt"]["cost"])
    for output in run["basis_outputs"]:
        accounting["CONTRASTIVE_BASIS_CRITIC"].update(output["cost"])
    failed_accounting = Counter()
    failed_receipts = {}
    failure_records = list(run.get("failures", []))
    for history in run.get("recovery_history", []):
        failure_records.append(history.get("original_failure", {}))
        failure_records.append(history.get("recovery_failure", {}))
    for failure in failure_records:
        invocation = failure.get("invocation_receipt") or {}
        receipt_hash = invocation.get("receipt_hash")
        if receipt_hash:
            failed_receipts[receipt_hash] = invocation
    for invocation in failed_receipts.values():
        usage = invocation.get("token_usage") or {}
        failed_accounting.update({
            "provider_calls": int(usage.get("provider_calls") or 1),
            "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
            "latency_ms": int(usage.get("latency_ms") or 0),
        })
    routed = {output["conflict_id"]: output["payload"] for output in run["routed_outputs"]}
    common = set(routed) & set(tuple_index[TUPLE_ARMS[0]]) & set(tuple_index[TUPLE_ARMS[1]])
    axis_disagreements = {
        field: sum(tuple_index[TUPLE_ARMS[0]][case][field] != tuple_index[TUPLE_ARMS[1]][case][field] for case in common)
        for field in (*PRIMARY_AXES, "assessment_completeness")
    }
    baseline_cost = accounting["SINGLE_MODEL_BASELINE"]
    routed_path = Counter(role_analysis["accounting"])
    for arm in (*TUPLE_ARMS, "CONTRASTIVE_BASIS_CRITIC"):
        routed_path.update(accounting[arm])
    routed_path.update(failed_accounting)
    baseline_tokens = baseline_cost["input_tokens"] + baseline_cost["output_tokens"]
    routed_tokens = routed_path["input_tokens"] + routed_path["output_tokens"]
    common_coverage = len(common) / corpus["case_count"]
    if len(common) == corpus["case_count"]:
        candidate_state = "AXIS_ROUTED_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL"
    elif common_coverage >= 0.95:
        candidate_state = "AXIS_ROUTED_PARTIAL_ABOVE_COVERAGE_GATE_AWAITING_EXTERNAL_PANEL"
    else:
        candidate_state = "AXIS_ROUTING_INCOMPLETE"
    commitment = {
        "analysis_version": AXIS_ROUTING_VERSION,
        "source_run_hash": run["run_hash"],
        "coverage": {
            arm: round(len(tuple_index[arm]) / corpus["case_count"], 6) for arm in TUPLE_ARMS
        } | {"AXIS_ROUTED": round(len(routed) / corpus["case_count"], 6)},
        "common_case_count": len(common),
        "baseline_coordinator_axis_disagreements": axis_disagreements,
        "fusion_override_count": sum(bool(output["fusion_receipt"]["coherence_overrides"]) for output in run["routed_outputs"]),
        "basis_source_counts": dict(Counter(output["basis_source"] for output in run["basis_outputs"])),
        "accounting": {arm: dict(values) for arm, values in accounting.items()},
        "failed_invocation_accounting": dict(failed_accounting),
        "failed_invocation_receipt_count": len(failed_receipts),
        "local_role_accounting": role_analysis["accounting"],
        "routed_path_accounting": dict(routed_path),
        "baseline_total_tokens": baseline_tokens,
        "routed_path_total_tokens": routed_tokens,
        "routed_to_baseline_token_ratio": round(routed_tokens / baseline_tokens, 6) if baseline_tokens else None,
        "semantic_accuracy_available": False,
        "collective_gain_claim_allowed": False,
        "external_panel_required": True,
        "candidate_state": candidate_state,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_axis_routing_run(*, corpus, run):
    commitment = {key: value for key, value in run.items() if key != "run_hash"}
    if (
        run.get("run_hash") != hash_payload(commitment)
        or run.get("source_corpus_hash") != corpus.get("artifact_hash")
        or run.get("external_reference_available") is not False
    ):
        raise ValueError("axis_routing_run_invalid")
    seen = set()
    for output in run.get("tuple_outputs", []):
        key = (output.get("arm"), output.get("conflict_id"))
        if key in seen:
            raise ValueError("axis_routing_tuple_duplicate")
        seen.add(key)
        validate_coordinator_payload(output["payload"], conflict_id=output["conflict_id"], evidence_refs=tuple(corpus["evidence_refs"]))
        validate_action_receipt(output["action_receipt"])
        _validate_hash(output, "output_hash")
    for output in run.get("basis_outputs", []):
        _validate_hash(output, "output_hash")
        if output.get("selection_basis") not in BASES or output.get("selected_object") not in SELECTIONS:
            raise ValueError("axis_routing_basis_output_invalid")
        if output.get("action_receipt") is not None:
            validate_action_receipt(output["action_receipt"])
    for output in run.get("routed_outputs", []):
        _validate_hash(output, "output_hash")
        validate_coordinator_payload(output["payload"], conflict_id=output["conflict_id"], evidence_refs=tuple(corpus["evidence_refs"]))
        validate_action_receipt(output["action_receipt"])


def build_axis_external_annotation_pack(*, corpus, run):
    validate_axis_routing_holdout(corpus)
    validate_axis_routing_run(corpus=corpus, run=run)
    commitment = {
        "pack_version": "cognitive_action_axis_external_annotation_pack_v0_17",
        "source_corpus_hash": corpus["artifact_hash"],
        "frozen_candidate_run_hash_commitment": run["run_hash"],
        "instructions": {
            "task": "Independently label each public object as one coherent full semantic tuple.",
            "criteria": ["SELECTED_OBJECT", "SELECTION_BASIS", "PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE"],
            "selected_values": list(SELECTIONS),
            "basis_values": list(BASES),
            "completeness_values": list(COMPLETENESS),
            "basis_definitions": {
                "LEXICAL_EXACT": "The prompt directly names or explicitly defines the selected candidate.",
                "COMPOSITIONAL_ENTAILMENT": "The selected candidate follows from combining prompt constraints without an exact definition.",
                "PRAGMATIC_DEFAULT": "Neither candidate is entailed, but ordinary context favors one; selected object must be NONE.",
                "NO_PREFERENCE": "Neither candidate is entailed or contextually favored; selected object and preference must be NONE.",
                "UNCERTAIN": "The displayed surface is internally conflicting or too incomplete to classify the relation.",
            },
            "important": "A justified open result can be COMPLETE. Candidate outputs are withheld and must not be inferred.",
        },
        "public_items": corpus["public_surface"]["items"],
        "candidate_outputs_exposed": False,
        "construction_truth_exposed": False,
        "ground_truth_claim": False,
    }
    return {**commitment, "pack_hash": hash_payload(commitment)}


def _invoke_tuple(*, item, arm, role_receipts, evidence_refs, adapter):
    task = _tuple_task(item=item, arm=arm, role_receipts=role_receipts, evidence_refs=evidence_refs, adapter=adapter)
    envelope = ProviderTaskRouter([adapter]).route(task)
    invocation = envelope.invocation_receipt.as_dict()
    if envelope.status != "COMPLETED":
        return {"failure": {"stage": arm, "conflict_id": item["conflict_id"], "status": envelope.status, "validation_errors": list(envelope.validation_errors), "invocation_receipt": invocation}}
    try:
        validate_coordinator_payload(envelope.normalized_result, conflict_id=item["conflict_id"], evidence_refs=evidence_refs)
    except ValueError as exc:
        return {"failure": {"stage": arm, "conflict_id": item["conflict_id"], "status": "SEMANTIC_VALIDATION_FAILED", "validation_errors": [str(exc)], "payload": envelope.normalized_result, "invocation_receipt": invocation}}
    payload = envelope.normalized_result
    usage = invocation.get("token_usage") or {}
    receipt = build_action_receipt(
        action_id="action-" + hash_payload([AXIS_ROUTING_VERSION, arm, item["conflict_id"]])[:18],
        action_type="SYNTHESIZE",
        object_ref="object://" + item["conflict_id"],
        actor_role="COORDINATOR",
        actor_instance=f"{adapter.profile.model_id}:{arm}",
        method=AXIS_ROUTING_VERSION,
        result_state="CANDIDATE",
        result={key: payload[key] for key in ("selected_object", "selection_basis", "pragmatic_preference", "assessment_completeness", "action")},
        input_claim_refs=tuple(receipt["receipt_hash"] for receipt in role_receipts) if arm == "ROLE_INFORMED_COORDINATOR" else (),
        evidence_refs=evidence_refs,
        support=(payload["rationale"],),
        uncertainty=round(1 - payload["confidence"], 6),
        recommended_next_actions=("CLARIFY",) if payload["action"] == "CLARIFY" else ("ABSTAIN",) if payload["action"] == "ABSTAIN" else ("FALSIFY",),
        cost=_usage_cost(usage),
    )
    output_commitment = {
        "arm": arm,
        "conflict_id": item["conflict_id"],
        "payload": payload,
        "action_receipt": receipt,
        "invocation_receipt": invocation,
        "task_contract_hash": task.contract_hash(),
        "reference_available": False,
    }
    return {"output": {**output_commitment, "output_hash": hash_payload(output_commitment)}}


def _resolve_basis(*, item, baseline_output, coordinator_output, evidence_refs, adapter):
    selected = baseline_output["payload"]["selected_object"]
    preference = coordinator_output["payload"]["pragmatic_preference"]
    if selected in ("CANDIDATE_A", "CANDIDATE_B"):
        task = _basis_task(item=item, selected=selected, evidence_refs=evidence_refs, adapter=adapter)
        envelope = ProviderTaskRouter([adapter]).route(task)
        invocation = envelope.invocation_receipt.as_dict()
        if envelope.status != "COMPLETED":
            return {"failure": {"stage": "CONTRASTIVE_BASIS_CRITIC", "conflict_id": item["conflict_id"], "status": envelope.status, "validation_errors": list(envelope.validation_errors), "invocation_receipt": invocation}}
        payload = envelope.normalized_result
        if not _valid_basis_payload(payload, conflict_id=item["conflict_id"], selected=selected, evidence_refs=evidence_refs):
            return {"failure": {"stage": "CONTRASTIVE_BASIS_CRITIC", "conflict_id": item["conflict_id"], "status": "SEMANTIC_VALIDATION_FAILED", "payload": payload, "invocation_receipt": invocation}}
        usage = invocation.get("token_usage") or {}
        receipt = build_action_receipt(
            action_id="action-" + hash_payload([AXIS_ROUTING_VERSION, "basis", item["conflict_id"]])[:18],
            action_type="ADJUDICATE",
            object_ref="object://" + item["conflict_id"],
            actor_role="ADJUDICATOR",
            actor_instance=f"{adapter.profile.model_id}:CONTRASTIVE_BASIS_CRITIC",
            method=AXIS_ROUTING_VERSION,
            result_state="CANDIDATE",
            result={"selected_object": selected, "selection_basis": payload["selection_basis"]},
            input_claim_refs=(baseline_output["action_receipt"]["receipt_hash"],),
            evidence_refs=evidence_refs,
            support=(payload["rationale"],),
            uncertainty=round(1 - payload["confidence"], 6),
            recommended_next_actions=("SYNTHESIZE",),
            cost=_usage_cost(usage),
        )
        commitment = {
            "conflict_id": item["conflict_id"],
            "selected_object": selected,
            "selection_basis": payload["selection_basis"],
            "basis_source": "CONTRASTIVE_BASIS_CRITIC",
            "rationale": payload["rationale"],
            "confidence": payload["confidence"],
            "cost": receipt["cost"],
            "action_receipt": receipt,
            "invocation_receipt": invocation,
            "reference_available": False,
        }
        return {"output": {**commitment, "output_hash": hash_payload(commitment)}}
    if selected == "NONE" and preference in ("CANDIDATE_A", "CANDIDATE_B"):
        basis = "PRAGMATIC_DEFAULT"
    elif selected == "NONE":
        basis = "NO_PREFERENCE"
    else:
        basis = "UNCERTAIN"
    commitment = {
        "conflict_id": item["conflict_id"],
        "selected_object": selected,
        "selection_basis": basis,
        "basis_source": "MECHANICAL_COHERENCE_DERIVATION",
        "rationale": "Basis mechanically follows the frozen selected-object and preference states.",
        "confidence": 1.0,
        "cost": {"provider_calls": 0, "input_tokens": 0, "output_tokens": 0, "latency_ms": 0},
        "action_receipt": None,
        "invocation_receipt": None,
        "reference_available": False,
    }
    return {"output": {**commitment, "output_hash": hash_payload(commitment)}}


def _fuse_axes(*, item, baseline_output, coordinator_output, basis_output, role_receipts, evidence_refs, adapter):
    selected = baseline_output["payload"]["selected_object"]
    basis = basis_output["selection_basis"]
    preference = coordinator_output["payload"]["pragmatic_preference"]
    skeptic = next(receipt for receipt in role_receipts if receipt["actor_role"] == "ASSESSMENT_SKEPTIC")
    completeness = skeptic["result"]["assessment_completeness"]
    overrides = []
    if selected == "UNCERTAIN":
        if basis != "UNCERTAIN" or preference != "UNCERTAIN":
            overrides.append("UNCERTAIN_OBJECT_FORCES_UNCERTAIN_BASIS_AND_PREFERENCE")
        basis, preference = "UNCERTAIN", "UNCERTAIN"
    elif selected == "NONE" and preference == "UNCERTAIN":
        overrides.append("NONE_PLUS_UNCERTAIN_PREFERENCE_FAILS_CLOSED_TO_UNCERTAIN_TUPLE")
        selected, basis, preference = "UNCERTAIN", "UNCERTAIN", "UNCERTAIN"
    action = "ACCEPT" if selected in ("CANDIDATE_A", "CANDIDATE_B") and completeness == "COMPLETE" else "CLARIFY"
    payload = {
        "conflict_id": item["conflict_id"],
        "selected_object": selected,
        "selection_basis": basis,
        "pragmatic_preference": preference,
        "assessment_completeness": completeness,
        "action": action,
        "rationale": "Runtime assembled each axis from its preregistered source and applied only explicit tuple-coherence rules.",
        "confidence": min(
            baseline_output["payload"]["confidence"],
            coordinator_output["payload"]["confidence"],
            basis_output["confidence"],
            round(1 - skeptic["uncertainty"], 6),
        ),
        "evidence_refs": list(evidence_refs),
    }
    validate_coordinator_payload(payload, conflict_id=item["conflict_id"], evidence_refs=evidence_refs)
    input_refs = [
        baseline_output["action_receipt"]["receipt_hash"],
        coordinator_output["action_receipt"]["receipt_hash"],
        skeptic["receipt_hash"],
    ]
    if basis_output["action_receipt"]:
        input_refs.append(basis_output["action_receipt"]["receipt_hash"])
    receipt = build_action_receipt(
        action_id="action-" + hash_payload([AXIS_ROUTING_VERSION, "fuse", item["conflict_id"]])[:18],
        action_type="SYNTHESIZE",
        object_ref="object://" + item["conflict_id"],
        actor_role="COORDINATOR",
        actor_instance="runtime-axis-credibility-router",
        method=AXIS_ROUTING_VERSION,
        result_state="CANDIDATE",
        result={key: payload[key] for key in ("selected_object", "selection_basis", "pragmatic_preference", "assessment_completeness", "action")},
        input_claim_refs=tuple(input_refs),
        evidence_refs=evidence_refs,
        support=(payload["rationale"],),
        uncertainty=round(1 - payload["confidence"], 6),
        failure_boundary=";".join(overrides),
        recommended_next_actions=("FALSIFY",) if action == "ACCEPT" else ("CLARIFY",),
        cost=ActionCost(),
    )
    fusion_receipt = {
        "selected_object_source": "SINGLE_MODEL_BASELINE",
        "selection_basis_source": basis_output["basis_source"],
        "pragmatic_preference_source": "ROLE_INFORMED_COORDINATOR",
        "assessment_completeness_source": "LOCAL_ASSESSMENT_SKEPTIC_DESCRIPTIVE_ONLY",
        "coherence_overrides": overrides,
        "semantic_inference_performed_by_runtime": False,
    }
    commitment = {
        "arm": "AXIS_ROUTED",
        "conflict_id": item["conflict_id"],
        "payload": payload,
        "fusion_receipt": fusion_receipt,
        "action_receipt": receipt,
        "reference_available": False,
    }
    return {**commitment, "output_hash": hash_payload(commitment)}


def _tuple_task(*, item, arm, role_receipts, evidence_refs, adapter):
    role_input = [
        {
            "role": receipt["actor_role"],
            "model": receipt["actor_instance"],
            "result": receipt["result"],
            "uncertainty": receipt["uncertainty"],
            "receipt_hash": receipt["receipt_hash"],
        }
        for receipt in role_receipts
    ] if arm == "ROLE_INFORMED_COORDINATOR" else "WITHHELD_FOR_SINGLE_MODEL_BASELINE"
    objective = (
        "Return one coherent full semantic tuple. Separate what the prompt entails from what context merely favors. "
        "LEXICAL_EXACT or COMPOSITIONAL_ENTAILMENT requires selected A or B. PRAGMATIC_DEFAULT requires selected NONE and preference A or B. "
        "NO_PREFERENCE requires selected NONE and preference NONE. A justified open result may be COMPLETE. "
        + ("Treat local role receipts as fallible evidence and resolve conflicts without voting." if arm == "ROLE_INFORMED_COORDINATOR" else "Reason directly from the public object without role receipts.")
    )
    return ProviderCognitiveTask(
        task_id=f"{AXIS_ROUTING_VERSION}-{arm.lower()}-{item['conflict_id']}",
        task_kind=AXIS_TASK_KIND,
        objective=objective,
        inputs={"arm": arm, "public_object": item, "local_role_receipts": role_input, "external_reference": "WITHHELD"},
        allowed_evidence=list(evidence_refs),
        expected_schema=coordinator_schema(item["conflict_id"], evidence_refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="retain_failed_arm_without_local_semantic_substitution",
    )


def _basis_task(*, item, selected, evidence_refs, adapter):
    return ProviderCognitiveTask(
        task_id=f"{AXIS_ROUTING_VERSION}-basis-{item['conflict_id']}",
        task_kind=AXIS_TASK_KIND,
        objective=(
            "The selected object is already frozen. Classify only why the public prompt supports it. "
            "Choose LEXICAL_EXACT when the request directly names or explicitly defines the candidate. "
            "Choose COMPOSITIONAL_ENTAILMENT when support follows by combining constraints without an exact definition. "
            "Do not reconsider the selected object and do not use pragmatic preference."
        ),
        inputs={"public_object": item, "frozen_selected_object": selected, "external_reference": "WITHHELD"},
        allowed_evidence=list(evidence_refs),
        expected_schema=_basis_schema(item["conflict_id"], selected, evidence_refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="fail_closed_without_basis_substitution",
    )


def _basis_schema(conflict_id, selected, evidence_refs):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["conflict_id", "selected_object", "selection_basis", "rationale", "confidence", "evidence_refs"],
        "properties": {
            "conflict_id": {"type": "string", "enum": [conflict_id]},
            "selected_object": {"type": "string", "enum": [selected]},
            "selection_basis": {"type": "string", "enum": ["LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT"]},
            "rationale": {"type": "string", "minLength": 1, "maxLength": 800},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence_refs": {"type": "array", "minItems": len(evidence_refs), "maxItems": len(evidence_refs), "items": {"type": "string", "enum": list(evidence_refs)}},
        },
    }


def _valid_basis_payload(payload, *, conflict_id, selected, evidence_refs):
    return (
        isinstance(payload, dict)
        and set(payload) == set(_basis_schema(conflict_id, selected, evidence_refs)["required"])
        and payload.get("conflict_id") == conflict_id
        and payload.get("selected_object") == selected
        and payload.get("selection_basis") in ("LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT")
        and isinstance(payload.get("rationale"), str)
        and bool(payload["rationale"].strip())
        and isinstance(payload.get("confidence"), (int, float))
        and not isinstance(payload.get("confidence"), bool)
        and 0 <= payload["confidence"] <= 1
        and payload.get("evidence_refs") == list(evidence_refs)
    )


def _index_role_receipts(role_run):
    index = {}
    for output in role_run["outputs"]:
        conflict_id = output["object_ref"].removeprefix("object://")
        index.setdefault(conflict_id, []).append(output["action_receipt"])
    for conflict_id, receipts in index.items():
        receipts.sort(key=lambda receipt: receipt["actor_role"])
        if len(receipts) != 3:
            raise ValueError(f"axis_routing_role_receipts_incomplete:{conflict_id}")
    return index


def _usage_cost(usage):
    return ActionCost(
        provider_calls=max(1, int(usage.get("provider_calls") or 1)),
        input_tokens=int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        latency_ms=int(usage.get("latency_ms") or 0),
    )


def _validate_hash(value, hash_field):
    commitment = {key: item for key, item in value.items() if key != hash_field}
    if value.get(hash_field) != hash_payload(commitment):
        raise ValueError("axis_routing_output_hash_invalid")
