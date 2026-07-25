# SciFact Evidence-Set and Claim-Scope Closure v0.88

## Status

**REJECT_V0_88_PAIRED_DEVELOPMENT_GATE**

v0.88 is closed and immutable. The evidence-set plus claim-scope arm did not
outperform the direct semantic-warrant baseline, increased harmful strong
candidates, and had one contract-invalid receipt. It grants no CoreSlim,
retention, baseline, selection, or production authority.

## Window initialization

- Theory baseline: Cognitive Research Architecture v3.7
- Methodology baseline: MethodologyKernel v1.1
- Inherited accepted objects:
  - Provider semantic support without policy authority
  - deterministic Kernel candidate compilation
  - public/private benchmark separation
- Preserved caveats:
  - v0.87 is rejected and immutable
  - SciFact development data cannot establish external acceptance
  - pretraining contamination is not excluded
- Specific objective: test whether constructing evidence sets before judging
  claim scope improves official-style SciFact sentence recovery while
  preserving zero harmful strong candidates.
- Object-to-proxy chain:
  `EvidenceSet + ClaimScope -> frozen receipts -> Kernel candidate ->
  SciFact sentence precision/recall/F1`

## Architecture under test

The implementation is deliberately modular:

| Module | Responsibility | Authority |
| --- | --- | --- |
| `evidence_set_receipt.py` | Build minimal complete evidence groups and partition context and irrelevant units | Semantic support only |
| `claim_scope_receipt.py` | Judge aggregate, subgroup, conditional, exception, and conflict scope over frozen groups | Semantic support only |
| `kernel_scope_utility.py` | Compile strong, unresolved, or abstaining candidate state | Kernel-owned, candidate-only |
| `scifact_v0_88_runtime.py` | Bind receipts, hashes, failures, telemetry, and no-write state | Runtime orchestration |
| `scifact_v0_88_evaluation.py` | Apply frozen paired gates and sentence metric | Mechanical evaluation |

No module may promote a candidate or write CoreSlim or retention state.

## Frozen design

The holdout contains 18 fresh SciFact development claims, balanced at six
`SUPPORTED`, six `REFUTED`, and six `NOT_ENOUGH_INFO`. It shares no case ID
with v0.87.

| Arm | Provider operations per case |
| --- | ---: |
| A0 direct semantic warrant | 1 |
| A1 evidence set plus claim scope | 2 |

The authoritative rationale metric was frozen before calls as SciFact-style
sentence precision, recall, and F1. A gold evidence set counts only when the
predicted label is correct and the complete multi-sentence set is present.

The main semantic gates required:

- candidate label accuracy at least 0.80;
- sentence F1 at least 0.60;
- paired sentence-F1 improvement at least 0.05;
- zero harmful strong candidates;
- no more harmful strong candidates than A0;
- abstention at most 0.25;
- all material scope conflicts compiled to abstention.

## Execution integrity

| Artifact | SHA-256-bound artifact hash |
| --- | --- |
| Private holdout | `8358894c8b89813edc41d1ca2752adb528400279341ab9c8aa0f2c404ca3f5fd` |
| Preregistration | `cceac203ce1e527cdeb540db7540cfecb1b0e682164bcd1cc3d2834166808010` |
| A0 run | `7ebf8fa18d5bea4936571b1bf6e85e59319457ca7bb23c0a309483a770fd160b` |
| Evidence-set run | `ae3a1d23ed51eb2250db895b9116d6dd0757365ff9349e03e3e2ae846cf68ade` |
| Claim-scope run | `176112943d11f74c9021f6700ce57315780fe6262906d911b5f780a8d2661229` |
| Evaluation | `13b4ccc5902631ce0187cd5cacbb9edbb63ec0f2751fcf2d320a22eab8a44cdb` |

The public panel contained no private reference. All three runs remained
candidate-only with explicit Core and retention writes disabled.

## Results

| Metric | A0 direct | A1 evidence + scope | Delta |
| --- | ---: | ---: | ---: |
| Valid final receipts | 18/18 | 17/18 | -1 |
| Label accuracy | 0.7778 | 0.7778 | 0 |
| Correct gold sentences | 12 | 14 | +2 |
| Predicted sentences | 15 | 26 | +11 |
| Sentence precision | 0.8000 | 0.5385 | -0.2615 |
| Sentence recall | 0.5714 | 0.6667 | +0.0952 |
| Sentence F1 | 0.6667 | 0.5957 | -0.0709 |
| Overselected sentences | 3 | 12 | +9 |
| Unrecovered gold sentences | 9 | 7 | -2 |
| Harmful strong candidates | 1 | 3 | +2 |
| Abstention | 0 | 0.0556 | +0.0556 |
| Tokens | 36,967 | 96,051 | +59,084 |

A1 cost 2.60 times A0. The complete paired experiment used 54 logical
Provider calls and 133,018 tokens, within the frozen ceilings.

Operationally, A0 and EvidenceSet each produced 18/18 valid receipts.
ClaimScope produced 17/18. Case 36 returned
`NOT_ENOUGH_INFO + MATERIAL_SCOPE_CONFLICT`; the contract correctly rejected
that internally inconsistent state/effect pair.

## Case transitions

A1 repaired three A0 unresolved judgments:

