# Local Collective Cognition Experiment Pack

This optional workstation-local package compares a small-model collective with
a larger local baseline. It depends on AgentOS CoreSlim's public cognitive-work
contracts; AgentOS CoreSlim does not import or publish these machine-specific
adapters, benchmark fixtures, model paths, or smoke workflows as core features.

Experiment pack version: **0.66.0**

## Current v0.66 result

v0.66 follows the v0.65 benchmark bridge with a typed semantic-basis chain:
`Object/Timepoint Binding -> Comparator Orientation -> Significance Basis ->
Material Ambiguity -> Outcome Label`. Every admitted span receives a separate
typed record before a global Provider synthesis.

The 12-case calibration did not pass. All 12 basis receipts were complete, but
two of 12 synthesis receipts contradicted their own typed basis and were
blocked by the consistency gate. Exact label accuracy fell from the v0.65
baseline's `9/12` to `8/12`, with only `10/12` valid final receipts. The chain
corrected a `p=0.07` trend error and safely exposed one measurement ambiguity,
but it harmed two previously correct cases. The previously unused 36-case
fresh holdout was frozen but never executed.

The result narrows the next object to an explicit multi-arm `ComparisonFrame`
and a deterministic compiler from typed basis to candidate label or abstention.
A second free-form synthesis Provider should not be allowed to override the
coordinates it receives. CoreSlim remains `0.4.0-alpha.21`; v0.66 has no
production memory, retention, baseline, or pointer authority.

## Components

| Component | Responsibility | Authority boundary |
| --- | --- | --- |
| `LocalTransformersResidentPool` | Load all configured Transformers models once and keep them resident on CUDA | A single lock serializes generation on the shared GPU |
| `LocalTransformersJsonAdapter` | Produce schema-bounded JSON and record every successful or rejected attempt | It cannot score answers or issue Cognitive Work control |
| `OllamaJsonAdapter` | Call native Ollama JSON Schema output with a configurable long timeout | Thinking is retained separately in memory and never mixed into the semantic result |
| `ProviderTelemetryLedger` | Record model, task contract, tokens, calls, latency, cost, output, evidence, failure, and thinking commitments | Invalid retries remain visible cognitive work |
| `FrozenAnswerBenchmarkHarness` | Own hidden answers, audit Provider inputs, and score exact final answers | Providers never receive the private truth map; scoring is mechanical |
| `BenchmarkRoutingCalibrator` | Produce shrinkage-based domain, confidence, retry, and pairwise reviewer receipts | Aggregate correctness is Harness-owned; hidden answers never enter policy state |
| `CostAwareReviewPolicy` | Select a primary before observing peer outputs and budget review by expected marginal Cbit per cost | Advisory receipts guide routing but cannot score or promote themselves |
| `ReviewOutcomeReceipt` | Compare predicted review gain with actual corrections and harms | Outcome accounting is mechanical and feeds later calibration only |
| `ReliabilityLifecycleLedger` | Ingest candidate-only cycle evidence, require explicit promotion, decay old credit, and flag rank drift | Promotions are experiment-only and never alter Core baseline authority |
| Shadow exploration | Spend a bounded number of calls to refresh uncertain model credit | Exploration outputs are candidate-only and cannot change the current answer |
| `DisagreementOperatorReceipt` | Measure domain-scoped majority corrections, harms, and disagreement frequency | Historical operator value is advisory and bound to its source holdout |
| `ContextualDisagreementPolicy` | Compete `MAJORITY` against `STOP` using expected Cbit per extra call | Peer outputs are requested only after the operator clears its historical gate |
| `HierarchicalFingerprintCreditLedger` | Shrink Harness-owned credit from structural fingerprint to domain to global priors across promoted cycles | Source reports and promotions are hash-bound, experiment-only, and cannot alter Core authority |
| `StructuralMicroProbePolicy` | Route by structural task fingerprint and spend at most one peer call on a pre-registered low-evidence item | The schedule is frozen before current holdout outputs exist; outcome receipts separate correction from harm |
| `StructuralOperatorCompetitionPolicy` | Let `STOP`, second-ranked peer verification, and majority compete on immediate Cbit, information value, and work cost | Current outcomes cannot update their own route; counterfactual resolution is candidate-only |
| `CognitiveWorkExecutionBridge` | Bind telemetry and Harness receipts into one Cognitive Work observation | Submission fails unless audited task contracts and telemetry sources match exactly |

## Hidden-answer boundary

The Harness stores `BenchmarkQuestion` and `BenchmarkAnswerTruth` as separate
objects. `provider_inputs()` exposes only the public questions and evidence
surface. Every Provider task must be audited before its output can be scored.
Truth-bearing keys such as `expected_answer`, `answer_key`, `ground_truth`, and
`hidden_answers` cause a hard block.

The Harness receipt contains a truth commitment hash, not the answers. The
candidate covers every item exactly once and is mechanically scored. The
resulting exact accuracy is the Harness-owned observed Cbit for that trial.

## Work accounting

One Provider task may require more than one structured attempt. Each attempt
gets its own telemetry receipt. A rejected evidence citation, malformed JSON,
or schema violation is therefore counted rather than overwritten by the later
successful retry.

The ExecutionBridge aggregates:

- input, output, and cached tokens;
- actual Provider calls, including rejected attempts;
- wall-clock latency, API cost, tool calls, and tool cost;
- model IDs, agent IDs, organization topology, and round index;
- exact Harness Cbit, errors exposed, and errors corrected.

The aggregate is submitted to `CognitiveWorkAccountingRuntime`, whose normal
budget, marginal-Cbit, stop, reorganization, escalation, retention, replay,
and authority rules remain in force.

## Local smoke

The workstation defaults are configurable command-line arguments:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/local_provider_prerequisites_smoke.py
```

Useful modes:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/local_provider_prerequisites_smoke.py --small-only
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/local_provider_prerequisites_smoke.py --ollama-only --ollama-thinking
```

The smoke requires no cloud credential. The Transformers phase unloads before
the 32B Ollama phase so that a 16GB GPU does not need to host both groups at
once.

## Collective cognition pilot

The pilot compares three independent small-model runs, a no-communication
majority, a reviewer/synthesizer iterative team, and one DeepSeek-R1 32B run on
the same hidden-answer benchmark:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_collective_cognition_pilot.py
```

The three independent proposals are shared by the majority and iterative arms,
so the pilot estimates the marginal effect of communication without paying for
duplicate proposal generation. It is a deterministic single-workstation pilot,
not a general model-scaling result.

Protocol v0.2 uses the same per-item public slice and minimal structured answer
contract for every model size. Earlier batch-output checkpoints are protocol
diagnostics and are not admitted into the equal-contract comparison.

Protocol v0.3 treats v0.2 as a calibration set and evaluates a new frozen
holdout. Domain-scoped Harness reliability and current model confidence select
one primary model per item; a second model is called only when expected gain
clears the review cost floor:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_selective_collaboration_pilot.py
```

Protocol v0.4 turns confidence, sparse domain evidence, structured retries,
Provider work, and pairwise reviewer history into one advisory calibration
receipt. It chooses the primary model before peer outputs exist, then records
whether each paid review corrected, harmed, or left the answer unchanged:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_calibrated_collaboration_pilot.py
```

The v0.4 pilot preserved the best small-model score while using less than half
the majority arm's calls and tokens. Its seven reviews produced no correction
and one harmful override, so reviewer-value transfer is not yet validated. The
outcome receipt makes that failure explicit instead of treating review activity
as cognitive gain.

Protocol v0.5 requires positive observed correction surplus and a positive
Wilson-bounded net-Cbit estimate before a reviewer can receive work. It uses a
third frozen holdout and does not tune against the v0.4 evaluation set:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_evidence_gated_collaboration_pilot.py
```

The evidence gate eliminated harmful reviews, but the original calibration
profile did not transfer: Llama became the strongest member on holdout v3 while
the route continued to prefer Qwen and Gemma. Post-hoc domain receipts are
therefore emitted as candidate-only inputs for a later reliability lifecycle;
they never alter the trial that produced them.

Protocol v0.6 explicitly promotes the v0.5 diagnostic cycle for experiment use,
combines it with older calibration under recency decay, detects rank changes,
and reserves two paid shadow-exploration calls:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_reliability_lifecycle_pilot.py
```

The lifecycle route recovered the best-member score with roughly one third of
majority work. On the fourth holdout, however, majority voting exceeded every
single member and matched the 32B baseline. This shifts the next research target
from static model credit to selective disagreement arbitration.

Protocol v0.7 promotes both completed lifecycle cycles, generates a Harness-
owned majority-operator receipt from v0.6, and calls two peers only in domains
where historical majority corrections exceeded harms:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_contextual_arbitration_pilot.py
```

Formal-domain arbitration did not transfer to the fifth holdout: three paid
arbitrations produced no correction and no harm. The result narrows the next
target to task-structure fingerprints and hierarchical credit rather than more
domain-level threshold tuning.

Protocol v0.8 replaces broad domain routing with twelve observable structural
fingerprints. Five completed frozen cycles are converted into Harness-owned
credit receipts, explicitly promoted for experiment use, and combined through
fingerprint-to-domain-to-global shrinkage. A schedule of at most three
single-peer micro-probes is frozen before the sixth holdout begins:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_structural_fingerprint_pilot.py
```

On holdout v6, structural routing scored 7/12, exceeding the best small model
at 6/12 and full majority at 5/12 while using about 38% of majority calls and
tokens. DeepSeek-R1 32B scored 8/12 and the small-model candidate-union ceiling
was 11/12. All three micro-probes left their answers unchanged, so the observed
gain came from selecting members by task structure, not from extra discussion.
This is promising evidence for structural specialization, but one holdout is
not enough to grant production routing authority.

Protocol v0.9 promotes v0.8 as a sixth structural-credit cycle and generates a
Harness-owned operator receipt from the completed v0.8 result. `STOP`, one-peer
verification, and full majority then compete independently for each fingerprint;
immediate correction value, future information value, and work penalty remain
separate fields:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_structural_operator_pilot.py
```

On holdout v7, majority received no work because its v0.8 history showed no
corrections and two potential harms. Four one-peer verifications were selected.
The operational route scored 4/12, matching the best small model and majority
with 40% of majority work; all four verifications left the answer unchanged.
A Harness-owned counterfactual found that directly adopting the observed peer
on those paid disagreements would have corrected two items with no harm,
reaching 6/12 and matching the 32B baseline. The next bottleneck is therefore
disagreement resolution, not finding useful peers or adding more communication.

Protocol v0.10 separates acquisition credit from post-disagreement resolution
credit. The completed v0.9 disagreements become a Harness-owned evidence
candidate, receive an explicit experiment-only promotion, and are shrunk through
fingerprint, domain, and global resolver priors. Primary-selection confidence is
never reused to decide who wins a disagreement:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_resolution_lifecycle_pilot.py
```

On holdout v8, structural routing scored 8/12, above the best small model at
6/12, full majority at 5/12, and DeepSeek-R1 32B at 7/12. It used about 42% of
majority calls and tokens. Two paid peers agreed with the primary; the other two
disagreed, and independent resolver credit kept the primary both times. This
produced no direct correction or harm. A Harness-owned counterfactual showed
that blindly adopting both peers would have harmed two correct answers. The
resolver therefore demonstrated negative-transfer prevention, while positive
disagreement correction remains unproven on this holdout.

Protocol v0.11 promotes both v0.9 and v0.10 disagreement cycles, measures the
prediction-outcome error of the resolver, and adds two pre-frozen exploration
calls for sparse fingerprints. Acquisition credit remains frozen so that the
experiment isolates resolver calibration:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_calibrated_resolution_pilot.py
```

On holdout v9, the calibrated route scored 2/12 versus 3/12 for the best small
model and majority, 7/12 for DeepSeek-R1 32B, and a 4/12 small-model union
ceiling. It used about 51% of majority calls and tokens. The resolver kept the
primary on all four disagreements. A Harness counterfactual showed that two of
those peers would have corrected wrong answers with no harm. v0.11 therefore
rejects the stronger claim that fingerprint-only resolver credit is sufficient:
the gate became overconservative after cross-cycle shrinkage. The negative
result is retained as the design boundary for a future, independently testable
disagreement-context object rather than patched by lowering one threshold.

Protocol v0.12 introduces a Harness-owned `DisagreementResolutionContext`.
It combines directed primary-to-peer identity, an independent third-model
support topology, and task fingerprint credit. The third model never sees the
other proposals and is charged only after a real primary-peer disagreement:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_context_resolution_pilot.py
```

On holdout v10, the context route scored 4/12 versus 5/12 for the best small
model, 4/12 for majority, and 9/12 for DeepSeek-R1 32B. It used about 66% of
majority calls and tokens. Five disagreements triggered a third witness, but
the hard pair gate made no override: one possible override would have corrected
an answer and another would have harmed one, for zero counterfactual net Cbit.
This rejects the claim that third-model support topology alone is a sufficient
resolution signal.

Protocol v0.13 promotes the v0.12 outcomes into the directed pair ledger and
tests transfer on another untouched holdout:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_iterated_context_pilot.py
```

On holdout v11, the route scored 2/12 versus 3/12 for the best small model,
2/12 for majority, and 6/12 for DeepSeek-R1 32B. It used 58% of majority calls
and about 58% of its tokens. Both disagreements occurred on historically
negative directed pairs, so the gate kept the primary. One peer would have
corrected a wrong answer with no harm. The result rejects a second stronger
claim: directed model-pair credit is not a task-invariant constant. The next
resolution object must model a hierarchically shrunk pair-by-task-context
interaction and validate it on multiple frozen cycles before any production
authority is considered.

Protocol v0.14 replaces historical pair credit as decision authority with
current-case semantic evidence. Two isolated advocates justify the disagreeing
answers, then a third model judges randomized anonymous candidate records. The
Harness retains hidden truth and computes the outcome receipt:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_case_adjudication_pilot.py
```

On holdout v12, the route scored 5/12 versus 6/12 for the best small model,
4/12 for majority, 7/12 for DeepSeek-R1 32B, and a 7/12 small-model union
ceiling. It used 88.2% of majority calls and 92.4% of its tokens. Four
disagreements triggered case adjudication; every judge returned `AMBIGUOUS`, so
the Kernel made no override and produced no correction or harm. A Harness
counterfactual found two possible corrections and one possible harm. The result
therefore rejects the present argument contract as sufficient for positive
held-out Cbit. It supports the architecture boundary, but not effectiveness:
historical credit is diagnostic only, Provider failure is fail-closed, and
current-case authority requires explicit, auditable semantic evidence.

The next experiment must use a newly frozen holdout. It should test structured
derived facts, claim-to-step consistency, and judge-visible mechanical checks;
v0.14 is evidence to preserve, not a dataset for threshold tuning.

Protocol v0.15 implements that object as a truth-blind Harness replay receipt.
Candidate advocates remain isolated, the Harness replays only expressions
submitted by each advocate, and the blinded judge sees anonymous arguments plus
their replay status. An override requires a verified peer argument, a
non-verified primary argument, and a confident Provider judgment selecting the
peer:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_verified_case_pilot.py
```

On fresh holdout v13, the route scored 7/12, equal to the best small model,
versus 4/12 for majority and 3/12 for DeepSeek-R1 32B. It used 70.0% of majority
calls and 74.2% of its tokens. The result is not evidence that replay improved
semantic adjudication: all four disagreement cases failed closed at the first
argument stage, so no real replay receipt or judge decision was produced.
Moreover, the selected peers offered zero possible corrections and three
possible harms; the small-model union ceiling was also 7/12. v0.15 is therefore
classified as both a construction failure and a coverage failure. It does show
that failed semantic support remains charged, truth-blind, and unable to damage
the best member.

The next cycle must simplify the Provider surface to one expression while the
Harness derives replay details, and must freeze an opportunity-coverage gate
before routing. The gate may confirm that correction opportunities exist, but
must never disclose their item identities to the runtime policy.

Protocol v0.16 implements both changes. The Provider returns only an item id,
anonymous candidate id, one expression, and evidence refs. The Harness derives
the result and checks whether it actually supports the assigned candidate. A
pre-route aggregate receipt confirms correction headroom before any case work,
without exposing item identities or gaining routing authority:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_single_expression_pilot.py
```

On fresh holdout v14, the opportunity gate passed with one possible correction
and two possible harms among six frozen primary-peer pairs. The route scored
7/12 versus 6/12 for the best small model, 5/12 for majority, and 7/12 for
DeepSeek-R1 32B; the union ceiling was 10/12. That score improvement did not
come from the new mechanism: no case override occurred. Three of four cases
completed dual expressions, replay, and judgment, but all six expressions
failed replay or candidate binding. The route also cost 130.7% of majority
tokens.

The most informative failure occurred on the sole correction opportunity. The
wrong primary advocate derived the correct numeric value, which contradicted
its assigned answer and was therefore rejected as supporting evidence. This is
the desired safety behavior, but it exposes an orientation limit: a role forced
to defend a candidate cannot turn its own counterevidence into belief revision.
The next object is a Provider-backed `SUPPORT / RETRACT / REVISE` receipt, with
Harness replay identifying candidate consistency and Kernel retaining final
state-transition authority.

Protocol v0.17 implements that candidate-belief object. Each isolated role may
retain, revise, or retract its original answer. The Harness replays the supplied
expression and binds its result to a public option; a revision changes state
only when a blinded judge selects a verified receipt above the frozen Kernel
confidence gate. The aggregate pre-route gate now measures primary errors, not
only correct peers, so self-correction remains testable:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_candidate_revision_pilot.py
```

On fresh holdout v15, three of six frozen pairs contained a primary error even
though none had a correct peer. The route scored 3/12, equal to the best small
model and majority, versus 4/12 for DeepSeek-R1 32B; the small-model union
ceiling was also 4/12. Four cases completed without Provider transport/schema
failure, but all seven non-retracted expressions failed replay and the eighth
role retracted. No revision was adopted, so corrections, harms, and net case
Cbit were all zero. A direct peer override would have caused three harms.

This preserves candidate revision as the right cognitive object while rejecting
free-form expressions as a sufficiently constructible interface for the tested
1B-2B models. The next cycle should use a typed derivation plan or a
Harness-issued operand/operator scaffold. Providers must still select the
semantic operation and proposed candidate; Harness code remains limited to
mechanical validation, execution, binding, receipts, and hidden-truth scoring.

Protocol v0.18 supplies that typed scaffold. Public prompt values become
`VALUE_n` symbols, universal constants are limited to `CONST_1` and
`CONST_100`, and Providers build sequential steps from seven arithmetic/string
operators. Choice-only values are excluded. The Harness validates references,
executes the plan, binds the result to a public option, and returns a receipt:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_typed_derivation_pilot.py
```

On fresh holdout v16, the route scored 6/12 versus 5/12 for the best small
model, 3/12 for majority, 7/12 for DeepSeek-R1 32B, and an 8/12 small-model
union ceiling. It used 72.0% of majority calls and 88.8% of its tokens. That
one-point gain came from the inherited calibrated primary route, not the new
case mechanism. Two primary-error opportunities existed, but all four case
attempts failed at the first revision role: two typed-step validation failures
and two exhausted structured retries. No plan reached Harness execution.

Reference and synthetic tests prove that the typed algebra covers all 12 task
families and can support a verified self-revision. The real result nevertheless
rejects one-shot whole-plan serialization for the tested 1B-2B models. The next
object is an iterative session in which each turn chooses only one
`APPLY(operator, inputs)`, `FINALIZE(candidate)`, or `ABSTAIN` action and the
Harness immediately returns the next public `STEP_n` symbol. This keeps
semantic choice with the Provider while measuring the extra iterations and
coordination cost predicted by the cognitive-work hypothesis.

Protocol v0.19 implements that bounded iterative session:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_iterative_derivation_pilot.py
```

On fresh holdout v17, the route scored 5/12 versus 6/12 for the best small
model, 4/12 for majority, 6/12 for DeepSeek-R1 32B, and an 8/12 small-model
union ceiling. It used 68.75% of majority calls and 79.93% of its tokens. Three
sessions consumed eight Provider turns and 6,290 tokens. Two valid operations
reached immediate Harness execution, a narrower failure boundary than v0.18,
but six invalid actions closed all sessions before a final receipt. No answer
changed and case Cbit remained zero.

