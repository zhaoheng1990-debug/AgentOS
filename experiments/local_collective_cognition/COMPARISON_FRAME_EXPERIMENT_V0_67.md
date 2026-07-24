# AgentOS Local Collective Cognition v0.67

## Research Object

v0.67 tests whether a comparison frame and a deterministic basis compiler can
close the gap exposed by v0.66. The object is not a better final-answer prompt.
It is the authority boundary between Provider-backed semantic parsing and a
locally replayable decision.

The frozen chain is:

`Shared Admission -> ComparisonFrameReceipt -> FrameBoundBasisReceipt ->
DeterministicBasisCompiler`

The Provider may identify study arms, focal contrast, timepoint, measurement,
direction, significance, and conflict. It cannot submit or override the final
label.

## Comparison Frame

Each frame must bind:

- study arms and focal intervention/comparator members;
- binary, grouped, multi-arm, or within-group baseline contrast;
- normalization rule;
- exact, implicit, unconstrained, or unresolved timepoint;
- exact, implicit, unconstrained, or unresolved measurement.

A query that does not name a timepoint or measurement is unconstrained. An
explicit passage coordinate is therefore allowed rather than contradictory.

## Compiler

The zero-Provider compiler:

- reverses comparator-first directional evidence mechanically;
- maps non-significant or borderline directional results to `NO_DIFFERENCE`;
- uses only exact, frame-compatible basis records;
- partitions every admitted span;
- abstains on unresolved frames, missing key coordinates, or mixed effects;
- emits a hash-bound receipt that must replay byte-for-byte.

## Frozen Evaluation

The development calibration reuses the 12 revealed v0.66 cases and their
shared admission receipts. The 36-case train-split holdout is reused without
selection changes and remains inaccessible until every calibration gate
passes.

No Core, memory, retention, baseline, or pointer write is authorized.
