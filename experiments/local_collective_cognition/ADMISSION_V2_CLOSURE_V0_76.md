# Typed Evidence Admission v0.76 Closure

## Decision

**REJECT_ADMISSION_V2_CALIBRATION.**

v0.76 did not reuse the v0.75 holdout. It built a balanced 12-case
development projection from previously revealed v0.65 data and excluded the
12 objects repeatedly used by the v0.66-v0.74 surface calibration line.

Admission V2 separated:

1. object relation: exact, contextual, or irrelevant;
2. evidence utility: effect-bearing, context-only, or none;
3. disposition: admit evidence, retain context, or reject.

Local compilation produced complete `evidence_span_ids`,
`context_span_ids`, and `rejected_span_ids` partitions. A synthetic
`NO_APPLICABLE_EVIDENCE` receipt correctly forced downstream abstention.

## Result

| Metric | Binary baseline | Admission V2 |
| --- | ---: | ---: |
| Valid receipts | 12/12 | 12/12 |
| Contract/compiler failures | 0 | 0 |
| Complete partitions | 12/12 | 12/12 |
| Evidence precision | 1.0000 | 0.9167 |
| Evidence recall | 1.0000 | 0.8194 |
| Evidence F1 | 1.0000 | 0.8472 |
| Retained context spans | 0 | 17 |
| False no-applicable states | 0 | 1 |
| Provider tasks | 0 replay | 12 |
| Physical tokens | 0 replay | 21,209 |

No case improved under the existing rationale-span metric. `11806`, `11995`,
and `6857` were harmed, so the frozen gate rejected the candidate and did not
authorize a new holdout.

## Failure anatomy

### Zero effect is still effect-bearing

For `11806`, two exact-object spans reported no significant difference in
PICD frequency. The Provider classified them as context-only because they did
not provide a positive or negative direction, producing a false
`NO_APPLICABLE_EVIDENCE` state.

This is a real ontology/prompt error. Evidence supporting no difference is
effect-bearing evidence. The definition must cover positive, negative, and
bounded-null effects, including significance and uncertainty.

### Corroboration is not merely context

For `11995`, one gold span was admitted while a second exact-object span with
specific insulin-dose values was demoted to context as a "subset." The
minimality instinct removed valid corroborating evidence.

Admission should ask whether a span can support the claim, not whether another
span is already more concise.

### Existing gold is not typed ontology gold

For `6857`, the Provider retained two compliance-related spans as context
because they did not directly compare formulations. The benchmark counts them
as gold rationales. This may be an Admission V2 error, a benchmark annotation
granularity mismatch, or both.

The existing gold distinguishes target rationale from distractor. It does not
distinguish effect-bearing evidence from useful context. Therefore scalar
evidence F1 alone cannot validate the new three-axis ontology.

## Next experiment

v0.77 should freeze an external typed-evidence annotation pack before changing
the runtime:

- GPT and Gemini independently label object relation, evidence utility, and
  disposition for every calibration span;
- Kimi adjudicates disagreements;
- `EFFECT_BEARING` explicitly includes increased, decreased, no-difference,
  uncertainty, quantitative corroboration, and significance evidence;
- Provider calibration is scored against typed consensus, while the original
  benchmark rationale set remains a separate coverage guard.

No human annotation is required. The v0.75 holdout remains excluded and cannot
be rerun. No CoreSlim, retention, accepted baseline, or production state was
changed.
