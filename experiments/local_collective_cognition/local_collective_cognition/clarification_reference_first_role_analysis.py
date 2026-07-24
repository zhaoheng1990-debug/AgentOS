"""Post-freeze quality and work accounting for local specialist receipts v0.15."""

from __future__ import annotations

from collections import Counter, defaultdict

from .clarification_reference_first_holdout import validate_reference_first_holdout
from .clarification_reference_first_panel import validate_reference_first_reference
from .clarification_reference_first_role_runtime import validate_specialist_role_run
from .clarification_reference_first_roles import ROLE_IDS, validate_specialist_role_plan
from .provider_telemetry import hash_payload


ANALYSIS_VERSION = "clarification_reference_first_role_analysis_v0_15"


def build_specialist_role_analysis(*, corpus_artifact, frozen_reference, role_plan, role_run):
    validate_reference_first_holdout(corpus_artifact)
    validate_reference_first_reference(frozen_reference)
    validate_specialist_role_plan(role_plan)
    validate_specialist_role_run(role_run, corpus_artifact=corpus_artifact, role_plan=role_plan)
    if role_plan["frozen_reference_hash"] != frozen_reference["artifact_hash"]:
        raise ValueError("specialist_role_analysis_reference_mismatch")
    reference = {label["conflict_id"]: label["criteria"] for label in frozen_reference["labels"]}
    provenance = corpus_artifact["private_provenance"]["bindings"]
    metric_counts = defaultdict(lambda: Counter(total=0, correct=0))
    role_counts = defaultdict(lambda: Counter(total=0, correct=0))
    family_counts = defaultdict(lambda: Counter(total=0, correct=0))
    confidence = defaultdict(list)
    rows = []
    for receipt in role_run["receipts"]:
        model_id, role_id = receipt["model_id"], receipt["role_id"]
        for decision in receipt["payload"]["decisions"]:
            conflict_id = decision["conflict_id"]
            truth = reference[conflict_id]
            if role_id == "OBJECT_GROUNDING":
                metrics = {
                    "SELECTED_OBJECT": decision["selected_object"] == truth["SELECTED_OBJECT"],
                    "SELECTION_BASIS": decision["selection_basis"] == truth["SELECTION_BASIS"],
                    "OBJECT_BASIS_PAIR": decision["selected_object"] == truth["SELECTED_OBJECT"] and decision["selection_basis"] == truth["SELECTION_BASIS"],
                }
            elif role_id == "PRAGMATIC_DEFAULT":
                metrics = {"PRAGMATIC_PREFERENCE": decision["pragmatic_preference"] == truth["PRAGMATIC_PREFERENCE"]}
            else:
                metrics = {"AXIS_ASSESSMENT_COMPLETE": decision["assessment_completeness"] == truth["AXIS_ASSESSMENT_COMPLETE"]}
            for metric, correct in metrics.items():
                metric_counts[(model_id, role_id, metric)]["total"] += 1
                metric_counts[(model_id, role_id, metric)]["correct"] += int(correct)
            primary_correct = all(metrics.values())
            role_counts[role_id]["total"] += 1
            role_counts[role_id]["correct"] += int(primary_correct)
            family = provenance[conflict_id]["object_family"]
            family_counts[(role_id, family)]["total"] += 1
            family_counts[(role_id, family)]["correct"] += int(primary_correct)
            confidence[(model_id, role_id)].append(decision["confidence"])
            rows.append({
                "conflict_id": conflict_id,
                "case_id": provenance[conflict_id]["case_id"],
                "object_family": family,
                "model_id": model_id,
                "role_id": role_id,
                "metrics": metrics,
                "primary_correct": primary_correct,
                "confidence": decision["confidence"],
                "decision_hash": hash_payload(decision),
            })
    expected_decisions = role_plan["assignment_count"]
    observed_decisions = len(rows)
    complete = observed_decisions == expected_decisions and not role_run["failures"]
    model_role_metrics = {}
    for (model_id, role_id, metric), counts in sorted(metric_counts.items()):
        model_role_metrics.setdefault(model_id, {}).setdefault(role_id, {})[metric] = {
            "correct": counts["correct"],
            "total": counts["total"],
            "accuracy": counts["correct"] / counts["total"],
        }
    role_metrics = {role: {"correct": counts["correct"], "total": counts["total"], "accuracy": counts["correct"] / counts["total"] if counts["total"] else 0.0} for role, counts in sorted(role_counts.items())}
    family_metrics = {f"{role}:{family}": {"correct": counts["correct"], "total": counts["total"], "accuracy": counts["correct"] / counts["total"] if counts["total"] else 0.0} for (role, family), counts in sorted(family_counts.items())}
    observations = [
        f"Local specialists produced {observed_decisions}/{expected_decisions} assigned role decisions across {len(role_run['receipts'])} completed batches; failed batches: {len(role_run['failures'])}.",
        "Role accuracies are " + ", ".join(f"{role} {role_metrics.get(role, {}).get('accuracy', 0.0):.3f}" for role in ROLE_IDS) + ".",
        f"Collection used {role_run['accounting']['provider_calls']} Provider calls, {role_run['accounting']['input_tokens']} input tokens, and {role_run['accounting']['output_tokens']} output tokens.",
    ]
    interpretations = [
        "Latin rotation prevents a single model identity from being identical to a cognitive role, enabling later model-versus-role decomposition.",
        "Role scores describe isolated specialist evidence, not a complete semantic tuple and not coordinator performance.",
        "Only the coordinator can test whether combining partial role evidence yields positive Cbit after communication cost.",
    ]
    unknowns = [
        "The completeness role is evaluated on a reference containing only COMPLETE objects, so its apparent accuracy may be a trivial-base-rate effect.",
        "No coordinator correction, harm, or token efficiency can be measured until these receipts are frozen and integrated.",
        "The model-panel reference remains candidate evidence rather than external ground truth.",
    ]
    intuition_triggers = [
        "A weak model may still be useful if its assigned role extracts a complementary axis reliably enough for a stronger integrator.",
        "Role specialization should be credited on marginal correction after integration, not isolated axis accuracy alone.",
        "Rotation data can reveal whether a role is intrinsically difficult or merely mismatched to one model family.",
    ]
    commitment = {
        "analysis_version": ANALYSIS_VERSION,
        "source_corpus_hash": corpus_artifact["artifact_hash"],
        "frozen_reference_hash": frozen_reference["artifact_hash"],
        "role_plan_hash": role_plan["plan_hash"],
        "role_run_hash": role_run["run_hash"],
        "expected_decision_count": expected_decisions,
        "observed_decision_count": observed_decisions,
        "failed_batch_count": len(role_run["failures"]),
        "receipt_coverage": observed_decisions / expected_decisions,
        "model_role_metrics": model_role_metrics,
        "role_metrics": role_metrics,
        "family_role_metrics": family_metrics,
        "mean_confidence_by_model_role": {f"{model}:{role}": sum(values) / len(values) for (model, role), values in sorted(confidence.items())},
        "accounting": role_run["accounting"],
        "rows": sorted(rows, key=lambda item: (item["case_id"], item["role_id"])),
        "observations": observations,
        "interpretations": interpretations,
        "unknowns": unknowns,
        "intuition_triggers": intuition_triggers,
        "next_required_evidence": "DEEPSEEK_COORDINATOR_ON_FROZEN_SPECIALIST_RECEIPTS" if complete else "LOCAL_SPECIALIST_RECEIPT_RECOVERY",
        "candidate_state": "LOCAL_SPECIALIST_RECEIPTS_FROZEN" if complete else "LOCAL_SPECIALIST_RECEIPTS_INCOMPLETE",
        "reference_available_to_roles": False,
        "local_role_receipts_frozen": complete,
        "coordinator_run_allowed": complete,
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_specialist_role_analysis(artifact, *, corpus_artifact, frozen_reference, role_plan, role_run):
    expected = build_specialist_role_analysis(
        corpus_artifact=corpus_artifact,
        frozen_reference=frozen_reference,
        role_plan=role_plan,
        role_run=role_run,
    )
    if artifact != expected:
        raise ValueError("specialist_role_analysis_invalid")


def render_specialist_role_analysis(analysis):
    lines = ["# Reference-First Local Specialist Roles v0.15 Analysis", ""]
    for title, key in (("Observations", "observations"), ("Interpretations", "interpretations"), ("Unknowns", "unknowns"), ("Intuition Triggers", "intuition_triggers")):
        lines.extend((f"## {title}", ""))
        lines.extend(f"- {value}" for value in analysis[key])
        lines.append("")
    lines.extend((f"Next evidence: `{analysis['next_required_evidence']}`", f"State: `{analysis['candidate_state']}`", f"Artifact hash: `{analysis['artifact_hash']}`", ""))
    return "\n".join(lines)


def build_specialist_recovery_analysis(
    *, corpus_artifact, frozen_reference, role_plan, initial_run, recovery_plan, recovery_run
):
    from .clarification_reference_first_role_recovery import (
        validate_specialist_recovery_plan,
        validate_specialist_recovery_run,
    )

    validate_reference_first_holdout(corpus_artifact)
    validate_reference_first_reference(frozen_reference)
    validate_specialist_role_plan(role_plan)
    validate_specialist_role_run(initial_run, corpus_artifact=corpus_artifact, role_plan=role_plan)
    validate_specialist_recovery_plan(recovery_plan, role_plan=role_plan, failed_run=initial_run)
    validate_specialist_recovery_run(recovery_run, recovery_plan=recovery_plan)
    reference = {label["conflict_id"]: label["criteria"] for label in frozen_reference["labels"]}
    provenance = corpus_artifact["private_provenance"]["bindings"]
    task_index = {item["recovery_task_id"]: item for item in recovery_plan["tasks"]}
    structural = defaultdict(lambda: Counter(total=0, success=0))
    semantic = defaultdict(lambda: Counter(total=0, correct=0))
    role_semantic = defaultdict(lambda: Counter(total=0, correct=0))
    rows = []
    for task in recovery_plan["tasks"]:
        structural[(task["model_id"], task["role_id"])]["total"] += 1
    for output in recovery_run["outputs"]:
        task = task_index[output["recovery_task_id"]]
        model_id, role_id = task["model_id"], task["role_id"]
        structural[(model_id, role_id)]["success"] += 1
        payload = output["payload"]
        truth = reference[payload["conflict_id"]]
        if role_id == "OBJECT_GROUNDING":
            metrics = {
                "SELECTED_OBJECT": payload["selected_object"] == truth["SELECTED_OBJECT"],
                "SELECTION_BASIS": payload["selection_basis"] == truth["SELECTION_BASIS"],
                "OBJECT_BASIS_PAIR": payload["selected_object"] == truth["SELECTED_OBJECT"] and payload["selection_basis"] == truth["SELECTION_BASIS"],
            }
        elif role_id == "PRAGMATIC_DEFAULT":
            metrics = {"PRAGMATIC_PREFERENCE": payload["pragmatic_preference"] == truth["PRAGMATIC_PREFERENCE"]}
        else:
            metrics = {"AXIS_ASSESSMENT_COMPLETE": payload["assessment_completeness"] == truth["AXIS_ASSESSMENT_COMPLETE"]}
        for metric, correct in metrics.items():
            semantic[(model_id, role_id, metric)]["total"] += 1
            semantic[(model_id, role_id, metric)]["correct"] += int(correct)
        primary_correct = all(metrics.values())
        role_semantic[role_id]["total"] += 1
        role_semantic[role_id]["correct"] += int(primary_correct)
        rows.append({
            "recovery_task_id": output["recovery_task_id"],
            "conflict_id": payload["conflict_id"],
            "case_id": provenance[payload["conflict_id"]]["case_id"],
            "object_family": provenance[payload["conflict_id"]]["object_family"],
            "model_id": model_id,
            "role_id": role_id,
            "metrics": metrics,
            "primary_correct": primary_correct,
            "confidence": payload["confidence"],
            "payload_hash": hash_payload(payload),
        })
    structural_metrics = {}
    for (model_id, role_id), counts in sorted(structural.items()):
        structural_metrics.setdefault(model_id, {})[role_id] = {
            "success": counts["success"],
            "total": counts["total"],
            "success_rate": counts["success"] / counts["total"],
        }
    semantic_metrics = {}
    for (model_id, role_id, metric), counts in sorted(semantic.items()):
        semantic_metrics.setdefault(model_id, {}).setdefault(role_id, {})[metric] = {
            "correct": counts["correct"],
            "total": counts["total"],
            "accuracy": counts["correct"] / counts["total"],
        }
    role_metrics = {
        role_id: {
            "correct": counts["correct"],
            "total": counts["total"],
            "accuracy": counts["correct"] / counts["total"] if counts["total"] else 0.0,
        }
        for role_id, counts in sorted(role_semantic.items())
    }
    total_work = {key: initial_run["accounting"][key] + recovery_run["accounting"][key] for key in ("provider_calls", "input_tokens", "output_tokens")}
    total_work["latency_ms"] = sum(
        int(item["invocation_receipt"].get("token_usage", {}).get("latency_ms") or 0)
        for item in (*initial_run["receipts"], *initial_run["failures"], *recovery_run["outputs"], *recovery_run["failures"])
    )
    accepted = len(rows)
    expected = role_plan["assignment_count"]
    complete = accepted == expected and not recovery_run["failures"]
    observations = [
        f"The four-object contract produced 0/{expected} accepted decisions; flat one-object recovery produced {accepted}/{expected} strict assignment-level receipts.",
        f"Structural success by model is Qwen {sum(value['success'] for value in structural_metrics.get('qwen2.5-1.5b-instruct', {}).values())}/24, Gemma {sum(value['success'] for value in structural_metrics.get('gemma-2-2b-it', {}).values())}/24, and Llama {sum(value['success'] for value in structural_metrics.get('llama-3.2-1b-instruct', {}).values())}/24.",
        f"Total work including the failed first contract is {total_work['provider_calls']} Provider calls and {total_work['input_tokens'] + total_work['output_tokens']} tokens, or {(total_work['input_tokens'] + total_work['output_tokens']) / accepted:.1f} tokens per accepted role receipt.",
        "Semantic accuracy among structurally valid receipts is " + ", ".join(f"{role} {role_metrics.get(role, {}).get('accuracy', 0.0):.3f}" for role in ROLE_IDS) + ".",
    ]
    interpretations = [
        "Contract complexity, not CUDA availability, is the first bottleneck: flattening raises strict structural coverage from zero to a partial but still insufficient level.",
        "Qwen can usually follow flat role contracts, Gemma is role-sensitive, and Llama 1B fails the structured protocol entirely in this setting.",
        "Partial semantic scores are selection-biased by structural success and cannot be treated as fair model rankings or coordinator-ready evidence.",
        "The communication and recovery overhead currently dominates any possible collective Cbit gain, so another prompt-only retry is not justified.",
    ]
    unknowns = [
        "No conclusion can be drawn about Llama's semantic competence because it produced no structurally valid receipt.",
        "The completeness score is degenerate because the frozen reference contains only COMPLETE objects.",
        "Whether a constrained decoder or grammar-backed local adapter can recover coverage at lower cost remains untested.",
    ]
    intuition_triggers = [
        "For very small models, the Harness may need to compile rich cognitive contracts into model-specific minimal grammars while preserving one canonical receipt schema.",
        "Role specialization helps only after protocol obedience is cheap enough; organizational intelligence cannot emerge when communication syntax consumes the budget.",
        "Structural reliability should be modeled as a first-class capability envelope, separate from semantic role quality.",
    ]
    commitment = {
        "analysis_version": "clarification_reference_first_role_recovery_analysis_v0_15",
        "source_corpus_hash": corpus_artifact["artifact_hash"],
        "frozen_reference_hash": frozen_reference["artifact_hash"],
        "role_plan_hash": role_plan["plan_hash"],
        "initial_run_hash": initial_run["run_hash"],
        "recovery_plan_hash": recovery_plan["plan_hash"],
        "recovery_run_hash": recovery_run["run_hash"],
        "expected_decision_count": expected,
        "accepted_decision_count": accepted,
        "strict_receipt_coverage": accepted / expected,
        "structural_metrics_by_model_role": structural_metrics,
        "semantic_metrics_by_model_role": semantic_metrics,
        "role_metrics_on_structurally_valid_receipts": role_metrics,
        "total_accounting": total_work,
        "tokens_per_accepted_receipt": (total_work["input_tokens"] + total_work["output_tokens"]) / accepted if accepted else None,
        "rows": sorted(rows, key=lambda item: (item["case_id"], item["role_id"])),
        "observations": observations,
        "interpretations": interpretations,
        "unknowns": unknowns,
        "intuition_triggers": intuition_triggers,
        "next_required_evidence": "DEEPSEEK_COORDINATOR_ON_FROZEN_SPECIALIST_RECEIPTS" if complete else "GRAMMAR_BACKED_LOCAL_ROLE_ADAPTER_CALIBRATION",
        "candidate_state": "LOCAL_SPECIALIST_RECEIPTS_FROZEN" if complete else "LOCAL_SPECIALIST_PROTOCOL_BOTTLENECK_CONFIRMED",
        "local_role_receipts_frozen": complete,
        "coordinator_run_allowed": complete,
        "further_prompt_only_recovery_allowed": False,
        "reference_available_to_roles": False,
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_specialist_recovery_analysis(
    artifact, *, corpus_artifact, frozen_reference, role_plan, initial_run, recovery_plan, recovery_run
):
    expected = build_specialist_recovery_analysis(
        corpus_artifact=corpus_artifact,
        frozen_reference=frozen_reference,
        role_plan=role_plan,
        initial_run=initial_run,
        recovery_plan=recovery_plan,
        recovery_run=recovery_run,
    )
    if artifact != expected:
        raise ValueError("specialist_recovery_analysis_invalid")
