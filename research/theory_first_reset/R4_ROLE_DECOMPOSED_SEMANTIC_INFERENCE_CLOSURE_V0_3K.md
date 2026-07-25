# R4 Role-Decomposed Semantic Inference Closure v0.3K

## Formal Status

`FAIL_GLOBAL_CONTEXT_REQUIREMENT`

Theory-qualified interpretation:

`NO_ROLE_DECOMPOSITION_BENEFIT_WITH_PRESENTATION_SENSITIVE_MULTI_WITNESS_BINDING`

Evidence coordinate:

`INTERNAL_PROJECT_PROVIDER_EVIDENCE_ON_FRESH_SYNTHETIC_CORPUS`

Claim ceiling:

`SAME_PROVIDER_MATCHED_FRESH_SYNTHETIC_RESPONSIBILITY_DECOMPOSITION_ONLY`

Thirteen of eighteen frozen gates passed. No prompt, corpus, reference,
threshold, compiler, scorer, or call order was changed after Provider exposure.

## Frozen Coordinate

- HumanGate freeze commit: `84b996a`;
- corpus and instrument freeze commit: `cc7f87a`;
- Provider and returned model: DeepSeek `deepseek-v4-flash`;
- logical calls: 8/8;
- physical attempts: 8/16;
- retries: zero;
- total tokens: 60078/100000;
- private surface exposed: false;
- extraction position exposed: false;
- Provider semantic coordinator: false;
- Provider relation, action, or revalidation authority: false;
- CoreSlim, retention, and baseline writes: zero.

Every call returned a mechanically valid receipt on its first attempt.

## Frozen Gate Result

Passed 13/18.

Failed gates:

1. split role-bundle gain;
2. split witness noninferiority;
3. split Runtime action accuracy;
4. split Runtime action noninferiority;
5. split forward-reverse action agreement.

Passed safety and boundary gates:

- exact call and receipt coverage;
- token budget;
- split semantic-attribute floor;
- split revalidation;
- zero false combine;
- zero false deduplicate;
- fail-closed mutations;
- forbidden-field exclusion;
- deterministic replay;
- zero protected writes and Provider decision authority.

## Role-Bundle Result

One exact role bundle requires all three role labels and all attribute-level
witness sets to be exact.

| Arm and round | Provenance | Effect-scope | Total |
| --- | ---: | ---: | ---: |
| wide forward | 14/16 | 16/16 | 30/32 |
| split forward | 14/16 | 16/16 | 30/32 |
| wide reverse | 15/16 | 15/16 | 30/32 |
| split reverse | 14/16 | 11/16 | 25/32 |

Matched split gain:

- forward: 0/32;
- reverse: -5/32.

The frozen leading model required at least +2/32 in both rounds. It is
rejected.

## Attribute And Witness Results

### Split Forward

Provenance labels:

- `SourceIdentity`: 14/16;
- `LineageCoupling`: 16/16;
- `TransformStatus`: 16/16.

Effect-scope labels:

- `InformationEffect`: 16/16;
- `AddedUncertainty`: 16/16;
- `TargetClaimRelation`: 16/16.

All split forward witness maps were exact.

### Split Reverse

Provenance labels:

- `SourceIdentity`: 14/16;
- `LineageCoupling`: 16/16;
- `TransformStatus`: 16/16.

Effect-scope labels:

- `InformationEffect`: 16/16;
- `AddedUncertainty`: 15/16;
- `TargetClaimRelation`: 16/16.

Effect-scope witness-bundle exactness fell from 16/16 to 12/16.

### Wide Control

The selected wide provenance source scored:

- forward: `SourceIdentity` 14/16, all other provenance labels 16/16;
- reverse: `SourceIdentity` 15/16, all other provenance labels 16/16.

The selected wide effect source scored:

- forward: all labels and witnesses 16/16;
- reverse: `AddedUncertainty` 15/16, all other labels 16/16, and all witnesses
  16/16.

The wide arm did not show the reverse-order witness omission.

## Runtime Outcomes

