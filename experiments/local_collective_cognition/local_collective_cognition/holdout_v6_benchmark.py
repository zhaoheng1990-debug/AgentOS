"""Sixth frozen holdout for structural-fingerprint routing protocol v0.8."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion, FrozenAnswerBenchmarkHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V6_BENCHMARK_ID = "local-reasoning-holdout-v0-6"
HOLDOUT_V6_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V6_BENCHMARK_ID}",)

HOLDOUT_V6_QUESTIONS = (
    BenchmarkQuestion("logic-7", "All sculptors are patient. No patient people are careless. Some nurses are sculptors. Which statement must be true?", ("A: Some nurses are not careless", "B: All nurses are patient", "C: Some sculptors are careless", "D: No nurses are careless")),
    BenchmarkQuestion("schedule-7", "K must be before L and M. Both L and M must be before N. Which order is valid?", ("A: L,K,M,N", "B: K,M,L,N", "C: K,N,L,M", "D: M,K,L,N")),
    BenchmarkQuestion("implication-7", "If R then S. If S then T. R is true. Which statement must be true?", ("A: S is false", "B: T is false", "C: T is true", "D: Nothing follows")),
    BenchmarkQuestion("modular-7", "What is the least positive integer n such that n mod 5 = 4 and n mod 7 = 2?", ("A: 9", "B: 14", "C: 19", "D: 24")),
    BenchmarkQuestion("probability-7", "A batch has 7 good and 3 defective parts. Two are selected without replacement. What is the probability of selecting at least one defective part?", ("A: 7/15", "B: 1/2", "C: 8/15", "D: 3/5")),
    BenchmarkQuestion("sets-7", "Among 150 users, 90 use A, 80 use B, and 50 use both. How many use neither?", ("A: 20", "B: 30", "C: 40", "D: 50")),
    BenchmarkQuestion("sequence-7", "What comes next in 2, 6, 13, 23, 36?", ("A: 47", "B: 49", "C: 51", "D: 52")),
    BenchmarkQuestion("rate-7", "A processor completes 420 units in 5.6 hours at a constant rate. How many units does it complete in 3.4 hours?", ("A: 240", "B: 250", "C: 255", "D: 270")),
    BenchmarkQuestion("bayes-7", "A condition has 4% prevalence. A test has 90% sensitivity and 96% specificity. Approximately what fraction of positive tests are true positives?", ("A: 1/3", "B: 1/2", "C: 2/3", "D: 9/10")),
    BenchmarkQuestion("code-7", "Start x = 2. For n in [1, 2, 3], replace x with x*n+n. What is the final x?", ("A: 18", "B: 21", "C: 24", "D: 27")),
    BenchmarkQuestion("string-7", "Start with ABCDEF. Rotate left by two characters, then reverse the entire result. What is the result?", ("A: FEDCBA", "B: BAFEDC", "C: BAFDEC", "D: CDEFAB")),
    BenchmarkQuestion("causal-7", "A program is assigned when a continuous score crosses a fixed cutoff. Which comparison identifies the local regression-discontinuity effect?", ("A: Participants versus all nonparticipants", "B: Units just above versus just below the cutoff", "C: Highest-score units versus lowest-score units", "D: Participants before versus after the program")),
)

_HOLDOUT_V6_TRUTHS = (
    BenchmarkAnswerTruth("logic-7", "A"), BenchmarkAnswerTruth("schedule-7", "B"),
    BenchmarkAnswerTruth("implication-7", "C"), BenchmarkAnswerTruth("modular-7", "A"),
    BenchmarkAnswerTruth("probability-7", "C"), BenchmarkAnswerTruth("sets-7", "B"),
    BenchmarkAnswerTruth("sequence-7", "D"), BenchmarkAnswerTruth("rate-7", "C"),
    BenchmarkAnswerTruth("bayes-7", "B"), BenchmarkAnswerTruth("code-7", "D"),
    BenchmarkAnswerTruth("string-7", "B"), BenchmarkAnswerTruth("causal-7", "B"),
)

HOLDOUT_V6_ITEM_DOMAINS = {
    "logic-7": "formal", "schedule-7": "formal", "implication-7": "formal",
    "modular-7": "quantitative", "probability-7": "quantitative", "sets-7": "quantitative",
    "sequence-7": "quantitative", "rate-7": "quantitative", "bayes-7": "quantitative",
    "code-7": "procedural", "string-7": "procedural", "causal-7": "causal",
}
HOLDOUT_V6_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V6_QUESTIONS))
validate_fingerprint_domains(HOLDOUT_V6_ITEM_DOMAINS, HOLDOUT_V6_ITEM_FINGERPRINTS)


def build_holdout_v6_harness() -> FrozenAnswerBenchmarkHarness:
    return FrozenAnswerBenchmarkHarness(
        harness_id="local-reasoning-holdout-v6-harness",
        benchmark_id=HOLDOUT_V6_BENCHMARK_ID,
        questions=HOLDOUT_V6_QUESTIONS,
        truths=_HOLDOUT_V6_TRUTHS,
        evidence_refs=HOLDOUT_V6_EVIDENCE_REFS,
    )
