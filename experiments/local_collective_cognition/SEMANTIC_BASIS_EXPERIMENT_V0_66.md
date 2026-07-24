# AgentOS Local Collective Cognition v0.66

## Window

This experiment inherits:

`TheoryBaseline + MethodologyKernel v1.1 + ExperimentSpecificSeed`

The research object is the **typed semantic basis between admitted evidence
and an outcome label**. v0.65 showed that better evidence admission can improve
evidence F1 while still producing the wrong claim. v0.66 therefore tests
whether explicit semantic coordinates can close that gap.

## Mechanism

The frozen comparison shares one span-admission receipt:

- `A1_DIRECT_BINDING`: the v0.65 baseline directly binds admitted evidence and
  predicts an outcome.
- `A2_TYPED_SEMANTIC_BASIS`: every admitted span receives one typed record for
  outcome, timepoint, measurement, comparison orientation, observed direction,
  significance basis, and material-ambiguity contribution. A separate global
  synthesis receipt consumes all records.

The candidate chain is:

`Object/Timepoint Binding -> Comparator Orientation -> Significance Basis ->
Material Ambiguity -> Outcome Label`

Local code validates completeness, hashes, state transitions, and consistency
between Provider receipts. It does not extract semantic coordinates from text.

## Calibration

Twelve already revealed v0.65 development cases are frozen: four per outcome
label and three known failures. The known failures are:

- `EI-CAL-11179`: a directional trend at `p=0.07` was promoted to an effect.
- `EI-CAL-5842`: the comparator-first statement was read in the wrong
  direction.
- `EI-CAL-13793`: admitted spans were omitted and measurement variants created
  material ambiguity.

The remaining nine cases are structurally matched significance, orientation,
or time/measurement controls. They are calibration cases, not fresh evidence.

## Fresh Holdout

Only a full calibration pass authorizes Provider execution on a frozen
36-case holdout from the previously unused Evidence Inference train split.
Selection is label-balanced and hash-deterministic after a public-text
challenge filter. No prompt or contract change is allowed after the first
semantic-basis receipt.

## Claim Boundary

- The public benchmark does not provide native gold labels for AgentOS
  semantic-basis coordinates or material ambiguity.
- Benchmark labels and rationale spans score downstream behavior only.
- `UNRESOLVED_MATERIAL_AMBIGUITY` counts as incorrect for exact label accuracy
  but is retained as an epistemic-safety outcome.
- Pretraining contamination is not excluded.
- No Core, memory, retention, baseline, or global pointer write is authorized.
