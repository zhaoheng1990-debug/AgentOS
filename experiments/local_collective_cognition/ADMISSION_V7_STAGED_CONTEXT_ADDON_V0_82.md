# Staged Context Utility Addon v0.82

## Status

**TYPED_REFERENCE_COMPLETE -
REJECT_STAGED_CONTEXT_TYPED_GATE.**

v0.82 removes the effect-rejudgment confound observed in v0.81. The workflow
is explicitly staged:

1. A14 produces atomic effect facts and a frozen evidence partition;
2. A16 receives only spans outside that evidence partition;
3. A16 returns grounded context-utility facts without effect fields;
4. Kernel compiles context versus reject while copying A14 evidence unchanged.

The candidate interface has no operation that can add, remove, or reclassify an
effect-evidence span. Evidence partition invariance is a preregistered hard
gate.

The fresh panel contains 12 balanced Evidence Inference test objects not used
by any local admission experiment through v0.81. Benchmark gold remains a
secondary evidence-coverage guard. Candidate acceptance requires an independent
typed semantic reference.

- prompt or contract tuning after freeze: forbidden;
- holdout re-execution: forbidden;
- candidate acceptance: false;
- Core or retention write: forbidden;
- production authority: false.

## Fresh Holdout Result

All three arms returned 12/12 valid receipts and complete partitions with no
contract or compiler failures.

| Measure | v0.76 baseline | A14 atomic | A14 + A16 staged |
|---|---:|---:|---:|
| Benchmark evidence precision | 0.8472 | 0.9722 | 0.9722 |
| Benchmark evidence recall | 0.9167 | 1.0000 | 1.0000 |
| Benchmark evidence F1 | 0.8722 | 0.9833 | 0.9833 |
| Evidence/context/reject spans | 25 / 15 / 8 | 25 / 23 / 0 | 25 / 4 / 19 |
| Arm physical tokens | 21,205 | 24,949 | 22,277 |

The complete staged candidate cost 47,226 physical tokens: 24,949 for A14 and
22,277 for A16. This is intentionally reported as a composed-system cost
rather than presenting the addon cost alone.

A16 changed 19 spans, all from context to rejection. Evidence membership
changed for zero spans. The candidate therefore:

- restored a non-degenerate context/reject partition;
- preserved A14 evidence precision, recall, and F1 exactly;
- produced no semantic conflict or ungrounded-quote failure;
- passed every preregistered integrity and budget condition.

## External Typed Panel

Operational success does not establish that the 19 rejections are semantically
correct. A 48-span double-blind panel has been frozen for independent GPT-5.6
and Gemini-3.1 annotation.

- panel id: `admission-v7-panel-cbaa80482adeaa8368`;
- GPT-5.6 lane hash:
  `e33c01206ea6946abdf0d5aabc534f96bdbdca43aaae1badd86bfbae8e4b3679`;
- Gemini-3.1 lane hash:
  `e9626bb4c57658c973046d1f8b843ca9bf73f00267b3b764a89e10dcbc922569`;
- benchmark gold exposed: false;
- baseline, atomic, and candidate outputs exposed: false.

Candidate acceptance remains false until both lanes, any required independent
adjudication, and frozen-reference scoring are complete.

## Preregistered Typed Gate

The post-reference decision logic was frozen before either annotation response
was received. Relative to A14, the staged candidate must satisfy all of:

1. typed accuracy improves;
2. typed macro F1 improves;
3. `REJECT` F1 improves;
4. `ADMIT_EVIDENCE` F1 is preserved exactly;
5. `RETAIN_CONTEXT` recall is at least 0.50 when valid context exists;
6. corrected spans outnumber harmed spans.

Passing these conditions yields only
`READY_PM_REVIEW_STAGED_CONTEXT_GAIN`. It does not authorize candidate
acceptance, runtime tuning, Core writes, retention writes, or production use.

The complete lane validation, anonymous-disagreement adjudication, typed
reference finalization, and three-arm scoring path passed a 48-span synthetic
protocol smoke test. Synthetic labels are test fixtures only and are not
retained as experimental evidence.

## External Lane Result

Both real annotation responses passed expected model, lane, pack hash,
48-span coverage, cross-field semantics, and blinding validation.

- complete typed-label agreement: 21/48;
- anonymous Kimi-K3 adjudication required: 27/48;
- agreed dispositions: 19 evidence and 2 reject;
- disagreement pairs: 18 context/reject, 2 evidence/context, and 7
  evidence/evidence disagreements in the remaining typed fields.

GPT-5.6 assigned 26 evidence, 20 context, and 2 reject labels. Gemini-3.1
assigned 28 evidence, 0 context, and 20 reject labels. This large difference
shows that the unresolved semantic boundary is whether target-relevant
non-effect material deserves an independent context state, rather than only
the candidate compiler's rejection threshold.

The Kimi pack contains anonymous positions only. Annotator identity, benchmark
gold, and baseline, atomic, and candidate outputs remain withheld.

## Typed Reference Result

Kimi-K3 returned all 27 requested decisions. The response passed panel,
adjudication-pack hash, coverage, position consistency, typed-label semantics,
and blinding validation. The frozen 48-span reference contains 26 evidence,
2 context, and 20 reject labels.

| Measure | v0.76 baseline | A14 atomic | A14 + A16 staged |
|---|---:|---:|---:|
| Typed accuracy | 0.6458 | 0.4792 | 0.8750 |
| Typed macro F1 | 0.4911 | 0.3007 | 0.6254 |
| `ADMIT_EVIDENCE` F1 | 0.9020 | 0.9020 | 0.9020 |
| `RETAIN_CONTEXT` F1 | 0.0000 | 0.0000 | 0.0000 |
| `REJECT` F1 | 0.5714 | 0.0000 | 0.9744 |

Relative to A14, A16 corrected 19 spans and harmed none. Accuracy improved by
0.3958 and macro F1 by 0.3248. Five of the six preregistered semantic
conditions passed.

The candidate failed the context-recall floor. Both valid context spans were
already admitted as evidence by A14, and A16 was prohibited from mutating the
frozen evidence partition. The remaining four errors were three reference
evidence spans retained as context and one reference reject span retained as
context.

## Final Decision

The preregistered decision is:

`REJECT_STAGED_CONTEXT_TYPED_GATE`

This rejects promotion of the combined candidate, not the A16 mechanism.
Every context-to-reject change made by A16 was correct under the frozen typed
reference. The bottleneck has moved upstream to the A14 evidence/context
boundary.

The next candidate should add a selective boundary-review stage with explicit
authority to propose evidence/context promotion or demotion only for witnessed
ambiguous spans. It must preserve ordinary A14 evidence, require independent
Provider support for any boundary mutation, and validate on a new holdout.
