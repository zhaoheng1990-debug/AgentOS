# Context Utility Witness Admission v0.81

## Status

**FRESH_HOLDOUT_DIAGNOSTIC_COMPLETE -
REJECT_CLEAN_ATTRIBUTION_EFFECT_REJUDGMENT_CONFOUND.**

v0.81 addresses the typed-reference failure in v0.80: atomic effect facts
recovered all effect-bearing evidence, but the broad non-effect relevance flag
retained every other span as context and produced no rejection.

The A15 Provider receipt keeps the v0.80 effect facts and replaces broad
context relevance with:

1. a bounded context-function code;
2. an explicit downstream-decision-change judgment;
3. an exact quote grounded in the assessed span.

Runtime owns the context ontology and final partition. It validates receipt
shape, quote grounding, conflict consistency, object binding, and policy
derivation. Provider policy labels remain forbidden.

## Decision Rules

- validated independent target-effect support becomes `ADMIT_EVIDENCE`;
- exact target-local non-effect material becomes `RETAIN_CONTEXT`;
- non-target material requires a grounded utility witness to become
  `RETAIN_CONTEXT`;
- absent, inconsistent, or ungrounded utility becomes `REJECT`;
- context conflicts cannot demote otherwise valid effect evidence.

## Freshness And Authority

The v0.81 holdout contains 12 balanced Evidence Inference test objects selected
after excluding every local object used through v0.80. It compares the v0.76
typed baseline, frozen v0.80 atomic witness, and v0.81 context utility witness
under one preregistration.

- benchmark gold: secondary coverage guard only;
- typed semantic reference: required before acceptance;
- candidate acceptance: false;
- runtime tuning after freeze: forbidden;
- Core or retention write: forbidden;
- production authority: false.

## Preflight Amendment

The first A15 launch stopped locally before any Provider request because the
runtime omitted its preregistration hash helper. A bounded preflight amendment
records the old and corrected runtime hashes and confirms:

- candidate Provider calls before correction: 0;
- prompt, schema, compiler policy, and holdout selection changed: false;
- baseline and atomic runs remained reusable;
- candidate re-execution occurred: false.

## Operational Result

All three arms returned 12/12 valid receipts and complete partitions with no
contract or compiler failures.

| Measure | v0.76 baseline | v0.80 atomic | v0.81 candidate |
|---|---:|---:|---:|
| Benchmark evidence precision | 0.9306 | 0.8889 | 0.7917 |
| Benchmark evidence recall | 0.8417 | 0.8417 | 0.7583 |
| Benchmark evidence F1 | 0.8653 | 0.8514 | 0.7569 |
| Evidence/context/reject spans | 24 / 20 / 7 | 23 / 27 / 1 | 22 / 21 / 8 |
| Physical tokens | 21,947 | 25,653 | 28,592 |

The context witness achieved its immediate operational objective: it restored
a non-degenerate context/reject split. Relative to v0.80, seven spans moved
from context to rejection.

However, the combined A15 task also asked the Provider to regenerate the v0.80
effect facts. Nine additional spans changed evidence status: five moved from
evidence to context and four moved from context to evidence. The benchmark
evidence decline and 11 conflicted spans therefore mix context-policy effects
with a fresh effect judgment.

## Decision

The preregistered integrity gates passed, so the run is mechanically eligible
for an external typed panel. It is not a clean causal test of context utility,
and full external annotation would have low marginal information value.

v0.81 is frozen as an architectural diagnostic and is not promoted. The next
candidate must be a staged context-only addon:

1. consume the frozen A14 atomic receipt and partition;
2. assess only spans not admitted as effect evidence;
3. prohibit any change to A14 evidence membership by construction;
4. compile grounded context utility into context versus reject;
5. validate on a fifth unseen holdout before external semantic scoring.
