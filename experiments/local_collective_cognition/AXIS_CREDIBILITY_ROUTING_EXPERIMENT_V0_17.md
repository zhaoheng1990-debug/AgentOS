# Axis Credibility Routing Experiment v0.17

This window inherits MethodologyKernel v1.1 and the frozen v0.16 external
evaluation. The v0.16 labels are calibration evidence only and must never be
used to edit v0.17 cases, prompts, or outputs after inference begins.

## Cognitive Object

```text
Axis-specific source credibility
-> a fixed source assignment for each semantic axis
-> fresh primary-axis correctness, correction/harm balance, and work cost
```

The hypothesis is narrower than "collaboration is better": a cognitive group
may outperform one member only when Runtime assigns each subproblem to the
source with evidence of relative competence and preserves tuple coherence.

## Frozen Source Assignment

- `SELECTED_OBJECT`: single-model DeepSeek baseline.
- `SELECTION_BASIS`: independent contrastive basis critic, conditioned only on
  the public object and the baseline's already-frozen selected object.
- `PRAGMATIC_PREFERENCE`: role-informed coordinator.
- `AXIS_ASSESSMENT_COMPLETE`: local assessment skeptic, reported descriptively
  and excluded from the promotion gate because v0.16 was label-degenerate.

Runtime performs only the registered field assembly and coherence repair. It
does not infer a semantic label locally. Any repair is explicit in a receipt.

## Fresh Holdout Gate

- 24 new objects, six structural families, no semantic labels or construction
  truth in the corpus artifact.
- Corpus hash and routing preregistration hash are frozen before any provider
  call.
- Local role receipts, baseline, coordinator, critic, and routed output are
  frozen before external labels are requested.
- GPT-5.6 and Gemini 3.1 independently label the public surface; Kimi K3
  adjudicates whole-tuple disagreements.

## Confirmatory Success Gate

The primary axes are selected object, selection basis, and pragmatic
preference. Completeness remains descriptive.

- Routed primary-axis correct cells exceed the single-model baseline by at
  least 3 of 72.
- Routed selected-object accuracy is no more than 1 case below baseline.
- Routed pragmatic-preference accuracy exceeds baseline by at least 4 cases.
- Routed selection-basis accuracy is not below baseline.
- Across primary axes, corrections exceed harms.
- Incremental accounted work is positive and no more than 40,000 tokens per
  net added correct primary-axis cell.

All conditions must pass. Otherwise Anti-Additive rejects baseline promotion.

## Stop And Rollback

- Structural coverage below 95 percent stops the next inference phase.
- Missing source receipts or incoherent source combinations fail closed.
- External labels never revise frozen candidate outputs.
- This experiment has no AgentOS baseline, retention, selection, or production
  authority.

