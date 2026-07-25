# Per-Round Theory Models v0.1

## Status

`RETROSPECTIVE_THEORY_MODEL_CANDIDATE`

This document models each auditable mainline experiment from v0.64 through
v0.89. It does not convert retrospective interpretation into preregistered
evidence. Its purpose is to make the theory transitions explicit before a new
experiment is chosen.

## Common Model Card

Each round is represented as:

```text
Mk = (Lk, Ok, Hk, Pk, Yk, Uk, Rk, Sk)
```

where:

- `Lk`: theory level under test;
- `Ok`: research object;
- `Hk`: causal hypothesis;
- `Pk`: discriminating prediction;
- `Yk`: observed result;
- `Uk`: theory update supported by the observation;
- `Rk`: live rival explanations;
- `Sk`: resulting theory state.

The theory levels are:

| Level | Meaning |
| --- | --- |
| `L0 GOVERNANCE` | transport, validation, replay, no-write, and hard gates |
| `L1 REPRESENTATION` | whether the relevant object and semantic relations are represented |
| `L2 COMPOSITION` | whether valid partial judgments are combined without amplification or loss |
| `L3 ORGANIZATION` | whether multiple cognitive actors produce unique net gain beyond the best member |

An experiment can support a lower-level mechanism while rejecting its
end-to-end chain. That distinction is central to this audit.

## Phase A: Transfer Pipeline

### v0.64 Fresh Selection-Retention

- **Evidence coordinate:** internal project evidence on a fresh local holdout;
  commit `3470d844176317693e580077fb1dfc888e49e244`.
- **L/O:** `L1 REPRESENTATION`; typed evidence binding as a prerequisite for
  selection and retention.
- **H:** if two role receipts bind the same typed relations consistently, the
  system can proceed to truth-state, selection, delayed consequence, and
  retention assessment.
- **P:** all 16 receipts pass the exclusivity contract and all eight cases
  reach relation consensus.
- **Y:** 9/16 receipts were valid; seven failed
  `BINDING_EVIDENCE_TYPE_OVERLAP`. The valid subset had 225/225 typed-field
  matches, but every downstream stage remained unexecuted. Cost was 51,147
  tokens.
- **U:** the failure was concentrated at a representation contract, not shown
  to be a selection or retention failure. Clean valid subsets cannot establish
  chain capability when almost half the receipts are discarded.
- **R:** the exclusivity rule may be too strict; the Provider may conflate
  evidence roles; the task ontology may permit legitimate multi-role spans.
- **S:** `REPRESENTATION_GATE_REJECTED`; selection-retention theory remains
  untested.

### v0.65 Benchmark Bridge

- **Evidence coordinate:** internal experiment on pinned public benchmark data;
  commit `af0cef20eaab9debf040b643c48a01995ba58e14`.
- **L/O:** `L1 REPRESENTATION`; staged evidence objectification.
- **H:** additional evidence-admission and binding work can compensate for a
  weaker one-pass judgment by improving evidence hygiene and final effective
  Cbit.
- **P:** staged A1 improves evidence and decision quality on the frozen test
  split without violating transfer gates.
- **Y:** A1 improved evidence F1 `0.9120 -> 0.9667` and aggregate effective
  Cbit `0.9230 -> 0.9491`, but label accuracy fell `0.9444 -> 0.9167`, one
  receipt failed, and cost rose `57,768 -> 122,063` tokens.
- **U:** extra work can improve evidence representation while harming the
  decision relation. Evidence hygiene is a supported submechanism; full
  staged replacement is rejected.
- **R:** benchmark ambiguity, missing comparator/significance coordinates, and
  an underpowered decision object can each explain the divergence.
- **S:** `SUBMECHANISM_SUPPORTED_COMPOSITE_REJECTED`.

## Phase B: Relational Representation Search

### v0.66 Typed Semantic Basis

- **L/O:** `L1 REPRESENTATION` plus an attempted `L2 COMPOSITION`; typed
  significance, orientation, measurement, and timepoint coordinates followed
  by free synthesis.
