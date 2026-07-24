"""Twelfth frozen holdout for current-case argument adjudication v0.14."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion, FrozenAnswerBenchmarkHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V12_BENCHMARK_ID = "local-reasoning-holdout-v0-12"
HOLDOUT_V12_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V12_BENCHMARK_ID}",)

HOLDOUT_V12_QUESTIONS = (
    BenchmarkQuestion("logic-13", "All engineers are methodical. No methodical people are reckless. Some artists are engineers. Which statement must be true?", ("A: All artists are methodical", "B: No artists are reckless", "C: Some artists are not reckless", "D: Some engineers are reckless")),
    BenchmarkQuestion("schedule-13", "J must be before K and L. Both K and L must be before M. Which order is valid?", ("A: J,K,L,M", "B: K,J,L,M", "C: J,M,K,L", "D: L,J,K,M")),
    BenchmarkQuestion("implication-13", "If A then B. If B then C. C is false. Which statement must be true?", ("A: B is true", "B: C is true", "C: A is true", "D: A is false")),
    BenchmarkQuestion("modular-13", "What is the least positive integer n such that n mod 8 = 3 and n mod 5 = 2?", ("A: 11", "B: 19", "C: 22", "D: 27")),
    BenchmarkQuestion("probability-13", "A batch has 9 good and 3 defective parts. Two are selected without replacement. What is the probability of selecting at least one defective part?", ("A: 4/11", "B: 5/11", "C: 1/2", "D: 6/11")),
    BenchmarkQuestion("sets-13", "Among 200 users, 120 use A, 105 use B, and 65 use both. How many use neither?", ("A: 30", "B: 35", "C: 40", "D: 45")),
    BenchmarkQuestion("sequence-13", "What comes next in 4, 10, 18, 28, 40?", ("A: 54", "B: 52", "C: 50", "D: 48")),
    BenchmarkQuestion("rate-13", "A processor completes 1080 units in 18 hours at a constant rate. How many units does it complete in 7.25 hours?", ("A: 420", "B: 435", "C: 450", "D: 465")),
    BenchmarkQuestion("bayes-13", "A condition has 8% prevalence. A test has 90% sensitivity and 92% specificity. What fraction of positive tests are true positives?", ("A: 9/20", "B: 12/25", "C: 45/91", "D: 18/25")),
    BenchmarkQuestion("code-13", "Start x = 2. For n in [1, 2, 3], replace x with 2*x+n. What is the final x?", ("A: 24", "B: 25", "C: 26", "D: 27")),
    BenchmarkQuestion("string-13", "Start with ABCDEF. Swap the two halves, then reverse each adjacent pair. What is the result?", ("A: EDAFCB", "B: DEFABC", "C: FEDCBA", "D: BADCFE")),
    BenchmarkQuestion("causal-13", "An instrumental-variable study uses Z to estimate the effect of X on Y. Which condition is the exclusion restriction?", ("A: Z strongly predicts X", "B: Z affects Y only through X", "C: X and Y have equal variance", "D: Z is independent of X")),
)

_HOLDOUT_V12_TRUTHS = (
    BenchmarkAnswerTruth("logic-13", "C"), BenchmarkAnswerTruth("schedule-13", "A"),
    BenchmarkAnswerTruth("implication-13", "D"), BenchmarkAnswerTruth("modular-13", "D"),
    BenchmarkAnswerTruth("probability-13", "B"), BenchmarkAnswerTruth("sets-13", "C"),
    BenchmarkAnswerTruth("sequence-13", "A"), BenchmarkAnswerTruth("rate-13", "B"),
    BenchmarkAnswerTruth("bayes-13", "C"), BenchmarkAnswerTruth("code-13", "D"),
    BenchmarkAnswerTruth("string-13", "A"), BenchmarkAnswerTruth("causal-13", "B"),
)

HOLDOUT_V12_ITEM_DOMAINS = {
    "logic-13": "formal", "schedule-13": "formal", "implication-13": "formal",
    "modular-13": "quantitative", "probability-13": "quantitative", "sets-13": "quantitative",
    "sequence-13": "quantitative", "rate-13": "quantitative", "bayes-13": "quantitative",
    "code-13": "procedural", "string-13": "procedural", "causal-13": "causal",
}
HOLDOUT_V12_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V12_QUESTIONS))
validate_fingerprint_domains(HOLDOUT_V12_ITEM_DOMAINS, HOLDOUT_V12_ITEM_FINGERPRINTS)


def build_holdout_v12_harness() -> FrozenAnswerBenchmarkHarness:
    return FrozenAnswerBenchmarkHarness(
        harness_id="local-reasoning-holdout-v12-harness", benchmark_id=HOLDOUT_V12_BENCHMARK_ID,
        questions=HOLDOUT_V12_QUESTIONS, truths=_HOLDOUT_V12_TRUTHS, evidence_refs=HOLDOUT_V12_EVIDENCE_REFS,
    )
