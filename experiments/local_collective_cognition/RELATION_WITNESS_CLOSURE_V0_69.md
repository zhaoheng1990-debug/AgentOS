# Relation Witness v0.69 Closure

## Decision

**CLOSED: calibration rejected; fresh holdout not executed.**

v0.69 required exact subject and relation surfaces for every evidence span.
All 12 frames passed, but only seven bases and compiled receipts survived.

| Metric | Baseline | v0.69 |
| --- | ---: | ---: |
| Valid receipts | 11/12 | 7/12 |
| Label accuracy | 0.7500 | 0.4167 |
| Evidence F1 | 0.9000 | 0.5833 |
| Effective Cbit | 0.8474 | 0.5278 |
| Tokens | 41,101 | 71,744 |

Five bases failed grounding: `13790`, `5842`, `13793`, `11179`, and `8861`.
The failures were concentrated in exact alias or relation-surface membership.

The important positive observation is `5842`: its primary span correctly
identified `less user control` as `FOCAL_COMPARATOR` and compiled the intended
relation coordinates. The whole receipt failed because its supporting
continuation span did not repeat that alias and full relation phrase.

The false assumption was therefore span self-sufficiency. Evidence passages
can form discourse units in which one span supplies the subject and another
supplies the predicate, statistics, or continuation.

v0.70 should retain local substring and alias checks but add a hash-bound
`anchor_span_id`. Continuation records may inherit subject identity only from
an admitted anchor whose exact witness is validated. This is stricter than
free contextual inference while matching the actual evidence structure.

Fresh holdout calls remained zero; CoreSlim and production state were
unchanged.
