# Study-Relation Review v0.85

## Status

**DEVELOPMENT_SCREEN_COMPLETE -
AWAITING_MUTATION_CASE_TYPED_PANEL.**

v0.85 tests whether a shared case-level study relation graph can repair the
two coupled residual errors observed in v0.84:

- exact evidence can be confused with a related or composite outcome;
- useful target context can be rejected when each span is interpreted without
  a shared study-object model.

A19 first binds intervention aliases, comparator aliases, target contrasts,
target outcomes, composite outcomes, related outcomes, and non-target arms.
Each span then references those bindings and reports comparison, outcome,
effect, pooling, and coreference relations.

Provider does not receive upstream dispositions and cannot return policy
labels. Kernel permits only:

- evidence to context;
- context to evidence;
- reject to context.

Evidence/context to reject and reject to evidence are forbidden. Any incomplete
or ungrounded graph preserves the entire case upstream.

## Holdout Boundary

The Evidence Inference test split has only three unused eligible objects left,
one per effect label. Reusing prior test objects was forbidden.

This screen therefore uses 12 balanced, locally unseen objects from the
validation split. They are disjoint from all prior local admission surfaces,
but this is explicitly a development screen rather than an external transfer
holdout.

- local object freshness: true;
- prior surface reuse: false;
- external acceptance eligible: false;
- benchmark gold: secondary coverage guard only;
- external typed assessment: required for the screen result;
- Core or retention write: forbidden;
- production authority: false.

## Development Result

All four arms returned 12/12 valid receipts and complete partitions with no
contract or compiler failure. All operational and budget conditions passed.

| Measure | Baseline | A14 | A14 + A16 | A14 + A16 + A19 |
|---|---:|---:|---:|---:|
| Benchmark evidence precision | 0.8750 | 0.9444 | 0.9444 | 0.9444 |
| Benchmark evidence recall | 0.8333 | 1.0000 | 1.0000 | 0.9583 |
| Benchmark evidence F1 | 0.8333 | 0.9667 | 0.9667 | 0.9389 |
| Evidence/context/reject spans | 23 / 18 / 8 | 27 / 22 / 0 | 27 / 4 / 18 | 26 / 6 / 17 |
| Arm physical tokens | 22,192 | 26,218 | 21,792 | 43,800 |

The composed A14+A16+A19 system consumed 91,810 physical tokens.

A19 made two bounded mutations:

- one evidence to context;
- one reject to context.

Both occurred in the same conflict-free case. The other 11 cases produced 38
grounding or graph-consistency conflicts and were preserved upstream. No
unauthorized mutation occurred.

## Phenomena

The evidence-to-context mutation concerns a span containing complete before
and after values for both target arms. A19 classified it as descriptive rather
than an independent comparative effect. This likely repeats an old error:
quantitative arm-wise corroboration can be effect-bearing even without a
separate inferential sentence.

The reject-to-context mutation concerns a null comparison between the target
arms on side effects rather than the target defecation-frequency outcome. It
may be valid study context because it scopes the same intervention/comparator
relation, but it may also be irrelevant to the exact outcome. External typed
assessment is required.

The relation graph increased interpretability but is currently too brittle:

- exact quote discipline was often violated;
- effect anchors were supplied when the declared effect relation forbade them;
- target contrast and outcome records sometimes omitted required graph refs;
- fail-closed case scope reduced actionable coverage to 1/12;
- A19 cost approximately twice the A16 arm.

## External Gate

A blinded mutation-case panel contains all four spans from the only mutated
case. Selection basis, benchmark gold, lane identity, and all system outputs
are withheld. GPT-5.6 and Gemini-3.1 will independently label the four spans;
lane disagreements will require anonymous Kimi-K3 adjudication.

Current decision:

`DEFER_A19_SCREEN_PENDING_MUTATION_CASE_TYPED_PANEL`

Even a positive mutation result cannot accept A19 because the source split is
development-only. A positive result would authorize acquisition of a new
benchmark and a redesigned v0.86 protocol; a non-positive result will freeze
A19 as another bounded negative result.