- **H:** explicit semantic coordinates allow a second Provider stage to
  synthesize more reliable labels.
- **P:** A2 outperforms direct binding and corrects the known significance,
  comparator, and ambiguity failures.
- **Y:** effective Cbit fell `0.8474 -> 0.7444`; all basis receipts were
  complete, but synthesis contradicted correct orientation facts and a binary
  comparison frame failed on multi-arm studies.
- **U:** typed coordinates can expose useful distinctions, but a free synthesis
  stage can discard them. Frame construction and basis-to-decision composition
  are separate failure loci.
- **R:** poor prompt compliance versus an incorrect comparison ontology.
- **S:** `REPRESENTATION_PARTIAL_COMPOSITION_REJECTED`.

### v0.67 Comparison Frame

- **L/O:** `L1 REPRESENTATION`; study-arm frame plus deterministic label
  compilation.
- **H:** removing free synthesis and freezing a comparison frame will convert
  valid semantic coordinates into reliable decisions.
- **P:** the deterministic chain improves calibration and preserves known
  corrections.
- **Y:** the compiler itself had zero failures, but label accuracy fell to
  `0.5000`; Provider-facing enums confused mention order with mathematical
  subject/reference relations, and exact string identity broke aliases.
- **U:** deterministic authority is supported conditionally: it protects valid
  coordinates but faithfully amplifies invalid coordinates. The upstream
  relational vocabulary remains the active object.
- **R:** vocabulary design, object identity, and benchmark conventions.
- **S:** `COMPILER_SUPPORTED_INPUT_MODEL_REJECTED`.

### v0.68 Relational Contrast

- **L/O:** `L1 REPRESENTATION`; stable arm IDs and explicit subject/reference
  relations.
- **H:** identity-stable relational coordinates remove alias and orientation
  ambiguity.
- **P:** the candidate clears calibration with no new harm.
- **Y:** receipts became 12/12 valid; accuracy rose to `0.8333`, evidence F1
  to `0.9556`, and effective Cbit to `0.9111`, but the zero-harm and 11/12
  gates failed.
- **U:** stable IDs and separation of relevance from significance are supported
  mechanisms. Schema validity still cannot detect a semantic contradiction
  between a rationale and its enum.
- **R:** Provider semantic reliability versus missing source-grounded relation
  witnesses.
- **S:** `POSITIVE_LOCAL_MECHANISM_TRANSFER_UNAUTHORIZED`.

### v0.69 Relation Witness

- **L/O:** `L1 REPRESENTATION`; exact source-grounded subject and relation
  witnesses.
- **H:** exact grounding will prevent structured semantic fields from
  contradicting the source.
- **P:** witness validation preserves or improves v0.68 while removing semantic
  contradictions.
- **Y:** only 7/12 receipts survived; effective Cbit fell to `0.5278`. A known
  comparator case was semantically corrected but rejected because continuation
  spans did not repeat the full subject and predicate.
- **U:** the hypothesis assumed span self-sufficiency. Exact source grounding
  is useful for provenance but is not a sufficient discourse semantics.
- **R:** copying quality versus genuine cross-span composition.
- **S:** `GROUNDING_GATE_SUPPORTED_SPAN_OBJECT_REJECTED`.

### v0.70 Discourse Witness Replay

- **L/O:** `L1 REPRESENTATION`; case-level inheritance of witnesses.
- **H:** allowing continuation spans to inherit a validated anchor recovers the
  semantically valid v0.69 receipts.
- **P:** zero-call replay restores most failures without new semantic risk.
- **Y:** validity rose only `7/12 -> 8/12`; paraphrased relations and incomplete
  alias catalogs remained blocked.
- **U:** discourse inheritance solves only one part of the surface-binding
  problem. Free-text witness production remains a noisy proxy.
- **R:** inadequate surface catalog versus Provider paraphrase behavior.
- **S:** `LOCAL_RECOVERY_INSUFFICIENT`.

### v0.71 Source-Surface Binding

