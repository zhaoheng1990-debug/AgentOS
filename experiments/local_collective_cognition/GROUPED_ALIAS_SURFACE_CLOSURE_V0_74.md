# Grouped Alias Surface Runtime v0.74 Closure

## Decision

**PASS on frozen prospective calibration; fresh holdout is authorized but has
not been executed.**

v0.74 added one narrow mechanism to the v0.73 prospective chain: a local,
deterministic grouped-object alias normalizer. It can split immutable arm
catalog text on comma, semicolon, or pipe delimiters. It cannot invent
synonyms, consume Provider-proposed additions, or change the canonical object.

| Metric | Baseline | v0.73 | v0.74 |
| --- | ---: | ---: | ---: |
| Valid receipts | 11/12 | 11/12 | 12/12 |
| Label accuracy | 0.7500 | 0.9167 | 1.0000 |
| Evidence F1 | 0.9000 | 0.8722 | 0.9556 |
| Effective Cbit | 0.8474 | 0.8833 | 0.9666 |
| Provider tasks | 0 | 23 | 24 |
| Physical tokens | 0 | 226,128 | 245,682 |

All frozen gate conditions passed. The run corrected `11179`, `13793`, and
`5842`, harmed no baseline-correct case, restored `3189=DECREASED`, and
preserved the required `6743` and `8861` labels. Provider and compiler
contract failures were both zero.

Three calibration objects activated deterministic grouping:

- `13790` and `13793`: `expert system-based, print-delivered physical activity
  intervention`;
- `3189`: `Kuntai, Tibolone, Control`.

The v0.73 rejected `3189` receipt passed the new contract because all three
member aliases were recoverable from the immutable canonical arm string. An
unlisted synonym remains rejected.

## Interpretation

v0.72 achieved the same final metrics by replaying already revealed Provider
outputs. v0.74 achieved them after a complete new 24-task Provider execution.
This converts the coordinate-projection and surface-binding result from
positive replay evidence into positive prospective calibration evidence.

It is still calibration evidence, not fresh generalization evidence. The
36-case holdout hash remains unchanged and no holdout Provider call has been
made. The next version should freeze a descriptive holdout protocol before
execution, prohibit further mechanism changes, and report corrections, harms,
Cbit, and token cost whether the result is positive or negative.

No CoreSlim, retention, accepted baseline, or production state was changed.
