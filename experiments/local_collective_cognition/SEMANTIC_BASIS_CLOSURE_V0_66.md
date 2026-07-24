# Typed Semantic Basis v0.66 Closure

## Decision

**CLOSED: calibration rejected; fresh holdout not executed.**

v0.66 tested whether explicit semantic coordinates could convert v0.65's
cleaner evidence admission into more reliable outcome decisions. The answer is
bounded: the typed basis produced useful intermediate cognition, but a second
free-form Provider synthesis did not reliably obey that basis.

## Architecture

The candidate used one shared v0.65 admission receipt and two new stages:

1. `A2_SEMANTIC_BASIS` produced exactly one record per admitted span for
   outcome binding, timepoint, measurement, comparison orientation, observed
   direction, significance state, admissibility, and ambiguity axes.
2. `A2_SEMANTIC_SYNTHESIS` consumed all basis records and emitted a final label
   or `UNRESOLVED_MATERIAL_AMBIGUITY`.

Local runtime code checked schema, exact span coverage, hashes, partition
completeness, admissibility-state mapping, orientation normalization, and
significance consistency. It did not extract semantic fields from text.

## Frozen Window

- Development calibration: 12 revealed v0.65 challenge cases, four per label.
- Known failures: `11179` significance, `5842` comparator orientation, and
  `13793` material ambiguity/completeness.
- Fresh holdout: 36 balanced challenge cases from the previously unused
  Evidence Inference train split.
- Fresh holdout Provider execution: **0 calls**, blocked by calibration gate.
- Raw benchmark data in repository: **0 files**.

## Calibration Result

| Metric | A1 direct binding | A2 typed semantic basis |
| --- | ---: | ---: |
| Valid final receipts | 11/12 | 10/12 |
| Total candidate failures | 1 | 2 |
| Label accuracy | 0.7500 | 0.6667 |
| Evidence F1 | 0.9000 | 0.7889 |
| Rationale token F1 | 0.8922 | 0.7777 |
| Effective Cbit | 0.8474 | 0.7444 |
| Tokens | 41,101 | 64,868 |
| Cbit / 1k tokens | 0.2474 | 0.1377 |

All 12 typed basis receipts were structurally complete. Ten synthesis receipts
passed the hard consistency gate; two were rejected. Among valid candidate
receipts, eight of ten labels were correct.

## Observed Mechanisms

### Significance Boundary Worked

`EI-CAL-11179` was corrected. The basis recorded lower directional values but
`NOT_SIGNIFICANT` for `p=0.07` and `p=0.12`; synthesis returned
`NO_DIFFERENCE`. This supports keeping significance as a first-class
coordinate.

### Orientation Basis Worked, Synthesis Ignored It

For `EI-CAL-5842`, both records correctly stated
`COMPARATOR_VS_INTERVENTION + HIGHER + SIGNIFICANT`. Normalization therefore
requires `DECREASED` for the focal intervention. Synthesis returned
`INCREASED`; the mechanical consistency gate blocked it. The semantic work was
done correctly, then discarded by a redundant free-form decision stage.

### Multi-Arm Comparison Frame Failed

`EI-CAL-3189` contains a compound intervention string:
`Kuntai, Tibolone, Control`, with comparator `baseline`. The basis assigned
`COMPARATOR_VS_INTERVENTION + LOWER`, which mechanically implies `INCREASED`,
while synthesis selected the benchmark's `DECREASED`. This is not merely a
label error. The binary intervention/comparator object is inadequate for a
multi-arm study and must be normalized before passage interpretation.

### Ambiguity Was Both Useful and Over-Triggered

`EI-CAL-13793` separated borderline accelerometer results from significant
alternative measurement results and returned unresolved measurement
ambiguity. This is epistemically safer than forcing an increase.

`EI-CAL-9330`, however, treated explicit passage timepoints as different from a
query that did not specify a timepoint. It abstained where the baseline was
correct. The runtime needs an explicit distinction between:

- query requires a particular timepoint;
- query leaves timepoint unconstrained;
- passage refers to a genuinely different timepoint.

## Interpretation

Adding typed fields is not sufficient if a later Provider can freely override
them. v0.66 demonstrates two distinct failure loci:

1. **Frame construction failure**: the comparison object is wrong or
   under-specified before evidence interpretation.
2. **Basis-to-decision failure**: the basis is correct but synthesis does not
   obey its orientation or significance implications.

The consistency gate was valuable precisely because it prevented these
internally contradictory receipts from becoming valid candidates. The right
next step is not another review role or a longer synthesis prompt.

## Claim Boundary

- Supported: per-span typed basis can expose significance, orientation, and
  measurement distinctions that direct binding misses.
- Supported: a hard consistency gate prevents basis-contradicting promotion.
- Rejected: the full v0.66 chain improves calibration accuracy or Cbit.
- Not tested: fresh holdout transfer.
- Not claimed: native Evidence Inference performance or pretraining-fresh
  generalization.
- Not authorized: Core, memory, retention, baseline, or pointer writes.

## Verification

- Focused v0.66 tests: 15 passed.
- Full local collective cognition pack: 442 passed.
- AgentOS CoreSlim: 394 passed.
- Largest v0.66 semantic module: 202 lines.
- CoreSlim version: `0.4.0-alpha.21`.

## Next Candidate

v0.67 should replace free synthesis with:

`ComparisonFrameReceipt -> TypedBasisReceipt -> DeterministicBasisCompiler`

`ComparisonFrameReceipt` must represent study arms, focal contrast,
timepoint requirement, and measurement requirement before any evidence span is
typed. The compiler should mechanically emit a candidate label or abstention
from Provider-backed coordinates. A Provider may identify conflict or missing
coordinates, but it must not override the compiled orientation and
significance result.

The frozen v0.66 fresh holdout remains unused and can be retained for v0.67 if
the new mechanism first passes development calibration without changing its
selection.
