"""Frozen-answer Harness extension for aggregate opportunity auditing."""

from __future__ import annotations

from .argument_opportunity_receipt import build_argument_opportunity_receipt
from .candidate_revision_opportunity_receipt import build_candidate_revision_opportunity_receipt
from .frozen_answer_harness import FrozenAnswerBenchmarkHarness


class OpportunityFrozenAnswerHarness(FrozenAnswerBenchmarkHarness):
    def audit_argument_opportunities(self, *, experiment_id: str, pairs: tuple[dict[str, str], ...]):
        return build_argument_opportunity_receipt(
            experiment_id=experiment_id, pairs=pairs, truths=self._truths,
            truth_commitment=self._truth_commitment,
        )

    def audit_candidate_revision_opportunities(
        self, *, experiment_id: str, pairs: tuple[dict[str, str], ...],
    ):
        return build_candidate_revision_opportunity_receipt(
            experiment_id=experiment_id, pairs=pairs, truths=self._truths,
            truth_commitment=self._truth_commitment,
        )
