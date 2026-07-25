# Ternary Evidence Boundary Review v0.84

## Status

**EXTERNAL_LANE_ANALYSIS_COMPLETE -
REJECT_A18_ALL_MUTATIONS_EXTERNALLY_HARMFUL.**

v0.84 replaces the rejected v0.83 binary boundary facts with a ternary
ontology:

- target components: `MATCHED`, `EXPLICITLY_CONTRADICTED`, `NOT_STATED`;
- isolation: `ISOLATED`, `EXPLICITLY_POOLED`,
  `NOT_APPLICABLE_OR_NOT_STATED`;
- omission alone cannot demote evidence;
- demotion requires a grounded explicit contradiction or explicit pooling;
- promotion requires a grounded independent target-effect statement and
  supported target coreference;
- semantic conflicts preserve the upstream state.

The Provider receives neither upstream dispositions nor benchmark gold and
cannot return a policy label. Kernel retains all mutation authority. The A16
reject partition is immutable.

The seventh fresh holdout contains 12 balanced Evidence Inference test objects
not used by local admission experiments through v0.83.

- benchmark gold: secondary coverage guard only;
- external typed reference: required before acceptance;
- prompt or contract tuning after freeze: forbidden;
- holdout re-execution: forbidden;
- candidate acceptance: false;
- Core or retention write: forbidden;
- production authority: false.

## Fresh Holdout Result

All four arms returned 12/12 valid receipts and complete partitions with no
contract or compiler failure. All preregistered integrity and budget
conditions passed.

| Measure | Baseline | A14 | A14 + A16 | A14 + A16 + A18 |
|---|---:|---:|---:|---:|
| Benchmark evidence precision | 0.9583 | 0.9583 | 0.9583 | 0.7917 |
| Benchmark evidence recall | 0.9583 | 0.9583 | 0.9583 | 0.7917 |
| Benchmark evidence F1 | 0.9583 | 0.9583 | 0.9583 | 0.7917 |
| Evidence/context/reject spans | 24 / 9 / 15 | 24 / 22 / 2 | 24 / 2 / 22 | 20 / 6 / 22 |
| Arm physical tokens | 21,188 | 24,938 | 22,107 | 27,842 |

The composed A14+A16+A18 system consumed 74,887 physical tokens.

A18 made four mutations, all from evidence to context. This is a substantial
reduction from v0.83's 15 demotions, confirming that `NOT_STATED` prevents much
of the previous collapse. The reject partition remained exactly invariant.

## Phenomena

The four remaining demotions form two duplicated semantic disputes:

1. Two spans state that the target outcome was not significantly different
   between "the two groups." The Provider marked this as
   `EXPLICITLY_POOLED`, although a direct two-arm comparison may itself be the
   target effect rather than a pooled outcome.
2. Two spans compare a ketorolac group with a lidocaine group while the target
   object names lidocaine versus lidocaine plus ketorolac. The Provider treated
   both arms as explicitly contradicted. The exact study-arm binding requires
   independent review.

Six additional records contained semantically plausible but non-verbatim
effect anchors, including ellipses or normalized minus signs. Kernel correctly
recorded these as grounding conflicts and preserved their upstream states.
This is a receipt-quality issue, not evidence that the underlying effect
interpretation is wrong.

The result supports three provisional conclusions:

- ternary absence handling solves most, but not all, v0.83 over-demotion;
- explicit pooling still needs an external semantic distinction between a
  direct group comparison and a genuinely non-separable aggregate;
- exact substring grounding is safe as a fail-closed gate but Provider prompts
  need better quote discipline before any future iteration.

## External Gate

A blinded 48-span typed panel has been frozen for GPT-5.6 and Gemini-3.1.
Neither lane receives benchmark gold, peer labels, DeepSeek outputs, or any
arm disposition. Lane disagreements will require anonymous Kimi-K3
adjudication.

Both responses passed the frozen contract without repair. The lanes produced
38 complete typed-label agreements and 10 disagreements, for a semantic
agreement rate of 0.7917.

Crucially, all four A18 mutations are among the 38 agreements. Both lanes label
all four spans `ADMIT_EVIDENCE`:

- the two "not significantly different between the two groups" spans are
  direct null-effect evidence, not pooled outcomes;
- the two ketorolac-versus-lidocaine spans are treated as exact target-effect
  evidence under the study-arm binding, not explicit target contradictions.

The paired mutation result is therefore:

- corrected: 0;
- harmed: 4;
- pending adjudication: 0.

A18 and A16 are identical on the remaining 44 spans. Consequently, no Kimi
decision on the 10 unchanged-span disagreements can reverse the relative
finding that A18 is worse than A16.

Current mechanism decision:

`REJECT_A18_ALL_MUTATIONS_EXTERNALLY_HARMFUL`

Kimi-K3 adjudication remains required to complete the 48-span archival typed
reference, but no longer gates the A18 mechanism decision. No mechanism tuning
is authorized on this holdout.

The next fresh-holdout design should preserve A14+A16 and replace component
literalism with explicit study-relation modeling:

- distinguish direct arm comparison from non-separable pooling;
- resolve intervention/comparator aliases at the study-object level before
  judging a span;
- require a relational contradiction witness, not merely lexical arm-name
  divergence;
- keep exact quote grounding and fail-closed upstream preservation.