The first report counted iterative work only from completed receipts; a
hash-bound accounting addendum preserves the failed-session totals without
mutating the raw report. Future reports record completed, failed, and total
turns, steps, and invalid actions directly. The next experiment should split
action selection from action-specific arguments so each Provider call sees one
narrow contract, while charging the extra control turn explicitly.

Protocol v0.20 implements that two-stage surface on a fresh holdout:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_staged_derivation_pilot.py
```

The two-stage route scored 3/12, equal to the best small model and majority,
versus 6/12 for DeepSeek-R1 32B. It consumed 80 calls and 67,303 tokens, or
148.15% of majority calls and 261.00% of majority tokens. Six case sessions
produced 21 control turns, 17 argument turns, and twelve real Harness-executed
steps. Two sessions reached six steps each, demonstrating much deeper stateful
construction than v0.19. Nevertheless, all six sessions failed before a final
receipt, so no answer changed and case Cbit remained zero.

This is an anti-additive result at the outcome layer. Narrow schemas improve
mechanical depth, but a separate prompt-mediated JSON control call adds large
serialization and retry cost without reliable termination. The next object is
a constrained enum or tool action channel: Provider semantic choice remains
authoritative, while the local adapter mechanically guarantees registered
action and field shapes. More prompt stages are not the next move.

Protocol v0.21 implements a finite token-constrained tool channel:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_constrained_tool_pilot.py
```

The Runtime registers only truth-blind, mechanically executable calls. A token
trie constrains generation to those calls, the Provider logits choose the
semantic path, the Adapter maps it to a typed result, and the Harness executes
it. On fresh holdout v19, all eight candidate sessions across four cases
terminated successfully. They produced 46 constrained tool turns, 38 real
Harness steps, and zero invalid actions or channel failures. This closes the
serialization and termination defect observed through v0.20.

The cognitive result remained negative. The route scored 2/12 versus 4/12 for
the best small model, 3/12 for majority, and 7/12 for DeepSeek-R1 32B. It used
155.77% of majority calls and 433.33% of its tokens. No revision was adopted.
Three cases failed only after candidate completion, at the unchanged free-JSON
judge. A hash-bound addendum preserves six terminal receipts omitted by the raw
failure-path report without inventing their unrecoverable statuses.

v0.21 therefore passes the action-channel engineering gate but only partially
clears the cognitive gate. The next object is hierarchical constrained
selection over small action/operator/operand enums plus a constrained judge.
This must reduce the 9,724-option cumulative search surface and greedy-prefix
bias before more agents or roles are added.

Protocol v0.22 implements that hierarchy and gives every action-stage and
judge-stage choice a hash-bound score receipt:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_hierarchical_tool_pilot.py
```

On fresh holdout v20, all eight candidate sessions and all four constrained
judges terminated without Provider transport or schema failure. The cumulative
surface fell from 9,724 flat registered calls to 442 local menu entries, with a
mean of 4.56 options per inference pass. All 32 persisted score receipts passed
hash and distribution validation. This closes the hierarchical transport,
lineage, and free-JSON judge defects.

It does not yet close semantic selection. The route scored 3/12, equal to
majority, below the best small model at 4/12 and DeepSeek-R1 32B at 7/12. Only
one candidate receipt was verified, it merely supported an already-correct
answer, and no revision was adopted. Token cost reached 539.27% of majority.
Seven of twenty binary APPLY actions reused the same symbol as both operands,
showing that legal next-token menu choices are not calibrated semantic-utility
estimates. The next object is context-calibrated option scoring plus a bounded
Provider plan-intent receipt. Adding more roles or turns before that gate would
be anti-additive.

Protocol v0.23 subtracts a model-and-menu-size content-free label prior from
each bounded semantic choice. Candidate roles now commit a global intent mode,
ordered plan actions, and one terminal action in a Provider-backed receipt. A
Kernel-owned gate validates mode/operator consistency, replays the complete
plan, checks that finalization targets the last planned step, and enforces
frozen turn, inference-pass, and input-token budgets:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_plan_intent_pilot.py
```

On fresh holdout v21, the plan-intent route scored 4/12, equal to the best
small model and DeepSeek-R1 32B, below majority at 6/12. It used 79.25% of
majority calls and 170.05% of its tokens, within the predeclared 1.5x call and
4.0x token budgets. Context calibration reduced same-symbol binary operations
from seven in v0.22 to zero. Six completed plans passed Kernel replay, and one
additional session was blocked when its 15,376 input tokens exceeded the
14,000-token per-plan limit. All 15 semantic score receipts, six plan receipts,
six gate receipts, and the budget-stop receipt passed hash validation.

No plan produced a verified revision, no candidate changed, and observed case
Cbit remained zero. Both roles also classified the string task as numeric.
v0.23 therefore closes label-prior accounting, global-plan transport, and
Kernel consistency/cost enforcement, but not plan adequacy or cognitive gain.
The next object is a task-grounded intent-and-plan adequacy critic evaluated
before execution, not additional unqualified agents or turns.

Protocol v0.24 lifts the research object above planning. Two isolated Providers
form bounded problem-definition candidates, an independent coordinator compares
them, and a Kernel-owned gate admits only a formally coherent cognitive object.
Every admitted object is hash-bound to subsequent plan intent and allowed
operator families:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_problem_formulation_pilot.py
```

On fresh holdout v22, the route scored 5/12, matching the best small model and
DeepSeek-R1 32B, above majority at 2/12. It used 83.93% of majority calls and
116.14% of its tokens, within the frozen aggregate budget. All five scheduled
disagreement cases failed closed at Problem Admission, so no plan was executed
and no candidate changed.

The failure is upstream and informative. Across ten isolated problem candidates,
none exactly matched the Harness-held problem object and no item had an exact
candidate in its two-model union. Problem family accuracy was 0/10; intent mode,
target kind, and critical constraint each matched 2/10. One-shot factorized menu
selection is therefore rejected as a sufficient proxy for problem emergence.
The next object is an iterative Problem Dialogue in which proposal, objection,
and revision operate on a shared candidate object before Kernel admission.

Protocol v0.25 implements two context-isolated Problem Dialogue threads. In
each thread one model proposes a complete problem receipt, another model binds
an explicit critique and replacement object to it, and the original proposer
keeps, replaces, or retracts the object. A third model coordinates the two
revised threads. Kernel validates the full hash lineage before applying the
unchanged problem-admission and problem-plan gates:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_problem_dialogue_pilot.py
```

On fresh holdout v23, the route scored 4/12, equal to the best small model and
above majority and DeepSeek-R1 32B at 2/12. It used 94.00% of majority calls
and 202.59% of its tokens, inside the frozen budget. The apparent score gain
was primary-answer preservation, not dialogue correction: zero answers changed
and observed case Cbit remained zero.

All six dialogue lineages passed Kernel validation, but all three cases failed
closed at Problem Admission. Across proposal, critic suggestion, and revision,
no complete object matched the Harness reference and exact-item union stayed
at 0/3. The result therefore accepts role isolation and lineage transport while
rejecting critique over the same four factorized fields as a sufficient
problem-emergence mechanism. The next object is a truth-blind registry of
coherent whole-object templates plus a contrastive question that distinguishes
the leading alternatives. Adding more turns over independent field menus would
be anti-additive.

The structural-prior mini pilot tests the more upstream hypothesis that problem
formation needs an object-structure space, and that a Provider can synthesize a
temporary structural prior when AgentOS has no retained one:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_structural_prior_mini_pilot.py
```

Six fresh paired tasks used the same proposer in control and treatment. A
different model first expanded entities, relations, invariants, boundaries,
and a discriminating question for treatment. All priors remained hash-bound
`EPHEMERAL_CANDIDATE` objects with retention disabled. Field matches improved
from 2/24 to 7/24 across the six tasks: four improved, one was harmed, and one
was unchanged. A second real run reproduced every semantic output exactly.

This is preliminary support only. Exact problem objects remained 0/6, target
and critical-constraint accuracy remained zero, and treatment used 2.33 times
the calls and 3.33 times the tokens of control. It passed the inherited token
limit but failed the call limit. The next object is therefore a compact,
contrastive structural packet invoked selectively or amortized across several
hypotheses, not another unrestricted dialogue round.

The v0.24 experiment pack tests that compact selective path on a fresh holdout:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_contrastive_structural_pilot.py
```

A truth-blind Kernel policy escalates at most two risky direct definitions. One
independent Provider call supplies both compact packets, and only the selected
original proposers run again. Provenance hashes remain bound to receipts but
are excluded from semantic menu ordering. Two post-fix runs reproduced the
same selected items, per-item field changes, and exact packet contents. Calls
were exactly 1.5 times control; tokens were 1.76 times control.

The cognitive result is rejected, not promoted. Both packets were exact copies
of their public questions rather than rival structures with a discriminating
question. Field matches rose from 2/24 to 3/24 with no exact object, but that
change cannot be attributed to structural expansion. The Runtime records
`REJECTED_EXACT_PUBLIC_PROMPT_RESTATEMENT`; retention and baseline promotion
remain disabled. The next gate is an independent Provider-backed packet-quality
receipt before revision, with one selected item so the full path can still fit
the 1.5x call budget.

Protocol v0.25 closes that quality gate on a fresh holdout:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_quality_gated_structural_pilot.py
```

One model proposes the original object, a second elicits the contrastive packet,
and a third independently judges rival completeness, decisive contrast,
discriminating-question quality, and non-restatement. Kernel alone admits or
blocks revision. Two real runs reproduced the same result: `modular-27` was
selected, the elicitor returned only the identifier `modular-27`, the quality
Provider rejected all four criteria, and Kernel blocked revision. Selected-item
field matches remained 1/4. Calls were exactly 1.5 times control and tokens were
1.202 times control.

This is a quality-lifecycle success and a cognitive-result rejection. It proves
that a format-valid but semantically empty structural packet no longer reaches
revision, retention, or baseline evolution. It does not show that the local
small-model team can synthesize a useful structural prior. Because elicitation
needed two attempts, the blocked path already consumed the complete nine-call
budget; a successful revision would exceed it. The next gate is therefore
evidence-backed structure-elicitor capability routing plus a cheap mechanical
identifier/placeholder pre-gate, followed by another fresh holdout.

Protocol v0.26 tests that next gate without promoting cross-context credit to
same-context support:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_capability_routed_structural_pilot.py
```

The route treated the v0.1 per-model field gains as transfer-candidate evidence,
selected Gemma as the structure elicitor, and marked the binding
`TRANSFER_CANDIDATE_EXPLORATORY`. A cheap mechanical gate then checked for an
identifier, exact prompt copy, explicit placeholder, or structurally impossible
length before spending a semantic-quality or revision call.

Two live runs reproduced the same negative cognitive result. Gemma returned only
`modular-28` after two attempts; the mechanical gate blocked it, no quality judge
or revision ran, and selected-item field gain remained zero. The path used 8 calls
versus 6 for control (1.333x) and 1.056x the control tokens, so the cost gate
passed while cognition did not. This falsifies downstream problem-field gain as
a sufficient proxy for contrastive-packet elicitation capability. The next
capability object must be measured directly on packet completeness,
non-restatement, decisive contrast, and discriminating-question quality before
another fresh holdout. Adding more routing rounds with the current proxy would be
anti-additive.

Direct structure-elicitor calibration v0.2 replaces that proxy with a
four-case hidden Harness and a shared packet grammar:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_structure_elicitor_calibration.py
```

Every model receives the same public task and must produce `RIVAL_A`,
`RIVAL_B`, `CONTRAST`, and `QUESTION` fields. The Harness, not a Provider,
scores grammar completeness, non-restatement, rival-structure coverage,
decisive contrast, and discriminating-question quality. Failed transport
attempts remain in the token and call ledger. DeepSeek-R1 32B runs first and
is released before the three small models are loaded, so the 16 GB GPU never
hosts both groups.

An initial measurement was rejected because the semantic prompt exposed an
`output_key -> item_id` mapping and all models copied the identifier. After
removing that shortcut and adding a mechanical raw-packet wrapper that cannot
alter semantic content, two runs reproduced every packet and aggregate quality score exactly.
Lineage and telemetry hashes remain run-specific; the final main artifact also restores failed-attempt
costs that the earlier repeat receipt did not expose.
DeepSeek-R1 32B scored `0.65`; Gemma 2B scored `0.60`; Qwen 1.5B scored `0.55`;
Llama 1B scored zero after eight failed transport attempts. Gemma therefore
reached `92.3%` of the 32B calibration score with 1,242 versus 1,514 tokens and
one perfect packet versus none for 32B. This is calibration evidence, not a
fresh-holdout result: the receipt remains
`CALIBRATION_TRANSFER_CANDIDATE_EXPLORATORY`, grants no selection or retention
authority, and must next be tested on unseen structural objects with a frozen
rubric and 32B ceiling.

Fresh holdout v0.1 performs that test without changing the parser, five
criteria, or hidden lexical terms after seeing model output:

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_structure_elicitor_fresh_holdout.py
```

The four unseen objects ask models to distinguish edges from vertices, elapsed
duration from inclusive sample count, signed change from magnitude, and total
count from rate. The run is bound to the calibration artifact hash. It executes
the calibrated Gemma route, Qwen runner-up, and DeepSeek-R1 32B ceiling; Llama's
eight calibration transport failures remain visible as an explicit budget
exclusion rather than disappearing from the receipt.

Two deterministic runs reproduced all 12 trial outputs, including the same Qwen
transport failure, and the complete aggregate result. Gemma scored `0.55` on
4/4 successful trials, Qwen scored `0.35` on 3/4,
and DeepSeek-R1 32B scored `0.70` on 4/4. Gemma therefore retained zero routing
regret and reached `78.6%` of the 32B score. Each run used 13 Provider calls and
4,378 tokens. This advances the route to
`PROJECT_CAPABILITY_EVIDENCE_CANDIDATE`, but still grants no selection or
retention authority.

The frozen Harness is deliberately conservative. Its exact lexical terms gave
all three models low rival-coverage and contrast rates even where manual review,
especially of the 32B packets, finds semantically complete distinctions. The
experiment therefore supports reproducible relative routing under the matched
rubric; it does not yet establish a calibrated absolute semantic-quality scale.
Every prompt also states that an ambiguity exists, so this result does not test
endogenous object discovery or problem emergence.

Dual-Provider semantic calibration v0.1 tests whether the frozen lexical score
is also a credible absolute quality scale:

```powershell
python experiments/local_collective_cognition/examples/run_structure_semantic_judge.py
```

The Runtime creates a deterministic anonymous surface from the hash-validated
fresh artifact, shuffles the available Gemma, Qwen, and 32B packets within each
object batch, and withholds every source model ID and prior score. DeepSeek and
Kimi independently assign `PRESENT`, `UNCERTAIN`, or `ABSENT` to six frozen
semantic criteria. Providers cannot emit a total score. Local code validates
the exact candidate set, computes strict unanimous-present scores, preserves
direct conflicts, and grants neither judge selection or retention authority.
The unavailable Qwen path packet remains an explicit excluded trial.

The first live attempt completed DeepSeek 4/4 and Kimi 3/4; the partial 48
criterion pairs showed 81.25% exact agreement and 8.33% direct conflict, but the
completeness gate blocked promotion. A bounded recovery implementation now
retries only failed batches once and retains the original failed work. One
intermediate transport run established that Moonshot rejects the optional
`temperature` parameter and produced no semantic evidence.

The final bounded run completed all eight judge batches, with one Kimi batch
recovered. It consumed nine Provider calls and 30,694 tokens. Exact criterion
agreement was 83.33%, but direct conflict was 15.15%, above the prefrozen 10%
ceiling. The state therefore remains
`SEMANTIC_JUDGE_DISAGREEMENT_REQUIRES_AUDIT`. Strict effective semantic scores
were `0.75` for Gemma, `0.333` for Qwen, and `0.958` for DeepSeek-R1 32B; the
calibrated Gemma route still replicated and reached 78.3% of the 32B score.
Compared with the lexical Harness, semantic support raised Gemma by 0.20 and
32B by 0.258, while Qwen changed by -0.017.

Ten direct conflicts were concentrated in weak packets: eight on Qwen's change
and rate cases, two on Gemma's change case, and none on 32B. This supports the
need for Provider-backed semantic evidence while showing that two Providers do
not yet constitute an absolute gold scale.

Model-panel reference protocol v0.1 replaces the previously proposed human
annotation step with two fresh, independent model annotations and a bounded
disagreement adjudicator. It prepares separate GPT-5.6 and Gemini-3.1 packs:

```powershell
python experiments/local_collective_cognition/examples/prepare_structure_reference_panel.py
```

Each lane receives a different alias surface and deterministic order. Public
packs contain only the prompt, packet, frozen six-criterion rubric, response
contract, and expected annotator identity. Original model identity, mechanical
scores, earlier DeepSeek/Kimi judgments, and both alias maps remain in a private
hash-bound manifest. The generated panel currently contains 11 packets and 66
criterion labels and is explicitly `AWAITING_MODEL_ANNOTATIONS`.

After both responses are available, only their criterion-level disagreements
are sent to Kimi K3. Agreement cells do not consume an adjudication call:

```powershell
python experiments/local_collective_cognition/examples/build_structure_k3_adjudication_pack.py `
  --gpt-response <gpt-response.json> `
  --gemini-response <gemini-response.json>

python experiments/local_collective_cognition/examples/finalize_structure_reference_panel.py `
  --k3-bundle <clean-session-kimi-k3.zip>
```

K3 sees two anonymous, deterministically reordered positions per disputed
criterion, not GPT/Gemini names, source model identities, or prior scores. It
may select either position, independently reassess, or preserve
`UNCERTAIN/UNRESOLVED`. Its receipt must attest that only the pack was used,
annotator and source identities and prior scores were unavailable, and no
external content-based pairing was performed. The final artifact is a
`MODEL_PANEL_REFERENCE_CANDIDATE`: it is not human gold, ground truth, a model
selection authority, or a retention authority. This protocol measures panel
agreement and adjudication cost without pretending that model consensus alone
closes the epistemic gap.

Identity-aware adjudication records are not discarded when their semantic
surface is useful. The shadow importer verifies every lane alias through the
private manifest, requires the exact six-dispute surface, rebuilds all 66 final
labels, and preserves the source file hash:

```powershell
python experiments/local_collective_cognition/examples/ingest_structure_shadow_adjudication.py `
  --record <identity-aware-adjudication.json>
```

Such an artifact is fixed at `IDENTITY_AWARE_SHADOW_REFERENCE_CANDIDATE` with
`protocol_compliant=false`; it cannot satisfy the anonymous K3 receipt or gain
selection, retention, ground-truth, or human-gold authority.

An adjudicator that honestly discloses prior session exposure is handled by a
second shadow path rather than coerced into a false blinding attestation:

```powershell
python experiments/local_collective_cognition/examples/ingest_compromised_k3_bundle.py `
  --bundle <kimi-adjudication.zip>
