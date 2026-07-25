# SciFact Claim-Atom Binding Closure v0.89

## Status

**REJECT_V0_89_BINDING_VETO_DEVELOPMENT_GATE**

v0.89 is closed and immutable. Explicit claim-atom binding plus an isolated
veto-only challenger removed the only harmful strong baseline candidate, but
that removal came from an invalid binding receipt and downstream fail-closed
behavior rather than a valid semantic veto. Among valid receipts, all nine
semantic vetoes were false vetoes. No CoreSlim, retention, baseline,
selection, or production authority is granted.

## Window initialization

- Theory baseline: Cognitive Research Architecture v3.7
- Methodology baseline: MethodologyKernel v1.1
- Inherited objects:
  - Provider semantic support without policy authority
  - deterministic Kernel candidate compilation
  - public/private benchmark separation
  - v0.88 EvidenceSet and ClaimScope research objects
- Preserved caveats:
  - v0.87 and v0.88 remain rejected and immutable
  - development-split evidence is not external acceptance
  - pretraining contamination is not excluded
  - SciFact reference tension remains possible
- Objective: determine whether claim-atom binding and an isolated veto-only
  challenger reduce harmful strong candidates without excessive loss of
  correct evidence.
- Object-to-proxy chain:
  `ClaimAtomBinding + isolated challenge -> Kernel veto-only candidate ->
  paired safety and SciFact sentence metrics`

## Modular architecture

| Module | Responsibility | Authority |
| --- | --- | --- |
| `claim_atom_binding.py` | Decompose claims and bind atoms to evidence groups | Semantic support only |
| `evidence_binding_challenge.py` | Independently challenge directness without seeing binding, scope, or candidate state | Veto evidence only |
| `kernel_binding_veto.py` | Preserve or veto an existing strong candidate | Kernel-owned, candidate-only |
| `scifact_v0_89_base_runtime.py` | Run shared EvidenceSet and frozen ClaimScope path | Runtime orchestration |
| `scifact_v0_89_binding_runtime.py` | Run binding, challenge, and mechanical compilation | Runtime orchestration |
| `scifact_v0_89_evaluation.py` | Apply frozen safety, retention, and sentence gates | Mechanical evaluation |
| `scifact_v0_89_posthoc.py` | Separate valid semantic veto from upstream failure | Descriptive only |

The candidate arm cannot promote a non-strong baseline state. All artifacts
are candidate-only and explicitly disable Core and retention writes.

## Frozen design

The holdout contains 18 fresh SciFact development claims, balanced at six
`SUPPORTED`, six `REFUTED`, and six `NOT_ENOUGH_INFO`. It has zero case
overlap with v0.87 and v0.88.

Both arms share:

1. one EvidenceSet call per case;
2. one ClaimScope call per case.

A0 compiles the frozen v0.88 candidate. A1 adds:

3. one ClaimAtomBinding call per case;
4. one context-isolated BindingChallenger call per case;
5. a zero-Provider veto-only Kernel compiler.

The main gates required zero harmful strong candidates, at least 0.90 strong
candidate precision, at least 0.80 retention of correct strong candidates,
sentence precision no lower than A0, sentence F1 loss no greater than 0.05,
label-accuracy loss no greater than 0.10, abstention no greater than 0.35, and
zero promotion from a non-strong baseline.

## Artifact integrity

| Artifact | SHA-256-bound artifact hash |
| --- | --- |
| Private holdout | `1f5fb83a301bb7be93d12facaeba13cf12a6dfabb518b7bb74eab64935779481` |
| Preregistration | `1759989ad4efeb431dffe6e4035421df245d766a9bb647b4b68bd02da378f6b2` |
| EvidenceSet run | `3f4daaa90add590bc4f2b567d3cb281f15539fc468503c8f86ec00eba1b2e281` |
| A0 ClaimScope run | `f2118f94f1ed20890be3197e0b3aa3aa43cfe3752fe8712b20eef078f4a4d0f3` |
| ClaimAtomBinding run | `56d5216b82235902236031ecddbbde54a1dbcb2c6cf42c683a9a2d85196f2902` |
| BindingChallenger run | `d85db1f299874a40cd81a304b17beb0c6102b7781587d5cbb1277407aff37670` |
| Candidate compilation | `b245c8ff1dfb24a643927f9c08369fd4a56dd2d447d8196678c8b5e2a8dbebe7` |
| Evaluation | `5b4b1d383bf163c8c21f51f5fb79501271e11a0e387cab8095d842484be71c1c` |
| Descriptive posthoc | `323d10e01ddd3957f9bced90f21c9b73c7ce7b0fca6f42820fd90babd7737798` |

