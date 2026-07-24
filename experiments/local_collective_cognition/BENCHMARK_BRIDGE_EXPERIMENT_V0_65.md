# AgentOS Local Collective Cognition v0.65

## Window

This experiment inherits:

`TheoryBaseline + MethodologyKernel v1.1 + ExperimentSpecificSeed`

The research object is the **evidence objectification mechanism**: whether a
Provider-backed runtime can turn candidate passages into a stable,
object-bound evidence receipt before it performs relation typing and outcome
classification.

## Source Boundary

- Evidence Inference is pinned to commit
  `a661e8c14f973398380c8865cf2f27a535aaaf6d` under its MIT license.
- ERASER metric semantics are referenced at commit
  `36467f1662812cbd4fbdd66879946cd7338e08ec` under Apache-2.0.
- Raw benchmark files are cached outside this repository under
  `%LOCALAPPDATA%\AgentOS\benchmark_cache`.
- The nine-case panel is a development calibration derived from the Evidence
  Inference validation split. It is not a benchmark-native end-to-end score.
- Pretraining contamination is not excluded, so this window cannot establish a
  fresh generalization claim.

## Frozen Comparison

- `A0_ONE_PASS`: classify the outcome and partition all candidate spans in one
  semantic receipt.
- `A1_STAGED_ADMISSION_BINDING`: first admit or reject every span, then type
  only the admitted evidence and classify the outcome.

The panel contains three increased, three decreased, and three no-difference
cases. Gold labels and rationale memberships remain private to scoring.
Provider prompts receive only the PICO object and shuffled candidate spans.
Before any Provider call, prompt `5964` was excluded because its article
offered only one eligible distractor; prompt `1113` replaced it under the same
split, label, and two-gold/two-distractor eligibility rule.
The same pre-call rule replaced prompt `6203` with prompt `866`.

## Gate

The staged arm must have zero contract failures and zero cross-type overlap,
score at least 8/9 labels, reach at least 0.80 evidence F1 and rationale token
F1, and not regress from the one-pass arm on label or rationale quality.
It must also produce a positive mechanism delta through higher effective Cbit
or fewer contract/overlap failures. Effective Cbit per 1,000 tokens must
remain positive. Token cost is secondary to stable positive Cbit.

No prompt may change after the first semantic receipt. Failure closes v0.65 as
a preserved negative result. Only a full calibration pass authorizes freezing
a separate external benchmark-transfer holdout.

## Authority

This experiment is local, candidate-only, and outside AgentOS Core. It cannot
write production memory, retention state, baseline state, or global pointers.