```

The received K3 response bound all six adjudication IDs and selected positions,
but declared every blinding condition false because the same session had seen
annotator identities and prior scores. Under its stricter reading of the frozen
criterion definitions, four of six dispute labels flipped relative to the
identity-aware report, while zero of 11 packet-level PASS/REJECT verdicts
changed. The result is retained as
`CONTEXT_COMPROMISED_ADJUDICATION_SHADOW_CANDIDATE`. This is useful evidence of
criterion-level definition and context sensitivity, not a canonical panel
receipt.

A subsequent clean-session K3 bundle satisfied the exact pack hash, all six
adjudication IDs and position bindings, confidence/rationale fields, and all
five pack-only blinding attestations. The finalized artifact contains 66 labels:
60 GPT/Gemini agreements and six K3 adjudications, with two retained
`UNCERTAIN` cells. It differs from the first identity-aware shadow on one cell
and from the disclosed context-compromised shadow on three cells. Three of 11
packets are strict all-`PRESENT` passes.

Mapped back through the private manifest, available-packet mean `PRESENT`
scores are `0.833` for DeepSeek-R1 32B, `0.75` for Gemma 2B, and `0.50` for
Qwen 1.5B. Treating Qwen's unavailable fourth trial as zero gives an effective
`0.375`. This preserves the calibrated Gemma-over-Qwen route and raises Gemma
to 90% of the 32B reference score. The result remains
`MODEL_PANEL_REFERENCE_CANDIDATE`; model-panel agreement does not create
ground-truth, selection, retention, or production authority.

The finalized panel can calibrate the two historical semantic judges without
turning the panel into ground truth:

```powershell
python experiments/local_collective_cognition/examples/calibrate_structure_semantic_judges.py
```

Kimi K2.5 matched 59/66 panel labels (`0.894`) and DeepSeek V4 Flash matched
53/66 (`0.803`). Historical strict consensus matched 51/66. The candidate
policy therefore routes first to Kimi, but requires an independent second
judge for `UNCERTAIN`, confidence below `0.8`, and the weak
`NO_INVENTED_FACT_OR_SOLUTION_DEPENDENCE` criterion. Remaining conflict goes
to a model panel. This is a routing hypothesis, not selection authority.

Unstated-ambiguity holdout v0.4 then tests the missing upstream capability:
can a model notice that the requested output object itself has competing
interpretations when the prompt never says that an ambiguity exists?

```powershell
conda run -n dhrf_4080s python experiments/local_collective_cognition/examples/run_unstated_ambiguity_holdout.py
python experiments/local_collective_cognition/examples/analyze_ambiguity_role_complementarity.py
```

The hidden Harness contains four positive/null pairs over signed change, path
length, interval duration, and traffic count/rate. Prompts expose neither the
labels nor ambiguity vocabulary. Frozen gates require at least `0.75` balanced
accuracy, positive recall, and null specificity, with at most `0.25` null
false-positive rate. v0.1 isolated transport failures; v0.2 closed transport;
v0.3 separated state detection from packet construction and exposed a concrete
answer-template prior; v0.4 removed that template and counterbalanced the state
menu by item. Truth and gates remained unchanged across these construction
audits.

All 24 v0.4 trials completed with nonzero self-confidence. Gemma 2B obtained
`1.0` positive recall and `0.0` null specificity, with one `UNCERTAIN` null
case. Qwen 1.5B returned `AMBIGUITY_PRESENT` on every item. DeepSeek-R1 32B
returned `NO_MATERIAL_AMBIGUITY` on every item, giving `0.0` recall and `1.0`
specificity. Every model therefore had `0.50` balanced accuracy and failed the
frozen gate. Counterbalanced menu positions did not change these orientations.

The role artifact binds Gemma as the lower-cost high-sensitivity proposer and
32B as the high-specificity skeptic. They disagree on all eight items. Naive
OR and three-model majority exploit Gemma's one `UNCERTAIN` result and reach
`0.625` balanced accuracy, but specificity remains `0.25`; AND remains at
`0.50`. Hidden-label oracle choice reaches `1.0`, but is explicitly recorded as
non-operational. The result is therefore
`ROLE_COMPLEMENTARITY_OBSERVED_COORDINATOR_VALIDATION_REQUIRED`, not evidence
of successful collective discovery.

Kimi K2.5 is named only as an unvalidated semantic-coordinator candidate from
the separate 66-label calibration. The next test must use a fresh hidden
holdout and identity-blind proposer/skeptic receipts. It must compare the
coordinator against the best fixed vote under the same Provider-call and token
budget, abstain on missing or unresolved receipts, and leave final candidate
state with the Kernel. Reusing these eight labels to tune or validate the
coordinator is forbidden.

Fresh coordinator holdout v0.1 freezes that next test on 12 new items and six
new positive/null pairs. It reuses neither the prior eight prompts nor their
item IDs. The public objects cover rectangle size, hexadecimal size, table
dimension, vote support, network size, and compression. Gemma proposer and
local DeepSeek-R1 32B skeptic receipts are generated before any coordinator
call, persisted in a hash-bound checkpoint, and then exposed only as
counterbalanced `POSITION_A`/`POSITION_B` records. Model identity, Provider,
role orientation, prior scores, and hidden truth remain outside Provider input.

```powershell
conda run -n dhrf_4080s python `
  experiments/local_collective_cognition/examples/run_ambiguity_coordinator_fresh_holdout.py
```

The fixed `OR_POSITIVE` comparator, semantic target, labels, and gates were
committed before execution. The coordinator must reach at least `0.75`
balanced accuracy, recall, and specificity; improve balanced accuracy by at
least `0.08`; keep uncertainty at or below `0.25`; and remain within `1.25x`
Provider calls and `2.5x` tokens. AgentOS retains final candidate-state
authority.

The local roles again reached only `0.50` balanced accuracy. Gemma obtained
`0.667` recall and `0.333` specificity; 32B obtained `0.0` recall and `1.0`
specificity. Their OR was identical to Gemma. The Kimi K2.5 primary coordinator
then produced zero semantic decisions. v0.1 preserved four
`provider_response_contains_no_json_object` receipts across two six-item
batches. A construction-only v0.2 reused the exact checkpoint, labels, semantic
objective, and gates while splitting to four three-item batches with one call
each. It still produced zero decisions: two responses contained no JSON object
and two contained invalid JSON. Further prompt or batching changes on this
holdout were stopped.

The calibrated secondary judge was therefore activated through a separate,
hash-bound fallback role candidate rather than silently replacing Kimi:

```powershell
conda run -n dhrf_4080s python `
  experiments/local_collective_cognition/examples/run_ambiguity_coordinator_fallback.py
```

DeepSeek V4 Flash completed all 12 decisions. It raised balanced accuracy from
the frozen OR's `0.50` to `0.75`, with `0.833` recall, `0.667` specificity, four
corrected comparator errors, one harmed case, and no abstentions. The route used
29 versus 25 Provider calls (`1.16x`) and 18,170 versus 9,861 tokens (`1.843x`).
All frozen gates passed except null specificity, so the artifact remains
`COORDINATOR_CALIBRATION_GATE_FAILED`.

The semantic residual is interpretable. The coordinator invented ambiguity in
two explicit nulls (hexadecimal character count and support percentage), while
one positive rectangle-size case was missed after the proposer supplied
semantically collapsed rivals. This revises the object from "coordination is
absent" to "positive coordination Cbit is observed, but materiality
specificity and input-receipt quality remain unresolved." No Baseline Object
Update follows. The next test requires new hard-null cases and an independently
frozen receipt-quality/materiality control; these 12 labels cannot be used for
further tuning.

Hard-null holdout v0.1 closes that next test without reusing the 12 labels. It
freezes 16 new, independently worded items, eight material positives and eight
hard nulls, plus two hash-bound controls before Provider execution. The
materiality control requires two task-grounded interpretations that change the
operation, boundary, unit, or output and are not resolved by an explicit
qualifier. The receipt-quality control requires complete, grounded, distinct,
and output-sensitive support before any positive coordinator decision.

```powershell
conda run -n dhrf_4080s python `
  experiments/local_collective_cognition/examples/run_ambiguity_hard_null_holdout.py
```

The pre-execution commitment was written before either local role ran. Gemma
2B again produced the high-sensitivity orientation (`0.75` recall, `0.25`
specificity), while DeepSeek-R1 32B produced the exact null orientation (`0.0`
recall, `1.0` specificity). Their frozen OR remained at `0.50` balanced
accuracy. DeepSeek V4 Flash completed only 8 of 16 controlled decisions: it
reached `0.375` balanced accuracy, `0.50` recall, and `0.25` hard-null
specificity, a `-0.125` balanced change from OR. Two later batches were rejected
because `USABLE_MATERIAL_SUPPORT` conflicted with their own quality flags.
Calls (`1.125x`) and tokens (`2.317x`) stayed within budget, but completeness,
specificity, gain, recall, and uncertainty gates failed. The result is
`HARD_NULL_COORDINATOR_GATE_FAILED`; the same labels must not be used for
prompt, threshold, quality-state, or routing adaptation.

Receipt-quality calibration v0.1 therefore moves upstream and removes final
ambiguity classification from the calibration object. Its independent corpus
contains 14 new receipts over 14 new prompts: two complete controls and two
targeted perturbations for each of the six frozen quality criteria. Construction
targets stay in the private manifest and are explicitly not ground truth.

```powershell
python experiments/local_collective_cognition/examples/prepare_receipt_quality_calibration.py
python experiments/local_collective_cognition/examples/run_receipt_quality_candidate_judge.py
```

The first command creates lane-specific GPT-5.6 and Gemini-3.1 annotation packs
with different aliases and item orders. The second froze all 14 DeepSeek V4
criterion predictions before any panel labels existed, using 14 calls and
23,667 tokens with no failed batches. `build_receipt_quality_k3_pack.py`
validates the two independent responses and sends only criterion disagreements
to an identity-blind Kimi K3 pack. `finalize_receipt_quality_calibration.py`
then builds the candidate-only panel reference and applies the already frozen
agreement, packet-state, false-usable, and unresolved-rate gates.

The returned GPT-5.6 and Gemini-3.1 responses both passed pack, lane, model,
annotation-ID, criterion, note, confidence, and whole-response validation. They
agree on 77 of 84 criterion cells and disagree on seven. Six disagreements are
on `QUESTION_RESOLVES_AMBIGUITY`; one is on `RIVAL_A_OBJECT_FIT`. Only those
seven anonymous cells are present in the Kimi K3 pack, which exposes neither
annotator identity nor construction targets, prior labels, or DeepSeek
predictions. The returned Kimi K3 receipt resolved all seven cells and produced
an 84-label `MODEL_PANEL_REFERENCE_CANDIDATE` with no ground-truth claim.

Against that complete reference, the frozen DeepSeek candidate reached `0.75`
criterion agreement, `0.429` packet-state accuracy, and `0.667` false-usable
rate. It passed only complete prediction coverage and unresolved-rate gates;
agreement, packet accuracy, and false-usable control failed. The strongest
criterion was `RIVALS_STRUCTURALLY_DISTINCT` (`1.00`), while
`QUESTION_RESOLVES_AMBIGUITY` was weakest (`0.571`). Eight of twelve reference-
unusable packets were incorrectly promoted to `USABLE`. Final state:
`RECEIPT_QUALITY_JUDGE_CALIBRATION_GATE_FAILED`.

Negative-evidence split holdout v0.1 starts from that failure without reusing
any of its 14 prompts or labels. It freezes 18 new receipts in three private
construction groups: six complete controls, six false-ambiguity controls, and
six invented-dependence controls. The construction groups remain diagnostics,
not truth. A six-criterion monolithic baseline runs beside two isolated
Provider roles: a live-ambiguity auditor and a fabrication-dependence auditor.
The local fusion rule is mechanical and one-way: either specialist may
downgrade a baseline receipt, but neither may promote one.

```powershell
python experiments/local_collective_cognition/examples/prepare_negative_evidence_holdout.py
python experiments/local_collective_cognition/examples/run_negative_evidence_candidate.py
```

The pre-label DeepSeek V4 Flash run completed 27/27 calls over nine two-item
batches and used 42,717 tokens. The monolithic baseline marked 16/18 packets
`USABLE`; veto fusion retained six and rejected twelve. As a non-ground-truth
construction diagnostic, all six complete controls were retained, all six
false-ambiguity controls were vetoed by the live-ambiguity role, and all six
invented-dependence controls were vetoed by the fabrication role. The frozen
candidate run hash is
`dd3a9eb507a9cf78a5e264758b4027acc8c1e714e84018bd7fce18eccdef7de5`.
GPT-5.6 and Gemini-3.1 packs are now frozen; only their complete model-panel
reference, with Kimi K3 adjudicating disagreements, may determine whether the
false-usable, usable-recall, unresolved-rate, and `3.2x` call-budget gates pass.
Both returned annotation surfaces passed identity, pack-hash, annotation-ID,
criterion, note, confidence, and completeness validation. GPT-5.6 and
Gemini-3.1 agree on 96/108 criterion cells. All twelve disagreements concern
`QUESTION_RESOLVES_AMBIGUITY`; the other five criteria agree on all 90 cells.
Only those twelve anonymous cells have moved into the Kimi K3 adjudication
pack. Kimi K3 returned twelve `ABSENT` decisions with no unresolved cell,
completing a candidate-only reference of six `USABLE` and twelve `UNUSABLE`
packets. Relative to that reference, the monolithic baseline preserved all six
usable packets but falsely promoted ten of twelve unusable packets
(`0.833` false-usable rate). Veto fusion preserved the same `1.0` usable recall
and rejected all twelve unusable packets (`0.0` false-usable rate), with no
unresolved output and a `3.0x` Provider-call multiplier. All frozen gates pass;
the state is `NEGATIVE_EVIDENCE_SPLIT_CALIBRATION_CANDIDATE`.

This is calibration evidence against a model-panel reference, not human gold or
ground truth. It grants no selection, retention, coordination, or production
authority. A new distribution-shifted holdout is required before the split
roles can become an AgentOS capability policy.

Negative-evidence generalization v0.2 supplies that next holdout without
reusing any earlier prompt or label. Its 24 receipts cross six private
construction categories and four packet formats, including mixed defects and
adversarially clean cases. Four arms are frozen: one monolithic pass, three
independent monolithic passes with criterion-wise majority, same-model
live/fabrication specialists, and a heterogeneous live specialist. Every
three-call arm is scored against the same baseline receipt, and the same-model
split must gain at least `0.10` packet accuracy over the `3x` monolithic arm.

```powershell
python experiments/local_collective_cognition/examples/prepare_negative_evidence_generalization.py
python experiments/local_collective_cognition/examples/run_negative_evidence_generalization.py
```

The first pre-label run preserved all payloads but was transport-incomplete:
DeepSeek lost one baseline and one repeated-monolithic batch, while Kimi K2.5
returned `12/12 PROVIDER_UNAVAILABLE` with zero tokens. Before any reference
label returned, transport-recovery v0.2.1 froze a full rerun, at most two exact-
contract attempts, unchanged prompts/gates, and local DeepSeek-R1 32B as the
heterogeneous live auditor. The recovery contract hash is
`3a281809e6e336aa0c23b94656775e4997270348e8bcbcbcdefbf56da22600aa`.

The recovery run completed every DeepSeek lane. Single and budget-matched
monolithic arms marked all 24 packets `USABLE`; same-model split retained ten
and vetoed fourteen, using 37 attributed calls (`3.083x`). The local 32B lane
completed only 5/12 batches; seven exhausted both attempts because they emitted
evidence references outside admitted scope. Its heterogeneous arm is therefore
transport/contract-incomplete and already exceeds the `3.2x` call gate on the
recorded lower bound. Private construction diagnostics also show same-model
split vetoing one clean-ambiguous and one boundary-composition item, so recall
cannot be assumed. Frozen candidate hash:
`8571a911fb0bb497d435c4b59fb116703a8b867730f82d161531f3c8d15d7ee1`.
The returned GPT-5.6 and Gemini-3.1 annotations pass their independent lane,
pack-hash, panel, schema, and complete-coverage checks. They agree on 136/144
criterion cells. All eight disagreements concern
`QUESTION_RESOLVES_AMBIGUITY`; the other five criteria agree on all 120 cells.
Only those eight cells were exposed in the identity-blind Kimi K3 pack bound to
hash `182e5bd86a49efaf2848a23623dfa34d46df40a017a40e5f092759b3a859422e`.
The exact panel/hash-bound K3 response resolves all eight, producing a complete
144-label model-panel reference with 12 usable and 12 unusable packets.

The frozen comparison does not admit the architecture. Single and budget-
matched monolithic arms both reach `0.50` packet accuracy and falsely promote
all 12 unusable packets. Same-model split reaches `0.917` accuracy, reduces
false-usable rate from `1.0` to `0`, and stays inside budget at `3.083x`, but
vetoes two reference-usable packets. Its usable recall is `0.833`, below the
frozen `0.85` minimum, and its `0.167` recall harm exceeds the allowed `0.10`.
Both errors originate in the live-ambiguity specialist, while fabrication
passes. The heterogeneous arm is also rejected at `0.50` accuracy, `0` usable
recall, `0.167` unresolved rate, and `3.417x` recorded calls. Current state:
`ROLE_STRUCTURE_GENERALIZATION_GATE_FAILED`; the result grants no selection,
retention, coordination, or production authority.

### Precision-confirmed veto v0.3

The next external experiment targets the two false live-ambiguity vetoes without
reusing any v0.2 prompt. It freezes 24 new receipts across common-default,
multi-dimensional, reporting-boundary, explicit-object, invalid/equivalent-
rival, and invented-dependence constructions. These construction categories
remain private diagnostics rather than truth. The current model-panel labels do
not exist at prediction time.

The architecture adds one context-isolated confirmation role. It is called only
when the monolithic baseline is `USABLE`, the live-ambiguity specialist emits
`VETO`, and fabrication emits `PASS`. The confirmer cannot see the first
auditor's identity, state, or rationale. It may confirm the veto or restore the
baseline, but cannot promote a baseline failure. Four frozen arms compare one
monolithic pass, a four-pass monolithic supermajority ceiling, naive specialist
veto, and conditional confirmed veto. Admission requires at least `0.90` usable
recall, at most `0.10` false-usable rate, no false-usable increase over naive
veto, positive recall gain over naive veto, at least `0.10` accuracy gain over
the four-pass control, and no more than `4.0x` calls.

The first pre-reference run preserved one fabrication semantic-shape failure.
Runtime v0.3.1 added only fail-closed candidate binding for failed confirmation
receipts, froze a full-run recovery contract, and prohibited individual-batch
patching. The complete rerun used 75 calls and 131,500 tokens. Single and four-
pass monolithic arms retained 23/24 receipts; naive veto retained 14 and rejected
10. Conditional confirmation used three extra batch calls over naive veto,
rejected all five eligible vetoes, and therefore retained 19 while rejecting
five at `3.25x` calls with no unresolved output.

This is not yet a correction result. Private diagnostics place all five restored
receipts in explicit-object or invalid/equivalent-rival constructions, which is
a warning that confirmation may be cancelling correct vetoes. The returned
GPT-5.6 and Gemini-3.1 annotations pass their independent lane, pack-hash,
panel, schema, and complete-coverage checks. They agree on 133/144 criterion
cells. All eleven disagreements concern `QUESTION_RESOLVES_AMBIGUITY`; the
other five criteria agree on all 120 cells. Only those eleven cells are exposed
in the identity-blind Kimi K3 pack bound to hash
`de9ee92c5b83e4edb1203bd5a4c4639dca18b1b2ebbea12781ed8029262d828c`.
The exact panel/hash-bound K3 response resolves all eleven cells without an
uncertain or unresolved label, producing a complete 144-label model-panel
reference with 12 usable and 12 unusable packets. The frozen result rejects the
confirmation architecture. Naive veto reaches `0.917` packet accuracy, `1.0`
usable recall, and `0.167` false-usable rate at `3.0x` calls. Conditional
confirmation restores five vetoed receipts, but all five are reference-unusable:
accuracy falls to `0.708` and false-usable rate rises to `0.583` at `3.25x`,
with no recall gain. It fails the false-usable, marginal recall-gain, no-harm,
and worst-category gates. Current state:
`PRECISION_CONFIRMED_VETO_GATE_FAILED`. The naive comparator is informative but
was not pre-registered for admission in this contract, so neither arm receives
selection, retention, coordination, or production authority.

### Structured semantic defer v0.4

The next fresh 24-receipt holdout pre-registers two independent questions. The
first asks whether the three-role naive architecture replicates under the v0.2
safety gates. The second compares that arm with an equal-cost structured live-
ambiguity role. Instead of emitting `PASS` or `VETO`, the structured Provider
reports whether the requested object is explicitly fixed, whether both rivals
are valid and distinct, and whether an answer to the proposed question would
discriminate. Runtime alone derives `PASS`, `VETO`, or `UNCERTAIN` from those
subjudgments. Both role arms use exactly 36 calls (`3.0x`), share baseline and
fabrication receipts, cannot promote a baseline failure, and are scored only
after a new GPT-5.6/Gemini-3.1/Kimi K3 reference exists.

