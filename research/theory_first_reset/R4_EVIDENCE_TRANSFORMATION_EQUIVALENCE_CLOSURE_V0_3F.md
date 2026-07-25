# R4 Evidence Transformation Equivalence Closure v0.3F

## Formal Status

`PASS_SYNTHETIC_FORMAL_TRANSFORMATION_EQUIVALENCE`

Evidence coordinate:

`SYNTHETIC_FORMAL_AUDIT`

Claim ceiling:

`ATTRIBUTE_COMPILATION_COHERENCE_ONLY`

All 14 frozen gates passed. The result supports the internal coherence and
necessity of the frozen transformation-equivalence attributes on the finite
grid. It does not establish that a Provider can infer those attributes or that
the resulting equivalence is safe for natural evidence or future claims.

## Frozen Coordinate

- theory:
  `R4_EVIDENCE_TRANSFORMATION_EQUIVALENCE_THEORY_V0_3F.md`;
- authorization:
  `R4_EVIDENCE_TRANSFORMATION_EQUIVALENCE_AUTHORIZATION_V0_3F.json`;
- preregistration:
  `R4_EVIDENCE_TRANSFORMATION_EQUIVALENCE_PREREGISTRATION_V0_3F.md`;
- theory freeze commit: `b4a3e4d`;
- Provider calls: zero;
- CoreSlim, retention, and baseline writes: zero;
- existing relation states or actions modified: zero.

Before the first experiment execution, implementation inspection found that the
frozen removal test for a separate-pipeline witness required an explicit
`lineage_witness_ref`, while the initial unexecuted contract carried only the
lineage enum. The witness reference was added before any result exposure. No
case expectation, threshold, metric, compiler rule, or result artifact changed
after the first execution.

## Engineering Object

The standalone instrument remains modular:

| Module | Responsibility | Lines |
| --- | --- | ---: |
| `transform_contracts.py` | typed attributes and immutable receipts | 105 |
| `transform_cases.py` | frozen 18-case grid and six removals | 259 |
| `transform_compiler.py` | pure attribute-to-relation compilation | 122 |
| `transform_evaluation.py` | gates and diagnostic summaries | 187 |
| `transform_cli.py` | ignored artifact writing and hashes | 72 |

The compiler contains no case identifier, family, or transformation-name
branch. Changing only case identity and family leaves relation, action, and
errors unchanged. No module imports a Provider client, network library,
CoreSlim, retention, or baseline code.

## Formal Results

| Quantity | Result |
| --- | ---: |
| frozen gates | 14/14 |
| relation-state matches | 18/18 |
| Runtime-action matches | 18/18 |
| intended deduplications | 5/5 |
| unintended deduplications | 0 |
| removal or perturbation tests | 6/6 |
| Provider calls | 0 |
| protected writes | 0 |
| complete experiment tests | 52 passed |

The five deduplicated transformations were:

1. source renaming;
2. lossless compression;
3. exact unit conversion;
4. claim-preserving redaction;
5. calibrated conversion with error below an explicit claim tolerance.

The same source produced blocking actions for material calibration error,
aggregation, lossy summarization, model-derived scoring, stochastic
transformation, and distinct statistics. Therefore source identity alone does
not determine evidence equivalence.

## Removal Results

| Perturbation | Result |
| --- | --- |
| remove transformation witness | `UNRESOLVED -> BLOCK` |
| remove claim-tolerance witness | `UNRESOLVED -> BLOCK` |
| make calibration error material | `DEPENDENT_DISTINCT -> BLOCK` |
| change the redaction target claim | `SCOPE_INCOMPATIBLE -> BLOCK` |
| remove separate-pipeline witness | `UNRESOLVED -> BLOCK` |
| make subset source identity unknown | `UNRESOLVED -> BLOCK` |

These results show that deduplication is witness-bound and revocable. The
compiler does not treat a semantic label as sufficient authority.

## Deterministic Replay

Two complete runs were byte-identical:

| Artifact | SHA-256 |
| --- | --- |
| `result.json` | `017d96cf1f7faaff920d5bb1865d4cb2a4c13d8959a5576ff9b872163a055773` |
| `hash_inventory.json` | `5c07440c3c342cbabcdde50607b9dd321952b8f944a06cee1cad04e07c4ed4d3` |
| `closure.json` | `cf3599cfc9ef73286b5b3e332b9d533882252433ce01bf48c421aa76e80f95d7` |

Generated outputs remain ignored and are not promotion artifacts.

## Theory Interpretation

### Leading Model

`M1_ATTRIBUTE_COMPILATION_SUFFICIENCY` is supported on the frozen formal grid.
The five typed attributes compile the tested transformations into the existing
six relation states and action surface. A seventh relation state was not
required.

### Rival Models

- `M0_SOURCE_IDENTITY_SUFFICIENCY` is rejected on the formal grid. Same-source
  cases required both deduplicate and block actions.
- `M2_REPRESENTATION_IDENTITY_REQUIRED` is rejected on the formal grid. Exact
  unit conversion and bounded claim-preserving transformations safely compiled
  to deduplication despite different representations.
- `M3_NEW_RELATION_STATE_REQUIRED` is not supported by these cases. Existing
  states expressed every required action.
- `M4_TARGET_RELATIVE_EQUIVALENCE_UNSAFE` remains unresolved. The grid contains
  no future broader-claim reuse and cannot measure negative transfer.
- `M5_UNCERTAINTY_THRESHOLD_UNDERDEFINED` is addressed only structurally.
  Explicit tolerance and uncertainty witnesses are required, but their truth
  and quality were not tested.

## Experimental Phenomena

The central phenomenon is that equivalence is claim-relative rather than
packet-global:

```text
same source
  + verified transform
  + same target claim
  + immaterial uncertainty under an explicit tolerance
  -> exact duplicate for this composition
```

Changing only uncertainty materiality redirects the action to block. Removing
only a witness redirects it to unresolved. Changing only the target claim
redirects it to scope incompatibility.

This explains the preserved v0.3E `R43E-06` disagreement more precisely. Raw
telemetry and calibrated Celsius are not unconditionally duplicate or
distinct. Their relation depends on verified transformation lineage,
calibration uncertainty, the target claim, and an explicit tolerance.

## Negative Results And Boundaries

The experiment did not validate:

- semantic extraction of the five attributes from natural text;
- correctness of transformation or lineage witnesses;
- validity of a claim tolerance;
- future-scope safety of redaction or coarsening;
- cross-domain or cross-Provider transfer;
- CoreSlim integration readiness.

The safe Runtime object is therefore not merely an `EXACT_DUPLICATE` label. It
must preserve the target-claim, tolerance, transformation, uncertainty, and
lineage bindings that justified the label.

## Theory Update

The formal object is retained with one strengthened lifecycle implication:

`TransformationEquivalenceReceipt` must be scoped to its target claim and
tolerance. Reuse under a changed claim or expired witness must trigger
revalidation rather than inherit deduplication authority.

This implication is a candidate theory update, not an implemented Runtime
policy.

## Next Research Object

The next highest-information experiment is:

`R4_V0_3G_PROVIDER_TRANSFORMATION_ATTRIBUTE_INFERENCE`

It should test whether a Provider can infer the frozen attributes and identify
missing witnesses from fresh natural descriptions. The Provider must not emit
the final Runtime action. Runtime compiles only validated structured
attributes, and any missing or invalid binding fails closed.

Required theory work before calls:

1. freeze a fresh semantic corpus with no relation or action labels exposed;
2. bind target claim, transformation, uncertainty, tolerance, and lineage
   witnesses explicitly;
3. separate attribute accuracy from final action accuracy;
4. make false deduplication a hard failure;
5. include changed-claim and missing-witness counterfactual pairs;
6. preserve future-scope safety as `PENDING`, not inferred from this pass.