- **L/O:** `L1 REPRESENTATION`; immutable locally enumerated surfaces selected
  by Provider IDs.
- **H:** candidate-ID binding removes quote-copy failures while preserving
  Provider semantic support.
- **P:** the full chain clears calibration within cost.
- **Y:** 12/12 receipts were valid; effective Cbit returned to `0.9111`, but
  the Provider rejudged a frame-set timepoint coordinate and cost reached
  245,471 tokens, over the frozen ceiling.
- **U:** immutable surface identity is supported. Provider authority over
  mechanically implied coordinates is redundant and harmful.
- **R:** architecture cost versus semantic task complexity.
- **S:** `SURFACE_IDENTITY_SUPPORTED_REDUNDANT_AUTHORITY_REJECTED`.

### v0.72 Coordinate Projection

- **L/O:** `L2 COMPOSITION`; deterministic projection of frame-set coordinates.
- **H:** removing redundant Provider authority recovers correct labels without
  changing evidence or adding calls.
- **P:** revealed replay improves the candidate with zero harm.
- **Y:** replay reached 12/12 validity, `1.0000` accuracy, and `0.9666`
  effective Cbit with zero additional calls.
- **U:** deterministic projection is strongly supported on revealed receipts.
  The result identifies a composition rule, not fresh transfer.
- **R:** replay overfitting and Provider-output instability.
- **S:** `MECHANISM_REPLAY_SUPPORTED_TRANSFER_PENDING`.

### v0.73 Prospective Surface Runtime

- **L/O:** `L1+L2`; prospective execution of frame, surface binding,
  projection, and compilation.
- **H:** the v0.72 replay mechanism survives new Provider execution.
- **P:** the exact chain reproduces calibration success.
- **Y:** accuracy was `0.9167`; the three key corrections survived, but a
  grouped intervention alias failed the frozen contract. Effective Cbit was
  `0.8833` at 226,128 tokens.
- **U:** projection and surface binding retained value prospectively. The
  remaining failure moved to object normalization.
- **R:** one narrow contract defect versus general instability of the chain.
- **S:** `PROSPECTIVE_SUBMECHANISM_SUPPORTED_GATE_REJECTED`.

### v0.74 Grouped Alias

- **L/O:** `L1 REPRESENTATION`; deterministic decomposition of canonical
  grouped-object names.
- **H:** a bounded local normalizer closes the v0.73 object-identity defect
  without expanding semantics.
- **P:** prospective calibration reaches the v0.72 result with no harm.
- **Y:** 12/12 valid, `1.0000` accuracy, `0.9666` effective Cbit, no harmed
  cases, and 245,682 tokens.
- **U:** the narrow normalization rule is supported on calibration. This is
  the strongest local representation result in the chain.
- **R:** calibration specificity and hidden admission-state incompleteness.
- **S:** `CALIBRATION_MODEL_ACCEPTED_FRESH_TRANSFER_REQUIRED`.

### v0.75 Fresh Holdout

- **L/O:** attempted transfer of the complete `L1+L2` chain.
- **H:** the calibrated relation pipeline generalizes to a fresh 36-case
  holdout.
- **P:** baseline admission succeeds and the candidate can be evaluated.
- **Y:** baseline admission produced 34/36 valid admission receipts and 32
  valid bindings; four contract failures stopped all candidate tasks before
  private-gold scoring.
- **U:** the relation pipeline was not the active transfer bottleneck. The
  upstream admission ontology lacked no-evidence, context-only, and retained
  context states.
- **R:** baseline contract defect versus a fundamentally task-relative notion
  of context.
- **S:** `TRANSFER_UNIDENTIFIABLE_OBJECT_UPGRADE_REQUIRED`.

## Phase C: Admission Ontology Search

### v0.76 Typed Evidence Admission

- **L/O:** `L1 REPRESENTATION`; object relation, evidence utility, and
  disposition as independent axes.
- **H:** a three-axis admission ontology resolves the v0.75 contract failures.
- **P:** the candidate improves typed evidence handling on a development panel.
- **Y:** all receipts were valid, but evidence F1 fell `1.0000 -> 0.8472`;
  null evidence and corroboration were demoted, and no case improved.
