# SciFact Semantic Warrant Closure v0.87

## Status

`REJECT_V0_87_DEVELOPMENT_GATE`

v0.87 is frozen. The same holdout, prompt, receipt contract, score gate, and
Provider run must not be retuned or rerun as v0.87.

This is a development result, not external acceptance evidence. No receipt or
compiled candidate may write CoreSlim, retention, baseline, or production
state.

## Experiment object

v0.87 tests whether a Provider-backed `SemanticWarrantReceipt` can support the
Kernel's claim-state cognition without giving the Provider admission or state
mutation authority.

The cognitive path is:

1. SciFact supplies a claim and candidate evidence sentences.
2. The Provider returns a semantic state and selected rationale sentence IDs.
3. Strict Runtime validation rejects malformed, ungrounded, or policy-bearing
   receipts.
4. `KernelUtilityCompiler` deterministically maps a valid receipt to a
   candidate-only action.
5. Private SciFact references score labels and rationales after the run.

The Provider cannot emit promotion, admission, retention, utility, candidate
state, or write actions.

## Frozen design

- Source: SciFact `dev` split.
- Source archive SHA-256:
  `11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be`.
- Selection: SHA-256 ranking over claim IDs, independently within each label.
- Cases: 18.
- Balance: 6 `SUPPORTED`, 6 `REFUTED`, 6 `NOT_ENOUGH_INFO`.
- Provider: DeepSeek `deepseek-v4-flash`, temperature 0, thinking disabled.
- Maximum physical attempts: 36.
- Hard token ceiling: 80,000.

Frozen commitments:

| Artifact | Commitment hash |
|---|---|
| Private holdout | `4c1f834c70a23a304dc55bc171a110070529541600fc51113a29f6c45ffe274c` |
| Public holdout | `5799f13bfe3279924f51d05e6da686650ebdf0b758ba715af7e5cf7cd89220cb` |
| Preregistration | `08e7b6243147e851158e41f752c72690b9b8b6425ed8c3ec07edfc4c53e0497c` |
| Provider run | `a9784d6537a112963b063b807ee864382f47214cce1ccdfa4e32167188d91fd3` |
| Preregistered evaluation | `ca0ec38c2b64d932995261e533af7e5eb555e14d45f1babebd539a8bf7a27b3b` |
| Official-metric posthoc | `80a1f84cf1fe2dd0c002044ed34f90343da1358805f58b3f26bb65c1cbf8729e` |

The public panel contained no expected state, gold label, or gold rationale
coordinate. Selection and score gates were frozen before the first Provider
call.

## Preregistered result

| Metric | Result | Gate | Pass |
|---|---:|---:|---|
| Valid receipts | 18/18 | 18/18 | Yes |
| Contract failures | 0 | 0 | Yes |
| Label accuracy | 17/18 = 0.9444 | >= 0.80 | Yes |
| Internal macro rationale F1 | 0.8407 | >= 0.70 | Yes |
| Joint exact success | 12/18 = 0.6667 | >= 0.65 | Yes |
| Harmful compiled candidates | 1 | 0 | **No** |
| Abstention rate | 0 | <= 0.25 | Yes |
| Physical attempts | 18 | <= 36 | Yes |
| Total tokens | 35,725 | <= 80,000 | Yes |

All six `REFUTED` and all six `NOT_ENOUGH_INFO` cases were labeled correctly.
Five of six `SUPPORTED` cases were labeled correctly. The remaining supported
case was compiled as a refutation candidate, so the zero-harm gate rejected
the version.

## Official SciFact metric audit