The public panel contained no private reference.

## Execution

| Stage | Valid receipts | Failures | Tokens |
| --- | ---: | ---: | ---: |
| EvidenceSet | 18/18 | 0 | 49,208 |
| ClaimScope | 18/18 | 0 | 53,271 |
| ClaimAtomBinding | 15/18 | 3 | 69,517 |
| BindingChallenger | 18/18 | 0 | 52,740 |
| Total | 69/72 | 3 unique Provider failures | 224,736 |

The deterministic candidate run propagated the three missing binding receipts
as three additional fail-closed records. The preregistered evaluation reports
six failure records, while the posthoc audit correctly distinguishes three
unique failed cases from three downstream propagations.

## Paired result

| Metric | A0 frozen v0.88 | A1 binding veto | Delta |
| --- | ---: | ---: | ---: |
| Valid candidates | 18/18 | 15/18 | -3 |
| Label accuracy | 0.9444 | 0.3333 | -0.6111 |
| Strong candidates | 13 | 1 | -12 |
| Strong-candidate precision | 0.9231 | 1.0000 | +0.0769 |
| Correct strong candidates retained | 12 | 1 | 0.0833 retention |
| Sentence precision | 0.7200 | 1.0000 | +0.2800 |
| Sentence recall | 0.5625 | 0.0313 | -0.5313 |
| Sentence F1 | 0.6316 | 0.0606 | -0.5710 |
| Harmful strong candidates | 1 | 0 | -1 |
| Abstention | 0 | 0.6667 | +0.6667 |

A1 became a nearly universal rejector. Higher strong precision is therefore
not evidence of improved cognition: it was purchased by discarding eleven of
twelve correct strong candidates and losing nearly all rationale recall.

## Posthoc correction

The frozen evaluation mechanically counted every transition from a strong
baseline to no strong candidate as a veto. The descriptive audit separated
the mechanisms:

| Posthoc quantity | Count |
| --- | ---: |
| Valid-receipt semantic vetoes | 9 |
| Valid semantic vetoes of harmful candidates | 0 |
| Valid semantic false vetoes | 9 |
| Harmful baseline removed by binding failure | 1 |
| Refutation-polarity asymmetry cases | 6 |

The only harmful A0 case, 628, produced a semantically informative but
contract-invalid binding receipt and therefore failed closed. v0.89 did not
demonstrate a valid semantic correction.

## Failure analysis

### 1. Refutation polarity was compiled backwards

All six correct `REFUTED` candidates were vetoed. The binding role marked one
or more claim atoms `CONTRADICTED`, which is appropriate evidence for a
refutation. The v0.89 Kernel nevertheless allowed only `BOUND_EXPLICIT` and
`BOUND_COMPOSITIONAL` atom states for both support and refutation. It therefore
treated successful contradiction as a binding defect.

This is not a Provider-quality failure. It is a relation-insensitive Kernel
meta-rule failure.

### 2. Absence was incorrectly represented as a required atom

The binding role sometimes emitted atoms such as "no explicit condition or
time specified." The contract required every emitted atom to be required and
the Kernel required every required atom to bind to evidence. A statement's
absence cannot normally cite a positive sentence coordinate, so valid support
could be vetoed for failing to evidence an artificial absence atom.

### 3. Bridge consistency was too narrow

Case 628 correctly identified that "endemic in Africa" does not establish
"most frequent in individuals of African origin." It returned
`QUALIFIED_ONLY` together with `unstated_bridge_required=true`. The validator
allowed the bridge flag only with the single
`REQUIRES_UNSTATED_BRIDGE` directness enum and rejected the otherwise useful
receipt. This is a schema-state equivalence error.

### 4. Group-bounded citations exposed evidence-set incompleteness