The pre-reference run completed 72 calls and 118,793 tokens. Single and budget-
matched monolithic arms retained 23/24 receipts. Naive replication retained ten
and vetoed fourteen with complete receipts. Structured defer vetoed 22 and left
two unresolved after one semantic consistency failure. Every one of its 22
valid receipts classified the requested object as `EXPLICITLY_FIXED`, including
all private open-ambiguity constructions. This is a pre-label warning rather
than an accuracy claim, but it is sufficient to stop additional Provider runs:
the representation has collapsed toward universal rejection.

The completed GPT-5.6/Gemini-3.1/Kimi K3 panel yields a candidate reference of
11 usable and 13 unusable packets. Single and budget-matched monolithic arms
both score `0.500` accuracy, `0.923` false-usable rate, and `1.0` usable recall.
Naive replication improves accuracy to `0.708` and false-usable rate to `0.231`,
but recall falls to `0.636`; it fails the frozen false-usable, recall, and worst-
category gates. Structured defer reaches zero false-usable output only by
reducing usable recall to zero, with `0.542` accuracy and two unresolved packets.
Current state: `STRUCTURED_REPLICATION_GATE_FAILED`. This is retained as an
anti-additive representation boundary; neither arm has authority.

### Execution-warranted veto v0.5.1

The next experiment upgrades the object from another semantic classifier to
the negative-evidence burden required for Runtime to execute a Provider-backed
veto. A Provider still owns the semantic assessment and may return `PASS`,
`VETO`, or `UNCERTAIN`. A veto also carries one strongest warrant. Runtime gives
execution authority only to an exact prompt-bound explicit fixation, a Provider-
judged invalid rival, or Provider-judged equivalent rivals. A claim that the
question is merely ineffective is recorded but cannot veto by itself. Runtime
does not replace the Provider's semantic judgment, and no specialist may promote
a monolithic baseline failure.

The fresh holdout contains 24 new packets and exposes no predecessor examples or
labels. Four frozen arms compare one monolithic pass, a three-pass monolithic
control, the original three-role naive veto, and an equal-cost warranted veto.
Both role arms use 36 attributed calls (`3.0x`). Admission requires at most
`0.20` false-usable rate, at least `0.85` usable recall, at most `0.10` unresolved
output, at least `0.15` accuracy gain over budget-matched monolithic, at least
`0.04` accuracy gain and `0.15` recall gain over naive veto, no false-usable
increase over naive veto, and bounded category risk.

The first v0.5 pre-reference run is preserved as a construction failure. A
rewritten shared fabrication control produced 17 uncertain judgments and made
the admission gate unreachable before any reference labels existed. The v0.5.1
recovery restored the frozen v0.4 monolithic, legacy-live, and fabrication
control prompts, changed the contract hash, and reran all 72 calls without using
the failed candidate run as evidence. It consumed 123,594 tokens. One complete
fabrication batch failed semantic shape validation and is preserved, leaving two
unresolved packets in each role arm. Naive and warranted veto each produce 11
usable, 11 unusable, and two unresolved outputs, but disagree on six packet
decisions. All other lanes completed 12/12 batches. Current state:
`AWAITING_MODEL_ANNOTATIONS`.

The completed GPT-5.6/Gemini-3.1/Kimi K3 panel yields a candidate reference of
12 usable and 12 unusable packets. Single and budget-matched monolithic both
score `0.542` accuracy, `0.917` false-usable rate, and `1.0` usable recall.
Naive replication improves accuracy to `0.708` and false-usable rate to `0.250`,
but recall falls to `0.667`. Warranted veto falls back to `0.542` accuracy,
raises false-usable rate to `0.417`, and lowers recall to `0.500`, with the same
two unresolved packets and greater token cost than naive replication. Of the six
decisions changed by warrant execution, one corrects naive output and five cause
new errors: three restore reference-unusable packets and two reject reference-
usable packets. Current state: `VETO_WARRANT_GATE_FAILED`. The warrant classes
do not carry stable execution value, so no selection, retention, coordination,
or production authority is granted.

### Formal clarification regret v0.6

The next object upgrade stops treating semantic veto labels as execution value.
It evaluates the action itself under a committed formal utility contract: a
correct direct object choice receives `1.0`, a wrong choice receives `0.0`, and
asking costs `0.25` before revealing the private intended object. Twenty fresh
cases contain eight balanced open-intent trials and twelve explicit, equivalent,
or fabricated-rival controls. The private oracle and category bindings are hash-
committed before prediction and are unavailable to every Provider lane. This is
a synthetic/formal audit and makes no real-world ground-truth claim.

Four isolated Provider lanes compare a holistic direct action with one and three
regret-estimation passes. Regret Providers do not choose the final action. They
propose a preferred direct answer and estimate its probability of targeting the
wrong object; Runtime asks only when estimated expected loss exceeds the frozen
clarification cost. The pilot completed 40 calls and 53,598 tokens without a
failed receipt. Direct policy asks on 14/20 cases and reaches `0.775` mean utility,
slightly above the `0.750` always-ask control but below the `0.900` operational
oracle, with `0.50` unnecessary-question rate. Both single and three-pass regret
ask on all 20 cases and score exactly like always-ask. Every regret pass emits
`0.50` wrong-object probability for every case, including all explicit,
equivalent, and fabricated controls. Three passes consume 41,586 attributed
tokens without changing one action.

Current state: `CLARIFICATION_REGRET_GATE_FAILED`. Provider self-estimated scalar
probability collapses candidate multiplicity into a uniform uncertainty score
and carries no calibrated action value. The next candidate object is historical
action credit learned from held-out correction/harm outcomes and structural
fingerprints, not another self-reported confidence or probability field. No
selection, retention, coordination, or production authority is granted.

### Clarification action credit v0.7

This experiment replaces self-reported confidence with outcome-calibrated
action credit. The frozen v0.6 corpus is used only as calibration history. A
single Provider assigns an outcome-blind structural fingerprint and a preferred
direct answer; Runtime then constructs an experiment-only Beta(1,1) ledger from
the hidden historical outcomes. Direct action is permitted only when a
fingerprint has at least two observations and its posterior direct-success rate
strictly exceeds the fixed `0.75` utility of asking. Validation uses 20 new,
hash-committed formal cases. Their outcomes cannot update the current ledger.

The calibration run used 10 calls and 13,467 tokens with no failed receipt, but
the fingerprint representation did not separate prompt-fixed controls. It
assigned 14/20 cases to `OPEN_RIVALS`, four to `EQUIVALENT_RIVALS`, two to
`UNSUPPORTED_RIVAL`, and none to `PROMPT_FIXED`. Consequently, every learned
direct-success posterior was at most the asking utility. On the fresh holdout,
the ledger policy asked on all 20 cases and reached `0.750` mean utility. The
equal-call holistic direct policy asked on 19 cases and reached `0.7625`; its
only direct answer was correct. Ledger policy therefore has zero wrong answers
and zero missed clarifications, but `1.0` unnecessary-question rate, `0.750`
control utility, and negative utility gain relative to direct policy. Four of
eight frozen gates pass.

Current state: `ACTION_CREDIT_TRANSFER_GATE_FAILED`. Historical outcomes are a
better execution object than scalar self-confidence, but credit cannot recover
information discarded by a collapsed structural fingerprint. The next useful
object is not a larger ledger or another threshold adjustment. It is an
outcome-blind, contrastive representation that can distinguish prompt-fixed
controls from genuinely open rivals before action credit is estimated. This
negative result has no Core baseline, selection, retention, coordination, or
production authority.

### Contrastive requested-object representation v0.8

This round isolates the representation problem before reconnecting any action
policy. Twenty-four new formal cases form twelve matched pairs. Within each
pair, facts and candidate objects are identical and only the requested-output
wording changes: one request remains open and the other explicitly selects A or
B. Fixed direction and pair position are balanced. Both isolated lanes receive
the same pair and call budget. The old lane directly assigns an ambiguity
category; the candidate lane must quote the requested object, identify explicit
selection, and let Runtime derive `OPEN_RIVALS` or `PROMPT_FIXED`. Corpus,
oracle, and eight admission gates are hash-frozen before Provider execution.

The run completed 24 calls and 28,505 tokens with no failed receipt. Direct
category fingerprinting reaches `0.708` accuracy, `0.583` fixed recall, `0.833`
open recall, and `0.417` matched-pair flip rate. Evidence-bound request
selection reaches `0.875` accuracy at slightly lower token cost, a `+0.167`
gain. It recovers all twelve prompt-fixed cases and selects the correct A/B
direction in all twelve. It also binds every requested-object quote to the
public prompt. This directly repairs the v0.7 failure to see prompt fixation.

The candidate nevertheless fails the frozen gate. Three formally open cases
are emitted as `UNCERTAIN`, leaving `0.750` open recall, `0.750` pair-flip rate,
and `0.125` unresolved output. Close reading reveals a sharper phenomenon: all
three explanations explicitly say that the prompt does not select either
candidate, yet encode that object state as assessor uncertainty instead of
`NEITHER`. A post-score, non-admissible shadow mapping of those three tokens to
no explicit selection would score `1.0`, but it does not alter the registered
result. The failure is therefore informative evidence of an ontology collision:
openness belongs to the task object, while uncertainty belongs to the judging
process, and they should not share one enum.

Current state: `CONTRASTIVE_REPRESENTATION_GATE_FAILED`. The requested-object
coordinate is materially better than direct ambiguity categorization on this
holdout, but matched-pair visibility remains a live alternative explanation and
downstream action utility is untested. The next object is a two-axis receipt:
object selection (`A`, `B`, or no explicit selection) separated from assessment
status (`RESOLVED` or `UNRESOLVED`), followed by an ablation of pair visibility.
Action credit remains disconnected. The machine-readable and human-readable
post-experiment analyses are emitted under
`outputs/clarification_contrastive_v0_8`; they cannot change gates or authority.

### Two-axis selection and pair-visibility ablation v0.9

This round separates task-object state from assessor state. The Provider must
always record object selection as `CANDIDATE_A`, `CANDIDATE_B`, or `NONE`, while
independently recording whether that judgment is `RESOLVED` or `UNRESOLVED`.
`NONE + RESOLVED` is the intended representation of a genuinely open request.
The fresh 24-case corpus again contains twelve minimal pairs, but three equal-
call lanes distinguish representation from contextual scaffolding: direct
category fingerprinting sees shuffled unrelated cases, paired two-axis sees
true counterparts, and the admission arm sees the same two-axis schema with
true counterparts shuffled apart. Each arm uses twelve calls.

The frozen run completed 36 calls and 44,439 tokens. One direct-category batch
failed semantic validation; both two-axis lanes completed without failed or
unresolved receipts. Direct category fingerprinting scores `0.542` accuracy,
with only `0.167` fixed recall. Paired two-axis reaches `0.958` accuracy and
`0.917` matched-pair success. The operational shuffled arm reaches `0.875`, a
`+0.333` gain over direct categorization, with `1.0` fixed recall, `1.0` A/B
direction accuracy, zero unresolved output, and only `0.083` paired-visibility
advantage. The two-axis ontology therefore survives removal of most live
counterfactual scaffolding and eliminates the v0.8 `NONE/UNCERTAIN` collision.

It still fails the frozen accuracy, open-recall, and pair-flip gates. All three
shuffled errors are formally open requests promoted to candidate A: “laboratory
workload,” “service volume,” and “inspection activity.” Their receipts claim
that these generic phrases explicitly define the event-count candidate, even
though the prompt states no such definition. True-pair visibility corrects two
of the three; “service volume” remains over-fixed even with its counterpart.
This is a coherent over-commitment failure rather than random noise. The
Provider is promoting a natural default or semantic compatibility into explicit
prompt entailment. That default may still be useful evidence: “workload,”
“volume,” and “activity” pragmatically favor event counts even when they do not
formally fix them. The representation should preserve this weak preference
without granting it hard-constraint status.

Current state: `TWO_AXIS_REPRESENTATION_GATE_FAILED`. The state ontology is now
substantially better, but action credit remains disconnected. The next object is
an explicit-selection proof obligation with three separate coordinates:
explicit selection, pragmatic preference, and assessor status. A Provider-backed
warrant must prevent default compatibility from becoming hard fixation while
retaining it as decision evidence, and it must survive a fresh hard-generic
holdout without relying on matched pairs. The
scoring and result-analysis artifacts live under
`outputs/clarification_two_axis_v0_9` and carry no Core, selection, retention,
coordination, or production authority.

### Explicit-selection warrant v0.10

This experiment separates explicit selection, pragmatic preference, and
assessment status on 24 fresh, unpaired cases. Twelve requests name an object
explicitly; twelve use generic but pragmatically directional wording. A/B
directions are balanced within both constructions. The equal-call baseline uses
the v0.9 two-axis receipt. The candidate adds warrant types for exact mention,
explicit definition, explicit operation, default compatibility, and no explicit
warrant. Runtime grants hard fixation only to the first three while preserving
soft preference as receipt evidence. The corpus does not expose its generic
terms, labels, or construction menu in the Provider objective.

The run completed 24 calls and 31,832 tokens. All candidate receipts are valid,
but seven of twelve baseline batches fail semantic validation, mostly because a
`NONE` selection carries a non-`NONE` decisive quote. The baseline therefore
scores only `0.208`; the registered `+0.583` candidate gain is confounded and
cannot support a comparative claim. The candidate itself scores `0.792`, with
`1.0` explicit recall, `1.0` fixed-direction accuracy, and `0.923` hard-warrant
precision. It identifies twelve exact mentions, eleven default-compatibility
warrants, and one explicit definition. Four default cases are marked unresolved,
leaving pragmatic-open recall and constructed preference alignment at `0.583`.

Close reading exposes three distinct boundaries. First, assessment status again
absorbs object openness: all four unresolved receipts correctly record explicit
selection as `NONE` and provide a pragmatic direction, but call the assessment
unresolved because the task remains ambiguous. Second, the only formal false
hard fixation is “membership base” to distinct member count, a judgment that may
reflect genuine semantic entailment rather than Provider error. Third, all six
author-constructed A-leaning defaults align with the Provider, while only one of
six B-leaning defaults does. Terms such as reach, coverage, footprint,
participation, and adoption do not provide a trustworthy synthetic preference
oracle merely because the corpus author assigned one.

Current state: `EXPLICIT_SELECTION_WARRANT_GATE_FAILED`. The experiment supports
separating constraint strength from semantic preference, but it does not yet
validate the preference labels or action value. Further prompt tuning on these
24 constructions is prohibited. The next evidence object is an identity-blind
GPT-5.6/Gemini-3.1 panel for explicit entailment and pragmatic preference, with
Kimi K3 adjudicating only disagreements. Assessment completion must also be
renamed or redefined so an open task can still carry a completed semantic
assessment. Action credit remains disconnected, and no Core, selection,
retention, coordination, or production authority is granted.

The independent panel infrastructure is now frozen under panel ID
`warrant-panel-13d6250249256e7a`. GPT-5.6 and Gemini 3.1 receive lane-specific
aliases and orderings for 24 items and three criteria: explicit selection,
pragmatic preference, and assessment completeness. Their pack hashes are
`dff4b63deb2f57f0cab9f79f2a6bdab2117dd8bc3238e44761339927cccae959`
and `cc34ee71d9254ef596fa0498ca1c9c5d42d49179e40507f2a24e0cd0598f096e`.
Validated responses will be reduced to identity-blind disagreement cells for
Kimi K3; agreements bypass adjudication. Response validators, K3 pack creation,
bundle ingestion, and candidate-only reference synthesis are implemented and
tested. The initial panel state was `AWAITING_MODEL_ANNOTATIONS`.

The returned GPT-5.6 and Gemini 3.1 responses pass all identity, pack-hash,
schema, enum, and complete-coverage checks. They agree on 67/72 criterion cells.
All 24 pragmatic-preference cells and all 24 assessment-completeness cells
agree; every assessment is `COMPLETE`. On the twelve pragmatic-open items, the
agreed preference direction matches all twelve constructed proxies, while all
twelve explicitly fixed directions also agree. This shifts the prior diagnosis:
the DeepSeek preference mismatch is more likely a Provider error orientation
than a failed preference proxy, and its `UNRESOLVED` outputs misuse assessment
status to encode task openness.

All five disagreements concern `EXPLICIT_SELECTION`: support workload, factory
throughput, membership base, transaction volume, and warehouse volume. In each
case, both annotators agree on the pragmatic direction but disagree on whether
the phrase semantically entails that candidate or only favors it. These five
cells are frozen in identity-blind Kimi K3 pack hash
`46f3d3804b13dafea1b184da009763d5b21a0e81a8da5e1203770f80c39f5124`.
The panel then entered `AWAITING_KIMI_K3_ADJUDICATION`; no final reference or
Runtime adaptation was permitted before adjudication.

The validated Kimi K3 response resolves all five disagreements toward semantic
selection rather than `NONE`. The complete 72-cell candidate reference therefore
contains seventeen prompt-fixed and seven open objects, twelve A and twelve B
pragmatic preferences, and twenty-four `COMPLETE` assessments. This revises the
construction boundary without changing the frozen experiment: author-assigned
explicit-selection labels align with the panel on `0.792` of cases, while the
constructed pragmatic preferences align on all cases. “Membership base” is no
longer a false hard fixation under the model-panel reference.

The diagnostic-only panel recalibration rejects warrant transfer. DeepSeek
reaches `0.833` explicit-selection accuracy, `0.792` pragmatic-preference
accuracy, `0.833` assessment-completeness accuracy, and `0.750` final Runtime
category accuracy. Its hard-warrant precision is `1.0`, but panel-fixed recall
is only `0.765`; panel-open recall is `0.714`, with `0.167` unresolved output.
The error structure is now clear: issued hard warrants are precise, semantic-
entailment selection is under-recalled, preference errors remain directional,
and open tasks are still misencoded as incomplete assessments. Current state:
`WARRANT_PANEL_RECALIBRATION_DIAGNOSTIC_ONLY`; transfer recommendation:
`REJECT_WARRANT_TRANSFER`. The next admissible experiment must use fresh lexical
constructions, rename assessment completion, and test semantic-entailment recall
without lowering hard-warrant precision before action credit is reconnected.

### Four-class semantic-basis transfer v0.11

This round freezes a new, unpaired 24-case corpus before Provider execution.
The cases are balanced across four construction classes: exact lexical
selection, compositional entailment, pragmatic default, and no preference.
The v0.10 warrant receipt is retained as an equal-call baseline. The candidate
must instead emit the selected object, one of the four semantic bases, a
separate pragmatic preference, and an explicit assessment-completeness flag.
Runtime grants hard fixation only to lexical or compositional entailment;
pragmatic defaults remain soft evidence, and a complete `NONE` assessment is a
valid open-task result. Construction labels are diagnostic proxies only and
cannot become a semantic reference or action authority.

The DeepSeek run completed 24 calls and 36,245 tokens with no failed batch in
either lane. This removes the v0.10 comparative confound. Against the frozen
construction proxies, the old warrant baseline reaches `0.375` category
accuracy and emits `UNCERTAIN` on `0.583` of cases. The four-class candidate
reaches `0.708` category and basis accuracy, a `+0.333` equal-call gain, with
`1.0` assessment completeness and `0.917` fixed-direction accuracy. It therefore
repairs the task-openness/assessment-incompleteness collision and recovers most
compositional selections.

The candidate also exposes a new, systematic failure. It never emits
`PRAGMATIC_DEFAULT`; all six pragmatic-default constructions are promoted to
`COMPOSITIONAL_ENTAILMENT`, yielding only `0.647` hard-selection precision and
`0.500` open recall. One constructed compositional case is instead demoted to
`NO_PREFERENCE`. Its pragmatic-preference alignment is `0.333`, partly because
it records `NONE` on many fixed cases even when the selected object is also the
natural answer. This is not yet evidence that every construction label is
correct. It is evidence that the receipt now localizes the disputed boundary:
semantic entailment versus contextual default, rather than hiding the error in
an undifferentiated ambiguity category.