After the frozen run, the implementation was compared with SciFact's official
[evaluation definition](https://github.com/allenai/scifact/blob/master/doc/evaluation.md).
This exposed a validity limitation in the preregistered rationale metric.

The preregistered metric selected the best individual gold rationale set for
each case and macro-averaged case scores. Official sentence scoring instead:

- counts every predicted rationale sentence against precision;
- gives credit to a sentence from a multi-sentence rationale only when the
  complete gold set is predicted;
- aggregates sentence counts across the evaluated corpus;
- does not inflate the score with empty-evidence `NOT_ENOUGH_INFO` cases.

The official-style descriptive audit produced:

| Metric | Result |
|---|---:|
| Correct predicted sentences | 13 |
| All predicted sentences | 24 |
| Gold evidence sentences | 22 |
| Sentence precision | 0.5417 |
| Sentence recall | 0.5909 |
| Sentence F1 | 0.5652 |
| Overselected sentences | 11 |
| Unrecovered gold sentences | 9 |

This posthoc result has no gate authority and does not replace the frozen
evaluation. The original decision was already `REJECT`; the corrected official
metric supplies an additional reason not to promote the mechanism.

## Experiment analysis

### Facts

- The Provider completed all 18 tasks with schema-valid receipts.
- Runtime preserved the public/private boundary and made no state write.
- Overall label discrimination was strong but not zero-harm.
- Rationale selection was substantially weaker under the benchmark's official
  sentence definition than under the preregistered internal proxy.
- Token cost was inside the frozen budget and was not the blocking variable.

### Main phenomenon: aggregate scope versus local exceptions

The harmful case was SciFact claim `1146`:

> Teaching hospitals do not provide better care than non-teaching hospitals.

The source review's aggregate conclusion says that teaching status on its own
does not markedly improve or worsen patient outcomes and that teaching
structures typically do not do better. SciFact therefore labels the claim
`SUPPORTED`.

The Provider focused on small benefits for particular diagnoses and a
borderline aggregate mortality estimate, then interpreted the claim as an
exceptionless universal. It returned `REFUTED`.

This is not merely sentence-level entailment failure. It is a conflict among:

- the claim's apparent quantifier;
- the paper's aggregate conclusion;
- subgroup exceptions;
- whether exceptions qualify or overturn the aggregate claim.

The current receipt has no typed representation for those relations, so a
plausible local observation can become a harmful global candidate.

### Second phenomenon: rationale abundance is not rationale minimality

The prompt requested a minimal complete rationale, but the Provider commonly
selected adjacent explanatory or corroborating sentences. This produced 11
overselected sentences.

Case `619` shows the complementary failure: one sentence from a two-sentence
gold rationale was selected, while other selected sentences came from a
different document. The global label was correct, but the benchmark-complete
evidence set was not recovered.

The runtime therefore needs to distinguish:

- a minimal complete evidence set;
- additional supporting context;
- an incomplete fragment of a multi-sentence warrant;
- evidence from another document that supports the same interpretation but is
  not part of the benchmark reference set.

### Rival explanations

The single harmful case may partly reflect benchmark convention rather than a
clear factual mistake. A strict reading of “do not provide better care” can be
challenged by any genuine subgroup benefit. However, AgentOS must either align
with the declared benchmark aggregation rule or explicitly abstain on the
scope conflict. Opening a strong refutation candidate is unsafe under either
interpretation.

The low official sentence F1 may also understate broader cognitive usefulness:
some overselected sentences were relevant explanatory context. That does not
make them valid minimal rationales under the benchmark contract. Context value
and warrant sufficiency must remain separate coordinates.

### Negative results preserved

- A schema-valid semantic receipt does not guarantee a safe compiled
  candidate.
- High label accuracy does not satisfy a zero-harm runtime gate.
- The preregistered rationale proxy was not benchmark-equivalent.
- Asking for minimal evidence in prose did not reliably produce minimal
  evidence sets.
- v0.87 provides no basis for CoreSlim or retention promotion.

## Architecture update

The result supports a further modular split:

1. `EvidenceSetReceipt`
   - groups sentences into minimal complete evidence sets;
   - separates core evidence from context;
   - marks incomplete multi-sentence sets.
2. `ClaimScopeReceipt`
   - identifies aggregate, subgroup, conditional, and exception scope;
   - records whether an exception qualifies or overturns the main claim;
   - preserves material scope conflict.
3. `KernelUtilityCompiler`
   - opens a strong candidate only when evidence-set completeness and scope
     aggregation agree;
   - otherwise retains unresolved state or abstains;
   - continues to own every candidate-state transition.

This keeps Runtime as the cognitive subject: it defines the objects, composes
the receipts, resolves conflicts, applies meta-rules, and owns final state.
Providers supply the semantic judgments needed by those operations.

## Next stage

v0.88 should use a fresh, non-overlapping SciFact dev subset. Before any
Provider call it must freeze:

- the official SciFact sentence metric as the authoritative rationale metric;
- an evidence-first `EvidenceSetReceipt`;
- a separate `ClaimScopeReceipt`;
- a Kernel rule that converts material aggregate/exception conflict to
  `ABSTAIN` rather than a strong candidate;
- zero harmful candidates as the hard gate;
- token cost as a secondary metric.

The 18 v0.87 cases remain analysis-only and must not be reused to tune or score
v0.88.
