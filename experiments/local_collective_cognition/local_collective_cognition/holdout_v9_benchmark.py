"""Ninth frozen holdout for multi-cycle resolution calibration v0.11."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion, FrozenAnswerBenchmarkHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V9_BENCHMARK_ID = "local-reasoning-holdout-v0-9"
HOLDOUT_V9_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V9_BENCHMARK_ID}",)

HOLDOUT_V9_QUESTIONS = (
    BenchmarkQuestion("logic-10", "All composers are attentive. No attentive people are careless. Some tutors are composers. Which statement must be true?", ("A: All tutors are attentive", "B: Some tutors are not careless", "C: No tutors are careless", "D: Some composers are careless")),
    BenchmarkQuestion("schedule-10", "M must be before N and P. Both N and P must be before Q. Which order is valid?", ("A: N,M,P,Q", "B: M,Q,N,P", "C: M,P,N,Q", "D: P,M,N,Q")),
    BenchmarkQuestion("implication-10", "If R then S. If S then T. T is false. Which statement must be true?", ("A: S is true", "B: R is true", "C: T is true", "D: R is false")),
    BenchmarkQuestion("modular-10", "What is the least positive integer n such that n mod 8 = 5 and n mod 3 = 2?", ("A: 5", "B: 13", "C: 21", "D: 29")),
    BenchmarkQuestion("probability-10", "A batch has 9 good and 3 defective parts. Two are selected without replacement. What is the probability of selecting at least one defective part?", ("A: 3/11", "B: 4/11", "C: 5/11", "D: 6/11")),
    BenchmarkQuestion("sets-10", "Among 220 users, 130 use A, 120 use B, and 70 use both. How many use neither?", ("A: 20", "B: 25", "C: 30", "D: 40")),
    BenchmarkQuestion("sequence-10", "What comes next in 3, 8, 15, 24, 35?", ("A: 46", "B: 48", "C: 49", "D: 50")),
    BenchmarkQuestion("rate-10", "A processor completes 720 units in 9 hours at a constant rate. How many units does it complete in 4.25 hours?", ("A: 320", "B: 330", "C: 340", "D: 360")),
    BenchmarkQuestion("bayes-10", "A condition has 10% prevalence. A test has 80% sensitivity and 90% specificity. What fraction of positive tests are true positives?", ("A: 4/13", "B: 8/17", "C: 2/3", "D: 8/9")),
    BenchmarkQuestion("code-10", "Start x = 2. For n in [1, 2, 3], replace x with 2*x+n. What is the final x?", ("A: 27", "B: 29", "C: 31", "D: 33")),
    BenchmarkQuestion("string-10", "Start with ABCDEF. Rotate left by two characters, then reverse each adjacent pair. What is the result?", ("A: CDFEAB", "B: EFBADC", "C: DCFEBA", "D: FEDCBA")),
    BenchmarkQuestion("causal-10", "A difference-in-differences design compares treated and untreated groups before and after treatment. Which assumption identifies the treatment effect?", ("A: Perfect treatment compliance", "B: No outcome measurement error", "C: Equal group sizes", "D: Parallel untreated trends")),
)

_HOLDOUT_V9_TRUTHS = (
    BenchmarkAnswerTruth("logic-10", "B"), BenchmarkAnswerTruth("schedule-10", "C"),
    BenchmarkAnswerTruth("implication-10", "D"), BenchmarkAnswerTruth("modular-10", "A"),
    BenchmarkAnswerTruth("probability-10", "C"), BenchmarkAnswerTruth("sets-10", "D"),
    BenchmarkAnswerTruth("sequence-10", "B"), BenchmarkAnswerTruth("rate-10", "C"),
    BenchmarkAnswerTruth("bayes-10", "B"), BenchmarkAnswerTruth("code-10", "A"),
    BenchmarkAnswerTruth("string-10", "C"), BenchmarkAnswerTruth("causal-10", "D"),
)

HOLDOUT_V9_ITEM_DOMAINS = {
    "logic-10": "formal", "schedule-10": "formal", "implication-10": "formal",
    "modular-10": "quantitative", "probability-10": "quantitative", "sets-10": "quantitative",
    "sequence-10": "quantitative", "rate-10": "quantitative", "bayes-10": "quantitative",
    "code-10": "procedural", "string-10": "procedural", "causal-10": "causal",
}
HOLDOUT_V9_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V9_QUESTIONS))
validate_fingerprint_domains(HOLDOUT_V9_ITEM_DOMAINS, HOLDOUT_V9_ITEM_FINGERPRINTS)


def build_holdout_v9_harness() -> FrozenAnswerBenchmarkHarness:
    return FrozenAnswerBenchmarkHarness(
        harness_id="local-reasoning-holdout-v9-harness", benchmark_id=HOLDOUT_V9_BENCHMARK_ID,
        questions=HOLDOUT_V9_QUESTIONS, truths=_HOLDOUT_V9_TRUTHS, evidence_refs=HOLDOUT_V9_EVIDENCE_REFS,
    )