- **U:** three axes are descriptively useful, but their categories were not
  aligned with effect-bearing nulls, corroboration, or the benchmark rationale
  object.
- **R:** Provider error, rubric ambiguity, and benchmark ontology mismatch.
- **S:** `ONTOLOGY_PLAUSIBLE_OPERATIONAL_MODEL_REJECTED`.

### v0.77 External Typed Panel

- **L/O:** measurement model for the v0.76 ontology.
- **H:** independent model annotation can freeze a stable typed reference for
  evidence, context, and rejection.
- **P:** high agreement localizes runtime error against a usable reference.
- **Y:** full typed agreement was 39/50; 11 disagreements required Kimi
  adjudication. Ten disagreements crossed object relation together with
  utility/disposition. The reference remained candidate-only.
- **U:** the main ambiguity is the object-relation/outcome-separability
  boundary, not merely null-effect coding. The measurement object itself is
  uncertain.
- **R:** annotator-specific context policy and adjudicator preference.
- **S:** `MEASUREMENT_CANDIDATE_FROZEN_GROUND_TRUTH_UNAVAILABLE`.

### v0.78 Witness-Backed Admission

- **L/O:** `L1 REPRESENTATION`; separability and effect-basis witnesses.
- **H:** explicit witnesses make the three-axis ontology internally reliable.
- **P:** valid partitions and evidence quality improve on a fresh holdout.
- **Y:** validity fell `11/12 -> 7/12`; five contracts failed; among seven
  jointly valid cases, partitions were identical to baseline. Cost rose 28.5%.
- **U:** redundant semantic declarations created false bijections between
  axes. More fields added contradiction without information.
- **R:** contract overconstraint versus Provider inconsistency.
- **S:** `ANTI_ADDITIVE_REDUNDANT_REPRESENTATION`.

### v0.79 Minimal Semantic Witness

- **L/O:** boundary between Provider semantic facts and Runtime policy.
- **H:** independent semantic facts plus deterministic policy derivation
  remove the v0.78 declaration conflicts.
- **P:** the candidate improves evidence hygiene without policy-bearing
  Provider fields.
- **Y:** full validity was 9/12, but on jointly valid cases mean evidence F1
  rose `0.8074 -> 0.9778`, with three improvements and no harm.
- **U:** semantic-support/policy separation is supported. The remaining
  category still bundled mention-in-passage with separate extractability.
- **R:** positive valid-subset selection bias versus genuine mechanism gain.
- **S:** `MECHANISM_SIGNAL_POSITIVE_INTEGRITY_REJECTED`.

### v0.80 Atomic Semantic Witness

- **L/O:** `L1 REPRESENTATION`; atomic facts for target mention,
  extractability, support, and contextual relevance.
- **H:** atomization removes categorical ambiguity and yields a complete
  evidence/context/reject partition.
- **P:** typed-reference metrics improve across all classes.
- **Y:** all benchmark evidence was recovered, but the candidate predicted no
  rejection. Typed accuracy rose by `0.0417` while macro F1 fell by `0.1216`;
  reject F1 became `0`.
- **U:** effect evidence and context utility are separate research objects.
  Atomization improved one boundary by collapsing another.
- **R:** an overbroad relevance prompt versus the absence of a universal
  context ontology.
- **S:** `EFFECT_OBJECT_SUPPORTED_CONTEXT_OBJECT_UNRESOLVED`.

### v0.81 Context Utility Witness

- **L/O:** `L1+L2`; grounded context utility combined with regenerated effect
  facts.
- **H:** an explicit decision-change witness restores a meaningful
  context/reject boundary.
- **P:** candidate changes can be attributed to context utility.
- **Y:** rejection was restored, but nine evidence-status changes came from a
  fresh effect judgment and 11 semantic conflicts appeared. Evidence F1 fell.
- **U:** the mechanism may alter context correctly, but the experimental design
  cannot identify that effect because two semantic objects changed together.
