# Ternary Evidence Boundary Review v0.84

## Status

**FRESH_HOLDOUT_DIAGNOSTIC_COMPLETE -
AWAITING_EXTERNAL_TYPED_REFERENCE.**

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

Current decision:

`DEFER_TERNARY_BOUNDARY_ACCEPTANCE_PENDING_EXTERNAL_TYPED_REFERENCE`

No mechanism tuning is authorized on this holdout. The next implementation
decision must be based on the frozen external reference:

- accept A18 only if the four demotions are supported without harming valid
  unchanged evidence;
- otherwise preserve A14+A16 and freeze A18 as a bounded negative result;
- use any newly observed failure only to design a new fresh-holdout version.
