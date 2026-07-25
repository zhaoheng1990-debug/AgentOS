# Fresh Holdout v0.75 Closure

## Decision

**BLOCKED_BY_ADMISSION_CONTRACT before candidate execution.**

v0.75 froze the untouched 36-case holdout, the successful v0.74 calibration
lineage, the unchanged mechanism sources, symmetric cost accounting, and
paired statistical interpretation before making any Provider call.

The staged baseline stopped the experiment:

| Observation | Result |
| --- | ---: |
| Expected admission receipts | 36 |
| Valid admission receipts | 34 |
| Valid baseline binding receipts | 32 |
| Contract failures | 4 |
| Provider tasks | 70 |
| Physical tokens | 117,642 |
| Candidate tasks | 0 |
| Private-gold scoring | 0 |

The candidate runtime was not started. Fresh generalization is therefore not
assessable, and the result must not be described as either positive or
negative transfer.

## Failure anatomy

`EI-CAL-13742` returned `ADMISSION_EMPTY`. The Provider assessed every span
and found that none simultaneously matched sitagliptin, placebo, and vascular
resistance. This is a potentially correct null-evidence judgment, but the old
contract requires at least one admitted span and treats absence as malformed.

`EI-CAL-4226` returned `ADMISSION_REJECT_RELATION_CONFLICT`. A contextual span
was rejected because it did not mention the target outcome. The old contract
requires every rejected span to be `IRRELEVANT`, conflating evidence relevance
with admission disposition.

`EI-CAL-11049` and `EI-CAL-6806` returned
`SPAN_PARTITION_INCOMPLETE`. Their binding receipts selected effect-bearing
spans but omitted admitted contextual spans because the old output model has
no explicit non-decisive context partition.

## Interpretation

The bottleneck has moved upstream. Surface ID binding, coordinate projection,
and deterministic compilation cannot be evaluated if the evidence-admission
layer cannot represent:

- no applicable evidence after complete assessment;
- contextual but non-effect-bearing evidence;
- admitted context that must remain visible without being forced into primary,
  corroborating, or counter-evidence roles.

This is not a reason to weaken fail-closed validation. It is evidence that the
admission ontology is too narrow.

## Next experiment

v0.76 should use a new development calibration panel, not this holdout. It
should separate three axes:

1. object relation: exact, contextual, or irrelevant;
2. evidentiary utility: effect-bearing, context-only, or none;
3. disposition: admit as evidence, retain as context, or reject.

It should also add a typed `NO_APPLICABLE_EVIDENCE` receipt and an explicit
`context_span_ids` partition. The compiler must abstain rather than force an
effect label when no applicable evidence exists.

Only after that contract passes new calibration should a different untouched
holdout be selected. The v0.75 holdout is consumed at the admission stage and
must not be rerun for a formal generalization claim.

No private gold was scored, no candidate execution occurred, and no CoreSlim,
retention, accepted baseline, or production state was changed.