Current state: `AWAITING_SEMANTIC_WARRANT_MODEL_PANEL`. The pre-panel analysis
is frozen under `outputs/clarification_semantic_basis_v0_11`. An independent
96-cell panel now covers selected object, selection basis, pragmatic preference,
and assessment completeness. GPT-5.6 pack hash:
`862a2a877e194af010f22aa233643ab8abf474e96b3f73d7492d73bcd1a630b9`;
Gemini-3.1 pack hash:
`2667fd7bdef3e3592eef9770c5b3ef11c4abb35f24bc4660333795a6e67a3f02`;
panel ID: `semantic-basis-panel-767188c3e0ad7ad0`. Both packs withhold the
construction classes, DeepSeek outputs, and prior scores. Kimi K3 adjudication
will be generated only after independent responses are validated. Action
credit, selection, retention, coordination, and production authority remain
disconnected.

The returned GPT-5.6 and Gemini-3.1 responses pass identity, pack-hash, schema,
enum, and complete-coverage validation. They agree on 90/96 cells. Selected
object, pragmatic preference, and assessment completeness are each 24/24
agreements: six A, six B, and twelve NONE selected objects; nine A, nine B, and
six NONE preferences; and twenty-four COMPLETE assessments. Both annotators
therefore reject DeepSeek's hard selection on all six generic pragmatic cases.
The remaining disagreements are exclusively `SELECTION_BASIS`: GPT-5.6 calls
all six `PRAGMATIC_DEFAULT`, while Gemini-3.1 calls them `NO_PREFERENCE` despite
assigning the same directional A/B preferences. This creates six retained
cross-axis coherence warnings in the Gemini lane rather than an automatic
rewrite. The anonymous Kimi-K3 pack contains only those six cells, has hash
`1b8074d13e659ecf3fb2c893647ebc7b9b41807d68f20cfd5fd693fa09c0c421`,
and sets the panel state to `AWAITING_KIMI_K3_ADJUDICATION`.

The returned Kimi-K3 response passes exact bundle-member selection, panel and
pack identity, six-decision coverage, enum, position binding, confidence, and
blinding-attestation checks. K3 selects three `PRAGMATIC_DEFAULT` positions,
one `NO_PREFERENCE` position, and independently introduces two
`COMPOSITIONAL_ENTAILMENT` decisions. Criterion-local validation succeeds, but
the assembled receipt fails the new cross-axis coherence gate: the two
compositional labels coexist with the already agreed `SELECTED_OBJECT=NONE`,
and the no-preference label coexists with an agreed directional preference.
The three affected constructions are customer reach, processing volume, and
community participation. No axis is silently overwritten.

The final model-panel reference is therefore frozen as
`SEMANTIC_BASIS_MODEL_PANEL_REFERENCE_COHERENCE_FAILED`, artifact hash
`e5df9546eceb53d8117c6fe4ca724b322dda5a5e373a3e63facbb62a6644122c`.
Diagnostic recalibration gives DeepSeek `0.708` selected-object and Runtime-
category accuracy, `0.792` basis accuracy, `0.333` pragmatic-preference
accuracy, `1.0` completeness accuracy, and `0.647` hard-selection precision.
The basis score cannot support transfer because two credited basis labels are
globally inconsistent. Transfer recommendation remains
`REJECT_SEMANTIC_BASIS_TRANSFER`. The next evidence object is joint cross-axis
coherence resolution, not another independent per-cell vote.

### Joint cross-axis semantic coordinator v0.12

This stage tests whether a coordinator can resolve the three real cross-axis
conflicts left by v0.11. The identity-blind surface contains each complete
semantic tuple, anonymous basis positions, the local adjudication outcome, and
three locked axes with 2/2 independent agreement. Construction labels,
DeepSeek predictions, model identities, and prior scores remain withheld. The
Provider must return a complete tuple and explicitly choose preservation,
consensus reopening, ontology conflict, or unresolved. Runtime independently
checks semantic coherence, changed consensus axes, preserve/reopen declarations,
and authority boundaries.

Fixture tests close coherent preservation, explicit reopening, incoherent
proposal rejection, and tamper rejection. The live DeepSeek coordinator then
uses one call and 3,418 tokens to return all three decisions without schema
failure. Runtime accepts zero repairs and classifies all three as
`INVALID_PRESERVATION_PROPOSAL`. Two proposed tuples are semantically coherent
but governance-invalid: they change the unanimously selected object, correctly
list that axis as reopened, yet label the overall disposition as
`PRESERVE_CONSENSUS_REPAIR`. The third preserves all consensus axes but leaves
`NO_PREFERENCE` paired with a directional preference. The coordinator follows
the local K3 basis outcome on all three cases instead of integrating its lower
support strength with the unanimous axes.

This negative result validates the Runtime gate and exposes two separate
bottlenecks. First, the Provider does not yet apply evidence-priority rules
reliably. Second, the contract redundantly asks it to encode governance intent
both as an overall disposition and as per-axis preserve/reopen lists, creating
a preventable mismatch. Current state:
`OBSERVED_CONFLICT_REPAIR_DIAGNOSTIC_ONLY`; accepted repair count: zero. The
same three cases will not be rerun. The next experiment should mechanically
derive overall governance state from per-axis actions and use a fresh holdout
that varies which axis is wrong, including cases where reopening unanimous
consensus is genuinely correct. Action credit and all production authority
remain disconnected.

### Fresh de-redundant joint coordination v0.13

This round removes the redundant overall disposition and asks the Provider only
for per-axis `PRESERVE/REOPEN` actions, a local-basis `PRESERVE/REVISE` action,
and the complete final tuple. Runtime derives governance state mechanically
from actual value changes. The fresh 24-case holdout rotates the target among
selection basis, selected object, pragmatic preference, and assessment
completeness. Each six-case group contains three preserve and three reopen or
revise constructions. The Provider cannot see target axes, actions, or
construction truth. A preserve-all strategy is frozen as the comparator and
reaches `0.500` tuple and target-action accuracy.

The live DeepSeek run completes 24/24 receipts in six calls and 19,220 tokens
with no failed batch. Contract ergonomics improve materially: action-declaration
validity reaches `0.958`, and false reopening is only `0.016`. Semantic
coordination does not improve with it. Construction-only tuple accuracy is
`0.542`, only `+0.042` above preserve-all; coherence is `0.667`, selected-object
accuracy `0.833`, basis accuracy `0.875`, pragmatic-preference accuracy `0.875`,
and completeness accuracy `0.917`. Runtime records fourteen coherent
preservations, eight incoherent tuples, one invalid action declaration, and
only one valid consensus reopening.

The asymmetry is decisive: target-preserve accuracy is `1.000`, while target
reopen-or-revise accuracy is `0.083`; consensus-axis reopen recall is `0.111`.
Removing the redundant governance enum therefore fixes most expression errors
but reveals strong consensus anchoring. The coordinator copies locked axes or
the local basis even when that combination violates its own tuple invariants.
Current state: `AWAITING_JOINT_COORDINATOR_MODEL_PANEL`; all construction scores
remain pre-panel diagnostics and transfer is not permitted.

The independent semantic panel is frozen under ID
`joint-fresh-panel-ec64a31acb41dbf0`. It sees only raw prompts and candidate
objects, then labels selected object, selection basis, pragmatic preference,
and assessment completeness. Locked consensus, local basis, DeepSeek output,
construction labels, and prior scores are withheld. GPT-5.6 pack hash:
`f079084d607d58512dc743e3779a57d91af0aa27ba2b882931f1005ee86e8786`;
Gemini-3.1 pack hash:
`07cfff26db29370f4c2aca107b3811396b9ab6943d5833f0e1a542be5760e0f4`.
Panel semantic tuples will be converted to governance actions mechanically;
annotators are not asked to restate Runtime policy.

The returned GPT-5.6 and Gemini-3.1 responses pass identity, pack-hash, schema,
enum, and 24-item coverage validation. They agree on 80/96 cells: 21/24
selected objects, 13/24 selection bases, 23/24 pragmatic preferences, and
23/24 completeness labels. Eleven of sixteen disputes concern selection basis;
eight are GPT-5.6 `PRAGMATIC_DEFAULT` versus Gemini-3.1 `NO_PREFERENCE`.
Support workload and freight volume additionally split between GPT hard
selection and Gemini `NONE/NO_PREFERENCE`. The opaque-candidate control disputes
all four axes, directly exposing complete-NONE versus genuine-incompleteness.

Tuple coherence is role-asymmetric. GPT-5.6 produces zero cross-axis-invalid
tuples. Gemini-3.1 produces ten `NO_PREFERENCE_AXIS_MISMATCH` tuples by pairing
`NO_PREFERENCE` with a directional pragmatic preference, replicating the same
orientation seen in v0.11. This does not automatically make GPT correct: its
coherent workload and volume selections may still be semantic over-promotion.
The sixteen disputed cells are frozen in anonymous Kimi-K3 pack hash
`94910427940ec0fc2604a8e49c35345947dfe5653bd8dca3431def82c1fcb6b5`.
Current state: `AWAITING_KIMI_K3_ADJUDICATION`; post-adjudication tuple coherence
must pass before governance actions or coordinator recalibration are derived.

The returned Kimi-K3 response passes exact mixed-bundle member selection,
panel/pack identity, sixteen-decision coverage, position binding, confidence,
and blinding-attestation validation. The assembled 96-cell reference then fails
the mandatory tuple-coherence gate on five cases: three hard bases coexist with
`SELECTED_OBJECT=NONE`, and two `NO_PREFERENCE` bases coexist with directional
preferences. This independently reproduces the v0.11 result that criterion-
local adjudication can create a globally impossible cognitive object.

The coherence-failed panel reference nevertheless supports axis-level
diagnostics. It aligns with construction labels on `1.0` of preference and
completeness cells, `0.917` of selected objects, and only `0.708` of selection
bases. The panel revises support workload and freight volume from constructed
open objects to candidate A with compositional entailment. Against panel cells,
DeepSeek reaches `0.750` selected-object, `0.708` basis, `0.875` preference, and
`0.917` completeness accuracy. Full-tuple accuracy is `0.458`, or `0.526` on
the nineteen coherent reference tuples.

Most importantly, panel-derived governance actions confirm consensus anchoring:
of eleven consensus axes that should reopen, DeepSeek reopens one (`0.091`
recall), while preserving 60/61 axes that should remain fixed (`0.984`
specificity). Local-basis action accuracy is `0.750`. The final reference state
is `JOINT_FRESH_MODEL_PANEL_REFERENCE_COHERENCE_FAILED`, artifact hash
`444dedf76fe99262980427692b4bf8ca40d068cea5f1d1995a372919ebcf799d`;
transfer recommendation is `REJECT_JOINT_COORDINATOR_TRANSFER`. The next
adjudication unit must be a complete semantic tuple rather than another cell.

### Identity-blind joint-tuple repair v0.14

This round changes the adjudication object from an isolated criterion cell to
the complete four-axis semantic tuple. It carries forward only the five v0.13
references that failed the mechanical coherence gate. For each object, Kimi-K3
receives the raw prompt, both candidates, the current incoherent tuple, its
explicit violations, anonymous GPT/Gemini positions on all four criteria, and
the prior cell-level outcome where a dispute existed. Model identities,
construction labels, locked coordinator axes, DeepSeek outputs, and prior
scores remain withheld.

The response contract requires one complete coherent tuple per object and an
exact declaration of every changed criterion. Runtime rejects missing objects,
duplicate decisions, invalid states, residual cross-axis contradictions,
incorrect change declarations, lineage mismatch, identity leakage, and hash
tampering. A repaired reference preserves the previous tuple, repaired tuple,
changed criteria, rationale, confidence, source hashes, and authority boundary.
It remains candidate-only and cannot award action credit or alter production,
selection, or retention state.

The frozen public Kimi-K3 pack contains five objects and has hash
`7d1c434e12b3a8ee2ded97782105ceaffd099e1c7368a6c03e60a00200c21d7f`.
The returned mixed ZIP contains exactly one response matching repair version,
panel ID, and pack hash. All five full-tuple decisions pass binding, coverage,
exact-change, and coherence validation. Kimi-K3 changes only one criterion per
object: selected object in three cases and pragmatic preference in two. It
retains compositional entailment for processing volume, customer reach, and
audience reach, selecting the corresponding specific object; it retains
`NO_PREFERENCE` for community and learner participation, removing the
unsupported directional preference. Mean repair confidence is `0.580`.

The repaired reference has zero incoherent tuples and hash
`03f9d3a53bb7fa055f2a7bdc40dcb1eb4c2717ce39b01a8c3fdefc180618dec3`.
Recalibration makes the frozen DeepSeek coordinator look weaker, not stronger:
full-tuple accuracy falls from `0.458` to `0.417`, selected-object accuracy from
`0.750` to `0.625`, preference accuracy from `0.875` to `0.792`, consensus-
action accuracy from `0.847` to `0.778`, and reopen recall from `0.091` to
`0.063`. Preserve specificity remains high at `0.982`. The coherent reference
requires sixteen consensus-axis reopenings; DeepSeek performs one.

All five repairs also move away from their construction labels, reducing
construction alignment on selected object from `0.917` to `0.792` and on
preference from `1.000` to `0.917`. Construction labels were already declared
pre-panel diagnostics, so this is not a gate failure; it is evidence that future
holdouts should freeze coherent multi-Provider semantic references before
coordinator evaluation. Current state:
`JOINT_TUPLE_REFERENCE_COHERENT_DIAGNOSTIC_ONLY`; transfer remains rejected.
Deterministic generation, exact mixed-bundle ingest, full-tuple closure,
response tamper rejection, residual-incoherence rejection, repaired-reference
lineage, and analysis lineage are covered. The complete local experiment suite
passes 236 tests.

### Reference-first fresh full-tuple panel v0.15

This stage reverses the previous evaluation order. A new 24-object holdout is
frozen before any candidate coordinator run. It covers temporal scope,
gross-versus-net measures, rate denominators, entity-versus-event measures,
stock-versus-flow measures, and population scope, with four objects per family.
No target axis, target action, semantic label, construction truth, or hidden
answer exists in the corpus. Private provenance contains only case identity,
object family, and public-item hashes.

GPT-5.6 and Gemini-3.1 receive independently randomized, identity-blind packs.
Each annotator must return a globally coherent four-axis tuple for every object;
Runtime rejects incoherent tuples before panel comparison. Agreement is defined
over the entire tuple. If any criterion differs, the later Kimi-K3 pack exposes
two anonymous complete positions and requires one complete coherent decision.
There is no cell-level adjudication or tuple-splicing path.

The frozen corpus hash is
`02df71dc73378b0e68d05110ee3630a0e2260483999b2d2903e5c69d67b0f5d4`;
panel ID is `reference-first-panel-ad4d5f597dcc3ffa`. GPT-5.6 pack hash:
`b9cc4e37e6c8b4c538bd6f5daa9d6431140e663192d6b4c3c28d6740b1466198`;
Gemini-3.1 pack hash:
`19e89fb4d33fcc33b925eb5e89ba236acb72066e6d7a865467dff9fb88d0850b`.
The frozen phase order is corpus, coherent dual annotation, whole-object K3
adjudication, coherent reference freeze, local role collection, DeepSeek
coordination, and scoring without reference revision.

Both returned annotation files pass panel identity, pack hash, exact 24-object
coverage, enum, rationale, confidence, blinding, and per-object full-tuple
coherence validation. GPT-5.6 and Gemini-3.1 agree on 15/24 complete tuples.
Axis agreement is 21/24 selected objects, 15/24 selection bases, 22/24
pragmatic preferences, and 23/24 completeness judgments. Nine objects require
adjudication: five differ on one axis, three on two axes, and one on all four.

Five of the nine disagreements are only the boundary between `LEXICAL_EXACT`
and `COMPOSITIONAL_ENTAILMENT`; object, preference, and completeness remain
identical. Four change a substantive semantic commitment. These include two
selected-object disputes, one open-object preference dispute, and one
recognized-revenue case where complete `NONE/NO_PREFERENCE` competes with an
incomplete all-`UNCERTAIN` tuple. All nine remain in the whole-object K3 pack
because basis strength can still affect downstream governance even when the
selected object is unchanged.

The anonymous Kimi-K3 pack has hash
`c23b8821f7c9a6296e2084da6d9ed465786ebd146e7693435506af5d3228e759`.
The returned mixed ZIP contains one exact version/panel/pack match. All nine
Kimi-K3 decisions select a displayed anonymous full position and pass position
binding plus coherence validation; no criterion splicing or independent tuple
construction occurs. Mean confidence is `0.622`. Private lineage shows four
selected positions originated in the GPT lane and five in the Gemini lane. For
the five hard-basis granularity disputes, Kimi-K3 selects
`COMPOSITIONAL_ENTAILMENT` three times and `LEXICAL_EXACT` twice.

The frozen 24-object reference has hash
`1984d1fe8bd9524d1e6c4ad3f8bc2a31448f91cf38e68ddec0f2aa167d02f887`
and zero cross-axis inconsistencies. Fifteen tuples come directly from
dual-model agreement and nine from whole-object adjudication. Its selected-
object distribution is fourteen A, five B, and five open; basis distribution
is seventeen compositional, two lexical, four no-preference, and one pragmatic
default. All 24 assessments are `COMPLETE`. The latter is a measured limitation:
this holdout can evaluate object, basis, and preference coordination, but not
complete-versus-incomplete discrimination. The frozen corpus will not be
modified to compensate.

Current state: `REFERENCE_FROZEN_AWAITING_LOCAL_ROLE_OUTPUTS`. Local specialist
collection is now permitted, but DeepSeek coordinator execution remains
disabled until role receipts are frozen. Reference revision is prohibited.

### Rotated local specialist roles v0.15

The frozen public surface is assigned to three isolated roles:
`OBJECT_GROUNDING`, `PRAGMATIC_DEFAULT`, and `ASSESSMENT_SKEPTIC`. Qwen 1.5B,
Gemma 2B, and Llama 1B rotate through a Latin assignment so every model handles
each role eight times and every object receives all three roles from different
models. Provider inputs contain the public object and role contract only; the
reference, reference hash, peer outputs, and coordinator output are absent.

The first four-object structured contract fails completely: 18/18 batches are
rejected and no role decision becomes a receipt. The models often echo schema
or input fields, omit required nested fields, use categorical rather than
numeric confidence, or produce semantically inconsistent object/basis pairs.
CUDA inference itself remains healthy. This failed attempt consumes 21 Provider
calls, 6,547 input tokens, and 2,403 output tokens and remains in Cognitive Work
accounting.

One bounded recovery compiles the same assignments into one-object, one-role,
flat JSON tasks. No failed semantic payload is reused and the reference remains
hidden. Strict structural coverage improves to 34/72. Qwen succeeds on 23/24
flat tasks: 8/8 skeptic, 7/8 object grounding, and 8/8 pragmatic default. Gemma
succeeds on 11/24: 1/8 skeptic, 2/8 object grounding, and 8/8 pragmatic default.
Llama succeeds on 0/24. This establishes model-and-role-specific protocol
reliability rather than a generic local-model capability.

Semantic scores are reported only on structurally valid receipts and are
therefore selection-biased. Pragmatic preference reaches 8/16 overall: Qwen
5/8 and Gemma 3/8. Object-plus-basis reaches 2/9: Qwen 1/7 and Gemma 1/2. Qwen
basis alone reaches 4/7 but selected object only 1/7, showing that local basis
labels do not reliably bind to the correct object. The skeptic role reaches
0/9 because valid local receipts systematically mark cases incomplete while
the frozen reference marks every case complete; the holdout's completeness
base rate also prevents a balanced capability estimate.

Total work across the failed contract and bounded recovery is 116 Provider
calls, 43,720 input tokens, and 12,155 output tokens. The 34 accepted
assignment-level receipts cost about 1,643 tokens each. Flat recovery proves
that contract compilation matters, but coverage and semantic quality remain
too weak for coordination. Prompt-only recovery is now prohibited. Current
state: `LOCAL_SPECIALIST_PROTOCOL_BOTTLENECK_CONFIRMED`; DeepSeek coordinator
execution remains blocked. The next admissible experiment is a grammar-backed
or constrained-decoding local role adapter calibration, not another prompt
rewrite.