| Case | Gold | Transition |
| --- | --- | --- |
| 115 | REFUTED | NOT_ENOUGH_INFO -> REFUTED |
| 852 | REFUTED | NOT_ENOUGH_INFO -> REFUTED |
| 1019 | SUPPORTED | NOT_ENOUGH_INFO -> SUPPORTED |

It also regressed three correct unresolved judgments:

| Case | Gold | Transition | Failure mode |
| --- | --- | --- | --- |
| 36 | NOT_ENOUGH_INFO | NOT_ENOUGH_INFO -> invalid | Unsupported folate-to-B12 bridge plus inconsistent scope receipt |
| 577 | NOT_ENOUGH_INFO | NOT_ENOUGH_INFO -> SUPPORTED | Dose sensitivity was expanded into an unsupported lower-dose growth direction |
| 1344 | NOT_ENOUGH_INFO | NOT_ENOUGH_INFO -> SUPPORTED | Senescence associations were expanded into a stronger p53-upregulation and lifespan-causation claim |

Case 808 remained a harmful `SUPPORTED -> REFUTED` error in both arms. The
supplied abstract contains an explicit statement that termination does not
depend on cis-acting sequences, while the benchmark reference marks a
different sentence as support. This is a benchmark-reference tension that
must be audited independently; it cannot be resolved by tuning on this case.

## Phenomena

1. **Recall rose, but precision collapsed.** Evidence-first decomposition
   recovered two additional gold sentences but predicted eleven additional
   sentences, nine of which were overselected.
2. **The second semantic stage did not provide independent correction.**
   ClaimScope generated no valid `MATERIAL_SCOPE_CONFLICT` case. Apart from
   the rejected case 36 receipt, it converted every nonempty evidence group
   into a resolved state.
3. **The active error lies before policy compilation.** The Kernel faithfully
   compiled the supplied typed judgments. Harm entered when plausible
   scientific association was treated as direct claim support.
4. **Evidence grouping improved some missed labels but not minimality.**
   EvidenceSet produced 16 groups across the 18 cases, yet A1 selected 26
   sentences for 21 gold sentences and only 14 counted as correct.
5. **More semantic work was anti-additive on this surface.** The extra role
   increased token cost, lowered sentence F1, and increased strong-state harm.

## Mechanism interpretation and rivals

The leading explanation is a missing **claim-atom binding and entailment
directness object**. EvidenceSet asks whether sentences form a plausible
warrant, but does not require explicit binding of every claim variable,
direction, quantifier, and causal edge. ClaimScope then receives an already
framed group and is anchored toward confirming it.

Competing explanations remain live:

- the same Provider in sequential roles may create correlated rather than
  independent errors;
- the evidence-group prompt may encourage explanatory completion from model
  priors;
- SciFact gold rationales can prefer a different sentence from a semantically
  plausible one, so part of the sentence loss may be benchmark-coordinate
  mismatch;
- the 18-case development sample is too small to estimate general performance.

The result does not distinguish these rivals. It does rule out the claim that
this two-stage decomposition alone reliably improves the tested runtime.

## Negative results preserved

- Typed decomposition does not itself create cognitive multiplication.
- A complete evidence partition does not guarantee direct entailment.
- A downstream scope role can amplify an upstream framing error.
- Higher recall cannot compensate for harmful strong candidates.
- Token cost is acceptable only when effective Cbit improves; here it did not.
- No same-version prompt repair or threshold adjustment is authorized.

## Object-state closure

### Accepted

- Public/private separation, hash binding, candidate-only compilation, and
  no-write boundaries remained intact.
- EvidenceSet and ClaimScope are valid modular research objects, but not
  admitted performance-improving capabilities.

### Revised

- The bottleneck is no longer described primarily as aggregate-versus-subgroup
  scope. It is earlier: whether an evidence group directly binds the full
  claim without importing an unstated scientific bridge.
- Scope assessment must be able to challenge the evidence framing rather than
  merely classify its extent.

### Pending

- fresh validation of claim-atom binding and entailment directness;
- an independent, context-isolated challenge to each proposed evidence group;
- a reference-conflict audit that remains separate from model performance;
- replication across a larger or independently held benchmark surface.

## Evidence coordinate

This is **internal project evidence produced on an external public benchmark
development split**. It is stronger than synthetic-only evidence but is not an
external replication, production validation, or accepted benchmark result.
The private labels were used only after Provider execution for scoring.

## Next experiment

v0.89 should use a new non-overlapping holdout and freeze a narrower object
before any Provider call:

`ClaimAtomBindingReceipt`

For each proposed evidence group it should record:

- exact entity and population binding;
- property or outcome binding;
- direction and polarity binding;
- quantifier and scope binding;
- causal versus associational status;
- any required but unstated bridge;
- direct entailment, qualified entailment, contradiction, or insufficient
  binding.

A context-isolated evidence challenger should veto, never promote, groups that
depend on an unstated bridge. The Kernel should open a strong candidate only
when complete claim-atom binding, evidence relation, and claim scope agree.
The next test should compare this against the frozen v0.88 architecture on a
fresh holdout, retain zero harmful strong candidates as the hard gate, and
continue to treat token cost as secondary to effective Cbit.
