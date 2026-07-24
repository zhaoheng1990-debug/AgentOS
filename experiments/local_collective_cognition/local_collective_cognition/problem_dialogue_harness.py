"""Truth-isolated stage audit for problem-dialogue object discovery."""

from __future__ import annotations

from .problem_formulation_harness import ProblemFormulationHarness
from .provider_telemetry import hash_payload


class ProblemDialogueHarness(ProblemFormulationHarness):
    def audit_problem_dialogue(self, *, experiment_id, admission_receipts,
                               proposal_receipts, suggestion_receipts, final_receipts):
        stages = {
            "proposal": self._audit_stage(proposal_receipts),
            "critic_suggestion": self._audit_stage(suggestion_receipts),
            "revision_final": self._audit_stage(final_receipts),
        }
        admitted = self.audit_problem_definitions(
            experiment_id=experiment_id + "-admission",
            admission_receipts=admission_receipts,
        )
        committed = {
            "audit_version": "problem_dialogue_harness_audit_v0_25",
            "experiment_id": experiment_id, "benchmark_id": self.benchmark_id,
            "stages": stages, "admitted": admitted,
            "proposal_to_revision_exact_item_gain": (
                stages["revision_final"]["union_exact_items"]
                - stages["proposal"]["union_exact_items"]
            ),
            "proposal_to_suggestion_exact_item_gain": (
                stages["critic_suggestion"]["union_exact_items"]
                - stages["proposal"]["union_exact_items"]
            ),
            "truth_commitment": hash_payload(self._problem_truths),
            "harness_owned": True, "selection_authority": False,
        }
        return {**committed, "receipt_hash": hash_payload(committed)}

    def _audit_stage(self, receipts):
        exact, fields, hashes = 0, [0, 0, 0, 0], []
        items, exact_items = set(), set()
        for problem in receipts:
            item_id = problem.get("item_id")
            if item_id not in self._problem_truths:
                raise ValueError("problem_dialogue_candidate_item_unknown")
            observed = tuple(problem[key] for key in (
                "intent_mode", "problem_family", "target_kind", "critical_constraint",
            ))
            expected = self._problem_truths[item_id]
            items.add(item_id); hashes.append(problem["receipt_hash"])
            if observed == expected:
                exact += 1; exact_items.add(item_id)
            fields = [count + (left == right)
                      for count, left, right in zip(fields, observed, expected)]
        return {
            "items": len(items), "definitions": len(hashes),
            "exact_definitions": exact, "union_exact_items": len(exact_items),
            "field_matches": dict(zip(
                ("intent_mode", "problem_family", "target_kind", "critical_constraint"),
                fields,
            )),
            "receipt_hashes": hashes,
        }