- **R:** context mechanism failure versus effect-rejudgment noise.
- **S:** `CAUSAL_IDENTIFIABILITY_FAILURE`.

### v0.82 Staged Context Addon

- **L/O:** `L2 COMPOSITION`; context-only stage consuming a frozen effect
  partition.
- **H:** staging isolates context utility and preserves effect evidence by
  construction.
- **P:** candidate improves context/reject routing without evidence harm.
- **Y:** 19 spans moved from context to reject, all correct against the typed
  reference, with zero harm and invariant evidence F1. Yet both true context
  spans had already been misclassified upstream, so the full gate failed.
- **U:** A16 has positive local causal contribution; the composed system fails
  because an upstream stage controls the reachable state space.
- **R:** reference scarcity for context and upstream A14 over-admission.
- **S:** `LOCAL_COMPONENT_SUPPORTED_SYSTEM_COMPOSITION_REJECTED`.

### v0.83 Selective Boundary Review

- **L/O:** `L2 COMPOSITION`; reviewer authorized to mutate only witnessed
  evidence/context boundaries.
- **H:** a selective reviewer corrects upstream errors without reopening
  successful context/reject routing.
- **P:** sparse, grounded mutations improve the composed system.
- **Y:** A17 made 15 evidence-to-context mutations and no promotions; benchmark
  evidence F1 collapsed `0.9722 -> 0.3611`.
- **U:** the reviewer treated absence of a repeated component as explicit
  contradiction. Grounded quotes established source presence, not warranted
  negative interpretation.
- **R:** binary ontology defect versus intrinsically conservative review.
- **S:** `REVIEWER_MODEL_REJECTED`.

### v0.84 Ternary Boundary Review

- **L/O:** `L1+L2`; ternary matched/contradicted/not-stated relation model.
- **H:** representing omission separately from contradiction prevents
  v0.83 over-demotion.
- **P:** fewer, higher-precision mutations improve the staged baseline.
- **Y:** demotions fell from 15 to four, confirming the local ternary effect,
  but external lanes agreed all four mutations were harmful. Accuracy and
  macro F1 fell versus A16.
- **U:** ternary absence handling is supported; free-standing span review is
  still the wrong object because direct comparison and pooling require
  study-level relations.
- **R:** remaining relation literalism versus external-reference error.
- **S:** `LOCAL_ONTOLOGY_SUPPORTED_REVIEW_MECHANISM_REJECTED`.

### v0.85 Study-Relation Review

- **L/O:** `L1 STRUCTURE` feeding `L2 COMPOSITION`; case-level arm, outcome,
  pooling, and coreference graph.
- **H:** shared structural binding allows safe evidence/context correction.
- **P:** graph-backed mutations repair the residual A16 errors.
- **Y:** only one of 12 cases was conflict-free; two mutations were made and
  both were independently judged harmful. The composed cost was 91,810 tokens.
- **U:** study structure increases interpretability but does not determine
  evidence utility. Binding and warrant must be separated.
- **R:** brittle graph contract versus the more fundamental structure/utility
  distinction.
- **S:** `STRUCTURAL_OBJECT_USEFUL_UTILITY_INFERENCE_REJECTED`.

## Phase D: Factorization and Role Composition

### v0.86 Factorized Benchmark Acquisition

- **L/O:** theory-level object split across binding, semantic warrant, context
  utility, and Kernel state utility.
- **H:** non-equivalent cognitive objects require separate observable surfaces
  and cannot be validated by one admission benchmark.
- **P:** distinct benchmarks expose distinct objects without granting
  cross-object authority.
- **Y:** SciFact, EBM-NLP, and a QASPER fixture were mapped to different
  objects; licensing and data boundaries were preserved. No Provider
  performance experiment occurred.
- **U:** this is the first explicit object upgrade after the admission patch
  chain. It is a theory and measurement architecture, not capability evidence.
- **R:** the factorization may be too benchmark-driven or omit organization
  variables.
