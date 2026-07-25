# R4 Sequential Semantic-Witness Binding Theory v0.3L

## Identity

- packet id: `R4_SEQUENTIAL_SEMANTIC_WITNESS_BINDING_V0_3L`;
- theory baseline: `Cognitive Research Architecture v3.7`;
- methodology: `MethodologyKernel v1.1`;
- research object: `EVIDENCE_SUFFICIENCY_OBLIGATION`;
- evidence coordinate:
  `MODEL_INFERENCE_FROM_INTERNAL_PROJECT_PROVIDER_EVIDENCE`;
- status: `REVIEW_READY_HUMAN_FREEZE_REQUIRED`.

This window inherits MethodologyKernel v1.1.
If any experimental conclusion conflicts with this kernel, the conflict must be
explicitly stated and converted into a theory revision, downgrade, or caveat.

No Provider call, fresh corpus, experiment implementation, Runtime module, or
baseline write is authorized by this document.

## Inherited Evidence

### R4 v0.3K

The matched role-decomposition experiment closed 13/18:

- forward wide and split role bundles tied at 30/32;
- reverse wide remained 30/32 while split fell to 25/32;
- split effect reverse retained nearly exact semantic labels;
- four correct `AddedUncertainty` labels omitted the separate claim-tolerance
  witness;
- Runtime correctly emitted
  `CLAIM_TOLERANCE_WITNESS_MISSING -> UNRESOLVED -> BLOCK`;
- two conservative false blocks occurred;
- false combine and false deduplicate remained zero;
- revalidation remained 16/16 in both split rounds;
- split calls used 23.92 percent fewer tokens;
- source and uncertainty private references exposed two ontology ambiguities.

The main unresolved object is not another semantic role. It is how a Runtime
turns accepted semantic premises into explicit evidence-sufficiency
requirements before asking Provider to bind evidence.

### Earlier Binding Evidence

Internal v0.62-v0.63 work established a bounded typed-evidence mechanism:

- v0.62 stopped at 11/12 valid binding receipts and 20/30 strict relation
  consensuses;
- v0.62.1 recovered 12/12 receipts and 28/30 consensuses after moving
  `binding_state` derivation to Runtime and treating exact versus coreference
  as coarse bound identity;
- the remaining disagreements concerned primary versus corroborating evidence;
- v0.63 used typed evidence roles, strict primary-evidence consensus, and
  typed auxiliary union;
- v0.63 completed 12/12 binding receipts, 30/30 relation consensuses, 12/12
  state receipts, and zero state-reference mismatch in 24 calls and 82847
  tokens.

That evidence is a revealed-case mechanism calibration. It does not establish
fresh transfer, low-cost sufficiency, or the v0.3L obligation interface.

### Earlier Sequential-Role Failures

v0.88 tested sequential `EvidenceSet -> ClaimScope` roles:

- recall increased;
- F1 fell from 0.6667 to 0.5957;
- harmful strong candidates increased from one to three;
- cost increased from 36967 to 96051 tokens;
- downstream review amplified upstream framing.

v0.89 reduced apparent harm through fail-closed suppression but retained only
1/12 correct strong candidates.

Therefore v0.3L must not give a downstream Provider authority to reinterpret
claim scope, semantic labels, or final utility.

## Object Chain

```text
Constraint-guided effective compression
  -> accepted typed semantic premise
  -> Runtime-derived evidence-sufficiency obligations
  -> Provider-backed obligation-to-evidence binding
  -> deterministic obligation validation
  -> relation, action, and revalidation readbacks
```

Observable chain:

```text
Explicit obligation guidance
  -> exact obligation coverage and witness precision
  -> fail-closed compilation and order stability
```

The experiment may update only:

`OBLIGATION_GUIDED_TYPED_EVIDENCE_BINDING`

It cannot establish:

- semantic-inference accuracy;
- independent cognitive agents;
- collective cognition;
- general Provider coordination;
- natural-evidence transfer;
- production Runtime value;
- retention or baseline readiness.

## Object Definition

