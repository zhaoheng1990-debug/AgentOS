"""Opportunity Harness exposing only public, answer-independent derivation symbols."""

from __future__ import annotations

from .opportunity_harness import OpportunityFrozenAnswerHarness


class TypedDerivationHarness(OpportunityFrozenAnswerHarness):
    def __init__(self, *, derivation_values: dict[str, tuple[str, ...]], **values) -> None:
        super().__init__(**values)
        if set(derivation_values) != set(self._question_ids):
            raise ValueError("typed_derivation_scaffold_coverage_invalid")
        questions = {item.item_id: item.prompt for item in self._questions}
        if any(
            not entries or any(str(entry) not in questions[item_id] for entry in entries)
            for item_id, entries in derivation_values.items()
        ):
            raise ValueError("typed_derivation_scaffold_source_invalid")
        self._derivation_values = {key: tuple(map(str, value)) for key, value in derivation_values.items()}

    def derivation_scaffold(self, item_id: str) -> dict[str, str]:
        values = self._derivation_values[item_id]
        return {"CONST_1": "1", "CONST_100": "100",
                **{f"VALUE_{index}": value for index, value in enumerate(values, 1)}}
