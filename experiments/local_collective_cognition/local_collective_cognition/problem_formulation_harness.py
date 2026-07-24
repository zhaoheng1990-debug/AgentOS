"""Truth-isolated Harness audit for admitted problem definitions."""

from __future__ import annotations

from .iterative_derivation_harness import IterativeDerivationHarness
from .provider_telemetry import hash_payload


class ProblemFormulationHarness(IterativeDerivationHarness):
    def __init__(self, *args, problem_truths, **kwargs):
        super().__init__(*args, **kwargs)
        self._problem_truths = {item_id: tuple(value) for item_id, value in problem_truths.items()}
        if set(self._problem_truths) != {item.item_id for item in self._questions}:
            raise ValueError("problem_truth_coverage_invalid")

    def audit_problem_definitions(self, *, experiment_id, admission_receipts,
                                  candidate_receipts=()):
        seen, exact = set(), 0
        field_matches = [0, 0, 0, 0]
        hashes = []
        for admission in admission_receipts:
            if admission.get("status") != "ALLOW" or admission["item_id"] in seen:
                raise ValueError("problem_admission_audit_input_invalid")
            item_id = admission["item_id"]
            if item_id not in self._problem_truths:
                raise ValueError("problem_admission_item_unknown")
            seen.add(item_id); hashes.append(admission["receipt_hash"])
            problem = admission["selected_problem"]
            observed = tuple(problem[key] for key in (
                "intent_mode", "problem_family", "target_kind", "critical_constraint",
            ))
            expected = self._problem_truths[item_id]
            exact += observed == expected
            field_matches = [count + (left == right)
                             for count, left, right in zip(field_matches, observed, expected)]
        candidate_exact, candidate_fields, candidate_hashes = 0, [0, 0, 0, 0], []
        candidate_items, exact_items = set(), set()
        for problem in candidate_receipts:
            item_id = problem.get("item_id")
            if item_id not in self._problem_truths:
                raise ValueError("problem_candidate_audit_item_unknown")
            candidate_items.add(item_id); candidate_hashes.append(problem["receipt_hash"])
            observed = tuple(problem[key] for key in (
                "intent_mode", "problem_family", "target_kind", "critical_constraint",
            ))
            expected = self._problem_truths[item_id]
            if observed == expected:
                candidate_exact += 1; exact_items.add(item_id)
            candidate_fields = [count + (left == right)
                                for count, left, right in zip(candidate_fields, observed, expected)]
        committed = {
            "audit_version": "problem_definition_harness_audit_v0_24",
            "experiment_id": experiment_id, "benchmark_id": self.benchmark_id,
            "admitted_items": len(seen), "exact_problem_definitions": exact,
            "field_matches": dict(zip(
                ("intent_mode", "problem_family", "target_kind", "critical_constraint"),
                field_matches,
            )),
            "admission_receipt_hashes": hashes,
            "candidate_items": len(candidate_items),
            "candidate_definitions": len(candidate_hashes),
            "exact_candidate_definitions": candidate_exact,
            "candidate_union_exact_items": len(exact_items),
            "candidate_field_matches": dict(zip(
                ("intent_mode", "problem_family", "target_kind", "critical_constraint"),
                candidate_fields,
            )),
            "candidate_receipt_hashes": candidate_hashes,
            "truth_commitment": hash_payload(self._problem_truths),
            "harness_owned": True, "selection_authority": False,
        }
        return {**committed, "receipt_hash": hash_payload(committed)}