An evidence-sufficiency obligation is:

```text
EvidenceObligation
= PremiseRef
+ ObligationType
+ EvidenceScope
+ CardinalityRule
+ SufficiencyPredicate
```

Where:

- `PremiseRef` identifies the accepted semantic label that creates the
  obligation;
- `ObligationType` identifies what must be evidenced;
- `EvidenceScope` bounds admissible case-local evidence;
- `CardinalityRule` states whether one or multiple evidence roles are needed;
- `SufficiencyPredicate` is the deterministic validation rule.

The obligation says what evidence relation is required. It does not decide
which admitted passage satisfies that relation.

## Runtime And Provider Boundary

### Runtime

Runtime may derive an obligation only when the mapping from an accepted typed
premise to a witness requirement is already deterministic and frozen.

Examples:

```text
AddedUncertainty = IMMATERIAL_FOR_CLAIM
  -> UNCERTAINTY_WITNESS
  -> CLAIM_TOLERANCE_WITNESS

AddedUncertainty = MATERIAL_FOR_CLAIM
  -> UNCERTAINTY_WITNESS
  -> CLAIM_TOLERANCE_WITNESS

InformationEffect = GLOBAL_EQUIVALENT
  -> INFORMATION_EFFECT_WITNESS
  -> FULL_DOMAIN_WITNESS

InformationEffect = CLAIM_EQUIVALENT
  -> INFORMATION_EFFECT_WITNESS
  -> CLAIM_SCOPE_OR_TOLERANCE_WITNESS

LineageCoupling != NOT_APPLICABLE
  -> LINEAGE_WITNESS
```

Runtime:

- generates the exact obligation set;
- binds obligations to case and semantic-premise hashes;
- validates exact obligation coverage;
- validates case-local refs and duplicate/conflict rules;
- compiles deterministic consequences;
- fails closed on missing or conflicting obligations.

Runtime does not choose which evidence semantically satisfies an obligation.

### Provider

Provider:

- receives admitted evidence, frozen semantic premises, and obligation
  contracts;
- selects evidence refs that satisfy each obligation;
- may return `UNRESOLVED` when admitted evidence is insufficient;
- cannot alter a semantic label;
- cannot add or remove an obligation;
- cannot emit relation, action, revalidation, acceptance, retention, or
  promotion state.

## Why This Is Not Mechanical Outsourcing

Runtime remains the cognitive subject because it owns:

- the target semantic state;
- the obligation-generating meta-rule;
- admitted evidence scope;
- conflict and sufficiency rules;
- fail-closed behavior;
- final candidate state.

Provider supplies the semantic correspondence:

```text
Does evidence item E actually satisfy obligation O?
```

Local code cannot answer that correspondence from string identity alone.

## Compared Arms

Both arms receive:

- identical fresh public evidence;
- identical frozen typed semantic premises;
- identical case order;
- one isolated Provider context per call;
- identical admissible evidence refs;
- identical final deterministic compiler;
- no private expected witness set;
- no action or state authority.

### Generic Binding Control

The control receives the current per-attribute request:

```text
For each semantic field, cite the admitted evidence refs that support it.
```

It does not receive an explicit Runtime obligation list.

### Obligation-Guided Binding

The candidate receives:

- the same semantic fields;
- Runtime-derived obligation IDs;
- the required evidence role for each obligation;
- the same admitted evidence scope.

It returns only:

```text
obligation_id -> evidence refs | unresolved
```

The candidate does not receive the private expected refs.

## Semantic Premise Boundary

v0.3L supplies the typed semantic labels as public task premises.

This is intentional:

- the unresolved object is witness sufficiency given a semantic premise;
- allowing Provider to infer labels again would reintroduce v0.3K's upstream
  semantic variable;
- the experiment therefore makes no semantic-inference claim.

A later composed validation must replace supplied premises with independently
validated Provider semantic receipts. v0.3L cannot authorize that transfer.

## Theoretical Readbacks

For case `c`, let `O_c` be the Runtime-derived obligation set and `R_c` the
Provider binding receipt.

