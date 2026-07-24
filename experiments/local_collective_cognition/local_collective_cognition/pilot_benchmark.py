"""Frozen synthetic reasoning benchmark for the workstation-local pilot."""

from __future__ import annotations

from .frozen_answer_harness import (
    BenchmarkAnswerTruth,
    BenchmarkQuestion,
    FrozenAnswerBenchmarkHarness,
)


PILOT_BENCHMARK_ID = "local-reasoning-pilot-v0-1"
PILOT_EVIDENCE_REFS = (f"benchmark://{PILOT_BENCHMARK_ID}",)

PILOT_QUESTIONS = (
    BenchmarkQuestion("logic-1", "All R are S. No S are T. Which statement must be true?", ("A: No R are T", "B: Some R are T", "C: All T are R", "D: Some S are R")),
    BenchmarkQuestion("modular-1", "What is the least positive integer n such that n mod 5 = 2 and n mod 3 = 1?", ("A: 5", "B: 7", "C: 12", "D: 17")),
    BenchmarkQuestion("probability-1", "A bag has 3 red and 2 blue balls. Two are drawn without replacement. What is the probability they have the same color?", ("A: 0.2", "B: 0.3", "C: 0.4", "D: 0.5")),
    BenchmarkQuestion("code-1", "Start x = 1. For i in [2, 3, 4], replace x with x*i - 1. What is the final x?", ("A: 5", "B: 6", "C: 8", "D: 7")),
    BenchmarkQuestion("schedule-1", "P must be before Q; R must be after Q; S must be before R. Which order is impossible?", ("A: P,S,Q,R", "B: S,P,Q,R", "C: P,Q,S,R", "D: Q,P,S,R")),
    BenchmarkQuestion("sets-1", "Among 40 users, 25 use A, 18 use B, and 10 use both. How many use neither?", ("A: 5", "B: 7", "C: 10", "D: 13")),
    BenchmarkQuestion("causal-1", "Coffee use is associated with productivity, and sleep affects both. Which design best identifies the causal effect of coffee?", ("A: Randomly assign coffee while holding other conditions comparable", "B: Compare existing heavy and light coffee users", "C: Ask productive people how much coffee they drink", "D: Remove sleep from the report")),
    BenchmarkQuestion("sequence-1", "What comes next in 2, 6, 12, 20, 30?", ("A: 36", "B: 40", "C: 42", "D: 44")),
    BenchmarkQuestion("truth-1", "Exactly one of X and Y is true. X says 'Y is false'. Y says 'X and Y have the same truth value'. Which assignment is consistent?", ("A: X true, Y false", "B: X false, Y true", "C: Both true", "D: Both false")),
    BenchmarkQuestion("rate-1", "A machine makes 120 parts in 8 minutes at a constant rate. How many parts does it make in 45 minutes?", ("A: 600", "B: 640", "C: 675", "D: 720")),
    BenchmarkQuestion("string-1", "Start with ABCDE. Move the last character to the front, twice. What is the result?", ("A: EABCD", "B: CDEAB", "C: BCDEA", "D: DEABC")),
    BenchmarkQuestion("bayes-1", "A condition has 10% prevalence. A test has 90% sensitivity and 80% specificity. Approximately what fraction of positive tests are true positives?", ("A: 1/5", "B: 1/3", "C: 1/2", "D: 4/5")),
)

_PILOT_TRUTHS = (
    BenchmarkAnswerTruth("logic-1", "A"),
    BenchmarkAnswerTruth("modular-1", "B"),
    BenchmarkAnswerTruth("probability-1", "C"),
    BenchmarkAnswerTruth("code-1", "D"),
    BenchmarkAnswerTruth("schedule-1", "D"),
    BenchmarkAnswerTruth("sets-1", "B"),
    BenchmarkAnswerTruth("causal-1", "A"),
    BenchmarkAnswerTruth("sequence-1", "C"),
    BenchmarkAnswerTruth("truth-1", "A"),
    BenchmarkAnswerTruth("rate-1", "C"),
    BenchmarkAnswerTruth("string-1", "D"),
    BenchmarkAnswerTruth("bayes-1", "B"),
)

PILOT_ANSWER_SCHEMA = {
    "type": "object",
    "required": ["answers", "evidence_refs"],
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["item_id", "answer"],
                "properties": {
                    "item_id": {"type": "string"},
                    "answer": {"type": "string", "enum": ["A", "B", "C", "D"]},
                },
            },
        },
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
    },
}

PILOT_ITEM_ANSWER_SCHEMA = {
    "type": "object",
    "required": ["item_id", "answer", "confidence", "evidence_refs"],
    "properties": {
        "item_id": {"type": "string"},
        "answer": {"type": "string", "enum": ["A", "B", "C", "D"]},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
    },
}


def build_pilot_harness() -> FrozenAnswerBenchmarkHarness:
    return FrozenAnswerBenchmarkHarness(
        harness_id="local-reasoning-pilot-harness",
        benchmark_id=PILOT_BENCHMARK_ID,
        questions=PILOT_QUESTIONS,
        truths=_PILOT_TRUTHS,
        evidence_refs=PILOT_EVIDENCE_REFS,
    )