### Cognitive action and routed roles v0.16

The v0.16 window separates a stable canonical cognitive-action protocol from
model-specific Harness grammars. Runtime keeps object, evidence, conflict,
state, replay, and final-candidate authority. Providers choose semantic
actions; the Harness owns syntax and mechanically lifts each choice into a
hashed action receipt. This experiment remains outside CoreSlim.

Three adapter representations are preserved rather than reporting only the
best one. Anonymous finite calls obtain 72/72 structurally valid receipts and
reduce generated-output overhead, but arbitrary code binding fails semantic
viability. Context-calibrated natural-description likelihood also obtains
72/72 receipts but behaves as continuation scoring rather than classification.
The final staged adapter uses short semantic labels, null-context subtraction,
and A/B orientation reversal. Its pooled object accuracy remains weak, while a
calibration-selected one-to-one route reaches 0.625 for Gemma object grounding,
0.500 for Llama pragmatic default, and 1.000 for Qwen completeness assessment.
The completeness score remains caveated because the calibration reference is
all `COMPLETE`.

A new 24-object, six-family holdout is frozen before inference with hash
`31be0a69984c993cffd239755fa09d8d893ef668a5baf3b0383d6db07a4da5d5`.
The routed local roles produce 72/72 canonical receipts without labels. The
skeptic emits `COMPLETE` on all 24 objects, including deliberately
underspecified surfaces, which is retained as a possible transfer failure.

DeepSeek R1 32B then runs two counterbalanced blind arms on the same public
surface. Both arms cover 24/24 objects, but their full tuples differ on 21/24.
The role-informed coordinator matches local receipts on 21/24 object-plus-basis
judgments, 19/24 pragmatic preferences, and 24/24 completeness judgments,
showing that it consumes role evidence. This is influence, not demonstrated
gain. The external GPT-5.6 and Gemini 3.1 panel plus Kimi K3 adjudication remains
required before correctness, collective Cbit gain, or retention can be
claimed. Current state: `BLIND_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL`.

The complete local experiment suite now passes 267 tests. The v0.16 manifest,
hash inventory, replay pointer, rollback pointer, annotation pack, and full
post-experiment analysis are in
`outputs/cognitive_action_overnight_v0_16`.

The independent GPT-5.6 and Gemini 3.1 responses both pass panel, lane, pack,
coverage, blinding, enum, confidence, rationale, and full-tuple coherence
validation. They agree on 11/24 complete tuples. Selected object, pragmatic
preference, and completeness each agree on 19/24; selection basis agrees on
11/24. Thirteen objects require whole-object Kimi K3 adjudication: eight are
basis-only disputes and five differ on all four axes. The anonymous K3 pack
contains no local-role, DeepSeek-arm, annotator-identity, object-family, or
construction context. Current external-panel state:
`AWAITING_KIMI_K3_FULL_TUPLE_ADJUDICATION`.

The exact cognitive-action member in the mixed Kimi bundle passes panel, pack,
13/13 coverage, anonymous-position binding, and full-tuple coherence checks.
The frozen external model-panel candidate reference contains 24 coherent
objects and is never promoted as human gold. Final scoring gives both the
single-model baseline and role-informed coordinator 57/96 correct semantic
cells. Coordination repairs 14 baseline errors and introduces 14 new errors.
Full-tuple correctness rises from 1/24 to 3/24, but the collective path consumes
6.190 times the accounted tokens. The anti-additive gate therefore returns
`REJECT`; neither baseline promotion nor retention write is allowed. Current
state: `EXTERNAL_EVALUATION_COMPLETE_NO_BASELINE_PROMOTION`. The next admissible
test is a fresh axis-specific credibility-routing holdout.

### Axis-specific credibility routing v0.17

The v0.17 experiment freezes the rejected v0.16 external evaluation as
calibration evidence and tests a narrower organizational hypothesis on 24 new
unlabeled objects: source credibility may transfer by semantic axis even when
an unweighted coordinator has zero net cell gain. The preregistered route uses
the single-model baseline for selected object, an independent contrastive
basis critic for selection basis, the role-informed coordinator for pragmatic
preference, and the local skeptic for descriptive completeness. Completeness
is excluded from the promotion gate because the v0.16 reference was
label-degenerate.

The fresh corpus hash is
`b7ebd12e63ded7de03a4bc1b1617a4c330a237fe1a0e0e14bf7a6cccb1b89be9`.
Local models produce 72/72 canonical role receipts. DeepSeek covers 24/24
baseline objects and 23/24 coordinator objects. On the remaining object it
twice returns the same incoherent tuple, selecting candidate A while declaring
`PRAGMATIC_DEFAULT`; Runtime rejects both attempts and preserves their cost.
The routed arm therefore freezes at 23/24, above the preregistered 95 percent
continuation gate but not full coverage.

Twenty basis decisions use the focused Provider critic and three open-object
bases follow mechanically from frozen object and preference states. Baseline
and coordinator disagree on 11 selected objects, 21 bases, and 12 preferences.
The coordinator creates 12 directional preferences where baseline creates one,
but also shifts strongly toward candidate B. The focused basis critic labels
all 20 provider-assessed hard selections `LEXICAL_EXACT`, exposing a possible
new basis-label collapse that must be judged against the external reference.
The routed path accounts for 178,639 tokens versus 22,757 for baseline, a ratio
of 7.850, including both rejected invocations. These are structural and cost
observations only. GPT-5.6 and Gemini 3.1 labels plus Kimi K3 whole-tuple
adjudication remain required before correctness, Cbit gain, or Anti-Additive
promotion can be assessed. Current state:
`AXIS_ROUTED_PARTIAL_ABOVE_COVERAGE_GATE_AWAITING_EXTERNAL_PANEL`.

The complete local experiment suite now passes 273 tests. v0.17 artifacts,
analysis, replay/rollback pointers, hash inventory, and the two-lane external
annotation return pack are in `outputs/axis_credibility_routing_v0_17`.

Both v0.17 external lanes validate with exact panel identity, 24/24 coverage,
blinding attestation, legal enums, bounded confidence, nonempty rationale, and
coherent full tuples. They agree on 11/24 complete tuples. Axis agreement is
17/24 selected object, 12/24 selection basis, 15/24 pragmatic preference, and
18/24 completeness. Thirteen objects therefore enter anonymous whole-tuple
Kimi K3 adjudication.

The disagreement structure is systematic. All six family-balanced `x04`
missing-specification objects differ on all four axes: one lane uses
`UNCERTAIN + INCOMPLETE`, while the other treats justified nonselection as
`NONE + COMPLETE`. Four additional disputes are basis-only and isolate the
`LEXICAL_EXACT` versus `COMPOSITIONAL_ENTAILMENT` boundary. Candidate outputs,
model identities, case IDs, families, and construction provenance remain
absent from the K3 pack. Current state:
`AWAITING_KIMI_K3_FULL_TUPLE_ADJUDICATION`.

The Kimi K3 response passes 13/13 identity binding, anonymous-position
binding, confidence, rationale, and whole-tuple coherence validation. K3 uses
POSITION_1 six times and POSITION_2 seven times with mean confidence 0.93. The
frozen candidate reference contains 24 coherent objects and resolves every
assessment as `COMPLETE`, so completeness remains non-discriminating.

Final primary-axis scoring is 30/72 for the single-model baseline, 30/72 for
the role-informed coordinator, and 29/72 for axis routing. Relative to
baseline, routing changes selected-object correctness by zero, selection basis
by -2, and pragmatic preference by +1. It makes seven corrections and eight
harms, including the conservatively scored missing output. The routed path
uses 178,639 tokens versus 22,757 for baseline, a 7.850 ratio. Only the
coverage and selected-object-loss conditions pass; the preregistered semantic,
correction, basis, preference, and cost conditions fail. Anti-Additive returns
`REJECT`, with no baseline promotion or retention write.

The post-hoc diagnosis is not a replacement route. It shows that source
ranking reverses across holdouts, the current basis critic makes no correction
and two harms, and preference gains nearly cancel their harms. The next
admissible experiment is a new fresh object-conditional selective-escalation
holdout after retiring the basis critic and separating known evidence absence
from incomplete assessment. Current state:
`AXIS_ROUTING_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION`.

### Object-conditional selective escalation v0.18

The v0.18 experiment replaces static axis ownership with a narrower runtime
question: when is extra collaboration worth buying? It freezes 24 new objects,
cross-balanced across six object families and four construction strata. The
Provider baseline returns the semantic tuple plus a separate evidence state
and assessment-process state. Runtime admits collaboration only for
`SOFT_AMBIGUITY + selected NONE`, caps admissions at eight, and preserves the
frozen baseline on non-admission or failure. The v0.17 basis critic is absent;
the only possible specialist path is one local pragmatic role followed by one
focused DeepSeek preference adjudication.

The preregistration hash is
`2ca4ad78635e630483b4f4d7ced14dde27091fd16bfc05009b11cc473cf4f4fa`;
the fresh corpus hash is
`cfa79cefecc8f156333b2353a272889d502278c20cf46ed220a30f996e32eb3b`.
DeepSeek returns 21/24 mechanically and semantically valid baseline tuples.
Runtime rejects three additional tuples because their evidence state,
selection, and basis conflict. Among the 21 accepted outputs, DeepSeek labels
18 `DIRECTLY_DEFINED` and three `OPAQUE_REFERENCE`; it emits no
`SOFT_AMBIGUITY` object, so the frozen rule admits zero objects.

The zero-admission path deliberately skips local-model loading and additional
Provider calls. All 21 valid baseline outputs are preserved exactly, selected
object changes on zero objects, and routed-path cost equals baseline cost:
24,791 accounted tokens, including the three rejected invocations. Post-hoc
construction diagnostics suggest an evidence-state collapse: all six
compositional objects and the three accepted soft-ambiguity objects are called
`DIRECTLY_DEFINED`, as are three opaque-specification objects. Construction
strata are experimental design commitments, not reference truth, so external
GPT-5.6 and Gemini 3.1 labels remain necessary before admission recall or
misclassification can be claimed.

This is a useful negative result. The runtime avoided additive cost, but the
admission gate appears too overconfident to expose collaboration opportunities.
No baseline promotion or retention write is allowed. The complete local
experiment suite now passes 279 tests. Frozen analysis, replay and rollback
pointers, hash inventory, and the dual-lane external annotation return pack
are in `outputs/selective_escalation_v0_18`. Current state:
`SELECTIVE_ESCALATION_FROZEN_AWAITING_EXTERNAL_PANEL`.

Both v0.18 external responses pass exact lane binding, pack hash, 24/24
coverage, blinding, enum, confidence, rationale, and five-axis tuple-coherence
validation. They agree on 10/24 complete tuples. Axis agreement is 18/24 for
selected object, 10/24 for selection basis, 16/24 for pragmatic preference,
18/24 for evidence state, and 18/24 for assessment-process state. Fourteen
objects therefore enter anonymous whole-tuple Kimi K3 adjudication.

Both independent lanes identify six `SOFT_AMBIGUITY` and six
`OPAQUE_REFERENCE` objects, strongly localizing the frozen baseline's zero
admissions to evidence-state recognition rather than holdout composition.
Eight disagreements span two axes. All six opaque-design objects differ on
four axes because one lane represents missing defining evidence as
`UNCERTAIN + INCOMPLETE`, while the other represents justified nonselection as
`NONE + COMPLETE`. The K3 pack hides annotator identity, candidate outputs,
object family, and design stratum. Current state:
`AWAITING_KIMI_K3_SELECTIVE_FULL_TUPLE_ADJUDICATION`.

The Kimi K3 response passes 14/14 panel identity, pack binding, anonymous
position, confidence, rationale, and five-axis coherence checks. It selects
POSITION_1 eight times and POSITION_2 six times with mean confidence 0.9386.
K3 resolves every opaque reference as `NONE + NO_PREFERENCE + COMPLETE`: the
object remains unresolved, but the assessment process successfully determines
that neither candidate is supported.

The frozen 24-object candidate reference contains six collaboration-eligible
soft-ambiguity objects. The baseline gate admits none, yielding 0/6 recall;
precision is explicitly undefined because there are no predicted admissions.
Baseline and selective routing are identical: both score 35/72 primary cells,
68/120 across all five axes, and 3/24 complete tuples. Evidence-state
correctness is 12/24. Three soft-ambiguity tuples rejected during baseline
collection are conservatively incorrect, while the other three are
over-promoted to `DIRECTLY_DEFINED`.

No collaboration call occurs, so cost remains 24,791 tokens at a 1.0 routed
ratio. This is a gate failure, not evidence that pragmatic collaboration lacks
value: the collaboration path receives no admitted test object. The
preregistered recall, gain, correction, net-token, and coverage conditions
fail; Anti-Additive returns `REJECT`. No baseline promotion or retention write
is authorized. Current state:
`SELECTIVE_ESCALATION_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION`.

### Contrastive evidence-state calibration v0.19

The v0.19 experiment isolates admission prediction before restoring specialist
collaboration. It compares the old free-label evidence-state control with a
contrastive source calibrator on 24 entirely new objects. The Provider selects
an operative definition source; Runtime mechanically maps that source to
evidence state and selection basis. Candidate option text is explicitly
forbidden from counting as definition evidence.

The control arm retains 19/24 valid outputs and collapses to 18
`DIRECTLY_DEFINED`, one `OPAQUE_REFERENCE`, and zero `SOFT_AMBIGUITY`.
The calibrator retains 22/24 outputs and produces 14 direct, five opaque, and
three soft objects. Its definition sources are six established terms, eight
explicit definitions, five missing specifications, and three underspecified
surfaces. Seven outputs across both arms are rejected by semantic coherence
gates rather than repaired across arms.

The calibrator/control token ratio is 1.280, within the frozen 1.50 budget, but
calibrator coverage is 0.917 and therefore already below the preregistered
0.95 threshold. The observed recovery of soft and opaque states is promising
but remains structural, not accuracy evidence. GPT-5.6 and Gemini 3.1 external
labels are required before admission precision, soft recall, evidence-state
gain, or selected-object preservation can be scored. The complete experiment
suite now passes 284 tests. Current state:
`EVIDENCE_CALIBRATION_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL`.

Both v0.19 external lanes pass exact binding, 24/24 coverage, blinding,
five-axis enums, confidence, rationale, and tuple-coherence validation. They
agree on 14/24 complete tuples. Axis agreement is 18/24 selected object,
14/24 selection basis, 15/24 pragmatic preference, 23/24 evidence state, and
18/24 assessment-process state.

Both lanes independently identify six `SOFT_AMBIGUITY` and six
`OPAQUE_REFERENCE` objects. The ten whole-tuple disagreements comprise four
two-axis disputes and six four-axis disputes. As in v0.18, the six broad
disputes concern whether an opaque but correctly identified object should be
represented as `UNCERTAIN + INCOMPLETE` or `NONE + COMPLETE`. Candidate arms,
definition-source receipts, families, and design strata remain hidden from
the anonymous Kimi K3 pack. Current state:
`AWAITING_KIMI_K3_EVIDENCE_FULL_TUPLE_ADJUDICATION`.

The Kimi K3 response passes exact panel, pack, decision-ID, whole-tuple,
blinding, and coherence validation for all ten disputes. It selects six
`POSITION_1` and four `POSITION_2` tuples at mean confidence 0.898. All six
opaque-reference disputes resolve to a completed justified `NONE`; the frozen
24-object candidate reference therefore contains seven direct, five
compositional, six soft-ambiguity, and six opaque-reference objects. This is a
three-model candidate reference, not human gold or real-world validity.

Against that reference, contrastive calibration raises evidence-state
correctness from 8/24 to 14/24 and selected-object correctness from 12/24 to
18/24. Total correct five-axis cells rise from 52/120 to 69/120, while
full-tuple correctness rises from one to three objects. These are genuine local
semantic gains and satisfy the frozen evidence-gain, selected-object
preservation, and 1.280 token-ratio conditions.

The admission policy nevertheless fails. It predicts three soft objects, with
two true positives, one false positive, and four false negatives: precision
0.667 and recall 0.333. Two false negatives are retained semantic collapses to
`DIRECTLY_DEFINED`; two are missing outputs rejected by Runtime coherence
checks. One rejected receipt correctly identifies an underspecified surface
but uses an incoherent process tuple. The other exposes a sharper gate defect:
text explicitly stating that a denominator is undefined is misread as an
`EXPLICIT_REQUEST_DEFINITION`, then rejected as a decisive source without a
selection. Coverage is 0.917 and evidence-state accuracy is 0.583, so
precision, recall, coverage, and accuracy all fail their preregistered gates.

Anti-Additive therefore returns `REJECT`. The failed receipts remain preserved
as counterexamples; the frozen candidate is not repaired post hoc. No baseline
promotion, retention write, or production activation is authorized. The
complete experiment suite now passes 286 tests. Current state:
`EVIDENCE_CALIBRATOR_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION`.

### Source-recognition and gate-policy factorial v0.20

The v0.20 experiment separates the two failure mechanisms exposed by v0.19.
It freezes 24 entirely new objects across six structural families and four
construction strata, then runs a two-by-two factorial:

- legacy source prompt with legacy Runtime gate;
- repaired source prompt with legacy Runtime gate;
- legacy source prompt with repaired Runtime gate;
- repaired source prompt with repaired Runtime gate.

Only two Provider calls are made per object. Each raw source receipt is
preserved and passed through both Runtime gates, so gate comparison does not
duplicate Provider work. The repaired gate keeps decisive-source hard stops,
but represents a recognized soft or opaque state as a completed assessment and
mechanically maps an unsupported uncertain preference to no supported default.
The repaired Provider prompt distinguishes a positive definition from text
stating that a definition is absent.

Both source-prompt lanes complete 24/24 Provider calls. Legacy-source/legacy-
gate coverage is 0.708; the repaired gate recovers seven rejected receipts and
raises legacy-source coverage to 1.000. The repair performs ten open-state
completion transforms and seven unsupported-preference-to-none transforms.
This is a real structural availability gain, but external reference tuples are
still required to determine whether the admitted outputs are semantically
correct.

The source-prompt repair produces a second, opposed collapse. It changes 21/24
source tuples, increases `UNDERSPECIFIED_SURFACE` from four to twelve, and
classifies all six compositional-design objects as soft ambiguity. Among six
direct-design objects, only three remain direct; one becomes soft and two are
correctly rejected by both gates because the Provider claims an explicit
definition without selecting an object. The combined cell therefore has only
0.875 coverage and does not structurally dominate the legacy-source/repaired-
gate cell. The repaired/legacy source-prompt token ratio is 1.052.

These construction strata are localization aids, not reference truth.
Candidate outputs, source policies, gate policies, object families, and strata
remain hidden from the GPT-5.6 and Gemini 3.1 annotation lanes. The current
24 objects are now retired from further prompt tuning. No factor can be
promoted until the frozen model-panel reference scores precision, recall,
evidence-state accuracy, selected-object preservation, false soft admissions,
coverage, and cost. The complete experiment suite now passes 291 tests.
Current state:
`EVIDENCE_FACTORIAL_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL`.

Both v0.20 annotation lanes now pass exact panel identity, pack binding,
24/24 annotation coverage, blinding, five-axis enums, confidence, rationale,
and tuple-coherence validation. They agree on 13/24 complete tuples. Axis
agreement is 18/24 selected object, 13/24 selection basis, 15/24 pragmatic
preference, 22/24 evidence state, and 18/24 assessment-process state.

Both lanes independently recover six `SOFT_AMBIGUITY` and six
`OPAQUE_REFERENCE` objects. GPT-5.6 divides the remaining twelve into eight
direct and four compositional objects; Gemini 3.1 divides them evenly into six
and six. The eleven whole-tuple disputes comprise six four-axis opaque-state
conventions, three two-axis soft-default disputes, and two two-axis
direct-versus-compositional disputes.