Exact obligation coverage:

```text
CoverageExact(c) = 1
iff every obligation in O_c appears exactly once in R_c
```

Exact witness set:

```text
WitnessExact(c) = 1
iff each obligation is bound to the private expected evidence-ref set
```

False witness:

```text
FalseWitness(c)
= selected admitted evidence that does not satisfy its obligation
```

Operational readbacks:

```text
RelationExact
ActionExact
RevalidationExact
FalseCombine
FalseDeduplicate
FalseBlock
```

Stability readbacks:

```text
ReplicateAgreement
ForwardReverseAgreement
ObligationSetDrift
WitnessSetDrift
```

The result remains a vector:

```text
(coverage, precision, state, action, harm, stability, tokens, latency)
```

No cost scalar may compensate for false evidence or harmful certainty.

## Possibility Space

### M1 Obligation Externalization Benefit

Provider omits required witnesses because the semantic label and its proof
obligations remain implicit in one receipt. Runtime-externalized obligations
improve exact witness binding and order stability without increasing false
witnesses or harmful actions.

Expected signature:

- guided exact witness sets exceed generic binding in both case orders;
- tolerance and full-domain multi-witness cases show the largest gain;
- guided replicate and order agreement improve;
- false witness remains zero;
- Runtime action accuracy is not lower;
- cost may rise or fall but remains within budget.

### M0 Generic Binding Is Sufficient

Per-attribute evidence requests already make the obligation clear. Explicit
obligations add no stable information or operational benefit.

### M2 Obligation Overconstraint

Explicit obligations pressure Provider to fill every slot even when admitted
evidence is insufficient.

Expected signature:

- nominal coverage rises;
- false witness, weak-evidence filling, or harmful action rises;
- `UNRESOLVED` precision falls.

### M3 Runtime Obligation Projection Failure

The semantic premise does not determine a unique evidence obligation, or the
frozen obligation generator creates the wrong requirement.

Expected signature:

- formal oracle obligations disagree with the compiler-derived set;
- an obligation exception is needed for individual cases;
- Provider performance is unscorable.

This is a construction or object failure, not Provider failure.

### M4 Supplied-Premise Anchoring

Obligation guidance works only because the experiment gives Provider the
correct semantic label. The benefit may disappear when labels are uncertain or
wrong.

v0.3L cannot reject this rival. It is preserved as the transfer boundary.

### M5 Presentation Or Backend Drift

Apparent arm gain is caused by case order, call timing, caching, or backend
variation.

Two separated replicates per arm and order test this rival.

### M6 Reference-Ontology Ambiguity

Private expected witness sets are not uniquely warranted by the public
evidence.

Expected signature:

- multiple evidence sets satisfy the same obligation;
- independent reference audit disagrees;
- errors concentrate in contested cases rather than arm.

## Minimal Experimental Operator

The smallest admissible Provider experiment uses:

- twenty fresh cases;
- five tolerance-pair obligation cases;
- five domain-or-claim-scope obligation cases;
- five provenance-chain obligation cases;
- five null or unknown-sufficiency cases;
- supplied typed semantic premises;
- private exact obligation and evidence-ref references;
- two arms;
- forward and reverse case orders;
- two separated replicates per arm and order;
- eight logical calls total;
- no Provider semantic coordinator;
- no Provider state assessor;
- no role consensus;
- no debate, challenger, or veto stage.

Call order:

```text
generic_forward_a
obligation_forward_a
obligation_reverse_a
generic_reverse_a
generic_reverse_b
obligation_reverse_b
obligation_forward_b
generic_forward_b
```

This symmetric schedule separates identical-condition replicates in time and
counterbalances arm and case order.

Replicates are measurement cells only. They may not be voted, merged, selected
by hindsight, or composed into a stronger action receipt.

## Discriminating Predictions

The leading model requires all of the following:

1. twenty mechanically valid receipts in every call;
2. zero semantic-label mutation or Provider state field;
3. guided exact obligation coverage at least 19/20 in every call;
4. guided exact witness sets exceed generic by at least 4/40 aggregated cases
   in both forward and reverse order;
