"""Kernel-owned validation of proposal, critique, and revision lineage."""

from __future__ import annotations

from .problem_dialogue_contracts import (
    validate_critique_receipt, validate_dialogue_objects, validate_revision_receipt,
)
from .provider_telemetry import hash_payload


PROBLEM_DIALOGUE_LINEAGE_GATE_VERSION = "problem_dialogue_lineage_kernel_gate_v0_25"


class ProblemDialogueLineageKernelGate:
    def evaluate(self, *, thread_id, source_problem, suggested_problem, critique_receipt,
                 revision_receipt, final_problem):
        reasons = []
        try:
            validate_dialogue_objects(source_problem, suggested_problem, final_problem)
            validate_critique_receipt(
                critique_receipt, source_problem=source_problem,
                suggested_problem=suggested_problem,
            )
            validate_revision_receipt(
                revision_receipt, source_problem=source_problem,
                critique_receipt=critique_receipt, suggested_problem=suggested_problem,
                final_problem=final_problem,
            )
        except (KeyError, ValueError) as exc:
            reasons.append(type(exc).__name__ + ":" + str(exc))
        if critique_receipt.get("thread_id") != thread_id or revision_receipt.get(
            "thread_id"
        ) != thread_id:
            reasons.append("PROBLEM_DIALOGUE_THREAD_BINDING_INVALID")
        expected = {
            "ORIGINAL": source_problem.get("receipt_hash"),
            "CRITIC_REVISION": suggested_problem.get("receipt_hash"),
            "ABSTAIN": final_problem.get("receipt_hash"),
        }.get(revision_receipt.get("selection"))
        if final_problem.get("receipt_hash") != expected:
            reasons.append("PROBLEM_DIALOGUE_SELECTION_INVALID")
        if revision_receipt.get("selection") == "ABSTAIN" and not all(
            final_problem.get(key) == "ABSTAIN" for key in (
                "intent_mode", "problem_family", "target_kind", "critical_constraint",
            )
        ):
            reasons.append("PROBLEM_DIALOGUE_ABSTAIN_OBJECT_INVALID")
        committed = {
            "gate_version": PROBLEM_DIALOGUE_LINEAGE_GATE_VERSION,
            "item_id": source_problem.get("item_id", ""), "thread_id": thread_id,
            "status": "BLOCK" if reasons else "ALLOW", "reasons": reasons,
            "source_problem_hash": source_problem.get("receipt_hash", ""),
            "critique_receipt_hash": critique_receipt.get("receipt_hash", ""),
            "suggested_problem_hash": suggested_problem.get("receipt_hash", ""),
            "revision_receipt_hash": revision_receipt.get("receipt_hash", ""),
            "final_problem_hash": final_problem.get("receipt_hash", ""),
            "kernel_owned": True, "provider_authority": False,
            "hidden_truth_used": False,
        }
        return {**committed, "receipt_hash": hash_payload(committed)}
