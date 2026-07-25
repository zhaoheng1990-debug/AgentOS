# Coordinate Projection v0.72 Closure

## Decision

**PASS on frozen calibration replay; fresh holdout remains blocked.**

v0.72 removed Provider authority over coordinates already settled by the
frame. It performed 17 deterministic projections and added zero Provider
calls.

| Metric | Baseline | v0.71 | v0.72 |
| --- | ---: | ---: | ---: |
| Valid receipts | 11/12 | 12/12 | 12/12 |
| Label accuracy | 0.7500 | 0.8333 | 1.0000 |
| Evidence F1 | 0.9000 | 0.9556 | 0.9556 |
| Effective Cbit | 0.8474 | 0.9111 | 0.9666 |

`6743` and `8861` were recovered without changing their evidence, relation, or
significance fields. The existing `11179`, `13793`, and `5842` corrections were
preserved. No previously correct case was harmed.

Every projection receipt records the source frame and basis hashes, changed
field, before/after values, applied rule, and projected basis hash. Original
Provider receipts remain unchanged.

This replay used revealed calibration outputs. It supports the mechanism but
does not authorize fresh holdout consumption. v0.73 should freeze the combined
prospective runtime:

`Frame -> Local Surface Catalog -> Provider ID Binding -> Coordinate
Projection -> Deterministic Compiler`

Only a prospective calibration replay of that exact chain may authorize the
untouched 36-case holdout.
