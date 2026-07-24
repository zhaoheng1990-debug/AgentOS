"""Typed Harness that executes one answer-independent derivation action at a time."""

from __future__ import annotations

from .iterative_derivation_receipt import execute_step, finalize_session
from .typed_derivation_harness import TypedDerivationHarness


class IterativeDerivationHarness(TypedDerivationHarness):
    def execute_derivation_step(self, **values):
        return execute_step(**values)

    def finalize_derivation_session(self, **values):
        item_id = values["item_id"]
        question = self.provider_inputs((item_id,))["questions"][0]
        return finalize_session(**values, question=question)