This pattern sharpens both v0.20 hypotheses without yet scoring them. Agreement
on six rather than twelve soft objects strongly constrains the repaired source
prompt's expansion. Conversely, the six opaque disputes directly test the
repaired gate's conversion from `UNCERTAIN + INCOMPLETE` to a completed
justified `NONE`. All eleven disputes are now in one anonymous Kimi K3 pack;
annotator identities, candidate arms, source receipts, factorial policies,
families, strata, and prior scores remain hidden. The complete experiment
suite now passes 292 tests. Current state:
`AWAITING_KIMI_K3_FACTORIAL_FULL_TUPLE_ADJUDICATION`.

Kimi K3 validates all eleven whole-tuple decisions against the anonymous pack,
selecting eight `POSITION_1` and three `POSITION_2` tuples at mean confidence
0.911. The frozen 24-object candidate reference contains seven direct, five
compositional, six soft-ambiguity, and six opaque-reference objects; all 24
assessment processes are `COMPLETE`. This remains a three-model candidate
reference rather than human gold or real-world validity.

The final factorial evaluation isolates a strong but incomplete gate effect.
Under the legacy source prompt, repaired gating raises coverage from 0.708 to
1.000, correct five-axis cells from 53/120 to 86/120, evidence-state
correctness from 10/24 to 15/24, selected-object correctness from 14/24 to
20/24, and full-tuple correctness from zero to eight. It does so without an
additional Provider call. Admission precision is 0.750 with three true
positives and one false positive, but recall remains 0.500 and evidence-state
accuracy 0.625. The gate mechanism is therefore worth carrying into a new
ablation, but this frozen cell is not independently promotable.

The repaired source prompt is anti-additive. Its source-only and combined cells
are identical: 72/120 correct cells, 14/24 evidence-state and selected-object
correctness, ten full tuples, and 0.875 coverage. Soft recall rises to 0.833,
but twelve predicted soft objects contain seven false positives, reducing
precision to 0.417. Relative to legacy-source/repaired-gate, source repair loses
14 correct cells and six selected-object cases. The all-cell interaction is
-33, showing that malformed source receipts remove the very cases on which
gate repair provides value.

The combined cell passes recall, minimum evidence-correct gain, selected-object
loss, and token-ratio conditions. It fails precision, evidence-state accuracy,
coverage, and maximum false-soft admissions. Anti-Additive returns `REJECT`.
No baseline promotion, retention write, or production activation is
authorized. The current 24 labels remain retired from tuning. The complete
experiment suite now passes 294 tests. Current state:
`EVIDENCE_FACTORIAL_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION`.

The v0.21 source-ontology ablation carries forward only the surviving
legacy-source/repaired-gate cell as its baseline. It freezes 24 new objects
across six new object families before Provider inference. The candidate source
receipt separates lexical definition, compositional derivation, external
specification dependency, and pragmatic preference. One axis receipt is reused
by a legacy-enum collapse path and a native Runtime synthesis path, so their
difference does not require another Provider call.

The local DeepSeek R1 32B run completes all 48 source calls with no failures.
All three cells have complete coverage, and the decomposed source uses 1.219
times the baseline source tokens. Structural behavior is concerning rather
than confirmatory: the baseline emits 12 direct, six soft, and six opaque
states, while both axis paths emit eight direct, twelve compositional, and four
uncertain states. They emit no soft or opaque states and are identical on all
five output axes for all 24 objects.

Private construction diagnostics sharpen the suspected mechanism without
serving as reference truth. Five of six missing-specification objects are
reported as `REQUIRED_AVAILABLE`; four are assigned a compositional candidate.
Four of six open-surface objects are also assigned a compositional candidate.
This suggests that decomposing a question into fields can cause the Provider to
repeat candidate rationalization across fields rather than produce independent
evidence. GPT-5.6 and Gemini 3.1 whole-tuple labels are required before this can
be scored as semantic harm or gain. The 24 candidate outputs are frozen and
retired from tuning. No promotion, retention write, or production activation
is authorized. The complete experiment suite now passes 300 tests. Current
state:
`SOURCE_ONTOLOGY_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL`.

Both v0.21 annotation lanes now pass exact identity, pack binding, blinding,
24/24 coverage, five-axis enum, rationale, confidence, and tuple-coherence
validation. They agree on 12/24 complete tuples. Axis agreement is 18/24
selected object, 12/24 selection basis, 15/24 pragmatic preference, 21/24
evidence state, and 18/24 assessment-process state.

Both lanes independently identify six soft-ambiguity and six opaque-reference
objects. GPT-5.6 divides the remaining twelve into nine direct and three
compositional objects; Gemini 3.1 divides them evenly into six and six. This
sharply contradicts the decomposed source arm's zero soft and zero opaque
outputs, but it remains candidate evidence until whole-tuple disputes are
adjudicated.

The twelve disputes comprise six four-axis opaque-completion conventions, three
two-axis soft-default conventions, and three two-axis
direct-versus-compositional conventions. They are frozen in one anonymous Kimi
K3 pack. Annotator identities, candidate outputs, source receipts, source
ontology policies, Runtime gates, object families, design strata, and prior
scores remain withheld. No semantic reference, promotion, retention write, or
production activation is authorized before K3 adjudication. The complete
experiment suite now passes 301 tests. Current state:
`AWAITING_KIMI_K3_SOURCE_ONTOLOGY_FULL_TUPLE_ADJUDICATION`.

Kimi K3 validates all twelve whole-tuple decisions, selecting nine
`POSITION_1` and three `POSITION_2` tuples at mean confidence 0.920. The
resulting three-model candidate reference contains eight direct, four
compositional, six soft-ambiguity, and six opaque-reference objects. All 24
assessment processes are `COMPLETE`. This remains internal model-panel
evidence rather than human gold or real-world validity.

The final evaluation rejects unconditional source-axis decomposition. The
legacy-source/repaired-gate baseline scores 92/120 correct five-axis cells,
seven complete tuples, 24/24 selected objects, and 18/24 evidence states. It
identifies six soft objects with precision and recall both 0.833. The collapsed
and native axis paths are identical: 66/120 correct cells, zero complete
tuples, 12/24 selected objects, 12/24 evidence states, and zero soft-object
recall. Relative to baseline, each loses 26 correct cells, twelve
selected-object cases, six evidence-state cases, and seven complete tuples.

Native Runtime synthesis contributes no correction after the decomposed
Provider receipt is formed. The representation induces correlated candidate
rationalization: missing specifications and ordinary open surfaces are
converted into apparently decisive compositional evidence. The native cell
passes only coverage, source-token ratio, and maximum false-soft conditions. It
fails precision, recall, evidence-state accuracy, evidence gain, and
selected-object preservation. Anti-Additive returns `REJECT`.

Unconditional decomposed-axis prompting is retired. A future fresh mechanism
may test evidence objects before labels: quoted support spans, explicit
derivation steps, and absence witnesses that cannot cite candidate option text.
Axis analysis should be considered only as a selective challenge for
low-confidence or internally inconsistent baseline receipts. The baseline's
relative advantage does not authorize its promotion as a complete solution.
No retention write or production activation follows. The current 24 labels are
retired from tuning. The complete experiment suite now passes 303 tests.
Current state:
`SOURCE_ONTOLOGY_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION`.

The v0.22 evidence-first selective mechanism freezes 16 new objects across
four new families. It runs the surviving legacy-source/repaired-gate baseline
once per object, then mechanically admits at most four decisive and two open
receipts to a two-stage challenge. The first Provider call may produce only
quoted support spans, derivation steps, or an absence witness. Runtime verifies
that every support span is an exact substring of the evidence text before
candidate options. A separate judge receives only the verified witness and
candidate identities. Failed witnesses or judgments preserve baseline output.

The local DeepSeek R1 32B run completes all 16 baseline calls and admits six
objects. Five challenges complete; one witness is rejected because it
paraphrases rather than exactly quotes the displayed evidence. The selective
arm preserves complete output coverage and changes only two objects, each on
selected object, selection basis, and evidence state. Total selective tokens
are 1.733 times baseline tokens. Twenty-seven Provider calls are recorded.

Evidence-first sequencing therefore limits answer churn and activates its
mechanical boundary, but it does not yet establish correction. Witness
validation is 0.833 and fails the preregistered 1.0 requirement. Both changed
objects are missing-specification constructions whose witnesses claim positive
definition, so the same named-request-versus-available-definition confusion may
remain in a more selective form. GPT-5.6 and Gemini 3.1 whole-tuple labels are
required to classify the two changes as corrections or harms and to score net
Cbit. No promotion, retention write, or production activation is authorized.
The 16 candidate outputs are frozen and retired from tuning. The complete
experiment suite now passes 308 tests.

The validated GPT-5.6 and Gemini 3.1 lanes agree on eight of sixteen complete
tuples. Their axis agreement counts are 12 selected objects, eight selection
bases, eleven pragmatic preferences, thirteen evidence states, and twelve
assessment-process states. The eight whole-tuple disputes separate into four
opaque completion conventions, three direct-versus-compositional boundaries,
and one soft-default convention. Both lanes independently recover four soft
and four opaque objects.

`EW-TA04` and `EW-TE04` are the only outputs changed by the evidence-first
challenge. Across their six changed axes, neither challenge value is supported
by either validated lane position: both lanes classify each object as opaque
and neither selects Candidate A. Selecting either supplied K3 position
therefore leaves every challenge change unsupported, although K3 retains an
independent reassessment option. This is candidate model-panel evidence, not
human gold, and does not yet freeze the semantic reference. The anonymous Kimi
K3 whole-tuple pack contains the eight disputes without lane identity,
candidate outputs, challenge plans, or witness receipts. Current state:
`AWAITING_KIMI_K3_EVIDENCE_FIRST_FULL_TUPLE_ADJUDICATION`.

Kimi K3 validates all eight adjudication decisions at mean confidence 0.945,
selecting six `POSITION_2` and two `POSITION_1` tuples. The resulting
three-model candidate reference contains six direct, two compositional, four
soft-ambiguity, and four opaque-reference objects. All sixteen assessment
processes are `COMPLETE`. This remains internal model-panel evidence rather
than human gold or real-world validity.

The final evidence-first evaluation is negative. The baseline scores 59/80
correct five-axis cells and five complete tuples; the selective challenge
scores 55/80 and the same five complete tuples. It produces zero corrections
and four harms: selected-object correctness falls from 13/16 to 11/16 and
selection-basis correctness from 12/16 to 10/16. Evidence-state correctness
does not improve. The selective path consumes 10,552 incremental tokens,
reaches 1.733 times baseline cost, and yields a proxy delta of -0.379 correct
cells per thousand incremental tokens.

Only output coverage and the token-ratio ceiling pass. Net cell gain,
evidence-state gain, challenged full-tuple gain, selected-object preservation,
corrections-over-harms, and witness-validation requirements fail.
Anti-Additive returns `REJECT`; the current evidence-first challenge is retired
without promotion or retention write. Exact-span provenance is insufficient:
the next fresh mechanism must bind the requested object, available definition
source, missing-specification status, and candidate entailment before a
positive-definition witness can be admitted. Current state:
`EVIDENCE_FIRST_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION`.

The v0.23 relational-witness mechanism freezes another sixteen fresh objects
across four new families. It replaces the second free-form Provider judge with
one structured receipt that binds the requested object, definition-source
availability, evidence relation, candidate entailment, and contextual default.
Runtime alone maps a validated receipt to the five-axis tuple. The frozen
challenge budget remains four decisive and two open baseline receipts, while
the token-ratio ceiling is reduced to 1.55.

The local DeepSeek R1 32B run fails structurally before semantic evaluation.
One baseline receipt fails the existing repaired gate, leaving both cells at
15/16 coverage. All six relational receipts fail validation and preserve their
baseline outputs, so the candidate arm produces no completed challenges and no
semantic changes. The path consumes 22,852 tokens versus 14,617 baseline
tokens, a ratio of 1.563 that narrowly exceeds the frozen ceiling.

Post-hoc diagnostics separate three mechanisms without changing the gate:
two otherwise plausible direct-definition receipts are rejected by an
overstrict rule that forbids explanatory steps; two receipts violate exact
grounding by importing candidate-side language or fabricating an ellipsis; and
two receipts retain the central semantic error by promoting an open surface to
an available definition or collapsing a missing named source into ordinary
underspecification. The richer representation localizes failure more clearly,
but the current contract is not a usable execution path.

No external annotation pack is generated because zero relational outputs
complete and the arm makes no changes. v0.23 is frozen without prompt repair or
rerun. The next fresh mechanism should permit harmless explanatory steps,
keep exact quote checks, separate source-availability judgment from candidate
entailment, and give explicit missing-source evidence a Runtime veto over
`AVAILABLE`. The complete experiment suite passes 311 tests. Current state:
`RELATIONAL_WITNESS_STRUCTURAL_VALIDATION_FAILED_NO_EXTERNAL_PANEL`.

The v0.24 candidate-blind funnel tests a smaller contract on eight fresh
synthetic smoke objects. The first Provider stage receives only evidence text
and a conflict identifier; candidate options are withheld. Runtime routes only
validated `AVAILABLE` receipts to a second candidate-entailment stage and
synthesizes missing, unspecified, and conflicted branches locally. Four source
statuses are represented by two objects each. The claim ceiling is structural
smoke evidence, not external semantic validity.

Candidate blindness passes mechanically at 8/8 source calls, adaptive routing
is exact, and the one observed entailment receipt validates. The raw Provider
source-status judgment matches private synthetic construction on 7/8 objects,
with no false `AVAILABLE` promotion. Candidate blindness therefore removes the
v0.23 pattern in which candidate-side wording turns open evidence into a
positive definition.

The smoke gate still rejects. Only five of eight source receipts pass exact
grounding, output coverage is 0.625, and accepted-receipt construction match is
0.8. Three otherwise status-correct receipts reproduce evidence with ellipsis,
paraphrase, or grammatical normalization. The remaining semantic error maps a
missing named source to ordinary underspecification. The run uses 7,954 tokens
across nine Provider calls.

The full fresh holdout remains unauthorized and no external panel is
generated. Exact evidence integrity remains a Runtime responsibility, but
Provider-side quote reproduction is retired as the transport mechanism. The
next structural smoke should have Runtime deterministically segment evidence
and assign immutable span IDs; Provider receipts should select span IDs and
semantic relations instead of copying source text. The complete experiment
suite passes 314 tests. Current state:
`CANDIDATE_BLIND_FUNNEL_SMOKE_REJECTED_STOP`.

The v0.25 immutable span-ID funnel freezes eight more synthetic smoke objects
across four new families. Runtime deterministically segments the
candidate-blind evidence surface, assigns each span an immutable identifier and
text hash, and later resolves accepted identifiers back to source text.
Provider receipts can select identifiers and semantic relations but cannot
copy or paraphrase evidence. `CONFLICTED` requires at least two source-status
span identifiers, and candidate entailment may use only identifiers admitted
by a validated `AVAILABLE` source receipt.

The transport layer closes cleanly. All eight Runtime span packs revalidate,
all eight source receipts pass the identifier contract, all six routed
entailment receipts validate, no entailment introduces a new identifier, and
output coverage remains complete. The v0.24 quote-copy failures disappear.

The semantic gate nevertheless rejects decisively. DeepSeek classifies six
objects as `AVAILABLE` and two as `UNSPECIFIED`, matching synthetic
construction metadata on only two of eight objects. Both missing-source
objects collapse to `UNSPECIFIED`; both truly unspecified objects and both
conflicted-source objects are falsely promoted to `AVAILABLE`. The resulting
four false routes expand the run to fourteen task calls and 17,755 tokens,
exceeding both frozen budgets.

This separates evidence transport from source-status cognition: immutable
identifiers solve provenance integrity but do not teach the Provider the
difference between a requested object, an available definition, a missing
named source, an unspecified rule, and conflicting definitions. On both
conflicted objects, the receipt selects only the first local definition and
does not bind the counterevidence span, exposing premature local closure rather
than an evidence-identity failure. v0.25 is closed without rerun,
full-holdout authorization, external annotation, promotion, or retention
write. Any repair must use a new fresh smoke rather than tuning against these
eight construction labels. The complete experiment suite passes 318 tests.
Current state: `SPAN_ID_FUNNEL_SMOKE_REJECTED_STOP`.

## Current boundary

The local Provider and measurement prerequisites live entirely in this pack.
Direct structure-elicitor calibration and a repeated fresh holdout are now
present. Dual-Provider semantic assessment remains blocked for disagreement;
the validated GPT-5.6/Gemini-3.1 responses agree on 60/66 criterion cells. The
six disputes now have a validated clean-session K3 receipt and a complete
candidate-only reference artifact. Two noncanonical K3 records remain as
shadow evidence: the second honestly discloses session compromise and flips
4/6 dispute cells without changing any packet verdict. The paired
unstated-ambiguity holdout is now complete and fails the single-model gate while
exposing opposed proposer/skeptic error orientations. A broader corpus,
randomized generation seeds, confidence intervals, and hard-null coordinator
replication remain future experiment artifacts. The first fresh coordinator
test produced positive but insufficient gain; the independent hard-null test
then produced negative gain and incomplete controlled receipts. The separate
receipt-quality calibration also failed because DeepSeek systematically
over-promoted semantically defective receipts. The split negative-evidence
candidate passes its frozen calibration gates against a complete model-panel
candidate reference. Distribution-shifted v0.2 candidate predictions are now
frozen, but independent reference labels remain outstanding and the
heterogeneous arm is contract-incomplete. No accepted baseline, global memory
write, or production activation follows from these local results.
## v0.26: Science constraints and structure-first problem emergence

The v0.26 external experiment freezes the institutional principles from
*"Agentic AI and the next intelligence explosion"* as upper-level constraints.
They do not authorize a large new CoreSlim module. In particular, a single
Provider response is not counted as group cognition, simulated consequences
remain candidate-only, and recursive sub-society formation remains blocked.

The accompanying fresh synthetic smoke tests a MiroFish-inspired mechanism
without copying MiroFish code or introducing its AGPL implementation into the
Apache-2.0 AgentOS base. Twelve unseen object worlds are evaluated under four
arms:

- `A0_DIRECT`: formulate problems directly.
- `A1_ONTOLOGY`: expand a multiview object census first.
- `A2_GRAPH`: add evidence-bound relations and graph-position perspectives.
- `A3_INTERVENTION`: add reverse, removal, object-switch, coordinate-switch,
  and counterexample interventions.

The primary metric is recovery of privately frozen unresolved object
relations, not the amount of structure emitted. Construction metadata is never
sent to the Provider. Runtime validates registry and evidence references,
scores the receipts, applies the preregistered gate, and emits replay,
rollback, hash inventory, manifest, and return-pack artifacts. The experiment
is isolated under `outputs/structural_world_v0_26`; it cannot write retention,
baseline, selection, or production state.
## v0.27: frontier gray admission and realized Cbit

Protocol v0.27 separates permission boundaries from epistemic gray states.
Whole-receipt blocking is reserved for case, arm, evidence-scope, and
parseability failures. Valid problem candidates survive unrelated malformed
ontology components as `PARTIAL_CANDIDATE`; weakly supported but falsifiable
ideas remain `SPECULATIVE_COMPONENT`; invalid references are quarantined
without erasing neighboring cognition.

`CORE` and `FRONTIER` candidates use one outcome-bound Cbit ledger. Frontier
status receives no bonus, while a falsifiable negative result may earn
positive Cbit when it prunes the frozen problem space. Token cost, quarantined
component friction, and unsupported promotion risk remain explicit.

The live experiment first runs a two-object neutral transport/token preflight.
Only a passed preflight may freeze the twelve-domain fresh holdout. The formal
comparison is intentionally limited to arm-native `A0_DIRECT` and
`A1_ONTOLOGY` receipts; A0 never sees ontology fields. Raw Provider receipts
are persisted before projection and checkpointed after every task. All
artifacts remain external, synthetic, candidate-only, and unable to write
CoreSlim, retention, baseline, selection, or production state.

## v0.28: higher-Cbit stability before cost compression

Protocol v0.28 tests whether the positive v0.27 ontology signal survives a
fresh twelve-domain holdout under two context-isolated object/evidence order
replications. Both replications use the same frozen outcome model and the same
v0.27 realized Cbit weights. Each A0/A1 comparison receives an arm-native
schema, raw receipts are checkpointed before projection, and no v0.27 labels
are reused.