5. guided false-witness count is zero;
6. guided exact Runtime action is at least 19/20 in every call;
7. guided action accuracy is not lower than generic in either order;
8. guided false combine and false deduplicate are zero;
9. guided within-condition replicate agreement is at least 19/20;
10. guided forward-reverse witness agreement is at least 19/20 after frozen
    replicate pairing;
11. every missing or conflicting obligation fails closed;
12. all obligation-generator formal audits pass before Provider exposure;
13. deterministic replay is byte-identical;
14. exact per-call token, latency, caching, model, and attempt telemetry is
    recorded;
15. the frozen call and token budget is not exceeded;
16. Provider decision authority and protected writes are zero.

M1 is rejected as stated if any leading-model requirement fails.

The result is construction failure rather than M1 rejection if:

- Runtime obligations do not match formal references;
- an arm receives different evidence or premises;
- private expected refs leak;
- a semantic label can change;
- a threshold, prompt, or obligation rule changes after exposure.

## Engineering Derivation Contract

| Engineering object | Frozen theory variable | Rival discrimination | Minimality | Removal test | Authority |
| --- | --- | --- | --- | --- | --- |
| obligation projector | `O_c` | M1 vs M3 | pure projection from existing typed labels | remove and recover generic control | experiment only |
| generic binding schema | control witness behavior | M1 vs M0 | existing per-attribute ref shape | candidate becomes uninterpretable without control | experiment only |
| obligation binding schema | explicit sufficiency contract | M1 vs M2 | obligation ID, refs, unresolved only | remove obligation content and recover control | experiment only |
| deterministic validator | coverage, precision, conflict | all | no semantic inference | oracle receipts remain replayable | experiment only |
| factor compiler adapter | relation, action, revalidation | operational readback | reuse existing compiler | binding metrics remain independently scorable | experiment only |
| telemetry timer | latency and backend drift | M5 | monotonic duration plus existing usage | cognition scores remain unchanged | audit only |

Explicitly excluded:

- new CoreSlim typed-evidence module;
- parallel Provider roles;
- Provider coordinator;
- binding consensus;
- claim-scope reviewer;
- state assessor;
- challenger or veto;
- new relation or action state;
- retention or baseline write.

## Relationship To Existing Typed Evidence

v0.3L does not replace the existing typed-evidence contract.

It tests a missing interface:

```text
accepted semantic premise
  -> explicit Runtime evidence obligation
  -> Provider evidence binding
```

Existing typed evidence distinguishes primary, corroborating,
counterevidence, and gap evidence after binding. v0.3L asks whether making the
required evidence role explicit before binding improves fresh-case
sufficiency.

No Core synchronization is eligible unless a fresh test passes and HumanGate
later approves a separate contract audit.

## Validation Versus Discovery Boundary

Before exposure, freeze:

- twenty-case public corpus;
- supplied semantic premises;
- exact private obligations and witness sets;
- obligation-projection rules;
- generic and guided prompts;
- schemas and call order;
- reference ambiguity audit;
- telemetry and token budgets;
- compiler, scorer, and test hashes;
- all thresholds above.

After exposure:

- raw responses are immutable;
- no witness may be inserted;
- no obligation may be relabeled;
- no private reference may be broadened;
- no disputed case may be silently removed;
- no same-version prompt or threshold repair is allowed.

## Cbit And Cost

Expected theory gain:

```text
implicit proof obligation
  versus explicit Runtime obligation
  versus overconstraint
  versus obligation-projection failure
  versus presentation drift
```

Each outcome changes architecture:

- M1 supported -> ephemeral obligation-guided binding becomes a candidate
  interface;
- M0 supported -> keep generic evidence binding and add no object;
- M2 supported -> explicit obligations are anti-additive;
- M3 supported -> revise the semantic-to-evidence object map;
- M5 supported -> stabilize measurement before architecture;
- M6 supported -> repair reference ontology in a new version.

Provisional budget:

- eight logical calls;
- at most sixteen physical attempts;
- at most 100000 total tokens;
- exact latency capture required.

Token savings are not expected and are not a primary gate.

## Anti-Additive Audit

Active patch temptation:

```text
v0.3K missing tolerance refs
  -> add stronger wording
  -> add evidence checker role
  -> add coordinator
```

v0.3L instead upgrades the object from prompt wording to evidence-sufficiency
obligations.

The proposal removes:

- provenance/effect role decomposition from the causal object;
- downstream claim-scope reinterpretation;
- duplicate binding roles;
- Provider consensus;
- Provider state assessment;
- any assumption that more roles create more cognition.

It adds one ephemeral deterministic projection and one bounded Provider
binding operation shared by both arms.

No durable Runtime state owner, semantic enum, relation, action, or promotion
path is introduced.

If the guided arm fails, do not add another checker or obligation exception in
v0.3L. Close under M0, M2, M3, M5, M6, or construction failure.

## Object Upgrading Audit

### Previous object

`ROLE_DECOMPOSED_SEMANTIC_INFERENCE`

### Failure

Role-local semantic labels remained strong, but evidence-sufficiency binding
changed with presentation and caused fail-closed action loss.

### Lifted object

`EVIDENCE_SUFFICIENCY_OBLIGATION`

### Why the lift is valid

It explains:

- v0.3J tolerance-witness omissions;
- v0.3K reverse split witness loss;
- v0.62 evidence-set disagreement;
- v0.63's benefit from typed primary versus auxiliary evidence;
- why v0.88 downstream semantic roles amplified framing instead of proving
  sufficiency.

It reduces architecture:

- no extra cognitive role;
- no semantic coordinator;
- no review loop;
- one deterministic obligation projection;
- one narrow semantic binding question.

The object remains falsifiable through exact obligation and witness-set
metrics.

## Proxy Validity Limits

Exact synthetic witness sets are proxies for evidence sufficiency.

They may be non-unique in natural evidence. A passing experiment supports only
the frozen synthetic obligation coordinate and one Provider.

Supplied correct semantic premises remove upstream inference uncertainty.
Therefore passing cannot establish end-to-end Runtime cognition.

Fail-closed action retention is not semantic correction and must be reported
separately.

## Authority Boundary

Allowed before HumanGate freeze:

- theory audit;
- comparison with v0.3K and archived v0.62-v0.63/v0.88-v0.89 evidence;
- wording corrections that do not alter the object or predictions.

Forbidden:

- Provider calls;
- fresh corpus construction or consumption;
- experiment code;
- CoreSlim or Runtime contract changes;
- retention or baseline writes;
- version promotion.

Rollback target:

`R4_V0_3K_CLOSED_NO_SEQUENTIAL_BINDING_AUTHORITY`

Promotion authority:

`PM_HUMAN_GATE_ONLY`

## Theory Freeze Gate

| Requirement | Review result |
| --- | --- |
| ontology and project object defined | yes |
| v0.88-v0.89 anti-additive boundary inherited | yes |
| leading model and six rivals explicit | yes |
| matched one-call binder arms | yes |
| repeated counterbalance present | yes |
| falsification conditions explicit | yes |
| supplied-premise limitation explicit | yes |
| proxy limits explicit | yes |
| removal tests present | yes |
| stop and rollback condition present | yes |
| expected theoretical Cbit margin positive | yes |
| PM/HumanGate freeze | pending |

Freeze decision:

`REVIEW_READY_NOT_AUTHORIZED`

## Closure Contract

Every v0.3L closure must report:

1. exact obligation, witness, and action facts;
2. multi-witness versus single-witness phenomena;
3. replicate, order, time, caching, and backend effects;
4. false witnesses separately from missing witnesses;
5. conservative blocks separately from semantic corrections;
6. leading and rival model adjudication;
7. all reference-ontology disputes;
8. token and exact latency cost;
9. accepted, revised, rejected, and pending theory objects;
10. whether the next object is obligation-guided binding, premise transfer, or
    no architecture change.

No baseline object is updated by theory review alone.