| Arm and round | Relation | Action | Revalidation | False combine | False deduplicate | False block |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wide forward | 16/16 | 16/16 | 16/16 | 0 | 0 | 0 |
| split forward | 16/16 | 16/16 | 16/16 | 0 | 0 | 0 |
| wide reverse | 15/16 | 16/16 | 16/16 | 0 | 0 | 0 |
| split reverse | 11/16 | 14/16 | 16/16 | 0 | 0 | 2 |

Split forward-reverse action agreement was 14/16. The frozen minimum was
15/16.

Runtime safety behavior remained correct:

- no incomplete receipt was promoted;
- no missing witness was invented;
- no invalid status-effect pair was repaired;
- missing evidence produced `UNRESOLVED -> BLOCK`.

## Primary Failure Mechanism

In split effect reverse, four semantically correct cases omitted the tolerance
witness from `AddedUncertainty`:

- `R43K-01`;
- `R43K-05`;
- `R43K-06`;
- `R43K-09`.

Each receipt cited the uncertainty statement but not the separate claim
tolerance statement.

Runtime therefore emitted:

```text
CLAIM_TOLERANCE_WITNESS_MISSING
  -> UNRESOLVED
  -> BLOCK
```

Consequences:

- `R43K-01` and `R43K-05`: two conservative false blocks instead of
  `DEDUPE_AND_COMBINE`;
- `R43K-06` and `R43K-09`: action remained `BLOCK`, but the relation became
  unsupported `UNRESOLVED`.

The corresponding wide reverse receipts included all four tolerance witnesses.

This is a multi-witness sufficiency failure. It is not a failure to infer
`TransformStatus`, `InformationEffect`, or the revalidation trajectory.

## Additional Case Boundaries

### Source Identity Ambiguity

`R43K-02` and `R43K-14` describe different records or entries within one
archive or manifest. Their private `SAME_SOURCE` labels are contestable under
the frozen definition “same source item or observation.”

Observed:

- `R43K-02` was classified `DISTINCT_SOURCE`;
- `R43K-14` varied among `DISTINCT_SOURCE`, `PARTIAL_SOURCE`, and
  `SAME_SOURCE` across calls.

This is a reference-ontology ambiguity and must not be treated as clean
Provider error.

Post-hoc sensitivity only:

- removing those two provenance bundles leaves forward split gain at 0;
- reverse split gain remains -4 because of tolerance-witness omissions.

The formal frozen score is unchanged.

### Undefined Versus Inapplicable Uncertainty

For `R43K-08`, both reverse arms inferred `UNKNOWN_UNCERTAINTY` where the
private reference was `NOT_APPLICABLE`.

The statement “no defined scalar conversion-error term” can support either
reading. The error affected both reverse arms and did not create the matched
role-decomposition difference.

## Presentation And Repeatability

The two wide calls in each round used identical prompts.

Canonical wide-call agreement:

- forward: 16/16 full attribute tuples and 16/16 reference maps;
- reverse: 16/16 full attribute tuples and 16/16 reference maps.

The two reverse wide raw responses were byte-identical. Forward raw formatting
differed, but canonical receipts were identical.

Split forward-reverse agreement:

- provenance full attribute tuple: 15/16;
- provenance reference map: 16/16;
- effect full attribute tuple: 15/16;
- effect reference map: 12/16.

The negative difference is therefore concentrated in split effect witness
binding under reversed presentation.

Case order, call time, and Provider backend drift remain partially confounded
because each split role has one call per round. The experiment does not prove
that missing global fields caused the failure.

## Cost

| Arm | Forward tokens | Reverse tokens | Mean per round |
| --- | ---: | ---: | ---: |
| wide paired | 17058 | 17062 | 17060 |
| split roles | 13000 | 12958 | 12979 |

Role decomposition reduced token use by approximately 23.92 percent.

This operational saving cannot compensate for failed cognition and action
gates.

Exact per-call latency was not instrumented. Latency therefore remains
unscored and cannot support a claim.

## Theory Adjudication

### M1 Responsibility-Bounded Interference

Rejected. Split role bundles did not improve in either round and degraded by
5/32 in reverse.

### M0 No Decomposition Benefit

Retained as the safer architecture conclusion. No positive decomposition
benefit was observed. Exact equivalence is not established because reverse
split performance was lower.

### M2 Context-Reset Benefit

Not supported. Both arms used two contexts, and the split arm did not improve.