Cases 911 and 985 cited context sentences outside the frozen evidence group
while explaining missing population, direction, or mechanism bindings. The
validator correctly rejected out-of-group citations. The observation,
however, shows that atom binding can reveal that the upstream evidence group
itself is incomplete. The current architecture has no typed route for
requesting group revision without mutating the frozen group.

### 5. Double strictness amplified correlated conservatism

The primary binding role classified all 14 valid group judgments as
`DIRECT_EXPLICIT` or `DIRECT_COMPOSITIONAL`, yet partial or contradicted atom
states still vetoed most groups. The challenger independently passed eight
groups and vetoed nine. Requiring every primary atom and challenger verdict to
be maximally positive made the composition noncompensable in the wrong way:
one local uncertainty erased an otherwise correct claim relation.

## Phenomena

1. The external benchmark baseline was strong on this slice: 17/18 labels
   correct and one harmful strong candidate.
2. Fine-grained decomposition exposed real semantic defects, including the
   unsupported superlative in case 628.
3. The Runtime failed to interpret typed evidence relative to the candidate
   relation. More structure produced less effective Cbit because the
   meta-rule was polarity-blind.
4. Operational complexity also rose: the richer binding schema caused three
   failures while the narrower challenger completed 18/18.
5. Fail-closed safety and cognitive correction are distinct measurements.
   The former worked; the latter did not.

## Mechanism interpretation and rivals

The leading explanation is not that claim-atom binding is useless. It is that
the v0.89 atom ontology and Kernel gate collapse three different meanings:

- identity/scope atoms that should remain bound under both support and
  refutation;
- proposition atoms that may be bound for support or contradicted for
  refutation;
- optional or absent dimensions that should not become required positive
  evidence.

Competing explanations remain:

- the same Provider supplies EvidenceSet, Scope, Binding, and Challenge,
  allowing correlated conservatism;
- SciFact gold rationales may not reward every semantically defensible
  evidence coordinate;
- an 18-case development slice is too small for general performance claims;
- the challenger may be intrinsically too conservative even after the Kernel
  polarity rule is repaired.

## Negative results preserved

- More detailed semantic receipts do not guarantee better Runtime cognition.
- A veto-only role can eliminate harm by eliminating almost all action.
- Fail-closed removal must not be counted as semantic correction.
- Noncompensable gates must be typed by relation and atom function.
- Refutation cannot share the support arm's all-atoms-bound rule.
- Same-version repair is forbidden after these results were revealed.

## Object-state closure

### Accepted

- Claim-atom binding exposed meaningful evidence defects that the coarser
  EvidenceSet and ClaimScope layers did not represent.
- Context isolation and no-promotion constraints remained intact.
- Fail-closed behavior prevented invalid receipts from producing candidates.

### Revised

- Claim atoms require functional types: identity anchors, proposition targets,
  and optional qualifiers.
- Binding acceptance must be relation-aware:
  support requires proposition binding, while refutation requires a
  contradiction witness with identity and scope still bound.
- Absence of a qualifier is metadata, not automatically a required atom.
- Bridge presence and directness must not be encoded as a false one-to-one
  equivalence.

### Pending

- whether a polarity-aware compiler recovers the six refutation candidates;
- whether optional-atom handling restores support recall;
- whether the challenger adds value after mechanical semantics are corrected;
- fresh validation after any revealed-receipt mechanism calibration.

## Evidence coordinate

This is internal project evidence on an external public benchmark development
split. It is not external replication, production validation, or an accepted
benchmark result. Private labels were used only after Provider execution.

## Next stage

v0.90 should begin with a **zero-Provider, descriptive mechanism replay** over
the frozen v0.89 receipts. It should not rescore v0.89 as a pass.

The replay compiler should freeze:

1. identity and scope atoms must remain bound in both relations;
2. support proposition atoms require binding;
3. refutation requires at least one explicit contradiction witness rather
   than rejecting `CONTRADICTED`;
4. absent or non-applicable dimensions are not required positive atoms;
5. upstream receipt failure remains fail closed;
6. challenger veto remains advisory until its incremental value is separated
   from primary binding.

Only if this zero-call replay restores correct-strong retention without
reintroducing the harmful candidate should a new v0.90 fresh holdout and new
Provider calls be authorized.
