# Atomic Semantic Witness Admission v0.80

## Status

**AWAITING_GPT_GEMINI_TYPED_ANNOTATIONS.**

v0.80 replaces categorical outcome scope with atomic Provider facts and gives
the Runtime an explicit semantic conflict ledger.

The Provider supplies:

1. exact target object mentioned;
2. target effect separately extractable;
3. independent target-effect support;
4. effect-basis codes;
5. non-effect contextual relevance;
6. bounded rationale.

The structural contract validates shape, types, binding, and span coverage. It
does not reject a complete receipt merely because its semantic facts conflict.
The Runtime records conflicts, and the local compiler fails conflicted spans
closed to context or rejection. Conflicted effect promotion is forbidden.

## Freshness Boundary

The 12-case holdout is the third balanced set of locally unseen Evidence
Inference test-split objects. It does not overlap any v0.65/v0.75, v0.77,
v0.78, or v0.79 object.

- panel hash:
  `7abe9b6876fa34a1701294e5f7c78338f7c01fa77eecbf60dc2b050e3abcd143`;
- preregistration hash:
  `3d1f43f27e49e8ccc78ddfecc4898c2752284587be9b0669847514ba4286e37e`;
- Provider calls at freeze: 0;
- holdout re-execution allowed: false;
- pretraining contamination excluded: false.

## Operational Result

| Measure | v0.76 baseline | v0.80 candidate |
|---|---:|---:|
| Valid receipts | 12/12 | 12/12 |
| Contract/compiler failures | 0 | 0 |
| Complete partitions | 12/12 | 12/12 |
| Benchmark evidence precision | 0.8333 | 1.0000 |
| Benchmark evidence recall | 0.8333 | 1.0000 |
| Benchmark evidence F1 | 0.8333 | 1.0000 |
| Provider tasks | 12 | 12 |
| Physical attempts | 12 | 12 |
| Physical tokens | 21,641 | 25,631 |
| Semantic conflict spans | N/A | 0 |

The candidate added 3,990 tokens, an 18.4% increase. It improved two cases and
harmed none under the secondary benchmark coverage guard.

For both `EI-CAL-13791` and `EI-CAL-5792`, the baseline returned no admitted
evidence. The candidate admitted both benchmark rationale spans in each case.
This is consistent with the intended recovery of valid null/no-difference or
corroborating evidence, but benchmark agreement is not typed semantic truth.

## Decision Boundary

The preregistered operational decision is:

`READY_EXTERNAL_TYPED_PANEL`

The semantic decision remains:

`DEFERRED_EXTERNAL_TYPED_REFERENCE_REQUIRED`

Perfect benchmark coverage does not authorize candidate acceptance. The new
three-axis typed reference must be produced independently before baseline and
candidate outputs are revealed for scoring.

## External Panel

The frozen panel contains 48 independently assessed spans:

- GPT-5.6 lane pack hash:
  `f1057d2b5d10f6a1a18ece2ade7901eee205c3662ad59cd13890b8d7e8838e98`;
- Gemini-3.1 lane pack hash:
  `6b2d134264d618bac3f5c9c44671b9ba6cabef0669219018e4b63bd8cdba302e`.

Each lane receives different anonymous IDs and item order. Neither lane
contains case IDs, span IDs, benchmark gold, baseline or candidate output,
peer annotation, scores, or prior error analysis.

## Authority Boundary

- candidate acceptance: false;
- runtime tuning: not authorized;
- Core or retention write: not authorized;
- production authority: false.