### M3 Composition-Boundary Failure

Partially supported only as an evidence-sufficiency boundary. Local labels were
mostly correct, but missing tolerance witnesses caused fail-closed composition.

No invalid `TransformStatus + InformationEffect` pair occurred. This result
does not justify adding a general Provider semantic coordinator.

### M4 Global-Context Requirement

The frozen scorer emitted this formal classification because split bundle gain
was negative.

The broad causal interpretation is not established:

- forward wide and split arms were equal;
- the main reverse failures omitted witnesses already inside the effect role's
  admitted evidence;
- no missing provenance field was required to identify those witnesses.

### M5 Presentation Drift

Supported. Split effect witness completeness changed from 16/16 to 12/16 under
reversed presentation, while wide witness completeness remained 16/16.

The experiment cannot separate case order, call timing, and backend variation.

## Negative Result Classification

Primary:

`NO_IDENTIFIED_ROLE_DECOMPOSITION_COGNITIVE_BENEFIT`

Mechanism-localized:

`PRESENTATION_SENSITIVE_MULTI_WITNESS_BINDING`

Secondary:

`REFERENCE_ONTOLOGY_AMBIGUITY`

The result is not classified as:

- factorized ontology failure;
- Provider mechanical construction failure;
- Runtime safety-kernel failure;
- token-budget failure;
- general semantic-coordinator failure;
- collective-cognition failure.

## Theory Update

Semantic label inference and evidence-sufficiency binding must be separated as
different cognitive operations.

The next theory object should be:

`SEQUENTIAL_SEMANTIC_WITNESS_BINDING`

Candidate sequence:

```text
Provider semantic role
  -> typed semantic labels

Runtime witness-obligation derivation
  -> exact required evidence obligations
  -> for example uncertainty statement plus claim tolerance

Provider witness binder
  -> evidence refs for the frozen obligations only

Runtime
  -> validates refs
  -> composes and compiles
  -> fails closed
```

This is not authorization for another Provider call or a new Runtime module.
The next theory must distinguish:

- explicit obligation benefit;
- extra-context benefit;
- order and backend drift;
- reference-label ambiguity;
- token and latency cost.

It must include repeated counterbalanced cells or another valid variance
control before making a causal role claim.

## Artifacts

| Artifact | SHA-256 |
| --- | --- |
| result | `74f3f44161cf1d8bd463e7310399609c9e43bc9857d8c384f21c5cfe02758fbc` |
| attempt ledger | `0959a72af260b0a21c62494b671418f57cff483499188944c968924826d3c8b0` |
| inventory | `bd02a56f227a648ccc33619a121ebff460618c0265d65c877c97a581a18ed2f4` |
| closure receipt | `7da3b08b374e539259aba599b61c050313e84fefce6e34fde755a8eab64ebe67` |
| split effect forward raw | `88c832a8d01433a59b34cacdcc2439a7707d0efb8b86fa552023937df36bff09` |
| split effect reverse raw | `a08fc5a2e7760846c7999cae1f8f5b3cee9c1d69d4c027216ebe8f8748a72578` |
| split provenance forward raw | `aa9ef2aa98432fc28d8a9aa4bf3efae647a0b5c1b0564d0ef4b28b517540dd5f` |
| split provenance reverse raw | `43c669a94e66627a4531a75238c6b7f0d60572240d9b5b5d2f8401c1776a7f22` |
| wide effect forward raw | `2854ba92ebfba846735f59038943b35a35c129c0a167d563b7051fd35b83ac39` |
| wide effect reverse raw | `065ad48bf25831aa639cef1b35e664056fbbe561a498334b79c1ba32e138cae2` |
| wide provenance forward raw | `712859d00cfcd5e01f896b9709afa4ef031c6e4b261a2683229b37300fec9b09` |
| wide provenance reverse raw | `065ad48bf25831aa639cef1b35e664056fbbe561a498334b79c1ba32e138cae2` |

## Validation

- corpus audit: 17/17;
- targeted role-decomposition tests: 15 passed;
- complete R4 experiment suite after Provider run: 86 passed;
- AgentOS CoreSlim suite: 394 passed;
- deterministic result replay: byte-identical;
- Provider calls after closure: paused;
- promotion authority: false.
