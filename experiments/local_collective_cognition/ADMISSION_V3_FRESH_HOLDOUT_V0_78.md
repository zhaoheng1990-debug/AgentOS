# Witness-Backed Admission v0.78

## Decision

**REJECT_RUNTIME_INTEGRITY.**

v0.78 preserved the rejected v0.76 runtime as its baseline and introduced a
separate witness-backed candidate. It did not modify v0.77's external typed
reference candidate.

The candidate added two modular semantic witnesses:

1. `OutcomeSeparabilityWitness` for exact, non-separable composite, related,
   or absent target outcomes;
2. `EffectBasisAdmission` for direction, uncertainty, null/no-difference, and
   quantitative corroboration support.

## Freshness Boundary

The holdout contains 12 hash-selected Evidence Inference test-split objects,
balanced across increased, decreased, and no-difference labels. None overlap
the 36 v0.65/v0.75 test objects or the 12 v0.77 development objects.

- panel hash:
  `0c1baa5083434c4a1ee8e74e89eaa35c315ae9ae914fa0d969db67b8cb88afe6`;
- preregistration hash:
  `62eaea293bfe649120dc4271137272d5ca472ae8f752d86d12833bed6f5f877b`;
- local pipeline object freshness: true;
- pretraining contamination excluded: false;
- re-execution allowed: false.

The benchmark rationale set was preregistered as a secondary coverage guard,
not as typed ontology truth. Semantic acceptance required a new external typed
reference.

## Result

| Measure | v0.76 baseline | v0.78 candidate |
|---|---:|---:|
| Valid receipts | 11/12 | 7/12 |
| Contract failures | 1 | 5 |
| Complete partitions | 11/12 | 7/12 |
| Benchmark evidence precision | 0.7222 | 0.5556 |
| Benchmark evidence recall | 0.6667 | 0.5417 |
| Benchmark evidence F1 | 0.6778 | 0.5389 |
| Provider tasks | 12 | 12 |
| Physical attempts | 12 | 12 |
| Physical tokens | 21,348 | 27,437 |

The candidate used 6,089 additional tokens, a 28.5% increase. On the seven
cases where both arms produced valid partitions, the evidence partitions were
identical and mean benchmark evidence F1 was 0.9238 for both arms. The extra
witness fields therefore produced no observed partition gain before external
semantic adjudication.

## Failure Anatomy

All five candidate failures included
`ADMISSION_V3_OUTCOME_RELATION_CONFLICT`. Three also included
`ADMISSION_V3_STATE_PARTITION_CONFLICT`.

The contract incorrectly treated several semantic axes as bijective:

- a target inside a non-separable composite was forced to
  `CONTEXTUAL_OBJECT`, while the Provider sometimes used `EXACT_OBJECT` to
  mean that the target was explicitly mentioned;
- `TARGET_ABSENT` was forced to `IRRELEVANT_OBJECT`, even when a mechanistic
  measurement remained useful context;
- `admission_state` was requested from the Provider even though it can be
  compiled mechanically from the final span dispositions.

This created redundant semantic declarations. A single Provider judgment could
be internally reasonable yet fail because two fields used different meanings
for "exact object." The holdout also exposed a real semantic distinction
between a non-separable composite and multiple separately reported outcomes;
the candidate did not reliably distinguish them.

The v0.76 baseline failure on `EI-CAL-10178` and the corresponding v0.78
failure are preserved. No failed receipt was repaired or retried.

## v0.79 Design Constraint

The next candidate should reduce the Provider receipt to independent semantic
facts:

1. target outcome scope: separately reported, component of a composite,
   related only, or absent;
2. independent target-effect support: true or false;
3. effect-basis codes;
4. contextual relevance: true or false;
5. bounded rationale.

Local deterministic code should derive object relation, evidence utility,
disposition, admission state, and the complete partition. This keeps Provider
support inside the Runtime's cognition while removing duplicated declarations.

v0.78 must not be rerun or tuned on this holdout. v0.79 requires a newly
selected unused-source holdout and a new preregistration.

## Authority Boundary

- external typed panel: not authorized after runtime-integrity rejection;
- semantic acceptance: deferred and then stopped;
- runtime tuning: not authorized;
- Core or retention write: not authorized;
- production authority: false.
