"""Truth-isolated paired audit for ephemeral structural-prior experiments."""

from __future__ import annotations

from .problem_formulation_harness import ProblemFormulationHarness
from .provider_telemetry import hash_payload


class StructuralPriorPilotHarness(ProblemFormulationHarness):
    def audit_paired_definitions(self, *, experiment_id, controls, treatments,
                                 prior_receipt_hashes):
        control = self._audit(controls)
        treatment = self._audit(treatments)
        by_item = []
        for left, right in zip(controls, treatments):
            if left["item_id"] != right["item_id"]:
                raise ValueError("structural_prior_pair_item_mismatch")
            expected = self._problem_truths[left["item_id"]]
            observed_left = _fields(left)
            observed_right = _fields(right)
            by_item.append({
                "item_id": left["item_id"],
                "control_field_matches": sum(a == b for a, b in zip(observed_left, expected)),
                "treatment_field_matches": sum(a == b for a, b in zip(observed_right, expected)),
                "control_exact": observed_left == expected,
                "treatment_exact": observed_right == expected,
                "control_receipt_hash": left["receipt_hash"],
                "treatment_receipt_hash": right["receipt_hash"],
            })
        committed = {
            "audit_version": "ephemeral_structural_prior_paired_audit_v0_1",
            "experiment_id": experiment_id, "benchmark_id": self.benchmark_id,
            "control": control, "treatment": treatment, "paired_items": by_item,
            "exact_definition_gain": treatment["exact_definitions"] - control["exact_definitions"],
            "exact_item_union_gain": treatment["union_exact_items"] - control["union_exact_items"],
            "total_field_match_gain": treatment["total_field_matches"] - control["total_field_matches"],
            "improved_items": sum(item["treatment_field_matches"] > item["control_field_matches"]
                                  for item in by_item),
            "harmed_items": sum(item["treatment_field_matches"] < item["control_field_matches"]
                                for item in by_item),
            "prior_receipt_hashes": list(prior_receipt_hashes),
            "truth_commitment": hash_payload(self._problem_truths),
            "harness_owned": True, "selection_authority": False,
        }
        return {**committed, "receipt_hash": hash_payload(committed)}

    def _audit(self, receipts):
        fields, exact, exact_items = [0, 0, 0, 0], 0, set()
        for receipt in receipts:
            expected = self._problem_truths[receipt["item_id"]]
            observed = _fields(receipt)
            if observed == expected:
                exact += 1; exact_items.add(receipt["item_id"])
            fields = [count + (left == right)
                      for count, left, right in zip(fields, observed, expected)]
        return {
            "definitions": len(receipts), "exact_definitions": exact,
            "union_exact_items": len(exact_items), "total_field_matches": sum(fields),
            "field_matches": dict(zip(
                ("intent_mode", "problem_family", "target_kind", "critical_constraint"),
                fields,
            )),
            "receipt_hashes": [item["receipt_hash"] for item in receipts],
        }


def _fields(receipt):
    return tuple(receipt[key] for key in (
        "intent_mode", "problem_family", "target_kind", "critical_constraint",
    ))
