# Prospective Surface Runtime v0.73 Closure

## Decision

**REJECT on frozen prospective calibration; fresh holdout remains untouched.**

v0.73 prospectively executed the complete mechanism proposed by v0.72:

`Frame -> Local Surface Catalog -> Provider ID Binding -> Coordinate
Projection -> Deterministic Compiler`

Unlike the v0.72 replay, both Provider-backed stages were re-executed without
access to prior Provider outputs or private gold.

| Metric | Baseline | v0.72 replay | v0.73 prospective |
| --- | ---: | ---: | ---: |
| Valid receipts | 11/12 | 12/12 | 11/12 |
| Label accuracy | 0.7500 | 1.0000 | 0.9167 |
| Evidence F1 | 0.9000 | 0.9556 | 0.8722 |
| Effective Cbit | 0.8474 | 0.9666 | 0.8833 |
| Provider tasks | 0 | 0 added | 23 |
| Physical tokens | 0 | 0 added | 226,128 |

The prospective chain corrected `11179`, `13793`, and `5842`, preserving the
three key gains first observed in v0.71. It also produced all five
pre-registered required labels and stayed within task, attempt, and token
budgets.

It did not pass the full gate. `EI-CAL-3189` failed at the frame contract:

`WITNESS_INTERVENTION_ALIASES_UNGROUNDED`

The local arm catalog represented the grouped intervention canonically as
`Kuntai, Tibolone, Control`. The Provider returned the individually grounded
aliases `Kuntai`, `Tibolone`, and `Control`. The frozen contract accepted only
aliases grounded as complete catalog strings, so the valid grouped-object
decomposition was rejected before surface binding. This missing receipt became
the only harmed case and lowered aggregate evidence F1.

## Interpretation

The positive Cbit delta is real but insufficient for authorization. It shows
that the prospective mechanism retained substantial correction value, while
the rejection localizes the next bottleneck to object normalization rather
than label semantics, coordinate projection, or deterministic compilation.

The next experiment should add a local, deterministic grouped-object alias
normalizer before witness validation. It should recognize delimiter-separated
members only when every member is recoverable from the immutable canonical arm
text. It must not introduce semantic synonyms or let Provider output expand
the catalog.

That change requires a new preregistered calibration version. v0.73 remains
frozen and rejected. No fresh holdout call was made, and no CoreSlim,
retention, or production state was changed.
