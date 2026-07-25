# Source-Surface Binding v0.71 Closure

## Decision

**CLOSED: calibration rejected; fresh holdout not executed.**

v0.71 removed free-text witness generation. Local code enumerated immutable
source surfaces and the Provider selected candidate IDs.

| Metric | Baseline | v0.71 |
| --- | ---: | ---: |
| Valid receipts | 11/12 | 12/12 |
| Label accuracy | 0.7500 | 0.8333 |
| Evidence F1 | 0.9000 | 0.9556 |
| Effective Cbit | 0.8474 | 0.9111 |
| Tokens | 41,101 | 245,471 |

The candidate corrected `11179`, `13793`, and `5842`. It harmed `6743` and
`8861`; both otherwise correct receipts used `timepoint_binding=UNRESOLVED`
even though their frames declared the query timepoint `UNCONSTRAINED`.
The candidate also exceeded the frozen 200,000-token ceiling.

The source-surface mechanism therefore worked, but the Provider was still
given authority over a coordinate already settled by the frame. v0.72 should
perform a zero-call deterministic projection:

- frame `UNCONSTRAINED` plus an explicit or absent passage timepoint becomes
  `ALLOWED_BY_UNCONSTRAINED`;
- Provider cannot downgrade it to `UNRESOLVED`;
- exact frame requirements continue to require Provider-backed matching.

The fresh holdout remained untouched. CoreSlim and production state were not
modified.