The primary decision variable is net realized Cbit after token cost and
coordination friction have already been subtracted. Cbit per token remains a
diagnostic, not a second acceptance gate. A higher-token A1 arm may therefore
pass as `PASS_HIGHER_CBIT_HIGHER_COST` when both replications show positive
gain, pooled case wins and frontier outcomes are stable, severe losses remain
bounded, and the hard resource-runaway cap is not crossed.

A pass authorizes only an independent external semantic panel. It does not
establish cross-provider stability and cannot promote candidates or write
CoreSlim, retention, baseline, selection, or production state.

## v0.29: role collaboration under full cognitive cost

Protocol v0.29 removes the candidate-volume ambiguity exposed by v0.28. Every
final A0, A1, and A2 receipt must contain exactly three eligible candidates.
The fresh ten-domain holdout is repeated under three object/evidence orders.

`A2_COLLAB` uses three genuinely isolated Provider contexts: mechanism mapping,
adversarial falsification, and object/coordinate shift. Their nine candidate
records form a frozen pool. A fourth evidence-first selector may choose three
pool IDs but cannot rewrite or generate a candidate. Runtime mechanically
checks pool membership, relation uniqueness, evidence scope, and final
admission.

All three proposer calls and the selector call are charged to A2 before
realized Cbit is compared with the single-call ontology and direct baselines.
The frozen gate requires positive mean and median gain, majority object wins,
replication consistency, bounded severe losses, and relation reproducibility.
Token efficiency remains diagnostic after token cost has already been
subtracted; only a resource-runaway cap is a hard cost stop.

The protocol remains synthetic, external, candidate-only, and unable to write
CoreSlim, retention, baseline, selection, or production state.

## v0.30: provider-backed selective role routing

Protocol v0.30 replaces all-role consultation with a pre-execution structural
router. For each fresh object world, the router chooses exactly one of the
default ontology, mechanism, adversarial, or coordinate-shift paths. Only the
selected worker runs, and the routed arm pays both router and worker tokens.
The baseline and routed receipts each contain exactly three candidates.

Three object/evidence-order replications test net Cbit, median and majority
object gain, severe losses, and relation reproducibility. One frozen
replication also executes unselected routes as a shadow audit. Those calls
measure private-outcome route regret but are excluded from deployment-path
Cbit and included in the physical resource cap.

Shadow best-route labels are diagnostic only. They cannot train the current
router, change its frozen decision, authorize production routing, or write
CoreSlim, retention, baseline, selection, or production state.

## v0.31: single-call comparative plan intent

Protocol v0.31 removes the separate routing call. One Provider receipt compares
all four route utilities and anti-additive risks, permits no escalation, then
generates exactly three candidates bound to the selected plan. Runtime checks
complete route comparison, utility-max selection, execution mode, margin-based
fallback, and candidate-plan consistency before scoring.

The fresh three-replication comparison charges each arm one Provider call.
Plan receipts remain synthetic, external, candidate-only, and unable to write
CoreSlim, retention, baseline, selection, or production state.

## v0.32: receipt-native lazy metacognition

Protocol v0.32 removes the fixed full-plan tax exposed by v0.31. The ordinary
ontology receipt first generates exactly three usable candidates and then emits
one compact escalation trigger. The trigger may keep the receipt as final or
request exactly one mechanism, adversarial, or coordinate-shift worker.

Runtime validates trigger consistency, evidence-span scope, route registration,
and final receipt quality. A specialized call is made only when the trigger
claims positive expected net Cbit after coordination and token cost. The lazy
arm pays for both calls whenever escalation occurs; untriggered cells pay only
for the receipt that already produced their final candidates.

The frozen gate evaluates net realized Cbit, repeated-case stability, severe
loss, relation reproducibility, completion, trigger-contract coverage, and a
hard runaway cap. Trigger rate itself is diagnostic rather than a target. This
prevents the experiment from passing by learning to always escalate or never
escalate.

The fresh eight-domain holdout is repeated under three object/evidence orders.
Private synthetic outcomes remain unavailable during inference. Raw receipts,
provisional candidates, final candidates, triggers, failures, replay,
rollback, and hashes remain external and candidate-only; no CoreSlim,
retention, baseline, selection, or production write is authorized.

## v0.33: zero-marginal-token Runtime escalation

Protocol v0.33 removes the remaining Provider-generated trigger text. A1 and
A2 receive exactly the same standard ontology objective, schema, public input,
and evidence scope. Runtime hashes the Provider-visible payload for every
paired cell and derives a replayable escalation receipt from the ordinary
three-candidate response.

The frozen policy observes only structural properties already present in that
response: unique relation count, represented-object coverage, bound-evidence
coverage, target concentration, and speculative fraction. It can flag relation
collapse, a narrow object frame, thin evidence binding, or speculation
dominance. No private outcome, semantic label, keyword classifier, or extra
Provider output is available to the trigger.

Unflagged A2 receipts become final without another call. A flagged receipt may
invoke exactly one mechanism, adversarial, or coordinate-shift worker. Runtime
then charges both the standard and specialized calls before comparing net Cbit
with A1. Prompt identity, trigger replay, worker execution, final receipt
quality, repeated-case stability, relation reproducibility, severe loss, and a
hard runaway cap are frozen gates; trigger rate itself remains diagnostic.

The fresh eight-domain hard/null holdout contains six registered objects and
seven evidence spans per case and is repeated under three order perturbations.
All raw and derived receipts remain external, synthetic, candidate-only, and
unable to write CoreSlim, retention, baseline, selection, or production state.

## v0.34: lineage-aware role revision

Protocol v0.34 keeps the v0.33 Runtime trigger policy unchanged and changes
only the triggered role interaction. The specialist receives the provisional
receipt, public evidence, and Runtime diagnostic. It must map each original
candidate slot to exactly one final slot using `KEEP`, `REVISE`, or `REPLACE`.

Runtime rejects disguised rewrites. `KEEP` must preserve every candidate field;
`REVISE` may improve evidence, constraints, falsifier, or test design but must
preserve the source-target relation; `REPLACE` must change that relation.
Candidate IDs, addressed diagnostic flags, evidence spans, worker route, and
the three-slot lineage are mechanically validated before final projection.

The formal gate now measures not only final net Cbit but the triggered worker's
gross candidate uplift, gross win and loss rates, token penalty, action mix,
lineage coverage, and relation reproducibility. There is still no selector
call. A specialist may keep all three candidates when no revision has clear
expected value.

The fresh eight-domain holdout is repeated under three object/evidence orders.
Standard A1/A2 Provider payloads remain identical, private outcomes remain
hidden during inference, and all artifacts remain synthetic, external,
candidate-only, and unable to write CoreSlim, retention, baseline, selection,
or production state.

## v0.35: Runtime-derived candidate diff

Protocol v0.35 removes Provider-declared revision actions and route echoes.
The triggered worker returns only the best final three-candidate receipt using
the original candidate IDs. Runtime compares every normalized candidate field
with the provisional receipt and derives the action as a fact.

An unchanged slot is `KEEP`; a changed slot with the same source-target
relation is `REVISE`; a changed relation is `REPLACE`. Runtime records changed
fields, relation change, final evidence spans, inherited route, source hashes,
and the no-private-truth boundary in a replayable diff receipt. A missing,
duplicated, or substituted candidate slot remains fail-closed.

The v0.33 trigger policy remains frozen. Formal gates retain final net Cbit,
worker gross uplift and loss rate, token penalty, prompt identity, lineage
coverage, relation reproducibility, and hard resource bounds. This stage tests
actual content revision, not whether a model can correctly describe the action
it took.

The fresh eight-domain holdout is repeated under three order perturbations.
All artifacts remain synthetic, external, candidate-only, and unable to write
CoreSlim, retention, baseline, selection, or production state.

## v0.36: independent counterproposal and candidate-wise arbitration

Protocol v0.36 separates exploration from preservation. The frozen v0.33
Runtime trigger still decides whether an additional path is warranted. When
triggered, an independent counterproposer sees the public case and selected
route but does not see provisional candidates or trigger diagnostics. This
tests whether context isolation restores the exploration suppressed in v0.35.

Runtime then constructs a six-entry pool from the three provisional and three
counterproposal candidates. Every entry has a globally unique pool ID, an
explicit source, and a canonical object-relation ID. A separate arbiter may
select exactly three entries but may not rewrite or generate candidates. It
must bind selected pool IDs and relation IDs in the same order, and Runtime
rejects duplicate relations or broken bindings before mechanically assigning
the final `C1`-`C3` IDs.

Formal scoring charges the triggered arm for the standard call, independent
counterproposal, and arbiter. Gross arbitration uplift, source adoption,
contract coverage, net Cbit, severe loss, repeated-case stability, relation
reproducibility, and the hard resource cap are frozen gates. A failed
additional stage preserves the provisional receipt as a fallback but still
fails the corresponding execution gate.

The fresh eight-domain holdout is repeated under three order perturbations.
Private outcomes remain unavailable during inference. Raw receipts, pools,
selections, mechanical lineage, failures, replay, rollback, and hashes remain
external and candidate-only; no CoreSlim, retention, baseline, selection, or
production write is authorized.

## v0.37: source-blind candidate value composition

Protocol v0.37 replaces free-form pool selection with a factorized semantic
value receipt. After the unchanged Runtime trigger and independent
counterproposal, Runtime blinds candidate provenance and exposes six opaque
candidate IDs. The Provider must evaluate every candidate independently for
relation evidence, counterevidence handling, constraint binding,
falsifiability, expected Cbit, and an admit/hold/reject verdict.

Relation evidence explicitly distinguishes supported effects, supported nulls,
indirect evidence, weak evidence, and genuine conflict. This prevents useful
negative results from being treated as low-value candidates merely because an
effect is absent.

The Provider cannot see `BASE` or `COUNTER` source labels, cannot see internal
pool IDs or the frozen numeric score map, and cannot select final candidates.
Runtime validates full six-candidate coverage and relation/evidence bindings,
applies the preregistered score map, keeps the highest-scoring candidate for
each relation, and deterministically composes the top three distinct
relations.

Formal scoring charges the standard, counterproposal, and value-receipt calls.
The fresh eight-domain holdout, three order perturbations, private-outcome
oracle audit, replay, rollback, and all raw/derived receipts remain external,
synthetic, candidate-only, and unable to mutate CoreSlim, retention, baseline,
selection, or production state.

## v0.38: embedded self-value composition

Protocol v0.38 removes the separate candidate-value Provider call. The
standard A1/A2 receipts and the independent counterproposal all use the same
expanded schema: every generated candidate carries the six factorized value
axes introduced in v0.37. Standard self-value cost is symmetric between arms;
the triggered arm pays only for one additional counterproposal.

Runtime validates every embedded value receipt, applies the unchanged v0.37
semantic score map, adds a small source-local ordinal bonus to reduce
cross-role scale drift, deduplicates relations, and deterministically composes
three candidates. Providers cannot see numeric scores and cannot select the
final set. A separate value-judgment stage is forbidden by the frozen gate.

This stage tests whether self-assessment preserves enough of v0.37's oracle
capture to make collaboration net-positive after token cost. The fresh
eight-domain holdout, three order perturbations, private-outcome calibration
audit, raw receipts, replay, rollback, and hashes remain external, synthetic,
candidate-only, and unable to mutate CoreSlim, retention, baseline, selection,
or production state.

## v0.39: truth-state and research-value separation

Protocol v0.39 keeps the zero-third-call topology of v0.38 but replaces its
ambiguous verdict. Each embedded candidate value now separates
`relation_truth_state` from `research_value_disposition`. A dedicated
`null_discrimination` axis records whether a supported null rules out a
plausible cause, constrains a boundary, or is merely redundant.

Runtime enforces cross-field consistency. A supported null must state its
discriminating role. A null that rules out a plausible cause or constrains a
boundary cannot be marked `DISCARD` or assigned negative expected Cbit.
Non-null candidates cannot claim null discrimination. These are meta-rules
over Provider-backed semantic judgments, not local keyword classification.

The existing evidence, counterevidence, constraint, falsifiability, and Cbit
weights remain unchanged. Runtime adds the explicit null-discrimination value,
applies the same source-local ordinal calibration, deduplicates relations, and
deterministically composes three candidates. Providers still cannot see the
numeric map or select the final set.

The fresh eight-domain holdout, three order perturbations, private-outcome
truth/value calibration audit, raw receipts, replay, rollback, and hashes
remain external, synthetic, candidate-only, and unable to mutate CoreSlim,
retention, baseline, selection, or production state.

## v0.49: schema-enforced warrant replication

Protocol v0.49 freezes a fresh eight-domain holdout and preserves the v0.48
review-ready/admission-ready split. A delta must now echo the exact source
warrant set in its JSON schema as well as pass Runtime lineage validation.
The cognitive-quality gate requires repeated positive gross Cbit, zero harmful
acceptance, full lineage coverage, and independent pairwise review. Token cost
is reported separately and only the hard runaway ceiling can stop the run.

The formal run was rejected rather than promoted. All eight authorized deltas
preserved their warrants and semantic lineage, all eight completed pairwise
review, and there were no Provider or contract failures. One accepted
informative null yielded `+2.0` gross and `+0.30` net Cbit, with no harmful
acceptance, but the frozen minimum of two beneficial acceptances was not met.

Private synthetic audit found a sharper bottleneck: six of eight proposed
compositions had positive gross value and none had negative gross value, while
the pairwise gate rejected five beneficial proposals. The rationales often
treated displacement from the current top-three composition as permanent
deletion, even though raw candidates remain preserved. The next experiment
should therefore test non-destructive portfolio displacement and marginal
Cbit arbitration without weakening evidence, lineage, or safety boundaries.

Artifacts remain external, synthetic, candidate-only, and unable to write
CoreSlim, retention, baseline, selection, or production state.

## v0.50: non-destructive portfolio displacement

Protocol v0.50 reframes pairwise replacement as a bounded active-portfolio
decision. The base and delta candidates both remain preserved; the arbiter
chooses only which candidate occupies the third active slot beside two fixed
companions. Its receipt must acknowledge zero permanent deletion cost and
compare marginal Cbit without giving positive-effect hypotheses categorical
priority over informative nulls.

The fresh formal run was rejected. Five cells reached delta generation, four
passed exact-warrant lineage and portfolio review, and two deltas were
activated. One activation gained `+2.0` gross Cbit and one lost `-0.5`, so the
frozen zero-harm and 100% gross-win gates correctly blocked promotion. One
additional `+1.0` proposal was rejected.

The run exposed two upstream validity problems. First, fixed companions used
local `C1`/`C2` identifiers that collide across BASE and COUNTER sources; two
arbiter rationales therefore misread a new delta as already active. Second,
the accepted cell scored harmful by private provenance cited an evidence span
that semantically supports its informative-null interpretation, making the
synthetic reference potentially incomplete. The next experiment must use
source-qualified candidate IDs and audit reference completeness before
claiming either improved safety or stable harm.

All artifacts remain external, synthetic, candidate-only, and unable to write
CoreSlim, retention, baseline, selection, or production state.

## v0.51: reference-complete source-qualified portfolio

Protocol v0.51 removes both validity ambiguities found in v0.50. Portfolio
identities are source-qualified (`BASE:C*` and `COUNTER:C*`), and local
candidate IDs are forbidden in arbiter receipts. Before preregistration, two
isolated Provider roles exhaustively assessed every focal relation in a fresh
eight-case holdout. All 16 audit receipts were contract-valid, with zero
cross-role disagreements and zero mismatches against the frozen synthetic
reference. This remains internal provider-audited synthetic evidence, not
external gold.

The formal run was rejected rather than promoted. Nine cells were authorized;
eight preserved exact-warrant lineage and completed pairwise review, while one
failed closed with `DELTA_RELATION_NOT_DISTINCT`. Four deltas were activated.
All four produced positive gross Cbit, with mean and median `+1.5` and no
harmful acceptance. No arbiter rationale confused BASE and COUNTER identities,
so the v0.50 identifier defect was not reproduced.

Private posthoc found eight beneficial proposals in the valid review set. The
gate accepted four and rejected four, yielding 100% precision on accepted
cells but only 50% positive-oracle capture. The bottleneck has therefore moved
from unsafe acceptance to conservative recall. Communication cost remained
material: accepted-cell mean net uplift was about `-0.59` after a mean
`2.09` Cbit-equivalent token penalty, and total usage was 188,231 tokens,
above the 183,643 soft reference but below the 214,251 hard stop.

The next experiment should target conservative marginal-Cbit arbitration
without relaxing evidence, lineage, source identity, or fail-closed controls.
Token reduction is useful but remains secondary to stable gross Cbit.

All artifacts remain external, synthetic, candidate-only, and unable to write
CoreSlim, retention, baseline, selection, or production state.

## v0.52: selective rejection challenge

Protocol v0.52 tests whether a rejected delta can receive structured
adversarial review without weakening Runtime authority. The initial acceptance
path is unchanged. Only `KEEP_BASE_ACTIVE` or unresolved receipts can enter a
rejection challenger. A challenger may request reopening but cannot activate a
candidate; a separate coordinator must resolve the evidence conflict before
the existing lineage, lane, protection, and state gates can accept the delta.

The fresh eight-domain holdout rotates effect, informative-null, and unresolved
relations across object positions. A preregistration-time dual-role reference
audit completed 16/16 receipts with zero contract failures, reference
mismatches, or cross-role disagreements.

The formal run was rejected as underpowered. Twenty raw triggers produced only
three qualified deltas under the frozen v0.41 qualification policy. Two were
accepted directly. The sole initial rejection was reopened by the challenger
and accepted by the coordinator. All three accepted cells gained `+2.0` gross
Cbit, and private posthoc confirmed that the coordinated recovery was
beneficial rather than harmful. Within the valid review set, positive-oracle
capture was 100%.

This is positive mechanism evidence, not sufficient replication: only one
rejection reached the challenger, below the frozen minimum of two, and only
three proposals could be accepted, below the minimum of five. Twenty-one of 24
receipts did not qualify; 20 were below the frozen semantic-spread threshold
because the fresh holdout produced more balanced candidate sets. The next
bottleneck is therefore cross-distribution qualification calibration, upstream
of portfolio arbitration.

All artifacts remain external, synthetic, candidate-only, and unable to write
CoreSlim, retention, baseline, selection, or production state.

## v0.53: context-normalized qualification

Protocol v0.53 replaces absolute semantic-spread dependence with a
zero-additional-token structural opportunity signal. The old asymmetry branch
remains unchanged. A new branch qualifies only when Runtime diagnostics have
already triggered and the standard receipt contains a review-ready focal
relation outside the current three candidates that is bound to evidence not
used by those candidates. Qualification does not read outcomes, add Provider
calls, or lower the v0.41 threshold.

Before the fresh run, an unlabeled replay over v0.51 and v0.52 changed
qualification from 9 and 3 cells to 19 and 17 cells, with a cross-source rate
range of 0.083. On a third fresh rotated holdout, the policy qualified 19/24
cells, including 17 through the structural-gap branch. This matched the
unlabeled calibration and stayed inside the frozen 8–22 range.

Eighteen deltas were authorized, 17 passed lineage and pairwise review, and one
failed closed with `DELTA_RELATION_NOT_DISTINCT`. Seven proposals were
accepted; every accepted proposal gained `+2.0` gross Cbit and none was
harmful. Twelve initial rejections reached the challenger, seven reopened, and
four were activated by the coordinator. Private posthoc confirmed all four
coordinated recoveries as beneficial.

The overall run remained rejected. The single duplicate delta reduced lineage
coverage below the frozen 1.0 requirement, and all accepted proposals belonged
to the informative-null lane, missing the required second acceptance lane.
Posthoc also found seven beneficial rejections and three safe tie rejections,
so positive-oracle capture remained 50%. Qualification is no longer the active
bottleneck; the remaining losses separate into effect-lane witness acquisition
and conservative arbitration.

All artifacts remain external, synthetic, candidate-only, and unable to write
CoreSlim, retention, baseline, selection, or production state.