- **S:** `OBJECT_LIFT_ACCEPTED_AS_RESEARCH_DIRECTION`.

### v0.87 SciFact Semantic Warrant

- **L/O:** `L1 SEMANTIC WARRANT` plus deterministic state compilation.
- **H:** a narrow warrant receipt can safely support claim-state cognition
  without Provider policy authority.
- **P:** strong label and rationale performance with zero harmful candidates.
- **Y:** label accuracy was `0.9444`, but one harmful strong candidate failed
  the gate. Official-style rationale F1 was `0.5652`, far below the
  preregistered internal proxy.
- **U:** the Provider can discriminate coarse warrant states, but claim scope
  and minimal complete evidence remain unresolved. Proxy equivalence failed.
- **R:** benchmark convention, aggregate/subgroup ambiguity, and rationale
  coordinate mismatch.
- **S:** `SEMANTIC_CAPACITY_SIGNAL_SAFETY_AND_MEASUREMENT_REJECTED`.

### v0.88 Evidence Set and Claim Scope

- **L/O:** attempted `L2 COMPOSITION`; sequential EvidenceSet and ClaimScope
  roles.
- **H:** evidence-first grouping followed by scope review provides independent
  correction and improves warrant safety.
- **P:** sentence F1 and harm improve relative to direct warrant.
- **Y:** sentence recall rose, but F1 fell `0.6667 -> 0.5957`; harmful strong
  candidates rose `1 -> 3`; cost rose `36,967 -> 96,051` tokens. ClaimScope
  produced no valid material-conflict correction.
- **U:** typed decomposition does not create cognitive multiplication.
  Downstream roles can inherit and strengthen an upstream framing.
- **R:** same-Provider correlation, evidence-group anchoring, benchmark
  coordinate mismatch, and small sample size.
- **S:** `COMPOSITION_ANTI_ADDITIVE`.

### v0.89 Claim-Atom Binding and Challenger

- **L/O:** `L2 COMPOSITION`; atom binding plus context-isolated veto-only
  challenge.
- **H:** explicit atom relations and an independent challenger remove harmful
  strong candidates while retaining correct ones.
- **P:** zero harm, high strong-candidate precision, and at least 0.80 correct
  retention.
- **Y:** harm fell `1 -> 0`, but only because the harmful case had an invalid
  binding receipt and failed closed. All nine valid semantic vetoes were false
  vetoes; correct-strong retention was `1/12`; label accuracy fell by `0.6111`.
- **U:** safety suppression is not cognitive correction. Relation-blind Kernel
  composition and correlated conservatism can turn detailed semantics into a
  nearly universal rejector.
- **R:** polarity compiler defect, challenger conservatism, same-Provider
  correlation, and atom ontology errors.
- **S:** `SAFETY_EFFECT_PRESENT_COGNITIVE_CONTRIBUTION_REJECTED`.

## Per-Round Theory-State Sequence

```text
v0.64  representation gate failure
v0.65  evidence-hygiene submechanism
v0.66  representation/composition split exposed
v0.67  deterministic compiler conditionality
v0.68  stable relational identity
v0.69  span-self-sufficiency rejected
v0.70  discourse inheritance insufficient
v0.71  immutable surfaces, redundant authority
v0.72  projection replay support
v0.73  prospective object-normalization failure
v0.74  local representation calibration pass
v0.75  transfer blocked by admission ontology
v0.76  three-axis ontology rejected operationally
v0.77  measurement ambiguity exposed
v0.78  redundant witness anti-additivity
v0.79  semantic fact/policy separation signal
v0.80  effect/context object split
v0.81  causal identifiability failure
v0.82  local component gain, system failure
v0.83  binary negative-review failure
v0.84  ternary local gain, reviewer rejection
v0.85  structure/utility distinction
v0.86  factorized object lift
v0.87  warrant capacity, safety/proxy rejection
v0.88  sequential-role anti-additivity
v0.89  suppression mistaken for correction
```

The sequence does not show monotonic capability growth. It shows repeated
local representation gains followed by transfer or composition failure.
